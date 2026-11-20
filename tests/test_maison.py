"""Variables communes de la maison (module app/maison.py). 0.8 : les anciens noms ne sont plus lus.
Sans réseau, jetons et adresses inventés."""
import pytest
from fastapi.testclient import TestClient

from app import config, main, maison
from app.config import Config

MDP = "mot-de-passe-de-test"
JETON_HA = "jeton-ha-de-test"
COMMUNES = ("MAISON_PASSWORD", "MAISON_JETON", "MAISON_JETON_ANCIEN", "MAISON_LECTURE_SEULE", "MAISON_ANNEAU_URL",
            "GAZETTE_PASSWORD", "GAZETTE_LECTURE_SEULE", "GAZETTE_CARNET_JETON", "GAZETTE_ADRESSE", "GAZETTE_JETON_HA",
            "GAZETTE_TITRE", "GAZETTE_SIGNATURE", "GAZETTE_LIEU", "GAZETTE_LAROUSSE", "GAZETTE_IMPRIMANTE")


@pytest.fixture(autouse=True)
def env_propre(monkeypatch):
    for nom in COMMUNES:
        monkeypatch.delenv(nom, raising=False)


def test_copie_du_module_non_retouchee():
    assert maison.CONTRAT == 3 and maison.CONTRAT_SAUVEGARDE == 1
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()


# ---------------------------------------------------------------- mot de passe

def test_mot_de_passe_commun_seul(monkeypatch):
    monkeypatch.setenv("GAZETTE_PASSWORD", "ancien-mot-de-passe")
    with pytest.raises(SystemExit, match="^MAISON_PASSWORD est absent ou trop court"):
        config.charger()                                                # l'ancien nom seul ne suffit plus
    monkeypatch.setenv("MAISON_PASSWORD", "commun-mot-de-passe")
    assert config.charger().password == "commun-mot-de-passe"


def test_mot_de_passe_absent_ou_court(monkeypatch):
    with pytest.raises(SystemExit, match="MAISON_PASSWORD est absent ou trop court"):
        config.charger()
    monkeypatch.setenv("MAISON_PASSWORD", "court")
    with pytest.raises(SystemExit):
        config.charger()


# ---------------------------------------------------------------- lecture seule (GAZETTE_LECTURE_SEULE reste)

def test_lecture_seule_maison_et_forcage(monkeypatch):
    monkeypatch.setenv("MAISON_PASSWORD", MDP)
    c = config.charger()
    assert (c.lecture_seule, c.lecture_seule_origine) == (False, "")
    monkeypatch.setenv("MAISON_LECTURE_SEULE", "oui")
    c = config.charger()
    assert (c.lecture_seule, c.lecture_seule_origine) == (True, "maison")
    monkeypatch.setenv("GAZETTE_LECTURE_SEULE", "non")                # forcée en écriture pour Gazette seule
    assert config.charger().lecture_seule is False
    monkeypatch.delenv("MAISON_LECTURE_SEULE")
    for v in ("oui", "1", "true"):
        monkeypatch.setenv("GAZETTE_LECTURE_SEULE", v)
        c = config.charger()
        assert (c.lecture_seule, c.lecture_seule_origine) == (True, "appli")


def _client(tmp_path, **cfg):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                              sources_actives=False, synchrone=True, jeton_ha=JETON_HA, **cfg)
    return TestClient(main.app)


def test_lecture_seule_affichee_avec_son_origine(tmp_path):
    with _client(tmp_path, lecture_seule=True, lecture_seule_origine="maison") as c:
        assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
        s = c.get("/api/session").json()
        assert (s["lecture_seule"], s["lecture_seule_origine"]) == (True, "maison")
        assert c.get("/api/reglages").json()["lecture_seule_origine"] == "maison"
    with _client(tmp_path, lecture_seule=True) as c:
        assert c.get("/api/session").json()["lecture_seule_origine"] == "appli"
    main.ETAT.clear()


# ---------------------------------------------------------------- jetons

def test_porte_ha_non_ouverte_par_le_jeton_commun(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test")
    with _client(tmp_path) as c:
        assert c.get("/ha/etat", headers={"Authorization": "Bearer jeton-commun-de-test"}).status_code == 401
        assert c.get("/ha/etat", headers={"Authorization": f"Bearer {JETON_HA}"}).status_code == 200
    main.ETAT.clear()


def test_jeton_envoye_a_carnet_commun_seul(monkeypatch):
    monkeypatch.setenv("MAISON_PASSWORD", MDP)
    monkeypatch.setenv("GAZETTE_CARNET_JETON", "jeton-gazette-de-test")
    assert config.charger().carnet_jeton == ""                          # l'ancien jeton par paire n'est plus lu
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test")
    assert config.charger().carnet_jeton == "jeton-commun-de-test"


# ---------------------------------------------------------------- adresse de Gazette

@pytest.mark.parametrize("brut, attendu", [
    ("", ""),
    ("http://nas.exemple:8089", "http://nas.exemple:8089"),
    ("http://nas.exemple:8089/", "http://nas.exemple:8089"),
    ("http://nas.exemple:8089/ha/sejour", "http://nas.exemple:8089"),
    ("https://gazette.exemple/ha/sejour?x=1#y", "https://gazette.exemple"),
    ("nas.exemple:8089/ha/sejour", "nas.exemple:8089"),
])
def test_racine_sans_chemin(brut, attendu):
    assert config.racine(brut) == attendu


def test_adresse_par_l_annuaire_seul(tmp_path, monkeypatch):
    monkeypatch.setenv("GAZETTE_ADRESSE", "http://repli.exemple:8089")      # ancienne variable : plus lue
    services = [{"nom": "Gazette", "locale": "http://nas.exemple:8089/", "privee": "http://gazette.exemple.ts.net"}]
    monkeypatch.setattr(main, "ANNUAIRE", maison.Annuaire(url="http://anneau", jeton="j", lire=lambda: services))
    entetes = {"Authorization": f"Bearer {JETON_HA}"}
    with _client(tmp_path) as c:
        # La tuile « Gazette » de l'Anneau, adresse locale (les liens partent vers Home Assistant)
        assert c.get("/ha/etat", headers=entetes).json()["adresse"] == "http://nas.exemple:8089"
        assert main._lien(3) == "http://nas.exemple:8089/#/livret/3"
    # L'Anneau ne connaît pas la tuile : lien relatif
    monkeypatch.setattr(main, "ANNUAIRE", maison.Annuaire(url="http://anneau", jeton="j", lire=lambda: []))
    with _client(tmp_path) as c:
        assert c.get("/ha/etat", headers=entetes).json()["adresse"] == ""
        assert main._lien(3) == "/#/livret/3"
    # L'Anneau injoignable : lien relatif aussi
    def panne():
        raise OSError("injoignable")
    monkeypatch.setattr(main, "ANNUAIRE", maison.Annuaire(url="http://anneau", jeton="j", lire=panne))
    with _client(tmp_path) as c:
        assert main._lien(3) == "/#/livret/3"
    main.ETAT.clear()


def test_adresse_de_l_annuaire_avec_chemin_corrigee(tmp_path, monkeypatch):
    services = [{"nom": "Gazette", "locale": "http://nas.exemple:8089/ha/sejour"}]
    monkeypatch.setattr(main, "ANNUAIRE", maison.Annuaire(url="http://anneau", jeton="j", lire=lambda: services))
    with _client(tmp_path) as c:
        assert main._lien(5) == "http://nas.exemple:8089/#/livret/5"
    main.ETAT.clear()
