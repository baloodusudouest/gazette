"""API : garde, fiches et livrets, relecture, À traiter, porte de Home Assistant. Personnes inventées."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import journal, main
from app.config import Config
from tests import fixtures as F

MDP = "mot-de-passe-de-test"
JETON = "jeton-ha-de-test"


@pytest.fixture()
def client(tmp_path):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True, jeton_ha=JETON)
    with TestClient(main.app) as c:
        b = main.ETAT["base"]
        journal.enregistrer(b, {**journal.charger(b), "titre": "Le Journal de Test", "signature": "Les hôtes de test",
                                "lieu": "Testville"})
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


def test_mesure_de_la_place(client):
    """Les blocs portent leur clé (data-bloc) ; la mesure rend la place manquante page par page (503 sans Chromium)."""
    connecter(client)
    pid = client.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    lv = client.get(f"/api/livrets/{pid}").json()["livret"]
    c = lv["contenu"]
    c["p2"]["items"][0]["texte"] = "Le Testland signe un accord qui couvre l'agriculture, la pêche et les transports. " * 30
    client.put(f"/api/livrets/{pid}", json={"contenu": c, "mot": lv["mot_defaut"]})
    html = client.get(f"/api/livrets/{pid}/apercu").text
    for cle in ('data-bloc="une"', 'data-bloc="p2:0"', 'data-bloc="breve:0"', 'data-bloc="chrono:0"', 'data-bloc="mot"'):
        assert cle in html
    r = client.get(f"/api/livrets/{pid}/mesure")
    if r.status_code == 503:
        pytest.skip("Chromium absent")
    pages = {p["page"]: p for p in r.json()["pages"]}
    assert pages[2]["deborde"] and pages[2]["exces"] > 0 and not pages[4]["deborde"]
    assert any(b["bloc"] == "p2:0" and b["h"] > 300 for b in pages[2]["blocs"])
    detail = client.post(f"/api/livrets/{pid}/approuver").json()["detail"]
    assert "page 2" in detail and "rouge" in detail and "vert" in detail


CARNET = [
    {"carnet_id": "c1", "nom": "Dominique INCONNU", "nom_carnet": "Dominique Inconnu", "prenom": "Dominique",
     "naissance": "1988-07-07", "jour": 7, "mois": 7, "annee": 1988},
    {"carnet_id": "c2", "nom": "Sacha Sansannee", "nom_carnet": "Sacha Sansannee", "prenom": "Sacha",
     "naissance": None, "jour": 3, "mois": 5, "annee": None},
    {"carnet_id": "c3", "nom": "Camille Fabre", "nom_carnet": "Camille Fabre", "prenom": "Camille",
     "naissance": "1988-07-08", "jour": 8, "mois": 7, "annee": 1988},
]


@pytest.fixture()
def client_carnet(tmp_path):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True, jeton_ha=JETON, carnet_url="http://carnet.test",
                              carnet_jeton="jeton-carnet")
    appels = []
    main.ETAT["carnet_lire"] = lambda url, jeton: (appels.append((url, jeton)), CARNET)[1]
    with TestClient(main.app) as c:
        b = main.ETAT["base"]
        for cle, contenu in {"wp:fr:Juillet 1988": F.MOIS_PUCES, "wp:fr:Juin 1988": "", "wp:fr:1988 en France": F.ANNEE_FRANCE,
                             "wp:fr:1988": F.ANNEE_MONDE, "wp:fr:7 juillet": F.JOUR, "lar:1988-07": F.LAROUSSE,
                             "lar:1988-06": ""}.items():
            b.garder_source(cle, contenu)
        c.appels = appels
        yield c
    main.ETAT.clear()


def test_carnet_fiche_auto_saisie_et_dates(client_carnet):
    c = client_carnet
    connecter(c)
    du = date.today() + timedelta(days=5)
    # HA annonce un invité sans fiche que carnet connaît (date complète) : fiche créée, livret préparé
    r = ha(c, {"chambre": "ami", "noms": ["DOMINIQUE INCONNU", "Sacha Sansannee"], "du": du.isoformat(),
               "jusqu_au": (du + timedelta(days=1)).isoformat()}).json()
    assert r["depuis_carnet"] == ["DOMINIQUE INCONNU"] and r["manquants"] == ["Sacha Sansannee"]
    assert r["a_relire"] == ["DOMINIQUE INCONNU"]
    dom = next(p for p in c.get("/api/livrets").json()["livrets"] if p["nom"] == "Dominique Inconnu")
    assert dom["naissance"] == "1988-07-07"
    assert c.appels and c.appels[0] == ("http://carnet.test", "jeton-carnet")
    # Sans année dans carnet : pas de fiche, mais À traiter dit ce que carnet sait
    t = c.get("/api/a-traiter").json()
    sacha = t["fiches"][0]
    assert sacha["nom"] == "Sacha Sansannee" and sacha["carnet"]["jour"] == 3 and sacha["carnet"]["annee"] is None
    assert c.post("/api/a-traiter/creer-depuis-carnet", json={"nom": "Sacha Sansannee"}).status_code == 409
    # Saisie assistée
    s = c.get("/api/carnet/suggestions", params={"q": "cami"}).json()["suggestions"]
    assert s[0]["nom"] == "Camille Fabre" and s[0]["naissance"] == "1988-07-08"
    # Date différente de carnet : à traiter, puis ignorée
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    d = c.get("/api/a-traiter").json()["dates"]
    assert d == [{"id": pid, "nom": "Camille Fabre", "gazette": "1988-07-07", "carnet": "1988-07-08", "cle": f"{pid}:1988-07-08"}]
    c.post("/api/a-traiter/ignorer", json={"sorte": "date", "cle": d[0]["cle"]})
    assert c.get("/api/a-traiter").json()["dates"] == []
    # Connexion : la tuile carnet
    v = c.post("/api/connexion/verifier").json()["carnet"]
    assert v["ok"] and "3 contacts, 2 avec date complète" in v["detail"]
    assert c.get("/api/connexion/etat").json()["carnet"]["personnes"] == 3


def test_carnet_en_panne(client_carnet):
    def panne(url, jeton):
        raise RuntimeError("carnet injoignable")
    main.ETAT["carnet"]._lire = panne
    main.ETAT["carnet"]._liste = None
    r = ha(client_carnet, {"chambre": "ami", "noms": ["Dominique Inconnu"], "du": date.today().isoformat(),
                           "jusqu_au": date.today().isoformat()}).json()
    assert r["manquants"] == ["Dominique Inconnu"] and r["depuis_carnet"] == []
    assert main.ETAT["carnet"].etat()["erreur"] == "carnet injoignable"


def test_suppression_d_une_fiche_garde_une_copie(client, tmp_path):
    """0.20.6 (audit du 17/11/2026) : copie de la base avant de supprimer une fiche."""
    connecter(client)
    pid = client.post("/api/personnes", json={"nom": "Personne Inventée", "naissance": "1988-07-07"}).json()["id"]
    assert client.request("DELETE", f"/api/personnes/{pid}", json={"confirmation": True}).status_code == 200
    copies = list((tmp_path / "sauvegardes").glob(f"gazette-*-avant-suppression-{pid}.db"))
    assert len(copies) == 1 and copies[0].stat().st_size > 0


def test_suppression_d_une_fiche_exige_la_confirmation(client):
    """0.20.9 (audit du 17/11/2026, M17) : sans {"confirmation": true}, la fiche reste."""
    connecter(client)
    pid = client.post("/api/personnes", json={"nom": "Personne Inventée", "naissance": "1988-07-07"}).json()["id"]
    assert client.delete(f"/api/personnes/{pid}").status_code == 400
    for corps in ({}, {"confirmation": False}, {"confirmation": "oui"}, [True]):
        assert client.request("DELETE", f"/api/personnes/{pid}", json=corps).status_code in (400, 422), corps
    assert client.get(f"/api/livrets/{pid}").status_code == 200
