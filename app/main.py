from fastapi import FastAPI
from .author_router import author_router
from .book_router import book_router
from .borrow_router import borrow_router
from .role import router


app = FastAPI()

app.include_router(router)
app.include_router(author_router)
app.include_router(book_router)
app.include_router(borrow_router) 
