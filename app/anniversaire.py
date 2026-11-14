"""Anniversaire proche du séjour (ajout du 14/11/2026).

Si l'anniversaire de l'invité tombe pendant le séjour, ou 1 à 14 jours avant l'arrivée, ou 1 à 14 jours après
le départ, Gazette le signale et propose trois phrases pour le souhaiter. L'âge en chiffres n'apparaît jamais."""
from __future__ import annotations

from datetime import date, timedelta

ECART = 14
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]

PHRASES = {
    "en_avance": [
        "Et puisque votre anniversaire arrive dans {n} : joyeux anniversaire, {prenom}, avec un peu d'avance !",
        "Un petit secret : on sait que vous soufflerez vos bougies {jour}. Joyeux anniversaire en avance !",
        "Bon anniversaire avant l'heure, {prenom} : ce journal en est le premier cadeau.",
    ],
    "le_jour_meme": [
        "Joyeux anniversaire, {prenom} ! Le fêter ici avec vous est un vrai bonheur.",
        "Le {date}, c'est votre jour : bon anniversaire, et merci de le passer avec nous.",
        "Votre anniversaire tombe pendant votre séjour : préparez-vous à quelques bougies.",
    ],
    "en_retard": [
        "Votre anniversaire, c'était il y a {n} : joyeux anniversaire en retard, {prenom}, mais de tout cœur !",
        "Mieux vaut tard que jamais : bon anniversaire, {prenom} !",
        "On n'a pas oublié votre anniversaire, on a juste attendu de vous avoir sous la main.",
    ],
}
LIBELLES = {"en_avance": "en avance", "le_jour_meme": "le jour même", "en_retard": "en retard"}


def anniversaire_en(naissance: date, annee: int) -> date:
    """L'anniversaire cette année-là ; le 29 février compte le 28 les années non bissextiles."""
    try:
        return naissance.replace(year=annee)
    except ValueError:
        return date(annee, 2, 28)


def _jours(n: int) -> str:
    return "un jour" if n == 1 else f"{n} jours"


def _date_longue(d: date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]}"


def proche(naissance: date | None, du: date, jusqu_au: date) -> dict | None:
    """Le cas de cet anniversaire pour ce séjour, ou None s'il est à plus de 14 jours.

    Rend {cas, libelle, anniversaire (ISO), ecart (jours, 0 pendant le séjour)}."""
    if naissance is None or jusqu_au < du:
        return None
    meilleur = None
    for annee in (du.year - 1, du.year, du.year + 1, jusqu_au.year + 1):
        a = anniversaire_en(naissance, annee)
        if du <= a <= jusqu_au:
            cas, ecart = "le_jour_meme", 0
        elif a < du:
            cas, ecart = "en_retard", (du - a).days
        else:
            cas, ecart = "en_avance", (a - jusqu_au).days
        if ecart <= ECART and (meilleur is None or ecart < meilleur["ecart"]):
            meilleur = {"cas": cas, "libelle": LIBELLES[cas], "anniversaire": a.isoformat(), "ecart": ecart}
    return meilleur


def phrases(cas: dict, prenom: str) -> list[str]:
    a = date.fromisoformat(cas["anniversaire"])
    valeurs = {"prenom": prenom or "cher invité", "n": _jours(cas["ecart"]),
               "jour": f"{JOURS[a.weekday()]} {_date_longue(a)}", "date": _date_longue(a)}
    return [p.format(**valeurs) for p in PHRASES[cas["cas"]]]
