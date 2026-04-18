# ============================================================
# Dockerfile — API PFE Attijari bank
# ============================================================

FROM python:3.11-slim

# ── Métadonnées ───────────────────────────────────────────────
LABEL maintainer="PFE Attijari bank — Sujet 21"
LABEL description="API FastAPI — Système IA & RPA détection anomalies IT"
LABEL version="1.0.0"

# ── Variables d'environnement ─────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# ── Dépendances système ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Répertoire de travail ─────────────────────────────────────
WORKDIR /app

# ── Dépendances Python ────────────────────────────────────────
# Copier requirements en premier pour bénéficier du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Code source ───────────────────────────────────────────────
COPY . .

# ── Créer les dossiers nécessaires ───────────────────────────
RUN mkdir -p logs backups data/raw data/processed data/cleaned models

# ── Utilisateur non-root (sécurité) ──────────────────────────
RUN useradd -m -u 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# ── Port exposé ───────────────────────────────────────────────
EXPOSE 8000

# ── Healthcheck ───────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Commande de démarrage ─────────────────────────────────────
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
