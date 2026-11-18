"""Santé des tâches de fond (0.21, socle 0.9.0) : /health porte version_socle, taches et copie_base ; messages
d'erreur seulement avec le jeton commun ; une préparation ratée fait passer sa tâche en erreur. Personnes inventées."""
import queue

import pytest
from fastapi.testclient import TestClient

from app import main, maison
from app.config import Config

MDP = "mot-de-passe-de-test"
COMMUN = "jeton-commun-de-test"


@pytest.fixture()
def registre(monkeypatch):
    neuf = maison.Taches()
    monkeypatch.setattr(maison, "TACHES", neuf)
    return neuf


@pytest.fixture()
def client(tmp_path, registre, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", COMMUN)
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True)
    with TestClient(main.app) as c:
        yield c
    main.ETAT.clear()


def test_health_porte_taches_et_copie(client):
    d = client.get("/health").json()
    assert d["ok"] is True and d["version"] == main.__version__ and "livrets" in d and "a_traiter" in d
    assert d["version_socle"] == "0.9.1"
    noms = {t["nom"]: t for t in d["taches"]}
    assert {"preparation", "recidive", "copie-des-bases"} <= set(noms)
    assert noms["preparation"]["type"] == noms["recidive"]["type"] == "demande"
    assert noms["copie-des-bases"]["type"] == "reguliere" and noms["copie-des-bases"]["periode_s"] == 86400
    assert all("message" not in t for t in d["taches"])                 # sans jeton : pas de message
    assert d["copie_base"]["bases"] == ["gazette.db"] and d["copie_base"]["le"] is None
    avec = client.get("/health", headers={"Authorization": f"Bearer {COMMUN}"}).json()
    assert all("message" in t for t in avec["taches"])
    assert all("message" not in t for t in client.get("/health", headers={"Authorization": "Bearer faux"}).json()["taches"])


def test_preparation_ratee_passe_en_erreur(client, monkeypatch):
    b = main.ETAT["base"]
    pid = b.creer_personne("Personne Exemple", "Personne", "1988-07-07")

    def rate(p):
        b.maj_livret(p, etat="a_preparer", erreur="Aucune source lisible : essai")
    monkeypatch.setattr(main, "_preparer", rate)
    main.ETAT["file"] = queue.Queue()
    main.ETAT["file"].put(pid)
    main.ETAT["file"].put(None)
    main._ouvrier()                                    # même fil : un tour puis l'arrêt
    t = {x["nom"]: x for x in maison.TACHES.etat(avec_messages=True)}["preparation"]
    assert t["etat"] == "erreur" and "Aucune source lisible" in t["message"]
    assert b.livret(pid)["erreur"] == "Aucune source lisible : essai"   # rien d'autre ne change

    monkeypatch.setattr(main, "_preparer", lambda p: b.maj_livret(p, etat="a_relire", erreur=""))
    main.ETAT["file"].put(pid)
    main.ETAT["file"].put(None)
    main._ouvrier()
    assert {x["nom"]: x for x in maison.TACHES.etat()}["preparation"]["etat"] == "ok"
