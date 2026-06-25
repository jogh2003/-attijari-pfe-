"""Smoke demo script — exercise main API flows using TestClient.
Run: python scripts/smoke_demo.py
"""
import os
import sys
from pathlib import Path
from pprint import pprint
from fastapi.testclient import TestClient

# Ensure project root on sys.path so `import app` works when run as script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure scheduler disabled
os.environ["TESTING"] = "true"

from app.main import app

client = TestClient(app)

RESULTS = {}

def login(email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    return r

# 1. Root + health
r = client.get("/")
RESULTS['root'] = r.status_code
r2 = client.get("/health")
RESULTS['health'] = r2.json()

# 2. Login robot and admin
robot = login("robot@attijaribank.tn", "Robot@2026!")
admin = login("admin@attijaribank.tn", "Admin@2026!")
RESULTS['robot_login'] = robot.json() if robot.status_code==200 else robot.status_code
RESULTS['admin_login'] = admin.json() if admin.status_code==200 else admin.status_code

robot_token = robot.json().get('access_token') if robot.status_code==200 else None
admin_token = admin.json().get('access_token') if admin.status_code==200 else None
headers_robot = {"Authorization": f"Bearer {robot_token}"} if robot_token else {}
headers_admin = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

# 3. Get responsable contact
r = client.get("/api/responsable", headers=headers_admin)
RESULTS['responsable'] = r.json() if r.status_code==200 else r.status_code

# 4. Get alertes
r = client.get("/api/alertes/?seuil=0.75", headers=headers_robot)
RESULTS['alertes_count'] = len(r.json()) if r.status_code==200 else r.status_code
RESULTS['sample_alerte'] = r.json()[0] if (r.status_code==200 and len(r.json())>0) else None

# 5. Notifier responsable for a sample alert id
sample_id = RESULTS['sample_alerte']['id'] if RESULTS['sample_alerte'] else 'REC-TEST-DEMO'
r = client.post(f"/api/alertes/{sample_id}/notifier", headers=headers_robot)
RESULTS['notifier'] = r.json()

# 6. Cloturer alert
r = client.post(f"/api/alertes/{sample_id}/cloturer", json={"action_effectuee":"Test action demo","statut_final":"resolue"}, headers=headers_robot)
RESULTS['cloturer'] = r.json() if r.status_code==200 else {'status': r.status_code}

# 7. Historique
r = client.get("/api/alertes/historique", headers=headers_robot)
RESULTS['historique_total'] = r.json().get('total') if r.status_code==200 else r.status_code

# 8. Predictions: predire
r = client.post("/api/predictions/predire", json={"type_operation":"Sécurité Opérationnelle","severite":1}, headers=headers_admin)
RESULTS['predire'] = r.json() if r.status_code==200 else r.status_code

# 9. Reclamations: analyser
r = client.post("/reclamations/analyser", json={"description":"Blocage firewall lors MAJ","type_operation":"Sécurité Opérationnelle","severite":1}, headers=headers_admin)
RESULTS['analyser'] = r.json() if r.status_code==200 else r.status_code

# 10. Recommandations: analyser
r = client.post("/api/recommandations/analyser", json={"texte":"Problème accès SWIFT","groupe":"SWIFT","categorie":"Erreur connexion"}, headers=headers_admin)
RESULTS['reco'] = r.json() if r.status_code==200 else r.status_code

# 11. List responsables
r = client.get("/api/responsables/", headers=headers_admin)
RESULTS['responsables_list'] = r.json() if r.status_code==200 else r.status_code

pprint(RESULTS)

# Quick pass/fail
ok = True
if not isinstance(RESULTS.get('root'), int) or RESULTS['root'] != 200:
    ok = False
if not RESULTS.get('admin_login') or 'access_token' not in RESULTS['admin_login']:
    ok = False
if not RESULTS.get('robot_login') or 'access_token' not in RESULTS['robot_login']:
    ok = False
print('\nSMOKE TEST RESULT :', 'PASS' if ok else 'FAIL')
if not ok:
    raise SystemExit(1)
