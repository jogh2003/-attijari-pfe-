"""Router pour gérer les contacts `responsables` (CRUD)"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.responsable import Responsable
from app.routers.auth import verifier_token
from app.core.audit import log_action

router = APIRouter()


class ResponsableCreate(BaseModel):
    nom: str
    email: str
    telephone: str | None = None
    role: str | None = "responsable_it"
    service: str | None = "Infrastructure"


class ResponsableOut(BaseModel):
    id: str
    nom: str
    email: str
    telephone: str | None
    role: str | None
    service: str | None


@router.get("/", response_model=List[ResponsableOut], summary="Lister responsables")
async def lister_responsables(payload: dict = Depends(verifier_token), db: Session = Depends(get_db)):
    items = db.query(Responsable).order_by(Responsable.nom).all()
    return [
        ResponsableOut(
            id=r.id, nom=r.nom, email=r.email, telephone=r.telephone, role=r.role, service=r.service
        )
        for r in items
    ]


@router.post("/", response_model=ResponsableOut, summary="Créer responsable")
async def creer_responsable(data: ResponsableCreate, payload: dict = Depends(verifier_token), db: Session = Depends(get_db)):
    r = Responsable(id=str(uuid.uuid4()), nom=data.nom, email=str(data.email), telephone=data.telephone, role=data.role or "responsable_it", service=data.service)
    try:
        db.add(r)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Impossible de créer le responsable")
    log_action(utilisateur=payload.get("sub","anonyme"), role=payload.get("role",""), action="CREER_RESPONSABLE", details=r.email)
    return ResponsableOut(id=r.id, nom=r.nom, email=r.email, telephone=r.telephone, role=r.role, service=r.service)
