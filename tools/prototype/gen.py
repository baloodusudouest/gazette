"""La Gazette — prototype du 14/11/2026 : livret A5 imposé sur A4 paysage (recto p4|p1, verso p2|p3).

Usage : python3 gen.py  → un PDF par invité dans ./sortie/
"""
import html
import pathlib
from playwright.sync_api import sync_playwright

ICI = pathlib.Path(__file__).parent
FONTS = ICI / "node_modules/@fontsource"
SORTIE = ICI / "sortie"
# Valeurs réelles : variables de la stack dans l'appli (GAZETTE_TITRE, GAZETTE_SIGNATURE, GAZETTE_LIEU).
TITRE = "La Gazette"
SIGNATURE = "Les hôtes"
LIEU = "La maison"
e = html.escape


def font_face():
    def f(fam, path, w, style="normal"):
        return (f"@font-face{{font-family:'{fam}';src:url('file://{FONTS / path}') format('woff2');"
                f"font-weight:{w};font-style:{style}}}")
    return "".join([
        f("Playfair", "playfair-display/files/playfair-display-latin-ext-700-normal.woff2", 700),
        f("Playfair", "playfair-display/files/playfair-display-latin-ext-900-normal.woff2", 900),
        f("Serif", "source-serif-4/files/source-serif-4-latin-ext-400-normal.woff2", 400),
        f("Serif", "source-serif-4/files/source-serif-4-latin-ext-600-normal.woff2", 600),
        f("Serif", "source-serif-4/files/source-serif-4-latin-ext-400-italic.woff2", 400, "italic"),
        f("Fraktur", "unifrakturmaguntia/files/unifrakturmaguntia-latin-400-normal.woff2", 400),
        f("Playfair", "playfair-display/files/playfair-display-latin-700-normal.woff2", 700),
        f("Playfair", "playfair-display/files/playfair-display-latin-900-normal.woff2", 900),
        f("Serif", "source-serif-4/files/source-serif-4-latin-400-normal.woff2", 400),
        f("Serif", "source-serif-4/files/source-serif-4-latin-600-normal.woff2", 600),
        f("Serif", "source-serif-4/files/source-serif-4-latin-400-italic.woff2", 400, "italic"),
    ])


CSS = """
@page{size:297mm 210mm;margin:0}
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
h2.gros{font-family:'Playfair',serif;font-weight:900;font-size:21pt;line-height:1.08;text-wrap:balance}
.chapo{font-size:11pt;line-height:1.35;text-wrap:pretty}
.encart{flex:0 0 33mm;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:1mm;border:0.3mm solid #161616;padding:2.5mm 1.5mm;text-align:center}
.encart .k{font-size:8.5pt;text-transform:uppercase;letter-spacing:.08em}
.encart .v{font-family:'Playfair',serif;font-weight:900;font-size:28pt;line-height:1;color:var(--a)}
.encart .l{font-size:9pt;line-height:1.25}
.breves{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:5mm;row-gap:3mm;flex:1 1 auto;align-content:start}
.breve h3{font-family:'Playfair',serif;font-weight:700;font-size:12pt;line-height:1.15;margin-bottom:1mm}
.breve p{font-size:10.5pt;line-height:1.38}
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
.item h3{font-family:'Playfair',serif;font-weight:700;font-size:12.5pt;line-height:1.15;margin-bottom:.8mm}
.item p{font-size:11pt;line-height:1.38}
.note{font-size:8.5pt;font-style:italic;line-height:1.35}
.chrono{display:flex;flex-direction:column;border-left:0.5mm solid #161616;margin-left:1.6mm}
.ev{display:flex;align-items:baseline;gap:2.6mm;padding:1.45mm 0}
.ev .pt{flex:0 0 auto;width:2.6mm;height:2.6mm;border-radius:50%;background:#161616;margin-left:-1.55mm;align-self:center}
.ev .q{flex:0 0 15mm;font-size:8.5pt;font-weight:600;text-transform:uppercase}
.ev .x{font-size:10.5pt;line-height:1.28}
.ev.moi .pt{width:3.6mm;height:3.6mm;margin-left:-2.05mm;background:var(--a)}
.ev.moi .q,.ev.moi .x{color:var(--a)}
.ev.moi .x{font-family:'Playfair',serif;font-weight:700;font-size:11pt}
.duo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:5mm}
.duo .lab{font-size:9pt;letter-spacing:.18em;text-transform:uppercase;color:var(--a);margin-bottom:1mm}
.duo p{font-size:10.5pt;line-height:1.4}
.duo h3{font-family:'Playfair',serif;font-weight:700;font-size:12pt;margin-bottom:1.2mm}
.duo .pers{font-size:10.5pt;line-height:1.45}
.mot{flex:1 1 auto;display:flex;flex-direction:column;gap:4mm;justify-content:flex-start}
.mot p{font-size:13.5pt;line-height:1.55;text-wrap:pretty}
.mot p.lettrine::first-letter{font-family:'Playfair',serif;font-weight:900;font-size:46pt;line-height:.8;float:left;padding:1.4mm 1.8mm 0 0;color:var(--a)}
.mot .sig{font-style:italic;text-align:right;font-size:13.5pt;margin-top:2mm}
.colophon{border:0.3mm solid #161616;padding:3mm;display:flex;flex-direction:column;align-items:center;gap:1mm;text-align:center}
.colophon .t{font-family:'Fraktur',serif;font-size:15pt}
.colophon p{font-size:9pt;line-height:1.35}
.orn{text-align:center;letter-spacing:.6em;color:var(--a);font-size:10pt}
"""


def page1(g):
    breves = "".join(f'<div class="breve"><h3>{e(t)}</h3><p>{e(x)}</p></div>' for t, x in g["breves"])
    return f"""<section class="page">
<div class="manchette"><span>{e(g['date_longue'])}</span><span>Édition unique</span><span>Exemplaire de {e(g['prenom'])}</span></div>
<div class="titre"><h1>{e(TITRE)}</h1><p>Le monde tel qu'il était le jour de votre naissance</p></div>
<div class="nom"><p class="surtitre">Ce jour-là naissait</p><p class="n">{e(g['nom'])}</p></div>
<div class="ouv filet"><div class="txt"><h2 class="gros">{e(g['une'][0])}</h2><p class="chapo">{e(g['une'][1])}</p></div>
<div class="encart"><span class="k">{e(g['encart'][0])}</span><span class="v">{g['encart'][1]}</span><span class="l">{g['encart'][2]}</span></div></div>
<div class="breves filet">{breves}</div>
<div class="pied"><span>Imprimé à la maison · {e(g['renvoi_p2'])}, page 2</span><span>1</span></div>
</section>"""


def page2(g):
    p2 = g["p2"]
    if p2["mode"] == "semaine":
        items = "".join(
            f'<div class="item"><div class="d"><b>{e(j)}</b><span>{e(m)}</span></div>'
            f'<div><h3>{e(t)}</h3><p>{e(x)}</p></div></div>' for j, m, t, x in p2["items"])
    else:
        items = "".join(
            f'<div class="item"><div class="lieu"><b>{e(l)}</b><span>{e(q)}</span></div>'
            f'<div><h3>{e(t)}</h3><p>{e(x)}</p></div></div>' for l, q, t, x in p2["items"])
    return f"""<section class="page">
<div class="ent"><span class="t">{e(TITRE)}</span><span class="r">{e(p2['rubrique'])}</span></div>
<div><p class="surtitre">{e(p2['surtitre'])}</p><h2 class="sec">{e(p2['titre'])}</h2></div>
<div class="liste">{items}</div>
<p class="note">{e(p2['note'])}</p>
<div class="pied"><span>Exemplaire de {e(g['prenom'])}</span><span>2</span></div>
</section>"""


def page3(g):
    evs = []
    for q, x in g["chrono"]:
        if x is None:
            evs.append(f'<div class="ev moi"><span class="pt"></span><span class="q">{e(q)}</span>'
                       f'<span class="x">Naissance de {e(g["prenom"])}</span></div>')
        else:
            qq = e(q).replace("1er", '1<span style="text-transform:none">er</span>')
            evs.append(f'<div class="ev"><span class="pt"></span><span class="q">{qq}</span><span class="x">{e(x)}</span></div>')
    return f"""<section class="page">
<div class="ent"><span class="t">{e(TITRE)}</span><span class="r">L'année &amp; la culture</span></div>
<div><p class="surtitre">Chronologie</p><h2 class="sec">{e(g['annee'])}, l'année de votre naissance</h2></div>
<div class="chrono">{''.join(evs)}</div>
<div class="duo filet"><div><p class="lab">Musique</p><p>{g['musique']}</p></div><div><p class="lab">Cinéma</p><p>{g['cinema']}</p></div></div>
<div class="duo filet" style="flex:1 1 auto"><div><h3>Nés un {e(g['jour_mois'])}</h3><p class="pers">{e(g['nes'])}</p></div>
<div><h3>Disparus un {e(g['jour_mois'])}</h3><p class="pers">{e(g['morts'])}</p></div></div>
<div class="pied"><span>Exemplaire de {e(g['prenom'])}</span><span>3</span></div>
</section>"""


def page4(g):
    paras = "".join(f'<p class="{"lettrine" if i == 0 else ""}">{e(t)}</p>' for i, t in enumerate(g["mot"]))
    return f"""<section class="page">
<div class="ent"><span class="t">{e(TITRE)}</span><span class="r">Le mot des hôtes</span></div>
<div><p class="surtitre">Édition spéciale</p><h2 class="sec">Bienvenue, {e(g['prenom'])}</h2></div>
<div class="mot filet">{paras}<p class="sig">{e(SIGNATURE)}</p></div>
<p class="orn">✦ ✦ ✦</p>
<div class="colophon"><span class="t">{e(LIEU)}</span>
<p>Exemplaire unique, imprimé pour {e(g['prenom'])} le {e(g['imprime_le'])}.</p></div>
<div class="pied"><span>Imprimé à la maison</span><span>4</span></div>
</section>"""


def document(g):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Gazette — {e(g['nom'])}</title>
<style>{font_face()}{CSS}:root{{--a:{g.get('accent', '#9E1B1B')}}}</style></head><body>
<div class="feuille">{page4(g)}{page1(g)}</div>
<div class="feuille">{page2(g)}{page3(g)}</div>
</body></html>"""


CAMILLE = {
    # Personne inventée (dépôt public) : seuls les faits de la date sont réels.
    "prenom": "Camille", "nom": "Camille Fabre",
    "date_longue": "Jeudi 7 juillet 1988", "annee": "1988", "jour_mois": "7 juillet",
    "une": ("Gorbatchev veut un président pour l'URSS",
            "Devant la conférence du Parti communiste, le numéro un soviétique défend une refonte des institutions "
            "pour ancrer la perestroïka."),
    "encart": ("Moscou", "5 000", "délégués<br>appelés à voter"),
    "breves": [
        ("Airbus iranien", "Reagan présente ses excuses ; Téhéran appelle à ne pas se venger trop vite."),
        ("Amnistie", "L'Assemblée adopte le texte à l'aube, après deux séances houleuses."),
        ("Tour de France", "Van Poppel s'impose au Mans, Teun Van Vliet garde le maillot jaune."),
        ("Église d'Angleterre", "Le synode anglican dit oui aux femmes prêtres."),
    ],
    "renvoi_p2": "La semaine",
    "p2": {
        "mode": "semaine", "rubrique": "La semaine", "surtitre": "Du 1er au 7 juillet 1988",
        "titre": "Les grands titres de la semaine",
        "items": [
            ("3", "juil.", "Drame dans le Golfe", "Un croiseur américain abat par erreur un Airbus d'Iran Air."),
            ("5", "juil.", "La Cour des comptes conseille l'État", "Son rapport annuel épingle des abus et propose des pistes."),
            ("5", "juil.", "Washington : Meese s'en va", "Le ministre de la justice de Ronald Reagan annonce son départ."),
            ("6", "juil.", "L'amnistie passe à l'Assemblée", "Socialistes et communistes votent pour ; le texte repart au Sénat."),
            ("7", "juil.", "Le jour J", "Un jeudi de début d'été, en plein Tour de France : naissance de Camille."),
        ],
        "note": "Édition automatique : grands titres de la semaine d'après les chronologies publiques.",
    },
    "chrono": [
        ("14 avril", "Accords de Genève : l'URSS va quitter l'Afghanistan"),
        ("8 mai", "François Mitterrand réélu président de la République"),
        ("26 juin", "Accords de Matignon sur la Nouvelle-Calédonie"),
        ("7 juil.", None),
        ("20 août", "Cessez-le-feu entre l'Iran et l'Irak après huit ans de guerre"),
        ("17 sept.", "Ouverture des Jeux olympiques de Séoul"),
        ("8 nov.", "George Bush élu président des États-Unis"),
        ("1er déc.", "Création du revenu minimum d'insertion (RMI)"),
    ],
    "musique": "<strong>Sandy</strong>, « J'ai faim de toi », n°1 du Top 50 après les huit semaines de "
               "<strong>Florent Pagny</strong> ; « Nuit de folie » arrive.",
    "cinema": "<strong>Le Grand Bleu</strong> de Luc Besson et <strong>La vie est un long fleuve tranquille</strong>.",
    "nes": "Gustav Mahler (1860), Marc Chagall (1887), George Cukor (1899), Ringo Starr (1940)",
    "morts": "Henri Nestlé (1890), Johanna Spyri (1901), Arthur Conan Doyle (1930)",
    "mot": [
        "Le 7 juillet 1988, Moscou parlait de réformes et le Tour roulait à l'heure néerlandaise. "
        "Ce soir, c'est ici que l'on vous attend.",
        "Ce petit journal est à vous : il raconte le monde tel qu'il tournait le jour de votre naissance.",
        "Installez-vous, reposez-vous, et surtout faites comme chez vous.",
    ],
    "imprime_le": "14 novembre 2026",
}


def main():
    SORTIE.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page()
        for slug, g in (("exemple", CAMILLE),):
            h = SORTIE / f"gazette_{slug}.html"
            h.write_text(document(g), encoding="utf-8")
            pg.goto(h.as_uri())
            pg.wait_for_timeout(400)
            pg.pdf(path=str(SORTIE / f"gazette_{slug}.pdf"), width="297mm", height="210mm",
                   print_background=True, prefer_css_page_size=True)
            print("ok", slug)
        nav.close()


if __name__ == "__main__":
    main()
