"""Lecture de carnet (l'appli de contacts de la maison) : noms et dates de naissance.

Gazette lit `GET /gazette/personnes` avec le jeton commun de la maison (MAISON_JETON ; 0.8 : plus d'ancien jeton
par paire) et n'écrit jamais rien dans carnet. La liste est gardée en mémoire 10 minutes (et la dernière bonne dans
la base, pour survivre à une panne de carnet).

Usages :
- un invité annoncé par Home Assistant sans fiche : si carnet connaît un seul contact à ce nom avec une date
  complète, la fiche est créée et le livret préparé (relecture et approbation restent à faire) ;
- la saisie d'une fiche propose les contacts de carnet ;
- une fiche dont la date diffère de celle de carnet arrive dans À traiter.

0.23 : la « fiche complète » pour les journaux (carnet 2.33), pépite par pépite, avec le même jeton :
`GET /gazette/personnes/{personne_id}/fiche`, `POST …/fiche/pepites`, `PUT` et `DELETE …/fiche/pepites/{id}`
(corps avec `le` : refus 409 si la pépite a changé entre-temps), `POST …/fiche/parues` ({ids, date}). La dernière
fiche bien lue est gardée dans la base (lecture seule « carnet injoignable », filtre des sujets interdits).
"""
from __future__ import annotations

import json
import time
from datetime import date
from typing import Callable

import httpx

from .base import Base, cle_nom, maintenant
from .fiche import pepites_valides as fiche_pepites

DUREE = 600          # secondes : fraîcheur de la liste en mémoire
DELAI = 8            # secondes : délai d'une lecture


def _lire_http(url: str, jeton: str) -> list[dict]:
    r = httpx.get(f"{url}/gazette/personnes", headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par carnet (MAISON_JETON différent de celui de carnet)")
    r.raise_for_status()
    return list(r.json().get("personnes") or [])


def _ecrire_http(url: str, jeton: str, personne_id: str, texte: str) -> None:
    r = httpx.put(f"{url}/gazette/personnes/{personne_id}/journaux", json={"texte": texte},
                  headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par carnet (MAISON_JETON différent de celui de carnet)")
    if r.status_code == 404:
        raise RuntimeError("carnet ne connaît pas cette adresse (carnet 2.29 nécessaire)")
    r.raise_for_status()


def _paru_http(url: str, jeton: str, personne_id: str, cle: str, corps: dict) -> None:
    r = httpx.put(f"{url}/gazette/personnes/{personne_id}/parus/{cle}", json=corps,
                  headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par carnet (MAISON_JETON différent de celui de carnet)")
    if r.status_code in (404, 405):
        raise RuntimeError("carnet ne connaît pas cette adresse (carnet 2.30 nécessaire)")
    r.raise_for_status()


class ErreurFiche(Exception):
    """0.23 : une demande de fiche refusée ou impossible. `statut` : 401 jeton, 404 inconnu, 409 pépite changée,
    422 refusée par carnet, 503 carnet injoignable (arrêté, réseau) ou pas réglé."""
    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut, self.message = statut, message


Requete = Callable[[str, str, str, str, dict | None], tuple[int, dict]]


def _fiche_http(url: str, jeton: str, methode: str, chemin: str, corps: dict | None) -> tuple[int, dict]:
    """Une demande à carnet : (statut, réponse JSON). Exceptions réseau laissées à l'appelant."""
    r = httpx.request(methode, f"{url}{chemin}", json=corps, headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    try:
        donnees = r.json()
    except ValueError:
        donnees = {}
    return r.status_code, donnees if isinstance(donnees, dict) else {"liste": donnees}


FICHE_DUREE = 30         # secondes : une fiche relue au plus toutes les 30 s pour l'IA (relue à chaque ouverture d'écran)


class Carnet:
    def __init__(self, url: str, jeton: str, base: Base, lire: Callable[[str, str], list[dict]] | None = None,
                 ecrire: Callable[[str, str, str, str], None] | None = None,
                 paru: Callable[[str, str, str, str, dict], None] | None = None,
                 fiche: Requete | None = None):
        self.url, self.jeton, self.base = url.rstrip("/"), jeton, base
        self._lire = lire or _lire_http
        self._ecrire = ecrire or _ecrire_http
        self._paru = paru or _paru_http
        self._fiche = fiche or _fiche_http
        self._fiches: dict[str, tuple[float, dict]] = {}
        self._liste: list[dict] | None = None
        self._lu_a = 0.0
        self.erreur = ""

    @property
    def actif(self) -> bool:
        return bool(self.url and self.jeton)

    def personnes(self, forcer: bool = False) -> list[dict]:
        """La liste de carnet (vide s'il n'est pas réglé). En panne : la dernière bonne liste gardée."""
        if not self.actif:
            return []
        if not forcer and self._liste is not None and time.monotonic() - self._lu_a < DUREE:
            return self._liste
        self._lu_a = time.monotonic()          # même en panne : pas une nouvelle tentative à chaque appel
        try:
            liste = self._lire(self.url, self.jeton)
            self._liste, self.erreur = liste, ""
            self.base.poser_reglage("carnet_liste", json.dumps(liste, ensure_ascii=False))
            self.base.poser_reglage("carnet_lu_le", maintenant())
        except Exception as ex:  # noqa: BLE001 — carnet arrêté, réseau, jeton : Gazette continue sans lui
            self.erreur = str(ex).splitlines()[0][:160] or ex.__class__.__name__
            if self._liste is None:
                garde = self.base.reglage("carnet_liste")
                self._liste = json.loads(garde) if garde else []
        return self._liste

    def chercher(self, nom: str) -> list[dict]:
        """Les contacts dont le nom (annoncé par HA ou celui de la fiche) est exactement ce nom (sans accents ni majuscules)."""
        c = cle_nom(nom)
        if not c:
            return []
        return [p for p in self.personnes() if c in (cle_nom(p.get("nom", "")), cle_nom(p.get("nom_carnet", "")))]

    def date_sure(self, noms: list[str]) -> dict | None:
        """Le contact unique qui porte l'un de ces noms, s'il a une date de naissance complète et possible."""
        trouves = {}
        for n in noms:
            for p in self.chercher(n):
                trouves[p.get("carnet_id") or id(p)] = p
        if len(trouves) != 1:
            return None
        p = next(iter(trouves.values()))
        try:
            d = date.fromisoformat(p.get("naissance") or "")
        except ValueError:
            return None
        return p if date(1900, 1, 1) <= d <= date.today() else None

    def suggestions(self, texte: str, n: int = 8) -> list[dict]:
        """Pour la saisie d'une fiche : contacts dont le nom contient ce texte."""
        c = cle_nom(texte)
        if len(c) < 2:
            return []
        res = []
        for p in self.personnes():
            if c in cle_nom(p.get("nom_carnet", "")) or c in cle_nom(p.get("nom", "")):
                res.append({"nom": p.get("nom_carnet") or p.get("nom", ""), "nom_ha": p.get("nom", ""),
                            "prenom": p.get("prenom", ""), "naissance": p.get("naissance"),
                            "jour": p.get("jour"), "mois": p.get("mois"), "annee": p.get("annee")})
        res.sort(key=lambda x: (not cle_nom(x["nom"]).startswith(c), x["nom"].casefold()))
        return res[:n]

    def ecrire_journaux(self, personne_id: str, texte: str) -> None:
        """0.10 : garde dans carnet (≥ 2.29) ce que Julien a écrit sur une personne pour les rumeurs. Seule écriture
        de Gazette chez carnet ; refusée en lecture seule par l'appelant."""
        if not self.actif or not personne_id:
            raise RuntimeError("carnet pas réglé ou personne inconnue de carnet")
        self._ecrire(self.url, self.jeton, personne_id, texte)
        for p in self._liste or []:                     # la liste en mémoire suit, sans relire carnet
            if p.get("personne_id") == personne_id:
                p["journaux"] = texte

    def ecrire_paru(self, personne_id: str, cle: str, corps: dict) -> None:
        """0.16 : range sur la fiche de carnet (≥ 2.30, « Journaux parus ») un numéro de La Récidive approuvé."""
        if not self.actif or not personne_id:
            raise RuntimeError("carnet pas réglé ou personne inconnue de carnet")
        self._paru(self.url, self.jeton, personne_id, cle, corps)
        for p in self._liste or []:                     # la liste en mémoire suit, sans relire carnet
            if p.get("personne_id") == personne_id:
                p["parus"] = [{"cle": cle, **corps}] + [x for x in p.get("parus") or [] if x.get("cle") != cle]

    # ------------------------------------------------------------ 0.23 : fiche complète (carnet 2.33)
    def _demander(self, methode: str, chemin: str, corps: dict | None = None) -> dict:
        if not self.actif:
            raise ErreurFiche(503, "carnet pas réglé (GAZETTE_CARNET_URL ou MAISON_JETON vide)")
        try:
            statut, donnees = self._fiche(self.url, self.jeton, methode, chemin, corps)
        except Exception as ex:  # noqa: BLE001 — carnet arrêté, réseau
            raise ErreurFiche(503, f"carnet injoignable ({str(ex).splitlines()[0][:120] or type(ex).__name__})") from ex
        if statut < 300:
            return donnees
        detail = str(donnees.get("detail") or "")[:200] if isinstance(donnees, dict) else ""
        if statut == 401:
            raise ErreurFiche(401, "jeton refusé par carnet (MAISON_JETON différent de celui de carnet)")
        if statut == 409:
            raise ErreurFiche(409, "Cette pépite a changé entre-temps (modifiée ailleurs) : la fiche est relue.")
        if statut in (404, 405):
            raise ErreurFiche(404, detail or "carnet ne connaît pas cette personne ou cette adresse (carnet 2.33 nécessaire)")
        if statut in (400, 422):
            raise ErreurFiche(422, detail or "carnet a refusé la pépite")
        raise ErreurFiche(503, f"carnet a répondu {statut}" + (f" ({detail})" if detail else ""))

    def fiche(self, personne_id: str, forcer: bool = True) -> dict:
        """La fiche complète : {pepites, connu, immich_id, lu_le, garde}. carnet injoignable : la dernière fiche bien lue
        (`garde` vrai) si elle existe, sinon ErreurFiche. `forcer` faux : 30 s de mémoire (demandes à l'IA)."""
        if not personne_id:
            raise ErreurFiche(404, "personne inconnue de carnet")
        vu = self._fiches.get(personne_id)
        if not forcer and vu and time.monotonic() - vu[0] < FICHE_DUREE:
            return vu[1]
        try:
            d = self._demander("GET", f"/gazette/personnes/{personne_id}/fiche")
        except ErreurFiche as ex:
            if ex.statut != 503:
                raise
            garde = self.base.reglage(f"fiche:{personne_id}")
            if not garde:
                raise
            f = {**json.loads(garde), "garde": True, "erreur": ex.message}
            self._fiches[personne_id] = (time.monotonic(), f)
            return f
        connu = d.get("connu") if isinstance(d.get("connu"), dict) else {}
        f = {"pepites": fiche_pepites(d.get("pepites")), "connu": connu,
             "immich_id": str(connu.get("immich_id") or d.get("immich_id") or ""), "lu_le": maintenant(), "garde": False}
        self.base.poser_reglage(f"fiche:{personne_id}", json.dumps(f, ensure_ascii=False))
        self._fiches[personne_id] = (time.monotonic(), f)
        return f

    def _oublier(self, personne_id: str) -> None:
        self._fiches.pop(personne_id, None)

    def ajouter_pepite(self, personne_id: str, corps: dict) -> dict:
        """{rubrique, texte, source, interdit} → la pépite créée par carnet (avec son id et son `le`)."""
        self._oublier(personne_id)
        d = self._demander("POST", f"/gazette/personnes/{personne_id}/fiche/pepites", corps)
        return d.get("pepite") if isinstance(d.get("pepite"), dict) else d

    def modifier_pepite(self, personne_id: str, pepite_id: str, corps: dict) -> dict:
        """{le, texte?, rubrique?, interdit?} → la pépite modifiée ; ErreurFiche 409 si elle a changé entre-temps."""
        self._oublier(personne_id)
        d = self._demander("PUT", f"/gazette/personnes/{personne_id}/fiche/pepites/{pepite_id}", corps)
        return d.get("pepite") if isinstance(d.get("pepite"), dict) else d

    def effacer_pepite(self, personne_id: str, pepite_id: str, le: str) -> None:
        self._oublier(personne_id)
        self._demander("DELETE", f"/gazette/personnes/{personne_id}/fiche/pepites/{pepite_id}", {"le": le})

    def marquer_parues(self, personne_id: str, ids: list[str], le: str) -> dict:
        """Les pépites qui ont servi aux textes d'un numéro approuvé reçoivent `parue_le`."""
        self._oublier(personne_id)
        return self._demander("POST", f"/gazette/personnes/{personne_id}/fiche/parues", {"ids": list(ids), "date": le})

    def etat(self) -> dict:
        liste = self._liste if self._liste is not None else None
        return {"regle": self.actif, "erreur": self.erreur, "lu_le": self.base.reglage("carnet_lu_le"),
                "personnes": len(liste) if liste is not None else None,
                "dates": sum(1 for p in liste if p.get("naissance")) if liste is not None else None}
