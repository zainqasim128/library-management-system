from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .models import Book, Author
from pydantic import BaseModel, validator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
from .role import staff_or_admin_required, get_current_user_jwt
import re
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

# authentication and role dependency stubs
from .author_router import get_current_user, staff_or_admin, UserStub



# pydantic schemas 
class BookCreate(BaseModel):
    id: int
    title: str
    isbn: str
    author_id: int
    published_date: date
    available: bool = True
    last_borrowed_date: Optional[datetime] = None

    @validator('isbn')
    def validate_isbn(cls, v):
        # Remove hyphens for validation
        isbn = v.replace('-', '')
        if not (len(isbn) == 10 or len(isbn) == 13) or not isbn.isdigit():
            raise ValueError('ISBN must be a 10 or 13 digit number (hyphens allowed)')
        return v


class BookRead(BaseModel):
    id: int
    title: str
    isbn: str
    author_id: int
    published_date: date
    available: bool
    last_borrowed_date: Optional[datetime]
    class Config:
        orm_mode = True


class BookUpdate(BaseModel):
    title: Optional[str] = None
    isbn: Optional[str] = None
    author_id: Optional[int] = None
    published_date: Optional[date] = None
    available: Optional[bool] = None
    last_borrowed_date: Optional[datetime] = None

    @validator('isbn')
    def validate_isbn(cls, v):
        if v is None:
            return v
        isbn = v.replace('-', '')
        if not (len(isbn) == 10 or len(isbn) == 13) or not isbn.isdigit():
            raise ValueError('ISBN must be a 10 or 13 digit number (hyphens allowed)')
        return v


# router 
book_router = APIRouter(prefix="/books", tags=["books"])


@book_router.post("/", response_model=BookRead, status_code=201, dependencies=[Depends(staff_or_admin_required)])
def create_book(book: BookCreate, db: Session = Depends(get_db)):

    # checks if book with this id or isbn already exists
    if db.query(Book).filter(Book.id == book.id).first():
        raise HTTPException(status_code=400, detail="Book with this id already exists.")
    if db.query(Book).filter(Book.isbn == book.isbn).first():
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists.")


    # checks if author exists
    if not db.query(Author).filter(Author.id == book.author_id).first():
        raise HTTPException(status_code=400, detail="Author with this id does not exist.")
    
    # creates a new book 
    db_book = Book(
        id=book.id,
        title=book.title,
        isbn=book.isbn,
        author_id=book.author_id,
        published_date=book.published_date,
        available=book.available,
        last_borrowed_date=book.last_borrowed_date
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


@book_router.get("/", response_model=List[BookRead]) # get all the books 
def list_books(
    db: Session = Depends(get_db),
    title: Optional[str] = Query(None),
    author_id: Optional[int] = Query(None),
    available: Optional[bool] = Query(None),
    isbn: Optional[str] = Query(None)
):
    query = db.query(Book)
    # filters the books by title, author_id, available, and isbn 
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))

    if author_id:
        query = query.filter(Book.author_id == author_id)

    if available is not None:
        query = query.filter(Book.available == available)

    if isbn:
        query = query.filter(Book.isbn == isbn)
    return query.all()


@book_router.get("/{id}", response_model=BookRead) # get book by id 
def get_book(id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book



@book_router.put("/{id}", response_model=BookRead, dependencies=[Depends(staff_or_admin_required)]) # update book by id 
def update_book(id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == id).first()
    # checks if book exists
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book_update.title is not None:
        book.title = book_update.title

    if book_update.isbn is not None:
        # Check for unique ISBN
        if db.query(Book).filter(Book.isbn == book_update.isbn, Book.id != id).first():
            raise HTTPException(status_code=400, detail="Book with this ISBN already exists.")
        book.isbn = book_update.isbn

    if book_update.author_id is not None:
        # Check if author exists
        if not db.query(Author).filter(Author.id == book_update.author_id).first():
            raise HTTPException(status_code=400, detail="Author with this id does not exist.")
        book.author_id = book_update.author_id

    if book_update.published_date is not None:
        book.published_date = book_update.published_date

    if book_update.available is not None:
        book.available = book_update.available

    if book_update.last_borrowed_date is not None:
        book.last_borrowed_date = book_update.last_borrowed_date
    db.commit()
    db.refresh(book)
    return book


@book_router.delete("/{id}", status_code=204, dependencies=[Depends(staff_or_admin_required)]) # delete book by id 
def delete_book(id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return None 