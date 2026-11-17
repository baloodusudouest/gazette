"""0.9.1 : propositions de titres pour La Récidive par une IA locale (Ollama sur le PC de la maison).

Julien écrit en quelques mots ce qu'on voit sur une photo ; le modèle de texte (qwen2.5:7b) propose 5 titres façon
presse à scandale, de 60 caractères au plus ; Julien en choisit un ou écrit le sien. Pas de modèle de vision : la
photo ne quitte pas Gazette, seule la description part vers le PC.

Le code filtre ce que le modèle rend (longueur, refus, lignes vides, doublons, anglais, genre) et redemande au plus
trois fois. PC éteint ou Ollama injoignable : aucune proposition, un message avec la marche à suivre ; la légende de
gabarit reste et Julien peut toujours écrire la sienne. Adresse : GAZETTE_OLLAMA_URL (vide : pas d'IA)."""
from __future__ import annotations

import re
from typing import Callable

import httpx

MODELE = "qwen2.5:7b"
MAXI = 60                 # caractères par titre (choix de Julien du 17/11/2026)
NOMBRE = 5
ESSAIS = 3
DELAI = 120               # secondes : le modèle doit parfois se charger sur la carte graphique

MARCHE = ("Sur le PC : ouvrir Ollama (icône près de l'horloge). Une seule fois : dans PowerShell, "
          "« setx OLLAMA_HOST 0.0.0.0 » puis quitter et rouvrir Ollama, et autoriser le port 11434 dans le pare-feu "
          "(« New-NetFirewallRule -DisplayName Ollama -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow », "
          "en administrateur) ; le modèle doit être là (« ollama pull qwen2.5:7b »). Dans la stack : "
          "GAZETTE_OLLAMA_URL=http://<adresse du PC>:11434.")

INTERDITS = re.compile(r"\b(je ne peux|désolé|en tant qu|as an ai|sorry|i can)\b", re.I)
ANGLAIS = re.compile(r"\b(the|and|with|her|his|is|of|you)\b", re.I)

Lire = Callable[[str, dict], dict]


def _lire_http(url: str) -> Lire:
    def lire(chemin: str, corps: dict | None):
        if corps is None:
            r = httpx.get(f"{url}{chemin}", timeout=8)
        else:
            r = httpx.post(f"{url}{chemin}", json=corps, timeout=DELAI)
        if r.status_code >= 400:
            # 0.9.4 : le message d'Ollama (« model 'qwen2.5:7b' not found »…) plutôt qu'un simple code
            try:
                detail = str(r.json().get("error") or "")
            except ValueError:
                detail = r.text[:160]
            raise ErreurOllama(r.status_code, detail or f"réponse {r.status_code}")
        return r.json()
    return lire


class ErreurOllama(Exception):
    """Ollama a répondu, mais avec une erreur (modèle absent, mémoire…) : le PC est joignable."""
    def __init__(self, statut: int, detail: str):
        super().__init__(detail)
        self.statut, self.detail = statut, detail


def consigne(description: str, sorte: str, genre: str, prenom: str) -> str:
    qui = {"femme": f"une femme, {prenom}", "homme": f"un homme, {prenom}"}.get(genre, f"{prenom} (genre inconnu : n'accorde rien au féminin ni au masculin)")
    quoi = ("le GROS TITRE de la une d'un journal à scandale qui annonce son retour chez nous"
            if sorte == "une" else "la LÉGENDE d'une photo dans un journal à scandale")
    return (f"Tu écris en français pour un faux journal à scandale offert à un invité qui revient chez nous : {qui}.\n"
            f"Écris {NOMBRE} propositions pour {quoi}.\n"
            f"Ce que montre la photo, d'après l'hôte : « {description} »\n"
            "Règles : ton tabloïd, drôle et bienveillant ; " f"{MAXI} caractères au plus chacune ; "
            "n'invente aucun fait absent de la description ; aucune moquerie du physique ; aucun autre nom que celui "
            "de l'invité ; pas de guillemets ni d'emoji.\n"
            f"Réponds seulement par les {NOMBRE} propositions, une par ligne, numérotées 1. à {NOMBRE}.")


def nettoyer(texte: str, genre: str) -> list[str]:
    """Les lignes qui tiennent : numéro retiré, sans refus, sans anglais, sans genre deviné, 60 caractères au plus."""
    res = []
    for l in (texte or "").splitlines():
        l = re.sub(r"^\s*(\d+[.)\-:]|[-•*])\s*", "", l).strip().strip('"«»“”*').strip()
        l = re.sub(r"\s+", " ", l)
        if not l or len(l) > MAXI or len(l) < 6 or INTERDITS.search(l) or len(ANGLAIS.findall(l)) >= 2:
            continue
        if not genre and re.search(r"\b(elle|il)\b", l, re.I):
            continue
        if l.casefold() not in {x.casefold() for x in res}:
            res.append(l)
    return res


class Ollama:
    def __init__(self, url: str, lire: Lire | None = None):
        self.url = url.rstrip("/")
        self._lire = lire or (_lire_http(self.url) if self.url else None)
        self.erreur = ""

    @property
    def actif(self) -> bool:
        return self._lire is not None

    def proposer(self, description: str, sorte: str = "photo", genre: str = "", prenom: str = "") -> list[str]:
        """Jusqu'à 5 titres. RuntimeError (avec la marche à suivre) si l'IA n'est pas joignable ou ne rend rien d'utile."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        description = " ".join((description or "").split())[:400]
        if len(description) < 3:
            raise ValueError("Écris d'abord en quelques mots ce qu'on voit sur la photo.")
        props: list[str] = []
        for _ in range(ESSAIS):
            try:
                r = self._lire("/api/generate", {"model": MODELE, "prompt": consigne(description, sorte, genre, prenom),
                                                 "stream": False, "options": {"temperature": 0.9, "num_predict": 300}})
            except ErreurOllama as ex:
                self.erreur = ex.detail[:160]
                if ex.statut == 404:
                    raise RuntimeError(f"Le PC répond, mais Ollama n'y trouve pas le modèle {MODELE} ({ex.detail}). "
                                       f"Sur le PC : « ollama list » doit le montrer ; sinon « ollama pull {MODELE} », ou "
                                       "vérifier OLLAMA_MODELS puis quitter et rouvrir Ollama.") from ex
                raise RuntimeError(f"Ollama a refusé la demande ({ex.detail}).") from ex
            except Exception as ex:  # noqa: BLE001 — PC éteint, Ollama fermé, pare-feu
                self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
                raise RuntimeError(f"IA du PC injoignable ({self.erreur}). " + MARCHE) from ex
            self.erreur = ""
            for p in nettoyer(str((r or {}).get("response", "")), genre):
                if p.casefold() not in {x.casefold() for x in props}:
                    props.append(p)
            if len(props) >= NOMBRE:
                break
        if not props:
            raise RuntimeError("L'IA n'a rien proposé d'utilisable : reformule la description, ou écris ton titre.")
        return props[:NOMBRE]

    def sonder(self) -> dict:
        if not self.actif:
            return {"ok": None, "detail": "pas réglée (GAZETTE_OLLAMA_URL vide) : pas de propositions de titres"}
        try:
            r = self._lire("/api/tags", None)
        except Exception as ex:  # noqa: BLE001
            self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
            return {"ok": False, "detail": f"PC injoignable ({self.erreur})"}
        noms = [m.get("name", "") for m in (r or {}).get("models", [])]
        if not any(n.split(":")[0] == MODELE.split(":")[0] and n.endswith(MODELE.split(":")[1]) for n in noms):
            return {"ok": False, "detail": f"PC joignable, mais le modèle {MODELE} n'y est pas (ollama pull {MODELE})"}
        return {"ok": True, "detail": f"PC prêt ({MODELE})"}

    def etat(self) -> dict:
        return {"regle": self.actif, "erreur": self.erreur, "modele": MODELE, "maxi": MAXI, "marche": MARCHE}
