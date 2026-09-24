from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientCreate

router = APIRouter()


@router.post("/patients")
def create_patient(
    patient: PatientCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    new_patient = Patient(
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        user_id=user_id
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return {
        "message": "Patient created successfully",
        "patient_id": new_patient.id
    }