from sqlalchemy import create_engine,MetaData
from sqlalchemy.orm import sessionmaker,declarative_base
from dotenv import load_dotenv
import os

load_dotenv() 

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in environment")

try:
    engine = create_engine(DATABASE_URL,
    connect_args={"application_name": "delhi-ai",
                  "connect_timeout": 2},
                    pool_size=5,    # 5
                    max_overflow=15,  # 15
                    pool_pre_ping=True,
                    pool_recycle=1800,)
    SessionLocal = sessionmaker(autocommit = False,autoflush=False,bind=engine)
    
except Exception as e:
    print(f"Database Connection failed: {e}")


Base = declarative_base()