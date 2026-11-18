"""0.23 : carnet 2.33 simulé pour la fiche complète (routes /gazette/personnes/{personne_id}/fiche[...]), aux formats
exacts de carnet (app/journaux.py de carnet 2.33.0) : pépites {id, rubrique, texte, interdit, source, parue_le, le, par},
GET {personne_id, rubriques, pepites, jauge, connu, suggestions}, POST → la pépite (ou {**même, deja: true}), PUT → la
pépite, DELETE → {ok, id}, parues → {ok, marquees, ignorees}, 404 personne ou pépite inconnue, 409 pépite changée.

Sert aux tests et au serveur de démonstration. Personnes et détails inventés."""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

RUBRIQUES = json.loads((Path(__file__).resolve().parents[1] / "app" / "rubriques_journaux.json").read_text(encoding="utf-8"))
CLES = {r["cle"] for f in RUBRIQUES["familles"] for r in f["rubriques"]} | {"interdits"}


class CarnetFiche:
    """Appelable comme `carnet._fiche_http` : (url, jeton, méthode, chemin, corps) → (statut, réponse JSON)."""

    def __init__(self, personnes: dict[str, dict] | None = None, version_ancienne: bool = False):
        # personne_id → {"pepites": [...], "connu": {...}, "suggestions": [...]}
        self.personnes = personnes or {}
        self.arrete = False                  # vrai : carnet injoignable (exception réseau)
        self.ancien = version_ancienne       # vrai : carnet d'avant 2.33 (route absente)
        self.appels: list[tuple[str, str, dict | None]] = []
        self._n = itertools.count(1)
        self._t = itertools.count(1)

    def _le(self) -> str:
        return f"2026-11-18T10:00:00.{next(self._t):06d}"

    def pepite(self, personne: str, rubrique: str, texte: str, source: str = "julien", parue_le: str | None = None) -> dict:
        """Ajoute directement une pépite (préparation d'un test)."""
        p = {"id": f"pp-{next(self._n):06x}", "rubrique": rubrique, "texte": texte, "interdit": rubrique == "interdits",
             "source": source, "parue_le": parue_le, "le": self._le(), "par": "carnet"}
        self.personnes.setdefault(personne, {"pepites": [], "connu": {}, "suggestions": []})["pepites"].append(p)
        return p

    def __call__(self, url: str, jeton: str, methode: str, chemin: str, corps: dict | None):
        self.appels.append((methode, chemin, corps))
        if self.arrete:
            raise ConnectionError("connexion refusée")
        if self.ancien:
            return 404, {"detail": "Not Found"}
        m = re.fullmatch(r"/gazette/personnes/([^/]+)/fiche(?:/(pepites|parues)(?:/([^/]+))?)?", chemin)
        if not m:
            return 404, {"detail": "Not Found"}
        ident, quoi, pid = m.groups()
        fiche = self.personnes.get(ident)
        if fiche is None:
            return 404, {"detail": "Personne inconnue de carnet."}
        liste = fiche["pepites"]
        if methode == "GET" and not quoi:
            n = sum(1 for p in liste if not p["interdit"])
            palier = "inépuisable" if n >= 30 else "bien fournie" if n >= 15 else "de quoi rire" if n >= 5 else ""
            return 200, {"personne_id": ident, "rubriques": RUBRIQUES, "pepites": [dict(p) for p in liste],
                         "jauge": {"nombre": n, "palier": palier, "prochain": next((s for s in (5, 15, 30) if n < s), None)},
                         "connu": dict(fiche.get("connu") or {}), "suggestions": list(fiche.get("suggestions") or [])}
        if quoi == "parues" and methode == "POST":
            ids, date = (corps or {}).get("ids"), (corps or {}).get("date")
            if not isinstance(ids, list) or not date:
                return 400, {"detail": "`ids` et `date` attendus."}
            marquees = 0
            for p in liste:
                if p["id"] in ids:
                    p["parue_le"] = date
                    marquees += 1
            return 200, {"ok": True, "marquees": marquees, "ignorees": len(set(ids)) - marquees}
        if quoi == "pepites" and methode == "POST" and not pid:
            texte = " ".join(str((corps or {}).get("texte") or "").split())
            if not texte or len(texte) > 200:
                return 400, {"detail": "Pépite vide ou trop longue."}
            rub = "interdits" if (corps or {}).get("interdit") is True else (corps or {}).get("rubrique") or "autre"
            if rub not in CLES:
                return 400, {"detail": "Rubrique inconnue."}
            meme = next((p for p in liste if p["rubrique"] == rub and p["texte"].casefold() == texte.casefold()), None)
            if meme:
                return 200, {**meme, "deja": True}
            p = self.pepite(ident, rub, texte, (corps or {}).get("source") or "julien")
            p["par"] = "gazette"
            return 200, dict(p)
        if quoi == "pepites" and pid and methode in ("PUT", "DELETE"):
            p = next((x for x in liste if x["id"] == pid), None)
            if p is None:
                return 404, {"detail": "Pépite introuvable (effacée entre-temps ?) : relis la fiche."}
            if (corps or {}).get("le") != p["le"]:
                return 409, {"detail": "Cette pépite a changé entre-temps (depuis l'autre appli) : relis la fiche."}
            if methode == "DELETE":
                liste.remove(p)
                return 200, {"ok": True, "id": pid}
            if "texte" in corps:
                p["texte"] = " ".join(str(corps["texte"]).split())
            if corps.get("interdit") is True:
                p["rubrique"] = "interdits"
            elif "rubrique" in corps:
                p["rubrique"] = corps["rubrique"]
            p["interdit"] = p["rubrique"] == "interdits"
            p["le"], p["par"] = self._le(), "gazette"
            return 200, dict(p)
        return 405, {"detail": "Method Not Allowed"}
