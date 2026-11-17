"""0.11.4 : un vrai code-barres Code 128 (jeu B) en SVG, pour le petit clin d'œil de la page 4 de La Récidive.

Le message (réglable dans l'édition, « Reviens vite, {prénom} ! » par défaut) est lisible par n'importe quelle appli de
scan. Le jeu B ne connaît que l'ASCII : accents retirés (é → e), autres signes remplacés par une espace. Aucun texte
lisible sous les barres : c'est la surprise."""
from __future__ import annotations

import unicodedata

MAXI = 30            # caractères : le code tient dans la largeur de la page et reste lisible (module ≈ 0,26 mm)

# Largeurs barre/espace de chaque symbole (valeurs 0 à 106), table standard du Code 128
MOTIFS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 "
    "123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 "
    "232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 "
    "313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 "
    "111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 "
    "114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112"
).split()
DEPART_B, ARRET = 104, 106


def ascii_(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("’", "'").replace("«", '"').replace("»", '"').replace("œ", "oe").replace("Œ", "OE").replace("°", "o")
    return "".join(c if 32 <= ord(c) <= 126 else " " for c in t).strip()[:MAXI]


def valeurs(texte: str) -> list[int]:
    """Les symboles : départ B, caractères, somme de contrôle, arrêt."""
    v = [DEPART_B] + [ord(c) - 32 for c in ascii_(texte)]
    controle = (v[0] + sum(i * x for i, x in enumerate(v[1:], start=1))) % 103
    return v + [controle, ARRET]


def modules(texte: str) -> str:
    """« 1 » = barre, « 0 » = espace, un caractère par module."""
    res = []
    for v in valeurs(texte):
        for i, largeur in enumerate(MOTIFS[v]):
            res.append(("1" if i % 2 == 0 else "0") * int(largeur))
    return "".join(res)


def svg(texte: str, hauteur: int = 40, module: float = 1.0) -> str:
    m = modules(texte)
    rects, x, i = [], 10, 0           # zone blanche de 10 modules de chaque côté
    while i < len(m):
        j = i
        while j < len(m) and m[j] == m[i]:
            j += 1
        if m[i] == "1":
            rects.append(f'<rect x="{x + i}" y="0" width="{j - i}" height="{hauteur}"/>')
        i = j
    largeur = len(m) + 20
    return (f'<svg class="cb" xmlns="http://www.w3.org/2000/svg" width="{largeur * module:.0f}" height="{hauteur}" '
            f'viewBox="0 0 {largeur} {hauteur}" shape-rendering="crispEdges" role="img" aria-label="code-barres">'
            f'<g fill="#111">{"".join(rects)}</g></svg>')
