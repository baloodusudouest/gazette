"""Ce que Gazette lit dans l'environnement du conteneur. Aucune valeur personnelle dans le code.

0.8 : seules restent les variables qui ne sont pas des réglages d'usage — le mot de passe et le jeton communs
(MAISON_PASSWORD, MAISON_JETON), la lecture seule (MAISON_LECTURE_SEULE, forçable par GAZETTE_LECTURE_SEULE), le
jeton de Home Assistant (GAZETTE_JETON_HA) et l'adresse de carnet dans la stack (GAZETTE_CARNET_URL). 0.9 : l'adresse
et la clé d'Immich (GAZETTE_IMMICH_URL, GAZETTE_IMMICH_CLE) pour La Récidive. Le titre du
journal, le lieu, les hôtes, le mot par défaut, la couleur et Larousse se règlent dans l'appli (journal.py)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import maison

APPLI = "gazette"


def racine(adresse: str) -> str:
    """0.7 : schéma, hôte et port seulement (« http://nas:8089/ha/sejour » → « http://nas:8089 »). Gazette est
    servie à la racine et ses liens ajoutent « /#/livret/… » : un chemin laissé dans l'adresse donnait un lien faux."""
    a = (adresse or "").strip()
    if not a:
        return ""
    if "://" not in a:
        return a.split("/", 1)[0]
    s = urlsplit(a)
    return f"{s.scheme}://{s.netloc}" if s.netloc else a.rstrip("/")


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    jeton_ha: str = ""                   # GAZETTE_JETON_HA : porte /ha/… ; vide : fermée
    lecture_seule: bool = False          # MAISON_LECTURE_SEULE ou GAZETTE_LECTURE_SEULE : n'imprime pas (seule écriture hors de chez elle)
    lecture_seule_origine: str = ""      # « maison », « appli » ou « » : d'où vient la lecture seule (affichée)
    sources_actives: bool = True         # coupé dans les tests : aucune lecture réseau
    attente_connexion: bool = True       # délai anti-essais ; coupé dans les tests
    synchrone: bool = False              # tests : la préparation se fait dans la requête, pas en file
    carnet_url: str = ""                 # GAZETTE_CARNET_URL : adresse de carnet (http://carnet:8096 dans la stack)
    carnet_jeton: str = ""               # MAISON_JETON (0.8 : plus d'ancien jeton par paire) ; vide : carnet pas lu
    immich_url: str = ""                 # 0.9 : GAZETTE_IMMICH_URL (http://immich_server:2283 dans la stack)
    immich_cle: str = ""                 # 0.9 : GAZETTE_IMMICH_CLE, clé d'API dédiée ; vide : pas de Récidive


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe()                       # 0.8 : MAISON_PASSWORD seul
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD est absent ou trop court (12 caractères au moins) : Gazette ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("GAZETTE_DATA", "/data")),      # dossier dans le conteneur (image), pas la stack
        static=Path(__file__).parent / "static",
        jeton_ha=os.environ.get("GAZETTE_JETON_HA", "").strip(),
        lecture_seule=maison.lecture_seule("GAZETTE_LECTURE_SEULE"),
        lecture_seule_origine=maison.origine_lecture_seule("GAZETTE_LECTURE_SEULE"),
        carnet_url=os.environ.get("GAZETTE_CARNET_URL", "").strip().rstrip("/") or "http://carnet:8096",
        carnet_jeton=maison.jeton_a_envoyer(),                 # 0.8 : MAISON_JETON seul
        immich_url=os.environ.get("GAZETTE_IMMICH_URL", "").strip().rstrip("/") or "http://immich_server:2283",
        immich_cle=os.environ.get("GAZETTE_IMMICH_CLE", "").strip(),
    )
