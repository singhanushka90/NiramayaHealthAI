from pydoc import doc

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import shutil

from app.db.database import get_db
from app.models.patient import Patient
from app.models.document import Document
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.document_processor import process_document


router = APIRouter()


@router.post("/documents/upload")
def upload_document(
    patient_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )


    if not file.file_name or Path(file.file_name).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )


    upload_dir = Path("uploads") / f"patient_{patient_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / Path(file.file_name).name

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()


    new_document = Document(
        patient_id=patient_id,
        file_name=Path(file.file_name).name,
        file_path=str(file_path),
        file_type=file.content_type or "application/pdf",
        processing_status="pending"
    )

    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        result = process_document(str(file_path))

        
        if result.get("status") != "success":
            new_document.processing_status = "error"
            db.commit()

            return {
                "message": "PDF uploaded, but text processing failed",
                "document_id": new_document.id,
                "processing_status": "error",
                "details": result.get("message", "Text extraction failed")
            }

    
        pdf_info = result["pdf_info"]
        classification = result["classification"]

        new_document.extracted_text = result["extracted_text"]
        new_document.pdf_type = pdf_info["document_type"]
        new_document.document_type = classification["document_type"]
        new_document.extraction_method = (
            "ocr"
            if pdf_info["document_type"] == "scanned"
            else "digital_text"
        )
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
            "text_length": len(new_document.extracted_text or ""),
            "processing_status": new_document.processing_status
        }

    except Exception:
        db.rollback()

        # Try to mark the document as failed if its record exists
        try:
            db.refresh(new_document)
            new_document.processing_status = "error"
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Document processing or database save failed. Check backend logs."
        )


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

    upload_root = (Path.cwd() / "uploads").resolve()
    file_path = Path(document.file_path).resolve()

  
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Document path is outside the uploads directory"
        )

    
    if file_path.exists():
        if not file_path.is_file():
            raise HTTPException(
                status_code=400,
                detail="Document path is not a file"
            )

        try:
            file_path.unlink()
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Could not delete the PDF file"
            )


    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not delete the document record"
        )

    return {
        "message": "Document deleted successfully",
        "document_id": document_id,
        "file_deleted": True
    }

@router.get("/patients/{patient_id}/documents")
def list_patient_documents(
    patient_id: int,
    current_user:User=Depends(get_current_user),
    db: Session =Depends(get_db)
):
    patient=db.query(Patient).filter(Patient.id==patient_id,
                                     Patient.user_id==current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )
    documents=(
        db.query(Document)
        .filter(Document.patient_id==patient_id)
        .order_by(Document.uploaded_at.desc()).all())
    return {
        "patient_id":patient_id,
        "total_documents":len(documents),
        "documents":[
            {"id":doc.id,
             "file_name":doc.file_name,
             "file_type":doc.file_name,
             "pdf_type":doc.pdf_type,
             "documents_type":doc.document_type,
             "extraction_method":doc.extraction_method,
             "processing_status":doc.processing_status,
             "uploaded_at":doc.uploaded_at}
             for doc in documents
        ]
    }
