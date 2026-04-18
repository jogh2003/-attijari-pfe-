"""Modele SQLAlchemy - Table reclamations"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Reclamation(Base):
    __tablename__ = "reclamations"

    id                   = Column(String(36),  primary_key=True, index=True)
    date                 = Column(DateTime,     nullable=False)
    type_operation       = Column(String(100),  nullable=False, index=True)
    categorie            = Column(String(100),  nullable=True)
    objet                = Column(Text,         nullable=True)
    description          = Column(Text,         nullable=True)
    action_effectuee     = Column(Text,         nullable=True)
    severite             = Column(Integer,      nullable=False, default=2)
    statut               = Column(String(50),   default="soumise", index=True)
    priorite_orig        = Column(String(50),   nullable=True)
    type_demande         = Column(String(50),   nullable=True)
    en_retard            = Column(Boolean,      default=False)
    duree_resolution_min = Column(Float,        nullable=True)
    score_anomalie       = Column(Float,        nullable=True)
    score_risque         = Column(Float,        nullable=True)
    created_at           = Column(DateTime,     server_default=func.now())
