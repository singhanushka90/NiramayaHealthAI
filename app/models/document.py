from sqlalchemy import Column , Integer , String , DateTime ,ForeignKey,Text,JSON
from sqlalchemy.sql import func
from app.db.database import Base

class Document(Base):
    __tablename__="documents"
    id=Column(Integer,primary_key=True,index=True)
    patient_id=Column(Integer,ForeignKey("patients.id"),nullable=False)
    file_name=Column(String,nullable=False)
    file_path=Column(String,nullable=False)
    file_type=Column(String,nullable=False)
    
    uploaded_at=Column(DateTime(timezone=True),server_default=func.now())
    extracted_text=Column(Text,nullable=True)
    pdf_type=Column(String(20),nullable=True)
    document_type=Column(String(100),nullable=True)
    extraction_method=Column(String(30),nullable=True)
    processing_status=Column(String(30),default="pending",nullable=True)
    cbc_values=Column(JSON,nullable=True)
