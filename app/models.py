from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# table for many to many relationship between Borrower and Book
borrower_books = Table(
    'borrower_books', Base.metadata,
    Column('borrower_id', Integer, ForeignKey('borrower.id'), primary_key=True),
    Column('book_id', Integer, ForeignKey('book.id'), primary_key=True)

)


# table for user model
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default='user') # role for the user ( user, admin, staff) 



# table for author model 
class Author(Base):
    __tablename__ = 'author'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    bio = Column(Text)
    books = relationship('Book', back_populates='author') # relationship with book model 


# table for book model 
class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    isbn = Column(String, unique=True, nullable=False)
    author_id = Column(Integer, ForeignKey('author.id'), nullable=False)
    published_date = Column(Date)
    available = Column(Boolean, default=True)
    last_borrowed_date = Column(DateTime)
    author = relationship('Author', back_populates='books') # realtionship with author model  
    borrowers = relationship('Borrower', secondary=borrower_books, back_populates='books_borrowed') # relationship with borrower model 



# table for borrower model 
class Borrower(Base):
    __tablename__ = 'borrower'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship('User') # relationship with user model 
    books_borrowed = relationship('Book', secondary=borrower_books, back_populates='borrowers') # relationship with book model  

    def can_borrow_more(self):
        return len(self.books_borrowed) < 3





