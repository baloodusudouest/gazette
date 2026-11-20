"""0.28 : Douze points simulé à partir des deux fichiers du contrat (`docs/journal-exemple.json`, finale, et
`docs/journal-exemple-demi.json`, demi-finale), recopiés de Douze points 1.9.0. Personnes inventées, aucun réseau."""
from __future__ import annotations

import base64
import copy
import json
import re
from pathlib import Path

from app.douze_points import Introuvable

DOCS = Path(__file__).resolve().parents[1] / "docs"
JETON = "jeton-commun-de-test"
# Une image PNG de 1 × 1 point (images figées de l'évènement) et un petit JPEG gris (aperçus d'Immich)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
GRIS = base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx"
                        "NDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAI"
                        "AQEAAD8AKp//2Q==")


def exemple(demi: bool = False) -> dict:
    return json.loads((DOCS / ("journal-exemple-demi.json" if demi else "journal-exemple.json")).read_text(encoding="utf-8"))


def habiller(j: dict, soiree_id: int, version: int = 1, images=("logo", "banniere", "poster", "apero"),
             photos: bool = True) -> dict:
    """Le journal d'exemple pour une soirée et une version : images figées, photos des duos dans Immich, identifiants de carnet."""
    j = copy.deepcopy(j)
    j["version"] = version
    j["soiree"]["id"] = soiree_id
    j["images"] = {s: (f"/externe/soirees/{soiree_id}/journal/{version}/image/{s}" if s in images else None)
                   for s in ("logo", "banniere", "poster", "apero")}
    if photos:
        for k, d in enumerate(j["duos"]):
            d["photos"] = [{"photo": 10 + k, "immich_id": f"40000000-000{k}"}] if k < 2 else []
    for i in j["invites"]:
        if i["id"] == 1:
            i["personne_id"] = "p-0123456789"          # identifiant maison donné par Douze points
        elif i["id"] == 3:
            i["carnet_id"] = "C-9"                     # seulement l'identifiant de carnet : retrouvé par carnet
    return j


class DouzeSimule:
    """`journaux` : {id de soirée : [journal version 1, version 2, …]}. Appelable comme `douze_points._lire_http`."""

    def __init__(self, journaux: dict[int, list[dict]], jeton: str = JETON):
        self.journaux, self.jeton = journaux, jeton
        self.appels: list[str] = []

    def __call__(self, url: str, jeton: str, chemin: str):
        self.appels.append(chemin)
        if jeton != self.jeton:
            raise Introuvable("404")
        if chemin == "/externe/soirees":
            return [{"id": sid, "nom": v[-1]["soiree"]["nom"], "emission": v[-1]["soiree"]["emission"],
                     "annee": v[-1]["soiree"]["annee"], "version": len(v), "le": v[-1]["le"]} for sid, v in self.journaux.items()]
        m = re.fullmatch(r"/externe/soirees/(\d+)/journal(?:/(\d+))?(?:/image/(\w+))?", chemin)
        if not m or int(m[1]) not in self.journaux:
            raise Introuvable("404")
        versions = self.journaux[int(m[1])]
        v = int(m[2]) if m[2] else len(versions)
        if not 1 <= v <= len(versions):
            raise Introuvable("404")
        if m[3]:
            if not versions[v - 1]["images"].get(m[3]):
                raise Introuvable("404")
            return PNG
        return copy.deepcopy(versions[v - 1])


def immich_simule(methode: str, chemin: str, corps: dict | None = None):
    if "/thumbnail" in chemin:
        return GRIS
    raise AssertionError(chemin)
