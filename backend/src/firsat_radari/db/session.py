from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from firsat_radari.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
