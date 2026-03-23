"""Modele SQLAlchemy - Table reclamations"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Reclamation(Base):
    __tablename__ = "reclamations"
    id = Column(String, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    type_operation = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    action_effectuee = Column(Text, nullable=True)
    severite = Column(Integer, nullable=False, default=1)
    statut = Column(String(50), default="soumise")
    score_anomalie = Column(Float, nullable=True)
    score_risque = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
