"""0.25 : banque d'inspiration (import, tirage, exemples pour l'IA), mot des hôtes jamais répété, bouton IA.
Personnes inventées."""
from app import banque as B
from app import main
from app import ollama as O
from tests.test_recidive import _deux_sejours, _faux_ollama, ha, j, monter  # noqa: F401  (fixture)

FICHIER = """# Banque d'essai
# RUMEURS
- Selon nos informations, {prenom} aurait tenté d'adopter un rond-point.
1. D'après le facteur, {prenom} parlerait le langage des chèvres.
* « Un voisin l'affirme : {Prénom} collectionnerait les bouchons. »
- Selon nos informations, {PRENOM} aurait tenté d'adopter un rond-point !
- Trop court
- Une rumeur avec une {balise} inconnue pour {prenom}, voilà.
# HOROSCOPES
- Mercure entre dans votre valise : un pigeon vous apportera une excellente nouvelle.
# MOTS
- {salut}, les draps sont frais et les ragots sont prêts. Faites comme chez vous.
- {salut}, la maison a ciré son parquet pour vous, {prenom}. Bon séjour.
- {salut}, une troisième version du mot, pour avoir le choix. À tout à l'heure.
- {salut}, une quatrième version du mot des hôtes, toute différente. Bienvenue.
# TITRES
- {prenom} démasqué{e} au rayon fromages
- EXCLUSIF : {prenom} fuit avec la télécommande
- {prenom} et un titre beaucoup trop long pour tenir sur la une du journal
titre | {prenom} sème la panique au marché
# COURRIER DES LECTEURS
- Depuis le départ de {prenom}, mon chien boude et réclame ses imitations de mouette. Que faire ? ::: Un voisin inquiet ::: La rédaction conseille de prolonger le séjour.
- Lettre sans séparateur pour {prenom}, donc refusée par la lecture.
- {prenom} a emprunté mon arrosoir et le rend toujours plein de confettis. ::: Le jardin d'à côté
"""


def _rid(r):
    return int(r["invites"][0]["lien"].rsplit("/", 1)[1])


def _troisieme(c, pid, rid):
    """Un 3e séjour avec photos (Immich simulé n'en a plus : on reprend celles du 2e)."""
    ha(c, {"chambre": "bleue", "noms": ["Camille Fabre"], "du": j(20), "jusqu_au": j(22)})
    b = main.ETAT["base"]
    rid3 = next(x["id"] for x in b.recidives(pid) if x["id"] != rid)
    b.maj_recidive(rid3, photos=b.recidive(rid)["photos"], etat="a_relire")
    return rid3


# ---------------------------------------------------------------- lecture du fichier

def test_lecture_du_fichier():
    lus, ecarts = B.lire(FICHIER)
    assert len(lus["rumeur"]) == 3 and lus["rumeur"][2] == "Un voisin l'affirme : {prenom} collectionnerait les bouchons."
    assert len(lus["horoscope"]) == 1 and len(lus["mot"]) == 4
    assert lus["titre"] == ["{prenom} démasqué{e} au rayon fromages", "EXCLUSIF : {prenom} fuit avec la télécommande",
                            "{prenom} sème la panique au marché"]
    assert len(lus["courrier"]) == 2 and B.lettre(lus["courrier"][1])["reponse"] == ""
    assert ecarts == {"doublon dans le fichier": 1, "trop court": 1, "balise inconnue": 1, "trop long": 1,
                      "lettre sans « ::: »": 1}


def test_rendre():
    assert B.rendre("{prenom} démasqué{e}", "Lou", "femme", "") == "Lou démasquée"
    assert B.rendre("{prenom} démasqué{e}", "Paul", "homme", "") == "Paul démasqué"
    assert B.rendre("{prenom} démasqué{e}", "Lou", "", "") is None                  # genre inconnu : pas proposé
    assert B.rendre("{salut}, bienvenue {chez}. {il} est là.", "Lou", "femme", "à la maison") == \
        "Chère Lou, bienvenue à la maison. Elle est là."


def test_fichier_de_claude_s_importe_en_entier():
    import pathlib
    f = pathlib.Path(__file__).resolve().parents[1] / "banque" / "gazette-banque-claude.txt"
    if not f.exists():
        return
    lus, ecarts = B.lire(f.read_text())
    assert all(len(lus[k]) == 1000 for k in ("rumeur", "horoscope", "mot", "titre")) and not ecarts


# ---------------------------------------------------------------- import, état, export, vider

def test_import_puis_reimport_sans_doublon(monter):
    c = monter()
    r = c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"}).json()
    assert r["ajoutes"] == {"rumeur": 3, "horoscope": 1, "mot": 4, "titre": 3, "courrier": 2} and r["deja"] == 0
    r2 = c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"}).json()
    assert r2["ajoutes"] == {"rumeur": 0, "horoscope": 0, "mot": 0, "titre": 0, "courrier": 0} and r2["deja"] == 13
    assert c.get("/api/banque").json()["comptes"] == {"rumeur": 3, "horoscope": 1, "mot": 4, "titre": 3, "courrier": 2}
    exp = c.get("/api/banque/export").text
    assert "# RUMEURS" in exp
    assert sum(len(v) for v in B.lire(exp)[0].values()) == 13                      # l'export se réimporte
    assert c.delete("/api/banque?sorte=titre").json()["retires"] == 3
    assert c.delete("/api/banque").json()["comptes"] == {"rumeur": 0, "horoscope": 0, "mot": 0, "titre": 0, "courrier": 0}


def test_import_illisible(monter):
    c = monter()
    rep = c.post("/api/banque/import", json={"texte": "bonjour\nrien ici", "source": "x"})
    assert rep.status_code == 422 and "# RUMEURS" in rep.json()["detail"]


# ---------------------------------------------------------------- piocher dans la banque

def test_piocher_pour_la_recidive(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    assert c.post(f"/api/recidives/{rid}/banque", json={"sorte": "rumeur"}).status_code == 404       # banque vide
    c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"})
    props = c.post(f"/api/recidives/{rid}/banque", json={"sorte": "rumeur"}).json()["propositions"]
    assert len(props) == 3 and all("Camille" in t and "{" not in t for t in props)
    assert main.ETAT["base"].recidive(rid)["propositions_rumeurs"] == props
    titres = c.post(f"/api/recidives/{rid}/banque", json={"sorte": "titre", "cible": "une"}).json()["propositions"]
    assert "Camille démasquée au rayon fromages" in titres                         # genre « femme » dans carnet
    photo = main.ETAT["base"].recidive(rid)["photos"][0]["id"]
    c.post(f"/api/recidives/{rid}/banque", json={"sorte": "titre", "cible": photo})
    assert main.ETAT["base"].recidive(rid)["photos"][0]["propositions"]
    lettres = c.post(f"/api/recidives/{rid}/banque", json={"sorte": "courrier"}).json()["propositions"]   # 0.26
    assert len(lettres) == 2 and all(set(x) == {"lettre", "signe", "reponse"} and "Camille" in x["lettre"] for x in lettres)
    assert main.ETAT["base"].recidive(rid)["propositions_courrier"] == lettres
    assert c.post(f"/api/recidives/{rid}/banque", json={"sorte": "autre"}).status_code == 422


def test_piocher_un_mot_pour_la_gazette(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"})
    props = c.post(f"/api/livrets/{pid}/banque").json()["propositions"]
    assert len(props) == 3 and all(t.startswith("Chère Camille,") for t in props)


def test_exemples_de_la_banque_donnes_a_l_ia(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"})
    faux = _faux_ollama(["1. Selon nos sources, Camille parle aux ceps."])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": ""})
    prompt = faux.appels[-1][1]["prompt"]
    assert "tirés de notre banque" in prompt and "rond-point" in prompt and "{prenom}" not in prompt


# ---------------------------------------------------------------- mot des hôtes jamais deux fois

def test_mot_deja_paru_refuse_puis_remplace_par_la_banque(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    b = main.ETAT["base"]
    assert c.post(f"/api/recidives/{rid}/approuver").status_code == 200           # 1re Récidive, mot par défaut
    rid3 = _troisieme(c, pid, rid)
    ed = c.get(f"/api/recidives/{rid3}").json()["edition"]
    assert ed["mots_parus"] and ed["mot"] == ""                                    # banque vide : rien à proposer
    rep = c.post(f"/api/recidives/{rid3}/approuver")
    assert rep.status_code == 409 and "déjà paru (La Récidive N° 2)" in rep.json()["detail"]
    c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"})
    ed = c.get(f"/api/recidives/{rid3}").json()["edition"]
    assert ed["mot"].startswith("Chère Camille,")                                  # un mot de la banque, gardé
    assert c.get(f"/api/recidives/{rid3}").json()["edition"]["mot"] == ed["mot"]   # stable
    assert c.post(f"/api/recidives/{rid3}/approuver").status_code == 200
    assert b.recidive(rid3)["etat"] == "approuve"


def test_le_mot_paru_ne_revient_pas_de_la_banque(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    c.post("/api/banque/import", json={"texte": FICHIER, "source": "essai.txt"})
    mot_ = B.rendre(B.lire(FICHIER)[0]["mot"][0], "Camille", "femme", "à la maison")
    c.put(f"/api/recidives/{rid}", json={"mot": mot_})
    assert c.post(f"/api/recidives/{rid}/approuver").status_code == 200
    rid3 = _troisieme(c, pid, rid)
    for _ in range(5):
        props = c.post(f"/api/recidives/{rid3}/banque", json={"sorte": "mot"}).json()["propositions"]
        assert mot_ not in props


# ---------------------------------------------------------------- 0.25.1 : fichiers de ChatGPT et Gemini

def test_section_sans_diese_et_lignes_sans_puce():
    """Vu le 18/11 : « RUMEURS » seul, puis une rumeur par ligne, séparées de lignes vides."""
    lus, ecarts = B.lire("RUMEURS\nSelon le majordome, {prenom} aurait négocié le loyer d'un potager.\n\n"
                         "On murmure au marché qu'{prenom} aurait confondu un tracteur avec un lit.\n"
                         "Voici la suite :\nSouhaitez-vous d'autres rumeurs ?\n**Titres :**\n{prenom} démasqué{e} au marché\n")
    assert len(lus["rumeur"]) == 2 and lus["titre"] == ["{prenom} démasqué{e} au marché"] and not ecarts


def test_prenom_perdu_remis():
    """Vu le 18/11 : la balise a disparu, il reste un double espace."""
    lus, ecarts = B.lire("RUMEURS\n- Selon le comité des hérissons,  aurait négocié avec une brouette.\n"
                         "- Le club des limaces soupçonne  de préparer un championnat de lenteur.\n"
                         "- Une rumeur sans prénom ni trou pour le mettre, voilà.\n")
    assert lus["rumeur"] == ["Selon le comité des hérissons, {prenom} aurait négocié avec une brouette.",
                             "Le club des limaces soupçonne {prenom} de préparer un championnat de lenteur."]
    assert ecarts == {"sans {prenom}": 1}


def test_elision_devant_le_prenom():
    t = "On murmure au marché qu'{prenom} aurait confondu un tracteur avec un lit."
    assert B.rendre(t, "Paul", "homme", "") == "On murmure au marché que Paul aurait confondu un tracteur avec un lit."
    assert B.rendre(t, "Audrey", "femme", "") == "On murmure au marché qu'Audrey aurait confondu un tracteur avec un lit."
    assert B.rendre("Le chien de {prenom}", "Émile", "homme", "") == "Le chien d'Émile"
