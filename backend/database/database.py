import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
SQL_LITE_URL = f"sqlite:///{os.path.join(DB_DIR, 'primoauditai.db')}"

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", SQL_LITE_URL)

# For SQLite, check_same_thread=False is needed. For Postgres, it throws an error.
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
