"""0.25 : banque d'inspiration — rumeurs, horoscopes, mots des hôtes et titres « scandale » importés depuis un fichier
texte (fait par Claude, ChatGPT ou Gemini). Elle sert deux fois : Gazette y pioche des propositions toutes prêtes
(bouton « Banque », même sans l'IA du PC), et l'IA du PC en reçoit quelques-unes comme exemples de ton.

Format du fichier (texte UTF-8, plusieurs fichiers ou morceaux recollés possibles) :

    # RUMEURS
    - Selon nos informations, {prenom} aurait tenté d'adopter un rond-point.
    # HOROSCOPES
    - Mercure entre dans votre valise : {prenom}, n'oubliez pas le chargeur.
    # MOTS
    - {salut}, la maison a rangé ses secrets : il ne reste que le vôtre.
    # TITRES
    - {prenom} démasqué{e} au rayon fromages

Une section commence par une ligne « # RUMEURS » (ou HOROSCOPES, MOTS, TITRES ; « # » facultatif, singulier,
accents et casse indifférents) ; sous une section, chaque ligne non vide est un élément (puce « - », « * », « • » ou
numéro « 12. » retirés ; phrases de l'IA comme « Voici la suite : » ignorées). Une rumeur ou un titre doit contenir
{prenom} ; si l'IA l'a perdu en laissant un double espace, il y est remis. Forme sur une ligne
aussi lue : « rumeur | texte ». Balises : {prenom}, {salut} (« Chère Camille », « Cher Paul »), {chez} (« à la
maison »), {il} (il / elle), {e} (« » / « e » pour l'accord). Un texte avec {il} ou {e} n'est pas proposé quand le
genre de la personne est inconnu.
"""
from __future__ import annotations

import re
import unicodedata

SORTES = ("rumeur", "horoscope", "mot", "titre")
NOMS = {"rumeur": "Rumeurs", "horoscope": "Horoscopes", "mot": "Mots des hôtes", "titre": "Titres scandale"}
# Longueur maximale une fois les balises remplacées (prénom de 10 lettres) : celle des cases de Gazette
MAXI = {"rumeur": 130, "horoscope": 240, "mot": 700, "titre": 60}
MINI = 12
BALISES = ("prenom", "salut", "chez", "il", "e")
_SECTIONS = {"rumeur": "rumeur", "rumeurs": "rumeur", "horoscope": "horoscope", "horoscopes": "horoscope",
             "mot": "mot", "mots": "mot", "mot des hotes": "mot", "mots des hotes": "mot", "droit de reponse": "mot",
             "titre": "titre", "titres": "titre", "titres scandale": "titre", "titre scandale": "titre",
             "titres type scandale": "titre", "legende": "titre", "legendes": "titre"}
ESSAI_PRENOM = "Maximilien"      # 10 lettres : sert à mesurer un texte à l'import
EXIGE_PRENOM = ("rumeur", "titre")  # 0.25.1 : une rumeur ou un titre sans {prenom} est écarté


def plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9{} ]+", " ", t).split())


def cle(sorte: str, texte: str) -> str:
    """Clé de doublon : même sorte, même texte à la ponctuation, aux accents et à la casse près."""
    return f"{sorte}:{plat(texte)}"


def _section(ligne: str) -> str | None:
    """« # RUMEURS », « [RUMEURS] », « == RUMEURS == », et 0.25.1 : « RUMEURS » ou « **Rumeurs :** » seul sur sa ligne."""
    m = re.match(r"^\s*(?:#{1,6}|\[|==+)?\s*\**\s*(.+?)\s*\**\s*(?:\]|==+)?\s*:?\s*\**\s*$", ligne)
    if not m:
        return None
    nom = plat(re.sub(r"\(.*?\)|\d+", " ", m.group(1)))
    return _SECTIONS.get(nom)


def _reparer_prenom(sorte: str, brut: str) -> str:
    """0.25.1 : une IA a perdu la balise {prenom} en route (« Selon le facteur,  aurait… ») : le double espace laissé
    à sa place la reçoit. Seulement pour les sortes qui exigent le prénom, et s'il n'y a aucune balise."""
    if sorte in EXIGE_PRENOM and "{" not in brut and re.search(r"\S {2,}\S", brut.strip()):
        return re.sub(r"(?<=\S) {2,}(?=\S)", " {prenom} ", brut.strip(), count=1)
    return brut


def _nettoyer(t: str) -> str:
    t = " ".join((t or "").split())
    t = re.sub(r"^(?:[-*•–—]|\d{1,4}\s*[.)\-:–—])\s*", "", t)      # puce ou numéro
    t = t.strip().strip("\"«»“”").strip()
    # balises écrites autrement par une IA : {Prénom}, [prenom], {{prenom}}, {PRENOM}
    t = re.sub(r"\{+\s*pr[ée]nom\s*\}+|\[\s*pr[ée]nom\s*\]", "{prenom}", t, flags=re.I)
    t = re.sub(r"\{+\s*(salut|chez|il|e)\s*\}+", lambda m: "{" + m.group(1).lower() + "}", t, flags=re.I)
    return t


def mesurer(sorte: str, texte: str) -> str | None:
    """Raison du refus d'un texte à l'import, ou None s'il est bon."""
    if len(texte) < MINI:
        return "trop court"
    if sorte in EXIGE_PRENOM and "{prenom}" not in texte:
        return "sans {prenom}"
    inconnues = {b for b in re.findall(r"\{([^{}]*)\}", texte) if b not in BALISES}
    if inconnues:
        return "balise inconnue {" + ", ".join(sorted(inconnues)) + "}"
    essai = rendre(texte, ESSAI_PRENOM, "femme", "à la maison")
    if not essai or len(essai) > MAXI[sorte]:
        return f"trop long (plus de {MAXI[sorte]} signes)"
    return None


def lire(contenu: str) -> tuple[dict[str, list[str]], dict[str, int]]:
    """({sorte: [textes]}, {raison: nombre}) d'un fichier ; les doublons internes sont retirés."""
    res: dict[str, list[str]] = {s: [] for s in SORTES}
    vus: set[str] = set()
    ecarts: dict[str, int] = {}
    courante: str | None = None
    for ligne in (contenu or "").replace("\r", "").split("\n"):
        if not ligne.strip():
            continue
        s = _section(ligne)
        if s:
            courante = s
            continue
        sorte, texte = courante, None
        m = re.match(r"^\s*(rumeurs?|horoscopes?|mots?|titres?)\s*[|;\t]\s*(.+)$", ligne, re.I)
        if m:
            sorte, texte = _SECTIONS[plat(m.group(1))], m.group(2)
        elif courante and (re.match(r"^\s*(?:[-*•–—]|\d{1,4}\s*[.)\-:–—])\s*\S", ligne) or not _bavardage(ligne)):
            texte = ligne              # 0.25.1 : une ligne sans puce sous une section compte aussi
        if not sorte or texte is None:
            continue
        texte = _nettoyer(_reparer_prenom(sorte, re.sub(r"^\s*(?:[-*•–—]|\d{1,4}\s*[.)\-:–—])\s*", "", texte)))
        pourquoi = mesurer(sorte, texte)
        if pourquoi:
            raison = "balise inconnue" if pourquoi.startswith("balise inconnue") else pourquoi.split(" (")[0]
            ecarts[raison] = ecarts.get(raison, 0) + 1
            continue
        k = cle(sorte, texte)
        if k in vus:
            ecarts["doublon dans le fichier"] = ecarts.get("doublon dans le fichier", 0) + 1
            continue
        vus.add(k)
        res[sorte].append(texte)
    return res, ecarts


def _bavardage(ligne: str) -> bool:
    """Une phrase de l'IA autour des textes (« Voici les 100 rumeurs : », « Souhaitez-vous la suite ? »), pas un texte."""
    t = ligne.strip()
    return (t.endswith(":") or t.endswith("?") or t.startswith(("```", "---", ">"))
            or bool(re.match(r"^(voici|here|bien s[uû]r|parfait|d'accord|souhaitez|veux-tu|voulez|je (vais|continue|peux)|"
                             r"lot|suite|fin du|total|compteur|rumeurs \d|horoscopes \d|mots \d|titres \d)", plat(t))))


def salut(genre: str, prenom: str) -> str:
    return {"femme": f"Chère {prenom}", "homme": f"Cher {prenom}"}.get(genre, f"Bonjour {prenom}")


def rendre(texte: str, prenom: str, genre: str, chez: str) -> str | None:
    """Le texte avec ses balises remplacées ; None si le genre manque pour {il} / {e}."""
    if not genre and re.search(r"\{(il|e)\}", texte):
        return None
    valeurs = {"prenom": prenom or "notre invité", "salut": salut(genre, prenom or ""), "chez": chez or "à la maison",
               "il": "elle" if genre == "femme" else "il", "e": "e" if genre == "femme" else ""}
    # 0.25.1 : élision devant le prénom (« qu'{prenom} » → « que Paul » ou « qu'Audrey », pareil pour « de / d' »)
    voyelle = bool(re.match(r"[aeiouyhàâäéèêëîïôöûüœ]", (prenom or "n").lower()))
    texte = re.sub(r"\b([Qq]u|[Dd])(?:e |'|’)(?=\{prenom\})", lambda m: m.group(1) + ("'" if voyelle else "e "), texte)
    sortie = re.sub(r"\{(prenom|salut|chez|il|e)\}", lambda m: valeurs[m.group(1)], texte)
    # « Il » en début de phrase
    sortie = re.sub(r"(^|[.!?…]\s+)(il|elle)\b", lambda m: m.group(1) + m.group(2).capitalize(), sortie)
    return " ".join(sortie.split())


def pour_ia(textes: list[str], sorte: str) -> str:
    """Les exemples donnés à l'IA du PC : pour le ton, jamais à recopier."""
    if not textes:
        return ""
    quoi = {"rumeur": "rumeurs", "horoscope": "horoscopes", "mot": "mots des hôtes", "titre": "titres"}[sorte]
    return (f"Exemples de {quoi} tirés de notre banque, pour le ton seulement (n'en recopie aucun, invente autre "
            "chose) :\n" + "\n".join(f"- {t}" for t in textes))


def exporter(lignes: list[dict]) -> str:
    """Le fichier de la banque, au format d'import (les balises sont gardées)."""
    morceaux = ["# Banque d'inspiration de Gazette (format d'import : une section par sorte, une ligne par texte)", ""]
    for s in SORTES:
        textes = [x["texte"] for x in lignes if x["sorte"] == s]
        if textes:
            morceaux += [f"# {NOMS[s].upper()}", *[f"- {t}" for t in textes], ""]
    return "\n".join(morceaux)
