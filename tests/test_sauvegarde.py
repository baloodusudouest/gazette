"""0.8 : réglages dans l'appli (reprise unique des anciennes variables), sauvegarde pour l'Anneau et restauration.
Sans réseau : l'Anneau est simulé par ETAT["anneau_lire"] (argument lire= de maison.lire_sauvegarde)."""
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app import journal, main, maison
from app.config import Config

MDP = "mot-de-passe-de-test"
JETON_HA = "jeton-ha-de-test"
COMMUN = "jeton-commun-de-test"
VARIABLES = ("MAISON_JETON", "MAISON_JETON_ANCIEN", "MAISON_ANNEAU_URL", "MAISON_PASSWORD", "MAISON_LECTURE_SEULE", "GAZETTE_CARNET_JETON",
             "GAZETTE_TITRE", "GAZETTE_SIGNATURE", "GAZETTE_LIEU", "GAZETTE_LAROUSSE")


@pytest.fixture(autouse=True)
def env_propre(monkeypatch):
    for nom in VARIABLES:
        monkeypatch.delenv(nom, raising=False)
    yield
    main.ETAT.clear()


def demarrer(tmp_path, anneau=None, **cfg):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True, jeton_ha=JETON_HA, **cfg)
    if anneau is not None:
        main.ETAT["anneau_lire"] = anneau
    return TestClient(main.app)


def connecter(c):
    assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200


def historique(c) -> str:
    return " | ".join(h["detail"] for h in c.get("/api/reglages").json()["historique"])


# ---------------------------------------------------------------- reprise au premier démarrage

def test_reprise_des_anciennes_variables_une_seule_fois(tmp_path, monkeypatch):
    monkeypatch.setenv("GAZETTE_TITRE", "Le Courrier des Essais")
    monkeypatch.setenv("GAZETTE_LAROUSSE", "non")
    with demarrer(tmp_path) as c:
        connecter(c)
        r = c.get("/api/reglages").json()["reglages"]
        assert r["titre"] == "Le Courrier des Essais" and r["larousse"] is False
        assert r["lieu"] == journal.DEFAUTS["lieu"]                     # variable absente : valeur par défaut
        assert main.ETAT["sources"].larousse_actif is False
        h = historique(c)
        assert "repris de GAZETTE_TITRE" in h and "repris de GAZETTE_LAROUSSE" in h and "GAZETTE_LIEU" not in h
    # Second démarrage : la variable a changé (ou a disparu de la stack), elle n'est plus lue
    monkeypatch.setenv("GAZETTE_TITRE", "Un autre titre")
    monkeypatch.setenv("GAZETTE_LIEU", "Un autre lieu")
    with demarrer(tmp_path) as c:
        connecter(c)
        r = c.get("/api/reglages").json()["reglages"]
        assert r["titre"] == "Le Courrier des Essais" and r["lieu"] == journal.DEFAUTS["lieu"]
        assert "Un autre" not in historique(c)


def test_reglages_deja_gardes_jamais_ecrases(tmp_path, monkeypatch):
    with demarrer(tmp_path) as c:
        connecter(c)
        assert c.put("/api/reglages", json={"titre": "Réglé dans l'appli"}).status_code == 200
    monkeypatch.setenv("GAZETTE_TITRE", "Venu de la stack")
    with demarrer(tmp_path) as c:
        connecter(c)
        assert c.get("/api/reglages").json()["reglages"]["titre"] == "Réglé dans l'appli"


# ---------------------------------------------------------------- écran Réglages

def test_put_reglages_et_mauvais_types(tmp_path):
    with demarrer(tmp_path) as c:
        assert c.put("/api/reglages", json={"titre": "x"}).status_code == 401     # session exigée
        connecter(c)
        r = c.put("/api/reglages", json={"titre": "La Gazette des Essais", "larousse": False, "accent": "#123456"})
        assert r.status_code == 200 and r.json()["titre"] == "La Gazette des Essais" and r.json()["larousse"] is False
        assert c.get("/api/reglages").json()["reglages"]["accent"] == "#123456"
        for corps, mot in (({"larousse": "non"}, "Larousse"), ({"titre": 12}, "Titre du journal"),
                           ({"signature": ["a"]}, "Signature"), ({"accent": "rouge"}, "#RRGGBB"),
                           ({"titre": ""}, "à remplir"), ([1, 2], "objet")):
            r = c.put("/api/reglages", json=corps)
            assert r.status_code == 400 and mot in r.json()["detail"], (corps, r.json())
        assert c.get("/api/reglages").json()["reglages"]["titre"] == "La Gazette des Essais"   # rien n'a changé


# ---------------------------------------------------------------- GET /externe/sauvegarde

def test_sauvegarde_porte_fermee_sans_jeton_commun(tmp_path, monkeypatch):
    monkeypatch.setenv("GAZETTE_CARNET_JETON", "ancien-jeton-par-paire")
    with demarrer(tmp_path) as c:
        assert c.get("/externe/sauvegarde").status_code == 404
        assert c.get("/externe/sauvegarde", headers={"Authorization": "Bearer ancien-jeton-par-paire"}).status_code == 404


def test_sauvegarde_ouverte_par_le_jeton_commun_seul(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", COMMUN)
    monkeypatch.setenv("GAZETTE_CARNET_JETON", "ancien-jeton-par-paire")
    with demarrer(tmp_path) as c:
        assert c.get("/externe/sauvegarde").status_code == 401
        for faux in ("ancien-jeton-par-paire", JETON_HA, MDP):              # ni l'ancien jeton, ni HA, ni le mot de passe
            assert c.get("/externe/sauvegarde", headers={"Authorization": f"Bearer {faux}"}).status_code == 401
        # La session ne l'ouvre pas non plus
        connecter(c)
        assert c.get("/externe/sauvegarde").status_code == 401
        c.put("/api/reglages", json={"titre": "Le Courrier des Essais", "larousse": False})
        r = c.get("/externe/sauvegarde", headers={"Authorization": f"Bearer {COMMUN}"})
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        s = r.json()
        assert s["contrat"] == 1 and s["appli"] == "gazette" and s["version"] == main.__version__
        assert s["reglages"]["titre"] == "Le Courrier des Essais" and s["reglages"]["larousse"] is False
        assert set(s["reglages"]) == set(journal.DEFAUTS)                     # tous les réglages du journal, rien d'autre
        assert not any(maison.est_secret(k) for k in s["reglages"])
        assert not set(map(maison.cle, journal.EXCLUS)) & set(map(maison.cle, s["reglages"]))
        texte = r.text
        for secret in (COMMUN, JETON_HA, MDP, "ancien-jeton-par-paire", str(tmp_path), "MAISON_", "GAZETTE_"):
            assert secret not in texte
        # X-Maison-Jeton est accepté aussi (même porte)
        assert c.get("/externe/sauvegarde", headers={"X-Maison-Jeton": COMMUN}).status_code == 200


def test_porte_ha_toujours_fermee_au_jeton_commun(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", COMMUN)
    with demarrer(tmp_path) as c:
        assert c.get("/ha/etat", headers={"Authorization": f"Bearer {COMMUN}"}).status_code == 401
        assert c.post("/ha/sejour", json={"chambre": "a"}, headers={"Authorization": f"Bearer {COMMUN}"}).status_code == 401


# ---------------------------------------------------------------- restaurer

SAUVES = {"titre": "La Gazette d'avant", "lieu": journal.DEFAUTS["lieu"], "accent": "#1B4E9E", "larousse": False,
          "jeton": "ne-doit-jamais-entrer", "cle_inconnue": "ignorée"}


def anneau(appels):
    def lire(adresse, jeton):
        appels.append((adresse, jeton))
        if "?le=2026-11-15" in adresse:
            return {"le": "2026-11-15", "version": "0.8.0", "reglages": SAUVES}
        if "?le=" in adresse:
            raise urllib.error.HTTPError(adresse, 404, "Not Found", {}, None)
        return {"dates": ["2026-11-15", "2026-11-14"]}
    return lire


def test_restaurer_dates_differences_application(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", COMMUN)
    appels = []
    with demarrer(tmp_path, anneau=anneau(appels)) as c:
        assert c.get("/api/restaurer").status_code == 401
        connecter(c)
        assert c.get("/api/restaurer").json() == {"dates": ["2026-11-15", "2026-11-14"]}
        assert appels[-1] == ("http://anneau:8094/externe/sauvegardes/gazette", COMMUN)
        v = c.get("/api/restaurer", params={"le": "2026-11-15"}).json()
        assert v["le"] == "2026-11-15" and v["version"] == "0.8.0"
        assert v["differences"] == [
            {"cle": "accent", "actuel": "#9E1B1B", "sauve": "#1B4E9E"},
            {"cle": "larousse", "actuel": True, "sauve": False},
            {"cle": "titre", "actuel": "La Gazette", "sauve": "La Gazette d'avant"},
        ]                                                                    # ni le jeton, ni la clé inconnue, ni ce qui est égal
        assert c.get("/api/restaurer", params={"le": "15/11/2026"}).status_code == 400
        r = c.get("/api/restaurer", params={"le": "2026-11-01"})
        assert r.status_code == 404 and "2026-11-01" in r.json()["detail"]
        r = c.post("/api/restaurer", json={"le": "2026-11-15"})
        assert r.status_code == 200 and sorted(r.json()["restaures"]) == ["accent", "larousse", "titre"]
        reg = c.get("/api/reglages").json()
        assert reg["reglages"]["titre"] == "La Gazette d'avant" and reg["reglages"]["larousse"] is False
        assert "jeton" not in reg["reglages"] and main.ETAT["sources"].larousse_actif is False
        assert "restaurés depuis la sauvegarde du 2026-11-15" in historique(c)
        # Une seconde fois : rien à restaurer
        assert c.post("/api/restaurer", json={"le": "2026-11-15"}).json()["restaures"] == []


def test_restaurer_permis_en_lecture_seule(tmp_path):
    with demarrer(tmp_path, anneau=anneau([]), lecture_seule=True, lecture_seule_origine="maison") as c:
        connecter(c)
        assert c.post("/api/restaurer", json={"le": "2026-11-15"}).status_code == 200
        assert c.get("/api/reglages").json()["reglages"]["titre"] == "La Gazette d'avant"


def test_restaurer_anneau_injoignable_ou_vide(tmp_path):
    def panne(adresse, jeton):
        raise OSError("injoignable")
    with demarrer(tmp_path, anneau=panne) as c:
        connecter(c)
        for r in (c.get("/api/restaurer"), c.get("/api/restaurer", params={"le": "2026-11-15"}),
                  c.post("/api/restaurer", json={"le": "2026-11-15"})):
            assert r.status_code == 503 and "Anneau injoignable" in r.json()["detail"]
    with demarrer(tmp_path, anneau=lambda adresse, jeton: {"dates": []}) as c:
        connecter(c)
        r = c.get("/api/restaurer")
        assert r.status_code == 404 and "aucune sauvegarde" in r.json()["detail"]


def test_restaurer_sauvegarde_invalide_refusee(tmp_path):
    lire = lambda adresse, jeton: {"le": "2026-11-15", "version": "0.8.0", "reglages": {"accent": "bleu"}}  # noqa: E731
    with demarrer(tmp_path, anneau=lire) as c:
        connecter(c)
        r = c.post("/api/restaurer", json={"le": "2026-11-15"})
        assert r.status_code == 422 and "#RRGGBB" in r.json()["detail"]
        assert c.get("/api/reglages").json()["reglages"]["accent"] == journal.DEFAUTS["accent"]
