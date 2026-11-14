"""Les règles de rédaction, sans IA : choisir, trier, raccourcir des faits datés. Rien n'est inventé.

Règles revues après le banc d'essai du 14/11/2026 (docs/banc-2026-11-14.md) :
- une : jour exact → veille → semaine → mois, avec la mention honnête de la portée ;
- classement : notoriété de TOUTES les pages liées (Wikidata), mots forts, pénalité du sport (sauf finale, record,
  jeux olympiques, coupe du monde), bonus du pays de naissance ;
- drames : repérés par mots entiers sur tous les blocs, marqués « sensibles » (jamais choisis seuls, toujours
  visibles à la relecture avec leur raison) ;
- personnes : seulement les êtres humains (Wikidata P31 = Q5), triées par notoriété ;
- titres coupés à une frontière (« : », « ; », parenthèse, virgule), jamais au milieu d'un mot.
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta

from .extraction import (MOIS, dedoublonner, evenements_en, evenements_fr, evenements_larousse,
                         personnes_du_jour, sans_accents)
from .sources import Sources, SourceIndisponible

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_COURT = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

SENSIBLE = re.compile(r"\b(" + "|".join([
    r"attentats?", r"terroris\w*", r"meurt", r"meurent", r"morts?", r"mortes?", r"mortels?", r"tue", r"tues", r"tuee?s?",
    r"tuent", r"victimes?", r"massacres?", r"assassin\w*", r"catastrophes?", r"seismes?", r"tremblements? de terre",
    r"explosions?", r"explosifs?", r"bombes?", r"bombard\w*", r"kamikazes?", r"crash", r"s'ecras\w*", r"accidents?",
    r"naufrages?", r"incendies?", r"otages?", r"fusill\w*", r"executes?", r"executees?", r"executions?",
    r"genocides?", r"epidemies?", r"inondations?", r"deces", r"decede\w*", r"suicides?", r"emeutes?", r"pendus?",
    r"noyes?", r"noyade", r"abattus?", r"guerres?", r"combats?", r"blesses?", r"attaques?", r"repression",
    r"enlev\w*", r"ouragans?", r"cyclones?", r"tsunamis?", r"famines?", r"viols?", r"violee?s?", r"meurtres?",
    r"tuerie", r"fusillades?", r"torpill\w*", r"invasion", r"envahi\w*", r"condamne\w* a mort", r"peine de mort",
    r"guillotin\w*", r"drame", r"effondre\w*", r"deraill\w*", r"disparition", r"obseques", r"funerailles",
    r"killed", r"dead", r"died", r"bomb\w*", r"murder\w*", r"crash\w*", r"war",
]) + r")\b")
FORTS = re.compile(r"\b(" + "|".join([
    r"elu", r"elue", r"election\w*", r"traite", r"accords?", r"independance", r"premier", r"premiere", r"lancement",
    r"lance", r"inaugur\w*", r"nobel", r"sommet", r"referendum", r"record", r"decouv\w*", r"signe\w*", r"loi",
    r"reforme", r"proclam\w*", r"president", r"constitution", r"investi\w*", r"ouverture", r"creation", r"cree\w*",
    r"fonde\w*", r"sacre\w*", r"couronn\w*", r"victoire", r"remporte", r"historique", r"spatial\w*", r"lune",
    r"satellite", r"europe\w*", r"olympiques?", r"coupe du monde", r"palme d'or",
]) + r")\b")
SPORT = re.compile(r"\b(football|tennis|rugby|cyclisme|tour de france|grand prix|formule 1|championnat|match|etape|"
                   r"boxe|golf|basket\w*|handball|ski|natation|athletisme|course|regate|marathon)\b")
SPORT_FORT = re.compile(r"\b(finale|record|olympiques?|coupe du monde|champion du monde|remporte le tour)\b")
PAYS_MOTS = {"france": re.compile(r"\b(france|francais\w*|paris|gaulle|mitterrand|pompidou|giscard|chirac|"
                                  r"assemblee nationale|senat|premier ministre)\b")}


def sensible(t: str) -> list[str]:
    return sorted({m.group(1) for m in SENSIBLE.finditer(sans_accents(t))})


# ================================================================ mise en forme

def jour_long(d: date) -> str:
    return f"{JOURS[d.weekday()].capitalize()} {'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


def jour_mois(d: date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]}"


def quand_court(d: date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {MOIS_COURT[d.month - 1]}"


BUDGET_P2, LONG_P2, BUDGET_BREVES = 1250, 550, 850   # signes ; la taille du texte s'ajuste ensuite à la page (rendu.AJUSTER)
_RENVOI = re.compile(r"\s*\((?:chrono?|cf|voir)\.?\s[^)]{0,24}\)", re.I)


def sans_renvoi(t: str) -> str:
    """Retire les renvois de chronique, « (chron. 4/02) », inutiles sur papier."""
    return _RENVOI.sub("", t or "").strip()


def premiere_phrase(t: str) -> str:
    return re.split(r"(?<=[a-zéèàûôîç0-9\)»%])\.\s+(?=[A-ZÉÈÀÂ«])", t.strip(), maxsplit=1)[0].rstrip(".")


def couper(t: str, maxi: int, mini: int = 25) -> str:
    """Coupe à la meilleure frontière avant `maxi` caractères : fin de phrase, puis « : », « ; », parenthèse,
    tiret, conjonction, virgule ; points de suspension seulement en dernier recours."""
    t = t.strip()
    if len(t) <= maxi:
        return t.rstrip(".") if t.count(".") == 1 and t.endswith(".") else t
    fins = [m.start() for m in re.finditer(r"(?<=[a-zéèàûôîç0-9\)»%])\.\s+(?=[A-ZÉÈÀÂ«])", t) if mini // 2 <= m.start() <= maxi]
    if fins:
        return t[:fins[-1] + 1]
    for motif in (r"\s+:\s+", r"\s*;\s+", r"\s+\(", r"\s+[—–]\s+", r"\s+(?:tout en|afin de|avant de|alors que|tandis que)\b",
                  r",\s+(?:qui|dont|où|après|alors|tandis|mais|et)\b", r",\s+"):
        coupes = [m.start() for m in re.finditer(motif, t) if mini <= m.start() <= maxi]
        if coupes:
            return t[:coupes[-1]].rstrip(" ,;:")
    return t[:maxi].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _majuscule(t: str) -> str:
    return t[0].upper() + t[1:] if t else t


FRONTIERES = (r"\s+:\s+", r"\s*;\s+", r"\s+[—–]\s+")


def scinder(t: str, maxi: int, mini: int = 20) -> tuple[str, str] | None:
    """Coupe en deux à une frontière naturelle (« : », « ; », tiret, « , qui »…) avant `maxi` caractères.
    Rien n'est perdu : la tête et le reste, ou None s'il n'y a pas de frontière."""
    for motif in FRONTIERES:
        coupes = [m for m in re.finditer(motif, t) if mini <= m.start() <= maxi]
        if coupes:
            m = coupes[-1]
            tete = t[:m.start()].rstrip(" ,;:")
            return tete, _majuscule(t[m.end():].strip())
    return None


def titre_et_chapo(t: str, maxi_titre: int = 110) -> tuple[str, str]:
    """Le gros titre et le chapeau, SANS RIEN PERDRE du texte de la source (14/11/2026) :
    première phrase courte → titre, la suite en chapeau ; sinon coupure à une frontière naturelle, la suite en
    chapeau ; sinon pas de titre, tout le texte en paragraphe."""
    t = t.strip()
    phrase = premiere_phrase(t)
    if len(phrase) <= maxi_titre:
        reste = t[len(phrase):].lstrip(" .").strip()
        return phrase.rstrip("."), _majuscule(reste)
    coupe = scinder(phrase, maxi_titre)
    if coupe:
        tete, suite = coupe
        reste = (suite + t[len(phrase):]).strip()
        if reste and not reste.endswith((".", "!", "?", "»", ")")):
            reste += "."
        return tete, reste
    return "", t


NOMBRE = re.compile(r"(?<![\d,])(\d{1,3}(?:[  .]\d{3})+|\d{2,}(?:,\d+)?)(?:\s*(%|km|kilomètres|mètres|tonnes|kg|millions?|milliards?))?"
                    r"((?:\s+[a-zéèêàâîôûç'’-]+){0,4})", re.I)
VIDES = {"est", "sont", "a", "ont", "qui", "que", "entre", "pour", "par", "dans", "sur", "en", "à", "au", "aux", "et",
         "ou", "avec", "contre", "selon", "lors", "sera", "seront", "fut", "furent"}


def _grouper(n: str) -> str:
    entier, _, dec = n.partition(",")
    chiffres = re.sub(r"\D", "", entier)
    g = " ".join(filter(None, [chiffres[max(0, i - 3):i] for i in range(len(chiffres), 0, -3)][::-1]))
    return g + ("," + dec if dec else "")


def encart(une: dict, d: date) -> dict:
    """Un nombre tiré du gros titre (hors années et jours) avec ce qu'il compte, sinon la date du jour."""
    for m in NOMBRE.finditer(une.get("texte", "")):
        brut = m.group(1)
        valeur = int(re.sub(r"\D", "", brut.split(",")[0]) or 0)
        mots = m.group(3).split()
        if 1000 <= valeur <= 2100 and not re.search(r"[  .]", brut):
            continue                                   # une année
        if mots and sans_accents(mots[0]) in [sans_accents(x) for x in MOIS]:
            continue                                   # une date
        unite = m.group(2) or ""
        libelle = []
        for w in mots:
            if sans_accents(w) in VIDES and libelle:
                break
            if sans_accents(w) in VIDES and w.lower() not in ("de", "d'", "des", "du"):
                break
            libelle.append(w)
        while libelle and sans_accents(libelle[-1]) in ("de", "des", "du", "d'", "la", "le", "les", "l'"):
            libelle.pop()
        if unite in ("millions", "million", "milliards", "milliard"):
            libelle = [unite] + libelle
            unite = ""
        if not libelle:
            continue
        valeur_txt = _grouper(brut) + (" " + unite if unite else "")
        return {"k": une.get("rubrique") or "En chiffres", "v": valeur_txt.replace(" ", "\u202f"), "l": " ".join(libelle)}
    return {"k": JOURS[d.weekday()].capitalize(), "v": str(d.day), "l": f"{MOIS[d.month - 1]} {d.year}"}


# ================================================================ classement

def score(e: dict, noto: dict, pays: str) -> float:
    s = 0.0
    ns = [noto.get(l, {}).get("n", 0) for l in e.get("liens", [])]
    if ns:
        s += 6 * math.log1p(max(ns)) + math.log1p(sum(ns)) / 2
    t = sans_accents(e["rubrique"] + " " + e["texte"])
    s += 4 * min(len(FORTS.findall(t)), 3)
    if SPORT.search(t) and not SPORT_FORT.search(t):
        s -= 12
    mots = PAYS_MOTS.get(sans_accents(pays or "France"))
    if mots and mots.search(t):
        s += 6
    if e["source"] == "larousse" and s < 8:
        s += 8                     # Larousse : faits déjà triés par une rédaction, sans liens à compter
    if e.get("langue") == "en":
        s -= 30                    # anglais : proposé, jamais choisi seul
    s += min(len(e["texte"]), 220) / 60
    return round(s, 2)


# ================================================================ préparation d'un livret

def _lire(fn, *args, notes: list, defaut=""):
    try:
        return fn(*args)
    except SourceIndisponible as ex:
        notes.append(str(ex))
        return defaut


def preparer(src: Sources, naissance: date, pays: str = "France") -> dict:
    """Lit les sources pour cette date et rend {propositions, contenu, sources, notes}.

    `propositions` garde toutes les possibilités (avec leur drapeau « sensible ») ; `contenu` est le choix
    automatique, modifiable bloc par bloc à la relecture."""
    d, y = naissance, naissance.year
    notes: list[str] = []
    utilisees: set[str] = set()
    evts: list[dict] = []

    mois_a_lire = {(y, d.month)}
    if d.day <= 8:
        p = d.replace(day=1) - timedelta(days=1)
        mois_a_lire.add((p.year, p.month))
    for (aa, mm) in sorted(mois_a_lire):
        w = _lire(src.wikipedia, Sources.titre_mois(aa, mm), notes=notes)
        if w:
            utilisees.add("wikipedia")
            evts += evenements_fr(w, aa, "wikipedia")
        lar = _lire(src.larousse, aa, mm, notes=notes)
        if lar:
            le = evenements_larousse(lar)
            if le:
                utilisees.add("larousse")
                evts += le
    annee_fr = evenements_fr(_lire(src.wikipedia, f"{y} en France", notes=notes), y, "wikipedia-france")
    annee_monde = evenements_fr(_lire(src.wikipedia, str(y), notes=notes), y, "wikipedia-annee")
    if annee_fr or annee_monde:
        utilisees.add("wikipedia")
    # Les pages annuelles complètent les jours (même date, autre formulation : dédoublonnage par début de texte)
    evts = dedoublonner(evts + [e for e in annee_fr + annee_monde if abs((date.fromisoformat(e["date"]) - d).days) <= 31])

    fenetre = [e for e in evts if d - timedelta(days=7) <= date.fromisoformat(e["date"]) <= d]
    if len([e for e in fenetre if not sensible(e["texte"])]) < 4:
        en = []
        for (aa, mm) in sorted(mois_a_lire):
            w = _lire(src.wikipedia, Sources.titre_mois_en(aa, mm), "en", notes=notes)
            if w:
                en += evenements_en(w, aa)
        if en:
            utilisees.add("wikipedia-en")
            evts += [e for e in en if abs((date.fromisoformat(e["date"]) - d).days) <= 31]

    jour_page = _lire(src.wikipedia, Sources.titre_jour(d.day, d.month), notes=notes)
    nes = [p for p in personnes_du_jour(jour_page, "Naissances") if p["annee"] <= y]
    morts = [p for p in personnes_du_jour(jour_page, "Décès") if p["annee"] <= y]

    titres = set()
    for e in evts + annee_fr + annee_monde:
        titres.update(e["liens"][:6])
    titres = sorted(titres)[:600] + [p["titre"] for p in nes + morts]
    noto = _lire(src.wikidata, titres, notes=notes, defaut={}) or {}
    if noto:
        utilisees.add("wikidata")

    def fiche(e: dict, i: int, prefixe: str) -> dict:
        de = date.fromisoformat(e["date"])
        titre, chapo = titre_et_chapo(e["texte"])
        return {"id": f"{prefixe}{i}", "date": e["date"], "quand": quand_court(de), "texte": sans_renvoi(e["texte"]),
                "titre": titre, "chapo": chapo, "rubrique": e["rubrique"], "source": e["source"],
                "langue": e.get("langue", "fr"), "sensible": sensible(e["rubrique"] + " " + e["texte"]),
                "score": score(e, noto, pays)}

    tous = [fiche(e, i, "e") for i, e in enumerate(evts)]
    tous = [f for f in tous if len(f["texte"].split()) >= 3]   # « Grande-Bretagne » seul n'est pas un fait

    def portee(f: dict) -> str:
        de = date.fromisoformat(f["date"])
        if de == d:
            return "jour"
        if de == d - timedelta(days=1):
            return "veille"
        if d - timedelta(days=6) <= de <= d:
            return "semaine"
        if de.year == y and de.month == d.month:
            return "mois"
        return "autour"
    for f in tous:
        f["portee"] = portee(f)
    rang = {"jour": 0, "veille": 1, "semaine": 2, "mois": 3, "autour": 4}
    une_cands = sorted([f for f in tous if f["portee"] != "autour"],
                       key=lambda f: (rang[f["portee"]], bool(f["sensible"]), f["langue"] != "fr", -f["score"]))
    # Choix automatique : la meilleure de la portée la plus proche qui a un fait propre en français
    une = None
    for p in ("jour", "veille", "semaine", "mois"):
        propres = [f for f in une_cands if f["portee"] == p and not f["sensible"] and f["langue"] == "fr"]
        if propres:
            une = max(propres, key=lambda f: f["score"])
            break

    pris = {une["id"]} if une else set()
    breves_cands = sorted([f for f in tous if d - timedelta(days=6) <= date.fromisoformat(f["date"]) <= d and f["id"] not in pris],
                          key=lambda f: (bool(f["sensible"]), f["langue"] != "fr", -f["score"]))
    breves = []
    for f in breves_cands:
        if f["sensible"] or f["langue"] != "fr":
            continue
        if sum(1 for b in breves if b["date"] == f["date"]) >= 2:
            continue
        if breves and sum(len(b["texte"]) for b in breves) + len(f["texte"]) > BUDGET_BREVES:
            continue
        breves.append(f)
        if len(breves) == 4:
            break
    pris |= {b["id"] for b in breves}

    semaine_cands = sorted([f for f in tous if d - timedelta(days=7) <= date.fromisoformat(f["date"]) < d],
                           key=lambda f: (bool(f["sensible"]), f["langue"] != "fr", -f["score"]))
    semaine = _choisir_p2([f for f in semaine_cands if not f["sensible"] and f["langue"] == "fr" and f["id"] not in pris])
    mode_p2 = "semaine"
    if len(semaine) < 3:
        # Semaine trop maigre : on passe au mois plutôt que de répéter les brèves de la une
        mois_c = [f for f in tous if f["portee"] in ("semaine", "mois", "autour") and f["id"] not in pris
                  and not f["sensible"] and f["langue"] == "fr"]
        mois_c.sort(key=lambda f: (f["date"][:7] != d.isoformat()[:7], -f["score"]))   # le mois de la naissance d'abord
        semaine = _choisir_p2(semaine + [f for f in mois_c if f not in semaine], par_jour=1)
        mode_p2 = "mois"
    semaine.sort(key=lambda f: f["date"])

    # Chronologie de l'année : 3 repères du pays (« <année> en France »), 3 du monde, un par mois d'abord ; 6 en tout pour laisser la place à la culture
    fr_ids = {id(e) for e in annee_fr}
    annee, origine = [], {}
    for i, e in enumerate(dedoublonner(annee_fr + annee_monde)):
        f = fiche(e, i, "a")
        f["portee"] = "annee"
        f["monde"] = id(e) not in fr_ids
        annee.append(f)

    def piocher(lot: list[dict], n: int, mois_vus: set) -> list[dict]:
        lot = sorted([f for f in lot if not f["sensible"] and f["date"] != d.isoformat()], key=lambda f: -f["score"])
        pris_ = []
        for f in lot:
            if f["date"][:7] not in mois_vus:
                pris_.append(f)
                mois_vus.add(f["date"][:7])
            if len(pris_) == n:
                return pris_
        for f in lot:
            if len(pris_) == n:
                break
            if f not in pris_:
                pris_.append(f)
        return pris_
    vus_mois: set = set()
    chrono = piocher([f for f in annee if not f["monde"]], 3, vus_mois)
    chrono += piocher([f for f in annee if f["monde"]], 6 - len(chrono), vus_mois)
    chrono.sort(key=lambda f: f["date"])
    for f in annee:
        f["court"] = premiere_phrase(f["texte"])

    def gens(lst: list[dict], n: int) -> list[dict]:
        vus, sortie = set(), []
        for p in sorted(lst, key=lambda p: -noto.get(p["titre"], {}).get("n", 0)):
            info = noto.get(p["titre"])
            if noto and (not info or not info.get("humain")):
                continue
            if p["titre"] in vus:
                continue
            vus.add(p["titre"])
            sortie.append({"nom": p["nom"], "annee": p["annee"], "titre": p["titre"],
                           "n": info.get("n", 0) if info else 0})
        return sortie[:n]
    nes_tri, morts_tri = gens(nes, 12), gens(morts, 12)

    propositions = {"evenements": sorted(une_cands, key=lambda f: (f["date"], -f["score"])),
                    "annee": sorted(annee, key=lambda f: f["date"]), "nes": nes_tri, "morts": morts_tri}
    contenu = {
        "une": _bloc_une(une, d),
        "breves": [_breve(b) for b in breves],
        "p2": {"mode": mode_p2, "items": [_item_p2(f) for f in semaine]},
        "chrono": [{"id": f["id"], "date": f["date"], "quand": f["quand"], "texte": f["court"]} for f in chrono],
        "musique": "", "cinema": "",
        "nes": [{"nom": p["nom"], "annee": p["annee"]} for p in nes_tri[:5]],
        "morts": [{"nom": p["nom"], "annee": p["annee"]} for p in morts_tri[:4]],
    }
    return {"propositions": propositions, "contenu": contenu, "sources": sorted(utilisees), "notes": notes}


def _bloc_une(une: dict | None, d: date) -> dict:
    if not une:
        return {"id": "", "titre": "", "chapo": "", "portee": "vide", "date": "", "rubrique": "",
                "encart": encart({}, d)}
    return {"id": une["id"], "titre": une["titre"], "chapo": une["chapo"], "portee": une["portee"], "date": une["date"],
            "rubrique": une["rubrique"], "encart": encart(une, d)}


def _noms(f: dict) -> set[str]:
    """Noms propres d'un texte (mot à majuscule de 5 lettres ou plus, hors début de phrase)."""
    mots = re.findall(r"(?<![.!?]\s)(?<!^)\b([A-ZÀ-Ý][a-zà-ÿ]{4,})", f["texte"])
    return set(mots) - {"France", "Paris", "Grande", "Union", "Église", "États"}


def _choisir_p2(cands: list[dict], par_jour: int = 2) -> list[dict]:
    """Jusqu'à 5 événements, au plus `par_jour` le même jour, qui tiennent ensemble sur la page (BUDGET_P2 signes) :
    le texte reste complet, on écarte d'abord les très longs, repris seulement s'il en manque."""
    pris: list[dict] = []
    for long_ok in (False, True):
        for f in cands:
            if f in pris or sum(1 for x in pris if x["date"] == f["date"]) >= par_jour:
                continue
            if any(x["date"] == f["date"] and _noms(x) & _noms(f) for x in pris):   # même fait, deux sources
                continue
            n = len(f["texte"])
            if n > LONG_P2 and not long_ok:
                continue
            if len(pris) >= 3 and sum(len(x["texte"]) for x in pris) + n > BUDGET_P2:
                continue
            pris.append(f)
            if len(pris) == 5:
                return pris
        if len(pris) >= 3:
            break
    return pris


def _item_p2(f: dict) -> dict:
    """Un titre de la page 2 : la rubrique de la source en titre si elle existe ; sinon la première phrase
    si elle est courte ; sinon pas de titre. Le texte complet est toujours gardé."""
    if f["rubrique"]:
        return {"id": f["id"], "date": f["date"], "titre": f["rubrique"], "texte": f["texte"]}
    phrase = premiere_phrase(f["texte"])
    if len(phrase) <= 80 and len(phrase) < len(f["texte"].rstrip(".")):
        return {"id": f["id"], "date": f["date"], "titre": phrase.rstrip("."),
                "texte": _majuscule(f["texte"][len(phrase):].lstrip(" .").strip())}
    return {"id": f["id"], "date": f["date"], "titre": "", "texte": f["texte"]}


def _breve(f: dict) -> dict:
    """Une brève : la rubrique de la source en titre, sinon la date (« Le 5 juillet ») ; le texte raccourci."""
    de = date.fromisoformat(f["date"])
    return {"id": f["id"], "titre": f["rubrique"] or f"Le {jour_mois(de)}", "texte": f["texte"],
            "date": f["date"]}


def bloc_depuis(f: dict, sorte: str, d: date) -> dict:
    """Le bloc construit à partir d'une proposition choisie à la relecture."""
    if sorte == "une":
        return _bloc_une(f, d)
    if sorte == "breve":
        return _breve(f)
    if sorte == "p2":
        return _item_p2(f)
    if sorte == "chrono":
        return {"id": f["id"], "date": f["date"], "quand": f["quand"], "texte": f.get("court") or premiere_phrase(f["texte"])}
    raise ValueError(sorte)


PORTEES = {"jour": "Ce jour-là", "veille": "La veille", "semaine": "Cette semaine-là", "mois": "Ce mois-là", "vide": ""}
