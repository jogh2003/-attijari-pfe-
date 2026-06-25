"""Modele SQLAlchemy - Table responsables (contacts IT)"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Responsable(Base):
    __tablename__ = "responsables"

    id = Column(String(36), primary_key=True, index=True)
    nom = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    telephone = Column(String(50), nullable=True)
    role = Column(String(50), default="responsable_it")
    service = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
