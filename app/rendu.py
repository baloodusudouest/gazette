"""Mise en page du livret : HTML (gabarit du prototype du 14/11/2026) puis PDF par Chromium (Playwright).

Deux sorties : « imposé » (une feuille A4 paysage, recto p4 | p1, verso p2 | p3, recto-verso bord court, plier)
et « lecture » (4 pages A5 dans l'ordre). Polices embarquées dans le HTML (OFL : UnifrakturMaguntia,
Playfair Display, Source Serif 4), donc le même document sert à l'aperçu et au PDF."""
from __future__ import annotations

import base64
import functools
import html
from datetime import date
from pathlib import Path

from . import journal
from .regles import MOIS, MOIS_COURT, PORTEES, jour_long, jour_mois

POLICES = Path(__file__).parent / "polices"
e = html.escape

FICHIERS_POLICES = [
    ("Playfair", "playfair-display-latin-700-normal.woff2", 700, "normal"),
    ("Playfair", "playfair-display-latin-900-normal.woff2", 900, "normal"),
    ("Playfair", "playfair-display-latin-ext-700-normal.woff2", 700, "normal"),
    ("Playfair", "playfair-display-latin-ext-900-normal.woff2", 900, "normal"),
    ("Serif", "source-serif-4-latin-400-normal.woff2", 400, "normal"),
    ("Serif", "source-serif-4-latin-600-normal.woff2", 600, "normal"),
    ("Serif", "source-serif-4-latin-400-italic.woff2", 400, "italic"),
    ("Serif", "source-serif-4-latin-ext-400-normal.woff2", 400, "normal"),
    ("Serif", "source-serif-4-latin-ext-600-normal.woff2", 600, "normal"),
    ("Serif", "source-serif-4-latin-ext-400-italic.woff2", 400, "italic"),
    ("Fraktur", "unifrakturmaguntia-latin-400-normal.woff2", 400, "normal"),
]


LATIN = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,"
         "U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")
LATIN_EXT = ("U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,"
             "U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF")


@functools.lru_cache(maxsize=1)
def font_face() -> str:
    regles = []
    for fam, nom, poids, style in FICHIERS_POLICES:
        f = POLICES / nom
        if not f.is_file():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        regles.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');"
                      f"font-weight:{poids};font-style:{style};unicode-range:{LATIN_EXT if '-ext-' in nom else LATIN}}}")
    return "".join(regles)


def polices_presentes() -> bool:
    return all((POLICES / nom).is_file() for _, nom, _, _ in FICHIERS_POLICES)


CSS = """


*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:'Serif',Georgia,serif;color:#161616;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.feuille{width:297mm;height:210mm;display:flex;page-break-after:always;overflow:hidden}
.feuille:last-child{page-break-after:auto}
.page{width:148.5mm;height:210mm;padding:10mm 10.5mm;background:#F7F3EA;display:flex;flex-direction:column;gap:3.4mm;overflow:hidden}
.page + .page{border-left:0.2mm dashed #cfc6b3}
p,h1,h2,h3{margin:0}
.ent{display:flex;justify-content:space-between;align-items:baseline;border-bottom:0.3mm solid #161616;padding-bottom:1.5mm}
.ent .t{font-family:'Fraktur',serif;font-size:13pt}
.ent .r{font-size:8.5pt;letter-spacing:.08em;text-transform:uppercase}
.manchette{display:flex;justify-content:space-between;font-size:8.5pt;letter-spacing:.04em;text-transform:uppercase;border-bottom:0.3mm solid #161616;padding-bottom:1.5mm}
.titre{display:flex;flex-direction:column;align-items:center;gap:1.2mm;border-bottom:0.9mm double #161616;padding-bottom:2.4mm}
.titre h1{font-family:'Fraktur',serif;font-weight:400;font-size:28pt;line-height:1;text-align:center}
.titre p{font-size:8.5pt;font-style:italic}
.surtitre{font-size:9pt;letter-spacing:.18em;text-transform:uppercase;color:var(--a)}
.nom{display:flex;flex-direction:column;align-items:center;gap:.5mm;padding:.5mm 0 1mm}
.nom .n{font-family:'Playfair',serif;font-weight:900;font-size:32pt;line-height:1.02;text-align:center}
.filet{border-top:0.3mm solid #161616;padding-top:2.8mm}
.ouv{display:flex;gap:4mm;align-items:stretch}
.ouv .txt{flex:1 1 0;display:flex;flex-direction:column;gap:2mm}
h2.gros{font-family:'Playfair',serif;font-weight:900;font-size:calc(21pt*var(--k,1));line-height:1.08;text-wrap:balance}
.chapo{font-size:calc(11pt*var(--k,1));line-height:1.35;text-wrap:pretty}
.encart{flex:0 0 33mm;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:1mm;border:0.3mm solid #161616;padding:2.5mm 1.5mm;text-align:center}
.encart .k{font-size:8.5pt;text-transform:uppercase;letter-spacing:.08em}
.encart .v{font-family:'Playfair',serif;font-weight:900;font-size:28pt;line-height:1;color:var(--a)}
.encart .l{font-size:9pt;line-height:1.25}
.breves{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:5mm;row-gap:3mm;flex:1 1 auto;align-content:start}
.breve h3{font-family:'Playfair',serif;font-weight:700;font-size:calc(12pt*var(--k,1));line-height:1.15;margin-bottom:1mm}
.breve p{font-size:calc(10.5pt*var(--k,1));line-height:1.38}
.pied{display:flex;justify-content:space-between;font-size:8.5pt;border-top:0.3mm solid #161616;padding-top:1.5mm;margin-top:auto}
h2.sec{font-family:'Playfair',serif;font-weight:900;font-size:20pt;line-height:1.08;text-wrap:balance}
.liste{flex:1 1 auto;display:flex;flex-direction:column;border-top:0.9mm double #161616}
.item{display:flex;gap:4mm;padding:3.6mm 0;border-bottom:0.3mm solid #161616}
.item:last-child{border-bottom:0}
.item .d{flex:0 0 17mm;display:flex;flex-direction:column;align-items:center}
.item .d b{font-family:'Playfair',serif;font-weight:900;font-size:19pt;line-height:1;color:var(--a)}
.item .d span{font-size:8.5pt;text-transform:uppercase}
.item .lieu{flex:0 0 22mm;display:flex;flex-direction:column;gap:.5mm}
.item .lieu b{font-size:8.5pt;text-transform:uppercase;letter-spacing:.08em;color:var(--a);font-weight:600}
.item .lieu span{font-size:8.5pt;color:#555}
.item h3{font-family:'Playfair',serif;font-weight:700;font-size:calc(12.5pt*var(--k,1));line-height:1.15;margin-bottom:.8mm}
.item p{font-size:calc(11pt*var(--k,1));line-height:1.38}
.note{font-size:8.5pt;font-style:italic;line-height:1.35}
.chrono{display:flex;flex-direction:column;border-left:0.5mm solid #161616;margin-left:1.6mm}
.ev{display:flex;align-items:baseline;gap:2.6mm;padding:1.45mm 0}
.ev .pt{flex:0 0 auto;width:2.6mm;height:2.6mm;border-radius:50%;background:#161616;margin-left:-1.55mm;align-self:center}
.ev .q{flex:0 0 15mm;font-size:8.5pt;font-weight:600;text-transform:uppercase}
.ev .x{font-size:calc(10.5pt*var(--k,1));line-height:1.28}
.ev.moi .pt{width:3.6mm;height:3.6mm;margin-left:-2.05mm;background:var(--a)}
.ev.moi .q,.ev.moi .x{color:var(--a)}
.ev.moi .x{font-family:'Playfair',serif;font-weight:700;font-size:calc(11pt*var(--k,1))}
.duo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:5mm}
.duo .lab{font-size:9pt;letter-spacing:.18em;text-transform:uppercase;color:var(--a);margin-bottom:1mm}
.duo p{font-size:calc(10.5pt*var(--k,1));line-height:1.4}
.duo h3{font-family:'Playfair',serif;font-weight:700;font-size:calc(12pt*var(--k,1));margin-bottom:1.2mm}
.duo .pers{font-size:calc(10.5pt*var(--k,1));line-height:1.45}
.mot{flex:1 1 auto;display:flex;flex-direction:column;gap:4mm;justify-content:flex-start}
.mot p{font-size:calc(13.5pt*var(--k,1));line-height:1.55;text-wrap:pretty}
.mot p.lettrine::first-letter{font-family:'Playfair',serif;font-weight:900;font-size:46pt;line-height:.8;float:left;padding:1.4mm 1.8mm 0 0;color:var(--a)}
.mot .sig{font-style:italic;text-align:right;font-size:calc(13.5pt*var(--k,1));margin-top:2mm}
.colophon{border:0.3mm solid #161616;padding:3mm;display:flex;flex-direction:column;align-items:center;gap:1mm;text-align:center}
.colophon .t{font-family:'Fraktur',serif;font-size:15pt}
.colophon p{font-size:9pt;line-height:1.35}
.orn{text-align:center;letter-spacing:.6em;color:var(--a);font-size:10pt}
"""
CSS += """
.lecture body{background:#e9e4d8}
.lecture .feuille{width:148.5mm;height:210mm;page-break-after:always}
.lecture .page + .page{border-left:0}
.ecran body{background:#2a2521;padding:6mm;display:flex;flex-direction:column;gap:6mm;align-items:center}
.ecran .feuille{box-shadow:0 2mm 6mm rgba(0,0,0,.35)}
.portee{font-size:8.5pt;letter-spacing:.14em;text-transform:uppercase;color:var(--a)}
.vide{font-style:italic;color:#8a8273}
.chapo.seul{font-size:calc(12.5pt*var(--k,1));line-height:1.38}
.chapo.seul::first-line{font-weight:600}
"""


def _prenom(personne: dict) -> str:
    return (personne.get("prenom") or personne.get("nom", "").split(" ")[0] or "").strip()


def _sources_txt(sources: list[str]) -> str:
    noms = []
    if any(s.startswith("wikipedia") for s in sources):
        noms.append("Wikipédia (CC BY-SA 4.0)")
    if "wikidata" in sources:
        noms.append("Wikidata")
    if "larousse" in sources:
        noms.append("Larousse, Journaux de l'année (d'après)")
    if "top5" in sources:
        noms.append("box-office, Billboard et Nielsen (top 5 de la maison)")
    return " · ".join(noms) or "chronologies publiques"


def _paragraphes(t: str) -> list[str]:
    return [p.strip() for p in (t or "").replace("\r", "").split("\n\n") if p.strip()] or \
           [l.strip() for l in (t or "").split("\n") if l.strip()]


def page1(g: dict) -> str:
    c, une = g["contenu"], g["contenu"].get("une", {})
    breves = "".join(f'<div class="breve" data-bloc="breve:{i}">' + (f'<h3>{e(b["titre"])}</h3>' if b.get("titre") else "") + f'<p>{e(b.get("texte", ""))}</p></div>'
                     for i, b in enumerate(c.get("breves", [])) if not b.get("masque"))
    enc = une.get("encart") or {}
    portee = PORTEES.get(une.get("portee", ""), "")
    portee_html = f'<p class="portee">{e(portee)}</p>' if portee and une.get("portee") != "jour" else ""
    gros = (f'<div class="txt" data-bloc="une">{portee_html}<h2 class="gros">{e(une.get("titre", ""))}</h2>'
            f'<p class="chapo">{e(une.get("chapo", ""))}</p></div>') if une.get("titre") else \
           (f'<div class="txt" data-bloc="une">{portee_html}<p class="chapo seul">{e(une["chapo"])}</p></div>' if une.get("chapo") else
            '<div class="txt"><p class="chapo vide">Aucun événement retenu pour la une.</p></div>')
    encart = (f'<div class="encart"><span class="k">{e(enc.get("k", ""))}</span><span class="v">{e(enc.get("v", ""))}</span>'
              f'<span class="l">{e(enc.get("l", ""))}</span></div>') if enc.get("v") else ""
    return f"""<section class="page" data-page="1">
<div class="manchette"><span>{e(g['date_longue'])}</span><span>Édition unique</span><span>Exemplaire de {e(g['prenom'])}</span></div>
<div class="titre"><h1>{e(g['titre'])}</h1>{f"<p>{e(g['sous_titre'])}</p>" if g['sous_titre'] else ""}</div>
<div class="nom"><p class="surtitre">Ce jour-là naissait</p><p class="n">{e(g['nom'])}</p></div>
<div class="ouv filet">{gros}{encart}</div>
<div class="breves filet">{breves}</div>
<div class="pied"><span>Imprimé {e(g['chez'])} · {e(g['renvoi_p2'])}, page 2</span><span>1</span></div>
</section>"""


def page2(g: dict) -> str:
    p2 = g["contenu"].get("p2", {"mode": "semaine", "items": []})
    items = []
    for i, it in enumerate(p2.get("items", [])):
        if it.get("masque"):
            continue
        try:
            dd = date.fromisoformat(it["date"])
            j, m = ("1er" if dd.day == 1 else str(dd.day)), MOIS_COURT[dd.month - 1]
        except (KeyError, ValueError):
            j, m = "", ""
        items.append(f'<div class="item" data-bloc="p2:{i}"><div class="d"><b>{e(j)}</b><span>{e(m)}</span></div>'
                     f'<div>' + (f'<h3>{e(it["titre"])}</h3>' if it.get("titre") else "") + (f'<p>{e(it["texte"])}</p>' if it.get("texte") else "") + '</div></div>')
    d = g["naissance"]
    if p2.get("mode") == "mois":
        surtitre, titre, rub = f"{MOIS[d.month - 1].capitalize()} {d.year}", "Les grands titres du mois", "Le mois"
    else:
        debut = date.fromordinal(d.toordinal() - 7)
        surtitre = f"Du {jour_mois(debut)} au {jour_mois(d)} {d.year}"
        titre, rub = "Les grands titres de la semaine", "La semaine"
    return f"""<section class="page" data-page="2">
<div class="ent"><span class="t">{e(g['titre'])}</span><span class="r">{e(rub)}</span></div>
<div><p class="surtitre">{e(surtitre)}</p><h2 class="sec">{e(titre)}</h2></div>
<div class="liste">{''.join(items) or '<p class="vide">Rien de retenu.</p>'}</div>
<p class="note">Édition préparée d'après : {e(_sources_txt(g['sources']))}.</p>
<div class="pied"><span>Exemplaire de {e(g['prenom'])}</span><span>2</span></div>
</section>"""


def page3(g: dict) -> str:
    c, d = g["contenu"], g["naissance"]
    evs, moi_pose = [], False
    chrono = [dict(x, _i=i) for i, x in enumerate(c.get("chrono", [])) if not x.get("masque")]
    for x in sorted(chrono + [{"date": d.isoformat(), "moi": True}], key=lambda x: (x.get("date", ""), bool(x.get("moi")))):
        if x.get("moi"):
            if moi_pose:
                continue
            moi_pose = True
            q = f"{'1er' if d.day == 1 else d.day} {MOIS_COURT[d.month - 1]}"
            evs.append(f'<div class="ev moi"><span class="pt"></span><span class="q">{e(q)}</span>'
                       f'<span class="x">Naissance de {e(g["prenom"])}</span></div>')
        else:
            qq = e(x.get("quand", "")).replace("1er", '1<span style="text-transform:none">er</span>')
            evs.append(f'<div class="ev" data-bloc="chrono:{x["_i"]}"><span class="pt"></span><span class="q">{qq}</span><span class="x">{e(x.get("texte", ""))}</span></div>')
    culture = ""
    if (c.get("musique") or "").strip() or (c.get("cinema") or "").strip():
        culture = (f'<div class="duo filet"><div data-bloc="musique"><p class="lab">Musique</p><p>{e(c.get("musique", ""))}</p></div>'
                   f'<div data-bloc="cinema"><p class="lab">Cinéma</p><p>{e(c.get("cinema", ""))}</p></div></div>')
    def gens(lst):
        return ", ".join(f"{p['nom']} ({p['annee']})" for p in lst if not p.get("masque"))
    return f"""<section class="page" data-page="3">
<div class="ent"><span class="t">{e(g['titre'])}</span><span class="r">L'année &amp; la culture</span></div>
<div><p class="surtitre">Chronologie</p><h2 class="sec">{d.year}, l'année de votre naissance</h2></div>
<div class="chrono">{''.join(evs)}</div>
{culture}
<div class="duo filet" style="flex:1 1 auto"><div><h3>Nés un {e(jour_mois(d))}</h3><p class="pers">{e(gens(c.get('nes', [])))}</p></div>
<div><h3>Disparus un {e(jour_mois(d))}</h3><p class="pers">{e(gens(c.get('morts', [])))}</p></div></div>
<div class="pied"><span>Exemplaire de {e(g['prenom'])}</span><span>3</span></div>
</section>"""


def page4(g: dict) -> str:
    paras = "".join(f'<p class="{"lettrine" if i == 0 else ""}">{e(t)}</p>' for i, t in enumerate(_paragraphes(g["mot"])))
    return f"""<section class="page" data-page="4">
<div class="ent"><span class="t">{e(g['titre'])}</span><span class="r">Le mot des hôtes</span></div>
<div><p class="surtitre">Édition spéciale</p><h2 class="sec">Bienvenue, {e(g['prenom'])}</h2></div>
<div class="mot filet" data-bloc="mot">{paras}<p class="sig">{e(g['signature'])}</p></div>
<p class="orn">✦ ✦ ✦</p>
<div class="colophon"><span class="t">{e(g['lieu'])}</span>{f"<p>{e(g['lieu_detail'])}</p>" if g['lieu_detail'] else ""}
<p>Exemplaire unique, imprimé pour {e(g['prenom'])} le {e(g['imprime_le'])}.</p></div>
<div class="pied"><span>Imprimé {e(g['chez'])}</span><span>4</span></div>
</section>"""


def mot_par_defaut(personne: dict, naissance: date, j: dict | None = None) -> str:
    return journal.mot(j or {"mot_modele": journal.MOT, "chez": "à la maison"}, _prenom(personne), naissance)


def document(personne: dict, livret: dict, j: dict, mode: str = "impose", aujourd_hui: date | None = None) -> str:
    """mode : « impose » (A4 paysage, 2 feuilles), « lecture » (4 pages A5), « ecran » (aperçu, lecture sur fond sombre).
    `j` : les éléments communs du journal (Réglages › Le journal, voir journal.py)."""
    naissance = date.fromisoformat(personne["naissance"])
    aujourd_hui = aujourd_hui or date.today()
    c = livret.get("contenu") or {}
    g = {
        "contenu": c, "naissance": naissance, "titre": j["titre"], "sous_titre": j.get("sous_titre", ""),
        "lieu": j["lieu"], "lieu_detail": j.get("lieu_detail", ""), "chez": j["chez"], "signature": j["signature"],
        "nom": personne["nom"], "prenom": _prenom(personne), "date_longue": jour_long(naissance),
        "mot": livret.get("mot") or mot_par_defaut(personne, naissance, j),
        "sources": c.get("sources", []),
        "renvoi_p2": "Le mois" if c.get("p2", {}).get("mode") == "mois" else "La semaine",
        "imprime_le": f"{'1er' if aujourd_hui.day == 1 else aujourd_hui.day} {MOIS[aujourd_hui.month - 1]} {aujourd_hui.year}",
    }
    if mode == "impose":
        corps = f'<div class="feuille">{page4(g)}{page1(g)}</div><div class="feuille">{page2(g)}{page3(g)}</div>'
        page = "@page{size:297mm 210mm;margin:0}"
    else:
        corps = "".join(f'<div class="feuille">{p(g)}</div>' for p in (page1, page2, page3, page4))
        page = "@page{size:148.5mm 210mm;margin:0}"
    accent = j.get("accent") or "#9E1B1B"
    if not (accent.startswith("#") and len(accent) in (4, 7) and all(ch in "0123456789abcdefABCDEF" for ch in accent[1:])):
        accent = "#9E1B1B"
    return (f'<!doctype html><html lang="fr" class="{"lecture" if mode != "impose" else "impose"} {"ecran" if mode == "ecran" else ""}">'
            f'<head><meta charset="utf-8"><title>{e(j["titre"])} — {e(personne["nom"])}</title>'
            f'<style>{font_face()}{CSS}{page}:root{{--a:{accent}}}</style></head><body>{corps}<script>{AJUSTER}</script></body></html>')


# ================================================================ PDF

AJUSTER = """window.deborde=p=>{const r=p.getBoundingClientRect(),cs=getComputedStyle(p),bas=r.bottom-parseFloat(cs.paddingBottom)*r.height/p.offsetHeight+1;
    if(p.scrollHeight>p.clientHeight+1)return true;
    for(const c of p.children){if(c.scrollHeight>c.clientHeight+1&&getComputedStyle(c).overflow!=='visible')return true;}
    for(const el of p.querySelectorAll('*')){if(el.getBoundingClientRect().bottom>bas)return true;}
    return false};
window.ajuster=function(){const deborde=window.deborde;
  for(const p of document.querySelectorAll('.page')){let k=1;p.style.setProperty('--k',k);
    while(deborde(p)&&k>0.861){k=Math.round((k-0.04)*100)/100;p.style.setProperty('--k',k);}
    p.dataset.k=k}};
(document.fonts?document.fonts.ready:Promise.resolve()).then(()=>window.ajuster());
window.mesure=function(){
  /* Hauteur naturelle de chaque bloc (rien ne rétrécit) et place qui manque, page par page, pour l'éditeur. */
  const pages=[...document.querySelectorAll('.page')],deb=pages.map(p=>window.deborde(p));
  const st=document.createElement('style');st.textContent='.page>*{flex-shrink:0!important}';document.head.appendChild(st);
  const r=pages.map((p,i)=>({page:+p.dataset.page,k:+(p.dataset.k||1),deborde:deb[i],
    exces:deb[i]?Math.max(1,Math.round(p.scrollHeight-p.clientHeight)):0,
    blocs:[...p.querySelectorAll('[data-bloc]')].map(b=>({bloc:b.dataset.bloc,h:Math.round(b.getBoundingClientRect().height)}))}));
  st.remove();return r.sort((a,b)=>a.page-b.page)};"""


class RenduImpossible(Exception):
    pass


def mesurer(html_doc: str) -> list[dict]:
    """Pour l'éditeur : par page, déborde-t-elle, de combien (px) et la hauteur de chaque bloc (data-bloc)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as ex:
        raise RenduImpossible("Chromium (Playwright) n'est pas installé.") from ex
    with sync_playwright() as pw:
        try:
            nav = pw.chromium.launch(args=["--no-sandbox"])
        except Exception as ex:  # noqa: BLE001
            raise RenduImpossible(f"Chromium ne démarre pas : {str(ex).splitlines()[0][:160]}") from ex
        try:
            pg = nav.new_page(viewport={"width": 600, "height": 900})
            pg.set_content(html_doc, wait_until="load")
            pg.evaluate("document.fonts.ready.then(() => window.ajuster && window.ajuster())")
            return pg.evaluate("window.mesure()")
        finally:
            nav.close()


def pdf(html_doc: str, mode: str = "impose") -> tuple[bytes, list[int]]:
    """Le PDF et la liste des pages qui débordent (contenu plus haut que la page)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as ex:
        raise RenduImpossible("Chromium (Playwright) n'est pas installé.") from ex
    largeur = "297mm" if mode == "impose" else "148.5mm"
    with sync_playwright() as pw:
        try:
            nav = pw.chromium.launch(args=["--no-sandbox"])
        except Exception as ex:  # noqa: BLE001 — navigateur absent : message clair
            raise RenduImpossible(f"Chromium ne démarre pas : {str(ex).splitlines()[0][:160]}") from ex
        try:
            pg = nav.new_page()
            pg.set_content(html_doc, wait_until="load")
            pg.evaluate("document.fonts.ready.then(() => window.ajuster && window.ajuster())")
            deborde = pg.evaluate("""() => [...document.querySelectorAll('.page')].filter(p => window.deborde(p)).map(p => +p.dataset.page)""")
            contenu = pg.pdf(width=largeur, height="210mm", print_background=True, prefer_css_page_size=True)
        finally:
            nav.close()
    return contenu, sorted(set(deborde))
