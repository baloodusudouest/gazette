"""0.9 : lecture d'Immich pour La Récidive (journal à scandale) — photos d'une personne entre deux dates,
photos de la personne taguées « scandale », aperçu d'une photo.

Gazette n'écrit jamais dans Immich : recherche (POST /api/search/metadata, lecture seule), liste des tags,
miniature « preview » d'une photo (jamais l'original : plus léger et assez net pour un A5). Les aperçus sont
gardés dans /data/photos (une photo imprimée ne change pas).

Clé d'API dédiée : GAZETTE_IMMICH_CLE (permissions asset.read, asset.view, tag.read ; 0.12 : album.read et
person.read en plus pour le contexte des photos). Vide : La Récidive le signale dans À traiter et le séjour garde
la Gazette.

0.12 : contexte d'une photo pour l'IA — les albums où elle se trouve (sauf les noms génériques : une année,
« divers », « pense-bête »…) et les personnes reconnues sur la photo et dans ces albums. Lecture seule ; sans
album.read ou person.read, le contexte est simplement vide (jamais une erreur de page)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import httpx

DELAI = 20            # secondes : une recherche sur une grande photothèque
PAR_PAGE = 250
PAGES_MAX = 8         # 2 000 photos au plus par recherche : bien assez pour en garder sept
TAG = "scandale"
ECHANTILLON = 12      # 0.12 : photos lues par album pour savoir qui s'y trouve
PERSONNES_MAXI = 8

# 0.12 : albums qui ne disent rien de la photo (on retire d'abord années, mois et chiffres du nom)
GENERIQUES = {"", "divers", "diverses", "pense bete", "pense betes", "photos", "photo", "images", "pellicule", "a trier",
              "trier", "tri", "vrac", "en vrac", "autres", "autre", "misc", "favoris", "favorites", "selection", "best of",
              "captures", "captures d ecran", "capture d ecran", "screenshots", "screenshot", "telechargements", "downloads",
              "whatsapp", "whatsapp images", "camera", "camera roll", "dcim", "recents", "import", "imports", "a imprimer",
              "imprimer", "partage", "partages", "scans", "scan", "numerisation", "fonds d ecran", "wallpaper", "test",
              "annee", "annees", "album", "nouvel album", "sans titre", "untitled"}
MOIS = r"janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"

Lire = Callable[[str, str, dict | None], object]


def _lire_http(url: str, cle: str) -> Lire:
    def lire(methode: str, chemin: str, corps: dict | None = None):
        r = httpx.request(methode, f"{url}/api{chemin}", json=corps, timeout=DELAI,
                          headers={"x-api-key": cle, "Accept": "application/json" if "thumbnail" not in chemin else "*/*"})
        if r.status_code in (401, 403):
            raise RuntimeError("clé refusée par Immich (GAZETTE_IMMICH_CLE : permissions asset.read, asset.view, tag.read, "
                               "album.read, person.read)")
        r.raise_for_status()
        return r.content if "thumbnail" in chemin else r.json()
    return lire


def _plat(texte: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def album_generique(nom: str) -> bool:
    """0.12 : « 2019 », « Photos 2019 », « Divers », « Pense-bête », « Août 2021 » → générique (rien à en tirer) ;
    « Noël 2019 », « Mariage de Léa » → parlant."""
    t = re.sub(rf"\b({MOIS})\b", " ", _plat(nom))
    t = " ".join(re.sub(r"\d+", " ", t).split())
    t = re.sub(r"^(de|du|des|en|l|le|la|les)\s+|\s+(de|du|des|en)$", "", t).strip()
    return t in GENERIQUES or len(t) < 3


def _prenom_immich(nom: str) -> str:
    return (nom or "").strip().split(" ")[0] if (nom or "").strip() else ""


def _date(a: dict) -> str:
    return str(a.get("localDateTime") or a.get("fileCreatedAt") or "")[:10]


class Immich:
    def __init__(self, url: str, cle: str, dossier: Path, lire: Lire | None = None):
        self.url, self.cle = url.rstrip("/"), cle
        self.dossier = dossier
        self._lire = lire or (_lire_http(self.url, cle) if self.url and cle else None)
        self.erreur = ""
        self._gens_album: dict[str, list[str]] = {}   # 0.12 : qui est dans un album (lu une fois par démarrage)

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

    def _gens(self, asset: str, sauf: str) -> list[str]:
        a = self._appel("GET", f"/assets/{asset}") or {}
        return [_prenom_immich(x.get("name", "")) for x in a.get("people") or []
                if x.get("name") and x.get("id") != sauf and not x.get("isHidden")]

    def contexte(self, asset: str, sauf: str = "") -> dict:
        """0.12 : {albums, personnes} d'une photo pour l'IA. `sauf` : l'invité (déjà nommé). Albums génériques
        écartés ; personnes de la photo d'abord, puis celles des albums parlants. Erreur : contexte vide."""
        vide = {"albums": [], "personnes": []}
        if not self.actif or not re.fullmatch(r"[0-9a-fA-F-]{8,64}", asset or ""):
            return vide
        personnes: list[str] = []
        try:
            personnes += self._gens(asset, sauf)
        except Exception:  # noqa: BLE001 — person.read absent : on continue sans
            pass
        albums: list[str] = []
        try:
            for al in self._appel("GET", f"/albums?assetId={asset}") or []:
                nom = " ".join(str(al.get("albumName") or "").split())
                if not nom or album_generique(nom):
                    continue
                albums.append(nom[:60])
                aid = str(al.get("id") or "")
                if aid and aid not in self._gens_album:
                    gens: list[str] = []
                    try:
                        r = self._appel("POST", "/search/metadata", {"albumIds": [aid], "type": "IMAGE", "size": ECHANTILLON,
                                                                      "page": 1, "withDeleted": False})
                        for a in ((r or {}).get("assets") or {}).get("items") or []:
                            gens += self._gens(a["id"], sauf)
                    except Exception:  # noqa: BLE001
                        pass
                    self._gens_album[aid] = gens
                personnes += [g for g in self._gens_album.get(aid, []) if g]
        except Exception:  # noqa: BLE001 — album.read absent : pas d'albums
            pass
        uniques: list[str] = []
        for x in personnes:
            if x and x.casefold() not in {u.casefold() for u in uniques}:
                uniques.append(x)
        return {"albums": list(dict.fromkeys(albums))[:4], "personnes": uniques[:PERSONNES_MAXI]}

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
