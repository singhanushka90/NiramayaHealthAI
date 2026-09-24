from fastapi import FastAPI
from app.db.database import engine,Base
from app.models.user import User
from app.models.patient import  Patient
from app.routes.auth import router as auth_router
from app.routes.patient import router as patient_router
from app.routes.document import router as document_router
from app.models.document import Document
Base.metadata.create_all(bind=engine)


app=FastAPI()
app.include_router(auth_router)
app.include_router(patient_router)
app.include_router(document_router)

@app.get("/")
def home():
    return {"message":"Niramaya AI backend is running"}