"""Modele SQLAlchemy - Table recommandations générées"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Recommandation(Base):
    __tablename__ = "recommandations"

    id = Column(String(36), primary_key=True, index=True)
    reclamation_id = Column(String(36), nullable=True, index=True)
    action_suggeree = Column(Text, nullable=False)
    taux_succes = Column(Float, nullable=False)
    nb_cas_similaires = Column(Integer, nullable=False)
    priorite = Column(Integer, nullable=False)
    statut_impl = Column(String(50), default="en_attente")
    valide_par = Column(String(150), nullable=True)
    commentaire_validation = Column(Text, nullable=True)
    date_validation = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())