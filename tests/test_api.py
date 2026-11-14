"""API : garde, fiches et livrets, relecture, À traiter, porte de Home Assistant. Personnes inventées."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Config
from tests import fixtures as F

MDP = "mot-de-passe-de-test"
JETON = "jeton-ha-de-test"


@pytest.fixture()
def client(tmp_path):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True, jeton_ha=JETON, titre="Le Journal de Test",
                              signature="Les hôtes de test", lieu="Testville")
    with TestClient(main.app) as c:
        b = main.ETAT["base"]
        for cle, contenu in {"wp:fr:Juillet 1988": F.MOIS_PUCES, "wp:fr:Juin 1988": "", "wp:fr:1988 en France": F.ANNEE_FRANCE,
                             "wp:fr:1988": F.ANNEE_MONDE, "wp:fr:7 juillet": F.JOUR, "lar:1988-07": F.LAROUSSE,
                             "lar:1988-06": ""}.items():
            b.garder_source(cle, contenu)
        yield c
    main.ETAT.clear()


def connecter(c):
    assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200


def ha(c, corps):
    return c.post("/ha/sejour", json=corps, headers={"Authorization": f"Bearer {JETON}"})


def test_garde(client):
    assert client.get("/health").json()["ok"] is True
    assert client.get("/api/livrets").status_code == 401
    assert client.post("/api/connexion", json={"mot_de_passe": "faux"}).status_code == 401
    assert client.post("/ha/sejour", json={}).status_code == 401
    assert client.post("/ha/sejour", json={}, headers={"Authorization": "Bearer faux"}).status_code == 401
    # Le jeton de HA n'ouvre pas l'API
    assert client.get("/api/livrets", headers={"Authorization": f"Bearer {JETON}"}).status_code == 401


def test_porte_ha_fermee_sans_jeton(tmp_path):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "s", attente_connexion=False,
                              sources_actives=False, synchrone=True)
    with TestClient(main.app) as c:
        assert c.post("/ha/sejour", json={"chambre": "a"}, headers={"Authorization": "Bearer "}).status_code == 401
    main.ETAT.clear()


def test_fiche_et_livret(client):
    connecter(client)
    r = client.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    pid = r.json()["id"]
    l = client.get(f"/api/livrets/{pid}").json()
    assert l["personne"]["prenom"] == "Camille"
    assert l["livret"]["etat"] == "a_relire" and l["livret"]["contenu"]["une"]["titre"]
    # Relecture : changer la une par une autre proposition, modifier le mot
    autre = next(f for f in l["livret"]["propositions"]["evenements"] if f["id"] != l["livret"]["contenu"]["une"]["id"])
    r = client.post(f"/api/livrets/{pid}/choisir", json={"bloc": "une", "proposition": autre["id"]})
    assert r.json()["contenu"]["une"]["id"] == autre["id"]
    assert client.put(f"/api/livrets/{pid}", json={"mot": "Bienvenue chez nous.", "contenu": {"musique": "Une chanson"}}).status_code == 200
    html = client.get(f"/api/livrets/{pid}/apercu").text
    assert "Le Journal de Test" in html and "Camille Fabre" in html and "Bienvenue chez nous." in html
    assert "Une chanson" in html and "Les hôtes de test" in html and "Testville" in html
    assert "Wikipédia (CC BY-SA 4.0)" in html and "Larousse" in html
    # Approuver (sans Chromium dans les tests : pas de contrôle de débordement)
    assert client.post(f"/api/livrets/{pid}/approuver").status_code == 200
    assert client.get(f"/api/livrets/{pid}").json()["livret"]["etat"] == "approuve"
    # Une modification après approbation : à relire de nouveau
    assert client.put(f"/api/livrets/{pid}", json={"mot": "Autre mot."}).json()["etat"] == "a_relire"


def test_modifier_date_refait_le_livret(client):
    connecter(client)
    pid = client.post("/api/personnes", json={"nom": "Lou Martin", "naissance": "1988-07-07"}).json()["id"]
    client.put(f"/api/personnes/{pid}", json={"naissance": "1950-03-03"})
    lv = client.get(f"/api/livrets/{pid}").json()["livret"]
    assert lv["etat"] == "a_preparer" and lv["erreur"]          # aucune source pour 1950 dans les tests


def test_refus(client):
    connecter(client)
    assert client.post("/api/personnes", json={"nom": "", "naissance": "1988-07-07"}).status_code == 422
    assert client.post("/api/personnes", json={"nom": "X", "naissance": "demain"}).status_code == 422
    assert client.post("/api/personnes", json={"nom": "X", "naissance": (date.today() + timedelta(days=2)).isoformat()}).status_code == 422


def test_porte_ha_et_a_traiter(client):
    connecter(client)
    du = date.today() + timedelta(days=10)
    fin = du + timedelta(days=2)
    # Anniversaire 3 jours après le départ → « en avance »
    anniv = fin + timedelta(days=3)
    naissance = anniv.replace(year=1988).isoformat() if not (anniv.month == 2 and anniv.day == 29) else "1988-02-28"
    pid = client.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": naissance, "alias": ["Cam"]}).json()["id"]
    r = ha(client, {"chambre": "ami", "noms": ["Camille FABRE", "Dominique Inconnu"], "du": du.isoformat(), "jusqu_au": fin.isoformat()})
    assert r.status_code == 200
    j = r.json()
    assert j["manquants"] == ["Dominique Inconnu"]
    cam = next(i for i in j["invites"] if i["fiche"])
    assert cam["anniversaire"]["cas"] == "en_avance" and cam["lien"].endswith(f"/#/livret/{pid}")
    t = client.get("/api/a-traiter").json()
    assert [f["nom"] for f in t["fiches"]] == ["Dominique Inconnu"]
    assert t["anniversaires"][0]["phrases"][0].startswith("Et puisque votre anniversaire arrive dans 3 jours")
    etat = client.get("/ha/etat", headers={"Authorization": f"Bearer {JETON}"}).json()
    assert etat["fiches_manquantes"] == 1 and etat["anniversaires"] == 1
    # Créer la fiche manquante relie l'invité au séjour
    client.post("/api/personnes", json={"nom": "Dominique Inconnu", "naissance": "1970-01-15"})
    assert client.get("/api/a-traiter").json()["fiches"] == []
    # Ajouter la phrase au mot ferme la tuile
    a = client.get("/api/a-traiter").json()["anniversaires"][0]
    client.post(f"/api/livrets/{pid}/mot/ajouter", json={"phrase": a["phrases"][2], "cle": a["cle"]})
    assert client.get("/api/a-traiter").json()["anniversaires"] == []
    assert a["phrases"][2] in client.get(f"/api/livrets/{pid}").json()["livret"]["mot"]
    # Le même invité revient : le livret est retrouvé, pas recréé
    r = ha(client, {"chambre": "ado", "noms": ["Cam"], "du": (du + timedelta(days=60)).isoformat(),
                    "jusqu_au": (du + timedelta(days=61)).isoformat()})
    assert r.json()["invites"][0]["lien"].endswith(f"/#/livret/{pid}")
    assert len(client.get("/api/livrets").json()["livrets"]) == 2
    # Chambre libérée
    ha(client, {"chambre": "ami", "noms": []})
    assert all(s["chambre"] != "ami" for s in client.get("/api/livrets").json()["sejours"])


def test_ha_dates_impossibles(client):
    r = ha(client, {"chambre": "ami", "noms": ["A"], "du": "2020-01-01", "jusqu_au": "2019-01-01"})
    assert r.status_code == 422


def test_reglages_du_journal(client):
    connecter(client)
    r = client.get("/api/reglages").json()
    assert r["journal"]["titre"] == "Le Journal de Test" and "mot_modele" in r["champs"]
    assert client.put("/api/reglages/journal", json={"accent": "rouge"}).status_code == 422
    assert client.put("/api/reglages/journal", json={"titre": ""}).status_code == 422
    j = client.put("/api/reglages/journal", json={
        "titre": "La Gazette des Essais", "lieu": "Les Essais", "lieu_detail": "Testville · Testland",
        "chez": "aux Essais", "signature": "Alex et Sam", "accent": "#123456", "larousse": False,
        "mot_modele": "Le {date}, {prenom}, on vous attend {chez}."}).json()
    assert j["larousse"] is False and main.ETAT["sources"].larousse_actif is False
    pid = client.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    html = client.get(f"/api/livrets/{pid}/apercu").text
    for t in ("La Gazette des Essais", "Testville · Testland", "Imprimé aux Essais", "Alex et Sam", "#123456",
              "Le 7 juillet 1988, Camille, on vous attend aux Essais."):
        assert t in html
    assert client.get("/api/livrets").status_code == 200
