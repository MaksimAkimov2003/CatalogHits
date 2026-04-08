import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Тот же способ конфигурации, что принят в «боевом» запуске: URL из окружения
# (в тестах задаётся до импорта приложения, см. tests/conftest.py).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recipe_book.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
