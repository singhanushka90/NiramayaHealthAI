from fastapi import FastAPI,Depends
from app.db.database import engine,Base
from app.models.user import User
from app.models.patient import  Patient
from app.routes.auth import router as auth_router
from app.routes.patient import router as patient_router
from app.routes.document import router as document_router
from app.models.document import Document
from app.core.dependencies import get_current_user
from app.models.user import User
Base.metadata.create_all(bind=engine)


app=FastAPI()
app.include_router(auth_router)
app.include_router(patient_router)
app.include_router(document_router)

@app.get("/me")
def get_me(current_user:User=Depends(get_current_user)):
    return {"user_id":current_user.id,
            "email":current_user.email}