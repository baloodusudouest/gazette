"""Gazette : « le monde le jour de votre naissance », un livret A5 par proche, préparé une fois et réimprimé
à chaque visite.

Routes : /health (publique) ; /api/… (session) ; /ha/… (jeton de Home Assistant) ; puis l'interface.
Gazette n'écrit chez personne : ni dans carnet, ni dans Immich, ni dans Home Assistant. L'impression (temps 3)
sera sa seule écriture extérieure, refusée en lecture seule."""
from __future__ import annotations

import asyncio
import hmac
import json
import queue
import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from . import __version__, anniversaire, culture, journal, rendu
from .auth import COMMUN, DUREE, Sessions
from .base import ETATS, Base, maintenant
from .config import APPLI, Config, charger
from .regles import bloc_depuis, preparer
from .sources import Sources

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
BLOCS = ("une", "breve", "p2", "chrono")


def _fichier_generation(cfg: Config):
    return cfg.data / "session_generation"


def _lire_generation(cfg: Config) -> int:
    try:
        return int(_fichier_generation(cfg).read_text().strip())
    except (OSError, ValueError):
        return 0


# ================================================================ préparation des livrets (une file, un ouvrier)

def _preparer(pid: int) -> None:
    base: Base = ETAT["base"]
    p = base.personne(pid)
    if not p or not p["naissance"]:
        return
    base.maj_livret(pid, etat="en_preparation", erreur="")
    try:
        r = preparer(ETAT["sources"], date.fromisoformat(p["naissance"]), p["pays"])
    except Exception as ex:  # noqa: BLE001 — l'erreur est montrée dans À traiter
        base.maj_livret(pid, etat="a_preparer", erreur=f"{type(ex).__name__} : {ex}"[:300])
        base.noter("erreur", pid, str(ex)[:200])
        return
    ancien = base.livret(pid) or {}
    contenu = r["contenu"]
    contenu["sources"], contenu["notes"] = r["sources"], r["notes"]
    # Page 3 : musique et cinéma depuis le top 5 culturel de l'année ; ce qui a été écrit à la main survit
    top = ETAT["culture"].annee(int(p["naissance"][:4]))
    r["propositions"]["culture"] = top
    if any(top.values()):
        contenu.update(culture.textes(top))
        r["sources"].append("top5")
    for cle in ("musique", "cinema"):
        if (ancien.get("contenu") or {}).get(cle) and (ancien.get("contenu") or {}).get(cle + "_main"):
            contenu[cle] = ancien["contenu"][cle]
            contenu[cle + "_main"] = True
    vide = not contenu["une"].get("titre") and not contenu["chrono"]
    base.maj_livret(pid, etat="a_preparer" if vide else "a_relire", contenu=contenu, propositions=r["propositions"],
                    prepare_le=maintenant(), approuve_le="",
                    erreur=("Aucune source lisible : " + "; ".join(r["notes"])[:250]) if vide else "")
    base.noter("preparation", pid, ", ".join(r["sources"]))


def _ouvrier() -> None:
    file: queue.Queue = ETAT["file"]
    while True:
        pid = file.get()
        if pid is None:
            return
        try:
            _preparer(pid)
        finally:
            ETAT["en_file"].discard(pid)
            file.task_done()


def demander_preparation(pid: int) -> None:
    if ETAT["cfg"].synchrone:
        _preparer(pid)
        return
    if pid in ETAT["en_file"]:
        return
    ETAT["en_file"].add(pid)
    ETAT["base"].maj_livret(pid, etat="en_preparation", erreur="")
    ETAT["file"].put(pid)


@asynccontextmanager
async def cycle(app: FastAPI):
    cfg = ETAT.get("cfg") or charger()
    cfg.data.mkdir(parents=True, exist_ok=True)
    base = Base(cfg.data / "gazette.db")
    ETAT.update(cfg=cfg, sessions=Sessions(APPLI, cfg.password, _lire_generation(cfg)), base=base,
                file=queue.Queue(), en_file=set(), culture=culture.Culture(cfg.data))
    ETAT.setdefault("sources", Sources(base, actives=cfg.sources_actives, larousse=cfg.larousse))
    ETAT["sources"].larousse_actif = journal.charger(base, cfg)["larousse"]
    ouvrier = threading.Thread(target=_ouvrier, daemon=True, name="preparation")
    ouvrier.start()
    # Livrets restés « en préparation » (redémarrage pendant une lecture) : on reprend
    for p in base.personnes():
        lv = base.livret(p["id"])
        if lv and lv["etat"] == "en_preparation":
            demander_preparation(p["id"])
    yield
    ETAT["file"].put(None)
    ETAT["sources"].fermer()
    base.fermer()


app = FastAPI(title=APPLI, version=__version__, lifespan=cycle, docs_url=None, redoc_url=None)


# ================================================================ sécurité

@app.middleware("http")
async def garde(request: Request, appel):
    chemin = request.url.path
    if chemin.startswith("/ha/"):
        jeton = ETAT["cfg"].jeton_ha
        if not jeton or not hmac.compare_digest(request.headers.get("authorization", "").encode(), f"Bearer {jeton}".encode()):
            return JSONResponse({"detail": "Jeton manquant ou invalide."}, status_code=401)
    elif chemin.startswith("/api/") and chemin not in PUBLIQUES and not ETAT["sessions"].connecte(request.cookies):
        return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    reponse = await appel(request)
    if chemin.startswith(("/api/", "/ha/")):
        reponse.headers["Cache-Control"] = "no-store"
    return reponse


class LectureSeule(Exception):
    pass


def exiger_ecriture(quoi: str = "") -> None:
    """En tête de toute route qui écrit hors de Gazette (l'impression, au temps 3)."""
    if ETAT["cfg"].lecture_seule:
        raise LectureSeule(f"Mode lecture seule : rien n'est envoyé{' à ' + quoi if quoi else ''}.")


@app.exception_handler(LectureSeule)
async def _lecture_seule(_: Request, exc: LectureSeule):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.get("/health")
def sante():
    """Public. Pour la tuile de l'Anneau : nombres seulement, aucun nom."""
    try:
        t = a_traiter()
        return {"ok": True, "version": __version__, "livrets": len(ETAT["base"].personnes()), "a_traiter": t["total"]}
    except Exception:  # noqa: BLE001 — la santé répond même si la base est occupée
        return {"ok": True, "version": __version__}


# ================================================================ connexion

@app.get("/api/session")
def session(request: Request):
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__,
            "lecture_seule": ETAT["cfg"].lecture_seule}


@app.post("/api/connexion")
async def connexion(corps: dict = Body(...)):
    s = ETAT["sessions"]
    if ETAT["cfg"].attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict")
    return r


@app.post("/api/deconnexion")
def deconnexion():
    s = ETAT["sessions"]
    s.generation += 1
    try:
        _fichier_generation(ETAT["cfg"]).write_text(str(s.generation))
    except OSError:
        pass
    r = JSONResponse({"ok": True})
    r.delete_cookie(s.cookie)
    r.delete_cookie(COMMUN)
    return r


# ================================================================ outils

def _date(v, nom: str = "date") -> date:
    try:
        return date.fromisoformat(str(v or "")[:10])
    except ValueError:
        raise HTTPException(422, f"{nom.capitalize()} illisible (AAAA-MM-JJ).")


def _personne_ou_404(pid: int) -> dict:
    p = ETAT["base"].personne(pid)
    if not p:
        raise HTTPException(404, "Fiche introuvable.")
    return p


def _prenom(p: dict) -> str:
    return p.get("prenom") or p["nom"].split(" ")[0]


def _sejours_de(pid: int) -> list[dict]:
    return [s for s in ETAT["base"].sejours() if any(i["personne_id"] == pid for i in s["invites"])]


def _anniversaires_de(p: dict) -> list[dict]:
    """Les séjours à venir de cette personne où son anniversaire est proche (± 14 jours)."""
    if not p.get("naissance"):
        return []
    sortie, ignores = [], ETAT["base"].ignores("anniversaire")
    for s in _sejours_de(p["id"]):
        cas = anniversaire.proche(date.fromisoformat(p["naissance"]), date.fromisoformat(s["du"]),
                                  date.fromisoformat(s["jusqu_au"]))
        if cas:
            cle = f"{p['id']}:{s['du']}"
            sortie.append({**cas, "cle": cle, "ignore": cle in ignores, "sejour": {k: s[k] for k in ("chambre", "du", "jusqu_au")},
                           "phrases": anniversaire.phrases(cas, _prenom(p))})
    return sortie


def _resume(p: dict) -> dict:
    lv = ETAT["base"].livret(p["id"]) or {}
    c = lv.get("contenu") or {}
    sej = _sejours_de(p["id"])
    return {"id": p["id"], "nom": p["nom"], "prenom": p["prenom"], "naissance": p["naissance"], "pays": p["pays"],
            "alias": p["alias"], "etat": lv.get("etat", "a_preparer"), "erreur": lv.get("erreur", ""),
            "approuve_le": lv.get("approuve_le", ""), "une": (c.get("une") or {}).get("titre", ""),
            "prochain_sejour": ({k: sej[0][k] for k in ("chambre", "du", "jusqu_au")} if sej else None),
            "anniversaire": next((a for a in _anniversaires_de(p) if not a["ignore"]), None)}


def _journal() -> dict:
    return journal.charger(ETAT["base"], ETAT["cfg"])


def _lien(pid: int) -> str:
    return f"{ETAT['cfg'].adresse}/#/livret/{pid}" if ETAT["cfg"].adresse else f"/#/livret/{pid}"


# ================================================================ fiches et livrets

@app.get("/api/livrets")
def livrets():
    base: Base = ETAT["base"]
    return {"livrets": [_resume(p) for p in base.personnes()],
            "sejours": base.sejours(), "etats": list(ETATS)}


def _champs_personne(corps: dict, exiger: bool) -> dict:
    champs = {}
    if exiger or "nom" in corps:
        nom = " ".join(str(corps.get("nom", "")).split())[:80]
        if not nom:
            raise HTTPException(422, "Nom manquant.")
        champs["nom"] = nom
    if "prenom" in corps or exiger:
        champs["prenom"] = " ".join(str(corps.get("prenom") or "").split())[:40] or (champs.get("nom", "").split(" ")[0] if exiger else "")
    if exiger or "naissance" in corps:
        d = _date(corps.get("naissance"), "date de naissance")
        if not date(1900, 1, 1) <= d <= date.today():
            raise HTTPException(422, "Date de naissance hors des dates possibles.")
        champs["naissance"] = d.isoformat()
    if "pays" in corps:
        champs["pays"] = str(corps.get("pays") or "France")[:40]
    if "alias" in corps:
        champs["alias"] = [" ".join(str(a).split())[:80] for a in (corps.get("alias") or []) if str(a).strip()][:8]
    return champs


@app.post("/api/personnes")
def creer_personne(corps: dict = Body(...)):
    c = _champs_personne(corps, exiger=True)
    base: Base = ETAT["base"]
    pid = base.creer_personne(c["nom"], c["prenom"], c["naissance"], c.get("pays", "France"), c.get("alias"))
    base.noter("fiche", pid, "créée")
    demander_preparation(pid)
    return {"id": pid}


@app.put("/api/personnes/{pid}")
def modifier_personne(pid: int, corps: dict = Body(...)):
    avant = _personne_ou_404(pid)
    c = _champs_personne(corps, exiger=False)
    ETAT["base"].modifier_personne(pid, **c)
    if c.get("naissance") and c["naissance"] != avant["naissance"]:
        demander_preparation(pid)
    return {"ok": True}


@app.delete("/api/personnes/{pid}")
def supprimer_personne(pid: int):
    _personne_ou_404(pid)
    ETAT["base"].supprimer_personne(pid)
    ETAT["base"].noter("fiche", None, f"fiche {pid} supprimée")
    return {"ok": True}


@app.get("/api/livrets/{pid}")
def livret(pid: int):
    p = _personne_ou_404(pid)
    lv = ETAT["base"].livret(pid)
    naissance = date.fromisoformat(p["naissance"])
    j = _journal()
    return {"personne": p, "livret": {**lv, "mot_defaut": rendu.mot_par_defaut(p, naissance, j)},
            "sejours": _sejours_de(pid), "anniversaires": _anniversaires_de(p), "signature": j["signature"]}


@app.put("/api/livrets/{pid}")
def enregistrer_livret(pid: int, corps: dict = Body(...)):
    """Les modifications de la relecture. Un livret approuvé qui change repasse « à relire »."""
    _personne_ou_404(pid)
    base: Base = ETAT["base"]
    lv = base.livret(pid)
    champs = {}
    if "contenu" in corps and isinstance(corps["contenu"], dict):
        recu = corps["contenu"]
        contenu = {**lv["contenu"], **{k: v for k, v in recu.items()
                                       if k in ("une", "breves", "p2", "chrono", "musique", "cinema", "nes", "morts")}}
        for cle in ("musique", "cinema"):
            if cle in recu and recu[cle] != lv["contenu"].get(cle):
                contenu[cle + "_main"] = True            # écrit à la main : une nouvelle préparation le garde
        champs["contenu"] = contenu
    if "mot" in corps:
        champs["mot"] = str(corps["mot"] or "")[:4000]
    if "accent" in corps:
        champs["accent"] = str(corps["accent"] or "#9E1B1B")[:7]
    if champs:
        if lv["etat"] == "approuve":
            champs["etat"], champs["approuve_le"] = "a_relire", ""
        base.maj_livret(pid, **champs)
    return {"ok": True, "etat": base.livret(pid)["etat"]}


@app.post("/api/livrets/{pid}/choisir")
def choisir(pid: int, corps: dict = Body(...)):
    """Remplace un bloc par une proposition : {bloc: une|breve|p2|chrono, proposition, index (rang du bloc)}."""
    p = _personne_ou_404(pid)
    base: Base = ETAT["base"]
    lv = base.livret(pid)
    bloc = corps.get("bloc")
    if bloc not in BLOCS:
        raise HTTPException(422, "Bloc inconnu.")
    pool = lv["propositions"].get("annee" if bloc == "chrono" else "evenements", [])
    f = next((x for x in pool if x["id"] == corps.get("proposition")), None)
    if not f:
        raise HTTPException(404, "Proposition introuvable.")
    d = date.fromisoformat(p["naissance"])
    nouveau = bloc_depuis(f, bloc, d)
    c = lv["contenu"]
    if bloc == "une":
        c["une"] = nouveau
    else:
        cle = {"breve": "breves", "chrono": "chrono", "p2": "p2"}[bloc]
        liste = c["p2"]["items"] if bloc == "p2" else c.setdefault(cle, [])
        i = corps.get("index")
        if isinstance(i, int) and 0 <= i < len(liste):
            liste[i] = nouveau
        else:
            liste.append(nouveau)
        if bloc == "chrono":
            liste.sort(key=lambda x: x.get("date", ""))
        if bloc == "p2":
            liste.sort(key=lambda x: x.get("date", ""))
    base.maj_livret(pid, contenu=c, **({"etat": "a_relire", "approuve_le": ""} if lv["etat"] == "approuve" else {}))
    return {"ok": True, "contenu": c}


@app.post("/api/livrets/{pid}/preparer")
def repreparer(pid: int, corps: dict = Body(default={})):
    """Prépare de nouveau le livret (le mot des hôtes, la musique et le cinéma sont gardés).
    `relire: true` oublie d'abord les pages gardées pour cette date."""
    p = _personne_ou_404(pid)
    if corps.get("relire"):
        d = date.fromisoformat(p["naissance"])
        src = ETAT["sources"]
        for cle in (f"wp:fr:{src.titre_mois(d.year, d.month)}", f"wp:fr:{d.year} en France", f"wp:fr:{d.year}",
                    f"wp:fr:{src.titre_jour(d.day, d.month)}", f"wp:en:{src.titre_mois_en(d.year, d.month)}",
                    f"lar:{d.year:04d}-{d.month:02d}"):
            ETAT["base"].oublier_sources(cle)
    demander_preparation(pid)
    return {"ok": True}


@app.post("/api/livrets/{pid}/mot/ajouter")
def ajouter_au_mot(pid: int, corps: dict = Body(...)):
    """Ajoute une phrase (anniversaire) à la fin du mot des hôtes."""
    p = _personne_ou_404(pid)
    phrase = " ".join(str(corps.get("phrase", "")).split())[:400]
    if not phrase:
        raise HTTPException(422, "Phrase vide.")
    base: Base = ETAT["base"]
    lv = base.livret(pid)
    mot = lv["mot"] or rendu.mot_par_defaut(p, date.fromisoformat(p["naissance"]), _journal())
    base.maj_livret(pid, mot=mot.rstrip() + "\n\n" + phrase,
                    **({"etat": "a_relire", "approuve_le": ""} if lv["etat"] == "approuve" else {}))
    if corps.get("cle"):
        base.ignorer("anniversaire", str(corps["cle"])[:60])
    return {"ok": True}


def _rendre(pid: int, mode: str) -> tuple[str, dict, dict]:
    p = _personne_ou_404(pid)
    lv = ETAT["base"].livret(pid)
    return rendu.document(p, lv, _journal(), mode=mode), p, lv


@app.get("/api/livrets/{pid}/apercu")
def apercu(pid: int, mode: str = "ecran"):
    doc, _, _ = _rendre(pid, mode if mode in ("ecran", "impose", "lecture") else "ecran")
    return HTMLResponse(doc, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src data:"})


@app.get("/api/livrets/{pid}/pdf")
def telecharger(pid: int, mode: str = "impose"):
    mode = mode if mode in ("impose", "lecture") else "impose"
    doc, p, _ = _rendre(pid, mode)
    try:
        contenu, deborde = rendu.pdf(doc, mode)
    except rendu.RenduImpossible as ex:
        raise HTTPException(503, str(ex))
    nom = "gazette-" + "".join(ch if ch.isalnum() else "-" for ch in p["nom"].lower()).strip("-") + f"-{mode}.pdf"
    return Response(contenu, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "X-Debordements": ",".join(map(str, deborde))})


@app.post("/api/livrets/{pid}/approuver")
def approuver(pid: int):
    """Contrôle qu'aucune page ne déborde, puis approuve. Rien ne s'imprime sans cette étape."""
    doc, p, lv = _rendre(pid, "impose")
    if not (lv.get("contenu") or {}).get("une"):
        raise HTTPException(409, "Livret pas encore préparé.")
    try:
        _, deborde = rendu.pdf(doc, "impose")
    except rendu.RenduImpossible:
        deborde = []                      # sans Chromium (tests), pas de contrôle
    if deborde:
        raise HTTPException(409, "Texte trop long : la page " + ", ".join(map(str, deborde))
                            + " déborde. Raccourcis ou masque un bloc avant d'approuver.")
    ETAT["base"].maj_livret(pid, etat="approuve", approuve_le=maintenant())
    ETAT["base"].noter("approuver", pid)
    return {"ok": True}


@app.post("/api/livrets/{pid}/culture")
def remplir_culture(pid: int):
    """Remplace musique et cinéma par le top 5 culturel de l'année de naissance."""
    p = _personne_ou_404(pid)
    base: Base = ETAT["base"]
    lv = base.livret(pid)
    top = ETAT["culture"].annee(int(p["naissance"][:4]))
    if not any(top.values()):
        raise HTTPException(404, f"Le top 5 culturel n'a rien pour {p['naissance'][:4]}.")
    c = lv["contenu"]
    c.update(culture.textes(top))
    c["musique_main"] = c["cinema_main"] = False
    c["sources"] = sorted(set(c.get("sources", [])) | {"top5"})
    props = lv["propositions"]
    props["culture"] = top
    base.maj_livret(pid, contenu=c, propositions=props,
                    **({"etat": "a_relire", "approuve_le": ""} if lv["etat"] == "approuve" else {}))
    return {"ok": True, "musique": c["musique"], "cinema": c["cinema"]}


# ================================================================ Top 5 culturel

@app.get("/api/culture")
def etat_culture():
    return {**ETAT["culture"].etat(), "prompt": culture.PROMPT.read_text(encoding="utf-8")}


@app.get("/api/culture/fichier")
def fichier_culture():
    return FileResponse(ETAT["culture"].fichier(), media_type="text/csv; charset=utf-8",
                        filename="top5_culture_annuel.csv")


@app.post("/api/culture/import")
def importer_culture(corps: dict = Body(...)):
    """Remplace le top 5 culturel par le fichier envoyé (contrôlé avant d'être gardé)."""
    texte = str(corps.get("texte") or "")
    if len(texte) > 5_000_000:
        raise HTTPException(413, "Fichier trop gros.")
    try:
        e = ETAT["culture"].importer(texte)
    except culture.FichierCultureInvalide as ex:
        raise HTTPException(422, str(ex))
    ETAT["base"].noter("culture", None, f"{e['lignes']} lignes, {e['annees'][0]}-{e['annees'][1]}")
    return e


@app.post("/api/culture/revenir")
def revenir_culture():
    e = ETAT["culture"].revenir()
    ETAT["base"].noter("culture", None, "version livrée avec l'appli")
    return e


# ================================================================ À traiter

def a_traiter() -> dict:
    base: Base = ETAT["base"]
    ign_fiches = base.ignores("fiche")
    fiches, vus = [], set()
    for s in base.sejours():
        for i in s["invites"]:
            if i["personne_id"] is None and i["nom"] not in vus and i["nom"] not in ign_fiches:
                vus.add(i["nom"])
                fiches.append({"nom": i["nom"], "chambre": s["chambre"], "du": s["du"], "jusqu_au": s["jusqu_au"]})
    relire, erreurs, annivs = [], [], []
    attendus = {i["personne_id"] for s in base.sejours() for i in s["invites"] if i["personne_id"]}
    for p in base.personnes():
        lv = base.livret(p["id"]) or {}
        if lv.get("etat") == "a_relire":
            relire.append({"id": p["id"], "nom": p["nom"], "attendu": p["id"] in attendus})
        if lv.get("erreur"):
            erreurs.append({"id": p["id"], "nom": p["nom"], "erreur": lv["erreur"]})
        for a in _anniversaires_de(p):
            if not a["ignore"]:
                annivs.append({"id": p["id"], "nom": p["nom"], **a})
    relire.sort(key=lambda x: not x["attendu"])
    return {"fiches": fiches, "relire": relire, "anniversaires": annivs, "erreurs": erreurs,
            "total": len(fiches) + len(relire) + len(annivs) + len(erreurs)}


@app.get("/api/a-traiter")
def route_a_traiter():
    return a_traiter()


@app.post("/api/a-traiter/ignorer")
def ignorer(corps: dict = Body(...)):
    sorte = corps.get("sorte")
    if sorte not in ("fiche", "anniversaire"):
        raise HTTPException(422, "Sorte inconnue.")
    ETAT["base"].ignorer(sorte, str(corps.get("cle", ""))[:80])
    return {"ok": True}


# ================================================================ Connexion et Réglages

@app.get("/api/connexion/etat")
def etat_connexions():
    base: Base = ETAT["base"]
    cfg: Config = ETAT["cfg"]
    return {"sources": base.stats_sources(), "erreurs": ETAT["sources"].erreurs,
            "ha": {"porte": bool(cfg.jeton_ha), "dernier_appel": base.reglage("ha_dernier_appel"),
                   "dernier_corps": base.reglage("ha_dernier_resume")},
            "rendu": {"polices": rendu.polices_presentes()},
            "imprimante": {"reglee": bool(cfg.imprimante)}, "larousse": _journal()["larousse"]}


@app.post("/api/connexion/verifier")
def verifier_sources():
    return ETAT["sources"].sonder()


@app.get("/api/reglages")
def reglages():
    cfg: Config = ETAT["cfg"]
    return {"journal": _journal(), "champs": {k: {"libelle": v[0], "aide": v[1], "maxi": v[2]} for k, v in journal.CHAMPS.items()},
            "lecture_seule": cfg.lecture_seule, "version": __version__, "historique": ETAT["base"].journal(40)}


@app.put("/api/reglages/journal")
def enregistrer_journal(corps: dict = Body(...)):
    """Les éléments communs à tous les livrets. Ils valent aussitôt pour les aperçus et les PDF ; un mot des
    hôtes déjà écrit dans un livret est gardé."""
    try:
        j = journal.valider(corps, _journal())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    ETAT["base"].poser_reglage("journal", json.dumps(j, ensure_ascii=False))
    ETAT["sources"].larousse_actif = j["larousse"]
    ETAT["base"].noter("reglages", None, "le journal")
    return j


# ================================================================ Home Assistant

@app.post("/ha/sejour")
def ha_sejour(corps: dict = Body(...)):
    """Home Assistant annonce un séjour : {chambre, noms, du, jusqu_au}. Sans nom : la chambre est libre.
    Gazette retrouve le livret de chaque invité (elle n'en crée pas), lance la préparation d'un livret pas encore
    fait, et rend ce qui manque. Rien n'est écrit dans Home Assistant."""
    base: Base = ETAT["base"]
    chambre = str(corps.get("chambre", "")).strip()[:40]
    if not chambre:
        raise HTTPException(422, "Chambre manquante.")
    base.poser_reglage("ha_dernier_appel", maintenant())
    noms = [" ".join(str(n).split()) for n in (corps.get("noms") or []) if str(n).strip()][:4]
    if not noms:
        base.retirer_sejours(chambre)
        base.poser_reglage("ha_dernier_resume", f"{chambre} : libre")
        return {"chambre": chambre, "invites": [], "manquants": [], "a_relire": [], "anniversaires": []}
    du, fin = _date(corps.get("du"), "date d'arrivée"), _date(corps.get("jusqu_au"), "date de départ")
    if fin < du or not date.today() - timedelta(days=60) <= fin <= date.today() + timedelta(days=400):
        raise HTTPException(422, "Dates de séjour impossibles.")
    sid = base.poser_sejour(chambre, du.isoformat(), fin.isoformat(), noms)
    sejour = next(s for s in base.sejours(depuis="0000") if s["id"] == sid)
    invites, manquants, relire, annivs = [], [], [], []
    for i in sejour["invites"]:
        if i["personne_id"] is None:
            manquants.append(i["nom"])
            invites.append({"nom": i["nom"], "fiche": False, "livret": None, "lien": ""})
            continue
        p = base.personne(i["personne_id"])
        lv = base.livret(p["id"])
        if lv["etat"] == "a_preparer" and not lv["erreur"]:
            demander_preparation(p["id"])
            lv = base.livret(p["id"])
        cas = anniversaire.proche(date.fromisoformat(p["naissance"]), du, fin)
        if lv["etat"] in ("a_relire", "en_preparation", "a_preparer"):
            relire.append(i["nom"])
        if cas:
            annivs.append({"nom": i["nom"], **cas})
        invites.append({"nom": i["nom"], "fiche": True, "livret": lv["etat"], "lien": _lien(p["id"]),
                        "anniversaire": cas})
    base.poser_reglage("ha_dernier_resume", f"{chambre} : {', '.join(noms)} ({du.isoformat()} → {fin.isoformat()})")
    return {"chambre": chambre, "invites": invites, "manquants": manquants, "a_relire": relire, "anniversaires": annivs}


@app.get("/ha/etat")
def ha_etat():
    """Pour le capteur de Home Assistant : ce qui attend un geste des hôtes, en phrases courtes."""
    t = a_traiter()
    lignes = [f"{f['nom']} ({f['chambre']}, {f['du']}) : pas de fiche dans Gazette" for f in t["fiches"]]
    lignes += [f"{r['nom']} : livret à relire" for r in t["relire"] if r["attendu"]]
    lignes += [f"{a['nom']} : anniversaire {a['libelle']} ({a['anniversaire']})" for a in t["anniversaires"]]
    return {"a_traiter": len(lignes), "fiches_manquantes": len(t["fiches"]),
            "a_relire": sum(1 for r in t["relire"] if r["attendu"]), "anniversaires": len(t["anniversaires"]),
            "liste": lignes, "adresse": ETAT["cfg"].adresse}


# ================================================================ interface

@app.get("/{chemin:path}")
def interface(chemin: str):
    statique = ETAT["cfg"].static
    fichier = (statique / chemin).resolve() if chemin else None
    if fichier and fichier.is_file() and statique.resolve() in fichier.parents:
        return FileResponse(fichier)
    index = statique / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Interface non compilée."}, status_code=404)
