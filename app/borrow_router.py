from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .models import Book, Borrower, User
from .role import user_required, get_current_user_jwt, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC
import os
import shutil

# database setup 
db_path = os.path.join("/tmp", "library.db")
if not os.path.exists(db_path):
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "..", "library.db"), db_path)
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

borrow_router = APIRouter(tags=["borrowing"])

@borrow_router.post("/borrow/{book_id}")
def borrow_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(user_required)):
    
    # finds the borrower record for this user
    borrower = db.query(Borrower).filter(Borrower.user_id == user.id).first()

    if not borrower:
        # creates a borrower record if not exists
        borrower = Borrower(user_id=user.id)
        db.add(borrower)
        db.commit()
        db.refresh(borrower)

    # checks if already borrowed 3 books
    if len(borrower.books_borrowed) >= 3:
        raise HTTPException(status_code=400, detail="You cannot borrow more than 3 books.")
    
    # checks if book exists and is available
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if not book.available:
        raise HTTPException(status_code=400, detail="Book is not available.")
    # Check if already borrowed this book
    if book in borrower.books_borrowed:
        raise HTTPException(status_code=400, detail="You have already borrowed this book.")
    # Borrow the book
    borrower.books_borrowed.append(book)
    book.available = False
    book.last_borrowed_date = datetime.now(UTC)
    db.commit()
    return {"message": f"Book '{book.title}' borrowed successfully."}

@borrow_router.post("/return/{book_id}")
def return_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(user_required)):
    borrower = db.query(Borrower).filter(Borrower.user_id == user.id).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="You have no borrowed books.")
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if book not in borrower.books_borrowed:
        raise HTTPException(status_code=400, detail="You have not borrowed this book.")
        
    # Return the book
    borrower.books_borrowed.remove(book)
    book.available = True
    db.commit()
    return {"message": f"Book '{book.title}' returned successfully."} 