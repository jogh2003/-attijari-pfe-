"""Initialisation de la base de donnees PostgreSQL"""
import sys, uuid
sys.path.insert(0, ".")

def init():
    from app.core.database import engine, Base
    from app.models.reclamation import Reclamation
    from app.models.utilisateur import Utilisateur
    from app.models.audit_log import AuditLog
    from app.core.security import hash_password
    from sqlalchemy.orm import Session

    print("Creation des tables PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("Tables creees.")

    with Session(engine) as db:
        admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@attijaribank.tn").first()
        if not admin:
            admin = Utilisateur(
                id=str(uuid.uuid4()),
                nom="Administrateur",
                email="admin@attijaribank.tn",
                mot_de_passe=hash_password("Admin@2026!"),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("Admin cree : admin@attijaribank.tn / Admin@2026!")

if __name__ == "__main__":
    init()
