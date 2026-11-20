"""0.28 : mise en page de « Good Evening Europe! » (édition spéciale Eurovision), style « Paillettes » des maquettes du
20/11/2026 (bleu nuit et rose), pour la finale (livret « finale ») et la demi-finale (livret « qualifies »).

Même feuille que la Gazette et La Récidive : A4 paysage, recto p4 | p1, verso p2 | p3, recto-verso bord court, plier ;
ou 4 pages A5 dans l'ordre (lecture, PDF pour les absents). Polices embarquées (celles de La Récidive : Anton, Oswald,
Special Elite, Source Serif 4) ; images embarquées en data: (aperçus d'Immich gardés, images figées de Douze points).
Le même document sert à l'aperçu, à la mesure et au PDF (fonctions de rendu.py)."""
from __future__ import annotations

import base64
import html
from typing import Callable

from . import eurovision as E
from . import rendu, rendu_recidive
from .douze_points import type_image

e = html.escape
NUIT = "#16123A"
ACCENT = "#E0177A"

# Dimensions en px CSS (96 ppp) : une page A5 = 561 × 794 px, comme les maquettes.
CSS = """
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:'Serif',Georgia,serif;color:var(--n);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.feuille{width:297mm;height:210mm;display:flex;page-break-after:always;overflow:hidden}
.feuille:last-child{page-break-after:auto}
.page{width:148.5mm;height:210mm;background:#fff;display:flex;flex-direction:column;overflow:hidden;position:relative}
.page + .page{border-left:1px dashed #999}
p,h1,h2,h3{margin:0}
.ac{color:var(--a)}
.mast{background:var(--n);color:#fff;padding:20px 36px 12px;display:flex;flex-direction:column;gap:6px;position:relative}
.rayons{position:absolute;inset:0;overflow:hidden}
.mast i{position:absolute;top:-20px;width:220px;height:260px;background:rgba(255,255,255,.07);clip-path:polygon(45% 0,55% 0,100% 100%,0 100%)}
.mast i.g{left:-40px;transform:rotate(-24deg)}.mast i.d{right:-40px;transform:rotate(24deg)}
.mast .sur{font-family:'Oswald',sans-serif;font-weight:500;font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--a);position:relative}
.mast h1{font-family:'Anton',Impact,sans-serif;font-weight:400;font-size:var(--tm,54px);line-height:.95;text-transform:uppercase;letter-spacing:.01em;position:relative}
.strip{display:flex;justify-content:space-between;gap:10px;background:var(--a);color:#fff;font-family:'Oswald',sans-serif;font-weight:500;font-size:12px;letter-spacing:.12em;text-transform:uppercase;padding:6px 36px}
.corps{padding:16px 36px 0;display:flex;flex-direction:column;gap:12px;flex:1 1 auto;min-height:0}
.ph{position:relative;border:3px solid var(--n);background:repeating-linear-gradient(135deg,#ECEAF3 0 10px,#DCD9E8 10px 20px);display:flex;align-items:flex-end;overflow:hidden}
.ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 35%}
.ph img.contenu{object-fit:contain;background:var(--n)}
.ph .tag{position:relative;background:var(--n);color:#fff;font-family:'Elite',monospace;font-size:12px;padding:3px 8px}
.pastille{position:absolute;right:-8px;top:-12px;z-index:2;width:96px;height:96px;border-radius:50%;background:#fff;border:3px solid var(--a);display:flex;align-items:center;justify-content:center;transform:rotate(10deg);overflow:hidden;text-align:center;font-family:'Anton',sans-serif;font-size:20px;line-height:1;text-transform:uppercase;color:var(--n)}
.pastille img{width:78%;height:78%;object-fit:contain}
.duo-vide{position:absolute;inset:0;background:var(--n);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;text-align:center;padding:6px}
.duo-vide img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;opacity:.35;padding:8px}
.duo-vide b{position:relative;font-family:'Anton',sans-serif;font-weight:400;font-size:var(--tv,40px);line-height:1;color:var(--a)}
.duo-vide span{position:relative;font-family:'Oswald',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:.08em}
.kick{align-self:flex-start;background:var(--n);color:#fff;font-family:'Oswald',sans-serif;font-weight:700;font-size:12px;letter-spacing:.1em;text-transform:uppercase;padding:3px 9px;transform:rotate(-2deg)}
.hl{font-family:'Anton',sans-serif;font-weight:400;font-size:calc(var(--t,38px)*var(--k,1));line-height:1;text-transform:uppercase;text-wrap:balance}
.txt{font-size:calc(15px*var(--k,1));line-height:1.4}
.txt b{font-weight:600}
.trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:12px 36px 34px}
.trio div{border:2px solid var(--n);padding:7px 9px;display:flex;flex-direction:column;gap:3px;min-width:0}
.trio div.nuit{background:var(--n);color:#fff;border-color:var(--n)}
.trio span{font-family:'Oswald',sans-serif;font-weight:700;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--a)}
.trio b{font-family:'Anton',sans-serif;font-weight:400;font-size:19px;text-transform:uppercase;line-height:1;overflow-wrap:anywhere}
.tete{display:flex;justify-content:space-between;align-items:baseline;gap:8px;padding:28px 0 8px;margin:0 36px;border-bottom:3px solid var(--n)}
.tete b{font-family:'Anton',sans-serif;font-weight:400;font-size:18px;text-transform:uppercase}
.tete span{font-family:'Oswald',sans-serif;font-weight:500;font-size:11px;letter-spacing:.1em;text-transform:uppercase;text-align:right}
.int{padding:14px 36px 0;display:flex;flex-direction:column;gap:12px;flex:1 1 auto;min-height:0}
.sur2{font-family:'Oswald',sans-serif;font-weight:700;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--a)}
h2.gros{font-family:'Anton',sans-serif;font-weight:400;font-size:calc(var(--t,42px)*var(--k,1));line-height:.98;text-transform:uppercase;text-wrap:balance}
.deux{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.bloc-t{color:#fff;font-family:'Anton',sans-serif;font-size:20px;text-transform:uppercase;padding:6px 10px;line-height:1;background:var(--n)}
.bloc-t.rose{background:var(--a)}
.podium{display:flex;align-items:flex-end;gap:4px;height:230px;margin-top:8px}
.podium>div{flex:1 1 0;display:flex;flex-direction:column;align-items:center;gap:5px;min-width:0}
.podium .p{font-family:'Oswald',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;text-align:center;line-height:1.1;overflow-wrap:anywhere}
.podium .pts{font-size:12px}
.podium .m{width:100%;display:flex;align-items:flex-start;justify-content:center;padding-top:6px;font-family:'Anton',sans-serif}
.verdict{border:3px solid var(--n);padding:11px 13px;display:flex;flex-direction:column;gap:8px}
.verdict>b{font-family:'Anton',sans-serif;font-weight:400;font-size:20px;text-transform:uppercase;line-height:1}
.chif{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.chif div{display:flex;flex-direction:column;gap:2px;min-width:0}
.chif b{font-family:'Anton',sans-serif;font-weight:400;font-size:28px;line-height:1;color:var(--a);overflow-wrap:anywhere}
.chif span{font-size:12px;line-height:1.3}
.votes{display:grid;gap:4px 10px;font-size:13px;align-items:baseline}
.votes .e{font-family:'Oswald',sans-serif;font-weight:700;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--a)}
.votes b{font-weight:600}
.liste{display:flex;flex-direction:column;gap:6px;min-width:0}
.liste .t{display:flex;align-items:baseline;justify-content:space-between;border-bottom:2px solid var(--n);padding-bottom:4px}
.liste .t b{font-family:'Anton',sans-serif;font-weight:400;font-size:25px;text-transform:uppercase;line-height:1}
.liste .t span{font-family:'Oswald',sans-serif;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.liste .l{display:flex;justify-content:space-between;align-items:baseline;gap:6px;font-size:calc(15px*var(--k,1))}
.liste .l b{font-weight:600;overflow-wrap:anywhere}
.liste .l span{font-family:'Oswald',sans-serif;font-size:13px;white-space:nowrap}
.liste .c{font-family:'Elite',monospace;font-size:12px;line-height:1.3}
.nuit-b{background:var(--n);color:#fff;padding:11px 13px;display:flex;flex-direction:column;gap:8px}
.nuit-b .t{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.nuit-b .t b{font-family:'Anton',sans-serif;font-weight:400;font-size:22px;text-transform:uppercase;line-height:1}
.nuit-b .t span{font-family:'Oswald',sans-serif;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#CFD1DC;text-align:right}
.palm{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.palm div{border:2px solid #CFD1DC;padding:7px 8px;display:flex;flex-direction:column;gap:2px;min-width:0}
.palm div:first-child{border-color:var(--a)}
.palm i{font-style:normal;font-family:'Oswald',sans-serif;font-weight:700;font-size:12px;text-transform:uppercase;color:#CFD1DC}
.palm div:first-child i{color:var(--a)}
.palm b{font-family:'Anton',sans-serif;font-weight:400;font-size:20px;text-transform:uppercase;line-height:1;overflow-wrap:anywhere}
.palm span{font-size:12px}
.comms{display:flex;flex-direction:column;gap:9px}
.comms>b{font-family:'Anton',sans-serif;font-weight:400;font-size:22px;text-transform:uppercase;line-height:1;border-bottom:2px solid var(--n);padding-bottom:4px}
.comm{display:flex;gap:10px;align-items:flex-start}
.comm>span{font-family:'Anton',sans-serif;font-size:36px;line-height:.8;color:var(--a)}
.comm p{font-size:calc(14.5px*var(--k,1));line-height:1.38;font-style:italic;overflow-wrap:anywhere}
.comm small{display:block;font-style:normal;font-family:'Oswald',sans-serif;font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.cases{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.cases div{border:3px solid var(--n);padding:9px 11px;display:flex;flex-direction:column;gap:2px;min-width:0}
.cases div.pointille{border-style:dashed}
.cases i{font-style:normal;font-family:'Oswald',sans-serif;font-weight:700;font-size:12px;letter-spacing:.1em;text-transform:uppercase}
.cases div:first-child i{color:var(--a)}
.cases b{font-family:'Anton',sans-serif;font-weight:400;font-size:24px;text-transform:uppercase;line-height:1;overflow-wrap:anywhere}
.cases span{font-size:13px}
.dix{display:flex;align-items:center;gap:8px;padding:3px 2px;border-bottom:1px solid #CFD1DC;font-size:calc(14px*var(--k,1))}
.dix i{font-style:normal;font-family:'Oswald',sans-serif;font-size:13px;width:18px}
.dix b{flex:1 1 auto;font-weight:600;min-width:0;overflow-wrap:anywhere}
.dix svg{flex:0 0 auto}
.dix .pv{font-family:'Oswald',sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;background:var(--a);color:#fff;padding:1px 6px;white-space:nowrap}
.note{font-family:'Elite',monospace;font-size:12px;line-height:1.35}
.duos{display:grid;gap:10px}
.duo{display:flex;flex-direction:column;gap:4px;min-width:0}
.duo .n{font-family:'Anton',sans-serif;font-weight:400;font-size:var(--tn,19px);text-transform:uppercase;line-height:1;overflow-wrap:anywhere}
.duo .c{font-family:'Elite',monospace;font-size:12px;line-height:1.25}
.vign{display:grid;gap:6px}
.vign div{background:var(--n);color:#fff;padding:6px 8px;font-family:'Oswald',sans-serif;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.04em;line-height:1.2}
.rdv{border:3px solid var(--n);display:flex;flex-direction:column}
.rdv .t{background:var(--a);color:#fff;padding:7px 12px;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.rdv .t b{font-family:'Anton',sans-serif;font-weight:400;font-size:23px;text-transform:uppercase;line-height:1}
.rdv .t span{font-family:'Oswald',sans-serif;font-weight:500;font-size:12px;letter-spacing:.08em;text-transform:uppercase}
.rdv .c{padding:9px 12px;display:flex;flex-direction:column;gap:6px;font-size:14px}
.fav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.fav div{display:flex;flex-direction:column;gap:1px;min-width:0}
.fav i{font-style:normal;font-family:'Anton',sans-serif;font-size:21px;color:var(--a);line-height:1}
.fav b{font-family:'Anton',sans-serif;font-weight:400;font-size:17px;text-transform:uppercase;line-height:1;overflow-wrap:anywhere}
.bas{margin-top:auto;display:flex;flex-direction:column;flex-shrink:0}
.ban{height:var(--hb,84px);background:repeating-linear-gradient(135deg,#2A2552 0 10px,#221E47 10px 20px);overflow:hidden;position:relative}
.ban img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.colo{background:var(--n);color:#fff;padding:10px 36px 30px;display:flex;justify-content:space-between;align-items:flex-end;gap:12px}
.colo div{display:flex;flex-direction:column;gap:2px;min-width:0}
.colo b{font-family:'Anton',sans-serif;font-weight:400;font-size:18px;text-transform:uppercase}
.colo span{font-family:'Oswald',sans-serif;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#CFD1DC}
.colo i{font-style:normal;font-family:'Anton',sans-serif;font-size:28px;color:var(--a);line-height:1}
.lecture body{background:#e9e4d8}
.lecture .feuille{width:148.5mm;height:210mm}
.lecture .page + .page{border-left:0}
.ecran body{background:#2a2521;padding:6mm;display:flex;flex-direction:column;gap:6mm;align-items:center}
.ecran .feuille{box-shadow:0 2mm 6mm rgba(0,0,0,.35)}
"""

COCHE = (f'<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="{NUIT}" stroke-width="3" stroke-linecap="round" '
         'stroke-linejoin="round" role="img" aria-label="qualifié"><path d="M4 12l5 5L20 6"></path></svg>')
CROIX = (f'<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="3" stroke-linecap="round" '
         'role="img" aria-label="éliminé"><path d="M6 6l12 12M18 6L6 18"></path></svg>')


def _src(octets: bytes | None) -> str:
    if not octets:
        return ""
    return f"data:{type_image(octets) or 'image/jpeg'};base64,{base64.b64encode(octets).decode()}"


def _img(octets: bytes | None, classe: str = "") -> str:
    s = _src(octets)
    return f'<img alt="" class="{classe}" src="{s}">' if s else ""


def _titre_mast(titre: str) -> str:
    """« Good Evening Europe! » : le dernier mot en rose, comme la maquette (titre réglable)."""
    mots = titre.split()
    if len(mots) < 2:
        return e(titre)
    return f'{e(" ".join(mots[:-1]))} <span class="ac">{e(mots[-1])}</span>'


def _taille_mast(titre: str) -> str:
    n = len(titre)
    return "56px" if n <= 22 else "46px" if n <= 28 else "38px" if n <= 34 else "32px"


def _taille_hl(t: str) -> str:
    n = len(t)
    return "40px" if n <= 22 else "34px" if n <= 32 else "29px" if n <= 44 else "25px"


def _tete(g: dict, page: int) -> str:
    return f'<div class="tete"><b>{_titre_mast(g["titre"])}</b><span>{e(g["numero"])} · {page}</span></div>'


def _pays(g: dict, cid) -> str:
    try:
        return (g["chansons"].get(int(cid)) or {}).get("pays", "?")
    except (TypeError, ValueError):
        return "?"


# ---------------------------------------------------------------- page 1 (la une), commune aux deux livrets

def _photo_duo(g: dict, cle: str, photo: str, haut: str, nom: str, taille_vide: str = "40px") -> str:
    octets = g["duo_image"](photo) if photo else None
    if octets:
        return f'<div class="ph" style="{haut}">{_img(octets)}<span class="tag">{e(nom)}</span></div>'
    logo = g["images"].get("logo")
    return (f'<div class="ph" style="{haut};border-style:dashed"><div class="duo-vide" style="--tv:{taille_vide}">{_img(logo)}'
            f'<b>12</b><span>{e(nom)}</span></div></div>')


def page1(g: dict) -> str:
    j = g["j"]
    une_sorte = g["image_une"]
    une = g["images"].get(une_sorte) if une_sorte else None
    logo = g["images"].get("logo")
    pastille = f'<div class="pastille">{_img(logo)}</div>' if logo else '<div class="pastille">12<br>points</div>'
    etiquette = {"apero": "L'apéro de la soirée", "poster": e((j.get("soiree") or {}).get("nom") or ""), "logo": ""}.get(une_sorte, "")
    photo = (f'<div class="ph" data-bloc="photo-une" style="flex:1 1 auto;min-height:150px">{_img(une, "contenu" if une_sorte == "logo" else "")}'
             f'{pastille}{f"<span class=tag>{etiquette}</span>" if etiquette else ""}</div>')
    inv = g["une"]
    qualif = g["livret"] == "qualifies"
    if inv:
        if qualif:
            kick, titre = "Le meilleur flair", f"{inv['prenom']} a le flair"
            texte = (f"<b>{inv.get('trouves')} qualifiés sur {inv.get('sur') or 10}</b> trouvés dans son top 10. "
                     "Personne n'a fait mieux ce soir.")
        else:
            kick, titre = "Le plus proche du vrai", f"{inv['prenom']} avait tout vu venir"
            texte = (f"Son classement n'était, en moyenne, qu'à <b>{e(E.places(inv.get('ecart')))}</b> du vrai classement "
                     "final. Personne n'a fait mieux ce soir.")
        duo = E.duo_de(j, inv["id"], g["duos"])
        nom_duo = E.noms_duo(j, duo["cle"]) if duo else inv["prenom"]
        cote = (f'<div style="flex:0 0 150px;display:flex;flex-direction:column;gap:4px" data-bloc="duo-une">'
                f'{_photo_duo(g, duo["cle"] if duo else "", duo["photo"] if duo else "", "flex:1 1 auto;min-height:140px", nom_duo if duo else inv["prenom"], "44px")}'
                f'<span class="note">{"Sa photo de duo de la soirée" if duo and duo["photo"] else "Pas de photo de duo ce soir"}</span></div>')
        bloc = (f'<div style="display:flex;gap:16px;align-items:stretch" data-bloc="invite-une"><div style="flex:1 1 0;display:flex;flex-direction:column;gap:6px;min-width:0">'
                f'<span class="kick">{kick}</span><h2 class="hl" style="--t:{_taille_hl(titre)}">{e(titre)}</h2>'
                f'<p class="txt">{texte}</p></div>{cote}</div>')
    else:
        bloc = (f'<div data-bloc="invite-une" style="display:flex;flex-direction:column;gap:6px"><span class="kick">Ce soir chez nous</span>'
                f'<h2 class="hl" style="--t:34px">{e((j.get("soiree") or {}).get("nom") or "La soirée")}</h2></div>')
    if qualif:
        demi = j.get("demi") or {}
        top = demi.get("notre_top") or []
        devines = sum(1 for x in top if x.get("qualifie"))
        fav = (demi.get("favoris") or [None])[0] or (top[0]["chanson"] if top else None)
        trio = (f'<div><span>Notre favori</span><b>{e(_pays(g, fav)) if fav else "—"}</b></div>'
                f'<div><span>Qualifiés devinés</span><b>{devines} / {len(demi.get("qualifies") or []) or 10}</b></div>'
                '<div class="nuit"><span>Page 4</span><b>Rendez-vous samedi</b></div>')
    else:
        pm, po = j.get("podium_maison") or [], j.get("podium_officiel") or []
        trio = (f'<div><span>Notre vainqueur</span><b>{e(_pays(g, pm[0])) if pm else "—"}</b></div>'
                f'<div><span>Le vrai vainqueur</span><b>{e(_pays(g, po[0])) if po else "—"}</b></div>'
                '<div class="nuit"><span>Page 4</span><b>Les jumeaux</b></div>')
    return f"""<section class="page" data-page="1">
<div class="mast"><div class="rayons"><i class="g"></i><i class="d"></i></div><span class="sur">Édition spéciale · {e((j.get("soiree") or {}).get("concours") or "Eurovision")}</span>
<h1 style="--tm:{_taille_mast(g['titre'])}">{_titre_mast(g['titre'])}</h1></div>
<div class="strip"><span>N° {e(g['numero'])}</span><span>{e(g['date'])}</span></div>
<div class="corps">{photo}{bloc}</div>
<div class="trio" data-bloc="trio">{trio}</div>
</section>"""


# ---------------------------------------------------------------- finale

def _podium(g: dict, ids: list, points, rose: bool) -> str:
    hauteurs = {1: 140, 2: 104, 3: 76}
    fonds = {1: (ACCENT if rose else NUIT, "#fff"), 2: ("#CFD1DC", NUIT), 3: ("#E6E7EE", NUIT)}
    ordre = [(2, 1), (1, 0), (3, 2)]
    cols = []
    for place, k in ordre:
        if k >= len(ids):
            cols.append("<div></div>")
            continue
        cid = ids[k]
        pts = points(cid)
        fond, coul = fonds[place]
        cols.append(f'<div><span class="p">{e(_pays(g, cid))}</span>{f"<span class=pts>{pts} pts</span>" if pts is not None else ""}'
                    f'<div class="m" style="height:{hauteurs[place]}px;background:{fond};color:{coul};font-size:{40 if place == 1 else 32}px">{place}</div></div>')
    return f'<div class="podium">{"".join(cols)}</div>'


def _gagnant(g: dict, cle) -> str:
    """La chanson classée 1re selon `cle(chanson)` (rang), ou « — »."""
    meilleurs = [c for c in g["chansons"].values() if cle(c) == 1]
    return meilleurs[0]["pays"] if meilleurs else "—"


def f_page2(g: dict) -> str:
    j = g["j"]
    pm, po = j.get("podium_maison") or [], j.get("podium_officiel") or []
    ch = g["chansons"]
    jury = E.avec_jury(j)
    droite = "jury et public réunis" if (j.get("soiree") or {}).get("avec_jury_officiel") else "le vote du public"
    intro = (f"À gauche, le podium de la maison, fait des classements de chacun. À droite, celui de l'Europe, {droite}.")
    gauche = _podium(g, pm, lambda c: (ch.get(int(c)) or {}).get("maison", {}).get("points"), False)
    droit = _podium(g, po, lambda c: (ch.get(int(c)) or {}).get("officiel", {}).get("total"), True)
    communs = len(set(pm[:3]) & set(po[:3]))
    cases = [f'<div><b>{communs} / 3</b><span>pays de notre podium sont sur le vrai</span></div>']
    if pm:
        r = (ch.get(int(pm[0])) or {}).get("officiel", {}).get("rang")
        cases.append(f'<div><b>{"Bien vu" if r == 1 else "Raté" if r else "—"}</b><span>notre vainqueur, {e(_pays(g, pm[0]))}, '
                     f'{"gagne aussi en Europe" if r == 1 else f"finit {E.rang(r)}" if r else "sans rang officiel"}</span></div>')
    if po:
        r = (ch.get(int(po[0])) or {}).get("maison", {}).get("rang")
        cases.append(f'<div><b>{e(E.rang(r))}</b><span>le vrai vainqueur, {e(_pays(g, po[0]))}, chez nous</span></div>')
    colonnes = (["jury"] if jury else []) + ["public"]
    votes = ""
    if any((c.get("officiel") or {}).get("rang_public") for c in ch.values()):
        entetes = "".join(f'<span class="e">{"Jury" if k == "jury" else "Public"}</span>' for k in colonnes)
        nous = "".join(f'<b>{e(_gagnant(g, lambda c, k=k: (c.get("maison") or {}).get(k, {}).get("rang")))}</b>' for k in colonnes)
        eux = "".join(f'<b>{e(_gagnant(g, lambda c, k=k: (c.get("officiel") or {}).get("rang_" + k)))}</b>' for k in colonnes)
        votes = (f'<div class="votes" data-bloc="votes" style="grid-template-columns:auto repeat({len(colonnes)},minmax(0,1fr))">'
                 f'<span class="e" style="color:inherit">En tête</span>{entetes}<span>Chez nous</span>{nous}<span>En Europe</span>{eux}</div>')
    return f"""<section class="page" data-page="2">
{_tete(g, 2)}
<div class="int">
<div data-bloc="intro" style="display:flex;flex-direction:column;gap:4px"><span class="sur2">Le match des podiums</span>
<h2 class="gros" style="--t:42px">Le salon contre l'Europe</h2><p class="txt">{e(intro)}</p></div>
<div class="deux" data-bloc="podiums"><div><div class="bloc-t rose">Chez nous</div>{gauche}</div><div><div class="bloc-t">Le vrai résultat</div>{droit}</div></div>
{votes}
<div class="verdict" data-bloc="verdict" style="margin:auto 0 34px"><b>Le verdict de la rédaction</b><div class="chif">{''.join(cases)}</div></div>
</div></section>"""


def _ligne_rang(g: dict, cid) -> str:
    c = g["chansons"].get(int(cid)) or {}
    return (f'<div class="l"><b>{e(c.get("pays", "?"))}</b><span>{e(E.rang((c.get("maison") or {}).get("rang")))} · '
            f'{e(E.rang((c.get("officiel") or {}).get("rang")))}</span></div>')


def _comms(g: dict) -> str:
    cs = g["commentaires"]
    if not cs:
        return ""
    corps = "".join(f'<div class="comm"><span>«</span><p>{e(c["texte"])}<small>— {e(c["prenom"])} · {e(c["pays"])}</small></p></div>' for c in cs)
    return f'<div class="comms" data-bloc="commentaires"><b>Entendu dans le salon</b>{corps}</div>'


def f_page3(g: dict) -> str:
    j = g["j"]
    ch = g["chansons"]
    mieux, rates = j.get("mieux_devines") or [], j.get("plus_rates") or []
    blocs = []
    if mieux or rates:
        def note_mieux():
            if not mieux:
                return ""
            c = ch.get(int(mieux[0])) or {}
            ec = (c.get("ecart") or {}).get("rang")
            return f"{c.get('pays', '?')}, pile à sa place." if ec == 0 else f"{c.get('pays', '?')}, à {E.places(ec)} près."

        def note_rate():
            if not rates:
                return ""
            c = ch.get(int(rates[0])) or {}
            m, o = (c.get("maison") or {}).get("rang"), (c.get("officiel") or {}).get("rang")
            if m is None or o is None:
                return ""
            ec = abs(float(m) - float(o))
            return f"{c.get('pays', '?')}, {E.places(ec)} plus {'haut' if o < m else 'bas'} que chez nous."
        g_ = (f'<div class="liste"><div class="t"><b>Bien vu !</b><span>nous · vrai</span></div>'
              f'{"".join(_ligne_rang(g, x) for x in mieux[:3])}<span class="c">{e(note_mieux())}</span></div>')
        d_ = (f'<div class="liste"><div class="t" style="border-color:var(--a)"><b class="ac">Raté !</b><span>nous · vrai</span></div>'
              f'{"".join(_ligne_rang(g, x) for x in rates[:3])}<span class="c">{e(note_rate())}</span></div>')
        blocs.append(f'<div class="deux" style="gap:14px" data-bloc="devines">{g_}{d_}</div>')
    haut = g["palmares"]
    if haut:
        cases = "".join(f'<div><i>{e(E.rang(x["rang"]))}</i><b>{e(x["prenom"])}</b><span>{e("à " + E.places(x.get("ecart")))}</span></div>' for x in haut)
        blocs.append(f'<div class="nuit-b" data-bloc="palmares"><div class="t"><b>Le palmarès des voyants</b><span>écart moyen au vrai classement</span></div>'
                     f'<div class="palm" style="grid-template-columns:repeat({len(haut)},minmax(0,1fr))">{cases}</div></div>')
    blocs.append(_comms(g))
    return f"""<section class="page" data-page="3">
{_tete(g, 3)}
<div class="int" style="gap:16px;padding-bottom:34px">{''.join(blocs)}</div>
</section>"""


def _jumeaux(g: dict, place: str) -> str:
    j = g["j"]
    duos = [d for d in g["duos"]]
    if not duos:
        return '<p class="txt" data-bloc="jumeaux">Pas de jumeaux de vote ce soir.</p>'
    gr = E.grille(len(duos), place)
    if gr["vignettes"]:
        cases = "".join(f'<div>{e(E.noms_duo(j, d["cle"]))}</div>' for d in duos)
        return f'<div class="vign" data-bloc="jumeaux" style="grid-template-columns:repeat({gr["cols"]},minmax(0,1fr))">{cases}</div>'
    tranches = {str(d.get("cle")): d for d in j.get("duos") or []}
    cases = []
    petit = gr["haut"] < 90
    for d in duos:
        nom = E.noms_duo(j, d["cle"])
        photo = "" if d.get("retiree") else d.get("photo") or ""
        t = tranches.get(d["cle"]) or {}
        legende = ("Jumeaux l'un de l'autre" if t.get("reciproques") else "") + (" · " if t.get("reciproques") and t.get("tranche") else "") + (t.get("tranche") or "")
        cases.append(f'<div class="duo" style="--tn:{"15px" if petit or gr["cols"] > 2 else "19px"}">'
                     f'{_photo_duo(g, d["cle"], photo, "height:" + str(gr["haut"]) + "px", nom, "26px" if petit else "44px")}'
                     f'<span class="n">{e(nom)}</span>{"" if petit else f"<span class=c>{e(legende)}</span>"}</div>')
    return f'<div class="duos" data-bloc="jumeaux" style="grid-template-columns:repeat({gr["cols"]},minmax(0,1fr))">{"".join(cases)}</div>'


def _bas(g: dict, hauteur: int) -> str:
    ban = g["images"].get("banniere")
    return (f'<div class="bas" data-bloc="colophon" style="margin:auto -36px 0"><div class="ban" style="--hb:{hauteur}px">{_img(ban)}</div>'
            f'<div class="colo"><div><b>{_titre_mast(g["titre"])}</b><span>N° {e(g["numero"])} — fabriqué à la maison par Douze points et Gazette</span></div>'
            '<i>12</i></div></div>')


def f_page4(g: dict) -> str:
    return f"""<section class="page" data-page="4">
{_tete(g, 4)}
<div class="int" style="gap:12px">
<div data-bloc="titre-jumeaux" style="display:flex;flex-direction:column;gap:4px"><h2 class="gros" style="--t:44px">Les jumeaux <span class="ac">de vote</span></h2>
<p class="txt">Chaque soir de concours, Douze points cherche pour chacun la personne qui a fait le classement le plus proche du sien. Voici les duos de la soirée.</p></div>
{_jumeaux(g, "finale")}
{_bas(g, 84)}
</div></section>"""


# ---------------------------------------------------------------- demi-finale (livret « qualifiés »)

def q_page2(g: dict) -> str:
    j = g["j"]
    demi = j.get("demi") or {}
    top = demi.get("notre_top") or []
    qualifies = demi.get("qualifies") or []
    nous_ids = {int(x["chanson"]) for x in top}
    gauche = "".join(f'<div class="dix"><i>{k + 1}</i><b>{e(_pays(g, x["chanson"]))}</b>{COCHE if x.get("qualifie") else CROIX}</div>'
                     for k, x in enumerate(top[:10]))
    vrais = sorted(qualifies, key=lambda c: _pays(g, c).casefold())
    droite = "".join(f'<div class="dix"><b>{e(_pays(g, c))}</b>{"" if int(c) in nous_ids else "<span class=pv>Pas vu venir</span>"}</div>'
                     for c in vrais)
    devines = sum(1 for x in top if x.get("qualifie"))
    flair = (demi.get("flair") or [None])[0]
    noms = E.prenoms(j)
    pleure = demi.get("pleure") or []
    cases = [f'<div><b>{devines} / {len(qualifies) or 10}</b><span>qualifiés devinés par la maison</span></div>']
    if flair:
        cases.append(f'<div><b>{e(noms.get(int(flair["invite"]), "?"))}</b><span>{flair.get("trouves")} sur {flair.get("sur") or 10}, le meilleur flair</span></div>')
    if pleure:
        r = ((g["chansons"].get(int(pleure[0])) or {}).get("maison") or {}).get("rang")
        cases.append(f'<div><b>{e(_pays(g, pleure[0]))}</b><span>notre {e(E.rang(r))}, éliminé</span></div>')
    return f"""<section class="page" data-page="2">
{_tete(g, 2)}
<div class="int" style="gap:12px">
<div data-bloc="intro" style="display:flex;flex-direction:column;gap:4px"><span class="sur2">Qui passe en finale ?</span>
<h2 class="gros" style="--t:40px">Nos {len(top[:10]) or 10} contre les {len(qualifies) or 10} de l'Europe</h2></div>
<div class="deux" data-bloc="qualifies"><div style="display:flex;flex-direction:column;gap:3px"><div class="bloc-t rose">Nos 10 premiers</div>{gauche}</div>
<div style="display:flex;flex-direction:column;gap:3px"><div class="bloc-t">Les {len(qualifies) or 10} qualifiés</div>{droite}
<span class="note" style="margin-top:4px">Ordre alphabétique : les places seront connues après la finale.</span></div></div>
<div class="nuit-b" data-bloc="bilan" style="margin:auto 0 34px"><div class="chif" style="grid-template-columns:repeat({len(cases)},minmax(0,1fr))">{''.join(cases)}</div></div>
</div></section>"""


def q_page3(g: dict) -> str:
    j = g["j"]
    demi = j.get("demi") or {}
    ch = g["chansons"]

    def lignes(ids):
        return "".join(f'<div class="l"><b>{e(_pays(g, c))}</b><span>{e(E.rang(((ch.get(int(c)) or {}).get("maison") or {}).get("rang")))} chez nous</span></div>' for c in ids[:3])
    blocs = []
    pleure, deteste = demi.get("pleure") or [], demi.get("deteste") or []
    if pleure or deteste:
        g_ = (f'<div class="liste"><div class="t" style="border-color:var(--a)"><b class="ac">On les pleure</b></div>{lignes(pleure)}'
              f'<span class="c">{"Dans notre top 10, éliminés quand même." if pleure else "Aucun : tout notre top 10 est passé."}</span></div>')
        d_ = (f'<div class="liste"><div class="t"><b>On les déteste</b></div>{lignes(deteste)}'
              f'<span class="c">{"Tout en bas chez nous, qualifiés malgré nous." if deteste else "Aucun : la maison a bon goût."}</span></div>')
        blocs.append(f'<div class="deux" style="gap:14px" data-bloc="pleure">{g_}{d_}</div>')
    haut = g["palmares"]
    if haut:
        cases = "".join(f'<div style="flex-direction:row;justify-content:space-between;align-items:baseline"><b>{e(x["prenom"])}</b>'
                        f'<b class="ac" style="font-size:22px">{x.get("trouves")}</b></div>' for x in haut)
        blocs.append(f'<div class="nuit-b" data-bloc="flair"><div class="t"><b>Le flair des invités</b><span>qualifiés trouvés sur {haut[0].get("sur") or 10}</span></div>'
                     f'<div class="palm" style="grid-template-columns:repeat({len(haut)},minmax(0,1fr))">{cases}</div></div>')
    cc, nul = demi.get("coup_de_coeur"), demi.get("nul_point")
    if cc or nul:
        def case(cid, titre, classe=""):
            if not cid:
                return ""
            moy = ((ch.get(int(cid)) or {}).get("maison") or {}).get("moyenne")
            m = f"{float(moy):.1f}".replace(".", ",").replace(",0", "") if moy is not None else "?"
            return f'<div class="{classe}"><i>{titre}</i><b>{e(_pays(g, cid))}</b><span>{m} / 20 de moyenne</span></div>'
        blocs.append(f'<div class="cases" data-bloc="coeur">{case(cc, "Coup de cœur de la maison")}{case(nul, "Nul point maison", "pointille")}</div>')
    blocs.append(_comms(g))
    return f"""<section class="page" data-page="3">
{_tete(g, 3)}
<div class="int" style="gap:14px;padding-bottom:34px">{''.join(blocs)}</div>
</section>"""


def q_page4(g: dict) -> str:
    demi = g["j"].get("demi") or {}
    favoris = demi.get("favoris") or []
    date_finale = demi.get("date_finale") or ""
    quand = "Finale · " + (E.date_longue(date_finale)[:-5] if date_finale else "samedi")
    fav = "".join(f'<div><i>{k + 1}</i><b>{e(_pays(g, c))}</b></div>' for k, c in enumerate(favoris[:3]))
    rdv = (f'<div class="rdv" data-bloc="rendez-vous"><div class="t"><b>Rendez-vous samedi</b><span>{e(quand)}</span></div>'
           f'<div class="c"><span>Nos favoris parmi les qualifiés de ce soir :</span><div class="fav">{fav}</div></div></div>') if favoris else ""
    return f"""<section class="page" data-page="4">
{_tete(g, 4)}
<div class="int" style="gap:11px">
<div data-bloc="titre-jumeaux" style="display:flex;flex-direction:column;gap:4px"><h2 class="gros" style="--t:36px">Les jumeaux <span class="ac">de vote</span></h2>
<p class="txt" style="font-size:calc(14px*var(--k,1))">Douze points cherche pour chacun la personne qui a fait le classement le plus proche du sien.</p></div>
{_jumeaux(g, "qualifies")}
{rdv}
<p class="note" data-bloc="phrase">Le classement exact de cette demi-finale n'est publié qu'après la finale : il arrivera dans la fiche PDF de la soirée (Douze points), envoyée à chacun dès qu'il sera connu.</p>
{_bas(g, 64)}
</div></section>"""


# ---------------------------------------------------------------- document

def donnees(numero: dict, titre: str, images: dict[str, bytes | None], duo_image: Callable[[str], bytes | None]) -> dict:
    """Ce dont la mise en page a besoin, d'après une ligne de la table `eurovisions` (journal, choix de la relecture).
    `images` : octets des images gardées (sorte → octets ; absentes ou retirées : rien) ; `duo_image(immich_id)`."""
    j = numero["journal"]
    gardees = numero.get("images") or {}
    vues = {s: o for s, o in images.items() if o and gardees.get(s, True)}
    return {
        "j": j, "titre": titre, "numero": numero.get("numero_main") or E.numero_defaut(j),
        "date": E.date_longue((j.get("soiree") or {}).get("date") or ""), "livret": E.livret(j),
        "chansons": E.chansons(j), "images": vues, "image_une": E.image_une(gardees, [s for s in vues]),
        "duo_image": duo_image, "duos": numero.get("duos") or [], "une": E.invite_une(j),
        "palmares": E.haut_palmares(j), "commentaires": E.commentaires_vus(j, numero.get("commentaires") or []),
    }


def document(g: dict, mode: str = "impose") -> str:
    pages = (page1, q_page2, q_page3, q_page4) if g["livret"] == "qualifies" else (page1, f_page2, f_page3, f_page4)
    if mode == "impose":
        corps = f'<div class="feuille">{pages[3](g)}{pages[0](g)}</div><div class="feuille">{pages[1](g)}{pages[2](g)}</div>'
        page = "@page{size:297mm 210mm;margin:0}"
    else:
        corps = "".join(f'<div class="feuille">{p(g)}</div>' for p in pages)
        page = "@page{size:148.5mm 210mm;margin:0}"
    return (f'<!doctype html><html lang="fr" class="{"lecture" if mode != "impose" else "impose"} {"ecran" if mode == "ecran" else ""}">'
            f'<head><meta charset="utf-8"><title>{e(g["titre"])} — N° {e(g["numero"])}</title>'
            f'<style>{rendu_recidive.font_face()}{CSS}{page}:root{{--a:{ACCENT};--n:{NUIT}}}</style></head><body>{corps}'
            f'<script>{rendu.AJUSTER}</script></body></html>')

