"""0.23 : la « fiche complète » d'une personne pour les journaux (Gazette et La Récidive), rangée dans carnet.

Version retenue le 18/11/2026 (après conseil et arbitrages de Julien) :
- la fiche est faite de « pépites » : `{id, rubrique, texte (200 au plus), le, source, parue_le}`, rangées dans les
  rubriques de `rubriques_journaux.json` (copie à l'identique du fichier de carnet : mêmes clés) ;
- « Sujets interdits » (rubrique `interdits`, ou `interdit` vrai) : jamais envoyés à l'IA ; toute proposition qui
  contient un de leurs mots significatifs (4 lettres au moins, hors mots vides) est écartée ;
- à chaque demande à l'IA, 3 à 5 pépites tirées au hasard, en priorité celles qui ne sont jamais parues ; le ton
  souhaité (rubrique `ton`) est toujours envoyé ;
- la ligne « vrac » est rangée dans la rubrique la plus probable par mots-clés (sans IA ; « autre » sinon).

Module pur : aucune lecture réseau, aucune base. carnet est lu et écrit par `carnet.py`."""
from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

FICHIER = Path(__file__).parent / "rubriques_journaux.json"
MAXI = 200                       # caractères par pépite
TIRAGE = (3, 5)                  # pépites tirées pour une demande à l'IA
PALIERS = [(5, "de quoi rire"), (15, "bien fournie"), (30, "inépuisable")]
SOURCES = ("julien", "carnet", "recidive", "sillage")
ECARTEES = "propositions écartées par les sujets interdits, relance"


def charger_rubriques(chemin: Path = FICHIER) -> dict:
    """Le fichier des rubriques, contrôlé : ValueError avec un message clair s'il n'a pas la forme attendue."""
    d = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(d, dict) or not isinstance(d.get("familles"), list) or not d["familles"]:
        raise ValueError("rubriques_journaux.json : « familles » (liste non vide) attendue.")
    vues = set()
    for f in d["familles"]:
        if not isinstance(f, dict) or not f.get("cle") or not f.get("titre") or not isinstance(f.get("rubriques"), list):
            raise ValueError("rubriques_journaux.json : chaque famille a une clé, un titre et des rubriques.")
        for r in f["rubriques"]:
            if not isinstance(r, dict) or not re.fullmatch(r"[a-z0-9-]+", str(r.get("cle") or "")) or not r.get("titre"):
                raise ValueError(f"rubriques_journaux.json : rubrique mal écrite ({r!r}) : clé en minuscules sans accents.")
            if r["cle"] in vues:
                raise ValueError(f"rubriques_journaux.json : clé en double ({r['cle']}).")
            vues.add(r["cle"])
    i = d.get("interdits")
    if not isinstance(i, dict) or i.get("cle") != "interdits" or not i.get("titre"):
        raise ValueError("rubriques_journaux.json : section « interdits » attendue.")
    if "autre" not in vues or "ton" not in vues:
        raise ValueError("rubriques_journaux.json : les rubriques « autre » et « ton » sont attendues.")
    return d


RUBRIQUES = charger_rubriques()
INTERDITS = RUBRIQUES["interdits"]["cle"]
TITRES = {r["cle"]: r["titre"] for f in RUBRIQUES["familles"] for r in f["rubriques"]}
TITRES[INTERDITS] = RUBRIQUES["interdits"]["titre"]
CLES = set(TITRES)               # rubriques permises, « interdits » compris


# ================================================================ mots

def norme(texte: str) -> str:
    """Minuscules, sans accents ; tout ce qui n'est pas lettre ou chiffre devient une espace."""
    s = "".join(c for c in unicodedata.normalize("NFD", texte or "") if unicodedata.category(c) != "Mn").lower()
    s = s.replace("œ", "oe").replace("æ", "ae")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


MOTS_VIDES = set(norme(
    "avec dans pour sans sous chez elle elles nous vous leur leurs mais donc plus moins tout tous toute toutes cette "
    "celle celles celui ceux sont était étaient être avoir fait faire comme quand très aussi bien encore même mêmes "
    "entre depuis vers alors parce notre votre nôtre vôtre quoi dont peut sait avait aura ainsi autre autres cela ceci "
    "rien jamais toujours souvent quelque quelques chaque après avant pendant contre selon parle parler sujet sujets "
    "dire dit pas trop peu fois").split())


def mots_significatifs(texte: str) -> set[str]:
    """Les mots de 4 lettres au moins, hors mots vides (forme normalisée)."""
    return {m for m in norme(texte).split() if len(m) >= 4 and m not in MOTS_VIDES and not m.isdigit()}


# ================================================================ pépites

def est_interdite(p: dict) -> bool:
    return bool(p.get("interdit")) or p.get("rubrique") == INTERDITS


def propre(texte) -> str:
    """Le texte d'une pépite : espaces réduites, 200 caractères au plus. ValueError si vide ou pas un texte."""
    if not isinstance(texte, str):
        raise ValueError("Un texte est attendu.")
    t = " ".join(texte.split())
    if not t:
        raise ValueError("Pépite vide.")
    if len(t) > MAXI:
        raise ValueError(f"Pépite trop longue ({MAXI} caractères au plus).")
    return t


def pepites_valides(liste) -> list[dict]:
    """Les pépites lisibles d'une réponse de carnet (les autres sont ignorées), champs connus seulement."""
    res = []
    for p in liste if isinstance(liste, list) else []:
        if not isinstance(p, dict) or not p.get("id") or not isinstance(p.get("texte"), str):
            continue
        rub = p.get("rubrique") if p.get("rubrique") in CLES else "autre"
        res.append({"id": str(p["id"]), "rubrique": rub, "texte": " ".join(p["texte"].split())[:MAXI],
                    "le": str(p.get("le") or ""), "source": p.get("source") if p.get("source") in SOURCES else "julien",
                    "parue_le": p.get("parue_le") or None, "interdit": est_interdite({**p, "rubrique": rub})})
    return res


def interdits(pepites: list[dict]) -> list[str]:
    return [p["texte"] for p in pepites if est_interdite(p)]


def ton(pepites: list[dict]) -> str:
    """Le ton souhaité (rubrique « ton »), toujours envoyé à l'IA."""
    return " ; ".join(p["texte"] for p in pepites if p.get("rubrique") == "ton" and not est_interdite(p))


def tirer(pepites: list[dict], rng: random.Random | None = None) -> list[dict]:
    """3 à 5 pépites au hasard (moins s'il n'y en a pas assez), jamais interdites ni « ton » (envoyé à part) ; d'abord
    celles qui ne sont jamais parues, puis les autres."""
    rng = rng or random.Random()
    dispo = [p for p in pepites if not est_interdite(p) and p.get("rubrique") != "ton" and (p.get("texte") or "").strip()]
    neuves = [p for p in dispo if not p.get("parue_le")]
    parues = [p for p in dispo if p.get("parue_le")]
    rng.shuffle(neuves)
    rng.shuffle(parues)
    n = rng.randint(*TIRAGE)
    return (neuves + parues)[:n]


def pour_ia(prenom: str, tirage: list[dict], ton_: str) -> str:
    """Ce que l'IA reçoit de la fiche : les pépites tirées, rubrique par rubrique, et le ton souhaité."""
    morceaux = []
    if tirage:
        morceaux.append(f"Détails de la fiche de {prenom or 'cette personne'} (piochés au hasard, à utiliser librement, "
                        "un ou deux suffisent) : " + " ; ".join(f"{TITRES.get(p['rubrique'], 'divers').lower()} : {p['texte']}"
                                                                for p in tirage))
    if ton_:
        morceaux.append(f"Ton souhaité pour {prenom or 'cette personne'} : {ton_}")
    return ". ".join(morceaux)


def _textes(prop) -> str:
    if isinstance(prop, dict):
        return " ".join(str(v) for v in prop.values() if isinstance(v, str))
    return str(prop or "")


def filtrer(propositions: list, textes_interdits: list[str]) -> tuple[list, int]:
    """Écarte toute proposition (texte, ou lettre du courrier) qui contient un mot significatif d'un sujet interdit
    (même mot, ou mot qui le prolonge : « divorce » écarte « divorcée »). Rend (gardées, nombre écartées)."""
    mots = set()
    for t in textes_interdits:
        mots |= mots_significatifs(t)
    if not mots:
        return list(propositions), 0
    gardees = []
    for prop in propositions:
        vus = norme(_textes(prop)).split()
        if any(v == m or (len(m) >= 5 and v.startswith(m)) for v in vus for m in mots):
            continue
        gardees.append(prop)
    return gardees, len(propositions) - len(gardees)


def palier(n: int) -> str:
    """« de quoi rire » à partir de 5 pépites, « bien fournie » à 15, « inépuisable » à 30."""
    nom = ""
    for seuil, libelle in PALIERS:
        if n >= seuil:
            nom = libelle
    return nom


# ================================================================ la ligne « vrac »

# rubrique : débuts de mots (forme normalisée). Le plus de débuts trouvés gagne ; à égalité, l'ordre de la liste.
MOTS_CLES: dict[str, tuple[str, ...]] = {
    "si-c-etait": ("serait",),
    "ressemble": ("ressembl", "sosie", "personnage"),
    "ton": ("taquin", "tendre", "absurde"),
    "surnoms": ("surnom", "appelle", "appelait"),
    "phrases": ("dit toujours", "phrase", "replique", "expression", "repete", "citation", "dicton", "rengaine"),
    "running-gags": ("gag", "blague", "rigole", "running"),
    "peurs": ("peur", "phobi", "terrifi", "angoiss", "araignee", "vertige", "panique"),
    "agace": ("agace", "enerv", "horripil", "insupport", "rage", "exaspere"),
    "talents": ("talent", "doue", "imite", "jongle", "virtuose", "champion"),
    "defauts": ("defaut", "retard", "distrait", "maladroit", "tete en l air", "perd ", "egare"),
    "manies": ("manie", "habitude", "tic", "maniaque", "obsession", "verifie"),
    "traits": ("genereu", "timide", "bavard", "jaloux", "ronchon", "curieu", "gentil", "patient", "optimist", "rale", "tetu",
               "caractere", "drole"),
    "gaffes": ("gaffe", "betise", "bourde", "casse", "tombe", "rate ", "oublie"),
    "anecdotes": ("histoire", "anecdote", "raconte", "une fois"),
    "sejours": ("sejour", "chambre", "petit dej", "venu", "derniere fois", "chez nous"),
    "projets": ("projet", "reve", "envie", "voudrait", "aimerait", "compte ", "futur"),
    "metier": ("travail", "boulot", "metier", "bureau", "collegue", "patron", "infirmi", "prof", "medecin", "ingenieur",
               "retraite", "usine", "entreprise", "job", "comptable", "agricult", "vigneron", "boulanger", "plombier"),
    "ville-maison": ("habite", "maison", "appartement", "ville", "village", "region", "quartier", "jardin", "demenag", "campagne"),
    "conjoint": ("mari", "epoux", "epouse", "conjoint", "compagn", "cheri", "pacse"),
    "enfants": ("enfant", "fils", "fille", "bebe", "ado", "gamin", "petit fils", "petite fille"),
    "animaux": ("chien", "chat", "cheval", "lapin", "perroquet", "animal", "animaux", "poule", "hamster", "tortue", "canari"),
    "famille": ("frere", "soeur", "parent", "pere", "mere", "maman", "papa", "oncle", "tante", "cousin", "grand", "famille", "belle"),
    "amis": ("ami", "copain", "copine", "copains", "bande", "pote"),
    "voiture": ("voiture", "auto", "moto", "train", "permis", "conduit", "scooter", "camping car", "garer", "bus", "trottinette"),
    "boissons": ("vin", "biere", "cafe", "champagne", "whisky", "pastis", "apero", "cocktail", "soda", "coca", "tisane", "boit",
                 "boire", "armagnac", "rhum"),
    "musique": ("musique", "chanson", "chante", "concert", "guitare", "piano", "rock", "rap", "karaoke", "danse", "album"),
    "ecrans": ("film", "serie", "emission", "tele", "netflix", "cinema", "regarde", "documentaire"),
    "livres": ("livre", "roman", "bd", "manga", "lecture", "polar", "bouquin", "lit des", "lire"),
    "sports": ("sport", "foot", "rugby", "tennis", "courir", "course", "marathon", "natation", "nage", "ski", "rando", "gym",
               "muscu", "match", "equipe", "supporter", "petanque", "golf", "judo", "yoga", "velo"),
    "jeux": ("jeu", "jeux", "scrabble", "belote", "cartes", "poker", "console", "playstation", "xbox", "switch", "escape",
             "monopoly", "sudoku", "mots croises", "tarot"),
    "loisirs": ("collection", "jardinage", "bricol", "tricot", "couture", "peinture", "peint", "photo", "peche", "passion", "loisir"),
    "voyages": ("voyage", "vacances", "pays", "plage", "montagne", "croisiere", "avion", "italie", "espagne", "ile ", "partir"),
    "fetes": ("eurovision", "fete", "anniversaire", "noel", "reveillon", "soiree", "carnaval", "deguis"),
    "style": ("porte ", "habill", "vetement", "chemise", "chapeau", "lunettes", "chaussure", "robe", "pull", "tenue", "look",
              "cravate", "basket", "style"),
    "sommeil": ("dort", "dormir", "sieste", "reveil", "ronfle", "insomni", "sommeil", "grasse matinee", "couche"),
    "techno": ("telephone", "portable", "smartphone", "ordinateur", "ordi", "internet", "appli", "tablette", "facebook",
               "instagram", "whatsapp", "techno", "tiktok", "selfie"),
}
ALIMENTS = ("plat", "gateau", "chocolat", "fromage", "pizza", "legume", "epinard", "chou", "brocoli", "viande", "pates",
            "frites", "soupe", "salade", "tarte", "cuisine", "mange", "repas", "dessert", "huitre", "escargot", "tomate",
            "endive", "poisson", "magret", "foie gras", "pruneau", "canele", "crepe", "glace", "bonbon", "aubergine",
            "courgette", "coriandre", "olive", "champignon", "oignon", "ail ", "abat", "tripe")
NEGATIFS = ("deteste", "horreur", "supporte pas", "degout", "allerg", "jamais", "pas de", "n aime pas", "aime pas",
            "intoleran", "beurk", "vomi")


def ranger(texte: str) -> str:
    """La rubrique la plus probable d'une ligne « vrac » (par mots-clés, sans IA) ; « autre » si rien ne ressort."""
    t = " " + norme(texte) + " "
    if re.search(r" si (c|elle|il|lui) etait ", t):
        return "si-c-etait"
    mots = t.split()

    def compte(cles: tuple[str, ...]) -> int:
        n = 0
        for c in cles:
            if c.endswith(" "):                         # mot entier
                n += f" {c.strip()} " in t
            elif " " in c:                              # expression : début cherché tel quel dans le texte
                n += f" {c}" in t
            else:
                n += any(m.startswith(c) for m in mots)
        return n

    if compte(ALIMENTS):                                 # un aliment : aimé ou détesté selon la phrase
        return "plats-detestes" if compte(NEGATIFS) else "plats-aimes"
    meilleur, score = "autre", 0
    for rub, cles in MOTS_CLES.items():
        n = compte(cles)
        if n > score:
            meilleur, score = rub, n
    return meilleur


# ================================================================ pré-remplissage (suggestions grisées « Ajouter »)

CONNU = {"metier": "metier", "conjoint": "conjoint", "enfants": "enfants", "animaux": "animaux"}
ALIMENTATION = {  # clé de carnet → (rubrique, préfixe)
    "plaisirs": ("plats-aimes", ""), "aimes": ("plats-aimes", ""), "aime": ("plats-aimes", ""),
    "non_aimes": ("plats-detestes", ""), "non aimes": ("plats-detestes", ""), "detestes": ("plats-detestes", ""),
    "allergies": ("plats-detestes", "Allergie : "), "intolerances": ("plats-detestes", "Intolérance : "),
    "regime": ("plats-detestes", "Régime : "),
}


def _liste(v) -> list[str]:
    """Une valeur de carnet (texte, liste de textes ou d'objets) → des textes."""
    if v is None or v is False:
        return []
    if isinstance(v, str):
        return [x for x in (" ".join(p.split()) for p in re.split(r"[\n;]", v)) if x]
    if isinstance(v, (int, float)):
        return [str(v)]
    if isinstance(v, dict):
        nom = v.get("nom") or v.get("texte") or v.get("prenom")
        return [" ".join(str(nom).split())] if nom else []
    if isinstance(v, list):
        return [t for x in v for t in _liste(x)]
    return []


def suggestions_connues(connu: dict | None, parus: list[dict] | None, etapes: list[dict] | None) -> list[dict]:
    """Ce qui est déjà connu, à valider d'un geste : carnet (métier, conjoint, enfants, animaux, alimentation), anciens
    numéros de La Récidive (événements, indices) et étapes du chemin de Sillage (nom et année, une par une)."""
    res: list[dict] = []
    connu = connu if isinstance(connu, dict) else {}
    for cle, rub in CONNU.items():
        for t in _liste(connu.get(cle)):
            res.append({"rubrique": rub, "texte": t, "source": "carnet", "origine": "fiche de carnet"})
    alim = connu.get("alimentation", connu.get("regime"))
    if isinstance(alim, dict):
        for cle, v in alim.items():
            rub, prefixe = ALIMENTATION.get(norme(cle).replace(" ", "_"), ALIMENTATION.get(norme(cle), ("plats-detestes", "")))
            for t in _liste(v):
                res.append({"rubrique": rub, "texte": prefixe + t, "source": "carnet", "origine": "fiche de carnet"})
    else:
        for t in _liste(alim):
            res.append({"rubrique": "plats-detestes", "texte": "Régime : " + t, "source": "carnet", "origine": "fiche de carnet"})
    for x in parus or []:
        if not isinstance(x, dict):
            continue
        an = str(x.get("le") or "")[:4]
        if (x.get("evenement") or "").strip():
            res.append({"rubrique": "sejours", "texte": (f"{an} : " if an else "") + " ".join(x["evenement"].split()),
                        "source": "recidive", "origine": f"La Récidive {an}".strip()})
        for t in re.split(r"[;\n]|(?<=[.!?])\s", str(x.get("indices") or "")):
            if len(t.strip()) >= 3:
                res.append({"rubrique": "autre", "texte": " ".join(t.split()).rstrip("."), "source": "recidive",
                            "origine": f"indices de La Récidive {an}".strip()})
    for e in etapes or []:
        if isinstance(e, dict) and (e.get("nom") or "").strip():
            an = e.get("annee")
            res.append({"rubrique": "voyages", "texte": " ".join(str(e["nom"]).split()) + (f" ({an})" if an else ""),
                        "source": "sillage", "origine": "chemin de Sillage"})
    vus, propres = set(), []
    for s in res:
        s["texte"] = s["texte"][:MAXI]
        k = norme(s["texte"])
        if k and k not in vus:
            vus.add(k)
            propres.append(s)
    return propres


def sans_doublons(suggestions: list[dict], pepites: list[dict]) -> list[dict]:
    """Les suggestions dont le texte n'est pas déjà une pépite (casse, accents et ponctuation ignorés)."""
    deja = {norme(p.get("texte", "")) for p in pepites}
    return [s for s in suggestions if norme(s["texte"]) not in deja]


# ================================================================ textes retenus → pépites parues

def proche(texte: str, propositions: list[str], seuil: float = 0.6) -> bool:
    """Un texte imprimé vient-il de l'une de ces propositions (Julien a pu la retoucher) ?"""
    import difflib
    t = norme(texte)
    if len(t) < 6:
        return False
    for p in propositions:
        q = norme(p)
        if q and (q in t or t in q or difflib.SequenceMatcher(None, t, q).ratio() >= seuil):
            return True
    return False
