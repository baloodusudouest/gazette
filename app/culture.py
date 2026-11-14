"""Le top 5 culturel de chaque année (films, séries, musique), pour la page 3 du livret.

Le fichier `top5_culture_annuel.csv` (séparateur `;`, UTF-8 avec BOM, colonnes
Annee;Categorie;Rang;Titre;Createur_Artiste;Metrique_Cles) est préparé avec Claude par le prompt de
`donnees/prompt_culture.md`, puis importé dans Gazette (Réglages). Une version est livrée avec l'appli ;
un fichier importé la remplace (`/data/culture.csv`). Les lignes « PROVISOIRE » sont proposées, signalées.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

DONNEES = Path(__file__).parent / "donnees"
INTEGRE = DONNEES / "top5_culture_annuel.csv"
PROMPT = DONNEES / "prompt_culture.md"
COLONNES = ["Annee", "Categorie", "Rang", "Titre", "Createur_Artiste", "Metrique_Cles"]
CATEGORIES = ("Film", "Serie", "Musique")


class FichierCultureInvalide(ValueError):
    pass


def lire_texte(texte: str) -> list[dict]:
    """Lit et contrôle un fichier ; rend les lignes {annee, categorie, rang, titre, createur, metrique, provisoire}."""
    texte = texte.lstrip("﻿")
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=";")
    if [c.strip() for c in (lecteur.fieldnames or [])] != COLONNES:
        raise FichierCultureInvalide("Colonnes attendues : " + ";".join(COLONNES) + ".")
    lignes, vus, erreurs = [], set(), []
    for n, l in enumerate(lecteur, start=2):
        try:
            annee, rang = int(l["Annee"]), int(l["Rang"])
        except (TypeError, ValueError):
            erreurs.append(f"ligne {n} : année ou rang illisible")
            continue
        cat, titre = (l["Categorie"] or "").strip(), (l["Titre"] or "").strip()
        if cat not in CATEGORIES:
            erreurs.append(f"ligne {n} : catégorie « {cat} » inconnue")
            continue
        if not 1 <= rang <= 5 or not titre or not 1800 <= annee <= 2200:
            erreurs.append(f"ligne {n} : rang, titre ou année hors des valeurs possibles")
            continue
        cle = (annee, cat, titre.lower())
        if cle in vus:
            erreurs.append(f"ligne {n} : doublon ({annee}, {cat}, {titre})")
            continue
        vus.add(cle)
        metrique = (l["Metrique_Cles"] or "").strip()
        lignes.append({"annee": annee, "categorie": cat, "rang": rang, "titre": titre,
                       "createur": (l["Createur_Artiste"] or "").strip(), "metrique": metrique,
                       "provisoire": metrique.upper().startswith("PROVISOIRE")})
    if erreurs:
        raise FichierCultureInvalide(f"{len(erreurs)} ligne(s) refusée(s) : " + " ; ".join(erreurs[:8]))
    if not lignes:
        raise FichierCultureInvalide("Fichier vide.")
    return lignes


class Culture:
    def __init__(self, data: Path):
        self.importe = data / "culture.csv"
        self._lignes: list[dict] | None = None

    def fichier(self) -> Path:
        return self.importe if self.importe.is_file() else INTEGRE

    def lignes(self) -> list[dict]:
        if self._lignes is None:
            try:
                self._lignes = lire_texte(self.fichier().read_text(encoding="utf-8-sig"))
            except (OSError, FichierCultureInvalide):
                self._lignes = lire_texte(INTEGRE.read_text(encoding="utf-8-sig")) if INTEGRE.is_file() else []
        return self._lignes

    def importer(self, texte: str) -> dict:
        lignes = lire_texte(texte)                      # refusé avant toute écriture
        self.importe.write_text(texte.lstrip("﻿"), encoding="utf-8-sig")
        self._lignes = lignes
        return self.etat()

    def revenir(self) -> dict:
        """Retire le fichier importé : la version livrée avec l'appli revient."""
        if self.importe.is_file():
            self.importe.unlink()
        self._lignes = None
        return self.etat()

    def etat(self) -> dict:
        l = self.lignes()
        f = self.fichier()
        return {"source": "importé" if f == self.importe else "livré avec l'appli",
                "importe_le": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds") if f == self.importe else "",
                "lignes": len(l), "annees": [min(x["annee"] for x in l), max(x["annee"] for x in l)] if l else [],
                "provisoires": sum(1 for x in l if x["provisoire"]),
                "a_verifier": sum(1 for x in l if "à vérifier" in x["metrique"])}

    def annee(self, annee: int) -> dict[str, list[dict]]:
        sortie = {c: [] for c in CATEGORIES}
        for x in self.lignes():
            if x["annee"] == annee:
                sortie[x["categorie"]].append(x)
        for c in sortie:
            sortie[c].sort(key=lambda x: x["rang"])
        return sortie


def _qui(x: dict) -> str:
    return f" ({x['createur']})" if x["createur"] else ""


def textes(top: dict[str, list[dict]]) -> dict[str, str]:
    """Les deux rubriques de la page 3, en phrases courtes (2 films et 2 titres, une série) : la page est pleine.
    « Le titre de l'année » et « en tête du box-office » seulement quand la source le mesure."""
    musique, cinema = "", ""
    m = top.get("Musique", [])[:2]
    if m:
        mesure = "year-end #1" in m[0]["metrique"].lower() or "ifpi" in m[0]["metrique"].lower()
        musique = f"« {m[0]['titre']} »{_qui(m[0])}, " + ("le titre de l'année" if mesure else "un des grands succès de l'année")
        if len(m) > 1:
            musique += f", devant « {m[1]['titre']} »{_qui(m[1])}"
        musique += "."
    f = top.get("Film", [])[:2]
    if f:
        mesure = f[0]["metrique"].upper().startswith(("N°1", "PROVISOIRE"))
        cinema = f"« {f[0]['titre']} »{_qui(f[0])} " + ("en tête du box-office" if mesure else "parmi les grands succès du cinéma")
        if len(f) > 1:
            cinema += f", devant « {f[1]['titre']} »"
        cinema += "."
    s = top.get("Serie", [])[:1]
    if s:
        cinema += (" " if cinema else "") + f"À la télé : « {s[0]['titre']} »."
    return {"musique": musique, "cinema": cinema}
