"""0.27 : envois vers carnet 3.1 (adresse commune des événements) — séjours, Gazettes, liens des numéros, photos
« scandale » (compte envoyé à carnet, alerte dans À traiter quand il n'y en a aucune), identifiants reçus de la carte
de réservation de Home Assistant, file de nouvel essai. Personnes inventées."""
import json

from app import main
from tests.test_recidive import IMMICH_CAMILLE, _carnet, ha, j, monter  # noqa: F401  (fixture)

PID_CARNET = "p-0123456789"


class FauxCarnet:
    """Appelable comme `carnet._fiche_http` : garde les envois ; `arrete` : injoignable."""

    def __init__(self):
        self.appels, self.arrete = [], False

    def __call__(self, url, jeton, methode, chemin, corps):
        if self.arrete:
            raise ConnectionError("connexion refusée")
        self.appels.append((methode, chemin, corps))
        if chemin.startswith(("/evenements/", "/compteurs/")):
            return 200, {"reconnues": 1, "a_rattacher": []}
        return 404, {"detail": "Not Found"}


def _monter(monter, **k):
    faux = FauxCarnet()
    c = monter(**k)
    main.ETAT["carnet"]._fiche = faux
    return c, faux


def _sejours(faux):
    return [(m, ch, co) for m, ch, co in faux.appels if ch.startswith("/evenements/gazette/sejour-")]


def test_027_sejour_envoye_avec_identifiants_de_ha(monter):
    c, faux = _monter(monter)
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "Chambre d'Ami", "noms": ["Camille Fabre", "Paul Essai"], "du": j(10), "jusqu_au": j(12),
           "personnes": [{"nom": "Camille Fabre", "personne_id": PID_CARNET, "immich_id": IMMICH_CAMILLE},
                         {"nom": "Paul Essai", "personne_id": "pas-un-id", "immich_id": "im-paul"}]})
    envois = _sejours(faux)
    assert len(envois) == 1
    methode, chemin, corps = envois[0]
    assert methode == "PUT" and chemin == f"/evenements/gazette/sejour-{j(10)}-chambre-d-ami"
    assert corps["type"] == "sejour" and corps["date"] == j(10) and "(2 nuits)" in corps["resume"]
    camille = next(x for x in corps["personnes"] if x["nom"] == "Camille Fabre")
    paul = next(x for x in corps["personnes"] if x["nom"] == "Paul Essai")
    assert camille["personne_id"] == PID_CARNET and camille["immich_id"] == IMMICH_CAMILLE
    assert "personne_id" not in paul and paul["immich_id"] == "im-paul"          # identifiant mal formé : écarté
    assert main.ETAT["base"].personne(pid)["carnet_personne_id"] == PID_CARNET  # la fiche garde l'identifiant
    # renvoyé à l'identique par HA : rien ne repart
    ha(c, {"chambre": "Chambre d'Ami", "noms": ["Camille Fabre", "Paul Essai"], "du": j(10), "jusqu_au": j(12),
           "personnes": [{"nom": "Camille Fabre", "personne_id": PID_CARNET, "immich_id": IMMICH_CAMILLE},
                         {"nom": "Paul Essai", "personne_id": "pas-un-id", "immich_id": "im-paul"}]})
    assert len(_sejours(faux)) == 1
    # chambre libérée avant l'arrivée : le séjour est retiré de carnet
    ha(c, {"chambre": "Chambre d'Ami", "noms": []})
    assert _sejours(faux)[-1][:2] == ("DELETE", f"/evenements/gazette/sejour-{j(10)}-chambre-d-ami")


def test_027_carnet_arrete_envoi_garde_puis_renvoye(monter):
    c, faux = _monter(monter)
    faux.arrete = True
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(6)})
    attente = c.get("/api/carnet/envois").json()["en_attente"]
    assert len(attente) == 1 and attente[0]["methode"] == "PUT" and "injoignable" not in attente[0]["erreur"]
    faux.arrete = False
    assert main.renvoyer_a_carnet() == {"faits": 1, "restes": 0}
    assert not c.get("/api/carnet/envois").json()["en_attente"]
    assert _sejours(faux)[-1][2]["personnes"][0]["immich_id"] == IMMICH_CAMILLE   # trouvé dans carnet par le nom


def test_027_lecture_seule_rien_ne_part(monter):
    c, faux = _monter(monter)
    from dataclasses import replace
    main.ETAT["cfg"] = replace(main.ETAT["cfg"], lecture_seule=True)
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(6)})
    assert not faux.appels and not main.ETAT["base"].envois_en_attente()
    assert c.post("/api/carnet/envoyer-tout").status_code == 409


def test_027_photos_scandale_comptees_envoyees_et_alerte(monter):
    c, faux = _monter(monter)
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    garde = main.compter_scandales(forcer=True)
    assert garde["personnes"][str(pid)]["n"] == 5
    envoi = next(co for m, ch, co in faux.appels if ch == "/compteurs/gazette/photos_scandale")
    assert envoi["complet"] is True and envoi["personnes"][0]["valeur"] == 5
    assert envoi["personnes"][0]["immich_id"] == IMMICH_CAMILLE
    assert c.get("/api/a-traiter").json()["sans_scandale"] == []
    # aucune photo taguée : alerte dans À traiter, qu'on peut ignorer
    main.ETAT["immich"]._lire = __import__("tests.test_recidive", fromlist=["_faux_immich"])._faux_immich({IMMICH_CAMILLE: []})
    main.compter_scandales(forcer=True)
    t = c.get("/api/a-traiter").json()
    assert [x["nom"] for x in t["sans_scandale"]] == ["Camille Fabre"] and t["total"] >= 1
    assert c.post("/api/a-traiter/ignorer", json={"sorte": "sans_scandale", "cle": str(pid)}).status_code == 200
    assert c.get("/api/a-traiter").json()["sans_scandale"] == []
    assert json.loads(main.ETAT["base"].reglage("scandales_compte"))["personnes"][str(pid)]["n"] == 0


def test_027_compte_garde_six_heures(monter):
    c, faux = _monter(monter)
    c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    main.compter_scandales(forcer=True)
    n = len(faux.appels)
    main.compter_scandales()
    assert len(faux.appels) == n


def test_027_envoyer_tout(monter):
    c, faux = _monter(monter)
    c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)})
    faux.appels.clear()
    r = c.post("/api/carnet/envoyer-tout").json()
    assert r["sejours"] == 1 and r["en_attente"] == 0
    assert any(ch.startswith("/evenements/gazette/sejour-") for m, ch, co in faux.appels)
    assert any(ch == "/compteurs/gazette/photos_scandale" for m, ch, co in faux.appels)


def test_027_remarques_eurovision_pour_l_ia():
    from app import fiche as FI
    soirees = [{"soiree": "Finale 2026", "date": "2026-05-16", "remarques": [
        {"pays": "Suède", "points": 0, "note": 2, "commentaire": "Une casserole"},
        {"pays": "Italie", "points": 12, "note": 19, "commentaire": "Sublime"},
        {"pays": "France", "points": 1, "note": 5.5, "commentaire": "Bof"}]}]
    t = FI.eurovision("Camille", soirees, "rumeurs", nombre=2)
    assert "Suède (0 point, 2/20) : « Une casserole »" in t and "France (1 point, 5.5/20)" in t and "Italie" not in t
    assert "expulsion de Camille" in t and "de 12 à 0" in t
    assert FI.eurovision("Camille", soirees, "horoscope") == "" and FI.eurovision("Camille", [], "rumeurs") == ""
