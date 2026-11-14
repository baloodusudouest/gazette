"""Banc d'essai des règles de la Gazette sur des dates tirées au hasard.

Lit Wikipédia FR (pages « <mois> <année> », « <année> en France », « <jour> <mois> ») en wikitext brut
(index.php?action=raw), et Wikidata (SPARQL) pour classer les personnes par notoriété (nombre de liens
interlangues). Applique les règles du dossier (une, brèves, semaine, chronologie, nés, disparus,
exclusions) et écrit un rapport Markdown.

Usage : python3 banc.py [--n 30] [--graine 14112026] [--cache DOSSIER] [--rapport FICHIER]
Aucune donnée personnelle : seules des dates tirées au hasard.
"""
import argparse
import datetime as dt
import json
import pathlib
import random
import re
import time
import urllib.parse

import mwparserfromhell
import requests

UA = "GazetteBanc/0.1 (https://github.com/baloodusudouest/gazette; contact via GitHub)"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]
# Exclusions : mots qui signalent un drame (racines, comparées sans accents ni casse).
DRAMES = ["attentat", "meurt", "mort", "morts", "tue ", "tues", "tuee", "tuees", "victime", "massacre",
          "assassin", "catastrophe", "seisme", "tremblement de terre", "explosion", "crash", "s'ecrase",
          "accident", "naufrage", "incendie", "otage", "fusille", "execute", "bombard", "genocide",
          "epidemie", "inondation", "deces", "suicide", "emeute", "pendu", "noye", "disparait",
          "abattu", "guerre", "combat", "blesse", "attaque", "repression", "terroris"]

session = requests.Session()
session.headers["User-Agent"] = UA


def sans_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def lire(titre, cache):
    f = cache / (re.sub(r"[^\w-]", "_", titre) + ".txt")
    if f.exists():
        return f.read_text()
    url = "https://fr.wikipedia.org/w/index.php?title=" + urllib.parse.quote(titre.replace(" ", "_")) + "&action=raw"
    for essai in range(6):
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            f.write_text(r.text)
            time.sleep(1.5)
            return r.text
        if r.status_code == 404:
            f.write_text("")
            return ""
        time.sleep(15 * (essai + 1))
    raise RuntimeError(f"{titre}: {r.status_code}")


def sparql_notoriete(titres, cache):
    if not titres:
        return {}
    import hashlib
    cle = cache / ("wd_" + hashlib.sha1("|".join(sorted(titres)).encode()).hexdigest()[:16] + ".json")
    if cle.exists():
        return json.loads(cle.read_text())
    connus = {}
    for f in cache.glob("wd_*.json"):
        connus.update(json.loads(f.read_text()))
    if connus and sum(t in connus for t in titres) >= 0.8 * len(titres):
        return {t: connus[t] for t in titres if t in connus}
    res = {}
    for k in range(0, len(titres), 120):
        lot = titres[k:k + 120]
        vals = " ".join('"' + t.replace('\\', '').replace('"', '\\"') + '"@fr' for t in lot)
        q = ("SELECT ?t ?n WHERE { VALUES ?t {" + vals + "} ?a schema:name ?t; schema:isPartOf "
             "<https://fr.wikipedia.org/>; schema:about ?i. ?i wikibase:sitelinks ?n. }")
        for essai in range(3):
            try:
                r = session.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"},
                                 headers={"Accept": "application/sparql-results+json"}, timeout=40)
            except requests.RequestException:
                time.sleep(5)
                continue
            if r.status_code == 200:
                res.update({b["t"]["value"]: int(b["n"]["value"]) for b in r.json()["results"]["bindings"]})
                break
            time.sleep(8 * (essai + 1))
        time.sleep(1)
    cle.write_text(json.dumps(res, ensure_ascii=False))
    return res


def texte(wikitexte):
    w = re.sub(r"<ref[^>]*/>", "", wikitexte)
    w = re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    code = mwparserfromhell.parse(w)
    for t in code.filter_templates(recursive=False):
        nom = str(t.name).strip().lower()
        try:
            if nom in ("date+", "date-") and t.params:
                code.replace(t, str(t.params[0].value))
            elif nom == "date" and len(t.params) >= 2:
                code.replace(t, " ".join(str(p.value) for p in t.params[:3]))
            elif re.fullmatch(r"1er \w+", nom):
                code.replace(t, nom)
            elif nom in ("er", "1er"):
                code.replace(t, "er")
            elif nom in ("formatnum", "formatnum:") and t.params:
                code.replace(t, str(t.params[0].value))
            elif nom in ("s-", "s") and t.params:
                code.replace(t, str(t.params[0].value) + "e siècle")
            elif nom.startswith("formatnum:"):
                code.replace(t, nom.split(":", 1)[1])
            elif nom in ("ier", "iie", "iiie"):
                code.replace(t, nom.upper()[:-1] if nom != "ier" else "Ier")
            else:
                code.replace(t, "")
        except ValueError:
            pass
    s = code.strip_code(normalize=True, collapse=True)
    s = re.sub(r"\[\[(?:Fichier|File|Image):[^\]]*\]\]", "", s)
    return re.sub(r"\s+", " ", s).strip()


DATE_TPL = re.compile(r"\{\{\s*(?:date\+?|date-)\s*\|\s*(1er|\d{1,2})\s+(\w+)", re.I)
UN_TPL = re.compile(r"\{\{\s*1er\s+(\w+)\s*\}\}", re.I)
LIEN_JOUR = re.compile(r"^\*\s*\[\[(1er|\d{1,2})\s+(\w+)(?:\|[^\]]*)?\]\]")
PLAIN = re.compile(r"^\*\s*(1er|\d{1,2})\s+(\w+)\s*:")


def jour_de(ligne):
    for rx in (DATE_TPL, ):
        m = rx.search(ligne[:80])
        if m:
            return m.group(1), m.group(2)
    m = UN_TPL.search(ligne[:40])
    if m:
        return "1er", m.group(1)
    m = LIEN_JOUR.match(ligne) or PLAIN.match(ligne)
    if m:
        return m.group(1), m.group(2)
    return None


STOP = re.compile(r"naissance|décès|deces|voir aussi|notes|références|references|liens externes|bibliographie|"
                  r"articles connexes|fondations", re.I)


def date_titre(titre, annee):
    """« Lundi {{date|1er mai 2000}} », « Vendredi {{1er juin}} [[2001]] », « Mercredi 4 août 2004 » → date."""
    t = re.sub(r"\{\{\s*1er\s*(\w*)\s*\}\}", r"1er \1", titre)
    t = re.sub(r"\{\{\s*date[+-]?\s*\|([^}]*)\}\}", lambda m: m.group(1).replace("|", " "), t, flags=re.I)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    m = re.search(r"\b(1er|\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", t)
    if not m:
        return None
    mois_n = [sans_accents(x) for x in MOIS]
    mm = sans_accents(m.group(2))
    if mm not in mois_n:
        return None
    try:
        return dt.date(int(m.group(3) or annee), mois_n.index(mm) + 1, 1 if m.group(1) == "1er" else int(m.group(1)))
    except ValueError:
        return None


def evenements(wikitexte, annee):
    """Liste (date, texte, liens) des puces datées hors des sections Naissances, Décès, etc.
    Gère les deux formes de Wikipédia FR : puces datées ({{date+|…}}) et sections par jour."""
    out, courant, du_titre, actif = [], None, None, False
    mois_n = [sans_accents(x) for x in MOIS]
    for ligne in wikitexte.split("\n"):
        mt = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", ligne)
        if mt:
            titre = mt.group(2)
            if STOP.search(titre):
                actif, du_titre, courant = False, None, None
                continue
            d = date_titre(titre, annee)
            if d is not None and d.year == annee:
                actif, du_titre, courant = True, d, d
            else:
                if re.search(r"vénements|vènements|faits marquants|actualités|chronologie", titre, re.I):
                    actif = True
                du_titre = courant = None
            continue
        if not actif or not ligne.startswith("*"):
            continue
        sous = ligne.startswith("**")
        j = jour_de("*" + ligne.lstrip("*")) if not sous else None
        if j:
            jj, mm = j
            mm = sans_accents(mm)
            if mm in mois_n:
                try:
                    courant = dt.date(annee, mois_n.index(mm) + 1, 1 if jj == "1er" else int(jj))
                except ValueError:
                    courant = None
            else:
                courant = du_titre
        elif not sous:
            courant = du_titre
        if courant is None:
            continue
        brut = ligne.lstrip("*").strip()
        liens = [str(l.title).split("#")[0].strip() for l in mwparserfromhell.parse(brut).filter_wikilinks()]
        t = texte(brut)
        t = re.sub(r"^(?:\d{1,2}|1er)(?:\s+\w+)?(?:\s*(?:[-–]|et|au)\s*(?:\d{1,2}|1er)(?:\s+\w+)?)?\s*:\s*", "", t)
        if len(t) < 8:
            continue
        out.append((courant, t, liens))
    return out


def personnes(wikitexte, section):
    m = re.search(r"^==\s*" + section + r"\s*==\s*$(.*?)(?=^==[^=])", wikitexte, re.S | re.M)
    if not m:
        return []
    out = []
    annee = None
    for ligne in m.group(1).split("\n"):
        ma = re.match(r"^\*\s*\[?\[?(\d{3,4})\]?\]?\s*:", ligne)
        if ma:
            annee = int(ma.group(1))
        if not ligne.startswith("*") or annee is None:
            continue
        for l in mwparserfromhell.parse(ligne).filter_wikilinks():
            titre = str(l.title).split("#")[0].strip()
            if re.fullmatch(r"\d{3,4}", titre) or titre.lower().startswith(("fichier", "image")):
                continue
            nom = str(l.text).strip() if l.text else titre
            out.append((annee, titre, nom))
            break
    return out


def drame(t):
    s = " " + sans_accents(t) + " "
    return [d for d in DRAMES if d in s]


def raccourcir(t, maxi=170):
    phrase = re.split(r"(?<=[a-zé\)»])\.\s", t)[0]
    phrase = phrase[0].upper() + phrase[1:] if phrase else phrase
    if len(phrase) <= maxi:
        return phrase, False
    coupe = phrase[:maxi].rsplit(" ", 1)[0]
    return coupe + "…", True


def banc_date(d, cache):
    mois_page = f"{MOIS[d.month - 1].capitalize()} {d.year}"
    evts = evenements(lire(mois_page, cache), d.year) + evenements(lire(f"{d.year} en France", cache), d.year)
    vus, uniq = set(), []
    for e in evts:
        k = (e[0], e[1][:60])
        if k not in vus:
            vus.add(k)
            uniq.append(e)
    jour = [e for e in uniq if e[0] == d]
    veille = [e for e in uniq if e[0] == d - dt.timedelta(days=1)]
    semaine = [e for e in uniq if d - dt.timedelta(days=6) <= e[0] <= d]
    annee_fr = evenements(lire(f"{d.year} en France", cache), d.year)
    page_annee = evenements(lire(str(d.year), cache), d.year)
    jour_page = lire(f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]}", cache)
    nes, morts = personnes(jour_page, "Naissances"), personnes(jour_page, "Décès")
    noto = sparql_notoriete(list({t for _, t, _ in nes + morts})[:400], cache)

    # Une : jour, sinon veille, sinon semaine ; drames exclus du gros titre ; classement par notoriété des liens.
    def score(e):
        return max([noto.get(l, 0) for l in e[2]] + [0])
    for nom_src, lot in (("jour", jour), ("veille", veille), ("semaine", semaine)):
        propres = [e for e in lot if not drame(e[1])]
        if propres:
            source_une = nom_src
            break
    else:
        source_une, propres = "vide", []
    # La notoriété n'est connue que pour les personnes ; on classe les événements sur leurs liens personnes,
    # puis par longueur (une entrée détaillée est souvent un événement majeur).
    propres.sort(key=lambda e: (score(e), len(e[1])), reverse=True)
    une = propres[0] if propres else None
    candidates_breves = [e for e in semaine if e is not une]
    breves_ok = [e for e in candidates_breves if not drame(e[1])]
    breves_drame = [e for e in candidates_breves if drame(e[1])]
    nes_tri = sorted({t: (a, t, n) for a, t, n in nes if a <= d.year}.values(), key=lambda x: -noto.get(x[1], 0))[:5]
    morts_tri = sorted({t: (a, t, n) for a, t, n in morts}.values(), key=lambda x: -noto.get(x[1], 0))[:4]
    une_txt, une_coupee = raccourcir(une[1]) if une else ("", False)
    return {
        "date": d.isoformat(), "jour_sem": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"][d.weekday()],
        "n_jour": len(jour), "n_veille": len(veille), "n_semaine": len(semaine),
        "n_drames_semaine": sum(1 for e in semaine if drame(e[1])),
        "source_une": source_une, "une": une_txt, "une_coupee": une_coupee,
        "une_date": une[0].isoformat() if une else "",
        "breves_ok": len(breves_ok), "breves_drame": len(breves_drame),
        "breves_exemples": [raccourcir(e[1], 110)[0] for e in breves_ok[:3]],
        "drames_vus": [(raccourcir(e[1], 90)[0], drame(e[1])[:3]) for e in breves_drame[:3]],
        "n_annee_fr": len(annee_fr), "n_page_annee": len(page_annee),
        "nes": [f"{n} ({a})" for a, t, n in nes_tri], "morts": [f"{n} ({a})" for a, t, n in morts_tri],
        "n_nes": len(nes), "n_morts": len(morts), "noto_trouvee": len(noto),
    }


def rapport(res, chemin):
    L = ["# Banc d'essai — Gazette", "",
         f"Exécuté le {dt.date.today().isoformat()} sur {len(res)} dates tirées au hasard entre 1940 et 2010 "
         "(graine fixe). Sources : Wikipédia FR (wikitext brut) et Wikidata (notoriété). "
         "Règles : celles du dossier v0.1, sans IA.", ""]
    n = len(res)
    def compte(f):
        return sum(1 for r in res if f(r))
    L += ["## Synthèse", "",
          "| Mesure | Résultat |", "|---|---|",
          f"| Une trouvée au jour exact | {compte(lambda r: r['source_une'] == 'jour')} / {n} |",
          f"| Une repliée sur la veille | {compte(lambda r: r['source_une'] == 'veille')} / {n} |",
          f"| Une repliée sur la semaine | {compte(lambda r: r['source_une'] == 'semaine')} / {n} |",
          f"| Une vide (rien dans la semaine) | {compte(lambda r: r['source_une'] == 'vide')} / {n} |",
          f"| Gros titre coupé (> 170 caractères) | {compte(lambda r: r['une_coupee'])} / {n} |",
          f"| Au moins 4 brèves propres dans la semaine | {compte(lambda r: r['breves_ok'] >= 4)} / {n} |",
          f"| Semaines avec au moins un drame écarté | {compte(lambda r: r['n_drames_semaine'] > 0)} / {n} |",
          f"| Chronologie : ≥ 6 événements datés dans « année en France » | {compte(lambda r: r['n_annee_fr'] >= 6)} / {n} |",
          f"| Nés : ≥ 5 personnes | {compte(lambda r: len(r['nes']) >= 5)} / {n} |",
          f"| Disparus : ≥ 4 personnes | {compte(lambda r: len(r['morts']) >= 4)} / {n} |",
          ""]
    for dec in range(1940, 2020, 10):
        lot = [r for r in res if dec <= int(r["date"][:4]) < dec + 10]
        if lot:
            L.append(f"- Années {dec} : {len(lot)} dates, événements datés dans la semaine en moyenne "
                     f"{sum(r['n_semaine'] for r in lot) / len(lot):.1f}, au jour exact {sum(r['n_jour'] for r in lot) / len(lot):.1f}.")
    L += ["", "## Détail par date", ""]
    for r in res:
        L += [f"### {r['jour_sem'].capitalize()} {r['date']}", "",
              f"- Événements : jour {r['n_jour']}, veille {r['n_veille']}, semaine {r['n_semaine']} "
              f"(dont {r['n_drames_semaine']} écartés comme drames) ; « année en France » {r['n_annee_fr']}, page de l'année {r['n_page_annee']}.",
              f"- **Une** ({r['source_une']}{', ' + r['une_date'] if r['une_date'] else ''}) : {r['une'] or '—'}" + (" ✂️" if r['une_coupee'] else ""),
              f"- Brèves propres : {r['breves_ok']}" + (" — " + " · ".join(r['breves_exemples']) if r['breves_exemples'] else ""),
              ]
        if r["drames_vus"]:
            L.append("- Écartés : " + " · ".join(f"{t} [{', '.join(m)}]" for t, m in r["drames_vus"]))
        L += [f"- Nés : {', '.join(r['nes']) or '—'}", f"- Disparus : {', '.join(r['morts']) or '—'}", ""]
    pathlib.Path(chemin).write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--graine", type=int, default=14112026)
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--rapport", default="rapport.md")
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    cache.mkdir(exist_ok=True)
    rnd = random.Random(a.graine)
    debut, fin = dt.date(1940, 1, 1), dt.date(2010, 12, 31)
    dates = sorted(debut + dt.timedelta(days=rnd.randrange((fin - debut).days + 1)) for _ in range(a.n))
    res = []
    for d in dates:
        try:
            res.append(banc_date(d, cache))
            print("ok", d, res[-1]["source_une"], res[-1]["n_semaine"], flush=True)
        except Exception as ex:  # noqa: BLE001
            print("ERREUR", d, ex, flush=True)
    (cache / "resultats.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    rapport(res, a.rapport)


if __name__ == "__main__":
    main()
