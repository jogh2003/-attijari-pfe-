"""Modele SQLAlchemy - Table alertes clôturées"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Alerte(Base):
    __tablename__ = "alertes"

    id = Column(String(36), primary_key=True, index=True)
    reclamation_id = Column(String(36), nullable=False, index=True)
    statut = Column(String(50), default="active")
    action_effectuee = Column(Text, nullable=True)
    cloture_par = Column(String(150), nullable=True)
    date_cloture = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())