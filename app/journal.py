"""Les éléments communs à tous les livrets (titre du journal, lieu, hôtes, mot par défaut, couleur, Larousse),
réglés dans l'appli (Réglages › Le journal) et gardés dans la base (`reglages`, clé « journal »).

0.8 : ce sont les réglages d'usage de Gazette, ceux que l'Anneau sauvegarde (GET /externe/sauvegarde) et que
« Restaurer les réglages » remet. Les anciennes variables de la stack (GAZETTE_TITRE, GAZETTE_SIGNATURE,
GAZETTE_LIEU, GAZETTE_LAROUSSE) ne sont lues qu'une fois, au premier démarrage, pour une clé encore absente de
la base (`reprendre`) ; ensuite seul l'écran Réglages fait foi."""
from __future__ import annotations

import json
import os
import re
from datetime import date

from . import maison
from .regles import jour_mois

CHAMPS = {
    # clé : (libellé, aide, longueur maximale)
    "titre": ("Titre du journal", "le grand titre gothique de la une et l'en-tête des pages", 60),
    "sous_titre": ("Sous-titre", "sous le titre de la une", 90),
    "lieu": ("Nom du lieu", "le colophon de la page 4", 60),
    "lieu_detail": ("Sous le nom du lieu", "par exemple la commune et le département ; vide : rien", 80),
    "chez": ("Chez vous, avec l'article", "« au … », « à la … » : sert à « Imprimé … » et dans le mot des hôtes", 60),
    "signature": ("Signature des hôtes", "au bas du mot des hôtes", 60),
    "mot_modele": ("Mot des hôtes par défaut", "{date}, {prenom} et {chez} sont remplacés ; une ligne vide sépare les paragraphes", 1500),
    "accent": ("Couleur d'accent", "titres de rubrique, chiffres, lettrine (#RRGGBB)", 7),
    # 0.18 : La Récidive (journal à scandale dès le 2e séjour) — réglages généraux (demande de Julien du 17/11)
    "r_titre": ("Titre du magazine", "le grand titre de la une de La Récidive", 40),
    "r_accroche_femme": ("Accroche sous le titre (femme)", "{prenom} est remplacé ; modifiable dans chaque édition", 80),
    "r_accroche_homme": ("Accroche sous le titre (homme)", "{prenom} est remplacé ; modifiable dans chaque édition", 80),
    "r_accroche_autre": ("Accroche sous le titre (genre inconnu)", "{prenom} est remplacé ; sans « il » ni « elle »", 80),
    "r_mot_modele": ("Droit de réponse par défaut", "le mot des hôtes de la page 4 ; {salut} (« Chère Camille », « Cher Paul ») et {prenom} sont remplacés ; une ligne vide sépare les paragraphes", 1500),
    # 0.22 : second modèle de l'IA du PC, pour « Autres propositions » (choix de Julien du 18/11 : on génère avec le
    # modèle habituel, GAZETTE_OLLAMA_MODELE, on régénère avec celui-ci). Un réglage de Gazette, pas de la stack.
    # 0.28 : « Good Evening Europe! », l'édition spéciale Eurovision (un numéro par soirée Douze points clôturée)
    "e_titre": ("Titre du magazine Eurovision", "le grand titre de l'édition spéciale ; le dernier mot est en rose", 40),
    "modele_second": ("Second modèle de l'IA", "nom dans « ollama list » (ex. qwen2.5:14b) ; sert au bouton « Autres propositions » ; vide : bouton caché", 80),
}
LIBELLES = {**{k: v[0] for k, v in CHAMPS.items()}, "larousse": "Larousse, Journaux de l'année",
            "eurovision": "Édition spéciale Eurovision (Douze points)"}
MOT = ("Le {date}, le monde tournait comme le racontent ces pages. Ce soir, c'est {chez} que l'on vous attend.\n\n"
       "Ce petit journal est à vous, {prenom} : il raconte le monde tel qu'il était le jour de votre naissance. "
       "Gardez-le, glissez-le dans un livre, ou relisez-le au petit-déjeuner.\n\n"
       "Installez-vous, reposez-vous, et surtout faites comme chez vous.")
R_MOT = ("{salut}, vous avez lu notre enquête : nous assumons tout. Les hôtes n'ont qu'un seul démenti à faire valoir : "
         "vous nous avez manqué.\n\n"
         "Votre chambre est prête. Rien ne sortira de la maison, hormis ce journal, et il est à vous.")
DEFAUTS = {"titre": "La Gazette", "sous_titre": "Le monde tel qu'il était le jour de votre naissance",
           "lieu": "La maison", "lieu_detail": "", "chez": "à la maison", "signature": "Vos hôtes",
           "mot_modele": MOT, "accent": "#9E1B1B", "larousse": True,
           "r_titre": "La Récidive", "r_accroche_femme": "Elle est revenue, nous aussi",
           "r_accroche_homme": "Il est revenu, nous aussi", "r_accroche_autre": "{prenom} est de retour, nous aussi",
           "r_mot_modele": R_MOT, "modele_second": "qwen2.5:14b",
           "e_titre": "Good Evening Europe!", "eurovision": True}
# Anciennes variables de la stack, lues une seule fois (premier démarrage) pour une clé absente de la base
VARIABLES = {"titre": "GAZETTE_TITRE", "signature": "GAZETTE_SIGNATURE", "lieu": "GAZETTE_LIEU",
             "larousse": "GAZETTE_LAROUSSE"}
# Jamais dans une sauvegarde, même si une telle clé apparaissait un jour (en plus de maison.est_secret)
EXCLUS = ("mot_de_passe", "password", "jeton", "jeton_ha", "jeton_carnet", "carnet_url", "imprimante")


def _lire(base) -> dict:
    try:
        j = json.loads(base.reglage("journal", "{}"))
    except ValueError:
        return {}
    return j if isinstance(j, dict) else {}


def reprendre(base) -> list[str]:
    """Au démarrage : complète le journal gardé dans la base. Une clé absente prend la valeur de son ancienne
    variable si elle est posée (reprise, rendue pour le journal de l'appli), sinon la valeur par défaut. Une clé
    déjà gardée n'est jamais changée : la variable n'est plus lue."""
    j, repris, change = _lire(base), [], False
    for cle, defaut in DEFAUTS.items():
        if cle in j:
            continue
        brut = os.environ.get(VARIABLES.get(cle, ""), "").strip() if cle in VARIABLES else ""
        if brut:
            j[cle] = brut.lower() not in maison.FAUX if isinstance(defaut, bool) else " ".join(brut.split())[:CHAMPS[cle][2]]
            repris.append(cle)
        else:
            j[cle] = defaut
        change = True
    if change:
        base.poser_reglage("journal", json.dumps(j, ensure_ascii=False))
    return repris


def charger(base) -> dict:
    j = dict(DEFAUTS)
    j.update({k: v for k, v in _lire(base).items() if k in DEFAUTS})
    return j


def enregistrer(base, j: dict) -> None:
    base.poser_reglage("journal", json.dumps({k: j[k] for k in DEFAUTS if k in j}, ensure_ascii=False))


def valider(corps: dict, actuel: dict) -> dict:
    """Contrôle et applique les clés connues (les autres sont ignorées). ValueError avec un message clair si une
    valeur n'a pas le bon type ou ne convient pas."""
    if not isinstance(corps, dict):
        raise ValueError("Réglages attendus sous forme d'objet JSON.")
    j = dict(actuel)
    for cle, (libelle, _, maxi) in CHAMPS.items():
        if cle not in corps:
            continue
        brut = corps[cle]
        if brut is None:
            brut = ""
        if not isinstance(brut, str):
            raise ValueError(f"{libelle} : texte attendu.")
        v = brut.replace("\r", "")
        v = v.strip() if cle in ("mot_modele", "r_mot_modele") else " ".join(v.split())
        if len(v) > maxi:
            raise ValueError(f"{libelle} : {maxi} caractères au plus.")
        if cle in ("titre", "lieu", "chez", "signature", "mot_modele", "r_titre", "r_accroche_femme", "r_accroche_homme",
                   "r_accroche_autre", "r_mot_modele", "e_titre") and not v:
            raise ValueError(f"{libelle} : à remplir.")
        if cle == "accent" and not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError("Couleur d'accent : au format #RRGGBB.")
        if cle == "modele_second" and not re.fullmatch(r"[\w.:/-]*", v):
            raise ValueError("Second modèle de l'IA : un nom comme dans « ollama list » (ex. qwen2.5:14b), sans espace.")
        j[cle] = v
    if "larousse" in corps:
        if not isinstance(corps["larousse"], bool):
            raise ValueError("Larousse : oui ou non attendu (true ou false).")
        j["larousse"] = corps["larousse"]
    if "eurovision" in corps:                 # 0.28 : interrupteur du type « eurovision »
        if not isinstance(corps["eurovision"], bool):
            raise ValueError("Édition spéciale Eurovision : oui ou non attendu (true ou false).")
        j["eurovision"] = corps["eurovision"]
    return j


def mot(j: dict, prenom: str, naissance: date) -> str:
    valeurs = {"date": f"{jour_mois(naissance)} {naissance.year}", "prenom": prenom, "chez": j["chez"]}
    return re.sub(r"\{(date|prenom|chez)\}", lambda m: valeurs[m.group(1)], j["mot_modele"])


# ================================================================ 0.18 : La Récidive

def r_accroche(j: dict, genre: str, prenom: str) -> str:
    """L'accroche sous le titre de La Récidive, selon le genre de la fiche carnet (Réglages › La Récidive)."""
    modele = j.get({"femme": "r_accroche_femme", "homme": "r_accroche_homme"}.get(genre, "r_accroche_autre")) \
        or DEFAUTS["r_accroche_autre"]
    return modele.replace("{prenom}", prenom or "Notre invité·e")


def r_mot(j: dict, salut: str, prenom: str) -> str:
    """Le droit de réponse par défaut de La Récidive."""
    return re.sub(r"\{(salut|prenom)\}", lambda m: {"salut": salut, "prenom": prenom}[m.group(1)],
                  j.get("r_mot_modele") or R_MOT)
