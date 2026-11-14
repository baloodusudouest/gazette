"""Lecture des sources brutes, sans réseau : wikitext de Wikipédia (FR et EN) et pages des Journaux de l'année
de Larousse. Chaque fonction rend des événements datés : {date, texte, liens, rubrique, source}.

Formats reconnus (banc d'essai du 14/11/2026) :
- Wikipédia FR, pages « <mois> <année> » : puces datées ({{date+|9 novembre}}, [[9 novembre]], « 9 novembre : ») ou
  une section par jour (« Lundi {{date|1er mai 2000}} », « Vendredi {{1er juin}} [[2001]] », « Mercredi 4 août 2004 ») ;
  sections « Événements », « Évènements », « Faits marquants », « Actualités du mois », « Chronologie ».
- Wikipédia FR, pages « <année> en France » et « <année> » : sections par mois, puces « 14 avril : … ».
- Wikipédia FR, pages « <jour> <mois> » : sections Naissances et Décès, puces par année.
- Wikipédia EN, pages « <Month>_<year> » : une section par jour (« == February 11, 1964 (Tuesday) == »).
- Larousse : <li date="JJ/MM/AAAA"> avec la rubrique en <div class="adresse"> ou en tête du texte en <b>.
"""
from __future__ import annotations

import html as html_mod
import re
import unicodedata
from datetime import date

import mwparserfromhell

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]
MOIS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
           "october", "november", "december"]


def sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


MOIS_N = [sans_accents(m) for m in MOIS]


def num_mois(mot: str) -> int | None:
    m = sans_accents(mot).strip(".")
    if m in MOIS_N:
        return MOIS_N.index(m) + 1
    if m in MOIS_EN:
        return MOIS_EN.index(m) + 1
    return None


def jour_num(j: str) -> int:
    return 1 if j.lower() in ("1er", "1re") else int(j)


# ================================================================ wikitext → texte

ORDINAUX = {"er": "er", "1er": "1er", "e": "e", "re": "re"}


def texte(wikitexte: str) -> str:
    """Rend lisible une ligne de wikitext : références retirées, modèles courants rendus, liens réduits à leur texte."""
    w = re.sub(r"<ref[^>]*/>", "", wikitexte)
    w = re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    code = mwparserfromhell.parse(w)
    for t in code.filter_templates(recursive=False):
        nom = str(t.name).strip()
        bas = nom.lower()
        params = [str(p.value).strip() for p in t.params]
        try:
            if bas in ("date+", "date-", "date-+") and params:
                rendu = " ".join(p for p in params[:3] if p)
            elif bas in ("date", "date de naissance", "date de décès") and params:
                rendu = " ".join(p for p in params[:3] if p)
            elif re.fullmatch(r"1er \w+", bas):
                rendu = bas
            elif bas in ("er", "re", "e", "ème", "eme", "ers", "res", "es") :
                rendu = {"ème": "e", "eme": "e"}.get(bas, bas)
            elif re.fullmatch(r"\d+(?:er|re|e|ème)", bas):
                rendu = re.sub(r"ème$", "e", bas)
            elif bas in ("1er", "1re"):
                rendu = bas
            elif bas.startswith("formatnum:"):
                rendu = nom.split(":", 1)[1]
            elif bas in ("formatnum", "nombre", "nb") and params:
                rendu = " ".join(params[:2])
            elif bas in ("unité", "unite") and params:
                rendu = " ".join(params[:2])
            elif bas in ("s-", "s", "siècle") and params:
                rendu = params[0] + "e siècle"
            elif bas in ("lang", "langue") and len(params) >= 2:
                rendu = params[1]
            elif bas in ("souverain2", "souverain3", "souverain", "nobr", "nowrap", "nom", "pc", "smallcaps",
                         "petites capitales", "romain", "rom", "romain-", "rom-maj", "lien", "ill", "lien web") and params:
                rendu = params[0] if bas not in ("souverain2", "souverain3", "souverain") else " ".join(params[:2])
            elif bas in ("ier", "iie", "iiie", "ive", "ve", "vie", "viie", "viiie", "ixe", "xe", "xie", "xiie"):
                rendu = nom.upper()[:-1] + "e" if bas != "ier" else "Ier"
            elif bas in ("abréviation", "abr", "sigle") and len(params) >= 1:
                rendu = params[0]
            elif re.fullmatch(r"[ivxlc]+e?", bas) and len(bas) <= 6:
                rendu = nom.upper()
            else:
                rendu = ""
            code.replace(t, rendu)
        except ValueError:
            pass
    s = code.strip_code(normalize=True, collapse=True)
    s = re.sub(r"\[\[(?:Fichier|File|Image):[^\]]*\]\]", "", s)
    s = re.sub(r"'{2,}", "", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s+([,.;])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def liens(wikitexte: str) -> list[str]:
    sortie = []
    for l in mwparserfromhell.parse(wikitexte).filter_wikilinks():
        t = str(l.title).split("#")[0].strip()
        if t and not re.match(r"(?i)(fichier|file|image|catégorie|category):", t):
            sortie.append(t[0].upper() + t[1:])
    return sortie


# ================================================================ pages mensuelles et annuelles (FR)

DATE_TPL = re.compile(r"\{\{\s*(?:date\+?|date-)\s*\|\s*(1er|\d{1,2})\s*(?:\||\s)\s*([^|}\s]+)", re.I)
UN_TPL = re.compile(r"\{\{\s*1er\s+(\w+)\s*\}\}", re.I)
LIEN_JOUR = re.compile(r"^\*\s*'*\[\[(1er|\d{1,2})\s+(\w+)(?:\s+\d{4})?(?:\|[^\]]*)?\]\]")
PLAIN = re.compile(r"^\*\s*'*(1er|\d{1,2})\s+([^\s:,]+)\s*(?:\d{4}\s*)?[:,]")
STOP = re.compile(r"naissance|décès|deces|voir aussi|notes|références|references|liens externes|bibliographie|"
                  r"articles connexes|fondations|œuvres|oeuvres|prix nobel|mort|records", re.I)
ACTIVE = re.compile(r"vénements|vènements|faits marquants|actualités|chronologie|politique|économie|culture|"
                    r"sport|société|science|monde|france|international|^[a-zéû]+$", re.I)
PREFIXE_DATE = re.compile(r"^(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?(?:\d{1,2}|1er)"
                          r"(?:\s+[a-zéû]+)?(?:\s+\d{4})?(?:\s*(?:[-–]|et|au)\s*(?:\d{1,2}|1er)(?:\s+[a-zéû]+)?)?\s*:\s*", re.I)


def jour_de(ligne: str):
    m = DATE_TPL.search(ligne[:90])
    if m:
        return m.group(1), m.group(2)
    m = UN_TPL.search(ligne[:40])
    if m:
        return "1er", m.group(1)
    m = LIEN_JOUR.match(ligne) or PLAIN.match(ligne)
    if m:
        return m.group(1), m.group(2)
    return None


def date_titre(titre: str, annee: int) -> date | None:
    """« Lundi {{date|1er mai 2000}} », « Vendredi {{1er juin}} [[2001]] », « Mercredi 4 août 2004 » → date."""
    t = re.sub(r"\{\{\s*1er\s*(\w*)\s*\}\}", r"1er \1", titre)
    t = re.sub(r"\{\{\s*date[+-]?\s*\|([^}]*)\}\}", lambda m: m.group(1).replace("|", " "), t, flags=re.I)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    m = re.search(r"\b(1er|\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", t)
    if not m:
        return None
    mo = num_mois(m.group(2))
    if not mo:
        return None
    try:
        return date(int(m.group(3) or annee), mo, jour_num(m.group(1)))
    except ValueError:
        return None


def rubrique_et_reste(t: str) -> tuple[str, str]:
    """« Royaume-Uni : la reine… » → (« Royaume-Uni », « la reine… »). Rubrique courte, sans verbe apparent."""
    m = re.match(r"^([A-ZÉÈÀÂÎÔÛÇ][^:;.]{1,34}?)\s*:\s+(.{8,})$", t)
    if m and not re.search(r"\b(est|sont|a|ont|devient|signe|annonce)\b", m.group(1)):
        reste = m.group(2)
        return m.group(1).strip(), reste[0].upper() + reste[1:]
    return "", t


def evenements_fr(wikitexte: str, annee: int, source: str) -> list[dict]:
    """Événements datés d'une page mensuelle ou annuelle de Wikipédia FR (hors naissances, décès, etc.)."""
    out, courant, du_titre, actif = [], None, None, False
    for ligne in wikitexte.split("\n"):
        mt = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", ligne)
        if mt:
            niveau, titre = len(mt.group(1)), mt.group(2)
            if STOP.search(titre) and not date_titre(titre, annee):
                actif, du_titre, courant = False, None, None
                continue
            d = date_titre(titre, annee)
            if d is not None and d.year == annee:
                actif, du_titre, courant = True, d, d
            else:
                du_titre = courant = None
                if ACTIVE.search(titre) or niveau >= 3:
                    actif = actif or bool(ACTIVE.search(titre))
            continue
        if not actif or not ligne.startswith("*"):
            continue
        sous = ligne.startswith("**")
        j = jour_de("*" + ligne.lstrip("*")) if not sous else None
        if j:
            mo = num_mois(j[1])
            if mo:
                try:
                    courant = date(annee, mo, jour_num(j[0]))
                except ValueError:
                    courant = None
            else:
                courant = du_titre
        elif not sous:
            courant = du_titre
        if courant is None:
            continue
        brut = ligne.lstrip("*").strip()
        t = PREFIXE_DATE.sub("", texte(brut)).strip(" :–-")
        t = re.sub(r"^(?:1er|\d{1,2})\s+[a-zéû]+(?:\s+\d{4})?\s*,\s*", "", t)
        if len(t) < 12:
            continue
        rub, reste = rubrique_et_reste(t)
        reste = reste[0].upper() + reste[1:]
        out.append({"date": courant.isoformat(), "texte": reste, "rubrique": rub,
                    "liens": [l for l in liens(brut) if not re.fullmatch(r"\d{1,4}|(1er|\d{1,2}) \w+( \d{4})?", l)],
                    "source": source})
    return dedoublonner(out)


def dedoublonner(evts: list[dict]) -> list[dict]:
    vus, sortie = set(), []
    for e in evts:
        k = (e["date"], sans_accents(e["texte"])[:50])
        if k not in vus:
            vus.add(k)
            sortie.append(e)
    return sortie


# ================================================================ pages « jour mois » : naissances et décès

def personnes_du_jour(wikitexte: str, section: str) -> list[dict]:
    """[{annee, titre, nom}] des sections Naissances ou Décès d'une page « 7 juillet »."""
    m = re.search(r"^==\s*" + section + r"\s*==\s*$(.*?)(?=^==[^=]|\Z)", wikitexte, re.S | re.M)
    if not m:
        return []
    out, annee = [], None
    for ligne in m.group(1).split("\n"):
        ma = re.match(r"^\*\s*'*\[?\[?(\d{3,4})\]?\]?\s*(?:av\. J\.-C\.)?\s*:?", ligne)
        if ma and ligne.startswith("*") and not ligne.startswith("**"):
            annee = int(ma.group(1))
        if not ligne.startswith("*") or annee is None:
            continue
        reste = re.sub(r"^\*+\s*'*\[?\[?\d{3,4}\]?\]?\s*:?", "", ligne)
        for l in mwparserfromhell.parse(reste).filter_wikilinks():
            titre = str(l.title).split("#")[0].strip()
            if not titre or re.fullmatch(r"\d{3,4}", titre) or re.match(r"(?i)(fichier|image|file):", titre):
                continue
            nom = texte(str(l.text)) if l.text else titre
            nom = re.sub(r"\s*\(.*\)$", "", nom)
            out.append({"annee": annee, "titre": titre[0].upper() + titre[1:], "nom": nom})
            break
    return out


# ================================================================ Wikipédia EN : « February_1964 »

TITRE_EN = re.compile(r"^==\s*(?:\[\[)?([A-Z][a-z]+)\s+(\d{1,2})(?:\]\])?,?\s*(?:\[\[)?(\d{4})(?:\]\])?\s*(?:\(([A-Za-z]+)\))?\s*==\s*$")


def evenements_en(wikitexte: str, annee: int) -> list[dict]:
    """Événements d'une page mensuelle anglaise. Texte en anglais : proposé à la relecture, jamais choisi seul."""
    out, courant = [], None
    for ligne in wikitexte.split("\n"):
        mt = TITRE_EN.match(ligne)
        if mt:
            mo = num_mois(mt.group(1))
            try:
                courant = date(int(mt.group(3)), mo, int(mt.group(2))) if mo else None
            except ValueError:
                courant = None
            continue
        if re.match(r"^==[^=]", ligne):
            courant = None
            continue
        if courant is None or not ligne.startswith("*") or ligne.startswith("**"):
            continue
        brut = ligne.lstrip("*").strip()
        t = texte(brut)
        if re.match(r"(?i)^(born|died)\s*:", t) or len(t) < 15:
            continue
        out.append({"date": courant.isoformat(), "texte": t, "rubrique": "", "liens": liens(brut),
                    "source": "wikipedia-en", "langue": "en"})
    return out


# ================================================================ Larousse : Journaux de l'année

LI = re.compile(r'<li[^>]*\bdate="(\d{2})/(\d{2})/(\d{4})"[^>]*>(.*?)</li>', re.S)


def _propre(fragment: str) -> str:
    f = re.sub(r"<sup>(.*?)</sup>", r"\1", fragment, flags=re.S)
    f = re.sub(r"<[^>]+>", "", f)
    return re.sub(r"\s+", " ", html_mod.unescape(f)).strip()


def evenements_larousse(page: str) -> list[dict]:
    out = []
    for jj, mm, aaaa, corps in LI.findall(page):
        try:
            d = date(int(aaaa), int(mm), int(jj))
        except ValueError:
            continue
        mc = re.search(r'<div class="complet">(.*?)</div>', corps, re.S) or re.search(r'<div class="short">(.*?)</div>', corps, re.S)
        if not mc:
            continue
        complet = mc.group(1)
        rub = ""
        ma = re.search(r'<div class="adresse">(.*?)</div>', corps, re.S)
        if ma:
            rub = _propre(ma.group(1))
        else:
            mb = re.match(r"\s*<b>(.*?)</b>", complet, re.S)
            if mb and _propre(mb.group(1)).endswith((".", ":")):
                rub = _propre(mb.group(1)).rstrip(".: ")
                complet = complet[mb.end():]
        t = _propre(complet)
        if len(t) < 12:
            continue
        out.append({"date": d.isoformat(), "texte": t[0].upper() + t[1:], "rubrique": rub, "liens": [],
                    "source": "larousse"})
    return out
