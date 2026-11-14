"""Les sources libres, lues une fois puis gardées dans la base (le passé ne change pas).

- Wikipédia FR et EN : wikitext brut (index.php?action=raw), User-Agent descriptif, une pause entre deux pages,
  nouvel essai après « trop de requêtes » (429).
- Wikidata (SPARQL) : notoriété d'une page (nombre de liens interlangues) et nature « être humain » (P31 = Q5),
  par lots de 120 titres.
- Larousse, Journaux de l'année (1966 à ~2003) : une page par mois. Textes non libres : usage familial privé,
  rien n'en sort du NAS, mention « d'après Larousse » dans le livret.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse

import httpx

from .base import Base

UA = "Gazette/0.1 (https://github.com/baloodusudouest/gazette; contact via GitHub)"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
LAROUSSE_DEBUT, LAROUSSE_FIN = (1966, 7), (2003, 12)


class SourceIndisponible(Exception):
    pass


class Sources:
    def __init__(self, base: Base, actives: bool = True, larousse: bool = True, pause: float = 1.2):
        self.base = base
        self.actives = actives
        self.larousse_actif = larousse
        self.pause = pause
        self._client: httpx.Client | None = None
        self.erreurs: dict[str, str] = {}

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(headers={"User-Agent": UA}, timeout=40, follow_redirects=False)
        return self._client

    def fermer(self) -> None:
        if self._client:
            self._client.close()

    def _get(self, nom: str, url: str, **kw) -> httpx.Response:
        if not self.actives:
            raise SourceIndisponible(f"{nom} : lecture des sources coupée.")
        derniere = None
        for essai in range(4):
            try:
                r = self.client.get(url, **kw)
            except httpx.HTTPError as ex:
                derniere = str(ex)
                time.sleep(3 * (essai + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                derniere = f"réponse {r.status_code}"
                time.sleep(10 * (essai + 1))
                continue
            time.sleep(self.pause)
            self.erreurs.pop(nom, None)
            return r
        self.erreurs[nom] = derniere or "injoignable"
        raise SourceIndisponible(f"{nom} : {derniere}")

    # ------------------------------------------------------------ Wikipédia
    def wikipedia(self, titre: str, langue: str = "fr") -> str:
        """Le wikitext d'une page ; '' si elle n'existe pas. Gardé pour toujours."""
        cle = f"wp:{langue}:{titre}"
        deja = self.base.source(cle)
        if deja is not None:
            return deja
        url = (f"https://{langue}.wikipedia.org/w/index.php?title="
               + urllib.parse.quote(titre.replace(" ", "_")) + "&action=raw")
        r = self._get(f"wikipedia-{langue}", url)
        if r.status_code == 404:
            contenu = ""
        elif r.status_code == 200:
            contenu = r.text
            # Redirection interne (#REDIRECTION [[…]]) : on suit une fois
            if contenu.lstrip().upper().startswith(("#REDIRECT", "#REDIRECTION")):
                m = re.search(r"\[\[([^\]|#]+)", contenu)
                if m:
                    contenu = self.wikipedia(m.group(1).strip(), langue)
        else:
            raise SourceIndisponible(f"wikipedia-{langue} : réponse {r.status_code}")
        self.base.garder_source(cle, contenu)
        return contenu

    @staticmethod
    def titre_mois(d_annee: int, d_mois: int) -> str:
        return f"{MOIS[d_mois - 1].capitalize()} {d_annee}"

    @staticmethod
    def titre_jour(jour: int, mois: int) -> str:
        return f"{'1er' if jour == 1 else jour} {MOIS[mois - 1]}"

    @staticmethod
    def titre_mois_en(annee: int, mois: int) -> str:
        return f"{MONTHS[mois - 1]} {annee}"

    # ------------------------------------------------------------ Wikidata
    def wikidata(self, titres: list[str]) -> dict[str, dict]:
        """titre frwiki → {n: liens interlangues, humain: bool}. Titres inconnus : absents du résultat."""
        titres = sorted({t for t in titres if t})
        sortie, manquants = {}, []
        for t in titres:
            deja = self.base.source(f"wd:fr:{t}")
            if deja is not None:
                v = json.loads(deja)
                if v:
                    sortie[t] = v
            else:
                manquants.append(t)
        for k in range(0, len(manquants), 120):
            lot = manquants[k:k + 120]
            vals = " ".join('"' + t.replace("\\", "").replace('"', '\\"') + '"@fr' for t in lot)
            q = ("SELECT ?t ?n ?h WHERE { VALUES ?t {" + vals + "} ?a schema:name ?t; schema:isPartOf "
                 "<https://fr.wikipedia.org/>; schema:about ?i. ?i wikibase:sitelinks ?n. "
                 "BIND(EXISTS { ?i wdt:P31 wd:Q5 } AS ?h) }")
            if not self.actives:
                break                      # lecture coupée : ce qui est déjà gardé suffit
            try:
                r = self.client.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"},
                                     headers={"Accept": "application/sparql-results+json"})
            except httpx.HTTPError as ex:
                self.erreurs["wikidata"] = str(ex)
                raise SourceIndisponible(f"wikidata : {ex}") from ex
            if r.status_code != 200:
                self.erreurs["wikidata"] = f"réponse {r.status_code}"
                raise SourceIndisponible(f"wikidata : réponse {r.status_code}")
            self.erreurs.pop("wikidata", None)
            trouves = {}
            for b in r.json()["results"]["bindings"]:
                trouves[b["t"]["value"]] = {"n": int(b["n"]["value"]), "humain": b["h"]["value"] == "true"}
            for t in lot:
                self.base.garder_source(f"wd:fr:{t}", json.dumps(trouves.get(t, {})))
            sortie.update(trouves)
            time.sleep(self.pause)
        return sortie

    # ------------------------------------------------------------ Larousse
    @staticmethod
    def larousse_couvre(annee: int, mois: int) -> bool:
        return LAROUSSE_DEBUT <= (annee, mois) <= LAROUSSE_FIN

    def larousse(self, annee: int, mois: int) -> str:
        """La page « chronologie du mois » ; '' hors couverture (redirection) ou si Larousse est coupé."""
        if not self.larousse_actif or not self.larousse_couvre(annee, mois):
            return ""
        cle = f"lar:{annee:04d}-{mois:02d}"
        deja = self.base.source(cle)
        if deja is not None:
            return deja
        url = f"https://www.larousse.fr/archives/journaux_annee/{annee + 1}/chrono/{annee:04d}-{mois:02d}"
        r = self._get("larousse", url)
        contenu = r.text if r.status_code == 200 else ""
        self.base.garder_source(cle, contenu)
        return contenu

    # ------------------------------------------------------------ état (écran Connexion)
    def sonder(self) -> dict:
        """Une lecture légère de chaque source, sans rien garder."""
        res = {}
        essais = {
            "wikipedia-fr": "https://fr.wikipedia.org/w/index.php?title=Wikip%C3%A9dia&action=raw",
            "wikipedia-en": "https://en.wikipedia.org/w/index.php?title=Wikipedia&action=raw",
            "wikidata": "https://query.wikidata.org/sparql?query=ASK%7B%7D&format=json",
            "larousse": "https://www.larousse.fr/archives/journaux_annee/1984/chrono/1983-11",
        }
        for nom, url in essais.items():
            if nom == "larousse" and not self.larousse_actif:
                res[nom] = {"ok": None, "detail": "coupé (GAZETTE_LAROUSSE=non)"}
                continue
            if not self.actives:
                res[nom] = {"ok": None, "detail": "lecture coupée"}
                continue
            try:
                r = self.client.get(url, timeout=15)
                res[nom] = {"ok": r.status_code == 200, "detail": f"réponse {r.status_code}"}
            except httpx.HTTPError as ex:
                res[nom] = {"ok": False, "detail": str(ex)[:120]}
        return res
