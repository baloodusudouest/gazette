"""0.23 : fiche complète d'une personne (carnet 2.33) — module pur `fiche.py` (tirage, sujets interdits, filtre de
sortie, rangement du vrac, pré-remplissage), puis l'API avec carnet et Sillage simulés (lecture, écriture pépite par
pépite avec 409, contact introuvable, carnet arrêté ou pas à jour) et l'IA (tirage envoyé, interdits jamais envoyés,
filtre sur toutes les personnes du numéro, « parues » à l'approbation). Personnes et détails inventés."""
import hashlib
import random
from datetime import date

import pytest

from app import fiche as F
from app import main
from app import ollama as O
from tests.carnet_simule import CarnetFiche
from tests.test_recidive import IMMICH_CAMILLE, _deux_sejours, ha, j, monter  # noqa: F401

# Empreinte de app/rubriques_journaux.json de carnet 2.33.0 : la copie de Gazette doit rester identique octet pour octet
EMPREINTE_RUBRIQUES = "2deff52a9d417927b80e234b1c5bd42fa238af84aa803eef9466838f92fbb51a"


def pp(i, rubrique="metier", texte=None, parue=None):
    return {"id": f"p{i}", "rubrique": rubrique, "texte": texte or f"détail numéro {i}", "le": "x", "source": "julien",
            "parue_le": parue, "interdit": rubrique == "interdits"}


# ---------------------------------------------------------------- module pur

def test_rubriques_identiques_a_carnet_et_valides():
    assert hashlib.sha256(F.FICHIER.read_bytes()).hexdigest() == EMPREINTE_RUBRIQUES
    d = F.charger_rubriques()
    assert sum(len(f["rubriques"]) for f in d["familles"]) == 39 and d["interdits"]["cle"] == "interdits"
    assert set(F.SUGGESTIONS) == F.CLES                                  # des exemples pour chaque rubrique
    assert all(3 <= len(v) <= 6 for v in F.SUGGESTIONS.values())
    r = F.rubriques_avec_suggestions()
    assert r["familles"][0]["rubriques"][0]["suggestions"] and r["interdits"]["suggestions"]


def test_rubriques_mal_ecrites_refusees(tmp_path):
    f = tmp_path / "r.json"
    f.write_text('{"familles": [{"cle": "a", "titre": "A", "rubriques": [{"cle": "Métier", "titre": "x"}]}]}', encoding="utf-8")
    with pytest.raises(ValueError):
        F.charger_rubriques(f)


def test_tirage_priorite_aux_non_parues():
    pepites = [pp(i) for i in range(4)] + [pp(10 + i, parue="2026-01-01") for i in range(6)]
    pepites += [pp(90, "interdits", "son divorce"), pp(91, "ton", "taquin")]
    for graine in range(30):
        t = F.tirer(pepites, random.Random(graine))
        assert 3 <= len(t) <= 5
        ids = [x["id"] for x in t]
        assert "p90" not in ids and "p91" not in ids                  # jamais d'interdit, le ton part à part
        assert all(x["id"] in {"p0", "p1", "p2", "p3"} for x in t[:min(4, len(t))])     # les jamais parues d'abord
    assert len(F.tirer([pp(1), pp(2)], random.Random(1))) == 2      # pas assez : ce qu'il y a
    assert F.tirer([pp(9, "interdits")]) == []


def test_pour_ia_sans_interdits_avec_ton():
    pepites = [pp(1, "plats-aimes", "adore la tarte aux prunes"), pp(2, "interdits", "son ancien patron"),
               pp(3, "ton", "taquin mais tendre")]
    texte = F.pour_ia("Camille", F.tirer(pepites, random.Random(2)), F.ton(pepites))
    assert "tarte aux prunes" in texte and "taquin mais tendre" in texte and "patron" not in texte
    assert F.interdits(pepites) == ["son ancien patron"]


def test_filtre_des_sujets_interdits():
    props = ["Camille parle enfin de son divorce", "Camille divorcée de son grille-pain", "Camille adopte un rond-point",
             {"lettre": "Mon patron est jaloux", "signe": "Un voisin", "reponse": "Courage"}]
    gardees, ecartees = F.filtrer(props, ["le divorce", "son patron"])
    assert gardees == ["Camille adopte un rond-point"] and ecartees == 3     # mot et prolongement, lettres comprises
    assert F.filtrer(props, ["avec elle"])[1] == 0                           # mots vides et mots courts ignorés
    assert F.filtrer(["Le Régime du roi"], ["régime"])[0] == []              # accents et casse ignorés


def test_ranger_la_ligne_vrac():
    assert F.ranger("Elle déteste les endives") == "plats-detestes"
    assert F.ranger("adore le fromage") == "plats-aimes"
    assert F.ranger("a peur des araignées") == "peurs"
    assert F.ranger("son chien s'appelle Biscotte") == "animaux"
    assert F.ranger("si c'était un animal, une loutre") == "si-c-etait"
    assert F.ranger("zzz qwerty") == "autre"


def test_preremplissage():
    connu = {"metier": "Infirmière — Clinique de Testville", "conjoint": ["Alex Exemple"], "enfants": [], "animaux": ["Biscotte"],
             "alimentation": {"plaisirs": ["chocolat noir"], "non_aimes": ["endives"], "allergies": [], "intolerances": []},
             "immich_id": "x"}
    parus = [{"le": "2025-06-01", "evenement": "soirée crêpes", "indices": "fan de pétanque. Chante faux"}]
    etapes = [{"nom": "Voyage en Islande", "annee": 2019, "photos": 30}]
    s = F.preremplir({"connu": connu, "pepites": [pp(1, "conjoint", "Alex Exemple")]}, parus, etapes)
    textes = {x["texte"]: x for x in s}
    assert "Infirmière — Clinique de Testville" in textes and textes["Biscotte"]["rubrique"] == "animaux"
    assert textes["chocolat noir"]["rubrique"] == "plats-aimes" and textes["endives"]["rubrique"] == "plats-detestes"
    assert "Alex Exemple" not in textes                                     # déjà une pépite
    assert textes["2025 : soirée crêpes"]["source"] == "recidive" and "fan de pétanque" in textes
    assert textes["Voyage en Islande (2019)"] == {"rubrique": "voyages", "texte": "Voyage en Islande (2019)",
                                                  "source": "sillage", "origine": "chemin de Sillage"}
    # carnet ≥ 2.33 donne ses suggestions : elles servent telles quelles (plus les étapes de Sillage)
    s = F.preremplir({"suggestions": [{"rubrique": "metier", "texte": "Infirmière", "source": "carnet"}], "pepites": []}, parus, etapes)
    assert [x["texte"] for x in s] == ["Infirmière", "Voyage en Islande (2019)"]


def test_jauge_et_paliers():
    assert F.jauge([pp(i) for i in range(4)]) == {"nombre": 4, "palier": "", "prochain": 5}
    assert F.jauge([pp(i) for i in range(15)] + [pp(99, "interdits")])["palier"] == "bien fournie"
    assert F.jauge([pp(i) for i in range(31)]) == {"nombre": 31, "palier": "inépuisable", "prochain": None}


def test_proche_pour_les_textes_retouches():
    assert F.proche("Selon nos sources, Camille parle aux ceps de vigne !", ["Selon nos sources, Camille parle aux ceps de vigne"])
    assert not F.proche("Rien à voir du tout", ["Selon nos sources, Camille parle aux ceps"])


# ---------------------------------------------------------------- API avec carnet et Sillage simulés

CAMILLE_PID = "pm-camille01"
PAUL_PID = "pm-paul00001"


def _carnet_liste(url, jeton):
    return [{"carnet_id": "C-1", "personne_id": CAMILLE_PID, "nom": "Camille Fabre", "nom_carnet": "Camille Fabre",
             "prenom": "Camille", "naissance": "1988-07-07", "jour": 7, "mois": 7, "annee": 1988, "genre": "femme",
             "immich_id": IMMICH_CAMILLE, "journaux": "ancien texte libre",
             "parus": [{"le": "2025-06-01", "evenement": "soirée crêpes", "indices": "fan de pétanque"}]},
            {"carnet_id": "C-2", "personne_id": PAUL_PID, "nom": "Paul Exemple", "nom_carnet": "Paul Exemple", "prenom": "Paul",
             "naissance": "1985-02-03", "jour": 3, "mois": 2, "annee": 1985, "genre": "homme"}]


@pytest.fixture()
def fiche_monter(monter):
    def faire(**kw):
        c = monter(**kw)
        main.ETAT["carnet"]._lire = _carnet_liste
        main.ETAT["carnet"].personnes(forcer=True)
        faux = CarnetFiche()
        faux.personnes[CAMILLE_PID] = {"pepites": [], "suggestions": [
            {"rubrique": "metier", "texte": "Infirmière", "source": "carnet"},
            {"rubrique": "sejours", "texte": "soirée crêpes (01/06/2025)", "source": "recidive"}],
            "connu": {"metier": "Infirmière", "conjoint": [], "enfants": [], "animaux": [],
                      "alimentation": {"allergies": [], "intolerances": [], "non_aimes": [], "plaisirs": []},
                      "immich_id": IMMICH_CAMILLE}}
        faux.personnes[PAUL_PID] = {"pepites": [], "connu": {}, "suggestions": []}
        main.ETAT["carnet"]._fiche = faux
        etapes = []
        main.ETAT["sillage"]._adresse = lambda: "http://sillage.test"
        main.ETAT["sillage"]._lire = lambda url, jeton, immich_id: (etapes.append(immich_id), {
            "contrat": 1, "etapes": [{"nom": "Voyage en Islande", "annee": 2019, "photos": 30}] if immich_id == IMMICH_CAMILLE else []})[1]
        return c, faux, etapes
    return faire


def _pid(c, nom="Camille Fabre"):
    return c.post("/api/personnes", json={"nom": nom, "naissance": "1988-07-07"}).json()["id"]


def test_lire_ecrire_la_fiche(fiche_monter):
    c, faux, etapes = fiche_monter()
    pid = _pid(c)
    d = c.get(f"/api/fiches/{pid}").json()
    assert d["etat"]["carnet"] == "ok" and d["etat"]["ecriture"] and d["pepites"] == []
    assert {s["texte"] for s in d["suggestions"]} == {"Infirmière", "soirée crêpes (01/06/2025)", "Voyage en Islande (2019)"}
    assert etapes == [IMMICH_CAMILLE] and d["sillage"]["etat"] == "ok" and d["jauge"]["nombre"] == 0
    assert len([r for f in d["rubriques"]["familles"] for r in f["rubriques"]]) == 39
    # Suggestion → pépite (rien n'est recopié sans ce geste)
    assert not faux.personnes[CAMILLE_PID]["pepites"]
    r = c.post(f"/api/fiches/{pid}/pepites", json={"rubrique": "metier", "texte": "Infirmière", "source": "carnet"}).json()
    assert r["pepite"]["rubrique"] == "metier" and r["pepite"]["source"] == "carnet"
    # Vrac : rangé par mots-clés, sans IA
    r = c.post(f"/api/fiches/{pid}/pepites", json={"rubrique": "vrac", "texte": "Elle a peur des pigeons"}).json()
    assert r["pepite"]["rubrique"] == "peurs"
    assert c.post("/api/fiches/ranger", json={"texte": "adore le fromage"}).json() == {"rubrique": "plats-aimes"}
    d = c.get(f"/api/fiches/{pid}").json()
    assert d["jauge"]["nombre"] == 2 and "Infirmière" not in {s["texte"] for s in d["suggestions"]}
    # Modifier avec le bon `le`, puis refus 409 avec un `le` périmé (modifiée ailleurs entre-temps)
    p = r["pepite"]
    m = c.put(f"/api/fiches/{pid}/pepites/{p['id']}", json={"le": p["le"], "rubrique": "interdits"}).json()["pepite"]
    assert m["interdit"] and m["rubrique"] == "interdits"
    r = c.put(f"/api/fiches/{pid}/pepites/{p['id']}", json={"le": p["le"], "texte": "autre chose"})
    assert r.status_code == 409 and "changé entre-temps" in r.json()["detail"]
    assert c.request("DELETE", f"/api/fiches/{pid}/pepites/{p['id']}", json={"le": p["le"]}).status_code == 409
    assert c.request("DELETE", f"/api/fiches/{pid}/pepites/{p['id']}", json={"le": m["le"]}).json() == {"ok": True}
    assert c.request("DELETE", f"/api/fiches/{pid}/pepites/{p['id']}", json={"le": m["le"]}).status_code == 404
    # Contrôles avant envoi
    assert c.post(f"/api/fiches/{pid}/pepites", json={"texte": "x" * 201}).status_code == 422
    assert c.post(f"/api/fiches/{pid}/pepites", json={"texte": "ok", "rubrique": "inconnue"}).status_code == 422
    assert c.put(f"/api/fiches/{pid}/pepites/pp-1", json={"texte": "sans le"}).status_code == 422


def test_contact_introuvable_rien_n_est_ecrit(fiche_monter):
    c, faux, _ = fiche_monter()
    pid = _pid(c, "Personne Inconnue")
    d = c.get(f"/api/fiches/{pid}").json()
    assert d["etat"]["carnet"] == "introuvable" and not d["etat"]["ecriture"] and "ne trouve pas" in d["etat"]["message"]
    assert c.post(f"/api/fiches/{pid}/pepites", json={"texte": "un détail"}).status_code == 404
    assert faux.appels == []                                              # rien demandé à carnet


def test_carnet_arrete_fiche_en_lecture_seule(fiche_monter):
    c, faux, _ = fiche_monter()
    pid = _pid(c)
    faux.pepite(CAMILLE_PID, "loisirs", "collectionne les magnets")
    assert c.get(f"/api/fiches/{pid}").json()["etat"]["ecriture"]
    faux.arrete = True
    d = c.get(f"/api/fiches/{pid}").json()
    assert d["etat"]["carnet"] == "injoignable" and not d["etat"]["ecriture"] and "lecture seule" in d["etat"]["message"]
    assert [p["texte"] for p in d["pepites"]] == ["collectionne les magnets"]      # la dernière fiche bien lue
    assert c.post(f"/api/fiches/{pid}/pepites", json={"texte": "un détail"}).status_code == 503
    # Jamais lue avant : rien à montrer, message clair
    autre = _pid(c, "Paul Exemple")
    d = c.get(f"/api/fiches/{autre}").json()
    assert d["etat"]["carnet"] == "injoignable" and d["pepites"] == [] and "injoignable" in d["etat"]["message"]


def test_carnet_pas_a_jour_la_gazette_marche_comme_avant(fiche_monter):
    c, faux, _ = fiche_monter()
    faux.ancien = True
    pid, r = _deux_sejours(c)
    d = c.get(f"/api/fiches/{pid}").json()
    assert d["etat"]["carnet"] == "ancien" and "2.33" in d["etat"]["message"]
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    e = c.get(f"/api/recidives/{rid}").json()
    assert e["indices_carnet"] == "ancien texte libre" and e["fiche_complete"] is False      # comme avant
    lire = _ollama_fixe("1. Selon nos sources, Camille parle aux tomates.\n2. Il se murmure que Camille dort debout.")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    assert c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": "fan de pétanque"}).status_code == 200
    assert "Détails de la fiche" not in lire.appels[-1]["prompt"]


LETTRE = ("Lettre : Depuis le départ de Camille, le hamac boude. Que faire ?\nSignature : Un jardin inquiet\n"
          "Réponse : La rédaction conseille un nouveau séjour.")


def _ollama_fixe(reponse):
    appels = []

    def lire(chemin, corps):
        appels.append(corps)
        if corps is None:
            return {"models": [{"name": "qwen2.5:7b"}]}
        return {"response": LETTRE if "Courrier des lecteurs" in corps["prompt"] else reponse}
    lire.appels = appels
    return lire


def test_ia_recoit_le_tirage_jamais_les_interdits(fiche_monter):
    c, faux, _ = fiche_monter()
    for t in ("adore la tarte aux prunes", "joue du ukulélé", "collectionne les magnets", "dort avec un bonnet",
              "imite les mouettes", "connaît tous les génériques"):
        faux.pepite(CAMILLE_PID, "loisirs", t)
    faux.pepite(CAMILLE_PID, "ton", "taquin mais tendre")
    faux.pepite(CAMILLE_PID, "interdits", "son ancien patron")
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    e = c.get(f"/api/recidives/{rid}").json()
    assert e["indices_carnet"] == "" and e["fiche_complete"] is True           # plus de texte libre dans la ligne
    lire = _ollama_fixe("1. Selon nos sources, Camille joue du ukulélé aux poules.\n2. Exclusif : Camille imite les mouettes au marché.")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    for route in ("rumeurs", "courrier", "horoscope", "mot"):
        c.post(f"/api/recidives/{rid}/{route}", json={"indices": "fan de pétanque"})
    c.post(f"/api/recidives/{rid}/proposer", json={"cible": "une", "description": "Camille sur un tracteur"})
    prompts = [x["prompt"] for x in lire.appels if x]
    assert len(prompts) >= 5
    for prompt in prompts:
        assert "Détails de la fiche de Camille" in prompt and "taquin mais tendre" in prompt
        assert "patron" not in prompt                                           # jamais envoyé à l'IA
        n = sum(t in prompt for t in ("tarte aux prunes", "ukulélé", "magnets", "bonnet", "mouettes", "génériques"))
        assert 3 <= n <= 5
    assert "fan de pétanque" in prompts[0]                                      # la ligne d'indices reste envoyée
    tirages = main.ETAT["base"].tirages("recidive", rid)
    assert {t["cible"] for t in tirages} == {"rumeurs", "courrier", "horoscope", "droit", "une"}
    assert all(t["personne"] == CAMILLE_PID and 3 <= len(t["pepites"]) <= 5 for t in tirages)


def test_filtre_interdits_d_un_autre_invite(fiche_monter):
    c, faux, _ = fiche_monter()
    faux.pepite(PAUL_PID, "interdits", "la pétanque")               # un sujet interdit de Paul, l'autre invité
    pid = _pid(c)
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)})
    r = ha(c, {"chambre": "ami", "noms": ["Camille Fabre", "Paul Exemple"], "du": j(10), "jusqu_au": j(12)}).json()
    rid = int(next(x for x in r["invites"] if x["nom"] == "Camille Fabre")["lien"].rsplit("/", 1)[1])
    lire = _ollama_fixe("1. Selon nos sources, Camille triche à la pétanque.\n2. Il se murmure que Camille parle aux tomates.")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    props = c.post(f"/api/recidives/{rid}/rumeurs", json={}).json()["propositions"]
    assert props == ["Il se murmure que Camille parle aux tomates."]
    # Tout est écarté : message « relance »
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_ollama_fixe("1. Camille champion de pétanque.\n2. La pétanque de Camille."))
    r = c.post(f"/api/recidives/{rid}/rumeurs", json={})
    assert r.status_code == 422 and r.json()["detail"] == "Propositions écartées par les sujets interdits, relance."


def test_approbation_marque_les_pepites_parues(fiche_monter):
    c, faux, _ = fiche_monter()
    for t in ("joue du ukulélé", "collectionne les magnets", "dort avec un bonnet", "imite les mouettes"):
        faux.pepite(CAMILLE_PID, "loisirs", t)
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_ollama_fixe(
        "1. Selon nos sources, Camille joue du ukulélé aux poules.\n2. Exclusif : Camille imite les mouettes."))
    props = c.post(f"/api/recidives/{rid}/rumeurs", json={}).json()["propositions"]
    tirage = main.ETAT["base"].tirages("recidive", rid)[-1]["pepites"]
    # Julien retouche un peu la rumeur choisie, puis approuve
    c.put(f"/api/recidives/{rid}", json={"rumeurs": [props[0] + " Incroyable !"]})
    rep = c.post(f"/api/recidives/{rid}/approuver").json()
    assert rep["ok"] and "notée(s) « parue »" in rep["fiche"]
    parues = {p["id"] for p in faux.personnes[CAMILLE_PID]["pepites"] if p["parue_le"] == date.today().isoformat()}
    assert parues == set(tirage)
    assert ("POST", f"/gazette/personnes/{CAMILLE_PID}/fiche/parues") in [(m, ch) for m, ch, _ in faux.appels]
    # Le tirage suivant préfère les pépites jamais parues
    f = main.ETAT["carnet"].fiche(CAMILLE_PID)
    restantes = {p["id"] for p in f["pepites"] if not p["parue_le"]}
    if restantes:
        assert set(x["id"] for x in F.tirer(f["pepites"], random.Random(3))[:len(restantes)]) == restantes


def test_mot_du_livret_tirage_sans_ancien_texte(fiche_monter):
    c, faux, _ = fiche_monter()
    for t in ("joue du ukulélé", "collectionne les magnets", "dort avec un bonnet"):
        faux.pepite(CAMILLE_PID, "loisirs", t)
    faux.pepite(CAMILLE_PID, "interdits", "son ancien patron")
    pid = _pid(c)
    lire = _ollama_fixe("Chère Camille, bienvenue chez nous, le ukulélé est accordé.\n---\nBienvenue Camille, votre patron n'est pas invité.")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    props = c.post(f"/api/livrets/{pid}/ia", json={"action": "mot", "texte": ""}).json()["propositions"]
    assert props == ["Chère Camille, bienvenue chez nous, le ukulélé est accordé."]          # filtre de sortie
    prompt = lire.appels[-1]["prompt"]
    assert "ukulélé" in prompt and "ancien texte libre" not in prompt and "patron" not in prompt
    main.ETAT["base"].maj_livret(pid, mot=props[0])
    assert "notée(s)" in main._marquer_parues("gazette", pid, [props[0]])
    assert all(p["parue_le"] for p in faux.personnes[CAMILLE_PID]["pepites"] if p["rubrique"] == "loisirs")


# ---------------------------------------------------------------- clients Sillage et carnet

def test_client_sillage():
    from app.sillage import Sillage
    appels = []
    lire = lambda url, jeton, immich_id: (appels.append((url, jeton, immich_id)), {
        "contrat": 1, "etapes": [{"nom": f"  Étape   {i} ", "annee": "2010", "photos": 70 - i} for i in range(70)]})[1]
    s = Sillage(lambda: "http://sillage.test/", "jeton-test", lire=lire)
    e = s.etapes("imm-1")
    assert len(e) == 60 and e[0] == {"nom": "Étape 0", "annee": 2010, "photos": 70}
    s.etapes("imm-1")
    assert appels == [("http://sillage.test", "jeton-test", "imm-1")]          # gardé 10 minutes
    assert Sillage(lambda: "", "j", lire=lire).etapes("imm-1") == []         # pas réglé : rien
    with pytest.raises(RuntimeError, match="contrat"):
        Sillage(lambda: "http://s", "j", lire=lambda *a: {"contrat": 2}).etapes("x")
    with pytest.raises(RuntimeError, match="injoignable"):
        Sillage(lambda: "http://s", "j", lire=lambda *a: (_ for _ in ()).throw(ConnectionError("refus"))).etapes("x")


def test_client_carnet_erreurs(tmp_path):
    from app.base import Base
    from app.carnet import Carnet, ErreurFiche
    reponses = {"statut": 401, "corps": {"detail": "Jeton refusé"}}
    c = Carnet("http://carnet", "j", Base(tmp_path / "g.db"), fiche=lambda *a: (reponses["statut"], reponses["corps"]))
    for statut, corps, attendu, ancien in ((401, {}, 401, False), (404, {"detail": "Not Found"}, 404, True),
                                           (404, {"detail": "Personne inconnue de carnet."}, 404, False),
                                           (409, {}, 409, False), (400, {"detail": "Pépite vide."}, 422, False),
                                           (500, {}, 503, False)):
        reponses.update(statut=statut, corps=corps)
        with pytest.raises(ErreurFiche) as ex:
            c.fiche("pm-1")
        assert (ex.value.statut, ex.value.ancien) == (attendu, ancien)
    assert not Carnet("", "", Base(tmp_path / "h.db")).actif
