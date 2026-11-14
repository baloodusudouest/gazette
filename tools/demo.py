"""Serveur de démonstration : Gazette avec des personnes et un séjour inventés, sources simulées (aucun réseau).

Sert aux tests d'écran et aux captures. Usage : python -m tools.demo [port]   (mot de passe : demo-demo-demo)
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

import httpx
import uvicorn

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app import main  # noqa: E402
from app.base import Base  # noqa: E402
from app.config import Config  # noqa: E402
from tests import fixtures as F  # noqa: E402

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
     "naissance": "1988-07-08", "jour": 8, "mois": 7, "annee": 1988},
]
NOTORIETE = [("Gustav Exemple", 90), ("Ringo Exemple", 120), ("Arthur Exemple", 80), ("Henri Exemple", 20)]


def configurer(data: Path) -> None:
    b = Base(data / "gazette.db")
    for cle, contenu in SOURCES.items():
        b.garder_source(cle, contenu)
    for t, n in NOTORIETE:
        b.garder_source(f"wd:fr:{t}", f'{{"n": {n}, "humain": true}}')
    b.fermer()
    main.ETAT.clear()
    main.ETAT["carnet_lire"] = lambda url, jeton: CARNET
    main.ETAT["cfg"] = Config(password=MDP, data=data, static=RACINE / "app" / "static", attente_connexion=False,
                              carnet_url="http://carnet.demo", carnet_jeton="jeton-de-demo",
                              sources_actives=False, synchrone=True, jeton_ha=JETON, titre="La Gazette de démonstration",
                              signature="Les hôtes", lieu="La maison")


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
        c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07", "alias": ["Cam"]})
        c.post("/api/personnes", json={"nom": "Lou Martin", "naissance": "1988-07-07"})
        a = date.today().year + (1 if date.today() >= date(date.today().year, 7, 3) else 0)
        c.post("/ha/sejour", headers={"Authorization": f"Bearer {JETON}"},
               json={"chambre": "verte", "noms": ["Camille Fabre", "Dominique Inconnu", "Sacha Exemple"],
                     "du": f"{a}-07-03", "jusqu_au": f"{a}-07-05"})


def lancer(port: int, data: Path) -> None:
    configurer(data)
    threading.Thread(target=semer, args=(f"http://127.0.0.1:{port}",), daemon=True).start()
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(int(sys.argv[1]) if len(sys.argv) > 1 else 8099, Path(tempfile.mkdtemp(prefix="gazette-demo-")))
