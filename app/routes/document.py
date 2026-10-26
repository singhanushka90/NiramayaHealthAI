from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
)
from sqlalchemy.orm import Session
from pathlib import Path
import shutil

from app.db.database import get_db
from app.models.patient import Patient
from app.models.document import Document
from app.models.user import User
from app.core.dependencies import get_current_user

from app.services.document_processor import process_document
from app.services.qdrant_service import store_document_chunks


router = APIRouter()


# --------------------------------------------------
# 1. Upload and Process PDF
# --------------------------------------------------

@router.post("/documents/upload")
def upload_document(
    patient_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check whether patient belongs to the logged-in user
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id == current_user.id,
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    # Allow only PDF files
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    # Create patient-specific upload directory
    upload_dir = Path("uploads") / f"patient_{patient_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Keep only the filename, not any supplied directory path
    file_name = Path(file.filename).name
    file_path = upload_dir / file_name

    # Save uploaded PDF
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not save the uploaded PDF",
        ) from exc
    finally:
        file.file.close()

    # Create document database record
    new_document = Document(
        patient_id=patient_id,
        file_name=file_name,
        file_path=str(file_path),
        file_type=file.content_type or "application/pdf",
        processing_status="pending",
    )

    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        # Step 1: Extract text, classify, chunk and generate embeddings
        result = process_document(str(file_path))

        if result.get("status") != "success":
            new_document.processing_status = "error"
            db.commit()

            return {
                "message": "PDF uploaded, but text processing failed",
                "document_id": new_document.id,
                "processing_status": "error",
                "details": result.get(
                    "message",
                    "Text extraction failed",
                ),
            }

        pdf_info = result["pdf_info"]
        classification = result["classification"]

        # Step 2: Save extracted medical data in PostgreSQL
        new_document.extracted_text = result["extracted_text"]
        new_document.pdf_type = pdf_info["document_type"]
        new_document.document_type = classification["document_type"]
        new_document.cbc_values = result.get("cbc_values")

        new_document.extraction_method = (
            result.get("extraction_method", "digital_text")
        )

        # Save extracted data before attempting vector storage
        new_document.processing_status = "pending"
        db.commit()
        db.refresh(new_document)

        # Step 3: Store chunks and embeddings in Qdrant Cloud
        stored_chunks = store_document_chunks(
            document_id=new_document.id,
            patient_id=patient_id,
            chunks=result["chunks"],
            embeddings=result["embeddings"],
        )

        # Step 4: Mark processing successful only after Qdrant storage
        new_document.processing_status = "success"
        db.commit()
        db.refresh(new_document)

        return {
            "message": "Document uploaded and processed successfully",
            "document_id": new_document.id,
            "patient_id": patient_id,
            "file_name": new_document.file_name,
            "pdf_type": new_document.pdf_type,
            "document_type": new_document.document_type,
            "extraction_method": new_document.extraction_method,
            "cbc_values": new_document.cbc_values,
            "text_length": len(new_document.extracted_text or ""),
            "qdrant_chunks_stored": stored_chunks,
            "processing_status": new_document.processing_status,
        }

    except HTTPException:
        raise

    except Exception as exc:
        import traceback
        traceback.print_exc()

        db.rollback()

        # Best-effort status update for an already-created record.
        try:
            existing_document = db.query(Document).filter(
                Document.id == new_document.id
            ).first()

            if existing_document:
                existing_document.processing_status = "error"
                db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing or Qdrant storage failed. "
                "Check backend logs."
            ),
        ) from exc



@router.get("/patients/{patient_id}/documents")
def get_patient_documents(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify patient ownership
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    documents = db.query(Document).filter(
        Document.patient_id == patient_id
    ).order_by(Document.uploaded_at.desc()).all()

    return {
        "patient_id": patient_id,
        "total_documents": len(documents),
        "documents": [
            {
                "id": document.id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "pdf_type": document.pdf_type,
                "document_type": document.document_type,
                "extraction_method": document.extraction_method,
                "processing_status": document.processing_status,
                "uploaded_at": document.uploaded_at
            }
            for document in documents
        ]
    }




@router.get("/documents/{document_id}")
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .join(Patient, Document.patient_id == Patient.id)
        .filter(
            Document.id == document_id,
            Patient.user_id == current_user.id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {
        "id": document.id,
        "patient_id": document.patient_id,
        "file_name": document.file_name,
        "file_type": document.file_type,
        "pdf_type": document.pdf_type,
        "document_type": document.document_type,
        "extraction_method": document.extraction_method,
        "processing_status": document.processing_status,
        "extracted_text": document.extracted_text,
        "cbc_values": document.cbc_values,
        "uploaded_at": document.uploaded_at
    }




@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .join(Patient, Document.patient_id == Patient.id)
        .filter(
            Document.id == document_id,
            Patient.user_id == current_user.id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )


    upload_root = Path("uploads").resolve()
    file_path = Path(document.file_path).resolve()

    
    if file_path != upload_root and upload_root not in file_path.parents:
        raise HTTPException(
            status_code=400,
            detail="Invalid document file path"
        )

    
    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document from database"
        )

    try:
        if file_path.is_file():
            file_path.unlink()
    except OSError:
        
        pass

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }