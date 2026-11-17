"""0.9 : lecture d'Immich pour La Récidive (journal à scandale) — photos d'une personne entre deux dates,
photos de la personne taguées « scandale », aperçu d'une photo.

Gazette n'écrit jamais dans Immich : recherche (POST /api/search/metadata, lecture seule), liste des tags,
miniature « preview » d'une photo (jamais l'original : plus léger et assez net pour un A5). Les aperçus sont
gardés dans /data/photos (une photo imprimée ne change pas).

Clé d'API dédiée : GAZETTE_IMMICH_CLE (permissions asset.read, asset.view, tag.read). Vide : La Récidive le
signale dans À traiter et le séjour garde la Gazette."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import httpx

DELAI = 20            # secondes : une recherche sur une grande photothèque
PAR_PAGE = 250
PAGES_MAX = 8         # 2 000 photos au plus par recherche : bien assez pour en garder sept
TAG = "scandale"

Lire = Callable[[str, str, dict | None], object]


def _lire_http(url: str, cle: str) -> Lire:
    def lire(methode: str, chemin: str, corps: dict | None = None):
        r = httpx.request(methode, f"{url}/api{chemin}", json=corps, timeout=DELAI,
                          headers={"x-api-key": cle, "Accept": "application/json" if "thumbnail" not in chemin else "*/*"})
        if r.status_code in (401, 403):
            raise RuntimeError("clé refusée par Immich (GAZETTE_IMMICH_CLE : permissions asset.read, asset.view, tag.read)")
        r.raise_for_status()
        return r.content if "thumbnail" in chemin else r.json()
    return lire


def _date(a: dict) -> str:
    return str(a.get("localDateTime") or a.get("fileCreatedAt") or "")[:10]


class Immich:
    def __init__(self, url: str, cle: str, dossier: Path, lire: Lire | None = None):
        self.url, self.cle = url.rstrip("/"), cle
        self.dossier = dossier
        self._lire = lire or (_lire_http(self.url, cle) if self.url and cle else None)
        self.erreur = ""

    @property
    def actif(self) -> bool:
        return self._lire is not None

    def _appel(self, methode: str, chemin: str, corps: dict | None = None):
        if not self.actif:
            raise RuntimeError("Immich n'est pas réglé (GAZETTE_IMMICH_CLE vide)")
        try:
            r = self._lire(methode, chemin, corps)
            self.erreur = ""
            return r
        except Exception as ex:  # noqa: BLE001 — l'erreur est gardée pour l'écran Connexion
            self.erreur = str(ex).splitlines()[0][:160] or ex.__class__.__name__
            raise

    def _chercher(self, filtre: dict) -> list[dict]:
        """Toutes les photos (pas les vidéos) qui répondent au filtre, page après page."""
        res, page = [], 1
        for _ in range(PAGES_MAX):
            r = self._appel("POST", "/search/metadata", {**filtre, "type": "IMAGE", "size": PAR_PAGE, "page": page,
                                                         "withDeleted": False, "isVisible": True})
            bloc = (r or {}).get("assets") or {}
            for a in bloc.get("items") or []:
                if a.get("id") and not a.get("isTrashed"):
                    res.append({"id": a["id"], "date": _date(a)})
            suivante = bloc.get("nextPage")
            if not suivante:
                break
            page = int(suivante)
        return res

    def photos(self, personne: str, du: str, au: str) -> list[dict]:
        """Photos où la personne est reconnue, prises de `du` (inclus) à `au` (exclu), plus anciennes d'abord."""
        res = self._chercher({"personIds": [personne], "takenAfter": f"{du}T00:00:00.000Z",
                              "takenBefore": f"{au}T00:00:00.000Z"})
        return sorted({p["id"]: p for p in res if du <= p["date"] < au}.values(), key=lambda p: (p["date"], p["id"]))

    def tag_scandale(self) -> str | None:
        """L'identifiant du tag « scandale » (casse et accents ignorés ; tag imbriqué « …/scandale » accepté)."""
        for t in self._appel("GET", "/tags") or []:
            nom = str(t.get("value") or t.get("name") or "")
            if re.sub(r"\s+", " ", nom.split("/")[-1]).strip().casefold() == TAG:
                return t.get("id")
        return None

    def scandales(self, personne: str) -> list[dict] | None:
        """Photos de la personne taguées « scandale ». None : le tag n'existe pas dans Immich."""
        tid = self.tag_scandale()
        if not tid:
            return None
        res = self._chercher({"personIds": [personne], "tagIds": [tid]})
        return sorted({p["id"]: p for p in res}.values(), key=lambda p: (p["date"], p["id"]))

    def apercu(self, asset: str) -> bytes | None:
        """L'aperçu d'une photo, gardé dans /data/photos ; None si Immich ne le donne pas."""
        if not re.fullmatch(r"[0-9a-fA-F-]{8,64}", asset or ""):
            return None
        f = self.dossier / f"{asset}.jpg"
        if f.is_file():
            return f.read_bytes()
        try:
            octets = self._appel("GET", f"/assets/{asset}/thumbnail?size=preview")
        except Exception:  # noqa: BLE001 — photo absente : case vide, jamais une erreur de page
            return None
        if not isinstance(octets, (bytes, bytearray)) or not octets:
            return None
        self.dossier.mkdir(parents=True, exist_ok=True)
        f.write_bytes(bytes(octets))
        return bytes(octets)

    def gardee(self, asset: str) -> bytes | None:
        """L'aperçu déjà gardé (sans appeler Immich) : pour la mise en page."""
        f = self.dossier / f"{asset}.jpg"
        return f.read_bytes() if re.fullmatch(r"[0-9a-fA-F-]{8,64}", asset or "") and f.is_file() else None

    def sonder(self) -> dict:
        if not self.actif:
            return {"ok": None, "detail": "pas réglé (GAZETTE_IMMICH_CLE vide)"}
        try:
            tid = self.tag_scandale()
        except Exception:  # noqa: BLE001
            return {"ok": False, "detail": self.erreur}
        return {"ok": True, "detail": "tag « scandale » trouvé" if tid else "joignable, mais aucun tag « scandale » dans Immich"}

    def etat(self) -> dict:
        return {"regle": self.actif, "erreur": self.erreur}
