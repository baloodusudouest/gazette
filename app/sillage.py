"""0.23 : lecture de Sillage (chemin de vie d'une personne d'après Immich) pour la fiche complète.
0.31 : et les nouveautés de son sillage depuis le séjour précédent, pour La Récidive
(`GET /externe/nouveautes?personne=…&depuis=AAAA-MM-JJ`, Sillage ≥ 0.26, contrat 1).

Gazette lit `GET /externe/personnes/{immich_id}/etapes` (Sillage ≥ 0.20, jeton commun MAISON_JETON) →
`{"contrat": 1, "etapes": [{"nom", "annee", "photos"}]}` : les noms d'étapes et leurs années deviennent des suggestions
grisées « Ajouter » de la fiche, une par une, jamais recopiées sans un geste de Julien. Adresse : réglage de Gazette
« sillage_url » (défaut http://sillage:8093 ; vide : pas de Sillage). Gazette n'écrit jamais rien dans Sillage."""
from __future__ import annotations

import time
from typing import Callable

import httpx

DELAI = 8
DUREE = 600                       # secondes : étapes gardées en mémoire 10 minutes
CONTRAT = 1

Lire = Callable[[str, str, str], dict]


def _lire_http(url: str, jeton: str, immich_id: str) -> dict:
    r = httpx.get(f"{url}/externe/personnes/{immich_id}/etapes", headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par Sillage (MAISON_JETON différent de celui de Sillage)")
    if r.status_code in (404, 405):
        raise RuntimeError("Sillage ne connaît pas cette adresse (Sillage 0.20 nécessaire)")
    r.raise_for_status()
    return r.json()


def _lire_nouveautes_http(url: str, jeton: str, immich_id: str, depuis: str) -> dict:
    r = httpx.get(f"{url}/externe/nouveautes", params={"personne": immich_id, "depuis": depuis},
                  headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 401:
        raise RuntimeError("jeton refusé par Sillage (MAISON_JETON différent de celui de Sillage)")
    if r.status_code in (404, 405):
        raise RuntimeError("Sillage ne connaît pas cette adresse (Sillage 0.26 nécessaire)")
    r.raise_for_status()
    return r.json()


SOUVENIRS_MAX = 4                 # lignes de « Du nouveau dans les souvenirs » (page 3 de La Récidive)


class Sillage:
    def __init__(self, adresse: Callable[[], str], jeton: str, lire: Lire | None = None,
                 lire_nouveautes: Callable[[str, str, str, str], dict] | None = None):
        self._adresse, self.jeton = adresse, jeton
        self._lire = lire or _lire_http
        self._lire_nouveautes = lire_nouveautes
        self._memo: dict[tuple[str, str], tuple[float, list[dict]]] = {}
        self.erreur = ""

    @property
    def url(self) -> str:
        return (self._adresse() or "").strip().rstrip("/")

    @property
    def actif(self) -> bool:
        return bool(self.url and self.jeton)

    def etapes(self, immich_id: str) -> list[dict]:
        """Les étapes du chemin de cette personne (vide si Sillage n'est pas réglé ou la personne inconnue).
        RuntimeError si Sillage est injoignable ou répond mal."""
        if not self.actif or not immich_id:
            return []
        cle = (self.url, immich_id)
        vu = self._memo.get(cle)
        if vu and time.monotonic() - vu[0] < DUREE:
            return vu[1]
        try:
            d = self._lire(self.url, self.jeton, immich_id)
        except Exception as ex:  # noqa: BLE001 — Sillage arrêté, réseau, jeton
            self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
            raise RuntimeError(f"Sillage injoignable ({self.erreur})") from ex
        if not isinstance(d, dict) or d.get("contrat") != CONTRAT:
            self.erreur = "réponse de Sillage inattendue (contrat 1 attendu)"
            raise RuntimeError(self.erreur)
        res = []
        for e in d.get("etapes") or []:
            if not isinstance(e, dict) or not str(e.get("nom") or "").strip():
                continue
            try:
                annee = int(e["annee"]) if e.get("annee") not in (None, "") else None
            except (TypeError, ValueError):
                annee = None
            try:
                photos = int(e.get("photos") or 0)
            except (TypeError, ValueError):
                photos = 0
            res.append({"nom": " ".join(str(e["nom"]).split())[:120], "annee": annee, "photos": photos})
        self.erreur = ""
        self._memo[cle] = (time.monotonic(), res[:60])
        return res[:60]

    def nouveautes(self, immich_id: str, depuis: str) -> dict:
        """0.31 : ce qui est arrivé dans le sillage de cette personne depuis `depuis` (jour) :
        {"lignes": [{nom, annee, photos, nouvelle, retrouvee}] (4 au plus), "autres_photos": n}. Vide si Sillage n'est pas
        réglé ou la personne inconnue ; RuntimeError si Sillage est injoignable ou répond mal."""
        vide = {"lignes": [], "autres_photos": 0}
        if not self.actif or not immich_id or not depuis:
            return vide
        try:
            d = (self._lire_nouveautes or _lire_nouveautes_http)(self.url, self.jeton, immich_id, depuis[:10])
        except Exception as ex:  # noqa: BLE001
            self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
            raise RuntimeError(f"Sillage injoignable ({self.erreur})") from ex
        if not isinstance(d, dict) or d.get("contrat") != CONTRAT:
            self.erreur = "réponse de Sillage inattendue (contrat 1 attendu)"
            raise RuntimeError(self.erreur)
        lignes = []
        for e in d.get("etapes") or []:
            if not isinstance(e, dict):
                continue
            try:
                annee, photos = int(e.get("annee")), int(e.get("photos") or 0)
            except (TypeError, ValueError):
                continue
            if photos <= 0:
                continue
            lignes.append({"nom": " ".join(str(e.get("nom") or "").split())[:80], "annee": annee, "photos": photos,
                           "nouvelle": bool(e.get("nouvelle")), "retrouvee": bool(e.get("retrouvee"))})
        try:
            autres = int(d.get("autres_photos") or 0)
        except (TypeError, ValueError):
            autres = 0
        autres += sum(x["photos"] for x in lignes[SOUVENIRS_MAX:])
        self.erreur = ""
        return {"lignes": lignes[:SOUVENIRS_MAX], "autres_photos": autres}
