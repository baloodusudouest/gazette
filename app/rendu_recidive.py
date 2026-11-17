"""0.9 : mise en page de La Récidive (journal à scandale), d'après la maquette S du 17/11/2026.

Même feuille que la Gazette : A4 paysage, recto p4 | p1, verso p2 | p3, recto-verso bord court, plier ; ou
4 pages A5 dans l'ordre (lecture). Polices embarquées (Anton et Oswald, OFL ; Special Elite, Apache 2.0 ;
Source Serif 4, OFL) ; photos embarquées en data: depuis les aperçus d'Immich gardés dans /data/photos. Le même
document sert à l'aperçu, à la mesure et au PDF (fonctions de rendu.py)."""
from __future__ import annotations

import base64
import functools
import html
import math
from datetime import date
from typing import Callable

from . import rendu
from .recidive import ACCENT, date_photo, jours_absence
from .regles import MOIS, MOIS_COURT, JOURS, jour_long

e = html.escape

POLICES = [
    ("Anton", "anton-latin-400-normal.woff2", 400, "normal"),
    ("Anton", "anton-latin-ext-400-normal.woff2", 400, "normal"),
    ("Oswald", "oswald-latin-500-normal.woff2", 500, "normal"),
    ("Oswald", "oswald-latin-700-normal.woff2", 700, "normal"),
    ("Oswald", "oswald-latin-ext-500-normal.woff2", 500, "normal"),
    ("Oswald", "oswald-latin-ext-700-normal.woff2", 700, "normal"),
    ("Elite", "special-elite-latin-400-normal.woff2", 400, "normal"),
    ("Elite", "special-elite-latin-ext-400-normal.woff2", 400, "normal"),
    ("Serif", "source-serif-4-latin-400-normal.woff2", 400, "normal"),
    ("Serif", "source-serif-4-latin-600-normal.woff2", 600, "normal"),
    ("Serif", "source-serif-4-latin-ext-400-normal.woff2", 400, "normal"),
    ("Serif", "source-serif-4-latin-ext-600-normal.woff2", 600, "normal"),
]


@functools.lru_cache(maxsize=1)
def font_face() -> str:
    regles = []
    for fam, nom, poids, style in POLICES:
        f = rendu.POLICES / nom
        if not f.is_file():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        regles.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');"
                      f"font-weight:{poids};font-style:{style};unicode-range:{rendu.LATIN_EXT if '-ext-' in nom else rendu.LATIN}}}")
    return "".join(regles)


def polices_presentes() -> bool:
    return all((rendu.POLICES / nom).is_file() for _, nom, _, _ in POLICES)


def _etoile(n: int = 18, r1: float = 50, r2: float = 40) -> str:
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.pi * i / n - math.pi / 2
        pts.append(f"{50 + r * math.cos(a):.1f}% {50 + r * math.sin(a):.1f}%")
    return "polygon(" + ",".join(pts) + ")"


# Dimensions en px CSS (96 ppp) : une page A5 = 561 × 794 px, comme la maquette.
CSS = """
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:'Serif',Georgia,serif;color:#111;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.feuille{width:297mm;height:210mm;display:flex;page-break-after:always;overflow:hidden}
.feuille:last-child{page-break-after:auto}
.page{width:148.5mm;height:210mm;background:#fff;display:flex;flex-direction:column;overflow:hidden;position:relative}
.page + .page{border-left:1px dashed #999}
p,h1,h2,h3{margin:0}
.mast{background:var(--a);color:#fff;padding:14px 30px 8px;border-bottom:6px solid #111}
.mast h1{font-family:'Anton',Impact,sans-serif;font-weight:400;font-size:80px;line-height:.95;letter-spacing:.01em;text-transform:uppercase;transform:skewX(-6deg)}
.mast .acc{font-family:'Oswald',sans-serif;font-weight:500;font-size:19px;line-height:1.2;color:#FFE600;letter-spacing:.02em;margin-top:2px}
.strip{display:flex;justify-content:space-between;background:#111;color:#FFE600;font-family:'Oswald',sans-serif;font-weight:500;font-size:13px;letter-spacing:.1em;text-transform:uppercase;padding:6px 30px}
.main{padding:16px 30px 18px;display:flex;flex-direction:column;gap:12px;flex:1 1 auto;min-height:0;position:relative}
.kick{align-self:flex-start;background:#FFE600;color:#111;font-family:'Oswald',sans-serif;font-weight:700;font-size:15px;letter-spacing:.08em;text-transform:uppercase;padding:3px 10px;transform:rotate(-2deg)}
.hl{font-family:'Anton',Impact,sans-serif;font-weight:400;font-size:calc(58px*var(--k,1));line-height:.98;text-transform:uppercase;text-wrap:balance}
.hl span{background:#FFE600;padding:0 6px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.sub{font-family:'Oswald',sans-serif;font-weight:500;font-size:19px;line-height:1.2;color:var(--a);text-transform:uppercase}
.ph{position:relative;background:repeating-linear-gradient(135deg,#e6e6e6 0 10px,#d2d2d2 10px 20px);border:3px solid #111;display:flex;align-items:flex-end;overflow:hidden}
.ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%}
.ph img.centre{object-position:50% 50%}.ph img.bas{object-position:50% 85%}
.ph img.entiere{object-fit:contain;background:#111}
.ph .tag{position:relative;background:#111;color:#fff;font-family:'Elite',monospace;font-size:12px;padding:3px 8px}
.ph.arch img{filter:grayscale(1) sepia(.35)}
.burst{position:absolute;z-index:2;width:104px;height:104px;background:var(--a);color:#FFE600;display:flex;align-items:center;justify-content:center;text-align:center;font-family:'Anton',sans-serif;font-size:23px;line-height:1;text-transform:uppercase;transform:rotate(-12deg);clip-path:ETOILE}
.burst.hg{top:10px;left:10px}.burst.hd{top:10px;right:10px}.burst.bg{bottom:30px;left:10px}.burst.bd{bottom:30px;right:10px}
.teas{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:auto}
.teas div{border:2px solid #111;padding:6px 8px;font-family:'Oswald',sans-serif;font-size:13px;line-height:1.2;text-transform:uppercase}
.teas b{display:block;background:#111;color:#FFE600;margin:-6px -8px 5px;padding:2px 8px;font-size:14px}
.band{background:#111;color:#FFE600;padding:12px 30px;display:flex;justify-content:space-between;align-items:baseline}
.band h2{font-family:'Anton',sans-serif;font-weight:400;font-size:40px;line-height:1;text-transform:uppercase}
.band span{font-family:'Oswald',sans-serif;font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:#fff}
.red{background:var(--a);color:#fff;padding:8px 14px;font-family:'Oswald',sans-serif;font-weight:700;font-size:16px;text-transform:uppercase;transform:rotate(-1.2deg)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 14px;align-content:start}
.fig{display:flex;flex-direction:column;gap:4px;min-width:0}
.fig .n{font-family:'Anton',sans-serif;font-size:18px;color:var(--a);line-height:1}
.cap{font-family:'Elite',monospace;font-size:calc(12.5px*var(--k,1));line-height:1.28}
.anc{grid-column:1/-1;display:flex;align-items:center;gap:10px;font-family:'Anton',sans-serif;font-size:22px;text-transform:uppercase;line-height:1;margin-top:4px}
.anc i{flex:1 1 0;border-top:4px solid #111}
.tl{display:flex;flex-direction:column;border-left:6px solid #111;margin-left:6px}
.tl .e{display:flex;gap:12px;padding:8px 0 8px 14px;position:relative;align-items:baseline}
.tl .e:before{content:"";position:absolute;left:-13px;top:14px;width:16px;height:16px;background:#FFE600;border:3px solid #111;border-radius:50%}
.tl .q{flex:0 0 100px;font-family:'Oswald',sans-serif;font-weight:700;font-size:14px;text-transform:uppercase;color:var(--a)}
.tl .x{font-size:calc(15px*var(--k,1));line-height:1.3}
.tl .e.big .x{font-family:'Anton',sans-serif;font-size:24px;line-height:1.05;text-transform:uppercase}
.chif{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.chif div{border:3px solid #111;text-align:center;padding:8px 4px;background:#FFE600}
.chif b{display:block;font-family:'Anton',sans-serif;font-weight:400;font-size:44px;line-height:1}
.chif span{font-family:'Oswald',sans-serif;font-size:13px;text-transform:uppercase;letter-spacing:.06em}
.note{font-size:calc(14px*var(--k,1));line-height:1.4;border-top:3px double #111;padding-top:8px}
.lettre p{font-size:calc(17px*var(--k,1));line-height:1.5;margin-bottom:12px;text-wrap:pretty}
.lettre p.d::first-letter{font-family:'Anton',sans-serif;font-size:62px;line-height:.8;float:left;padding:5px 8px 0 0;color:var(--a)}
.stamp{align-self:flex-end;border:4px solid var(--a);color:var(--a);font-family:'Anton',sans-serif;font-size:34px;line-height:1;text-transform:uppercase;padding:4px 14px;transform:rotate(-8deg)}
.sign{font-family:'Elite',monospace;font-size:20px;text-align:right}
.petit{font-family:'Oswald',sans-serif;font-size:12px;line-height:1.3;text-transform:uppercase;letter-spacing:.04em;border:2px solid #111;padding:8px 10px}
.bar{display:flex;align-items:stretch;height:34px;margin-top:auto}
.bar i{display:block;background:#111}
.pied{display:flex;justify-content:space-between;align-items:flex-end;font-family:'Oswald',sans-serif;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.lecture body{background:#e9e4d8}
.lecture .feuille{width:148.5mm;height:210mm}
.lecture .page + .page{border-left:0}
.ecran body{background:#2a2521;padding:6mm;display:flex;flex-direction:column;gap:6mm;align-items:center}
.ecran .feuille{box-shadow:0 2mm 6mm rgba(0,0,0,.35)}
""".replace("ETOILE", _etoile())

BARRES = "".join(f'<i style="width:{w}px;margin-right:{g}px"></i>' for w, g in
                 [(3, 2), (1, 3), (4, 2), (2, 2), (1, 4), (3, 3), (2, 2), (4, 2), (1, 3), (2, 2), (3, 4), (1, 2), (4, 3), (2, 2), (1, 3), (3, 2)])


def _court(iso: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return ""
    return f"{JOURS[d.weekday()][:3]}. {'1er' if d.day == 1 else d.day} {MOIS_COURT[d.month - 1]}"


def _photo(p: dict | None, image: Callable[[str], bytes | None], style: str = "", etiquette: str = "", dedans: str = "") -> str:
    if not p:
        return f'<div class="ph" style="{style}">{dedans}</div>'
    octets = image(p["id"])
    cadrage = p.get("cadrage") if p.get("cadrage") in ("haut", "centre", "bas", "entiere") else "haut"
    img = f'<img alt="" class="{cadrage}" src="data:image/jpeg;base64,{base64.b64encode(octets).decode()}">' if octets else ""
    tag = etiquette or ("ARCHIVES · " if p.get("ancien") else "") + date_photo(p.get("date", ""))
    return f'<div class="ph{" arch" if p.get("ancien") else ""}" style="{style}">{img}{dedans}<span class="tag">{e(tag)}</span></div>'


def _gros_titre(g: dict) -> str:
    """Par défaut « [Nom] revient ! » (nom surligné) ; 0.9.1 : le titre choisi ou écrit, le nom surligné s'il y est."""
    t = (g.get("titre_une") or "").strip()
    if not t:
        return f'<h2 class="hl" data-bloc="titre"><span>{e(g["nom"])}</span> revient !</h2>'
    for n in (g["nom"], g["prenom"]):
        if n and n.casefold() in t.casefold():
            i = t.casefold().index(n.casefold())
            return (f'<h2 class="hl" data-bloc="titre">{e(t[:i])}<span>{e(t[i:i + len(n)])}</span>{e(t[i + len(n):])}</h2>')
    return f'<h2 class="hl" data-bloc="titre"><span>{e(t)}</span></h2>'


def page1(g: dict) -> str:
    une = g["photos"][0] if g["photos"] else None
    n_rec, n_anc = g["n_rec"], g["n_anc"]
    sous = f"{n_rec} cliché{'s' if n_rec > 1 else ''} récent{'s' if n_rec > 1 else ''} {'ont' if n_rec > 1 else 'a'} fuité"
    sous += ", et les archives ressortent…" if n_anc else " !"
    place = g.get("macaron") or "hd"
    macaron = f'<div class="burst {place}">Exclusif !</div>' if place in ("hg", "hd", "bg", "bd") else ""
    return f"""<section class="page" data-page="1">
<div class="mast"><h1>La Récidive</h1><p class="acc">« {e(g['accroche'])} »</p></div>
<div class="strip"><span>N° {g['numero']} · {e(g['arrivee_longue'])}</span><span>Prix : offert par la maison</span></div>
<div class="main">
<span class="kick">Exclusif · Photos accablantes</span>
{_gros_titre(g)}
<p class="sub">{e(sous)}</p>
{_photo(une, g['image'], 'flex:1 1 auto;min-height:0', 'Pièce à conviction n°1 · ' + date_photo(une.get('date', '')) if une else '', macaron)}
<div class="teas">
<div><b>Page 2</b>Les preuves en images</div>
<div><b>Page 3</b>Chronologie des faits</div>
<div><b>Page 4</b>Droit de réponse</div>
</div>
</div></section>"""


def page2(g: dict) -> str:
    autres = g["photos"][1:]
    n_rec, n_anc = g["n_rec"], g["n_anc"]
    rangs = math.ceil(sum(1 for p in autres if not p.get("ancien")) / 2) + math.ceil(sum(1 for p in autres if p.get("ancien")) / 2)
    dispo = 600 - (30 if n_anc else 0)
    haut = max(90, min(250, int(dispo / max(1, rangs)) - 52))
    figs, i, separe = [], 1, False
    une = g["photos"][0] if g["photos"] else None
    for k, p in enumerate(autres):
        if p.get("ancien") and not separe:
            figs.append('<div class="anc"><span>Anciens scandales</span><i></i></div>')
            separe = True
        if p.get("ancien"):
            titre, num = "Archives", ""
        else:
            i += 1
            titre, num = f"Pièce à conviction n°{i}", f'<span class="n">N°{i}</span>'
        figs.append(f'<div class="fig" data-bloc="photo:{k + 1}">{_photo(p, g["image"], f"height:{haut}px")}{num}'
                    f'<p class="cap"><b>{e(titre)}.</b> {e(p.get("legende", ""))}</p></div>')
    if une and une.get("legende"):
        figs.insert(0, f'<p class="cap" data-bloc="photo:0" style="grid-column:1/-1"><b>En une, pièce n°1.</b> {e(une["legende"])}</p>')
    bandeau = f"{n_rec} cliché{'s' if n_rec > 1 else ''} depuis le dernier séjour" + (", complétés par les archives" if n_anc else "")
    return f"""<section class="page" data-page="2">
<div class="band"><h2>Les preuves</h2><span>Page 2</span></div>
<div class="main" style="gap:10px">
<div class="red">{e(bandeau)}</div>
<div class="grid">{''.join(figs)}</div>
</div></section>"""


def page3(g: dict) -> str:
    nom, prec = g["nom"], g["precedent"]
    evs = []
    if prec:
        evs.append(f'<div class="e"><span class="q">{e(_court(prec["du"]))}</span><span class="x">Arrivée de {e(nom)} pour son dernier séjour.</span></div>')
        if prec.get("jusqu_au"):
            evs.append(f'<div class="e"><span class="q">{e(_court(prec["jusqu_au"]))}</span><span class="x">Départ. La maison retient son souffle.</span></div>')
    t = g["trouvees"]
    phrase = f"{t} photo{'s' if t > 1 else ''} {'sont prises' if t > 1 else 'est prise'} avec {nom} dedans."
    if g["n_anc"]:
        phrase += " Pas assez : les archives sont rouvertes."
    if prec:
        try:
            d1, d2 = date.fromisoformat(prec["du"]), date.fromisoformat(g["du"])
            periode = f"{MOIS_COURT[d1.month - 1]} → {MOIS_COURT[d2.month - 1]}" if (d1.year, d1.month) != (d2.year, d2.month) else MOIS[d2.month - 1]
        except ValueError:
            periode = "Depuis"
        evs.append(f'<div class="e"><span class="q">{e(periode)}</span><span class="x">{e(phrase)}</span></div>')
    evs.append(f'<div class="e big"><span class="q">{e(_court(g["du"]))}</span><span class="x">Le retour de {e(nom)} !</span></div>')
    absence = g["absence"]
    note = (f"<b>Comment on a complété ?</b> Faute de preuves récentes en nombre suffisant, la rédaction a rouvert ses "
            f"archives : de vieux clichés de {e(nom)} comblent le manque, sous la rubrique « Anciens scandales ».") if g["n_anc"] else \
           (f"<b>Toutes les preuves sont récentes :</b> chaque cliché a été pris depuis le dernier passage de {e(nom)} à la maison.")
    return f"""<section class="page" data-page="3">
<div class="band"><h2>Chronologie des faits</h2><span>Page 3</span></div>
<div class="main" style="gap:14px">
<div class="tl">{''.join(evs)}</div>
<div class="chif"><div><b>{g['n_rec']}</b><span>photo{'s' if g['n_rec'] > 1 else ''} récente{'s' if g['n_rec'] > 1 else ''}</span></div>
<div><b>{g['n_anc']}</b><span>ancien{'s' if g['n_anc'] > 1 else ''} scandale{'s' if g['n_anc'] > 1 else ''}</span></div>
<div><b>{absence if absence is not None else '?'}</b><span>jours d'absence</span></div></div>
<p class="note">{note}</p>
<div class="bar">{BARRES}</div>
</div></section>"""


def page4(g: dict) -> str:
    paras = "".join(f'<p class="{"d" if i == 0 else ""}">{e(t)}</p>' for i, t in enumerate(rendu._paragraphes(g["mot"])))
    return f"""<section class="page" data-page="4">
<div class="band"><h2>Droit de réponse</h2><span>Page 4</span></div>
<div class="main" style="gap:14px">
<div class="lettre" data-bloc="mot">{paras}</div>
<span class="stamp">Démenti</span>
<p class="sign">{e(g['signature'])}</p>
<p class="petit">Une photo vous gêne ? Dites-le, elle sera retirée de l'édition. Chaque exemplaire est relu avant impression.</p>
<div class="bar">{BARRES}</div>
<div class="pied"><span>Imprimé {e(g['chez'])}</span><span>N° {g['numero']} · exemplaire unique</span></div>
</div></section>"""


def document(personne: dict, edition: dict, j: dict, image: Callable[[str], bytes | None], mode: str = "impose") -> str:
    """`edition` : une ligne de la table recidives (photos, numéro, accroche, mot, précédent…) ; `image(id)` : les
    octets de l'aperçu gardé (None : case hachurée)."""
    photos = [p for p in edition.get("photos") or [] if not p.get("retiree")]
    prec = edition.get("precedent") or None
    du = edition["sejour_du"]
    prenom = (personne.get("prenom") or personne["nom"].split(" ")[0]).strip()
    g = {
        "photos": photos, "image": image, "nom": personne["nom"], "prenom": prenom,
        "numero": edition.get("numero_main") or edition.get("numero") or 2,
        "accroche": edition.get("accroche") or "", "du": du, "precedent": prec,
        "arrivee_longue": jour_long(date.fromisoformat(du)),
        "n_rec": sum(1 for p in photos if not p.get("ancien")), "n_anc": sum(1 for p in photos if p.get("ancien")),
        "trouvees": int(edition.get("trouvees") or 0), "absence": jours_absence(prec, du),
        "mot": edition.get("mot") or "", "signature": j["signature"], "chez": j["chez"],
        "titre_une": edition.get("titre_une") or "", "macaron": edition.get("macaron") or "hd",
    }
    if mode == "impose":
        corps = f'<div class="feuille">{page4(g)}{page1(g)}</div><div class="feuille">{page2(g)}{page3(g)}</div>'
        page = "@page{size:297mm 210mm;margin:0}"
    else:
        corps = "".join(f'<div class="feuille">{p(g)}</div>' for p in (page1, page2, page3, page4))
        page = "@page{size:148.5mm 210mm;margin:0}"
    return (f'<!doctype html><html lang="fr" class="{"lecture" if mode != "impose" else "impose"} {"ecran" if mode == "ecran" else ""}">'
            f'<head><meta charset="utf-8"><title>La Récidive N° {g["numero"]} — {e(personne["nom"])}</title>'
            f'<style>{font_face()}{CSS}{page}:root{{--a:{ACCENT}}}</style></head><body>{corps}<script>{rendu.AJUSTER}</script></body></html>')
