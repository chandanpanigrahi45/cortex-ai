from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Credit_Transaction, User
from pydantic import BaseModel, Field
from security import create_access_token, get_current_user, password_hash

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

def auth_response(user: User):
    try:
        token = create_access_token(user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "credit_balance": user.credit_balance,
        },
    }

@router.post("/")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    username = user_data.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=422, detail="Username must contain at least 3 characters")
    email = user_data.email.strip().lower()
    db_user = db.query(User).filter(User.email == email).first()
    username_exists = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    if username_exists:
        raise HTTPException(status_code=409, detail="Username already taken")

    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash.hash(user_data.password),
        credit_balance=100,
    )
    db.add(new_user)
    db.flush()
    db.add(Credit_Transaction(
        user_id=new_user.id,
        amount=100,
        transaction_type="signup_bonus",
    ))
    response = auth_response(new_user)
    db.commit()
    db.refresh(new_user)
    response["user"]["credit_balance"] = new_user.credit_balance
    return response

@router.post("/login")
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_data.email.strip().lower()).first()
    if not db_user or not db_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not password_hash.verify(user_data.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return auth_response(db_user)

@router.get("/me")
def get_current_user_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "credit_balance": user.credit_balance,
    }
