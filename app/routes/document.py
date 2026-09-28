from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import shutil

from app.db.database import get_db
from app.models.patient import Patient
from app.models.document import Document
from app.models.user import User
from app.core.dependencies import get_current_user


router = APIRouter()


@router.post("/documents/upload")
def upload_document(patient_id: int,file: UploadFile = File(...),current_user:User=Depends(get_current_user),db: Session = Depends(get_db)):

    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id==current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    
    upload_dir = Path("uploads") / f"patient_{patient_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)


    file_path = upload_dir / Path(file.filename).name

   
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

   
    new_document = Document(
        patient_id=patient_id,
        file_name=file.filename,
        file_path=str(file_path),
        file_type=file.content_type
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return {
        "message": "Document uploaded successfully",
        "document_id": new_document.id,
        "patient_id": patient_id,
        "file_name": file.filename,
        "file_path": str(file_path)
    }