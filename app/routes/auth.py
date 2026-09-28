from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate,UserLogin
from app.core.security import hash_password,verify_password,create_access_token

router=APIRouter()


@router.post("/register")
def register(user:UserCreate,db:Session=Depends(get_db)):
    hashed_password=hash_password(user.password)
    new_user=User(email=user.email,password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return{
        "message":"User registered successfully",
        "user_id":new_user.id,
        "email":new_user.email
    }


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        return {"message": "Invalid email or password"}

    password_valid = verify_password(
        user.password,
        db_user.password_hash
    )

    if not password_valid:
        return {"message": "Invalid email or password"}

    access_token=create_access_token(db_user.id)

    return {
        "message": "Login successful",
        "access_token":access_token,
        "token_type":"bearer"
    }
