"""0.9.1 : propositions de titres pour La Récidive par une IA locale (Ollama sur le PC de la maison).

Julien écrit en quelques mots ce qu'on voit sur une photo ; le modèle de texte (mistral-nemo par défaut) propose 5 titres façon
presse à scandale, de 60 caractères au plus ; Julien en choisit un ou écrit le sien. Pas de modèle de vision : la
photo ne quitte pas Gazette, seule la description part vers le PC.

Le code filtre ce que le modèle rend (longueur, refus, lignes vides, doublons, anglais, genre) et redemande au plus
trois fois. PC éteint ou Ollama injoignable : aucune proposition, un message avec la marche à suivre ; la légende de
gabarit reste et Julien peut toujours écrire la sienne. Adresse : GAZETTE_OLLAMA_URL (vide : pas d'IA)."""
from __future__ import annotations

import difflib
import os
import re
from typing import Callable

import httpx

MODELE = os.environ.get("GAZETTE_OLLAMA_MODELE", "").strip() or "mistral-nemo"   # 0.9.6 : modèle changeable ; 0.24.2 : mistral-nemo par défaut (choix de Julien du 18/11)
MAXI = 60                 # caractères par titre (choix de Julien du 17/11/2026)
NOMBRE = 5
ESSAIS = 3
DELAI = 120               # secondes : le modèle doit parfois se charger sur la carte graphique

MARCHE = (f"Sur le PC : ouvrir Ollama depuis le menu Démarrer (pas depuis un PowerShell administrateur), attendre "
          f"10 secondes, puis Connexion › IA du PC › Vérifier. Le modèle {MODELE} doit être dans « ollama list ». "
          "Détails et pannes : Connexion › IA du PC.")


def meme_modele(nom: str, voulu: str) -> bool:
    """0.20.3 : « mistral-nemo » et « mistral-nemo:latest » sont le même modèle (Ollama ajoute « :latest » quand
    aucune étiquette n'est donnée). Avant, un nom sans « : » faisait planter la vérification."""
    complet = lambda m: m.strip() if ":" in m else m.strip() + ":latest"
    return complet(nom) == complet(voulu)


def guide(url: str) -> dict:
    """0.20.2 : la marche à suivre complète affichée dans Connexion › IA du PC : réglages lus, démarrage normal,
    installation (une seule fois) et pannes connues, avec les commandes PowerShell à copier. Rien de propre à une
    machine (ni dossier, ni nom) : l'adresse vient de GAZETTE_OLLAMA_URL, le modèle de GAZETTE_OLLAMA_MODELE."""
    adresse = url or "http://<adresse du PC>:11434"
    journal = '"$env:LOCALAPPDATA\\Ollama\\server.log"'
    return {
        "reglages": [
            {"nom": "Adresse appelée", "valeur": url or "pas réglée (GAZETTE_OLLAMA_URL vide)"},
            {"nom": "Modèle", "valeur": MODELE + ("" if os.environ.get("GAZETTE_OLLAMA_MODELE", "").strip()
                                                  else " (par défaut ; GAZETTE_OLLAMA_MODELE pour en changer)")},
            {"nom": "Propositions", "valeur": f"{NOMBRE} titres de {MAXI} caractères au plus, {ESSAIS} essais"},
            {"nom": "Attente", "valeur": f"{DELAI} secondes au plus par demande"},
        ],
        "allumer": [
            "Allumer le PC (ou le sortir de veille).",
            "Ouvrir Ollama depuis le menu Démarrer. Pas depuis un PowerShell administrateur : lancé de là, il ne lit "
            "pas tes réglages (dossier des modèles, écoute du réseau). L'icône du lama apparaît près de l'horloge.",
            "Attendre une dizaine de secondes, puis Connexion › IA du PC › Vérifier : la fiche passe à « Répond ».",
            "La première demande charge le modèle sur la carte graphique (10 à 30 secondes) ; il reste ensuite prêt 5 minutes.",
            "En fin de soirée : rien à faire. Ollama peut rester ouvert ; PC éteint, Gazette ne propose rien et on écrit les titres soi-même.",
        ],
        "une_fois": [
            {"texte": "Ollama écoute le réseau de la maison (PowerShell normal), puis quitter et rouvrir Ollama :",
             "commande": "setx OLLAMA_HOST 0.0.0.0"},
            {"texte": "Port 11434 ouvert au seul réseau local (PowerShell administrateur) :",
             "commande": "New-NetFirewallRule -DisplayName Ollama -Direction Inbound -Protocol TCP -LocalPort 11434 "
                         "-RemoteAddress LocalSubnet -Action Allow"},
            {"texte": "Si les modèles sont rangés ailleurs que dans le dossier habituel (PowerShell normal), puis "
                      "quitter et rouvrir Ollama :",
             "commande": 'setx OLLAMA_MODELS "X:\\chemin\\vers\\models"'},
            {"texte": "Le modèle utilisé :", "commande": f"ollama pull {MODELE}"},
            {"texte": "L'adresse du PC fixée dans la box (bail réservé), sinon elle peut changer et "
                      "GAZETTE_OLLAMA_URL ne la trouve plus.", "commande": ""},
        ],
        "pannes": [
            {"signe": "« PC injoignable » (connexion refusée, délai dépassé)",
             "faire": ["Le PC est-il allumé et sorti de veille ? Ollama est-il ouvert (icône près de l'horloge) ?",
                       f"Depuis un téléphone sur le Wi-Fi de la maison, ouvrir {adresse} : la page doit dire « Ollama is running ».",
                       "Rien ne s'affiche : comparer l'adresse du PC (première commande) à celle appelée ; si elle a changé, "
                       "corriger GAZETTE_OLLAMA_URL ou réserver l'adresse dans la box. Puis vérifier que la règle "
                       "de pare-feu « Ollama » existe et est active (seconde commande, True)."],
             "commandes": ["ipconfig | findstr IPv4", "Get-NetFirewallRule -DisplayName Ollama | Select-Object DisplayName, Enabled"]},
            {"signe": f"« PC joignable, mais le modèle {MODELE} n'y est pas »",
             "faire": ["Ollama lit sans doute un autre dossier de modèles. La première commande montre celui lu au démarrage.",
                       "Mauvais dossier : quitter Ollama (clic droit sur l'icône › Quit) et le rouvrir depuis le menu Démarrer. "
                       "S'il reste faux : Settings d'Ollama › Model location, ou OLLAMA_MODELS (voir « Installation »).",
                       f"La deuxième doit lister {MODELE} ; s'il manque vraiment : « ollama pull {MODELE} »."],
             "commandes": [f"Select-String -Path {journal} -Pattern \"OLLAMA_MODELS:[^ ]*\" | Select-Object -Last 1",
                           '$env:OLLAMA_HOST="127.0.0.1"; ollama list']},
            {"signe": "Dans le terminal, « ollama list » répond « connexion refusée »",
             "faire": ["Avec OLLAMA_HOST=0.0.0.0, la commande cherche Ollama à une adresse qui ne lui convient pas : taper "
                       "d'abord la première ligne dans ce terminal.",
                       "Si l'erreur reste, Ollama n'est pas lancé : la seconde commande ne montre aucun « ollama »."],
             "commandes": ['$env:OLLAMA_HOST="127.0.0.1"', "Get-Process ollama* | Select-Object Name, Id"]},
            {"signe": "Ollama se ferme tout seul après son ouverture",
             "faire": ["La fin du journal dit pourquoi : disque des modèles absent, dossier refusé, carte graphique…",
                       "Il démarre bien quand on y lit « Listening on [::]:11434 »."],
             "commandes": [f"Get-Content {journal} -Tail 15"]},
            {"signe": "Très lent (plus d'une minute)",
             "faire": ["Si le journal dit « AMD driver is too old », Ollama passe par Vulkan, plus lent : mettre à jour le "
                       "pilote AMD (Adrenalin), puis rouvrir Ollama.",
                       f"Gazette attend {DELAI} secondes au plus ; au-delà, elle abandonne et le dit."],
             "commandes": [f"Select-String -Path {journal} -Pattern \"inference compute|driver\" | Select-Object -Last 2"]},
            {"signe": "Aucun titre proposé, ou trop peu",
             "faire": [f"Le code écarte les titres trop longs (plus de {MAXI} caractères), en anglais, moqueurs sur le physique "
                       f"ou déjà parus, et redemande {ESSAIS} fois. Relancer, ou écrire le titre soi-même : la légende de "
                       "gabarit reste toujours."],
             "commandes": []},
        ],
        # 0.29 : textes que l'ancien écran Connexion écrivait lui-même autour du guide (fiche commune du socle 0.11.0)
        "terminal": "Les commandes se tapent dans PowerShell sur le PC (menu Démarrer › PowerShell).",
        "note": "Dans la stack : GAZETTE_OLLAMA_URL = adresse du PC et port 11434 ; GAZETTE_OLLAMA_MODELE pour changer "
                "de modèle (facultatif).",
    }


INTERDITS = re.compile(r"\b(je ne peux|désolé|en tant qu|as an ai|sorry|i can)\b", re.I)
ANGLAIS = re.compile(r"\b(the|and|with|her|his|is|of|you)\b", re.I)
# 0.18.1 : aucune moquerie du physique. 0.18.2 : les allusions sexuelles sont permises (choix de Julien du 17/11) :
# le filtre n'écarte plus que les moqueries sur l'apparence.
CORPS = re.compile(r"\b(obèse|grosse|maigrichon\w*|moche|laide?s?|bourrelets?|boudin|thon)\b", re.I)

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


SYSTEME = ("Tu es le rédacteur en chef d'un tabloïd français déjanté, entre Voici, Closer et Le Gorafi. Tes titres font "
           "rire : exagération dramatique, faux scoop, jeux de mots, sous-entendus, vocabulaire de presse people (« EXCLUSIF », "
           "« les images choc », « la vérité éclate », « elle sort du silence », « scandale », « révélations »). Tu taquines un "
           "proche avec affection et second degré : jamais d'humiliation, aucune moquerie du physique, rien de vulgaire, "
           "aucune accusation grave (drogue, crime, infidélité). Tu écris en français, sans anglicisme.")

EXEMPLES = [  # description de l'hôte → titre (0.9.6 : le modèle imite le ton, pas le contenu)
    ("Marc endormi sur le canapé", "Marc et le canapé : la liaison secrète enfin révélée !"),
    ("Sophie fait griller des saucisses au barbecue", "Barbecue : Sophie sort les pinces, les saucisses tremblent"),
    ("Paul en pyjama le matin dans la cuisine", "Paul surpris en tenue légère : la photo qui choque"),
    ("Léa lève son verre de vin en riant", "Léa et le rosé : « Ce n'est qu'un ami », jure-t-elle"),
    ("Tom fait un selfie devant la tour Eiffel", "Tom à Paris : il ose le cliché le plus attendu de l'année"),
]


def _feuilleton(deja: list[str]) -> str:
    if not deja:
        return ""
    return ("Déjà parus dans les numéros précédents (ne les reprends pas mot pour mot ; un clin d'œil façon feuilleton "
            "est bienvenu) :\n" + "\n".join(f"- {d}" for d in deja[:20]) + "\n\n")


def proche_de(texte: str, deja: list[str], seuil: float = 0.82) -> bool:
    """0.10 : trop proche d'un texte déjà imprimé (casse et ponctuation ignorées)."""
    t = re.sub(r"\W+", " ", texte.casefold()).strip()
    return any(difflib.SequenceMatcher(None, t, re.sub(r"\W+", " ", d.casefold()).strip()).ratio() >= seuil for d in deja)


def texte_contexte(ctx: dict | None) -> str:
    """0.12 : « album « Noël 2023 » ; avec Bastien, Léa » — ce qu'Immich dit d'une photo, pour l'IA (jamais imprimé)."""
    ctx = ctx or {}
    morceaux = []
    if ctx.get("albums"):
        morceaux.append("album " + ", ".join(f"« {a} »" for a in ctx["albums"]))
    sur = [x for x in ctx.get("sur_photo") or [] if x]
    if sur:                                    # 0.24.2 : sur la photo elle-même, avec l'invité
        morceaux.append("sur la photo avec l'invité : " + ", ".join(sur))
    autres = [x for x in ctx.get("personnes") or [] if x and x not in sur]
    if autres:
        morceaux.append(("autres personnes de l'album : " if sur else "avec ") + ", ".join(autres))
    return " ; ".join(morceaux)


def _prenoms_permis(prenom: str, ctx_personnes: list[str]) -> str:
    autres = [x for x in ctx_personnes if x and x.casefold() != (prenom or "").casefold()]
    return (f"aucun autre prénom que {prenom}" + (f" et ceux des personnes citées ({', '.join(autres)})" if autres else ""))


def consigne(description: str, sorte: str, genre: str, prenom: str, deja: list[str] | None = None,
             contexte: dict | None = None, fiche: str = "") -> str:
    accord = {"femme": f"{prenom} est une femme (accorde au féminin)", "homme": f"{prenom} est un homme (accorde au masculin)"}.get(
        genre, f"le genre de {prenom} est inconnu : formule sans accord féminin ni masculin, sans « il » ni « elle »")
    quoi = (f"le GROS TITRE de la une, qui annonce le retour de {prenom} chez nous" if sorte == "une"
            else "la LÉGENDE choc d'une photo volée")
    exemples = "\n".join(f"- « {d} » → {t}" for d, t in EXEMPLES)
    return (f"Exemples du ton voulu (description → titre) :\n{exemples}\n\n" + _feuilleton(deja or []) +
            f"Écris {NOMBRE} propositions pour {quoi}. {accord}.\n"
            + (f"Ce que montre la photo, d'après l'hôte : « {description} »\n" if description else "")
            + (f"D'après la photothèque : {texte_contexte(contexte)} (le nom de l'album dit l'occasion ; les personnes "
               "peuvent devenir complices, témoins ou rivaux)\n" if texte_contexte(contexte) else "")
            + (f"Au moins trois propositions mettent en scène {prenom} avec une des personnes sur la photo "
               f"({', '.join((contexte or {}).get('sur_photo') or [])}), en la nommant.\n"
               if (contexte or {}).get("sur_photo") else "")
            + (f"{fiche}\n" if fiche else "")                  # 0.23 : pépites tirées de la fiche complète, ton souhaité
            + f"Ne décris pas la photo : transforme-la en scandale ou en faux scoop. Cinq angles différents. "
            f"{MAXI} caractères au plus chacune ; n'invente aucun fait grave ; "
            f"{_prenoms_permis(prenom, (contexte or {}).get('personnes') or [])} ; "
            "pas de guillemets autour du titre, pas d'emoji.\n"
            f"Réponds seulement par les {NOMBRE} propositions, une par ligne, numérotées 1. à {NOMBRE}.")


MAXI_RUMEUR = 130       # 0.9.7 : une rumeur loufoque de la page 3
NOMBRE_RUMEURS = 8


def consigne_rumeurs(indices: str, genre: str, prenom: str, photos: list[str], deja: list[str] | None = None,
                     personnes: list[str] | None = None, fiche: str = "") -> str:
    accord = {"femme": f"{prenom} est une femme (accorde au féminin)", "homme": f"{prenom} est un homme (accorde au masculin)"}.get(
        genre, f"le genre de {prenom} est inconnu : formule sans accord féminin ni masculin, sans « il » ni « elle »")
    vu = "; ".join(p for p in photos if p)[:600]
    return ("Exemples du ton voulu :\n"
            "- Selon nos informations, Marc aurait tenté d'adopter un rond-point en Lot-et-Garonne.\n"
            "- Des voisins affirment que Sophie parle aux tomates du jardin, et qu'elles répondent.\n"
            "- Exclusif : Paul détiendrait le record départemental de siestes en position assise.\n\n" + _feuilleton(deja or [])
            + f"Écris {NOMBRE_RUMEURS} rumeurs LOUFOQUES et totalement inventées sur {prenom}, pour la rubrique "
            f"« Les rumeurs de la rédaction » d'un faux journal à scandale offert par ses hôtes. {accord}.\n"
            + (f"Ce que les hôtes savent de {prenom} : « {indices} »\n" if indices else "")
            + (f"Ce que montrent les photos du journal : {vu}\n" if vu else "")
            + (f"{fiche}\n" if fiche else "")                  # 0.23 : fiche complète
            + "Absurde, drôle et affectueux, style « Selon nos sources… », « Il se murmure que… », « Exclusif : … » ; "
              "jamais méchant, aucune moquerie du physique, rien de grave (santé, argent, couple, crime), rien de vulgaire. "
              f"{MAXI_RUMEUR} caractères au plus chacune, une seule phrase, {_prenoms_permis(prenom, personnes or [])}.\n"
              f"Réponds seulement par les {NOMBRE_RUMEURS} rumeurs, une par ligne, numérotées.")


NUMERO = re.compile(r"^\s*(\d+\s*[°º]?\s*[.)\-:–—/]+|\d+\s*[°º]|[-•*–—])\s*")     # 0.18.1 : « 1°) » aussi
# 0.14.1 : chiffres en émoji (« 1️⃣ », vus chez Julien le 17/11) et autres émojis, interdits par la consigne
EMOJI = re.compile("[0-9#*]\ufe0f?\u20e3|[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\ufe0f\u200d]")


def sans_emoji(texte: str) -> str:
    return " ".join(EMOJI.sub(" ", texte or "").split())


def sans_numero(texte: str) -> str:
    """0.9.8 : « 2 - Il se murmure… », « 3) … », « - … » → le texte seul (le modèle numérote à sa façon).
    0.14.1 : « 1️⃣ … » aussi, et plus aucun émoji."""
    t = sans_emoji(texte)
    return NUMERO.sub("", t, count=1).strip()


MAXI_LETTRE, MAXI_REPONSE, MAXI_HOROSCOPE = 400, 200, 240    # 0.11 : page 4 (0.11.2 : plus de marge, Julien raccourcit)
REFUS = re.compile(r"^\W*(je ne peux pas (écrire|répondre|aider|créer|produire)|désolé, (je|mais)|en tant qu|as an ai|sorry|i can)", re.I)
NOMBRE_LETTRES, NOMBRE_HOROSCOPES = 4, 3


def _accord(genre: str, prenom: str) -> str:
    return {"femme": f"{prenom} est une femme (accorde au féminin)", "homme": f"{prenom} est un homme (accorde au masculin)"}.get(
        genre, f"le genre de {prenom} est inconnu : formule sans accord féminin ni masculin, sans « il » ni « elle »")


def consigne_courrier(indices: str, genre: str, prenom: str, deja: list[str] | None = None, fiche: str = "") -> str:
    """0.11.1 : format à étiquettes (Lettre / Signature / Réponse), mieux suivi par les petits modèles que « ::: »."""
    return ("Exemple du ton et du format voulus :\n"
            "Lettre : Depuis que Marc est reparti, mon chien refuse de manger : il réclame ses imitations de mouette. Que faire ?\n"
            "Signature : Un voisin inquiet\n"
            "Réponse : La rédaction conseille de prolonger le séjour, pour le bien du chien.\n\n"
            + _feuilleton(deja or [])
            + f"Écris {NOMBRE_LETTRES} fausses lettres de lecteurs, drôles et affectueuses, pour la rubrique « Courrier des "
              f"lecteurs » d'un faux journal à scandale sur {prenom}, offert par ses hôtes. {_accord(genre, prenom)}.\n"
            + (f"Ce que les hôtes savent de {prenom} : « {indices} »\n" if indices else "")
            + (f"{fiche}\n" if fiche else "")                  # 0.23 : fiche complète
            + "Chaque lettre vient d'un correspondant anonyme et loufoque (« Un voisin inquiet », « Une tomate du jardin », "
              "« Le canapé du salon »…) et reçoit une réponse courte et piquante de la rédaction. Jamais méchant, aucune "
              f"moquerie du physique (les allusions coquines sont permises, avec esprit), rien de grave, aucun autre prénom que {prenom}.\n"
              "Pour chaque lettre, exactement trois lignes : « Lettre : … » (deux phrases au plus), « Signature : … », "
              "« Réponse : … » (une phrase). Une ligne vide entre deux lettres. Rien d'autre.")


def consigne_horoscope(signe_: str, indices: str, genre: str, prenom: str, deja: list[str] | None = None,
                       evenement: str = "", avant: list[str] | None = None, fiche: str = "") -> str:
    """0.15 : `evenement` — l'événement du séjour qui arrive (« soirée Eurovision, dort à la maison pour ne pas rentrer
    tard ») : chaque horoscope brode dessus. `avant` — les événements des séjours précédents, pour un clin d'œil."""
    # 0.18.1 : exemples sur un événement imaginaire (un concours de pétanque), et consigne de ne rien leur emprunter :
    # l'IA recopiait « soirée Eurovision » des exemples dans un séjour qui n'avait rien à voir (vu chez Julien le 17/11)
    exemple_ev = ("Exemples de broderie, pour un tout autre événement (un concours de pétanque) — n'en reprends AUCUN mot, "
                  "ni la pétanque : « Mars aligne vos boules : victoire au cochonnet, mais défaite au pastis. » ; "
                  "« Pluton percute votre signe vers 2 h du matin : migraine carabinée garantie au petit-déjeuner. »\n\n") if evenement else ""
    return ("Exemple du ton voulu : « Vénus s'installe dans votre chambre d'amis : évitez les décisions importantes avant "
            "le deuxième café. Chiffre de chance : le nombre de croissants restants. »\n\n" + exemple_ev + _feuilleton(deja or [])
            + f"Écris {NOMBRE_HOROSCOPES} horoscopes loufoques pour {prenom}, signe {signe_ or 'inconnu'}, pendant son "
              f"séjour chez ses hôtes, pour un faux journal à scandale. {_accord(genre, prenom)}.\n"
            + (f"Ce que les hôtes savent de {prenom} : « {indices} »\n" if indices else "")
            + (f"{fiche}\n" if fiche else "")                  # 0.23 : fiche complète
            + (f"Ce séjour est lié à un événement, et à lui seul : « {evenement} ». Chaque horoscope brode dessus "
               "(prédictions loufoques sur cet événement, ses suites, le lendemain), chacun sous un angle différent ; "
               "n'invente aucun autre événement.\n" if evenement else "")
            + (f"Séjours précédents de {prenom} : {' ; '.join(avant)} (un clin d'œil est permis, sans s'y attarder).\n"
               if avant else "")
            + "Style horoscope de magazine (planètes, chiffre ou couleur de chance), absurde et affectueux, jamais méchant, "
              f"rien de grave (santé, argent, couple), aucune moquerie du physique. {MAXI_HOROSCOPE} caractères au plus chacun, sur une seule ligne, "
              "sans répéter le nom du signe. Un horoscope par ligne, numérotés.")


# 0.24.2 : « il » impersonnel (« il faut », « il y a »…) ne dit rien du genre de la personne
IMPERSONNEL = r"(?:faut|fallait|faudra|faudrait|y|est temps|était une fois|paraît|parait|semble|semblerait|reste|restait|pleut|suffit|s'agit|vaut mieux|arrive|se peut)"
GENRE_DEVINE = re.compile(rf"\belles?\b|\bils\b|\bil\b(?!\s+{IMPERSONNEL}\b)", re.I)


def genre_devine(texte: str) -> bool:
    """Le texte parle de quelqu'un en « il » ou « elle » (genre inconnu : écarté). « il faut », « il y a »… ne comptent pas."""
    return bool(GENRE_DEVINE.search(texte or ""))


def phrases_qui_tiennent(texte: str, maxi: int) -> str:
    """0.24.2 : les phrases entières du début qui tiennent dans `maxi` caractères (le modèle écrit souvent trop long) ;
    vide si la première phrase seule dépasse."""
    texte = " ".join((texte or "").split())
    if len(texte) <= maxi:
        return texte
    garde = ""
    for ph in re.findall(r"[^.!?…]+[.!?…]+[»”\"']?\s*|[^.!?…]+$", texte):
        if len((garde + ph).strip()) > maxi:
            break
        garde += ph
    return garde.strip()


ETIQUETTES = {"lettre": "lettre", "signature": "signe", "signé": "signe", "signe": "signe", "de": "signe", "auteur": "signe",
              "réponse": "reponse", "reponse": "reponse", "la rédaction": "reponse", "rédaction": "reponse"}


def _propre(x: str) -> str:
    return " ".join(sans_numero(x.replace("**", "").replace("__", "")).strip().strip('"«»“”*').split())


def lettres(texte: str, genre: str, ecarts: dict | None = None) -> list[dict]:
    """0.11.1 : lit les lettres du modèle, sous la forme à étiquettes (« Lettre : … / Signature : … / Réponse : … »)
    ou sur une ligne (« lettre ::: signature ::: réponse », aussi avec « | »). Réponse facultative.
    0.24.2 : trop longues, lettre et réponse sont ramenées à leurs premières phrases entières (plus écartées) ; la
    signature est coupée au mot ; `ecarts` compte les raisons des lettres écartées (pour le message d'erreur)."""
    ecarts = ecarts if ecarts is not None else {}
    brutes, cour = [], {}
    for l in (texte or "").replace("\r", "").split("\n"):
        l = l.strip()
        if ":::" in l or l.count("|") >= 2:
            parts = [_propre(x) for x in re.split(r":::|\|", l)]
            parts = [x for x in parts if x]
            if len(parts) >= 2:
                brutes.append({"lettre": parts[0], "signe": parts[1], "reponse": parts[2] if len(parts) > 2 else ""})
            continue
        m = re.match(r"^\W*(lettre|signature|signé|signe|de|auteur|réponse|reponse|la rédaction|rédaction)\W*\s*[:：—-]\s*(.+)$",
                     sans_numero(l.replace("**", "")), re.I)
        if m:
            cle = ETIQUETTES[m.group(1).lower()]
            if cle == "lettre" and cour.get("lettre"):
                brutes.append(cour)
                cour = {}
            cour[cle] = _propre(m.group(2))
        elif not l and cour.get("lettre"):
            brutes.append(cour)
            cour = {}
    if cour.get("lettre"):
        brutes.append(cour)
    res = []
    for x in brutes:
        lettre = phrases_qui_tiennent(x.get("lettre", ""), MAXI_LETTRE)
        reponse = phrases_qui_tiennent(x.get("reponse", ""), MAXI_REPONSE)
        signe_ = x.get("signe", "") or "Un lecteur"
        if len(signe_) > 60:
            signe_ = signe_[:60].rsplit(" ", 1)[0].rstrip(",;:—-")
        if not lettre:
            ecarts["trop longue"] = ecarts.get("trop longue", 0) + 1
            continue
        # 0.11.2 : une lettre est écrite à la première personne (« Je ne peux plus dormir… ») : seul un vrai refus
        # en tête est écarté, plus « je ne peux » n'importe où
        if REFUS.search(lettre):
            ecarts["refus"] = ecarts.get("refus", 0) + 1
            continue
        if CORPS.search(f"{lettre} {signe_} {reponse}"):
            ecarts["physique"] = ecarts.get("physique", 0) + 1
            continue
        if not genre and genre_devine(lettre + " " + reponse):
            ecarts["genre inconnu"] = ecarts.get("genre inconnu", 0) + 1
            continue
        if lettre.casefold() not in {y["lettre"].casefold() for y in res}:
            res.append({"lettre": lettre, "signe": signe_, "reponse": reponse})
    return res


SYSTEME_GAZETTE = ("Tu es secrétaire de rédaction d'un journal français. Tu écris un français soigné et vivant. Tu ne gardes "
                   "que les faits du texte donné : jamais de date, de nom, de chiffre ou de détail ajouté. Tu ne commentes "
                   "pas ce que tu fais.")
ACTIONS_GAZETTE = ("titres", "raccourcir", "journal", "traduire", "mot")
SEPARATEUR = "---"


def consigne_gazette(action: str, texte: str, annee: int | None, signes: int | None, prenom: str, genre: str,
                     indices: str, chez: str, evenements: list[str] | None = None, fiche: str = "") -> tuple[str, int, int]:
    """(consigne, nombre de propositions, longueur maximale) pour une aide de la Gazette."""
    epoque = f"de {annee}" if annee else "de l'époque"
    sep = f"Sépare les versions par une ligne contenant seulement {SEPARATEUR}. Rien d'autre que les versions."
    if action == "titres":
        return (f"Texte d'un article :\n« {texte} »\n\nPropose 5 titres pour cet article, dans le style des journaux "
                f"{epoque} : courts, accrocheurs, 70 caractères au plus, sans rien ajouter au texte. "
                "Un titre par ligne, numérotés, sans guillemets.", 5, 70)
    if action == "raccourcir":
        n = max(60, int(signes or len(texte) * 0.75))
        return (f"Texte :\n« {texte} »\n\nÉcris 3 versions plus courtes de ce texte, de {n} caractères au plus chacune "
                f"(espaces compris), en gardant l'essentiel et les mêmes faits. {sep}", 3, n + 15)
    if action == "journal":
        n = int(len(texte) * 1.15) + 20
        return (f"Texte :\n« {texte} »\n\nRéécris ce texte en 3 versions façon article de presse {epoque} (ton, "
                f"vocabulaire et rythme d'un quotidien de l'époque), mêmes faits exactement, environ la même longueur "
                f"({n} caractères au plus). {sep}", 3, n)
    if action == "traduire":
        return (f"Texte en anglais :\n« {texte} »\n\nTraduis-le en français journalistique, en 2 versions, sans rien "
                f"ajouter ni retirer. {sep}", 2, int(len(texte) * 1.4) + 40)
    if action == "mot":
        accord = {"femme": "au féminin", "homme": "au masculin"}.get(genre, "sans accord de genre")
        return (f"Écris 3 versions du mot d'accueil des hôtes, imprimé en dernière page d'un journal offert à {prenom} "
                f"(né{'e' if genre == 'femme' else ''} en {annee or '…'}), qui vient dormir {chez or 'chez nous'}. "
                f"Accorde {accord}. Chaleureux, un brin d'humour, 3 à 5 phrases, 500 caractères au plus, au « vous ». "
                + (f"Ce qu'on sait de {prenom} : « {indices} ». " if indices else "")
                + (f"{fiche}. " if fiche else "")          # 0.23 : fiche complète
                # 0.17 : le mot s'appuie sur les événements racontés dans le journal (demande de Julien du 17/11)
                + ("Événements racontés dans ce journal (le monde à la naissance) : " + " ; ".join(evenements[:8])
                   + ". Fais un ou deux clins d'œil à ces événements, sans en inventer d'autres. " if evenements else "")
                + (f"Mot actuel, à améliorer : « {texte} ». " if texte else "")
                + "Ne signe pas (la signature est ajoutée). " + sep, 3, 520)
    if action == "droit":                # 0.18.1 : droit de réponse des hôtes, page 4 de La Récidive
        accord = {"femme": "au féminin", "homme": "au masculin"}.get(genre, "sans accord de genre")
        return (f"Écris 3 versions du « Droit de réponse » des hôtes, en dernière page d'un faux journal à scandale offert à "
                f"{prenom}, qui revient dormir {chez or 'chez eux'}. Les hôtes répondent aux « accusations » du journal avec "
                f"tendresse et second degré : ils assument tout et disent leur joie de la ou le revoir. Accorde {accord}. "
                "3 à 5 phrases, 500 caractères au plus, au « vous », aucune moquerie du physique. "
                + (f"Ce qu'on sait de {prenom} : « {indices} ». " if indices else "")
                + (f"{fiche}. " if fiche else "")          # 0.23 : fiche complète
                + ("Ce que raconte ce numéro : " + " ; ".join(evenements[:8]) + ". Fais un ou deux clins d'œil, sans rien inventer de grave. "
                   if evenements else "")
                + (f"Texte actuel, à améliorer : « {texte} ». " if texte else "")
                + "Ne signe pas (la signature est ajoutée). " + sep, 3, 520)
    if action == "legende":
        return (f"Photo d'un journal de {annee or 'l’époque'}, offert à {prenom} qui vient dormir chez ses hôtes.\n{texte}\n\n"
                f"Propose 5 légendes pour cette photo, dans le style sobre et un peu solennel de la presse {epoque} "
                "(« M. et Mme… », « Notre envoyée spéciale… », « photographiée lors de… »), affectueuses, sans moquerie, "
                f"90 caractères au plus chacune, sans rien inventer de grave ; aucun autre prénom que {prenom} et ceux "
                "cités. Une légende par ligne, numérotées, sans guillemets.", 5, 90)
    raise ValueError("Aide inconnue.")


def versions(brut: str, action: str, maxi: int) -> list[str]:
    """Découpe la réponse : une ligne par titre ; sinon des versions séparées par « --- » (ou des numéros)."""
    if action in ("titres", "legende"):
        return nettoyer(brut, "x", maxi)
    blocs = re.split(r"(?m)^\s*-{3,}\s*$", brut or "")
    if len(blocs) == 1:                                  # pas de séparateur : versions numérotées « 1. … »
        blocs = re.split(r"(?m)^\s*(?:version\s*)?\d+\s*[.):\-–]\s*", brut or "", flags=re.I)
    res = []
    for b in blocs:
        b = re.sub(r"(?im)^\s*(version\s*\d+\s*[:.)-]?)\s*", "", b.replace("**", "")).strip().strip('"«»“”').strip()
        b = "\n\n".join(" ".join(p.split()) for p in re.split(r"\n\s*\n", b) if p.strip())
        if len(b) >= 10 and len(b) <= maxi and not REFUS.search(b) and b.casefold() not in {x.casefold() for x in res}:
            res.append(b)
    return res


def nettoyer(texte: str, genre: str, maxi: int = MAXI) -> list[str]:
    """Les lignes qui tiennent : numéro retiré, sans refus, sans anglais, sans genre deviné, `maxi` caractères au plus."""
    res = []
    for l in (texte or "").splitlines():
        l = sans_numero(l).strip('"«»“”*').strip()
        l = re.sub(r"^.*?→\s*", "", l)            # 0.9.6 : le modèle recopie parfois « description → titre »
        l = re.sub(r"\s+", " ", l)
        if not l or len(l) > maxi or len(l) < 6 or INTERDITS.search(l) or CORPS.search(l) or len(ANGLAIS.findall(l)) >= 2:
            continue
        if not genre and genre_devine(l):
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

    def _demander(self, prompt: str, nombre: int, maxi: int, genre: str, deja: list[str] | None = None,
                  modele: str | None = None) -> list[str]:
        modele = modele or MODELE          # 0.22 : None = le modèle habituel (GAZETTE_OLLAMA_MODELE)
        props: list[str] = []
        for _ in range(ESSAIS):
            try:
                r = self._lire("/api/generate", {"model": modele, "prompt": prompt, "system": SYSTEME, "stream": False,
                                                 "options": {"temperature": 1.05, "top_p": 0.95, "repeat_penalty": 1.15,
                                                             "num_predict": 60 * nombre + 100}})
            except ErreurOllama as ex:
                self.erreur = ex.detail[:160]
                if ex.statut == 404:
                    raise RuntimeError(f"Le PC répond, mais Ollama n'y trouve pas le modèle {modele} ({ex.detail}). "
                                       f"Sur le PC : « ollama list » doit le montrer ; sinon « ollama pull {modele} », ou "
                                       "vérifier OLLAMA_MODELS puis quitter et rouvrir Ollama.") from ex
                raise RuntimeError(f"Ollama a refusé la demande ({ex.detail}).") from ex
            except Exception as ex:  # noqa: BLE001 — PC éteint, Ollama fermé, pare-feu
                self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
                raise RuntimeError(f"IA du PC injoignable ({self.erreur}). " + MARCHE) from ex
            self.erreur = ""
            for p in nettoyer(str((r or {}).get("response", "")), genre, maxi):
                if proche_de(p, deja or []):            # 0.10 : déjà imprimé dans un numéro précédent
                    continue
                if p.casefold() not in {x.casefold() for x in props}:
                    props.append(p)
            if len(props) >= nombre:
                break
        if not props:
            raise RuntimeError("L'IA n'a rien proposé d'utilisable : reformule, ou écris le texte toi-même.")
        return props[:nombre]

    def proposer(self, description: str, sorte: str = "photo", genre: str = "", prenom: str = "",
                 deja: list[str] | None = None, contexte: dict | None = None, modele: str | None = None,
                 fiche: str = "") -> list[str]:
        """Jusqu'à 5 titres. RuntimeError (avec la marche à suivre) si l'IA n'est pas joignable ou ne rend rien d'utile."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        description = " ".join((description or "").split())[:400]
        if len(description) < 3 and not texte_contexte(contexte):
            raise ValueError("Écris d'abord en quelques mots ce qu'on voit sur la photo.")
        if len(description) < 3:
            description = ""
        return self._demander(consigne(description, sorte, genre, prenom, deja, contexte, fiche), NOMBRE, MAXI, genre, deja, modele)

    def rumeurs(self, indices: str, genre: str = "", prenom: str = "", photos: list[str] | None = None,
                deja: list[str] | None = None, personnes: list[str] | None = None, modele: str | None = None,
                fiche: str = "") -> list[str]:
        """0.9.7 : jusqu'à 8 rumeurs loufoques (130 caractères au plus) pour la page 3. Indices facultatifs."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:1200]       # 0.19 : indices + livre d'or
        return self._demander(consigne_rumeurs(indices, genre, prenom, photos or [], deja, personnes, fiche), NOMBRE_RUMEURS, MAXI_RUMEUR,
                              genre, deja, modele)

    def _brut(self, prompt: str, nombre: int, modele: str | None = None) -> str:
        """Une demande, la réponse telle quelle (pour le courrier, qui a son propre format)."""
        try:
            r = self._lire("/api/generate", {"model": modele or MODELE, "prompt": prompt, "system": SYSTEME, "stream": False,
                                             "options": {"temperature": 1.05, "top_p": 0.95, "repeat_penalty": 1.15,
                                                         "num_predict": 130 * nombre + 100}})
        except ErreurOllama as ex:
            self.erreur = ex.detail[:160]
            raise RuntimeError(f"Ollama a refusé la demande ({ex.detail}).") from ex
        except Exception as ex:  # noqa: BLE001
            self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
            raise RuntimeError(f"IA du PC injoignable ({self.erreur}). " + MARCHE) from ex
        self.erreur = ""
        return str((r or {}).get("response", ""))

    def courrier(self, indices: str, genre: str = "", prenom: str = "", deja: list[str] | None = None,
                 modele: str | None = None, fiche: str = "") -> list[dict]:
        """0.11 : jusqu'à 4 fausses lettres de lecteurs avec la réponse de la rédaction (page 4)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:1200]       # 0.19 : indices + livre d'or
        res: list[dict] = []
        brut = ""
        ecarts: dict = {}
        for _ in range(ESSAIS):
            brut = self._brut(consigne_courrier(indices, genre, prenom, deja, fiche), NOMBRE_LETTRES, modele)
            for x in lettres(brut, genre, ecarts):
                if proche_de(x["lettre"], deja or []):
                    ecarts["déjà paru"] = ecarts.get("déjà paru", 0) + 1
                elif x["lettre"].casefold() not in {y["lettre"].casefold() for y in res}:
                    res.append(x)
            if len(res) >= NOMBRE_LETTRES:
                break
        if not res:
            extrait = " ".join(brut.split())[:220]
            pourquoi = ", ".join(f"{n} {k}" for k, n in ecarts.items()) or "aucune lettre lue dans sa réponse"
            raise RuntimeError("L'IA n'a rien proposé d'utilisable : relance, ou écris la lettre toi-même. "
                               f"Écartées : {pourquoi}. Début de sa réponse (pour Claude) : « {extrait or 'vide'} »")
        return res[:NOMBRE_LETTRES]

    def horoscope(self, signe_: str, indices: str, genre: str = "", prenom: str = "", deja: list[str] | None = None,
                  evenement: str = "", avant: list[str] | None = None, modele: str | None = None,
                  fiche: str = "") -> list[str]:
        """0.11 : jusqu'à 3 horoscopes loufoques du séjour (page 4)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:1200]       # 0.19 : indices + livre d'or
        evenement = " ".join((evenement or "").split())[:200]
        return self._demander(consigne_horoscope(signe_, indices, genre, prenom, deja, evenement, avant, fiche), NOMBRE_HOROSCOPES, MAXI_HOROSCOPE,
                              genre, deja, modele)

    # ------------------------------------------------------------ 0.12 : aides pour la Gazette classique
    def gazette(self, action: str, texte: str, annee: int | None = None, signes: int | None = None, prenom: str = "",
                genre: str = "", indices: str = "", chez: str = "", evenements: list[str] | None = None,
                modele: str | None = None, fiche: str = "") -> list[str]:
        """Propositions à choisir pour un bloc de la Gazette : « titres » (5), « raccourcir » (3, `signes` au plus),
        « journal » (3 réécritures façon presse de l'époque), « traduire » (2), « mot » (3 mots d'accueil). Mêmes faits
        que le texte donné : rien d'inventé (sauf le mot des hôtes, écrit d'après les indices)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        texte = (texte or "").strip()[:3000]
        if action not in ("mot", "legende", "droit") and len(texte) < 10:
            raise ValueError("Pas assez de texte dans ce bloc.")
        prompt, nombre, maxi = consigne_gazette(action, texte, annee, signes, prenom, genre, indices, chez, evenements,
                                               fiche if action in ("mot", "droit") else "")
        brut = ""
        for _ in range(ESSAIS):
            try:
                r = self._lire("/api/generate", {"model": modele or MODELE, "prompt": prompt, "system": SYSTEME_GAZETTE, "stream": False,
                                                 "options": {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1,
                                                             "num_predict": min(1600, max(300, (maxi // 2) * nombre))}})
            except ErreurOllama as ex:
                self.erreur = ex.detail[:160]
                raise RuntimeError(f"Ollama a refusé la demande ({ex.detail}).") from ex
            except Exception as ex:  # noqa: BLE001
                self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
                raise RuntimeError(f"IA du PC injoignable ({self.erreur}). " + MARCHE) from ex
            self.erreur = ""
            brut = str((r or {}).get("response", ""))
            props = versions(brut, action, maxi)
            if props:
                return props[:nombre]
        raise RuntimeError("L'IA n'a rien proposé d'utilisable : relance, ou écris le texte toi-même. "
                           f"Début de sa réponse (pour Claude) : « {' '.join(brut.split())[:200] or 'vide'} »")

    def sonder(self, second: str = "") -> dict:
        """0.22 : `second` (réglage « modele_second ») — dit aussi s'il est sur le PC (`second_present`), sans jamais
        changer `ok` : il ne sert qu'à « Autres propositions »."""
        if not self.actif:
            return {"ok": None, "detail": "pas réglée (GAZETTE_OLLAMA_URL vide) : pas de propositions de titres"}
        try:
            r = self._lire("/api/tags", None)
        except Exception as ex:  # noqa: BLE001
            self.erreur = str(ex).splitlines()[0][:160] or type(ex).__name__
            return {"ok": False, "detail": f"PC injoignable ({self.erreur})"}
        noms = [m.get("name", "") for m in (r or {}).get("models", [])]
        sec, en_plus = {}, ""
        if second:
            present = any(meme_modele(n, second) for n in noms)
            sec = {"second": second, "second_present": present}
            en_plus = (f" ; second modèle {second} présent" if present
                       else f" ; second modèle {second} absent (ollama pull {second}) : « Autres propositions » échouera")
        if not any(meme_modele(n, MODELE) for n in noms):
            return {"ok": False, "detail": f"PC joignable, mais le modèle {MODELE} n'y est pas (ollama pull {MODELE})" + en_plus, **sec}
        return {"ok": True, "detail": f"PC prêt ({MODELE})" + en_plus, **sec}

    def etat(self) -> dict:
        return {"regle": self.actif, "erreur": self.erreur, "modele": MODELE, "maxi": MAXI, "marche": MARCHE,
                "guide": guide(self.url)}
