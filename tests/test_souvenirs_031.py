"""0.31 : « Du nouveau dans les souvenirs » en page 3 de La Récidive : les nouveautés du sillage de la personne
depuis son séjour précédent, lues dans Sillage ≥ 0.26 (GET /externe/nouveautes, contrat 1). Personnes inventées."""
import dataclasses

from app import main, rendu
from app import sillage as S

from .test_recidive import IMMICH_CAMILLE, _deux_sejours, j, monter  # noqa: F401 (fixture)


def _sillage(reponse, appels):
    def lire(url, jeton, immich_id, depuis):
        appels.append((url, immich_id, depuis))
        if isinstance(reponse, Exception):
            raise reponse
        return reponse
    return lire


REPONSE = {"contrat": 1, "autres_photos": 7, "autres_etapes": 2, "etapes": [
    {"nom": "Mariage de Paul", "annee": 1987, "debut": "1987-06-15", "photos": 12, "nombre": 30, "nouvelle": False, "retrouvee": True},
    {"nom": "Vacances au lac", "annee": 2026, "debut": "2026-08-02", "photos": 9, "nombre": 9, "nouvelle": True, "retrouvee": False},
    {"nom": "", "annee": 2025, "debut": "2025-12-24", "photos": 3, "nombre": 10, "nouvelle": False, "retrouvee": False},
    {"nom": "Fête", "annee": 2026, "debut": "2026-07-14", "photos": 2, "nombre": 2, "nouvelle": True, "retrouvee": False},
    {"nom": "En trop", "annee": 2024, "debut": "2024-01-01", "photos": 1, "nombre": 5, "nouvelle": False, "retrouvee": False},
]}


def _monter_avec_sillage(monter, reponse, appels):
    def faire():
        c = monter()
        main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], sillage_url="http://sillage")
        main.ETAT["sillage"] = S.Sillage(lambda: "http://sillage", "jeton", lire_nouveautes=_sillage(reponse, appels))
        return c
    return faire


def test_la_recidive_dit_le_nouveau_des_souvenirs(monter):
    appels = []
    c = _monter_avec_sillage(monter, REPONSE, appels)()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    assert appels == [("http://sillage", IMMICH_CAMILLE, j(-38))]             # depuis la fin du séjour précédent
    s = c.get(f"/api/recidives/{rid}").json()["edition"]["souvenirs"][0]
    assert len(s["lignes"]) == S.SOUVENIRS_MAX and s["autres_photos"] == 7 + 1
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert "Du nouveau dans les souvenirs de Camille" in html
    assert "12 nouvelles pièces au dossier « Mariage de Paul, 1987 ». Ressorties des archives." in html
    assert "Nouvelle affaire : Vacances au lac, 2026 (9 photos)." in html
    assert "3 nouvelles pièces au dossier « l&#x27;année 2025 »." in html
    assert "Et 8 autres clichés versés au dossier." in html and "En trop" not in html
    # la page 3 tient, rumeurs comprises
    c.put(f"/api/recidives/{rid}", json={"rumeurs": ["Selon nos sources, Camille aurait adopté un rond-point voisin."] * 4})
    pages = rendu.mesurer(c.get(f"/api/recidives/{rid}/apercu").text)
    assert not any(p.get("deborde") for p in pages), pages


def test_sillage_muet_ou_sans_nouveaute_rien_ne_bloque(monter):
    appels = []
    c = _monter_avec_sillage(monter, RuntimeError("réseau"), appels)()
    pid, r = _deux_sejours(c)
    inv = r["invites"][0]
    assert inv["journal"] == "recidive" and inv["livret"] == "a_relire"
    rid = int(inv["lien"].rsplit("/", 1)[1])
    assert c.get(f"/api/recidives/{rid}").json()["edition"]["souvenirs"] == []
    assert "Du nouveau dans les souvenirs" not in c.get(f"/api/recidives/{rid}/apercu").text


def test_reponse_de_sillage_mal_formee():
    s = S.Sillage(lambda: "http://sillage", "jeton", lire_nouveautes=lambda *a: {"contrat": 2})
    try:
        s.nouveautes("x", "2026-01-01")
        raise AssertionError("contrat 2 accepté")
    except RuntimeError:
        pass
    assert S.Sillage(lambda: "", "jeton").nouveautes("x", "2026-01-01") == {"lignes": [], "autres_photos": 0}
