"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code :
le titre du journal, la signature et le lieu viennent de la stack."""
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
    # Valeurs de départ seulement : le journal se règle dans l'appli (Réglages › Le journal, journal.py)
    titre: str = "La Gazette"            # GAZETTE_TITRE
    signature: str = "Vos hôtes"         # GAZETTE_SIGNATURE
    lieu: str = "La maison"              # GAZETTE_LIEU
    jeton_ha: str = ""                   # GAZETTE_JETON_HA : porte /ha/… ; vide : fermée
    imprimante: str = ""                 # GAZETTE_IMPRIMANTE : adresse IPP (temps 3)
    lecture_seule: bool = False          # MAISON_LECTURE_SEULE ou GAZETTE_LECTURE_SEULE : n'imprime pas (seule écriture hors de chez elle)
    lecture_seule_origine: str = ""      # « maison », « appli » ou « » : d'où vient la lecture seule (affichée)
    sources_actives: bool = True         # coupé dans les tests : aucune lecture réseau
    attente_connexion: bool = True       # délai anti-essais ; coupé dans les tests
    synchrone: bool = False              # tests : la préparation se fait dans la requête, pas en file
    adresse: str = ""                    # GAZETTE_ADRESSE : repli de l'adresse de Gazette (tuile « Gazette » de l'Anneau d'abord)
    larousse: bool = True                # GAZETTE_LAROUSSE=non (valeur de départ, puis Réglages)
    carnet_url: str = ""                 # GAZETTE_CARNET_URL : adresse de carnet (http://carnet:8096 dans la stack)
    carnet_jeton: str = ""               # GAZETTE_CARNET_JETON, puis MAISON_JETON ; vide : carnet pas lu


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe("GAZETTE_PASSWORD")      # 0.7 : MAISON_PASSWORD, repli sur l'ancien nom
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD (ou GAZETTE_PASSWORD) est absent ou trop court (12 caractères au moins) : "
                         "Gazette ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("GAZETTE_DATA", "/data")),
        static=Path(__file__).parent / "static",
        titre=os.environ.get("GAZETTE_TITRE", "").strip() or "La Gazette",
        signature=os.environ.get("GAZETTE_SIGNATURE", "").strip() or "Vos hôtes",
        lieu=os.environ.get("GAZETTE_LIEU", "").strip() or "La maison",
        jeton_ha=os.environ.get("GAZETTE_JETON_HA", "").strip(),
        imprimante=os.environ.get("GAZETTE_IMPRIMANTE", "").strip(),
        lecture_seule=maison.lecture_seule("GAZETTE_LECTURE_SEULE"),          # 0.7 : MAISON_LECTURE_SEULE, forçable ici
        lecture_seule_origine=maison.origine_lecture_seule("GAZETTE_LECTURE_SEULE"),
        adresse=racine(os.environ.get("GAZETTE_ADRESSE", "")),                # 0.7 : sans chemin
        larousse=os.environ.get("GAZETTE_LAROUSSE", "").strip().lower() not in ("non", "0", "false", "no"),
        carnet_url=os.environ.get("GAZETTE_CARNET_URL", "").strip().rstrip("/") or "http://carnet:8096",
        carnet_jeton=maison.jeton_a_envoyer("GAZETTE_CARNET_JETON"),          # 0.7 : puis MAISON_JETON
    )
