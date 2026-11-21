"""Serveur de démonstration : Gazette avec des personnes et un séjour inventés, sources simulées (aucun réseau).

Sert aux tests d'écran et aux captures. Usage : python -m tools.demo [port]   (mot de passe : demo-demo-demo)
"""
from __future__ import annotations

import base64
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import uvicorn

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app import main  # noqa: E402
from app.base import Base  # noqa: E402
from app.config import Config  # noqa: E402
from tests import fixtures as F  # noqa: E402
from tests.carnet_simule import CarnetFiche  # noqa: E402
from tests import douze_simule as DS  # noqa: E402
from tests.faux_paperless import FauxPaperless  # noqa: E402

MDP = "demo-demo-demo"
JETON = "jeton-de-demo"
SOURCES = {"wp:fr:Juillet 1988": F.MOIS_PUCES, "wp:fr:Juin 1988": "", "wp:fr:1988 en France": F.ANNEE_FRANCE,
           "wp:fr:1988": F.ANNEE_MONDE, "wp:fr:7 juillet": F.JOUR, "wp:en:July 1988": F.EN_MOIS, "wp:en:June 1988": "",
           "lar:1988-07": F.LAROUSSE, "lar:1988-06": ""}
CARNET = [  # carnet simulé, personnes inventées
    {"carnet_id": "d1", "nom": "Dominique INCONNU", "nom_carnet": "Dominique Inconnu", "prenom": "Dominique",
     "naissance": "1988-07-07", "jour": 7, "mois": 7, "annee": 1988},
    {"carnet_id": "d2", "nom": "Sacha Exemple", "nom_carnet": "Sacha Exemple", "prenom": "Sacha",
     "naissance": None, "jour": 3, "mois": 5, "annee": None},
    {"carnet_id": "d3", "nom": "Lou MARTIN", "nom_carnet": "Lou Martin", "prenom": "Lou",
     "naissance": "1988-07-08", "jour": 8, "mois": 7, "annee": 1988, "genre": "femme", "immich_id": "10000000-0001",
     "personne_id": "pm-demo-lou"},
]


def carnet_fiche_simule() -> CarnetFiche:
    """0.23 : carnet 2.33 simulé — la fiche complète de Lou Martin (détails inventés). Camille Fabre n'est pas dans
    carnet : sa fiche dit « carnet ne trouve pas cette personne »."""
    f = CarnetFiche()
    f.personnes["pm-demo-lou"] = {"pepites": [], "suggestions": [
        {"rubrique": "metier", "texte": "Garde forestière", "source": "carnet"},
        {"rubrique": "animaux", "texte": "Pistache", "source": "carnet"}],
        "connu": {"metier": "Garde forestière", "conjoint": [], "enfants": [], "animaux": ["Pistache"],
                  "alimentation": {"allergies": [], "intolerances": [], "non_aimes": [], "plaisirs": []},
                  "immich_id": "10000000-0001"}}
    for rub, texte in (("plats-aimes", "Adore les cannelés"), ("manies", "Range les épices par ordre alphabétique"),
                       ("ton", "Taquin mais tendre"), ("interdits", "Le concours de chant raté")):
        f.pepite("pm-demo-lou", rub, texte)
    return f


def sillage_simule(url: str, jeton: str, immich_id: str) -> dict:
    """0.23 : Sillage simulé — deux étapes du chemin de Lou Martin (inventées)."""
    if immich_id != "10000000-0001":
        return {"contrat": 1, "etapes": []}
    return {"contrat": 1, "etapes": [{"nom": "Tour de Corse à vélo", "annee": 2018, "photos": 40},
                                     {"nom": "Vendanges", "annee": 2026, "photos": 12}]}
# 0.9 : Immich simulé pour La Récidive (Lou Martin revient) — une petite image grise pour chaque photo
GRIS = base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx"
                        "NDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAI"
                        "AQEAAD8AKp//2Q==")


def immich_simule(methode: str, chemin: str, corps: dict | None = None):
    auj = date.today()
    recentes = [{"id": f"20000000-000{i}", "localDateTime": (auj - timedelta(days=25 - i * 6)).isoformat() + "T12:00:00"} for i in range(3)]
    vieilles = [{"id": f"30000000-{an}", "localDateTime": f"{an}-08-15T12:00:00"} for an in (1994, 2003, 2011, 2017)]
    if chemin == "/tags":
        return [{"id": "tag-scandale", "value": "scandale"}]
    if chemin.startswith("/albums?assetId="):          # 0.12 : un album parlant, un générique (écarté)
        return [{"id": "album-vendanges", "albumName": "Vendanges 2026"}, {"id": "album-an", "albumName": "2026"}]
    if chemin.startswith("/assets/") and "/thumbnail" not in chemin:
        return {"people": [{"id": "10000000-0001", "name": "Lou Martin"}, {"id": "p-yves", "name": "Bastien"}]}
    if chemin == "/search/metadata":
        if "albumIds" in corps:
            return {"assets": {"items": recentes[:2], "nextPage": None}}
        if "tagIds" in corps:
            return {"assets": {"items": vieilles, "nextPage": None}}
        if "takenAfter" not in corps:                 # 0.13 : toutes les photos (page 4 de la Gazette)
            return {"assets": {"items": recentes + vieilles, "nextPage": None}}
        return {"assets": {"items": [a for a in recentes if corps["takenAfter"][:10] <= a["localDateTime"][:10] < corps["takenBefore"][:10]],
                           "nextPage": None}}
    return GRIS
NOTORIETE = [("Gustav Exemple", 90), ("Ringo Exemple", 120), ("Arthur Exemple", 80), ("Henri Exemple", 20)]


def ollama_simule(chemin: str, corps: dict | None):
    """0.9.1 : l'IA du PC simulée (titres fixes). 0.22 : d'autres titres avec le second modèle (« Autres propositions »)."""
    if corps is None:
        return {"models": [{"name": "qwen2.5:7b"}, {"name": "qwen2.5:14b"}]}
    if corps.get("model") == "qwen2.5:14b":
        return {"response": "1. Lou sort enfin du silence\n2. La vérité éclate sur la plage\n3. Révélations à l'heure de la sieste\n"
                            "4. Les aveux du parasol\n5. Un été sous haute surveillance"}
    return {"response": "1. Flagrant délit au soleil\n2. Les vacances secrètes de Lou\n3. Elle nie tout en bloc\n"
                        "4. Photo volée, sourire avoué\n5. Le scandale de l'été"}


def anneau_simule(adresse: str, jeton: str) -> dict:
    """L'Anneau simulé : deux sauvegardes des réglages, la plus récente d'abord (aucun réseau)."""
    if "?le=" not in adresse:
        return {"dates": ["2026-11-15", "2026-11-14"]}
    le = adresse.rsplit("?le=", 1)[1]
    return {"le": le, "version": "0.8.0", "reglages": {"titre": "La Gazette d'avant", "signature": "Les hôtes",
                                                       "accent": "#1B4E9E", "larousse": False}}


def configurer(data: Path) -> None:
    b = Base(data / "gazette.db")
    for cle, contenu in SOURCES.items():
        b.garder_source(cle, contenu)
    for t, n in NOTORIETE:
        b.garder_source(f"wd:fr:{t}", f'{{"n": {n}, "humain": true}}')
    b.fermer()
    main.ETAT.clear()
    main.ETAT["carnet_lire"] = lambda url, jeton: CARNET
    main.ETAT["carnet_fiche"] = carnet_fiche_simule()             # 0.23 : fiche complète (carnet 2.33)
    main.ETAT["carnet_paru"] = lambda url, jeton, pid, cle, corps: None     # numéros parus : rien ne sort
    main.ETAT["carnet_ecrire"] = lambda url, jeton, pid, texte: None
    main.ETAT["sillage_lire"] = sillage_simule
    main.ETAT["cfg"] = Config(password=MDP, data=data, static=RACINE / "app" / "static", attente_connexion=False,
                              carnet_url="http://carnet.demo", carnet_jeton="jeton-de-demo", sillage_url="http://sillage.demo",
                              sources_actives=False, synchrone=True, jeton_ha=JETON, douze_points_url="http://douze.demo",
                              paperless_url="http://paperless.demo", paperless_jeton="jeton-paperless-demo")
    main.ETAT["anneau_lire"] = anneau_simule
    main.ETAT["immich_lire"] = immich_simule
    main.ETAT["ollama_lire"] = ollama_simule
    # 0.28 : Douze points simulé (contrat de Douze points 1.9.0) — une finale et une demi-finale clôturées
    # 0.30 : Paperless simulé (faux Paperless du socle) : les numéros approuvés y sont rangés, rien ne sort
    main.ETAT["paperless_transport"] = FauxPaperless(delai_traitement=0).compte("jeton-paperless-demo", 3).transport
    main.ETAT["paperless_dormir"] = lambda s: None
    main.ETAT["douze_lire"] = DS.DouzeSimule({1: [DS.habiller(DS.exemple(), 1)], 2: [DS.habiller(DS.exemple(demi=True), 2)]},
                                             jeton="jeton-de-demo")


def semer(adresse: str) -> None:
    """Deux fiches, un séjour annoncé par « Home Assistant » (un invité sans fiche, un anniversaire en avance)."""
    for _ in range(200):
        try:
            if httpx.get(adresse + "/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    with httpx.Client(base_url=adresse) as c:
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        c.put("/api/reglages", json={"titre": "La Gazette de démonstration", "signature": "Les hôtes"})
        c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07", "alias": ["Cam"]})
        c.post("/api/personnes", json={"nom": "Lou Martin", "naissance": "1988-07-07"})
        a = date.today().year + (1 if date.today() >= date(date.today().year, 7, 3) else 0)
        c.post("/ha/sejour", headers={"Authorization": f"Bearer {JETON}"},
               json={"chambre": "verte", "noms": ["Camille Fabre", "Dominique Inconnu", "Sacha Exemple"],
                     "du": f"{a}-07-03", "jusqu_au": f"{a}-07-05"})
        # 0.9 : Lou Martin est venue il y a un mois et revient : La Récidive N° 2
        auj = date.today()
        for du, fin in ((auj - timedelta(days=30), auj - timedelta(days=28)), (auj + timedelta(days=12), auj + timedelta(days=14))):
            c.post("/ha/sejour", headers={"Authorization": f"Bearer {JETON}"},
                   json={"chambre": "bleue", "noms": ["Lou Martin"], "du": du.isoformat(), "jusqu_au": fin.isoformat()})
        c.post("/api/eurovision/relire")          # 0.28 : deux numéros de Good Evening Europe! à relire


def lancer(port: int, data: Path) -> None:
    configurer(data)
    threading.Thread(target=semer, args=(f"http://127.0.0.1:{port}",), daemon=True).start()
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(int(sys.argv[1]) if len(sys.argv) > 1 else 8099, Path(tempfile.mkdtemp(prefix="gazette-demo-")))
