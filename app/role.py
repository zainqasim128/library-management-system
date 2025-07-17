from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .models import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from typing import Optional
import os
import shutil

# database setup 
db_path = os.path.join("/tmp", "library.db")
if not os.path.exists(db_path):
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "..", "library.db"), db_path)
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT settings
class Settings(BaseModel):
    authjwt_secret_key: str = "super-secret-key"

@AuthJWT.load_config
def get_config():
    return Settings()

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"  # 'admin', 'staff', 'user'

class UserRead(BaseModel):
    id: int
    username: str
    role: str
    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str

# Role router
router = APIRouter(prefix="/role", tags=["role"])

@router.post('/register', response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post('/login')
def login(user: UserLogin, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = Authorize.create_access_token(subject=db_user.id)
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency to get current user from JWT

def get_current_user_jwt(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    try:
        Authorize.jwt_required()
    except AuthJWTException as e:
        raise HTTPException(status_code=401, detail=str(e))
    user_id = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Role-based dependencies
def admin_required(user: User = Depends(get_current_user_jwt)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def staff_or_admin_required(user: User = Depends(get_current_user_jwt)):
    if user.role not in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Staff or admin access required")
    return user

def user_required(user: User = Depends(get_current_user_jwt)):
    if user.role != "user":
        raise HTTPException(status_code=403, detail="User access required")
    return user 