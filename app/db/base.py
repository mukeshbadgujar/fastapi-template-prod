from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings


# Create SQLAlchemy engine
engine = create_engine(
    settings.SQLITE_URL, #DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base model for all database models
@as_declarative()
class Base:
    """
    Base class for SQLAlchemy models
    
    All models will have an __tablename__ attribute automatically generated
    from the class name
    """
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


def get_db() -> Generator:
    """
    Dependency function to get a database session
    
    Usage:
        @router.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
