"""Gazette : « le monde le jour de votre naissance », un livret A5 par proche pour son premier séjour ; 0.9 : à
partir du deuxième séjour, La Récidive, un journal à scandale fait des photos d'Immich prises depuis le séjour
précédent (une édition par séjour).

Routes : /health (publique) ; /api/… (session) ; /ha/… (jeton de Home Assistant) ; /externe/sauvegarde (jeton
commun de la maison, pour l'Anneau) ; puis l'interface.
Gazette n'écrit chez personne : ni dans carnet, ni dans Immich, ni dans Home Assistant. L'impression (temps 3)
sera sa seule écriture extérieure, refusée en lecture seule."""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import queue
import re
import threading
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from . import __version__, anniversaire, code_barres, culture, journal, maison, recidive as R, rendu, rendu_recidive
from .carnet import Carnet
from .immich import Immich
from . import ollama as ia
from .ollama import ACTIONS_GAZETTE, MAXI as MAXI_TITRE, Ollama, sans_numero, texte_contexte
from .auth import COMMUN, DUREE, Sessions, en_https
from .base import ETATS, Base, cle_nom, maintenant
from .config import APPLI, Config, charger, racine
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
    if not (base.livret(pid) or {}).get("photos_choix"):      # 0.13 : 6 photos d'Immich au choix pour la page 4
        _chercher_photos_gazette(pid, p)


PHOTOS_GAZETTE = 6


def _chercher_photos_gazette(pid: int, p: dict) -> str:
    """0.13 : 6 photos d'Immich où l'invité est reconnu, réparties dans le temps, pour la page 4 de la Gazette
    classique. Rend un message pour l'écran ; jamais une erreur (sans Immich ni personne liée : page 4 inchangée)."""
    immich: Immich = ETAT["immich"]
    if not immich.actif:
        return "Immich n'est pas réglé (GAZETTE_IMMICH_CLE vide) : pas de photo."
    immich_id = (_contact(p) or {}).get("immich_id") or ""
    if not immich_id:
        return "Pas de personne d'Immich liée à cette fiche dans carnet : pas de photo."
    try:
        toutes = immich.toutes(immich_id)
    except Exception as ex:  # noqa: BLE001
        return f"Immich : {str(ex).splitlines()[0][:160] or type(ex).__name__}"
    choix = R.etaler(toutes, PHOTOS_GAZETTE)
    choix = [{"id": x["id"], "date": x["date"]} for x in choix if immich.apercu(x["id"])]
    ETAT["base"].maj_livret(pid, photos_choix=choix)
    return f"{len(choix)} photo(s) proposée(s)." if choix else "Aucune photo de cette personne dans Immich."


# 0.21 (socle 0.9.0) : tâches à la demande suivies dans /health (maison.TACHES) — une préparation par tour
TACHE_GAZETTE = "preparation"     # livret de la Gazette (sources, top 5, photos)
TACHE_RECIDIVE = "recidive"       # édition de La Récidive (photos d'Immich)


class _PreparationRatee(Exception):
    """Préparation finie avec une erreur notée sur le livret ou l'édition : sert seulement à marquer le tour."""


def _preparer_suivi(tache) -> None:
    """Un tour de l'ouvrier sous maison.TACHES. Une erreur que la préparation a déjà notée (livret ou édition
    « à préparer » avec un message) compte comme un tour raté ; les autres exceptions repartent comme avant."""
    base: Base = ETAT["base"]
    try:
        if isinstance(tache, tuple):          # 0.9 : ("r", id, completer) — une édition de La Récidive
            with maison.TACHES.tour(TACHE_RECIDIVE):
                _preparer_recidive(tache[1], tache[2])
                ed = base.recidive(tache[1]) or {}
                if ed.get("erreur"):
                    raise _PreparationRatee(ed["erreur"])
        else:
            with maison.TACHES.tour(TACHE_GAZETTE):
                _preparer(tache)
                lv = base.livret(tache) or {}
                if lv.get("erreur"):
                    raise _PreparationRatee(lv["erreur"])
    except _PreparationRatee:
        pass


def _ouvrier() -> None:
    file: queue.Queue = ETAT["file"]
    while True:
        tache = file.get()
        if tache is None:
            return
        try:
            _preparer_suivi(tache)
        except Exception as ex:  # noqa: BLE001 — 0.20.4 : une tâche ratée ne tue plus l'ouvrier
            try:
                if isinstance(tache, tuple):
                    ETAT["base"].noter("erreur", None, f"Récidive {tache[1]} : {type(ex).__name__} : {ex}"[:200])
                else:
                    ETAT["base"].maj_livret(tache, etat="a_preparer", erreur=f"{type(ex).__name__} : {ex}"[:300])
                    ETAT["base"].noter("erreur", tache, f"préparation : {type(ex).__name__} : {ex}"[:200])
            except Exception:  # noqa: BLE001 — même la note ne doit pas arrêter la file
                pass
        finally:
            ETAT["en_file"].discard(tache if not isinstance(tache, tuple) else ("r", tache[1]))
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


# ================================================================ La Récidive (0.9)

def _contact(p: dict) -> dict:
    """Ce que carnet sait de cette fiche (genre, personne d'Immich) : le contact unique qui porte son nom ou un alias."""
    if not ETAT["carnet"].actif:
        return {}
    if p.get("essai_de"):                      # 0.20 : une fiche d'essai lit le contact de la vraie fiche
        p = ETAT["base"].personne(p["essai_de"]) or p
    trouves = {}
    for n in [p["nom"], *p["alias"]]:
        for c in ETAT["carnet"].chercher(n):
            trouves[c.get("carnet_id") or id(c)] = c
    return next(iter(trouves.values())) if len(trouves) == 1 else {}


def _numero_et_precedent(p: dict, du: str) -> tuple[int, dict | None]:
    sejours = ETAT["base"].sejours_de(p["id"])
    n = R.numero([s["du"] for s in sejours], du, p.get("sejours_avant") or 0)
    return n, R.precedent(sejours, du, p.get("dernier_avant") or "")


def _edition_du_sejour(pid: int, du: str) -> dict | None:
    """L'édition de La Récidive de ce séjour (créée et mise en préparation au besoin), ou None : premier séjour (ou
    Immich pas réglé), c'est la Gazette. Une édition pas encore approuvée d'un séjour redevenu le premier est retirée."""
    base: Base = ETAT["base"]
    p = base.personne(pid)
    if not p:
        return None
    n, prec = _numero_et_precedent(p, du)
    ed = base.recidive_de(pid, du)
    if n < 2:
        if ed and ed["etat"] != "approuve":
            base.supprimer_recidive(ed["id"])
        return None
    if not ETAT["immich"].actif and not (ed and ed["etat"] == "approuve"):
        return None                     # Immich pas réglé : pas de photos, le séjour garde la Gazette
    if not ed:
        rid = base.creer_recidive(pid, du, n)
        base.maj_recidive(rid, precedent=prec)
        base.noter("recidive", pid, f"N° {n}, séjour du {du}")
        demander_recidive(rid)
        return base.recidive(rid)
    if ed["numero"] != n or (ed["precedent"] or None) != prec:
        base.maj_recidive(ed["id"], numero=n, precedent=prec)
        ed = base.recidive(ed["id"])
    if ed["etat"] == "a_preparer" and not ed["erreur"]:
        demander_recidive(ed["id"])
        ed = base.recidive(ed["id"])
    return ed


def demander_recidive(rid: int, completer: bool = False) -> None:
    if ETAT["cfg"].synchrone:
        _preparer_recidive(rid, completer)
        return
    if ("r", rid) in ETAT["en_file"]:
        return
    ETAT["en_file"].add(("r", rid))
    ETAT["base"].maj_recidive(rid, etat="en_preparation", erreur="")
    ETAT["file"].put(("r", rid, completer))


def _preparer_recidive(rid: int, completer: bool = False) -> None:
    """Cherche les photos (Immich) et compose l'édition. `completer` : garde les photos et légendes de la relecture,
    remplace seulement les photos retirées."""
    base: Base = ETAT["base"]
    ed = base.recidive(rid)
    p = base.personne(ed["personne_id"]) if ed else None
    if not ed or not p:
        return
    base.maj_recidive(rid, etat="en_preparation", erreur="")
    contact = _contact(p)
    genre = contact.get("genre") if contact else ed["genre"]
    immich_id = (contact.get("immich_id") if contact else "") or ed["immich_id"]
    _, prec = _numero_et_precedent(p, ed["sejour_du"])

    def echec(message: str) -> None:
        base.maj_recidive(rid, etat="a_preparer", erreur=message[:300], genre=genre or "", immich_id=immich_id or "")
        base.noter("erreur", p["id"], f"La Récidive : {message}"[:200])

    immich: Immich = ETAT["immich"]
    if not immich.actif:
        return echec("Immich n'est pas réglé (GAZETTE_IMMICH_CLE vide) : pas de photos.")
    if not immich_id:
        return echec("Pas de personne d'Immich liée à cette fiche dans carnet (ou carnet ne la trouve pas).")
    if not prec and ed.get("essai"):           # 0.20 : essai sans séjour précédent connu : la dernière année
        prec = {"du": (date.fromisoformat(ed["sejour_du"]) - timedelta(days=365)).isoformat(), "jusqu_au": ""}
    if not prec:
        return echec("Date du séjour précédent inconnue : la noter sur la fiche (séjours d'avant Gazette).")
    try:
        recentes = immich.photos(immich_id, prec["du"], ed["sejour_du"])
        garder = [x for x in ed["photos"] if not x.get("retiree")] if completer else []
        exclus = {x["id"] for x in ed["photos"] if x.get("retiree")} if completer else set()
        dispo = [x for x in recentes if x["id"] not in exclus and x["id"] not in {g["id"] for g in garder}]
        scandales = immich.scandales(immich_id) if len(garder) + len(dispo) < R.PLACES else []
        choix = R.choisir(recentes, scandales, base.publies(p["id"]), garder=garder, exclus=exclus)
    except Exception as ex:  # noqa: BLE001 — Immich arrêté, clé refusée : message dans À traiter
        return echec(f"Immich : {str(ex).splitlines()[0][:200] or type(ex).__name__}")
    if completer:                        # les photos retirées restent notées (elles ne reviennent pas)
        choix["photos"] += [x for x in ed["photos"] if x.get("retiree")]
    for x in choix["photos"]:
        if not x.get("retiree"):
            immich.apercu(x["id"])
            if "contexte" not in x:      # 0.12 : albums et personnes, pour l'IA (vide si Immich ne le dit pas)
                x["contexte"] = immich.contexte(x["id"], immich_id)
    vide = not any(not x.get("retiree") for x in choix["photos"])
    accroche = ed["accroche"] if (completer and ed["accroche"]) else R.accroche(genre or "", _prenom(p), _journal())
    base.maj_recidive(rid, etat="vide" if vide else "a_relire", photos=choix["photos"], trouvees=choix["trouvees"],
                      manque_scandale=choix["manque_scandale"], tag_absent=choix["tag_absent"], genre=genre or "",
                      immich_id=immich_id,
                      accroche=accroche, precedent=prec, prepare_le=maintenant(), approuve_le="", erreur="")
    base.noter("recidive", p["id"], "aucune photo dans la fenêtre : la Gazette sert" if vide
               else f"{sum(1 for x in choix['photos'] if not x.get('retiree'))} photo(s)")
    if vide:                             # repli : le séjour garde la Gazette, qui doit être prête
        lv = base.livret(p["id"])
        if lv and lv["etat"] == "a_preparer" and not lv["erreur"]:
            demander_preparation(p["id"])


@asynccontextmanager
async def cycle(app: FastAPI):
    cfg = ETAT.get("cfg") or charger()
    cfg.data.mkdir(parents=True, exist_ok=True)
    chemin_base = cfg.data / "gazette.db"
    base = Base(chemin_base)
    ETAT.update(cfg=cfg, sessions=Sessions(APPLI, cfg.password, _lire_generation(cfg)), base=base,
                file=queue.Queue(), en_file=set(), culture=culture.Culture(cfg.data))
    # 0.8 : réglages d'usage — reprise unique des anciennes variables pour une clé encore absente de la base
    for cle in journal.reprendre(base):
        base.noter("reglages", None, f"{journal.LIBELLES[cle]} repris de {journal.VARIABLES[cle]} (premier démarrage)")
    larousse = journal.charger(base)["larousse"]
    ETAT.setdefault("sources", Sources(base, actives=cfg.sources_actives, larousse=larousse))
    ETAT["sources"].larousse_actif = larousse
    ETAT["carnet"] = Carnet(cfg.carnet_url, cfg.carnet_jeton, base, lire=ETAT.get("carnet_lire"),
                            ecrire=ETAT.get("carnet_ecrire"), paru=ETAT.get("carnet_paru"))
    ETAT["immich"] = Immich(cfg.immich_url, cfg.immich_cle, cfg.data / "photos", lire=ETAT.get("immich_lire"))
    ETAT["ollama"] = Ollama(cfg.ollama_url, lire=ETAT.get("ollama_lire"))
    maison.TACHES.declarer(TACHE_GAZETTE, type="demande")
    maison.TACHES.declarer(TACHE_RECIDIVE, type="demande")
    ouvrier = threading.Thread(target=_ouvrier, daemon=True, name="preparation")
    ouvrier.start()
    # 0.21 : copie cohérente de gazette.db chaque nuit (heure de Paris, maison.HEURES_COPIE) vers <data>/copies
    copie = asyncio.create_task(maison.planifier_copie(APPLI, [chemin_base], cfg.data / "copies",
                                                       maison.HEURES_COPIE[APPLI]))
    # Livrets restés « en préparation » (redémarrage pendant une lecture) : on reprend
    for p in base.personnes():
        lv = base.livret(p["id"])
        if lv and lv["etat"] == "en_preparation":
            demander_preparation(p["id"])
    for ed in base.recidives():
        if ed["etat"] == "en_preparation":
            demander_recidive(ed["id"])
    yield
    copie.cancel()                        # arrêt propre de la boucle de copie
    with contextlib.suppress(asyncio.CancelledError):
        await copie
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
    # /externe/… : chaque route contrôle le jeton commun elle-même (pas de session)
    elif chemin.startswith("/api/") and chemin not in PUBLIQUES and not ETAT["sessions"].connecte(request.cookies):
        return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    reponse = await appel(request)
    if chemin.startswith(("/api/", "/ha/", "/externe/")):
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
def sante(request: Request):
    """Public. Pour la tuile de l'Anneau : nombres seulement, aucun nom. 0.21 : + version_socle, taches, copie_base
    (socle 0.9.0) ; messages d'erreur des tâches seulement avec le jeton commun MAISON_JETON ou une session."""
    sessions = ETAT.get("sessions")
    taches = maison.sante(request, jeton_commun=maison.jetons(),
                          session_ok=bool(sessions and sessions.connecte(request.cookies)))
    try:   # 0.20.6 : « À traiter » recalculé au plus une fois par minute (appelée chaque minute par Docker et l'Anneau)
        garde = ETAT.get("sante")
        if not garde or time.monotonic() - garde[0] > 60:      # « À traiter » est le calcul coûteux
            garde = (time.monotonic(), a_traiter()["total"])
            ETAT["sante"] = garde
        return {"ok": True, "version": __version__, "livrets": len(ETAT["base"].personnes()), "a_traiter": garde[1],
                **taches}
    except Exception:  # noqa: BLE001 — la santé répond même si la base est occupée
        return {"ok": True, "version": __version__, **taches}


# ================================================================ connexion

@app.get("/api/session")
def session(request: Request):
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__,
            "lecture_seule": ETAT["cfg"].lecture_seule, "lecture_seule_origine": _origine_lecture_seule()}


@app.post("/api/connexion")
async def connexion(request: Request, corps: dict = Body(...)):
    s = ETAT["sessions"]
    if ETAT["cfg"].attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict", secure=en_https(request))
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
            "alias": p["alias"], "sejours_avant": p.get("sejours_avant", 0), "dernier_avant": p.get("dernier_avant", ""),
            "etat": lv.get("etat", "a_preparer"), "erreur": lv.get("erreur", ""),
            "approuve_le": lv.get("approuve_le", ""), "une": (c.get("une") or {}).get("titre", ""),
            "prochain_sejour": ({k: sej[0][k] for k in ("chambre", "du", "jusqu_au")} if sej else None),
            "anniversaire": next((a for a in _anniversaires_de(p) if not a["ignore"]), None)}


def _journal() -> dict:
    return journal.charger(ETAT["base"])


def _modele_demande(corps) -> str | None:
    """0.22 : `{"second": true}` dans le corps d'une demande à l'IA → le second modèle (réglage `modele_second`) ;
    sinon None, le modèle habituel (GAZETTE_OLLAMA_MODELE). Réglage vide : refus 400 (le bouton est caché)."""
    if not isinstance(corps, dict) or corps.get("second") is not True:
        return None
    m = str(_journal().get("modele_second") or "").strip()
    if not m:
        raise HTTPException(400, "Second modèle de l'IA pas réglé (Réglages › Le journal › Second modèle de l'IA) : "
                                 "« Autres propositions » est coupé.")
    return m


def _ia_etat() -> dict:
    """État de l'IA pour les écrans, avec le second modèle réglé (vide : pas de bouton « Autres propositions ») ; il
    s'ajoute aux réglages lus de Connexion › IA du PC."""
    e, second = ETAT["ollama"].etat(), str(_journal().get("modele_second") or "").strip()
    e["guide"]["reglages"].insert(2, {"nom": "Second modèle", "valeur": (f"{second} (« Autres propositions » ; Réglages › Le journal)"
                                                                        if second else "pas réglé (Réglages › Le journal) : pas de bouton « Autres propositions »")})
    return {**e, "modele_second": second}


ANNUAIRE = maison.Annuaire()


def _adresse() -> str:
    """Adresse de Gazette pour le navigateur (liens des notifications de Home Assistant), lue dans l'Anneau
    (tuile « Gazette ») seulement (0.8 : plus de variable de repli) ; inconnue : liens relatifs. Les liens partent
    vers HA, pas vers la page ouverte : jamais l'adresse privée (prive=False). Schéma, hôte et port seulement :
    un chemin donnait un lien faux."""
    return racine(ANNUAIRE.adresse("Gazette", prive=False, repli=""))


def _lien(pid: int) -> str:
    adresse = _adresse()
    return f"{adresse}/#/livret/{pid}" if adresse else f"/#/livret/{pid}"


def _lien_edition(rid: int) -> str:
    adresse = _adresse()
    return f"{adresse}/#/recidive/{rid}" if adresse else f"/#/recidive/{rid}"


def _origine_lecture_seule() -> str:
    """« maison » (MAISON_LECTURE_SEULE), « appli » (GAZETTE_LECTURE_SEULE) ou « » : pour l'écran."""
    cfg: Config = ETAT["cfg"]
    return (cfg.lecture_seule_origine or "appli") if cfg.lecture_seule else ""


# ================================================================ fiches et livrets

def _resume_edition(ed: dict, p: dict | None = None) -> dict:
    p = p or ETAT["base"].personne(ed["personne_id"]) or {"nom": "?"}
    vues = [x for x in ed["photos"] if not x.get("retiree")]
    return {"id": ed["id"], "personne_id": ed["personne_id"], "nom": p["nom"], "sejour_du": ed["sejour_du"],
            "numero": ed["numero_main"] or ed["numero"], "etat": ed["etat"], "erreur": ed["erreur"],
            "photos": len(vues), "anciens": sum(1 for x in vues if x.get("ancien")), "approuve_le": ed["approuve_le"]}


@app.get("/api/livrets")
def livrets():
    """0.9 : chaque invité d'un séjour à venir porte `edition` (La Récidive de ce séjour) ou rien (la Gazette)."""
    base: Base = ETAT["base"]
    sejours = base.sejours()
    for s in sejours:
        for i in s["invites"]:
            ed = _edition_du_sejour(i["personne_id"], s["du"]) if i["personne_id"] else None
            i["edition"] = _resume_edition(ed) if ed and ed["etat"] != "vide" else None
    ranges = {(a["journal"], a["id"]) for a in _archives()}       # 0.20 : rangés dans les Archives
    return {"livrets": [_resume(p) for p in base.personnes() if ("gazette", p["id"]) not in ranges], "sejours": sejours,
            "etats": list(ETATS), "archives": len(ranges),
            "recidives": [_resume_edition(ed) for ed in base.recidives() if ("recidive", ed["id"]) not in ranges]}


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
    if "sejours_avant" in corps:                 # 0.9 : séjours d'avant Gazette (comptent pour le N° de La Récidive)
        try:
            n = int(corps.get("sejours_avant") or 0)
        except (TypeError, ValueError):
            raise HTTPException(422, "Nombre de séjours d'avant Gazette illisible.")
        if not 0 <= n <= 99:
            raise HTTPException(422, "Nombre de séjours d'avant Gazette hors des valeurs possibles (0 à 99).")
        champs["sejours_avant"] = n
    if "dernier_avant" in corps:
        v = str(corps.get("dernier_avant") or "").strip()
        if v:
            d = _date(v, "date du dernier séjour d'avant Gazette")
            if d > date.today():
                raise HTTPException(422, "Le dernier séjour d'avant Gazette ne peut pas être dans le futur.")
            v = d.isoformat()
        champs["dernier_avant"] = v
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
    if "sejours_avant" in c or "dernier_avant" in c:      # le N° et la fenêtre des séjours à venir changent
        for s in _sejours_de(pid):
            ed = _edition_du_sejour(pid, s["du"])
            if ed and ed["etat"] in ("a_preparer", "a_relire", "vide") and "dernier_avant" in c:
                demander_recidive(ed["id"])
    return {"ok": True}


@app.delete("/api/personnes/{pid}")
def supprimer_personne(pid: int, corps: dict | None = Body(None)):
    _personne_ou_404(pid)
    # 0.20.9 : confirmation exigée côté serveur ({"confirmation": true} dans le corps)
    if not isinstance(corps, dict) or corps.get("confirmation") is not True:
        raise HTTPException(400, "Suppression non confirmée : envoyer {\"confirmation\": true}.")
    # 0.20.6 : copie de la base avant (livret, Récidives et scandales publiés partent avec la fiche)
    ETAT["base"].copie(ETAT["cfg"].data / "sauvegardes", f"gazette-{maintenant()[:19].replace(':', '-')}-avant-suppression-{pid}.db")
    ETAT["base"].supprimer_personne(pid)
    ETAT["base"].noter("fiche", None, f"fiche {pid} supprimée")
    return {"ok": True}


@app.get("/api/livrets/{pid}")
def livret(pid: int):
    p = _personne_ou_404(pid)
    lv = ETAT["base"].livret(pid)
    naissance = date.fromisoformat(p["naissance"])
    j = _journal()
    return {"personne": p, "livret": {**lv, "mot_defaut": rendu.mot_par_defaut(p, naissance, j),
                                      "code_barres_defaut": rendu.message_code_barres(_prenom(p)), "cadrages": R.CADRAGES,
                                      "immich": ETAT["immich"].actif},
            "ia": {"modele": ia.MODELE, "modele_second": _ia_etat()["modele_second"]},
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
    if "photo" in corps:                       # 0.13 : photo de la page 4 (une des photos proposées, ou aucune)
        ph = corps["photo"] if isinstance(corps["photo"], dict) else {}
        permis = {x["id"] for x in lv["photos_choix"]}
        if ph.get("id") in permis:
            ancienne = lv["photo"] if lv["photo"].get("id") == ph["id"] else {}
            date_ = next(x["date"] for x in lv["photos_choix"] if x["id"] == ph["id"])
            champs["photo"] = {**ancienne, "id": ph["id"], "date": date_,
                               "cadrage": ph.get("cadrage") if ph.get("cadrage") in R.CADRAGES else "haut",
                               "legende": " ".join(str(ph.get("legende") or "").split())[:160],
                               "description": " ".join(str(ph.get("description") or "").split())[:400]}
        else:
            champs["photo"] = {}
    if "valides" in corps:                     # 0.17 : éléments validés (ne change pas l'état du livret)
        valides = _valides(corps["valides"])
        if len(corps) == 1:
            base.maj_livret(pid, valides=valides)
            return {"ok": True, "etat": base.livret(pid)["etat"]}
        champs["valides"] = valides
    if "code_barres" in corps:                 # 0.13 : vide = « Bienvenue, {prénom} ! »
        champs["code_barres"] = " ".join(str(corps.get("code_barres") or "").split())[:code_barres.MAXI]
    if champs:
        # 0.17 : un livret approuvé repasse « à relire » seulement si un contenu change (pas pour une validation)
        if lv["etat"] == "approuve" and any(k != "valides" and champs[k] != lv.get(k) for k in champs):
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


@app.post("/api/livrets/{pid}/photos")
def chercher_photos_livret(pid: int):
    """0.13 : (re)cherche les 6 photos d'Immich proposées pour la page 4. La photo choisie reste choisie si elle en fait
    encore partie."""
    p = _personne_ou_404(pid)
    message = _chercher_photos_gazette(pid, p)
    lv = ETAT["base"].livret(pid)
    if lv["photo"].get("id") and lv["photo"]["id"] not in {x["id"] for x in lv["photos_choix"]}:
        ETAT["base"].maj_livret(pid, photos_choix=lv["photos_choix"] + [{"id": lv["photo"]["id"], "date": lv["photo"].get("date", "")}])
    return {"message": message, "photos_choix": ETAT["base"].livret(pid)["photos_choix"]}


@app.get("/api/livrets/{pid}/photos/{asset}")
def photo_livret(pid: int, asset: str):
    _personne_ou_404(pid)
    if asset not in {x["id"] for x in ETAT["base"].livret(pid)["photos_choix"]}:
        raise HTTPException(404, "Photo introuvable pour ce livret.")
    octets = ETAT["immich"].gardee(asset) or ETAT["immich"].apercu(asset)
    if not octets:
        raise HTTPException(404, "Aperçu indisponible (Immich injoignable ?).")
    return Response(octets, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@app.post("/api/livrets/{pid}/photo/proposer")
def proposer_legende_livret(pid: int, corps: dict = Body(default={})):
    """0.13 : {description} → 5 légendes façon presse de l'année de naissance pour la photo choisie, d'après la
    description de Julien, l'album parlant et les personnes d'Immich. Rien n'est choisi à sa place."""
    p = _personne_ou_404(pid)
    modele = _modele_demande(corps)
    lv = ETAT["base"].livret(pid)
    ph = dict(lv["photo"])
    if not ph.get("id"):
        raise HTTPException(409, "Choisis d'abord une photo.")
    if "contexte" not in ph and ETAT["immich"].actif:
        ph["contexte"] = ETAT["immich"].contexte(ph["id"], (_contact(p) or {}).get("immich_id") or "")
    description = " ".join(str(corps.get("description") or "").split())[:400]
    ctx = texte_contexte(ph.get("contexte"))
    if len(description) < 3 and not ctx:
        raise HTTPException(422, "Décris d'abord la photo en quelques mots (aucun album parlant ni personne connue dans Immich).")
    texte = "\n".join(t for t in (f"Ce que montre la photo, d'après l'hôte : « {description} »" if len(description) >= 3 else "",
                                    f"D'après la photothèque : {ctx}" if ctx else "",
                                    f"Prise le {ph['date']}" if ph.get("date") else "") if t)
    contact = _contact(p) or {}
    try:
        props = ETAT["ollama"].gazette("legende", texte, int(p["naissance"][:4]), None, _prenom(p), contact.get("genre", ""),
                                       modele=modele)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    ETAT["base"].maj_livret(pid, photo={**ph, "description": description, "propositions": props})
    ETAT["base"].noter("ia", pid, f"légende de la photo : {len(props)} proposition(s)")
    return {"propositions": props, "contexte": ph.get("contexte") or {}, "modele": modele or ia.MODELE}


def _valides(v) -> dict:
    """0.17 : {clé d'élément : empreinte de son contenu au moment de la validation}, bornés."""
    if not isinstance(v, dict):
        return {}
    return {str(k)[:60]: str(x)[:24] for k, x in list(v.items())[:300] if isinstance(x, (str, int))}


def _evenements_du_livret(lv: dict | None) -> list[str]:
    """0.17 : les titres des événements racontés dans la Gazette (une, brèves, page 2), pour le mot des hôtes."""
    c = (lv or {}).get("contenu") or {}
    res = [(c.get("une") or {}).get("titre", "")]
    res += [b.get("titre", "") for b in c.get("breves") or [] if not b.get("masque")]
    res += [b.get("titre", "") for b in (c.get("p2") or {}).get("items") or [] if not b.get("masque")]
    return [t.strip() for t in dict.fromkeys(res) if t and t.strip()][:8]


@app.post("/api/livrets/{pid}/ia")
def ia_livret(pid: int, corps: dict = Body(...)):
    """0.12 : aides de l'IA du PC pour la Gazette classique, sur le texte affiché (même pas enregistré) :
    {action: titres | raccourcir | journal | traduire | mot, texte, signes?}. Rend des propositions ; rien n'est
    changé dans le livret (Julien choisit, puis enregistre)."""
    p = _personne_ou_404(pid)
    modele = _modele_demande(corps)
    action = str(corps.get("action") or "")
    if action not in ACTIONS_GAZETTE:
        raise HTTPException(422, "Aide inconnue.")
    try:
        signes = int(corps["signes"]) if corps.get("signes") else None
    except (TypeError, ValueError):
        signes = None
    contact = _contact(p) if action == "mot" else {}
    evenements = _evenements_du_livret(ETAT["base"].livret(pid)) if action == "mot" else None
    try:
        props = ETAT["ollama"].gazette(action, str(corps.get("texte") or ""), int(p["naissance"][:4]), signes,
                                       _prenom(p), contact.get("genre", ""), contact.get("journaux", ""), _journal()["chez"],
                                       evenements, modele=modele)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    ETAT["base"].noter("ia", pid, f"{action} : {len(props)} proposition(s)")
    return {"propositions": props, "modele": modele or ia.MODELE}


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
    return rendu.document(p, lv, _journal(), mode=mode, image=ETAT["immich"].gardee), p, lv


@app.get("/api/livrets/{pid}/apercu")
def apercu(pid: int, mode: str = "ecran"):
    doc, _, _ = _rendre(pid, mode if mode in ("ecran", "impose", "lecture") else "ecran")
    return HTMLResponse(doc, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:; img-src data:"})


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


@app.get("/api/livrets/{pid}/mesure")
def mesure(pid: int):
    """Place prise par chaque bloc et place qui manque, page par page (blocs en rouge, compteurs et
    remplacements en vert dans l'éditeur). 503 sans Chromium : l'éditeur s'en passe."""
    doc, _, _ = _rendre(pid, "lecture")
    try:
        return {"pages": rendu.mesurer(doc)}
    except rendu.RenduImpossible as ex:
        raise HTTPException(503, str(ex))


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
                            + " déborde. Raccourcis un bloc en rouge, masque-le ou remplace-le par une proposition en vert.")
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


# ================================================================ La Récidive : relecture, aperçu, PDF, approbation (0.9)

def _edition_ou_404(rid: int) -> tuple[dict, dict]:
    ed = ETAT["base"].recidive(rid)
    p = ETAT["base"].personne(ed["personne_id"]) if ed else None
    if not ed or not p:
        raise HTTPException(404, "Édition introuvable.")
    return ed, p


def _evenements_avant(pid: int, ed: dict) -> list[str]:
    """0.15 : les événements notés pour les séjours précédents de la personne (« 2025 : soirée Eurovision »), les plus
    récents d'abord, pour un clin d'œil de l'horoscope."""
    res = []
    for x in ETAT["base"].recidives(pid):
        if x["id"] != ed["id"] and x["sejour_du"] < ed["sejour_du"] and (x.get("evenement") or "").strip():
            res.append(f"{x['sejour_du'][:4]} : {x['evenement'].strip()}")
    p = ETAT["base"].personne(pid)               # 0.16 : et ceux rangés sur la fiche de carnet
    for x in _parus_carnet(p, ed) if p else []:
        if (x.get("evenement") or "").strip() and (x.get("le") or "") < ed["sejour_du"]:
            res.append(f"{x['le'][:4]} : {x['evenement'].strip()}")
    return list(dict.fromkeys(res))[:5]


def _deja_paru(pid: int, sauf: int) -> list[str]:
    """0.10 : les textes imprimés dans les éditions approuvées précédentes de cette personne (gros titre, légendes
    écrites ou choisies, rumeurs) : l'IA ne les reprend pas, mais peut y faire un clin d'œil."""
    res = []
    for ed in ETAT["base"].recidives(pid):
        if ed["id"] == sauf or ed["etat"] != "approuve":
            continue
        res += [ed.get("titre_une") or ""] + list(ed.get("rumeurs") or []) + [ed.get("horoscope") or ""]
        res += [x.get("lettre", "") for x in ed.get("courrier") or []]
        res += [x.get("legende", "") for x in ed["photos"] if not x.get("retiree") and x.get("legende") != R.legende(x)]
    # 0.16 : et ce qui est rangé sur la fiche de carnet (« Journaux parus »), même si la base de Gazette l'a perdu
    p = ETAT["base"].personne(pid)
    cette = ETAT["base"].recidive(sauf) if sauf else None
    if p:
        for x in _parus_carnet(p, cette or {}):
            res += [t.split(" — ")[0] if " / La rédaction" in t else t for t in x.get("textes") or []]
    return [x for x in dict.fromkeys(t.strip() for t in res) if x][:40]


def _mot_recidive(ed: dict, p: dict) -> str:
    return ed["mot"] or R.mot_par_defaut(ed["genre"], _prenom(p), _journal())


@app.get("/api/recidives")
def liste_recidives():
    return {"recidives": [_resume_edition(ed) for ed in ETAT["base"].recidives()]}


@app.get("/api/recidives/{rid}")
def edition(rid: int):
    ed, p = _edition_ou_404(rid)
    j = _journal()
    return {"personne": p, "edition": {**ed, "mot_defaut": R.mot_par_defaut(ed["genre"], _prenom(p), _journal()),
                                       "accroche_defaut": R.accroche(ed["genre"], _prenom(p), _journal())},
            "signature": j["signature"], "places": R.PLACES, "titre_defaut": R.titre_une(p["nom"]),
            "code_barres_defaut": R.code_barres(_prenom(p)), "code_barres_maxi": code_barres.MAXI,
            "indices_carnet": _contact(p).get("journaux") or "", "deja_paru": _deja_paru(p["id"], rid), "macarons": R.MACARONS, "rumeurs_maxi": R.RUMEURS, "lettres_maxi": R.LETTRES,
            "signe": R.signe(p.get("naissance", ""))[0], "cadrages": R.CADRAGES,
            "ia": {**_ia_etat(), "maxi": MAXI_TITRE}}


@app.put("/api/recidives/{rid}")
def enregistrer_edition(rid: int, corps: dict = Body(...)):
    """La relecture : N° corrigé à la main, accroche, mot, légendes, photos retirées ou remises. Une édition approuvée
    qui change repasse « à relire »."""
    ed, _ = _edition_ou_404(rid)
    champs = {}
    if "numero_main" in corps:
        v = corps.get("numero_main")
        if v in (None, "", 0):
            champs["numero_main"] = None
        else:
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise HTTPException(422, "Numéro illisible.")
            if not 2 <= n <= 99:
                raise HTTPException(422, "Numéro hors des valeurs possibles (2 à 99).")
            champs["numero_main"] = n
    if "accroche" in corps:
        champs["accroche"] = " ".join(str(corps.get("accroche") or "").split())[:80]
    if "mot" in corps:
        champs["mot"] = str(corps.get("mot") or "")[:4000]
    if "macaron" in corps:                      # 0.9.2 : place du macaron « Exclusif ! » (ou aucun)
        if corps.get("macaron") not in R.MACARONS:
            raise HTTPException(422, "Place du macaron inconnue (hg, hd, bg, bd ou aucun).")
        champs["macaron"] = corps["macaron"]
    if "titre_une" in corps:                    # 0.9.1 : vide = « [Nom] revient ! »
        champs["titre_une"] = " ".join(str(corps.get("titre_une") or "").split())[:90]
    if isinstance(corps.get("rumeurs"), list):     # 0.9.7 : 4 rumeurs au plus, imprimées en page 3
        champs["rumeurs"] = [x for x in (sans_numero(" ".join(str(x).split()))[:160] for x in corps["rumeurs"]) if x][:R.RUMEURS]
    if isinstance(corps.get("courrier"), list):    # 0.11 : 2 lettres au plus, page 4
        lettres_ = []
        for x in corps["courrier"]:
            if isinstance(x, dict):
                l = {k: " ".join(str(x.get(k) or "").split())[:n] for k, n in (("lettre", 260), ("signe", 60), ("reponse", 140))}
                if l["lettre"]:
                    lettres_.append(l)
        champs["courrier"] = lettres_[:R.LETTRES]
    if "code_barres" in corps:                 # 0.11.4 : vide = « Reviens vite, {prénom} ! »
        champs["code_barres"] = " ".join(str(corps.get("code_barres") or "").split())[:60]
    if "horoscope" in corps:
        champs["horoscope"] = sans_numero(" ".join(str(corps.get("horoscope") or "").split()))[:280]
    if "valides" in corps:                     # 0.17 : éléments validés à la relecture
        champs["valides"] = _valides(corps["valides"])
    if "evenement" in corps:                   # 0.15 : événement du séjour, pour l'IA seulement (jamais imprimé)
        champs["evenement"] = " ".join(str(corps.get("evenement") or "").split())[:200]
    if "indices_rumeurs" in corps:
        champs["indices_rumeurs"] = " ".join(str(corps.get("indices_rumeurs") or "").split())[:400]
    if "description_une" in corps:
        champs["description_une"] = " ".join(str(corps.get("description_une") or "").split())[:400]
    if isinstance(corps.get("photos"), list):
        recues = {str(x.get("id")): x for x in corps["photos"] if isinstance(x, dict)}
        photos = []
        for x in ed["photos"]:
            r = recues.get(x["id"])
            if r:
                x = {**x, "legende": " ".join(str(r.get("legende", x["legende"])).split())[:220] or R.legende(x),
                     "retiree": bool(r.get("retiree", x.get("retiree"))),
                     "description": " ".join(str(r.get("description", x.get("description", ""))).split())[:400],
                     "cadrage": r.get("cadrage") if r.get("cadrage") in R.CADRAGES else x.get("cadrage", "haut")}
            photos.append(x)
        champs["photos"] = photos
    if champs:
        # 0.17 : une édition approuvée repasse « à relire » seulement si un contenu change (pas pour une validation)
        if ed["etat"] == "approuve" and any(k != "valides" and champs[k] != ed.get(k) for k in champs):
            champs["etat"], champs["approuve_le"] = "a_relire", ""
        if "photos" in champs and ed["etat"] in ("a_relire", "approuve") and not any(not x["retiree"] for x in champs["photos"]):
            raise HTTPException(409, "Toutes les photos seraient retirées : remets-en une, ou « Compléter » pour en chercher d'autres.")
        ETAT["base"].maj_recidive(rid, **champs)
    return {"ok": True, "etat": ETAT["base"].recidive(rid)["etat"]}


def _contexte_photo(ed: dict, photo: dict | None) -> dict:
    """0.12 : le contexte Immich d'une photo (albums parlants, personnes), lu une fois puis gardé dans l'édition."""
    if not photo:
        return {"albums": [], "personnes": []}
    if "contexte" not in photo and ETAT["immich"].actif:
        ctx = ETAT["immich"].contexte(photo["id"], ed.get("immich_id") or "")
        photos = [{**x, "contexte": ctx} if x["id"] == photo["id"] else x for x in ed["photos"]]
        ETAT["base"].maj_recidive(ed["id"], photos=photos)
        photo["contexte"] = ctx
        ed["photos"] = photos
    return photo.get("contexte") or {"albums": [], "personnes": []}


@app.post("/api/recidives/{rid}/proposer")
def proposer_titres(rid: int, corps: dict = Body(...)):
    """0.9.1 : {cible: « une » ou l'id d'une photo, description} → 5 titres de 60 caractères au plus, proposés par
    l'IA du PC d'après la description écrite par Julien (la photo ne part pas). La description et les propositions
    sont gardées ; rien n'est choisi à sa place. PC injoignable : 503 avec la marche à suivre."""
    ed, p = _edition_ou_404(rid)
    modele = _modele_demande(corps)
    cible = str(corps.get("cible") or "")
    description = " ".join(str(corps.get("description") or "").split())[:400]
    photo = next((x for x in ed["photos"] if x["id"] == cible), None)
    if cible != "une" and not photo:
        raise HTTPException(404, "Photo introuvable dans cette édition.")
    une = next((x for x in ed["photos"] if not x.get("retiree")), None)      # la photo de la une : la première gardée
    contexte = _contexte_photo(ed, une if cible == "une" else photo)
    try:
        props = ETAT["ollama"].proposer(description, "une" if cible == "une" else "photo", ed["genre"], _prenom(p),
                                        deja=_deja_paru(p["id"], rid), contexte=contexte, modele=modele)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    if cible == "une":
        ETAT["base"].maj_recidive(rid, description_une=description, propositions_une=props)
    else:
        photos = [{**x, "description": description, "propositions": props} if x["id"] == cible else x for x in ed["photos"]]
        ETAT["base"].maj_recidive(rid, photos=photos)
    ETAT["base"].noter("recidive", p["id"], f"{len(props)} titre(s) proposé(s) par l'IA ({'une' if cible == 'une' else 'photo'})")
    return {"propositions": props, "modele": modele or ia.MODELE}


@app.post("/api/recidives/{rid}/rumeurs")
def proposer_rumeurs(rid: int, corps: dict = Body(default={})):
    """0.9.7 : {indices} (facultatif, ce qu'on sait de l'invité) → 8 rumeurs loufoques inventées par l'IA du PC, pour la
    rubrique « Les rumeurs de la rédaction » (page 3). Rien n'est choisi à la place de Julien."""
    ed, p = _edition_ou_404(rid)
    modele = _modele_demande(corps)
    indices = " ".join(str(corps.get("indices") or "").split())[:400]
    gardees = [x for x in ed["photos"] if not x.get("retiree")]
    ctxs = [_contexte_photo(ed, x) for x in gardees]          # 0.12 : albums et personnes des photos
    vues = [" — ".join(t for t in (x.get("description", ""), texte_contexte(c)) if t) for x, c in zip(gardees, ctxs)]
    vues.append(ed.get("description_une", ""))
    for x in _parus_carnet(p, ed)[:3]:          # 0.16 : photos des numéros précédents (fiche de carnet), en clin d'œil
        vues += [f"(numéro de {x.get('le', '')[:4]}) {d}" for d in (x.get("descriptions") or [])[:3]]
    gens = list(dict.fromkeys(g for c in ctxs for g in c.get("personnes") or []))
    try:
        props = ETAT["ollama"].rumeurs(_avec_livre(p, indices), ed["genre"], _prenom(p), vues, deja=_deja_paru(p["id"], rid), personnes=gens,
                                       modele=modele)
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    ETAT["base"].maj_recidive(rid, indices_rumeurs=indices, propositions_rumeurs=props)
    ETAT["base"].noter("recidive", p["id"], f"{len(props)} rumeur(s) proposée(s) par l'IA")
    return {"propositions": props, "carnet": _garder_indices(p, indices), "modele": modele or ia.MODELE}


def _avec_livre(p: dict, indices: str) -> str:
    """0.19 : les indices pour l'IA, complétés par ce que la personne a écrit dans le livre d'or de la maison (fiche de
    carnet ≥ 2.31, envoyé par Home Assistant). Pour les rumeurs, le courrier et le droit de réponse ; jamais imprimé
    tel quel, jamais renvoyé dans « Pour les journaux »."""
    mots = [m for m in (_contact(p).get("livre_or") or []) if (m.get("message") or "").strip()][:3]
    if not mots:
        return indices
    livre = " ; ".join(f"« {' '.join(m['message'].split())[:220]} » ({m.get('le', '')[:4]})" for m in mots)
    return (indices + " — " if indices else "") + f"Ce que {_prenom(p)} a écrit dans le livre d'or de la maison : {livre}"


def _garder_indices(p: dict, indices: str) -> str:
    """0.10 : les indices écrits dans l'édition sont gardés dans carnet (« Pour les journaux »), pour le séjour suivant.
    Rend ce qui s'est passé, pour l'écran ; jamais une erreur de page."""
    contact = _contact(p)
    if not contact.get("personne_id"):
        return "pas gardé : carnet ne trouve pas cette personne"
    if (contact.get("journaux") or "") == indices:
        return "déjà dans carnet"
    if ETAT["cfg"].lecture_seule:
        return "pas gardé : lecture seule"
    try:
        ETAT["carnet"].ecrire_journaux(contact["personne_id"], indices)
    except Exception as ex:  # noqa: BLE001 — carnet arrêté, ancienne version, jeton
        return f"pas gardé dans carnet ({str(ex).splitlines()[0][:120]})"
    ETAT["base"].noter("carnet", p["id"], "« Pour les journaux » gardé dans carnet")
    return "gardé dans carnet"


@app.post("/api/recidives/{rid}/courrier")
def proposer_courrier(rid: int, corps: dict = Body(default={})):
    """0.11 : 4 fausses lettres de lecteurs, avec la réponse de la rédaction, pour la page 4. Rien n'est choisi."""
    ed, p = _edition_ou_404(rid)
    modele = _modele_demande(corps)
    indices = " ".join(str(corps.get("indices") or ed.get("indices_rumeurs") or "").split())[:400]
    try:
        props = ETAT["ollama"].courrier(_avec_livre(p, indices), ed["genre"], _prenom(p), deja=_deja_paru(p["id"], rid),
                                        modele=modele)
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    ETAT["base"].maj_recidive(rid, propositions_courrier=props)
    return {"propositions": props, "modele": modele or ia.MODELE}


@app.post("/api/recidives/{rid}/horoscope")
def proposer_horoscope(rid: int, corps: dict = Body(default={})):
    """0.11 : 3 horoscopes loufoques du séjour, d'après le signe (calculé de la date de naissance, jamais imprimée)."""
    ed, p = _edition_ou_404(rid)
    modele = _modele_demande(corps)
    indices = " ".join(str(corps.get("indices") or ed.get("indices_rumeurs") or "").split())[:400]
    evenement = " ".join(str(corps.get("evenement") if "evenement" in corps else ed.get("evenement") or "").split())[:200]
    try:
        props = ETAT["ollama"].horoscope(R.signe(p.get("naissance", ""))[0], indices, ed["genre"], _prenom(p),
                                         deja=_deja_paru(p["id"], rid), evenement=evenement,
                                         avant=_evenements_avant(p["id"], ed), modele=modele)
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    ETAT["base"].maj_recidive(rid, propositions_horoscope=props, evenement=evenement)
    return {"propositions": props, "modele": modele or ia.MODELE}


@app.post("/api/recidives/{rid}/mot")
def proposer_droit(rid: int, corps: dict = Body(default={})):
    """0.18.1 : 3 versions du droit de réponse (mot des hôtes, page 4), d'après les indices, l'événement du séjour et ce
    que raconte le numéro (gros titre, rumeurs). Rien n'est choisi à la place de Julien."""
    ed, p = _edition_ou_404(rid)
    modele = _modele_demande(corps)
    faits = [ed.get("titre_une") or "", ed.get("evenement") or "", *(ed.get("rumeurs") or [])[:4]]
    try:
        props = ETAT["ollama"].gazette("droit", str(corps.get("texte") or ""), None, None, _prenom(p), ed["genre"],
                                       _avec_livre(p, ed.get("indices_rumeurs") or ""), _journal()["chez"], [x for x in faits if x.strip()],
                                       modele=modele)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except RuntimeError as ex:
        raise HTTPException(503, str(ex))
    return {"propositions": props, "modele": modele or ia.MODELE}


@app.post("/api/recidives/{rid}/preparer")
def repreparer_edition(rid: int, corps: dict = Body(default={})):
    """De nouveau depuis Immich. `completer: true` garde les photos et légendes de la relecture et remplace seulement
    les photos retirées ; sinon tout est refait (le mot, l'accroche et le N° corrigé sont gardés)."""
    ed, _ = _edition_ou_404(rid)
    ETAT["base"].maj_recidive(rid, erreur="")
    demander_recidive(rid, bool(corps.get("completer")))
    return {"ok": True}


@app.get("/api/recidives/{rid}/photos/{asset}")
def photo_edition(rid: int, asset: str):
    ed, _ = _edition_ou_404(rid)
    if asset not in {x["id"] for x in ed["photos"]}:
        raise HTTPException(404, "Photo introuvable dans cette édition.")
    octets = ETAT["immich"].gardee(asset) or ETAT["immich"].apercu(asset)
    if not octets:
        raise HTTPException(404, "Aperçu indisponible (Immich injoignable ?).")
    return Response(octets, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


def _rendre_edition(rid: int, mode: str) -> tuple[str, dict, dict]:
    ed, p = _edition_ou_404(rid)
    ed = {**ed, "mot": _mot_recidive(ed, p), "accroche": ed["accroche"] or R.accroche(ed["genre"], _prenom(p), _journal())}
    return rendu_recidive.document(p, ed, _journal(), ETAT["immich"].gardee, mode=mode), p, ed


@app.get("/api/recidives/{rid}/apercu")
def apercu_edition(rid: int, mode: str = "ecran"):
    doc, _, _ = _rendre_edition(rid, mode if mode in ("ecran", "impose", "lecture") else "ecran")
    return HTMLResponse(doc, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:; img-src data:"})


@app.get("/api/recidives/{rid}/pdf")
def pdf_edition(rid: int, mode: str = "impose"):
    mode = mode if mode in ("impose", "lecture") else "impose"
    doc, p, ed = _rendre_edition(rid, mode)
    try:
        contenu, deborde = rendu.pdf(doc, mode)
    except rendu.RenduImpossible as ex:
        raise HTTPException(503, str(ex))
    nom = "la-recidive-" + str(ed["numero_main"] or ed["numero"]) + "-" + \
          "".join(ch if ch.isalnum() else "-" for ch in p["nom"].lower()).strip("-") + f"-{mode}.pdf"
    return Response(contenu, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "X-Debordements": ",".join(map(str, deborde))})


@app.get("/api/recidives/{rid}/mesure")
def mesure_edition(rid: int):
    doc, _, _ = _rendre_edition(rid, "lecture")
    try:
        return {"pages": rendu.mesurer(doc)}
    except rendu.RenduImpossible as ex:
        raise HTTPException(503, str(ex))


@app.post("/api/recidives/{rid}/approuver")
def approuver_edition(rid: int):
    """Contrôle qu'aucune page ne déborde, puis approuve ; les anciens scandales de l'édition sont notés comme parus
    (ils ne reviendront qu'une fois tous les autres publiés)."""
    doc, p, ed = _rendre_edition(rid, "impose")
    vues = [x for x in ed["photos"] if not x.get("retiree")]
    if ed["etat"] not in ("a_relire", "approuve") or not vues:
        raise HTTPException(409, "Édition pas encore prête (aucune photo).")
    try:
        _, deborde = rendu.pdf(doc, "impose")
    except rendu.RenduImpossible:
        deborde = []                      # sans Chromium (tests), pas de contrôle
    if deborde:
        raise HTTPException(409, "Texte trop long : la page " + ", ".join(map(str, deborde))
                            + " déborde. Raccourcis une légende ou le mot des hôtes.")
    if ed.get("essai"):                        # 0.20 : un essai ne compte jamais (scandales, carnet, numéros)
        ETAT["base"].maj_recidive(rid, etat="approuve", approuve_le=maintenant())
        return {"ok": True, "carnet": "essai : rien envoyé à carnet"}
    ETAT["base"].publier(p["id"], [x["id"] for x in vues if x.get("ancien")])
    ETAT["base"].maj_recidive(rid, etat="approuve", approuve_le=maintenant())
    ETAT["base"].noter("approuver", p["id"], f"La Récidive N° {ed['numero_main'] or ed['numero']}")
    return {"ok": True, "carnet": _envoyer_a_carnet(p, ETAT["base"].recidive(rid))}


def _envoyer_a_carnet(p: dict, ed: dict) -> str:
    """0.16 : à l'approbation, tout ce qui a été saisi et imprimé part sur la fiche de carnet (choix de Julien du
    17/11 : tout centraliser sur la fiche contact) — indices dans « Pour les journaux », le numéro dans « Journaux
    parus ». Rend ce qui s'est passé, pour l'écran ; jamais une erreur (l'approbation est faite)."""
    contact = _contact(p)
    if not contact.get("personne_id"):
        return "pas envoyé à carnet : carnet ne trouve pas cette personne"
    if ETAT["cfg"].lecture_seule:
        return "pas envoyé à carnet : lecture seule"
    vues = [x for x in ed["photos"] if not x.get("retiree")]
    textes = [ed.get("titre_une") or "", *[x.get("legende", "") for x in vues if x.get("legende") != R.legende(x)],
              *(ed.get("rumeurs") or []), ed.get("horoscope") or "",
              *[f"{x.get('lettre', '')} — {x.get('signe') or 'Un lecteur'}" + (f" / La rédaction : {x['reponse']}" if x.get("reponse") else "")
                for x in ed.get("courrier") or [] if x.get("lettre")]]
    corps = {"journal": "recidive", "numero": ed.get("numero_main") or ed["numero"], "le": ed["sejour_du"],
             "titre": ed.get("titre_une") or R.titre_une(p["nom"]),
             "evenement": ed.get("evenement") or "", "indices": ed.get("indices_rumeurs") or "",
             "descriptions": [d for d in [ed.get("description_une") or "", *[x.get("description", "") for x in vues]] if d.strip()],
             "textes": [t for t in dict.fromkeys(x.strip() for x in textes) if t]}
    if ed.get("indices_rumeurs"):
        _garder_indices(p, ed["indices_rumeurs"])
    try:
        ETAT["carnet"].ecrire_paru(contact["personne_id"], f"recidive-{ed['sejour_du']}", corps)
    except Exception as ex:  # noqa: BLE001 — carnet arrêté, ancienne version, jeton
        message = f"pas envoyé à carnet ({str(ex).splitlines()[0][:120]})"
        ETAT["base"].noter("erreur", p["id"], f"La Récidive : {message}"[:200])
        return message
    ETAT["base"].noter("carnet", p["id"], f"La Récidive N° {corps['numero']} rangée dans carnet (Journaux parus)")
    return "rangé sur la fiche de carnet"


def _parus_carnet(p: dict, ed: dict) -> list[dict]:
    """0.16 : les numéros parus rangés sur la fiche de carnet, sauf celui de ce séjour."""
    return [x for x in (_contact(p).get("parus") or []) if x.get("le") != ed.get("sejour_du")]


# ================================================================ 0.20 : essais (Réglages › Simuler) et archives

@app.get("/api/essais")
def essais():
    """Les numéros d'essai en cours : Gazettes (fiches d'essai) et Récidives d'essai."""
    base: Base = ETAT["base"]
    res = []
    for p in base.personnes(essais=True):
        if p.get("essai_de"):
            lv = base.livret(p["id"]) or {}
            res.append({"journal": "gazette", "id": p["id"], "nom": p["nom"], "etat": lv.get("etat", ""), "lien": f"#/livret/{p['id']}"})
    for ed in base.recidives(essais=True):
        p = base.personne(ed["personne_id"]) or {"nom": "?"}
        res.append({"journal": "recidive", "id": ed["id"], "nom": p["nom"], "etat": ed["etat"], "lien": f"#/recidive/{ed['id']}",
                    "numero": ed["numero_main"] or ed["numero"]})
    return {"essais": res}


@app.post("/api/essais")
def creer_essai(corps: dict = Body(...)):
    """{personne_id, journal: gazette | recidive} → un numéro d'essai à part : jamais compté (N°, déjà paru, carnet,
    archives, Home Assistant), supprimable. Rend le lien de l'éditeur."""
    base: Base = ETAT["base"]
    try:
        p = base.personne(int(corps.get("personne_id")))
    except (TypeError, ValueError):
        p = None
    if not p or p.get("essai_de"):
        raise HTTPException(404, "Fiche introuvable.")
    journal_ = corps.get("journal")
    if journal_ == "gazette":
        pid = base.creer_essai(p)
        base.noter("essai", p["id"], "Gazette d'essai créée")
        demander_preparation(pid)
        return {"lien": f"#/livret/{pid}"}
    if journal_ == "recidive":
        if not ETAT["immich"].actif:
            raise HTTPException(409, "Immich n'est pas réglé (GAZETTE_IMMICH_CLE vide) : pas de Récidive possible.")
        n, _ = _numero_et_precedent(p, date.today().isoformat())
        rid = base.creer_essai_recidive(p["id"], max(2, n))
        ed = base.recidive(rid)
        _, prec = _numero_et_precedent(p, ed["sejour_du"])
        base.maj_recidive(rid, precedent=prec or {})
        base.noter("essai", p["id"], "Récidive d'essai créée")
        demander_recidive(rid)
        return {"lien": f"#/recidive/{rid}"}
    raise HTTPException(422, "Journal inconnu (gazette ou recidive).")


@app.delete("/api/essais/{journal_}/{ident}")
def supprimer_essai(journal_: str, ident: int):
    base: Base = ETAT["base"]
    if journal_ == "gazette":
        p = base.personne(ident)
        if not p or not p.get("essai_de"):
            raise HTTPException(404, "Essai introuvable.")
        base.supprimer_personne(ident)
    elif journal_ == "recidive":
        ed = base.recidive(ident)
        if not ed or not ed.get("essai"):
            raise HTTPException(404, "Essai introuvable.")
        base.supprimer_recidive(ident)
    else:
        raise HTTPException(422, "Journal inconnu.")
    return {"ok": True}


def _archives() -> list[dict]:
    """0.20 : les numéros approuvés dont le séjour est fini — la Gazette du premier séjour, chaque Récidive — du plus
    récent au plus ancien. Ils quittent la liste Livrets."""
    base: Base = ETAT["base"]
    auj = date.today().isoformat()
    res = []
    for p in base.personnes():
        lv = base.livret(p["id"]) or {}
        sej = base.sejours_de(p["id"])
        if lv.get("etat") == "approuve" and sej and sej[0]["jusqu_au"] < auj:
            res.append({"journal": "gazette", "id": p["id"], "personne_id": p["id"], "nom": p["nom"], "numero": 1,
                        "sejour": sej[0], "approuve_le": lv.get("approuve_le", ""),
                        "titre": ((lv.get("contenu") or {}).get("une") or {}).get("titre", ""), "lien": f"#/livret/{p['id']}",
                        "pdf": f"/api/livrets/{p['id']}/pdf"})
    for ed in base.recidives():
        if ed["etat"] != "approuve":
            continue
        s = next((x for x in base.sejours_de(ed["personne_id"]) if x["du"] == ed["sejour_du"]), None)
        if not s or s["jusqu_au"] >= auj:
            continue
        p = base.personne(ed["personne_id"]) or {"nom": "?"}
        res.append({"journal": "recidive", "id": ed["id"], "personne_id": ed["personne_id"], "nom": p["nom"],
                    "numero": ed["numero_main"] or ed["numero"], "sejour": s, "approuve_le": ed["approuve_le"],
                    "titre": ed.get("titre_une") or R.titre_une(p["nom"]), "lien": f"#/recidive/{ed['id']}",
                    "pdf": f"/api/recidives/{ed['id']}/pdf"})
    return sorted(res, key=lambda x: (x["sejour"]["du"], x["nom"]), reverse=True)


@app.get("/api/archives")
def archives():
    return {"archives": _archives()}


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
                fiches.append({"nom": i["nom"], "chambre": s["chambre"], "du": s["du"], "jusqu_au": s["jusqu_au"],
                               "carnet": _carnet_sur(i["nom"])})
    relire, erreurs, annivs = [], [], []
    # 0.9 : un invité attendu dont le séjour a une Récidive n'attend pas sa Gazette
    editions_attendues, attendus = {}, set()
    for s in base.sejours():
        for i in s["invites"]:
            if not i["personne_id"]:
                continue
            ed = base.recidive_de(i["personne_id"], s["du"])
            if ed and ed["etat"] != "vide":
                editions_attendues[ed["id"]] = s
            else:
                attendus.add(i["personne_id"])
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
    recidives, scandales = [], []
    ign_scandales = base.ignores("scandale")
    for ed in base.recidives():
        if ed["etat"] == "approuve":
            continue
        nom = (base.personne(ed["personne_id"]) or {}).get("nom", "?")
        attendu = ed["id"] in editions_attendues
        if ed["erreur"]:
            erreurs.append({"id": ed["personne_id"], "nom": nom, "erreur": ed["erreur"], "recidive": ed["id"]})
        if ed["etat"] == "a_relire":
            recidives.append({"id": ed["id"], "personne_id": ed["personne_id"], "nom": nom, "attendu": attendu,
                              "numero": ed["numero_main"] or ed["numero"], "sejour_du": ed["sejour_du"]})
        cle = str(ed["personne_id"])
        if ed["manque_scandale"] and ed["etat"] == "a_relire" and cle not in ign_scandales:
            scandales.append({"id": ed["id"], "personne_id": ed["personne_id"], "nom": nom, "cle": cle,
                              "tag_absent": ed["tag_absent"],
                              "photos": sum(1 for x in ed["photos"] if not x.get("retiree")), "places": R.PLACES})
    recidives.sort(key=lambda x: not x["attendu"])
    # Date d'une fiche différente de celle de carnet (contact unique au même nom, date complète)
    dates = []
    if ETAT["carnet"].actif:
        ign_dates = base.ignores("date")
        for p in base.personnes():
            c = ETAT["carnet"].date_sure([p["nom"], *p["alias"]])
            if c and c["naissance"] != p["naissance"] and f"{p['id']}:{c['naissance']}" not in ign_dates:
                dates.append({"id": p["id"], "nom": p["nom"], "gazette": p["naissance"], "carnet": c["naissance"],
                              "cle": f"{p['id']}:{c['naissance']}"})
    return {"fiches": fiches, "relire": relire, "anniversaires": annivs, "erreurs": erreurs, "dates": dates,
            "recidives": recidives, "scandales": scandales,
            "total": len(fiches) + len(relire) + len(annivs) + len(erreurs) + len(dates) + len(recidives) + len(scandales)}


def _carnet_sur(nom: str) -> dict | None:
    """Ce que carnet sait d'un invité sans fiche : date complète (création possible) ou partielle (année inconnue)."""
    trouves = ETAT["carnet"].chercher(nom) if ETAT["carnet"].actif else []
    if len(trouves) != 1:
        return {"plusieurs": True} if trouves else None
    c = trouves[0]
    return {"naissance": c.get("naissance"), "jour": c.get("jour"), "mois": c.get("mois"), "annee": c.get("annee"),
            "nom": c.get("nom_carnet") or c.get("nom")}


@app.get("/api/a-traiter")
def route_a_traiter():
    return a_traiter()


@app.post("/api/a-traiter/ignorer")
def ignorer(corps: dict = Body(...)):
    sorte = corps.get("sorte")
    if sorte not in ("fiche", "anniversaire", "date", "scandale"):
        raise HTTPException(422, "Sorte inconnue.")
    ETAT["base"].ignorer(sorte, str(corps.get("cle", ""))[:80])
    return {"ok": True}


@app.post("/api/a-traiter/creer-depuis-carnet")
def creer_depuis_carnet(corps: dict = Body(...)):
    """Invité sans fiche que carnet connaît : même création que celle faite à l'annonce de HA."""
    pid = _fiche_depuis_carnet(str(corps.get("nom", ""))[:80])
    if not pid:
        raise HTTPException(409, "Carnet ne donne pas de date complète et sûre pour ce nom : crée la fiche à la main.")
    return {"id": pid}


@app.get("/api/carnet/suggestions")
def suggestions_carnet(q: str = ""):
    return {"actif": ETAT["carnet"].actif, "suggestions": ETAT["carnet"].suggestions(q[:80])}


# ================================================================ Connexion et Réglages

@app.get("/api/connexion/etat")
def etat_connexions():
    base: Base = ETAT["base"]
    cfg: Config = ETAT["cfg"]
    return {"sources": base.stats_sources(), "erreurs": ETAT["sources"].erreurs,
            "ha": {"porte": bool(cfg.jeton_ha), "dernier_appel": base.reglage("ha_dernier_appel"),
                   "dernier_corps": base.reglage("ha_dernier_resume")},
            "rendu": {"polices": rendu.polices_presentes()},
            "larousse": _journal()["larousse"],
            "carnet": ETAT["carnet"].etat(), "immich": ETAT["immich"].etat(), "ia": _ia_etat(),
            "rendu_recidive": {"polices": rendu_recidive.polices_presentes()}}


@app.post("/api/connexion/verifier")
def verifier_sources():
    r = ETAT["sources"].sonder()
    if ETAT["carnet"].actif:
        liste = ETAT["carnet"].personnes(forcer=True)
        err = ETAT["carnet"].erreur
        r["carnet"] = {"ok": not err, "detail": err or f"{len(liste)} contacts, {sum(1 for p in liste if p.get('naissance'))} avec date complète"}
    else:
        r["carnet"] = {"ok": None, "detail": "pas réglé (MAISON_JETON vide)"}
    for cle in ("immich", "ollama"):        # 0.20.3 : une sonde qui plante ne fait plus tomber toute la vérification
        try:
            r["ia" if cle == "ollama" else cle] = (ETAT[cle].sonder(_ia_etat()["modele_second"]) if cle == "ollama"
                                                   else ETAT[cle].sonder())
        except Exception as ex:  # noqa: BLE001
            r["ia" if cle == "ollama" else cle] = {"ok": False, "detail": f"vérification impossible ({type(ex).__name__} : {ex})"[:200]}
    return r


@app.get("/api/reglages")
def reglages():
    cfg: Config = ETAT["cfg"]
    j = _journal()
    return {"reglages": j, "journal": j,
            "champs": {k: {"libelle": v[0], "aide": v[1], "maxi": v[2]} for k, v in journal.CHAMPS.items()},
            "libelles": journal.LIBELLES,
            "lecture_seule": cfg.lecture_seule, "lecture_seule_origine": _origine_lecture_seule(), "version": __version__,
            "historique": ETAT["base"].journal(40)}


def _changer_reglages(corps, statut: int, geste: str) -> dict:
    """Contrôle, garde et applique les réglages (le journal). Ils valent aussitôt pour les aperçus et les PDF ;
    un mot des hôtes déjà écrit dans un livret est gardé."""
    try:
        j = journal.valider(corps, _journal())
    except ValueError as ex:
        raise HTTPException(statut, str(ex))
    journal.enregistrer(ETAT["base"], j)
    ETAT["sources"].larousse_actif = j["larousse"]
    ETAT["base"].noter("reglages", None, geste)
    return j


@app.put("/api/reglages")
def enregistrer_reglages(corps=Body(...)):
    """Contrat de sauvegarde 1 : mauvais type ou valeur refusée → 400 avec le message."""
    return _changer_reglages(corps, 400, "le journal")


@app.put("/api/reglages/journal")
def enregistrer_journal(corps=Body(...)):
    """Ancienne adresse (0.3), gardée : même chose, refus en 422."""
    return _changer_reglages(corps, 422, "le journal")


# ================================================================ sauvegarde et restauration (contrat de sauvegarde 1)

@app.get("/externe/sauvegarde")
def externe_sauvegarde(request: Request):
    """Pour l'Anneau (collecte de nuit) : les réglages d'usage de Gazette et sa version, rien d'autre. Porte ouverte
    par le jeton commun seul (MAISON_JETON) ; jeton commun vide : porte fermée (404)."""
    acceptes = maison.jetons()
    if not acceptes:
        raise HTTPException(404, "Not Found")
    if not maison.jeton_valide(maison.jeton_propose(request.headers), acceptes):
        raise HTTPException(401, "Jeton manquant ou invalide.")
    return maison.sauvegarde(APPLI, __version__, _journal(), exclus=journal.EXCLUS)


class AnneauMuet(Exception):
    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut, self.message = statut, message


def _lire_sauvegarde(le: str = "") -> dict:
    """Chez l'Anneau ; dans les tests et la démo, ETAT["anneau_lire"] remplace la lecture réseau."""
    try:
        r = maison.lire_sauvegarde(APPLI, le, lire=ETAT.get("anneau_lire"))
    except Exception as ex:  # noqa: BLE001 — Anneau arrêté, réseau, jeton : un message, jamais une erreur de page
        if getattr(ex, "code", None) == 404:
            raise AnneauMuet(404, f"L'Anneau n'a pas de sauvegarde de Gazette{' du ' + le if le else ''}.")
        if getattr(ex, "code", None) in (401, 403):
            raise AnneauMuet(503, "L'Anneau refuse le jeton (MAISON_JETON différent ou vide).")
        raise AnneauMuet(503, f"Anneau injoignable ({ex.__class__.__name__}) : réessaie plus tard.")
    if not isinstance(r, dict):
        raise AnneauMuet(503, "Réponse de l'Anneau illisible.")
    return r


@app.exception_handler(AnneauMuet)
async def _anneau_muet(_: Request, exc: AnneauMuet):
    return JSONResponse({"detail": exc.message}, status_code=exc.statut)


def _jour(le) -> str:
    le = str(le or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", le):
        raise HTTPException(400, "Date de sauvegarde attendue au format AAAA-MM-JJ.")
    return le


def _sauves(le: str) -> dict:
    r = _lire_sauvegarde(le)
    sauves = r.get("reglages")
    if not isinstance(sauves, dict):
        raise AnneauMuet(404, f"L'Anneau n'a pas de réglages de Gazette du {le}.")
    return r


@app.get("/api/restaurer")
def restaurer_voir(le: str = ""):
    """Sans « le » : les dates des sauvegardes gardées par l'Anneau. Avec « le » : ce qui changerait."""
    if not le:
        dates = _lire_sauvegarde().get("dates") or []
        if not dates:
            raise AnneauMuet(404, "L'Anneau n'a encore aucune sauvegarde de Gazette.")
        return {"dates": [str(d) for d in dates]}
    le = _jour(le)
    r = _sauves(le)
    return {"le": le, "version": r.get("version", ""),
            "differences": maison.differences(_journal(), r["reglages"], journal.EXCLUS)}


@app.post("/api/restaurer")
def restaurer(corps: dict = Body(...)):
    """Remet les réglages d'une sauvegarde (réglages seulement : ni fiches ni livrets). Permis en lecture seule :
    rien ne sort de Gazette."""
    le = _jour(corps.get("le"))
    r = _sauves(le)
    diff = maison.differences(_journal(), r["reglages"], journal.EXCLUS)
    if not diff:
        return {"reglages": _journal(), "restaures": [], "message": "Rien à restaurer : les réglages sont déjà ceux-là."}
    try:
        j = journal.valider({d["cle"]: d["sauve"] for d in diff}, _journal())
    except ValueError as ex:
        raise HTTPException(422, f"Sauvegarde du {le} refusée : {ex}")
    journal.enregistrer(ETAT["base"], j)
    ETAT["sources"].larousse_actif = j["larousse"]
    noms = ", ".join(journal.LIBELLES.get(d["cle"], d["cle"]) for d in diff)
    ETAT["base"].noter("reglages", None, f"restaurés depuis la sauvegarde du {le} : {noms}")
    return {"reglages": j, "restaures": [d["cle"] for d in diff]}


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
    # Invité sans fiche que carnet connaît (un seul contact, date complète) : la fiche est créée et le livret
    # préparé ; relecture et approbation restent à faire.
    crees = [n for n in (i["nom"] for i in sejour["invites"] if i["personne_id"] is None) if _fiche_depuis_carnet(n)]
    if crees:
        sejour = next(s for s in base.sejours(depuis="0000") if s["id"] == sid)
    invites, manquants, relire, annivs = [], [], [], []
    for i in sejour["invites"]:
        if i["personne_id"] is None:
            manquants.append(i["nom"])
            invites.append({"nom": i["nom"], "fiche": False, "livret": None, "lien": ""})
            continue
        p = base.personne(i["personne_id"])
        ed = _edition_du_sejour(p["id"], du.isoformat())
        if ed and ed["etat"] != "vide":                 # 0.9 : à partir du 2e séjour, La Récidive remplace la Gazette
            if ed["etat"] != "approuve":
                relire.append(i["nom"])
            invites.append({"nom": i["nom"], "fiche": True, "journal": "recidive", "numero": ed["numero_main"] or ed["numero"],
                            "livret": ed["etat"], "lien": _lien_edition(ed["id"]), "anniversaire": None})
            continue
        lv = base.livret(p["id"])
        if lv["etat"] == "a_preparer" and not lv["erreur"]:
            demander_preparation(p["id"])
            lv = base.livret(p["id"])
        cas = anniversaire.proche(date.fromisoformat(p["naissance"]), du, fin)
        if lv["etat"] in ("a_relire", "en_preparation", "a_preparer"):
            relire.append(i["nom"])
        if cas:
            annivs.append({"nom": i["nom"], **cas})
        invites.append({"nom": i["nom"], "fiche": True, "journal": "gazette", "livret": lv["etat"], "lien": _lien(p["id"]),
                        "anniversaire": cas})
    base.poser_reglage("ha_dernier_resume", f"{chambre} : {', '.join(noms)} ({du.isoformat()} → {fin.isoformat()})")
    return {"chambre": chambre, "invites": invites, "manquants": manquants, "a_relire": relire, "anniversaires": annivs,
            "depuis_carnet": crees}


def _fiche_depuis_carnet(nom: str) -> int | None:
    """Crée la fiche d'un invité d'après carnet (contact unique, date complète) et lance la préparation."""
    base: Base = ETAT["base"]
    if base.trouver(nom):
        return None
    c = ETAT["carnet"].date_sure([nom])
    if not c:
        return None
    nom_fiche = " ".join((c.get("nom_carnet") or c.get("nom") or nom).split())[:80]
    alias = []
    for autre in (nom, c.get("nom", "")):
        if autre and cle_nom(autre) != cle_nom(nom_fiche) and cle_nom(autre) not in map(cle_nom, alias):
            alias.append(" ".join(autre.split())[:80])
    prenom = " ".join((c.get("prenom") or nom_fiche.split(" ")[0]).split())[:40]
    pid = base.creer_personne(nom_fiche, prenom, c["naissance"], "France", alias)
    base.noter("fiche", pid, "créée d'après carnet")
    demander_preparation(pid)
    return pid


@app.get("/ha/etat")
def ha_etat():
    """Pour le capteur de Home Assistant : ce qui attend un geste des hôtes, en phrases courtes."""
    t = a_traiter()
    lignes = [f"{f['nom']} ({f['chambre']}, {f['du']}) : pas de fiche dans Gazette" for f in t["fiches"]]
    lignes += [f"{r['nom']} : livret à relire" for r in t["relire"] if r["attendu"]]
    lignes += [f"{r['nom']} : La Récidive N° {r['numero']} à relire" for r in t["recidives"] if r["attendu"]]
    lignes += [f"{a['nom']} : anniversaire {a['libelle']} ({a['anniversaire']})" for a in t["anniversaires"]]
    return {"a_traiter": len(lignes), "fiches_manquantes": len(t["fiches"]),
            "a_relire": sum(1 for r in t["relire"] if r["attendu"]) + sum(1 for r in t["recidives"] if r["attendu"]),
            "anniversaires": len(t["anniversaires"]),
            "liste": lignes, "adresse": _adresse()}


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
