from .models import Base
from sqlalchemy import create_engine

engine = create_engine('sqlite:///library.db')
Base.metadata.create_all(engine)
print('Database and tables created!') 