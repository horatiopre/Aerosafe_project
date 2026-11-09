from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_token(username: str, password: str) -> str:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_mauvais_mot_de_passe():
    r = client.post("/auth/login", data={"username": "utilisateur", "password": "faux"})
    assert r.status_code == 401


def test_sans_jeton_refuse():
    assert client.get("/alerts").status_code == 401


def test_jeton_invalide_refuse():
    r = client.get("/alerts", headers={"Authorization": "Bearer nimportequoi"})
    assert r.status_code == 401


def test_utilisateur_ne_voit_pas_les_alertes():
    token = get_token("utilisateur", "utilisateur123")
    r = client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_superviseur_voit_les_alertes():
    token = get_token("superviseur", "superviseur123")
    r = client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200