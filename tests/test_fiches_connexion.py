"""Fiches « Connexion » communes (contrat 3, socle 0.11.0) : forme de /api/maison/services, accès par session ou
ANNEAU_CLE seulement (jamais MAISON_JETON), « Vérifier » d'un service pas relié n'essaie rien, copies non retouchées
du module commun et de l'interface commune."""
from pathlib import Path

from app import maison
from app.config import APPLI
from tests.test_api import JETON, client, connecter, ha  # noqa: F401 — fixture partagée
from app import main

RACINE = Path(__file__).resolve().parent.parent
CLE = "cle-anneau-de-test-1234567890"
IDS = ["wikipedia-fr", "wikipedia-en", "wikidata", "larousse", "home-assistant", "carnet", "immich", "ia-pc",
       "douze-points", "sillage"]
CHAMPS = {"id", "nom", "genre", "cible", "etat", "lit", "ecrit", "reglage", "detail", "verifie_le", "guide",
          "derniere_ecriture", "gestes"}


def test_forme_du_contrat_3(client):
    connecter(client)
    r = client.get("/api/maison/services")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    corps = r.json()
    assert corps["contrat"] == 3 and corps["appli"] == APPLI and corps["simule"] is False
    assert [s["id"] for s in corps["services"]] == IDS
    for s in corps["services"]:
        assert set(s) == CHAMPS and s["lit"] and s["ecrit"] and s["etat"] in maison.ETATS_SERVICE
        assert len(s["gestes"]) <= 1
        if s["etat"] == "pas_relie":
            assert s["reglage"]


def test_acces_session_ou_cle_anneau(client, monkeypatch):
    assert client.get("/api/maison/services").status_code == 401
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test-12345")
    entete = {"Authorization": "Bearer jeton-commun-de-test-12345"}
    assert client.get("/api/maison/services", headers=entete).status_code == 401
    monkeypatch.setenv("ANNEAU_CLE", CLE)
    assert client.get("/api/maison/services", headers={"Authorization": f"Bearer {CLE}"}).status_code == 200
    assert client.get("/api/maison/services", headers={"Authorization": "Bearer mauvaise"}).status_code == 401


def test_verifier_inconnu_et_pas_relie(client):
    connecter(client)
    assert client.post("/api/maison/services/inconnu/verifier").status_code == 404
    for s in client.get("/api/maison/services").json()["services"]:
        if s["etat"] == "pas_relie":
            apres = client.post(f"/api/maison/services/{s['id']}/verifier").json()
            assert apres["etat"] == "pas_relie" and apres["verifie_le"] is None


def test_copies_communes_non_retouchees():
    assert maison.CONTRAT == 3 and maison.VERSION_SOCLE == "0.11.1"
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()
    for nom in maison.FICHIERS_INTERFACE:
        ecrite, calculee = maison.empreinte_interface(RACINE / "frontend" / "src" / "lib" / "services" / nom)
        assert ecrite and ecrite == calculee, nom


# ---------------------------------------------------------------- propre à Gazette (0.29)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _registre_vierge():
    """Le registre vit au niveau du module : chaque test repart sans dernier essai."""
    main.SERVICES._dernier.clear()
    yield
    main.SERVICES._dernier.clear()


def _fiche(c, sid):
    return next(s for s in c.get("/api/maison/services").json()["services"] if s["id"] == sid)


def test_etats_de_depart_et_reglages(client):
    connecter(client)
    etats = {s["id"]: (s["etat"], s["reglage"], s["genre"], s["cible"]) for s in client.get("/api/maison/services").json()["services"]}
    assert etats["wikipedia-fr"][0] == "relie" and etats["larousse"][0] == "relie"
    assert etats["home-assistant"][0] == "relie"                      # jeton HA des tests
    assert etats["ia-pc"] == ("pas_relie", "GAZETTE_OLLAMA_URL", "exterieur", None)
    assert etats["immich"] == ("pas_relie", "GAZETTE_IMMICH_URL et GAZETTE_IMMICH_CLE", "exterieur", None)
    assert etats["carnet"] == ("pas_relie", "GAZETTE_CARNET_URL et MAISON_JETON", "maison", "carnet")
    assert etats["douze-points"][2:] == ("maison", "douze-points")
    # Larousse coupé dans Réglages : pas relié, sans essai
    client.put("/api/reglages", json={**client.get("/api/reglages").json()["journal"], "larousse": False})
    assert _fiche(client, "larousse")["etat"] == "pas_relie"


def test_sources_web_lecture_coupee_et_pages_gardees(client):
    """Les tests ne lisent pas le réseau : « Vérifier » dit « lecture coupée » ; le guide garde « N pages gardées »."""
    connecter(client)
    f = client.post("/api/maison/services/wikipedia-fr/verifier").json()
    assert f["etat"] == "ne_repond_pas" and f["detail"] == "lecture coupée" and f["verifie_le"]
    reglages = {r["nom"]: r["valeur"] for r in f["guide"]["reglages"]}
    assert reglages["Pages gardées"].startswith("5 ")                  # pages de test du client
    assert {r["nom"]: r["valeur"] for r in _fiche(client, "larousse")["guide"]["reglages"]}["Pages gardées"].startswith("2 ")


def test_home_assistant_dernier_appel(client):
    connecter(client)
    f = client.post("/api/maison/services/home-assistant/verifier").json()
    assert f["etat"] == "ne_repond_pas" and "rien reçu" in f["detail"]
    main.SERVICES._dernier.clear()
    assert ha(client, {"chambre": "Bleue", "noms": []}).status_code == 200
    f = _fiche(client, "home-assistant")                               # noté par la route, sans « Vérifier »
    assert f["etat"] == "repond" and f["detail"].startswith("Dernier séjour reçu le ")
    reglages = {r["nom"]: r["valeur"] for r in f["guide"]["reglages"]}
    assert reglages["Porte /ha/sejour"].startswith("ouverte") and reglages["Dernier appel"] == "Bleue : libre"


def test_ia_du_pc_guide_complet(client, monkeypatch):
    """Le guide d'ollama.guide passe tel quel (réglages, allumer, pannes, une seule fois), avec le second modèle et la
    dernière erreur ; « Vérifier » ne lit que la liste des modèles."""
    connecter(client)
    appels = []

    def lire(chemin, corps):
        appels.append(chemin)
        return {"models": [{"name": "mistral-nemo:latest"}]}
    main.ETAT["ollama"] = main.Ollama("http://pc-de-test:11434", lire=lire)
    main.ETAT["ollama"].erreur = "délai dépassé"
    f = _fiche(client, "ia-pc")
    g = f["guide"]
    assert f["etat"] == "relie" and g["allumer"] and g["pannes"] and g["une_fois"] and g["terminal"] and g["note"]
    noms = [r["nom"] for r in g["reglages"]]
    assert noms[0] == "Dernière erreur" and "Second modèle" in noms and "Adresse appelée" in noms
    f = client.post("/api/maison/services/ia-pc/verifier").json()
    assert f["etat"] == "repond" and f["detail"].startswith("PC prêt") and appels == ["/api/tags"]


def test_douze_points_et_carnet_pas_relies_n_appellent_rien(client):
    connecter(client)
    for sid in ("carnet", "douze-points", "immich", "sillage"):
        f = client.post(f"/api/maison/services/{sid}/verifier").json()
        assert f["etat"] == "pas_relie" and f["verifie_le"] is None


def test_rendu_pdf_dans_reglages(client):
    connecter(client)
    assert "polices" in client.get("/api/reglages").json()["rendu"]
