"""0.9 : La Récidive, le journal à scandale qui remplace la Gazette à partir du deuxième séjour d'une personne.

Règles (dossier, ajout du 17/11/2026, arbitrées après le conseil du même jour) :
- N° = numéro du séjour de la personne (séjours connus de Gazette + séjours d'avant Gazette notés sur la fiche) ;
  corrigeable à la main. Premier séjour : la Gazette.
- Fenêtre des photos : de l'arrivée du séjour précédent (compris) à l'arrivée du nouveau.
- Le plus possible de photos récentes ; s'il en manque, des photos de la personne taguées « scandale » dans Immich
  (rubrique « Anciens scandales »), pas encore publiées d'abord, réparties sur les décennies, au hasard dans chaque
  décennie, puis en variant les années ; déjà publiées seulement s'il n'en reste plus.
- Aucune photo dans la fenêtre : pas de Récidive, le séjour garde la Gazette.
- Légendes de gabarit, modifiables à la relecture. 0.9.1 : Julien décrit une photo en quelques mots, l'IA locale
  (ollama.py) propose 5 titres de 60 caractères au plus pour la légende ou le gros titre de la une ; il en choisit un
  ou écrit le sien. Relecture et approbation obligatoires avant impression.
Aucune date de naissance dans ce journal."""
from __future__ import annotations

import random
from datetime import date

from .regles import MOIS

MACARONS = {"hg": "en haut à gauche", "hd": "en haut à droite", "bg": "en bas à gauche", "bd": "en bas à droite",
            "aucun": "sans macaron"}      # 0.9.2 : place du macaron « Exclusif ! » sur la photo de la une
CADRAGES = {"haut": "Rogner : haut", "centre": "centre", "bas": "bas", "entiere": "Photo entière"}    # 0.9.2 : cadrage de chaque photo (par défaut : rognée, garder le haut)
LETTRES = 2                   # 0.11 : courrier des lecteurs imprimé en page 4, au plus
DEBUTS = [((1, 1), "Capricorne", "♑"), ((1, 20), "Verseau", "♒"), ((2, 19), "Poissons", "♓"), ((3, 21), "Bélier", "♈"),
          ((4, 20), "Taureau", "♉"), ((5, 21), "Gémeaux", "♊"), ((6, 21), "Cancer", "♋"), ((7, 23), "Lion", "♌"),
          ((8, 23), "Vierge", "♍"), ((9, 23), "Balance", "♎"), ((10, 23), "Scorpion", "♏"), ((11, 22), "Sagittaire", "♐"),
          ((12, 22), "Capricorne", "♑")]       # premier jour de chaque signe (dates usuelles)


def signe(naissance: str) -> tuple[str, str]:
    """0.11 : le signe du zodiaque d'après la date de naissance (seul le signe est imprimé, jamais la date)."""
    try:
        d = date.fromisoformat(naissance[:10])
    except (TypeError, ValueError):
        return "", ""
    nom, sym = "", ""
    for debut, n, sy in DEBUTS:
        if (d.month, d.day) >= debut:
            nom, sym = n, sy
    return nom, sym


RUMEURS = 4                   # 0.9.7 : rumeurs loufoques imprimées en page 3, au plus
PLACES = 7                    # une photo en une (page 1) + six sur la page 2
ACCENT = "#D7191C"


def numero(arrivees: list[str], du: str, avant: int = 0) -> int:
    """Rang de ce séjour parmi les séjours connus de la personne (par date d'arrivée), plus ceux d'avant Gazette."""
    return max(0, int(avant or 0)) + 1 + sum(1 for a in set(arrivees) if a < du)


def precedent(sejours: list[dict], du: str, dernier_avant: str = "") -> dict | None:
    """Le séjour précédent : le dernier connu de Gazette arrivé avant `du`, sinon la date notée sur la fiche."""
    avant = [s for s in sejours if s["du"] < du]
    if avant:
        s = max(avant, key=lambda s: s["du"])
        return {"du": s["du"], "jusqu_au": s["jusqu_au"]}
    if dernier_avant and dernier_avant < du:
        return {"du": dernier_avant, "jusqu_au": ""}
    return None


def accroche(genre: str, prenom: str) -> str:
    """Le sous-titre de « La Récidive », accordé au genre de la fiche carnet (inconnu : avec le prénom)."""
    if genre == "femme":
        return "Elle est revenue, nous aussi"
    if genre == "homme":
        return "Il est revenu, nous aussi"
    return f"{prenom or 'Notre invité·e'} est de retour, nous aussi"


def titre_une(nom: str) -> str:
    """Le gros titre de la une par défaut (0.9.1 : remplaçable par un titre choisi ou écrit)."""
    return f"{nom} revient !"


def code_barres(prenom: str) -> str:
    """0.11.4 : le message caché dans le code-barres de la page 4, par défaut."""
    return f"Reviens vite, {prenom} !"


def salut(genre: str, prenom: str) -> str:
    return {"femme": f"Chère {prenom}", "homme": f"Cher {prenom}"}.get(genre, prenom)


def mot_par_defaut(genre: str, prenom: str) -> str:
    return (f"{salut(genre, prenom)}, vous avez lu notre enquête : nous assumons tout. Les hôtes n'ont qu'un seul "
            "démenti à faire valoir : vous nous avez manqué.\n\n"
            "Votre chambre est prête. Rien ne sortira de la maison, hormis ce journal, et il est à vous.")


def date_photo(iso: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return "date inconnue"
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


def legende(photo: dict) -> str:
    """Légende de gabarit (modifiable à la relecture) : rien d'inventé, seulement la date du cliché."""
    if photo.get("ancien"):
        return f"Cliché du {date_photo(photo.get('date', ''))}, ressorti pour l'occasion."
    return f"Cliché du {date_photo(photo.get('date', ''))}, versé au dossier."


def etaler(photos: list[dict], n: int) -> list[dict]:
    """n photos réparties dans le temps (la plus récente toujours gardée : elle fait la une)."""
    if n <= 0 or not photos:
        return []
    if len(photos) <= n:
        return list(photos)
    pas = (len(photos) - 1) / (n - 1) if n > 1 else 0
    rangs = sorted({round(len(photos) - 1 - i * pas) for i in range(n)})
    return [photos[r] for r in rangs]


def decennies(photos: list[dict], n: int, alea: random.Random) -> list[dict]:
    """n photos prises sur le plus de décennies possible : au hasard dans chaque décennie, une décennie après
    l'autre (départ au hasard), en évitant de reprendre une année déjà prise tant qu'une autre reste."""
    par_dec: dict[int, list[dict]] = {}
    for p in photos:
        try:
            an = int(p["date"][:4])
        except (KeyError, ValueError):
            an = 0
        par_dec.setdefault(an // 10, []).append(p)
    for lst in par_dec.values():
        alea.shuffle(lst)
    ordre = sorted(par_dec)
    if ordre:
        k = alea.randrange(len(ordre))
        ordre = ordre[k:] + ordre[:k]
    pris, annees = [], set()
    while len(pris) < n and any(par_dec[d] for d in ordre):
        for d in ordre:
            if len(pris) >= n or not par_dec[d]:
                continue
            lst = par_dec[d]
            i = next((j for j, p in enumerate(lst) if p["date"][:4] not in annees), 0)
            p = lst.pop(i)
            pris.append(p)
            annees.add(p["date"][:4])
    return pris


def choisir(recentes: list[dict], scandales: list[dict] | None, publies: set[str], garder: list[dict] | None = None,
            exclus: set[str] | None = None, graine: int | None = None) -> dict:
    """Les photos de l'édition.

    `recentes` : photos de la fenêtre (plus anciennes d'abord) ; `scandales` : photos taguées « scandale » (None :
    tag absent) ; `publies` : photos « scandale » déjà parues dans une édition approuvée ; `garder` : photos déjà
    choisies et gardées à la relecture (avec leur légende) ; `exclus` : photos retirées à la relecture.
    Rend {photos, manque_scandale, tag_absent, trouvees} ; `photos` vide : pas de Récidive (aucune photo récente)."""
    exclus, garder = set(exclus or ()), [p for p in (garder or []) if not p.get("retiree")]
    alea = random.Random(graine)
    pris = {p["id"] for p in garder}
    dispo = [p for p in recentes if p["id"] not in exclus and p["id"] not in pris]
    if not dispo and not any(not p.get("ancien") for p in garder):
        return {"photos": [], "manque_scandale": False, "tag_absent": scandales is None, "trouvees": len(recentes)}
    places = PLACES - len(garder)
    nouvelles = [{**p, "ancien": False} for p in etaler(dispo, places)]
    places -= len(nouvelles)
    anciennes, manque = [], False
    if places > 0:
        dans_fenetre = {p["id"] for p in recentes}
        candidats = [p for p in (scandales or []) if p["id"] not in exclus and p["id"] not in pris and p["id"] not in dans_fenetre]
        jamais = [p for p in candidats if p["id"] not in publies]
        anciennes = decennies(jamais, places, alea)
        if len(anciennes) < places:
            deja = [p for p in candidats if p["id"] in publies]
            anciennes += decennies(deja, places - len(anciennes), alea)
        anciennes = [{**p, "ancien": True} for p in anciennes]
        manque = not candidats
    photos = garder + nouvelles + anciennes
    # Récentes d'abord (la plus récente fait la une), puis les anciens scandales du plus ancien au plus récent
    rec = sorted((p for p in photos if not p.get("ancien")), key=lambda p: p.get("date", ""), reverse=True)
    anc = sorted((p for p in photos if p.get("ancien")), key=lambda p: p.get("date", ""))
    sortie = []
    for p in rec + anc:
        q = {k: p.get(k) for k in ("id", "date", "ancien")}
        q["legende"] = p.get("legende") or legende(q)
        q["retiree"] = False
        q["cadrage"] = p.get("cadrage") or "haut"
        q["description"] = p.get("description", "")          # 0.9.1 : ce que Julien voit sur la photo (pour l'IA)
        q["propositions"] = list(p.get("propositions") or [])
        if "contexte" in p:                                    # 0.12 : albums et personnes d'Immich, déjà lus
            q["contexte"] = p["contexte"]
        sortie.append(q)
    return {"photos": sortie, "manque_scandale": manque, "tag_absent": scandales is None, "trouvees": len(recentes)}


def jours_absence(prec: dict | None, du: str) -> int | None:
    if not prec:
        return None
    try:
        depart = date.fromisoformat((prec.get("jusqu_au") or prec["du"])[:10])
        return max(0, (date.fromisoformat(du) - depart).days)
    except (KeyError, ValueError):
        return None
