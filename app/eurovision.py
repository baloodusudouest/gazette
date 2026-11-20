"""0.28 : « Good Evening Europe! », l'édition spéciale Eurovision (troisième journal de Gazette), un numéro par soirée
Douze points clôturée. Règles pures (aucune lecture), d'après le dossier du 20/11/2026 (§ 8, 9 et 10 priment) :

- Tous les calculs (rangs, écarts, palmarès, plus proche, flair, qualifiés…) viennent de Douze points ; Gazette met en
  page et choisit seulement ce qui est imprimé.
- Livret « finale » (finale, sélection nationale) ou « qualifies » (demi-finale, `demi` non nul).
- N° = `soiree.numero` (« 2027 · Eurovision · Finale »), corrigeable à la main.
- Photo de la une : photo apéro, sinon poster, sinon logo ; logo en pastille ; bannière en bas de la page 4 (bandeau
  bleu nuit si absente). Chaque image peut être gardée ou retirée à la relecture.
- Palmarès imprimé : le haut seulement, l'invité en une retiré.
- Commentaires : 2 ou 3 tirés au hasard, sans IA et sans mention ; Changer = nouveau tirage, Refuser = retiré.
- Soirée sans jury chez nous ou sans vrai jury : rien sur le jury (pas de colonne vide)."""
from __future__ import annotations

import random

LIVRETS = ("finale", "qualifies")
MAXI_COMMENTAIRE = 220            # un commentaire plus long n'est pas tiré (la page 3 est petite)
HAUT = 3                          # haut du palmarès imprimé
SORTES_UNE = ("apero", "poster", "logo")     # photo de la une, dans l'ordre de préférence
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def livret(j: dict) -> str:
    """« qualifies » pour une demi-finale (bloc `demi`), sinon « finale »."""
    if j.get("demi"):
        return "qualifies"
    return "finale"


def numero_defaut(j: dict) -> str:
    s = j.get("soiree") or {}
    return str(s.get("numero") or f"{s.get('annee') or ''} · {s.get('concours') or 'Eurovision'} · {s.get('type') or 'Finale'}").strip(" ·")


def date_longue(iso: str, jour: bool = True) -> str:
    from datetime import date
    try:
        d = date.fromisoformat(str(iso or "")[:10])
    except ValueError:
        return ""
    texte = f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"
    return f"{JOURS[d.weekday()]} {texte}" if jour else texte


def prenoms(j: dict) -> dict[int, str]:
    return {int(i["id"]): str(i.get("prenom") or "?") for i in j.get("invites") or [] if "id" in i}


def chansons(j: dict) -> dict[int, dict]:
    return {int(c["id"]): c for c in j.get("chansons") or [] if "id" in c}


def rang(x) -> str:
    """Un rang lisible : 1 → « 1er », 3 → « 3e », 2.5 (ex æquo) → « 2,5e », None → « — »."""
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if v.is_integer():
        n = int(v)
        return "1er" if n == 1 else f"{n}e"
    return f"{v:.1f}".replace(".", ",") + "e"


def places(x) -> str:
    """Écart en clair, en rang : 2.33 → « 2,3 places », 1 → « 1 place », 0 → « 0 place »."""
    try:
        v = round(float(x), 1)
    except (TypeError, ValueError):
        return ""
    texte = str(int(v)) if v.is_integer() else f"{v:.1f}".replace(".", ",")
    return f"{texte} place{'s' if v >= 2 else ''}"


def ecart_clair(x) -> str:
    """« à 2,3 places en moyenne » (dossier § 8.7)."""
    p = places(x)
    return f"à {p} en moyenne" if p else ""


def avec_jury(j: dict) -> bool:
    """Les éléments jury ne s'impriment que si la soirée a un jury chez nous et un vrai jury."""
    s = j.get("soiree") or {}
    return bool(s.get("avec_jury_maison")) and bool(s.get("avec_jury_officiel"))


# ---------------------------------------------------------------- l'invité de la une et le haut du palmarès

def invite_une(j: dict) -> dict | None:
    """Finale : le plus proche du vrai classement (`plus_proche`, invités complets seulement) ; demi : celui qui a
    trouvé le plus de qualifiés (`demi.flair[0]`). {id, prenom, phrase, ...} ou None."""
    noms = prenoms(j)
    if livret(j) == "qualifies":
        flair = (j.get("demi") or {}).get("flair") or []
        if not flair:
            return None
        f = flair[0]
        i = int(f["invite"])
        return {"id": i, "prenom": noms.get(i, "?"), "trouves": f.get("trouves"), "sur": f.get("sur") or 10}
    pp = j.get("plus_proche")
    if pp is None:
        return None
    i = int(pp)
    ligne = next((x for x in j.get("palmares") or [] if int(x.get("invite", -1)) == i), {})
    return {"id": i, "prenom": noms.get(i, "?"), "ecart": ligne.get("ecart_moyen")}


def haut_palmares(j: dict, n: int = HAUT) -> list[dict]:
    """Le haut du palmarès imprimé, l'invité en une retiré. Finale : invités complets, rang dans le palmarès complet ;
    demi : le flair (qualifiés trouvés)."""
    noms, une = prenoms(j), invite_une(j)
    sauf = une["id"] if une else None
    if livret(j) == "qualifies":
        res = []
        for k, f in enumerate((j.get("demi") or {}).get("flair") or []):
            i = int(f["invite"])
            if i != sauf:
                res.append({"id": i, "prenom": noms.get(i, "?"), "rang": k + 1, "trouves": f.get("trouves"), "sur": f.get("sur") or 10})
        return res[:n]
    res = []
    complets = [x for x in j.get("palmares") or [] if x.get("complet")]
    for k, x in enumerate(complets):
        i = int(x["invite"])
        if i != sauf:
            res.append({"id": i, "prenom": noms.get(i, "?"), "rang": k + 1, "ecart": x.get("ecart_moyen")})
    return res[:n]


# ---------------------------------------------------------------- commentaires tirés au hasard

def cle_commentaire(c: dict) -> str:
    return f"{int(c.get('invite', 0))}-{int(c.get('chanson', 0))}"


def commentaires_possibles(j: dict) -> list[dict]:
    """Les commentaires qu'on peut tirer : non vides, pas trop longs."""
    res = []
    for c in j.get("commentaires") or []:
        t = " ".join(str(c.get("texte") or "").split())
        if t and len(t) <= MAXI_COMMENTAIRE:
            res.append({**c, "texte": t, "cle": cle_commentaire(c)})
    return res


def tirer(j: dict, deja: list[str] | None = None, refuses: list[str] | None = None, n: int | None = None,
          graine: int | None = None) -> list[str]:
    """Un tirage de 2 ou 3 commentaires (clés « invité-chanson »), au hasard, en variant les invités et les chansons ;
    jamais un commentaire refusé ni déjà pris (`deja` : ceux qu'on garde)."""
    alea = random.Random(graine)
    deja, refuses = list(deja or []), set(refuses or [])
    possibles = [c for c in commentaires_possibles(j) if c["cle"] not in refuses and c["cle"] not in deja]
    alea.shuffle(possibles)
    n = n if n is not None else alea.choice((2, 3))
    pris = list(deja)
    invites = {k.split("-")[0] for k in pris}
    titres = {k.split("-")[1] for k in pris}
    for passe in (0, 1):          # d'abord des invités et des chansons pas encore pris, puis n'importe lesquels
        for c in possibles:
            if len(pris) >= n:
                break
            if c["cle"] in pris:
                continue
            i, ch = str(c["invite"]), str(c["chanson"])
            if passe == 0 and (i in invites or ch in titres):
                continue
            pris.append(c["cle"])
            invites.add(i)
            titres.add(ch)
    return pris[:max(n, len(deja))]


def changer_commentaire(j: dict, choisis: list[str], cle: str, refuses: list[str] | None = None,
                        graine: int | None = None) -> list[str]:
    """Remplace un commentaire par un autre tiré au hasard (même place) ; s'il n'en reste pas, il est retiré."""
    autres = [k for k in choisis if k != cle]
    nouveau = tirer(j, autres, list(refuses or []) + [cle], n=len(autres) + 1, graine=graine)
    remplacant = [k for k in nouveau if k not in autres]
    return [remplacant[0] if k == cle else k for k in choisis] if remplacant else autres


def commentaires_vus(j: dict, cles: list[str]) -> list[dict]:
    """Les commentaires choisis, prêts à imprimer : {cle, texte, prenom, pays}."""
    noms, ch = prenoms(j), chansons(j)
    par = {c["cle"]: c for c in commentaires_possibles(j)}
    res = []
    for k in cles:
        c = par.get(k)
        if c:
            res.append({"cle": k, "texte": c["texte"], "prenom": noms.get(int(c["invite"]), "?"),
                        "pays": (ch.get(int(c["chanson"])) or {}).get("pays", "")})
    return res


# ---------------------------------------------------------------- photos des duos

def duos_defaut(j: dict, disponible=lambda immich_id: True) -> list[dict]:
    """Un choix par duo : la première photo Immich disponible (aperçu lisible), sinon aucune (logo en repli)."""
    res = []
    for d in j.get("duos") or []:
        ids = [str(p.get("immich_id")) for p in d.get("photos") or [] if p.get("immich_id")]
        photo = next((x for x in ids if disponible(x)), "")
        res.append({"cle": str(d.get("cle")), "photo": photo, "retiree": False})
    return res


def accorder_duos(j: dict, anciens: list[dict], disponible=lambda immich_id: True) -> list[dict]:
    """Nouvelle version du journal : garde le choix fait à la relecture pour les duos qui existent encore."""
    par = {d["cle"]: d for d in anciens or []}
    res = []
    for d in duos_defaut(j, disponible):
        a = par.get(d["cle"])
        ids = photos_duo(j, d["cle"])
        if a and (a.get("photo") in ids or not a.get("photo")):
            d = {**d, "photo": a.get("photo") or d["photo"], "retiree": bool(a.get("retiree"))}
        res.append(d)
    return res


def photos_duo(j: dict, cle: str) -> list[str]:
    d = next((x for x in j.get("duos") or [] if str(x.get("cle")) == cle), None)
    return [str(p.get("immich_id")) for p in (d or {}).get("photos") or [] if p.get("immich_id")]


def noms_duo(j: dict, cle: str) -> str:
    noms = prenoms(j)
    d = next((x for x in j.get("duos") or [] if str(x.get("cle")) == cle), None)
    return " & ".join(noms.get(int(i), "?") for i in (d or {}).get("invites") or [])


def duo_de(j: dict, invite: int, choix: list[dict]) -> dict | None:
    """Le duo de cet invité qui a une photo gardée (pour la une), sinon son premier duo."""
    leurs = [d for d in j.get("duos") or [] if int(invite) in [int(i) for i in d.get("invites") or []]]
    par = {c["cle"]: c for c in choix or []}
    for d in leurs:
        c = par.get(str(d.get("cle")))
        if c and c.get("photo") and not c.get("retiree"):
            return {"cle": str(d["cle"]), "photo": c["photo"]}
    return {"cle": str(leurs[0]["cle"]), "photo": ""} if leurs else None


def grille(n: int, place: str = "finale") -> dict:
    """La grille des jumeaux selon le nombre de duos (conseil du 20/11) ; au-delà, repli en vignettes."""
    if place == "qualifies":
        if n <= 2:
            return {"cols": 2, "haut": 130, "vignettes": False}
        if n <= 3:
            return {"cols": 3, "haut": 104, "vignettes": False}
        if n <= 6:
            return {"cols": 3, "haut": 62, "vignettes": False}
        return {"cols": 4, "haut": 0, "vignettes": True}
    if n <= 2:
        return {"cols": 2, "haut": 230, "vignettes": False}
    if n <= 4:
        return {"cols": 2, "haut": 132, "vignettes": False}
    if n <= 6:
        return {"cols": 3, "haut": 112, "vignettes": False}
    if n <= 9:
        return {"cols": 3, "haut": 64, "vignettes": False}
    return {"cols": 4, "haut": 0, "vignettes": True}


# ---------------------------------------------------------------- images de l'évènement

def images_presentes(j: dict) -> list[str]:
    """Les images que Douze points fournit pour ce journal (apéro aussi par Immich)."""
    imgs = j.get("images") or {}
    res = [s for s in ("apero", "poster", "logo", "banniere") if imgs.get(s)]
    if "apero" not in res and j.get("apero_immich_id"):
        res.insert(0, "apero")
    return res


def image_une(gardees: dict[str, bool], presentes: list[str]) -> str:
    """La sorte d'image de la une : apéro, sinon poster, sinon logo (parmi celles présentes et gardées) ; vide : aucune."""
    return next((s for s in SORTES_UNE if s in presentes and gardees.get(s, True)), "")
