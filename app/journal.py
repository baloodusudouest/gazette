"""Les éléments communs à tous les livrets (titre du journal, lieu, hôtes, mot par défaut, couleur…),
réglés dans l'appli (Réglages › Le journal) et gardés dans la base.

Les variables de la stack GAZETTE_TITRE, GAZETTE_SIGNATURE, GAZETTE_LIEU et GAZETTE_LAROUSSE ne donnent
plus que la valeur de départ, tant que rien n'a été enregistré dans l'appli."""
from __future__ import annotations

import json
import re
from datetime import date

from .regles import MOIS, jour_mois

CHAMPS = {
    # clé : (libellé, aide, longueur maximale)
    "titre": ("Titre du journal", "le grand titre gothique de la une et l'en-tête des pages", 60),
    "sous_titre": ("Sous-titre", "sous le titre de la une", 90),
    "lieu": ("Nom du lieu", "le colophon de la page 4", 60),
    "lieu_detail": ("Sous le nom du lieu", "par exemple la commune et le département ; vide : rien", 80),
    "chez": ("Chez vous, avec l'article", "« au … », « à la … » : sert à « Imprimé … » et dans le mot des hôtes", 60),
    "signature": ("Signature des hôtes", "au bas du mot des hôtes", 60),
    "mot_modele": ("Mot des hôtes par défaut", "{date}, {prenom} et {chez} sont remplacés ; une ligne vide sépare les paragraphes", 1500),
    "accent": ("Couleur d'accent", "titres de rubrique, chiffres, lettrine (#RRGGBB)", 7),
}
MOT = ("Le {date}, le monde tournait comme le racontent ces pages. Ce soir, c'est {chez} que l'on vous attend.\n\n"
       "Ce petit journal est à vous, {prenom} : il raconte le monde tel qu'il était le jour de votre naissance. "
       "Gardez-le, glissez-le dans un livre, ou relisez-le au petit-déjeuner.\n\n"
       "Installez-vous, reposez-vous, et surtout faites comme chez vous.")


def defauts(cfg) -> dict:
    return {"titre": cfg.titre, "sous_titre": "Le monde tel qu'il était le jour de votre naissance",
            "lieu": cfg.lieu, "lieu_detail": "", "chez": "à la maison", "signature": cfg.signature,
            "mot_modele": MOT, "accent": "#9E1B1B", "larousse": cfg.larousse}


def charger(base, cfg) -> dict:
    j = defauts(cfg)
    try:
        j.update(json.loads(base.reglage("journal", "{}")))
    except ValueError:
        pass
    return j


def valider(corps: dict, actuel: dict) -> dict:
    j = dict(actuel)
    for cle, (libelle, _, maxi) in CHAMPS.items():
        if cle not in corps:
            continue
        v = str(corps[cle] or "").replace("\r", "")
        v = v.strip() if cle == "mot_modele" else " ".join(v.split())
        if len(v) > maxi:
            raise ValueError(f"{libelle} : {maxi} caractères au plus.")
        if cle in ("titre", "lieu", "chez", "signature", "mot_modele") and not v:
            raise ValueError(f"{libelle} : à remplir.")
        if cle == "accent" and not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError("Couleur d'accent : au format #RRGGBB.")
        j[cle] = v
    if "larousse" in corps:
        j["larousse"] = bool(corps["larousse"])
    return j


def mot(j: dict, prenom: str, naissance: date) -> str:
    valeurs = {"date": f"{jour_mois(naissance)} {naissance.year}", "prenom": prenom, "chez": j["chez"]}
    return re.sub(r"\{(date|prenom|chez)\}", lambda m: valeurs[m.group(1)], j["mot_modele"])
