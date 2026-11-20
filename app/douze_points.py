"""0.28 : lecture de Douze points (soirées Eurovision clôturées) pour « Good Evening Europe! », le magazine de la soirée.

Douze points ≥ 1.9 fige à chaque clôture un journal versionné (contrat `docs/journal-exemple.json`, champ `format` = 1),
lu sur son adresse commune `/externe/…` avec le jeton commun de la maison (`Authorization: Bearer <MAISON_JETON>` ;
sans jeton, Douze points répond 404) :
- `GET /externe/soirees` → [{id, nom, emission, annee, version, le}] (dernière version de chaque soirée clôturée) ;
- `GET /externe/soirees/<id>/journal[/<version>]` → le journal (faits et calculs, tous faits dans Douze points) ;
- `GET /externe/soirees/<id>/journal/<version>/image/<sorte>` → les images figées à la clôture (logo, bannière, poster, apéro).
Adresse : GAZETTE_DOUZE_POINTS_URL (défaut http://douze-points:8088, interne à la stack). Gazette n'écrit jamais rien dans
Douze points. Lecture injectable dans les tests (`ETAT["douze_lire"]`) : aucun test ne sort sur le réseau."""
from __future__ import annotations

import re
from typing import Callable

import httpx

DELAI = 10
FORMAT = 1                        # contrat du journal accepté
IMAGES = ("logo", "banniere", "poster", "apero")

# lire(url, jeton, chemin) → dict | list (JSON) ou bytes (image) ; RuntimeError si Douze points répond mal
Lire = Callable[[str, str, str], object]


class Introuvable(RuntimeError):
    """Douze points répond 404 : soirée ou image absente, ou jeton refusé (porte fermée)."""


def _lire_http(url: str, jeton: str, chemin: str):
    r = httpx.get(f"{url}{chemin}", headers={"Authorization": f"Bearer {jeton}"}, timeout=DELAI)
    if r.status_code == 404:
        raise Introuvable("Douze points répond 404 (jeton MAISON_JETON différent, Douze points d'avant 1.9, ou rien à cette adresse)")
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    return r.content


def type_image(octets: bytes) -> str:
    """Le type d'une image d'après ses premiers octets (Douze points accepte PNG, JPEG et WebP) ; vide : inconnu."""
    if octets[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if octets[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if octets[:4] == b"RIFF" and octets[8:12] == b"WEBP":
        return "image/webp"
    return ""


class DouzePoints:
    def __init__(self, adresse: Callable[[], str], jeton: str, lire: Lire | None = None):
        self._adresse, self.jeton = adresse, jeton
        self._lire = lire or _lire_http
        self.erreur = ""
        self.lu_le = ""
        self.soirees_lues: int | None = None

    @property
    def url(self) -> str:
        return (self._adresse() or "").strip().rstrip("/")

    @property
    def actif(self) -> bool:
        return bool(self.url and self.jeton)

    def _appel(self, chemin: str):
        try:
            return self._lire(self.url, self.jeton, chemin)
        except Introuvable:
            raise
        except Exception as ex:  # noqa: BLE001 — Douze points arrêté, réseau
            message = str(ex).splitlines()[0][:160] if str(ex) else type(ex).__name__
            raise RuntimeError(f"Douze points injoignable ({message})") from ex

    def soirees(self) -> list[dict]:
        """Les soirées clôturées (dernière version de chacune). Vide si Douze points n'est pas réglé."""
        if not self.actif:
            return []
        from .base import maintenant
        try:
            d = self._appel("/externe/soirees")
        except RuntimeError as ex:
            self.erreur = str(ex)[:200]
            raise
        if not isinstance(d, list):
            self.erreur = "réponse de Douze points inattendue (liste des soirées attendue)"
            raise RuntimeError(self.erreur)
        res = []
        for s in d:
            try:
                res.append({"id": int(s["id"]), "nom": " ".join(str(s.get("nom") or "").split())[:120],
                            "emission": str(s.get("emission") or ""), "annee": s.get("annee"),
                            "version": int(s["version"]), "le": str(s.get("le") or "")})
            except (KeyError, TypeError, ValueError):
                continue
        self.erreur, self.lu_le, self.soirees_lues = "", maintenant(), len(res)
        return res

    def journal(self, soiree_id: int, version: int | None = None) -> dict:
        """Le journal d'une soirée (une version précise, ou la dernière). RuntimeError si le contrat n'est pas le bon."""
        chemin = f"/externe/soirees/{int(soiree_id)}/journal" + (f"/{int(version)}" if version else "")
        d = self._appel(chemin)
        if not isinstance(d, dict) or d.get("format") != FORMAT or not isinstance(d.get("soiree"), dict):
            raise RuntimeError(f"journal de Douze points inattendu (format {FORMAT} attendu)")
        return d

    def image(self, chemin: str) -> bytes | None:
        """Une image figée du journal (chemin `images.*`, relatif à l'adresse de Douze points) ; None si absente."""
        if not chemin or not re.fullmatch(r"/externe/soirees/\d+/journal/\d+/image/[a-z]+", chemin):
            return None
        try:
            d = self._appel(chemin)
        except (Introuvable, RuntimeError):
            return None
        return bytes(d) if isinstance(d, (bytes, bytearray)) and type_image(bytes(d)) else None

    def sonder(self) -> dict:
        """Connexion › Vérifier : lit la liste des soirées."""
        if not self.actif:
            return {"ok": None, "detail": "pas réglé (GAZETTE_DOUZE_POINTS_URL ou MAISON_JETON vide)"}
        try:
            n = len(self.soirees())
        except RuntimeError as ex:
            return {"ok": False, "detail": str(ex)[:200]}
        return {"ok": True, "detail": f"{n} soirée{'s' if n > 1 else ''} clôturée{'s' if n > 1 else ''} lue{'s' if n > 1 else ''}"}

    def etat(self) -> dict:
        return {"regle": self.actif, "url": self.url, "erreur": self.erreur, "lu_le": self.lu_le, "soirees": self.soirees_lues}
