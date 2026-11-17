"""0.9.1 : propositions de titres pour La Récidive par une IA locale (Ollama sur le PC de la maison).

Julien écrit en quelques mots ce qu'on voit sur une photo ; le modèle de texte (qwen2.5:7b) propose 5 titres façon
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

MODELE = os.environ.get("GAZETTE_OLLAMA_MODELE", "").strip() or "qwen2.5:7b"   # 0.9.6 : modèle changeable
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
    if ctx.get("personnes"):
        morceaux.append("avec " + ", ".join(ctx["personnes"]))
    return " ; ".join(morceaux)


def _prenoms_permis(prenom: str, ctx_personnes: list[str]) -> str:
    autres = [x for x in ctx_personnes if x and x.casefold() != (prenom or "").casefold()]
    return (f"aucun autre prénom que {prenom}" + (f" et ceux des personnes citées ({', '.join(autres)})" if autres else ""))


def consigne(description: str, sorte: str, genre: str, prenom: str, deja: list[str] | None = None,
             contexte: dict | None = None) -> str:
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
            + f"Ne décris pas la photo : transforme-la en scandale ou en faux scoop. Cinq angles différents. "
            f"{MAXI} caractères au plus chacune ; n'invente aucun fait grave ; "
            f"{_prenoms_permis(prenom, (contexte or {}).get('personnes') or [])} ; "
            "pas de guillemets autour du titre, pas d'emoji.\n"
            f"Réponds seulement par les {NOMBRE} propositions, une par ligne, numérotées 1. à {NOMBRE}.")


MAXI_RUMEUR = 130       # 0.9.7 : une rumeur loufoque de la page 3
NOMBRE_RUMEURS = 8


def consigne_rumeurs(indices: str, genre: str, prenom: str, photos: list[str], deja: list[str] | None = None,
                     personnes: list[str] | None = None) -> str:
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
            + "Absurde, drôle et affectueux, style « Selon nos sources… », « Il se murmure que… », « Exclusif : … » ; "
              "jamais méchant, aucune moquerie du physique, rien de grave (santé, argent, couple, crime), rien de vulgaire. "
              f"{MAXI_RUMEUR} caractères au plus chacune, une seule phrase, {_prenoms_permis(prenom, personnes or [])}.\n"
              f"Réponds seulement par les {NOMBRE_RUMEURS} rumeurs, une par ligne, numérotées.")


NUMERO = re.compile(r"^\s*(\d+\s*[.)\-:–—/]+|[-•*–—])\s*")
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


def consigne_courrier(indices: str, genre: str, prenom: str, deja: list[str] | None = None) -> str:
    """0.11.1 : format à étiquettes (Lettre / Signature / Réponse), mieux suivi par les petits modèles que « ::: »."""
    return ("Exemple du ton et du format voulus :\n"
            "Lettre : Depuis que Marc est reparti, mon chat refuse de manger : il réclame ses imitations de mouette. Que faire ?\n"
            "Signature : Un voisin inquiet\n"
            "Réponse : La rédaction conseille de prolonger le séjour, pour le bien du chat.\n\n"
            + _feuilleton(deja or [])
            + f"Écris {NOMBRE_LETTRES} fausses lettres de lecteurs, drôles et affectueuses, pour la rubrique « Courrier des "
              f"lecteurs » d'un faux journal à scandale sur {prenom}, offert par ses hôtes. {_accord(genre, prenom)}.\n"
            + (f"Ce que les hôtes savent de {prenom} : « {indices} »\n" if indices else "")
            + "Chaque lettre vient d'un correspondant anonyme et loufoque (« Un voisin inquiet », « Une tomate du jardin », "
              "« Le canapé du salon »…) et reçoit une réponse courte et piquante de la rédaction. Jamais méchant, aucune "
              f"moquerie du physique, rien de grave ni de vulgaire, aucun autre prénom que {prenom}.\n"
              "Pour chaque lettre, exactement trois lignes : « Lettre : … » (deux phrases au plus), « Signature : … », "
              "« Réponse : … » (une phrase). Une ligne vide entre deux lettres. Rien d'autre.")


def consigne_horoscope(signe_: str, indices: str, genre: str, prenom: str, deja: list[str] | None = None) -> str:
    return ("Exemple du ton voulu : « Vénus s'installe dans votre chambre d'amis : évitez les décisions importantes avant "
            "le deuxième café. Chiffre de chance : le nombre de croissants restants. »\n\n" + _feuilleton(deja or [])
            + f"Écris {NOMBRE_HOROSCOPES} horoscopes loufoques pour {prenom}, signe {signe_ or 'inconnu'}, pendant son "
              f"séjour chez ses hôtes, pour un faux journal à scandale. {_accord(genre, prenom)}.\n"
            + (f"Ce que les hôtes savent de {prenom} : « {indices} »\n" if indices else "")
            + "Style horoscope de magazine (planètes, chiffre ou couleur de chance), absurde et affectueux, jamais méchant, "
              f"rien de grave (santé, argent, couple). {MAXI_HOROSCOPE} caractères au plus chacun, sur une seule ligne, "
              "sans répéter le nom du signe. Un horoscope par ligne, numérotés.")


ETIQUETTES = {"lettre": "lettre", "signature": "signe", "signé": "signe", "signe": "signe", "de": "signe", "auteur": "signe",
              "réponse": "reponse", "reponse": "reponse", "la rédaction": "reponse", "rédaction": "reponse"}


def _propre(x: str) -> str:
    return " ".join(sans_numero(x.replace("**", "").replace("__", "")).strip().strip('"«»“”*').split())


def lettres(texte: str, genre: str) -> list[dict]:
    """0.11.1 : lit les lettres du modèle, sous la forme à étiquettes (« Lettre : … / Signature : … / Réponse : … »)
    ou sur une ligne (« lettre ::: signature ::: réponse », aussi avec « | »). Réponse facultative ; trop longs écartés."""
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
        lettre, signe_, reponse = x.get("lettre", ""), x.get("signe", "") or "Un lecteur", x.get("reponse", "")
        if not lettre or len(lettre) > MAXI_LETTRE or len(reponse) > MAXI_REPONSE or len(signe_) > 60:
            continue
        # 0.11.2 : une lettre est écrite à la première personne (« Je ne peux plus dormir… ») : seul un vrai refus
        # en tête est écarté, plus « je ne peux » n'importe où
        if REFUS.search(lettre) or (not genre and re.search(r"\b(elle|il)\b", lettre + " " + reponse, re.I)):
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
                     indices: str, chez: str) -> tuple[str, int, int]:
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
                + (f"Mot actuel, à améliorer : « {texte} ». " if texte else "")
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
        if not l or len(l) > maxi or len(l) < 6 or INTERDITS.search(l) or len(ANGLAIS.findall(l)) >= 2:
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

    def _demander(self, prompt: str, nombre: int, maxi: int, genre: str, deja: list[str] | None = None) -> list[str]:
        props: list[str] = []
        for _ in range(ESSAIS):
            try:
                r = self._lire("/api/generate", {"model": MODELE, "prompt": prompt, "system": SYSTEME, "stream": False,
                                                 "options": {"temperature": 1.05, "top_p": 0.95, "repeat_penalty": 1.15,
                                                             "num_predict": 60 * nombre + 100}})
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
                 deja: list[str] | None = None, contexte: dict | None = None) -> list[str]:
        """Jusqu'à 5 titres. RuntimeError (avec la marche à suivre) si l'IA n'est pas joignable ou ne rend rien d'utile."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        description = " ".join((description or "").split())[:400]
        if len(description) < 3 and not texte_contexte(contexte):
            raise ValueError("Écris d'abord en quelques mots ce qu'on voit sur la photo.")
        if len(description) < 3:
            description = ""
        return self._demander(consigne(description, sorte, genre, prenom, deja, contexte), NOMBRE, MAXI, genre, deja)

    def rumeurs(self, indices: str, genre: str = "", prenom: str = "", photos: list[str] | None = None,
                deja: list[str] | None = None, personnes: list[str] | None = None) -> list[str]:
        """0.9.7 : jusqu'à 8 rumeurs loufoques (130 caractères au plus) pour la page 3. Indices facultatifs."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:400]
        return self._demander(consigne_rumeurs(indices, genre, prenom, photos or [], deja, personnes), NOMBRE_RUMEURS, MAXI_RUMEUR,
                              genre, deja)

    def _brut(self, prompt: str, nombre: int) -> str:
        """Une demande, la réponse telle quelle (pour le courrier, qui a son propre format)."""
        try:
            r = self._lire("/api/generate", {"model": MODELE, "prompt": prompt, "system": SYSTEME, "stream": False,
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

    def courrier(self, indices: str, genre: str = "", prenom: str = "", deja: list[str] | None = None) -> list[dict]:
        """0.11 : jusqu'à 4 fausses lettres de lecteurs avec la réponse de la rédaction (page 4)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:400]
        res: list[dict] = []
        brut = ""
        for _ in range(ESSAIS):
            brut = self._brut(consigne_courrier(indices, genre, prenom, deja), NOMBRE_LETTRES)
            for x in lettres(brut, genre):
                if not proche_de(x["lettre"], deja or []) and x["lettre"].casefold() not in {y["lettre"].casefold() for y in res}:
                    res.append(x)
            if len(res) >= NOMBRE_LETTRES:
                break
        if not res:
            extrait = " ".join(brut.split())[:220]
            raise RuntimeError("L'IA n'a rien proposé d'utilisable : relance, ou écris la lettre toi-même. "
                               f"Début de sa réponse (pour Claude) : « {extrait or 'vide'} »")
        return res[:NOMBRE_LETTRES]

    def horoscope(self, signe_: str, indices: str, genre: str = "", prenom: str = "", deja: list[str] | None = None) -> list[str]:
        """0.11 : jusqu'à 3 horoscopes loufoques du séjour (page 4)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        indices = " ".join((indices or "").split())[:400]
        return self._demander(consigne_horoscope(signe_, indices, genre, prenom, deja), NOMBRE_HOROSCOPES, MAXI_HOROSCOPE,
                              genre, deja)

    # ------------------------------------------------------------ 0.12 : aides pour la Gazette classique
    def gazette(self, action: str, texte: str, annee: int | None = None, signes: int | None = None, prenom: str = "",
                genre: str = "", indices: str = "", chez: str = "") -> list[str]:
        """Propositions à choisir pour un bloc de la Gazette : « titres » (5), « raccourcir » (3, `signes` au plus),
        « journal » (3 réécritures façon presse de l'époque), « traduire » (2), « mot » (3 mots d'accueil). Mêmes faits
        que le texte donné : rien d'inventé (sauf le mot des hôtes, écrit d'après les indices)."""
        if not self.actif:
            raise RuntimeError("IA pas réglée (GAZETTE_OLLAMA_URL vide). " + MARCHE)
        texte = (texte or "").strip()[:3000]
        if action not in ("mot", "legende") and len(texte) < 10:
            raise ValueError("Pas assez de texte dans ce bloc.")
        prompt, nombre, maxi = consigne_gazette(action, texte, annee, signes, prenom, genre, indices, chez)
        brut = ""
        for _ in range(ESSAIS):
            try:
                r = self._lire("/api/generate", {"model": MODELE, "prompt": prompt, "system": SYSTEME_GAZETTE, "stream": False,
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
