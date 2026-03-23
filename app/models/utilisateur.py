"""Modele SQLAlchemy - Table utilisateurs"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(String, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(String(50), default="utilisateur")
    est_actif = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
