"""Modele SQLAlchemy - Table audit_logs"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(String(36),  primary_key=True, index=True)
    utilisateur  = Column(String(150), nullable=True, index=True)   # email ou identifiant
    utilisateur_id = Column(String(36), nullable=True)              # UUID si dispo
    role         = Column(String(50),  nullable=True)
    action       = Column(String(200), nullable=False, index=True)
    details      = Column(Text,        nullable=True)
    ip_address   = Column(String(50),  nullable=True)
    timestamp    = Column(DateTime,    server_default=func.now(), index=True)
