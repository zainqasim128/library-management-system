from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .models import Author
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .role import staff_or_admin_required, get_current_user_jwt
import os
import shutil

# database setup 
db_path = os.path.join("/tmp", "library.db")
if not os.path.exists(db_path):
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "..", "library.db"), db_path)
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# get the database session 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# --- Authentication & Role Dependency Stubs ---
class UserStub(BaseModel):
    id: int
    username: str
    role: str  # 'user', 'staff', 'admin'



def get_current_user():
    return UserStub(id=1, username="admin", role="admin")




def staff_or_admin(user: UserStub = Depends(get_current_user)):
    if user.role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    return user



# pydantic schemas 
class AuthorCreate(BaseModel):
    id: int
    name: str
    bio: str = ""


class AuthorRead(BaseModel):
    id: int
    name: str
    bio: str
    class Config:
        orm_mode = True


class AuthorUpdate(BaseModel):
    name: str = None
    bio: str = None




# router 
author_router = APIRouter(prefix="/authors", tags=["authors"])


@author_router.post("/", response_model=AuthorRead, status_code=201, dependencies=[Depends(staff_or_admin_required)]) # create author 
def create_author(author: AuthorCreate, db: Session = Depends(get_db)):
    # checks if author with id already exists
    if db.query(Author).filter(Author.id == author.id).first():
        raise HTTPException(status_code=400, detail="Author with this id already exists.")
    db_author = Author(id=author.id, name=author.name, bio=author.bio)
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    return db_author



@author_router.get("/", response_model=List[AuthorRead])   # get all the authors 
def list_authors(db: Session = Depends(get_db)):
    return db.query(Author).all()



@author_router.get("/{id}", response_model=AuthorRead) # get author by id 
def get_author(id: int, db: Session = Depends(get_db)):
    author = db.query(Author).filter(Author.id == id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author




@author_router.put("/{id}", response_model=AuthorRead, dependencies=[Depends(staff_or_admin_required)]) # update author by the id  
def update_author(id: int, author_update: AuthorUpdate, db: Session = Depends(get_db)): 
    author = db.query(Author).filter(Author.id == id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    if author_update.name is not None:
        author.name = author_update.name
    if author_update.bio is not None:
        author.bio = author_update.bio
    db.commit()
    db.refresh(author)
    return author




@author_router.delete("/{id}", status_code=204, dependencies=[Depends(staff_or_admin_required)]) # delete author by the id 
def delete_author(id: int, db: Session = Depends(get_db)):
    author = db.query(Author).filter(Author.id == id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    db.delete(author)
    db.commit()
    return None 







