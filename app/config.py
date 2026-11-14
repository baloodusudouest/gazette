"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code :
le titre du journal, la signature et le lieu viennent de la stack."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APPLI = "gazette"


def _oui(nom: str) -> bool:
    return os.environ.get(nom, "").strip().lower() in ("oui", "1", "true", "yes")


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
    lecture_seule: bool = False          # GAZETTE_LECTURE_SEULE : n'imprime pas (seule écriture hors de chez elle)
    sources_actives: bool = True         # coupé dans les tests : aucune lecture réseau
    attente_connexion: bool = True       # délai anti-essais ; coupé dans les tests
    synchrone: bool = False              # tests : la préparation se fait dans la requête, pas en file
    adresse: str = ""                    # GAZETTE_ADRESSE : adresse de Gazette dans le navigateur (liens des notifications)
    larousse: bool = True                # GAZETTE_LAROUSSE=non (valeur de départ, puis Réglages)
    carnet_url: str = ""                 # GAZETTE_CARNET_URL : adresse de carnet (http://carnet:8096 dans la stack)
    carnet_jeton: str = ""               # GAZETTE_CARNET_JETON : = CARNET_JETON_GAZETTE de carnet ; vide : carnet pas lu


def charger() -> Config:
    mot_de_passe = os.environ.get("GAZETTE_PASSWORD", "")
    if len(mot_de_passe) < 12:
        raise SystemExit("GAZETTE_PASSWORD est absent ou trop court (12 caractères au moins) : Gazette ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("GAZETTE_DATA", "/data")),
        static=Path(__file__).parent / "static",
        titre=os.environ.get("GAZETTE_TITRE", "").strip() or "La Gazette",
        signature=os.environ.get("GAZETTE_SIGNATURE", "").strip() or "Vos hôtes",
        lieu=os.environ.get("GAZETTE_LIEU", "").strip() or "La maison",
        jeton_ha=os.environ.get("GAZETTE_JETON_HA", "").strip(),
        imprimante=os.environ.get("GAZETTE_IMPRIMANTE", "").strip(),
        lecture_seule=_oui("GAZETTE_LECTURE_SEULE"),
        adresse=os.environ.get("GAZETTE_ADRESSE", "").strip().rstrip("/"),
        larousse=os.environ.get("GAZETTE_LAROUSSE", "").strip().lower() not in ("non", "0", "false", "no"),
        carnet_url=os.environ.get("GAZETTE_CARNET_URL", "").strip().rstrip("/") or "http://carnet:8096",
        carnet_jeton=os.environ.get("GAZETTE_CARNET_JETON", "").strip(),
    )
