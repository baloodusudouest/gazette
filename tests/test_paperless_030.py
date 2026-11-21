"""0.30 : les numéros approuvés sont rangés dans Paperless (compte « gazette »), retrouvés par leur titre, jamais en
double. Faux Paperless du socle (formes relevées par la sonde du 21/11/2026), personnes inventées."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import journal, main, rendu
from app.config import Config
from tests.faux_paperless import FauxPaperless
from tests.test_recidive import JETON, MDP, _carnet, _deux_sejours, _faux_immich, _photos_camille, ha, j  # noqa: F401


@pytest.fixture
def faux():
    f = FauxPaperless(delai_traitement=1)
    f.compte("jeton-gazette", 3).compte("jeton-julien", 2)
    return f


@pytest.fixture
def appli(tmp_path, faux, monkeypatch):
    monkeypatch.setattr(rendu, "pdf", lambda doc, mode: (b"%PDF-1.4 " + str(hash(doc)).encode(), []))

    def faire(jeton="jeton-gazette", lecture_seule=False):
        main.ETAT.clear()
        main.SERVICES._dernier.clear()           # le registre garde le dernier essai : remis à vide
        main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                                  sources_actives=False, synchrone=True, jeton_ha=JETON, carnet_url="http://carnet",
                                  carnet_jeton="jeton", paperless_url="http://paperless:8000", paperless_jeton=jeton,
                                  lecture_seule=lecture_seule)
        main.ETAT["carnet_lire"] = _carnet("femme")
        main.ETAT["immich_lire"] = _faux_immich(_photos_camille(), True)
        main.ETAT["paperless_transport"] = faux.transport
        main.ETAT["paperless_dormir"] = lambda s: None
        c = TestClient(main.app)
        c.__enter__()
        b = main.ETAT["base"]
        journal.enregistrer(b, {**journal.charger(b), "signature": "Les hôtes de test", "chez": "à Testville"})
        assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
        return c
    yield faire
    main.ETAT.clear()


def _titres(faux):
    return sorted(d["title"] for d in faux.documents.values())


def test_recidive_approuvee_rangee(appli, faux):
    c = appli()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    rep = c.post(f"/api/recidives/{rid}/approuver").json()
    assert rep["paperless"] == "rangé dans Paperless"
    doc = next(iter(faux.documents.values()))
    assert doc["title"] == f"La Récidive n° 2 — Camille Fabre — séjour du {j(10)[8:10]}/{j(10)[5:7]}/{j(10)[:4]}"
    assert doc["owner"] == 3 and doc["created"] == j(10)
    assert {faux.tags[t]["name"] for t in doc["tags"]} == {"Camille Fabre"}
    assert faux.types[doc["document_type"]]["name"] == "Journal maison"
    assert faux.tags[doc["tags"][0]]["matching_algorithm"] == 0
    # deuxième approbation (après correction) : rien ne repart
    c.post(f"/api/recidives/{rid}/approuver")
    assert faux.envois == 1


def test_anciens_numeros_une_fois(appli, faux):
    c = appli()
    pid, r = _deux_sejours(c)
    main.ETAT["base"].maj_livret(pid, etat="approuve", approuve_le="2026-01-01")
    assert c.get("/api/paperless").json()["anciens"] == 1
    assert c.post("/api/paperless/anciens").json() == {"mis_en_file": 1}
    assert _titres(faux) == [f"Gazette — Camille Fabre — {j(-40)[8:10]}/{j(-40)[5:7]}/{j(-40)[:4]}"]
    assert c.post("/api/paperless/anciens").json() == {"mis_en_file": 0}
    assert faux.envois == 1
    etat = c.get("/api/paperless").json()
    assert etat["relie"] and etat["anciens"] == 0 and etat["elements"][0]["etat"] == "range"


def test_essai_jamais_range(appli, faux):
    c = appli()
    pid, _ = _deux_sejours(c)
    lien = c.post("/api/essais", json={"personne_id": pid, "journal": "recidive"}).json()["lien"]
    rid = int(lien.rsplit("/", 1)[1])
    assert c.post(f"/api/recidives/{rid}/approuver").json().get("paperless") is None
    assert c.post("/api/paperless/anciens").json() == {"mis_en_file": 0}
    assert faux.envois == 0


def test_renvoi_voulu_autre_titre(appli, faux):
    c = appli()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    c.post(f"/api/recidives/{rid}/approuver")
    assert c.post(f"/api/paperless/recidive-{rid}/renvoyer").json()["ok"]
    titres = _titres(faux)
    assert len(titres) == 2 and any("(renvoi du " in t for t in titres)


def test_archives_portent_l_etat(appli, faux):
    c = appli()
    pid, _ = _deux_sejours(c)
    main.ETAT["base"].maj_livret(pid, etat="approuve", approuve_le="2026-01-01")
    c.post("/api/paperless/anciens")
    a = c.get("/api/archives").json()
    assert a["paperless_relie"] and a["archives"][0]["paperless"] == "range"


def test_pas_relie_rien_ne_part(appli, faux):
    c = appli(jeton="")
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    assert c.post(f"/api/recidives/{rid}/approuver").json()["paperless"] == "Paperless pas relié"
    assert c.post("/api/paperless/anciens").status_code == 409
    fiche = next(s for s in c.get("/api/maison/services").json()["services"] if s["id"] == "paperless")
    assert fiche["etat"] == "pas_relie" and fiche["reglage"] == "GAZETTE_PAPERLESS_JETON"
    assert faux.envois == 0


def test_lecture_seule_rien_ne_part(appli, faux):
    c = appli(lecture_seule=True)
    pid, _ = _deux_sejours(c)
    main.ETAT["base"].maj_livret(pid, etat="approuve", approuve_le="2026-01-01")
    assert c.post("/api/paperless/anciens").status_code in (403, 409, 423)
    assert faux.envois == 0


def test_fiche_connexion(appli, faux):
    c = appli()
    fiche = c.post("/api/maison/services/paperless/verifier").json()
    assert fiche["etat"] == "repond" and "3.5.1" in fiche["detail"]


def test_jeton_refuse_note_sur_la_fiche(appli, faux):
    c = appli(jeton="jeton-inconnu")
    fiche = c.post("/api/maison/services/paperless/verifier").json()
    assert fiche["etat"] == "ne_repond_pas" and "401" in fiche["detail"]


def test_homonyme_dans_carnet_annee_ajoutee(appli, faux):
    c = appli()
    main.ETAT["carnet"].chercher = lambda nom: [{"nom": nom}, {"nom": nom}]
    assert main.etiquette_personne({"nom": "Camille Fabre", "naissance": "1988-07-07"}) == "Camille Fabre (1988)"
    main.ETAT["carnet"].chercher = lambda nom: [{"nom": nom}]
    assert main.etiquette_personne({"nom": "Camille Fabre", "naissance": "1988-07-07"}) == "Camille Fabre"
