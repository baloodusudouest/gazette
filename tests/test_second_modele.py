"""0.22 : régénérer avec un second modèle (choix de Julien du 18/11/2026 : on génère avec le modèle habituel,
GAZETTE_OLLAMA_MODELE, on régénère avec le réglage « modele_second »). Données inventées."""
import pytest

from app import journal, main
from app import ollama as O
from tests.test_recidive import _deux_sejours, monter  # noqa: F401

LIGNES = "1. Camille et le gâteau du siècle\n2. Scandale au salon de thé\n3. Les aveux du dimanche matin"
LETTRES = ("Lettre : Mon chat réclame encore ses imitations de mouette. Que faire ?\nSignature : Un voisin inquiet\n"
           "Réponse : Prolongez le séjour.\n\nLettre : Le canapé se languit depuis son départ.\nSignature : Le salon\n"
           "Réponse : Nous transmettons.")


def _faux():
    """Faux Ollama : note le modèle de chaque demande ; répond selon la rubrique demandée."""
    modeles = []

    def lire(chemin, corps):
        if chemin == "/api/tags":
            return {"models": [{"name": O.MODELE}, {"name": "qwen2.5:14b"}]}
        modeles.append(corps["model"])
        return {"response": LETTRES if "Courrier des lecteurs" in corps["prompt"] else LIGNES}
    lire.modeles = modeles
    return lire


def _pret(c):
    """Une fiche avec Gazette (photo choisie) et Récidive ; rend (pid, rid, id d'une photo de la Récidive)."""
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    c.post(f"/api/livrets/{pid}/preparer", json={})
    lv = c.get(f"/api/livrets/{pid}").json()["livret"]
    if lv.get("photos_choix"):
        c.put(f"/api/livrets/{pid}", json={"photo": {"id": lv["photos_choix"][0]["id"]}})
    photo = c.get(f"/api/recidives/{rid}").json()["edition"]["photos"][1]["id"]
    return pid, rid, photo


def _routes(pid, rid, photo):
    return [
        (f"/api/livrets/{pid}/photo/proposer", {"description": "Camille à la plage, chapeau de paille"}),
        (f"/api/livrets/{pid}/ia", {"action": "titres", "texte": "Le maire a inauguré le pont du village."}),
        (f"/api/recidives/{rid}/proposer", {"cible": photo, "description": "Camille devant un gâteau renversé"}),
        (f"/api/recidives/{rid}/rumeurs", {"indices": "aime les gâteaux"}),
        (f"/api/recidives/{rid}/courrier", {}),
        (f"/api/recidives/{rid}/horoscope", {}),
        (f"/api/recidives/{rid}/mot", {"texte": ""}),
    ]


def test_reglage_par_defaut_et_sauvegarde(monter):
    c = monter()
    r = c.get("/api/reglages").json()
    assert r["reglages"]["modele_second"] == "qwen2.5:14b" and "modele_second" in r["champs"]
    assert c.put("/api/reglages", json={"modele_second": "qwen 2.5"}).status_code == 400        # pas d'espace
    assert c.put("/api/reglages", json={"modele_second": ""}).status_code == 200                 # vide : permis
    assert c.get("/api/reglages").json()["reglages"]["modele_second"] == ""
    assert "modele_second" in main._journal() and not main.maison.est_secret("modele_second")    # part à la sauvegarde


def test_second_modele_sur_les_sept_routes(monter):
    c = monter()
    faux = _faux()
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    pid, rid, photo = _pret(c)
    for chemin, corps in _routes(pid, rid, photo):
        faux.modeles.clear()
        r = c.post(chemin, json=corps)                                       # premier jet : le modèle habituel
        assert r.status_code == 200, (chemin, r.text)
        assert set(faux.modeles) == {O.MODELE} and r.json()["modele"] == O.MODELE, chemin
        faux.modeles.clear()
        r = c.post(chemin, json={**corps, "second": True})                   # « Autres propositions »
        assert r.status_code == 200, (chemin, r.text)
        assert set(faux.modeles) == {"qwen2.5:14b"} and r.json()["modele"] == "qwen2.5:14b", chemin
        assert r.json()["propositions"], chemin


@pytest.mark.parametrize("valeur", [False, "oui", 1])
def test_second_seulement_si_vrai(monter, valeur):
    c = monter()
    faux = _faux()
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    pid, _, _ = _pret(c)
    r = c.post(f"/api/livrets/{pid}/ia", json={"action": "titres", "texte": "Le maire a inauguré le pont.", "second": valeur})
    assert r.status_code == 200 and set(faux.modeles) == {O.MODELE}


def test_reglage_vide_refus_400(monter):
    c = monter()
    faux = _faux()
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    pid, rid, photo = _pret(c)
    b = main.ETAT["base"]
    journal.enregistrer(b, {**journal.charger(b), "modele_second": ""})
    for chemin, corps in _routes(pid, rid, photo):
        r = c.post(chemin, json={**corps, "second": True})
        assert r.status_code == 400 and "Second modèle" in r.json()["detail"], chemin
    assert faux.modeles == []                                               # rien n'est parti vers le PC
    assert c.get(f"/api/recidives/{rid}").json()["ia"]["modele_second"] == ""
    assert c.get(f"/api/livrets/{pid}").json()["ia"]["modele_second"] == ""


def test_sonde_dit_si_le_second_est_present(monter):
    c = monter()
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux())
    r = c.post("/api/connexion/verifier").json()["ia"]
    assert r["ok"] is True and r["second_present"] is True and "second modèle qwen2.5:14b présent" in r["detail"]
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lambda chemin, corps: {"models": [{"name": O.MODELE}]})
    r = c.post("/api/connexion/verifier").json()["ia"]
    assert r["ok"] is True and r["second_present"] is False and "absent" in r["detail"]       # sans bloquer
    assert c.get("/api/connexion/etat").json()["ia"]["modele_second"] == "qwen2.5:14b"
    # Sans second modèle : la sonde reste comme avant
    ia = O.Ollama("http://pc:11434", lire=lambda chemin, corps: {"models": [{"name": O.MODELE}]})
    assert ia.sonder() == {"ok": True, "detail": f"PC prêt ({O.MODELE})"}


def test_modele_none_garde_le_modele_habituel():
    faux = _faux()
    ia = O.Ollama("http://pc:11434", lire=faux)
    ia.proposer("Camille devant un gâteau", "photo", "femme", "Camille")
    ia.proposer("Camille devant un gâteau", "photo", "femme", "Camille", modele=None)
    n = len(faux.modeles)                         # 3 titres sur 5 : les essais sont refaits, comme avant
    assert n == 2 * O.ESSAIS and set(faux.modeles) == {O.MODELE}
    ia.gazette("legende", "Camille à la plage", 1988, None, "Camille", "femme", modele="qwen2.5:14b")
    assert faux.modeles[n:] == ["qwen2.5:14b"]
