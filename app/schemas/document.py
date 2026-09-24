from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: int
    patient_id: int
    file_name: str
    file_path: str
    file_type: str

    class Config:
        from_attributes=True
