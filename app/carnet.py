"""Lecture de carnet (l'appli de contacts de la maison) : noms et dates de naissance.

Gazette lit `GET /gazette/personnes` avec son jeton (GAZETTE_CARNET_JETON, la même valeur que
CARNET_JETON_GAZETTE côté carnet) et n'écrit jamais rien dans carnet. La liste est gardée en mémoire
10 minutes (et la dernière bonne dans la base, pour survivre à une panne de carnet).

Usages :
- un invité annoncé par Home Assistant sans fiche : si carnet connaît un seul contact à ce nom avec une date
  complète, la fiche est créée et le livret préparé (relecture et approbation restent à faire) ;
- la saisie d'une fiche propose les contacts de carnet ;
- une fiche dont la date diffère de celle de carnet arrive dans À traiter.
"""
from __future__ import annotations

import json
import time
from datetime import date
from typing import Callable

import httpx

from .base import Base, cle_nom, maintenant

DUREE = 600          # secondes : fraîcheur de la liste en mémoire
DELAI = 8            # secondes : délai d'une lecture


def _lire_http(url: str, jeton: str) -> list[dict]:
    r = httpx.get(f"{url}/gazette/personnes", headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par carnet (GAZETTE_CARNET_JETON ≠ CARNET_JETON_GAZETTE)")
    r.raise_for_status()
    return list(r.json().get("personnes") or [])


class Carnet:
    def __init__(self, url: str, jeton: str, base: Base, lire: Callable[[str, str], list[dict]] | None = None):
        self.url, self.jeton, self.base = url.rstrip("/"), jeton, base
        self._lire = lire or _lire_http
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

    def etat(self) -> dict:
        liste = self._liste if self._liste is not None else None
        return {"regle": self.actif, "erreur": self.erreur, "lu_le": self.base.reglage("carnet_lu_le"),
                "personnes": len(liste) if liste is not None else None,
                "dates": sum(1 for p in liste if p.get("naissance")) if liste is not None else None}
