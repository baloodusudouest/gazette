"""0.9 : La Récidive — règles (N°, fenêtre, choix des photos, décennies, accroche) et parcours par l'API avec un
Immich et un carnet simulés. Personnes et photos inventées."""
import random
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import journal, main
from app import recidive as R
from app.config import Config

MDP = "mot-de-passe-de-test"
JETON = "jeton-ha-de-test"
AUJ = date.today()


def j(n: int) -> str:
    return (AUJ + timedelta(days=n)).isoformat()


# ---------------------------------------------------------------- règles

def test_numero_et_precedent():
    assert R.numero([], "2026-12-01") == 1
    assert R.numero(["2026-03-01", "2026-12-01"], "2026-12-01") == 2
    assert R.numero(["2026-12-01"], "2026-12-01", avant=2) == 3
    sej = [{"du": "2026-03-01", "jusqu_au": "2026-03-04"}, {"du": "2026-12-01", "jusqu_au": "2026-12-03"}]
    assert R.precedent(sej, "2026-12-01") == {"du": "2026-03-01", "jusqu_au": "2026-03-04"}
    assert R.precedent(sej[1:], "2026-12-01", "2025-08-10") == {"du": "2025-08-10", "jusqu_au": ""}
    assert R.precedent(sej[1:], "2026-12-01") is None
    assert R.jours_absence({"du": "2026-03-01", "jusqu_au": "2026-03-04"}, "2026-03-14") == 10


def test_accroche_selon_le_genre():
    assert R.accroche("femme", "Camille") == "Elle est revenue, nous aussi"
    assert R.accroche("homme", "Paul") == "Il est revenu, nous aussi"
    assert R.accroche("", "Camille") == "Camille est de retour, nous aussi"
    assert R.mot_par_defaut("femme", "Camille").startswith("Chère Camille,")
    assert R.mot_par_defaut("autre", "Sam").startswith("Sam,")


def test_decennies_et_annees_variees():
    photos = [{"id": f"{an}-{k}", "date": f"{an}-06-0{k + 1}"} for an in (1995, 1996, 2004, 2012, 2013) for k in range(3)]
    pris = R.decennies(photos, 3, random.Random(1))
    assert len({p["date"][:3] for p in pris}) == 3            # trois décennies différentes
    pris = R.decennies(photos, 5, random.Random(2))
    assert len({p["date"][:4] for p in pris}) == 5            # cinq années différentes tant qu'il en reste


def test_choisir_recentes_puis_anciens_scandales():
    recentes = [{"id": f"r{i}", "date": f"2026-0{i}-01"} for i in range(1, 4)]
    scandales = [{"id": f"s{an}", "date": f"{an}-01-01"} for an in (1990, 2000, 2010, 2015, 2020)]
    c = R.choisir(recentes, scandales, publies={"s1990"}, graine=3)
    ids = [p["id"] for p in c["photos"]]
    assert ids[0] == "r3" and ids[:3] == ["r3", "r2", "r1"]         # la plus récente fait la une
    assert len(ids) == R.PLACES and "s1990" not in ids               # déjà publiée : écartée tant qu'il en reste
    assert all(p["ancien"] for p in c["photos"][3:])
    assert c["photos"][0]["legende"].startswith("Cliché du ")
    assert c["photos"][3]["legende"].endswith("ressorti pour l'occasion.")
    # Plus assez de photos jamais publiées : les déjà publiées reviennent
    c = R.choisir(recentes, scandales[:2], publies={"s1990", "s2000"})
    assert {"s1990", "s2000"} <= {p["id"] for p in c["photos"]}
    # Beaucoup de photos récentes : sept, réparties dans le temps, la plus récente gardée
    beaucoup = [{"id": f"b{i:02d}", "date": f"2026-01-{i:02d}"} for i in range(1, 29)]
    c = R.choisir(beaucoup, None, set())
    assert len(c["photos"]) == R.PLACES and c["photos"][0]["id"] == "b28" and not c["manque_scandale"]
    # Aucune photo récente : pas de Récidive
    assert R.choisir([], scandales, set())["photos"] == []
    # Tag absent et photos qui manquent : signalé
    c = R.choisir(recentes, None, set())
    assert c["tag_absent"] and c["manque_scandale"] and len(c["photos"]) == 3


# ---------------------------------------------------------------- Immich et carnet simulés

IMMICH_CAMILLE = "11111111-aaaa"


def _faux_immich(photos: dict, tags=True):
    appels = []

    def lire(methode, chemin, corps=None):
        appels.append((methode, chemin))
        if chemin == "/tags":
            return [{"id": "tag-scandale", "value": "Famille/Scandale"}] if tags else []
        if chemin == "/search/metadata":
            pid = corps["personIds"][0]
            items = []
            for a in photos.get(pid, []):
                if "tagIds" in corps:
                    if a.get("scandale"):
                        items.append(a)
                elif corps["takenAfter"][:10] <= a["date"] < corps["takenBefore"][:10]:
                    items.append(a)
            return {"assets": {"items": [{"id": a["id"], "localDateTime": a["date"] + "T12:00:00.000Z"} for a in items],
                               "nextPage": None}}
        if "/thumbnail" in chemin:
            return b"\xff\xd8\xff\xe0JPEG-" + chemin.encode()
        raise AssertionError(chemin)
    lire.appels = appels
    return lire


def _carnet(genre="femme", immich=IMMICH_CAMILLE):
    return lambda url, jeton: [{"carnet_id": "C-1", "nom": "Camille Fabre", "nom_carnet": "Camille Fabre", "prenom": "Camille",
                                "naissance": "1988-07-07", "jour": 7, "mois": 7, "annee": 1988, "genre": genre, "immich_id": immich}]


def _photos_camille():
    recentes = [{"id": f"aaaaaaaa-{i:04d}", "date": j(-30 + i * 8)} for i in range(3)]          # -30, -22, -14
    vieilles = [{"id": f"bbbbbbbb-{an}", "date": f"{an}-05-10", "scandale": True} for an in (1995, 1998, 2004, 2012, 2013)]
    return {IMMICH_CAMILLE: recentes + vieilles}


@pytest.fixture()
def monter(tmp_path):
    def faire(photos=None, tags=True, genre="femme", immich=True):
        main.ETAT.clear()
        main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                                  sources_actives=False, synchrone=True, jeton_ha=JETON,
                                  carnet_url="http://carnet", carnet_jeton="jeton")
        main.ETAT["carnet_lire"] = _carnet(genre)
        if immich:
            main.ETAT["immich_lire"] = _faux_immich(_photos_camille() if photos is None else photos, tags)
        c = TestClient(main.app)
        c.__enter__()
        b = main.ETAT["base"]
        journal.enregistrer(b, {**journal.charger(b), "signature": "Les hôtes de test", "chez": "à Testville"})
        assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
        return c
    yield faire
    main.ETAT.clear()


def ha(c, corps):
    return c.post("/ha/sejour", json=corps, headers={"Authorization": f"Bearer {JETON}"})


def _deux_sejours(c):
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    r1 = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)}).json()
    assert r1["invites"][0]["journal"] == "gazette"                      # premier séjour : la Gazette
    r2 = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(10), "jusqu_au": j(12)}).json()
    return pid, r2


def test_deuxieme_sejour_la_recidive(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    inv = r["invites"][0]
    assert inv["journal"] == "recidive" and inv["numero"] == 2 and inv["livret"] == "a_relire"
    rid = int(inv["lien"].rsplit("/", 1)[1])
    assert inv["lien"].endswith(f"/#/recidive/{rid}") and r["a_relire"] == ["Camille Fabre"]
    d = c.get(f"/api/recidives/{rid}").json()
    ed = d["edition"]
    assert ed["accroche"] == "Elle est revenue, nous aussi" and ed["genre"] == "femme"
    assert ed["precedent"] == {"du": j(-40), "jusqu_au": j(-38)}
    ids = [p["id"] for p in ed["photos"]]
    assert ids[0] == "aaaaaaaa-0002" and len(ids) == R.PLACES                # la plus récente en une, puis les archives
    assert sum(p["ancien"] for p in ed["photos"]) == 4 and ed["trouvees"] == 3
    assert d["edition"]["mot_defaut"].startswith("Chère Camille")
    # Aperçu : titre, accroche, N°, photos embarquées, aucune date de naissance
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert "La Récidive" in html and "Elle est revenue, nous aussi" in html and "N° 2" in html
    assert html.count("data:image/jpeg;base64,") == R.PLACES and "1988" not in html and "Anciens scandales" in html
    assert c.get(f"/api/recidives/{rid}/photos/{ids[0]}").content.startswith(b"\xff\xd8")
    assert c.get(f"/api/recidives/{rid}/photos/inconnue-0000").status_code == 404
    # À traiter et Home Assistant
    t = c.get("/api/a-traiter").json()
    assert [x["id"] for x in t["recidives"]] == [rid] and t["recidives"][0]["attendu"]
    assert t["relire"] == [] or not any(x["attendu"] for x in t["relire"])     # la Gazette n'est plus attendue
    etat = c.get("/ha/etat", headers={"Authorization": f"Bearer {JETON}"}).json()
    assert "Camille Fabre : La Récidive N° 2 à relire" in etat["liste"]
    # Livrets : le séjour à venir porte l'édition
    lv = c.get("/api/livrets").json()
    assert lv["sejours"][0]["invites"][0]["edition"]["id"] == rid and lv["recidives"][0]["numero"] == 2


def test_relecture_completer_approuver(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    une, retiree = ed["photos"][0]["id"], ed["photos"][1]["id"]
    corps = {"numero_main": 4, "accroche": "Camille est de retour", "mot": "Bienvenue.",
             "photos": [{"id": une, "legende": "Le regard qui en dit long."}, {"id": retiree, "retiree": True}]}
    assert c.put(f"/api/recidives/{rid}", json=corps).status_code == 200
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["numero_main"] == 4 and ed["photos"][0]["legende"] == "Le regard qui en dit long."
    assert c.put(f"/api/recidives/{rid}", json={"numero_main": 1}).status_code == 422
    # Compléter : la photo retirée ne revient pas, la légende écrite est gardée, la place libre est reprise
    c.post(f"/api/recidives/{rid}/preparer", json={"completer": True})
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    vues = [p for p in ed["photos"] if not p["retiree"]]
    assert retiree not in {p["id"] for p in vues} and any(p["id"] == retiree and p["retiree"] for p in ed["photos"])
    assert vues[0]["legende"] == "Le regard qui en dit long." and len(vues) == R.PLACES           # la 5e archive prend la place
    assert ed["accroche"] == "Camille est de retour" and ed["mot"] == "Bienvenue."
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert "N° 4" in html and "Le regard qui en dit long." in html
    # Approuver : les anciens scandales parus ne reviendront qu'après les autres
    assert c.post(f"/api/recidives/{rid}/approuver").status_code == 200
    parus = main.ETAT["base"].publies(pid)
    assert parus == {p["id"] for p in vues if p["ancien"]}
    # Une modification remet « à relire »
    assert c.put(f"/api/recidives/{rid}", json={"mot": "Autre mot."}).json()["etat"] == "a_relire"
    # Tout retirer est refusé
    tout = [{"id": p["id"], "retiree": True} for p in ed["photos"]]
    assert c.put(f"/api/recidives/{rid}", json={"photos": tout}).status_code == 409


def test_troisieme_sejour_archives_jamais_parues_d_abord(monter):
    photos = _photos_camille()
    photos[IMMICH_CAMILLE].append({"id": "aaaaaaaa-0099", "date": j(15)})        # prise entre le 2e et le 3e séjour
    c = monter(photos=photos)
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    c.post(f"/api/recidives/{rid}/approuver")
    parus = main.ETAT["base"].publies(pid)
    assert len(parus) == 4
    r3 = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(20), "jusqu_au": j(22)}).json()
    assert r3["invites"][0]["numero"] == 3
    ed = main.ETAT["base"].recidive_de(pid, j(20))
    assert ed["precedent"]["du"] == j(10) and ed["trouvees"] == 1 and ed["photos"][0]["id"] == "aaaaaaaa-0099"
    anciens = [p["id"] for p in ed["photos"] if p["ancien"]]
    jamais = ({f"bbbbbbbb-{an}" for an in (1995, 1998, 2004, 2012, 2013)} - parus).pop()
    assert jamais in anciens and len(anciens) == 5                   # la seule jamais parue, puis les déjà parues


def test_aucune_photo_repli_gazette(monter):
    c = monter(photos={IMMICH_CAMILLE: [{"id": "bbbbbbbb-1999", "date": "1999-01-01", "scandale": True}]})
    pid, r = _deux_sejours(c)
    assert r["invites"][0]["journal"] == "gazette" and r["invites"][0]["lien"].endswith(f"/#/livret/{pid}")
    assert main.ETAT["base"].recidives(pid)[0]["etat"] == "vide"
    assert c.get("/api/livrets").json()["sejours"][0]["invites"][0]["edition"] is None


def test_immich_pas_regle_la_gazette_sert(monter):
    c = monter(immich=False)
    pid, r = _deux_sejours(c)
    assert r["invites"][0]["journal"] == "gazette" and main.ETAT["base"].recidives() == []
    assert c.post("/api/connexion/verifier").json()["immich"]["ok"] is None


def test_sejours_d_avant_gazette(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    r = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(10), "jusqu_au": j(12)}).json()
    assert r["invites"][0]["journal"] == "gazette"
    # Venue deux fois avant Gazette, la dernière il y a 40 jours : c'est le N° 3
    assert c.put(f"/api/personnes/{pid}", json={"sejours_avant": 2, "dernier_avant": j(-40)}).status_code == 200
    r = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(10), "jusqu_au": j(12)}).json()
    assert r["invites"][0]["journal"] == "recidive" and r["invites"][0]["numero"] == 3
    ed = main.ETAT["base"].recidives(pid)[0]
    assert ed["precedent"] == {"du": j(-40), "jusqu_au": ""} and ed["trouvees"] == 3
    assert c.put(f"/api/personnes/{pid}", json={"dernier_avant": j(5)}).status_code == 422
    assert c.put(f"/api/personnes/{pid}", json={"sejours_avant": -1}).status_code == 422
    # Remis à zéro : premier séjour de nouveau, l'édition non approuvée est retirée
    c.put(f"/api/personnes/{pid}", json={"sejours_avant": 0, "dernier_avant": ""})
    assert main.ETAT["base"].recidives(pid) == []


def test_tag_absent_et_genre_inconnu(monter):
    c = monter(tags=False, genre="")
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["accroche"] == "Camille est de retour, nous aussi" and len(ed["photos"]) == 3
    t = c.get("/api/a-traiter").json()
    assert t["scandales"][0]["tag_absent"] and t["scandales"][0]["id"] == rid
    c.post("/api/a-traiter/ignorer", json={"sorte": "scandale", "cle": str(pid)})
    assert c.get("/api/a-traiter").json()["scandales"] == []


def test_personne_sans_immich_dans_carnet(monter, tmp_path):
    c = monter()
    main.ETAT["carnet"]._lire = _carnet(immich="")
    main.ETAT["carnet"]._liste = None
    pid, r = _deux_sejours(c)
    t = c.get("/api/a-traiter").json()
    assert any("Pas de personne d'Immich" in x["erreur"] and x.get("recidive") for x in t["erreurs"])


def test_chambre_liberee_garde_le_sejour_commence(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-1), "jusqu_au": j(1)})
    ha(c, {"chambre": "ami", "noms": []})
    assert main.ETAT["base"].sejours_de(pid) == [{"du": j(-1), "jusqu_au": j(-1), "chambre": "ami"}]
    assert c.get("/api/livrets").json()["sejours"] == []


# ---------------------------------------------------------------- 0.9.1 : titres proposés par l'IA du PC

from app import ollama as O  # noqa: E402


def test_nettoyer_les_propositions():
    brut = ("1. Camille encore prise la main dans le sac !\n2) « Scandale au barbecue : elle nie tout »\n"
            "3. Un titre beaucoup trop long qui dépasse largement les soixante caractères permis\n"
            "4. Je ne peux pas écrire cela\n5. The party is over with her\n- Camille encore prise la main dans le sac !\n\n")
    assert O.nettoyer(brut, "femme") == ["Camille encore prise la main dans le sac !", "Scandale au barbecue : elle nie tout"]
    assert O.nettoyer(brut, "") == ["Camille encore prise la main dans le sac !"]      # genre inconnu : pas de « elle »
    assert "60 caractères au plus" in O.consigne("un gâteau renversé", "photo", "femme", "Camille")


def _faux_ollama(reponses):
    appels = []

    def lire(chemin, corps):
        appels.append((chemin, corps))
        if chemin == "/api/tags":
            return {"models": [{"name": "qwen2.5:7b"}]}
        return {"response": reponses.pop(0) if reponses else ""}
    lire.appels = appels
    return lire


def test_proposer_des_titres(monter):
    c = monter()
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux_ollama([
        "1. Camille surprise en flagrant délit de gâteau\n2. Le gâteau du scandale\n3. Elle a tout mangé, seule",
        "1. Crème fouettée : les aveux de Camille\n2. Le gâteau du scandale\n3. Dessert interdit, preuves à l'appui"]))
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()
    assert ed["ia"]["maxi"] == 60 and ed["titre_defaut"] == "Camille Fabre revient !"
    photo = ed["edition"]["photos"][1]["id"]
    assert c.post(f"/api/recidives/{rid}/proposer", json={"cible": photo, "description": "x"}).status_code == 422
    props = c.post(f"/api/recidives/{rid}/proposer", json={"cible": photo, "description": "Camille devant un gâteau renversé"}).json()["propositions"]
    assert len(props) == 5 and all(len(x) <= 60 for x in props) and props.count("Le gâteau du scandale") == 1
    gardee = c.get(f"/api/recidives/{rid}").json()["edition"]["photos"][1]
    assert gardee["description"] == "Camille devant un gâteau renversé" and gardee["propositions"] == props
    assert gardee["legende"].startswith("Cliché du ")                  # rien n'est choisi à la place de Julien
    # Choisir une proposition pour la légende, écrire le gros titre de la une
    c.put(f"/api/recidives/{rid}", json={"photos": [{"id": photo, "legende": props[0]}], "titre_une": "Camille Fabre récidive !"})
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert props[0] in html and "<span>Camille Fabre</span> récidive !" in html
    # Compléter garde descriptions et propositions
    c.post(f"/api/recidives/{rid}/preparer", json={"completer": True})
    assert c.get(f"/api/recidives/{rid}").json()["edition"]["photos"][1]["propositions"] == props


def test_ia_injoignable_ou_pas_reglee(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    r = c.post(f"/api/recidives/{rid}/proposer", json={"cible": "une", "description": "Camille au marché"})
    assert r.status_code == 503 and "GAZETTE_OLLAMA_URL" in r.json()["detail"]

    def panne(chemin, corps):
        raise ConnectionError("Connection refused")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=panne)
    r = c.post(f"/api/recidives/{rid}/proposer", json={"cible": "une", "description": "Camille au marché"})
    assert r.status_code == 503 and "OLLAMA_HOST" in r.json()["detail"]
    assert c.post("/api/connexion/verifier").json()["ia"]["ok"] is False
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux_ollama(["1. Camille fait son marché en douce"]))
    props = c.post(f"/api/recidives/{rid}/proposer", json={"cible": "une", "description": "Camille au marché"}).json()["propositions"]
    assert props == ["Camille fait son marché en douce"]
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["propositions_une"] == props and ed["description_une"] == "Camille au marché"
    assert c.post("/api/connexion/verifier").json()["ia"]["ok"] is True



def test_place_du_macaron(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    d = c.get(f"/api/recidives/{rid}").json()
    assert d["edition"]["macaron"] == "hd" and set(d["macarons"]) == {"hg", "hd", "bg", "bd", "aucun"}
    assert 'class="burst hd"' in c.get(f"/api/recidives/{rid}/apercu").text
    assert c.put(f"/api/recidives/{rid}", json={"macaron": "bg"}).status_code == 200
    assert 'class="burst bg"' in c.get(f"/api/recidives/{rid}/apercu").text
    c.put(f"/api/recidives/{rid}", json={"macaron": "aucun"})
    assert 'class="burst' not in c.get(f"/api/recidives/{rid}/apercu").text
    assert c.put(f"/api/recidives/{rid}", json={"macaron": "milieu"}).status_code == 422



def test_cadrage_des_photos(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    d = c.get(f"/api/recidives/{rid}").json()
    p0 = d["edition"]["photos"][0]
    assert p0["cadrage"] == "haut" and set(d["cadrages"]) == {"haut", "centre", "bas", "entiere"}
    c.put(f"/api/recidives/{rid}", json={"photos": [{"id": p0["id"], "cadrage": "entiere"}, {"id": d["edition"]["photos"][1]["id"], "cadrage": "n_importe"}]})
    ph = c.get(f"/api/recidives/{rid}").json()["edition"]["photos"]
    assert ph[0]["cadrage"] == "entiere" and ph[1]["cadrage"] == "haut"
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert 'class="entiere"' in html and 'class="haut"' in html
    c.post(f"/api/recidives/{rid}/preparer", json={"completer": True})            # gardé par « Compléter »
    assert c.get(f"/api/recidives/{rid}").json()["edition"]["photos"][0]["cadrage"] == "entiere"



def test_ia_modele_absent(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])

    def absent(chemin, corps):
        raise O.ErreurOllama(404, "model 'qwen2.5:7b' not found")
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=absent)
    r = c.post(f"/api/recidives/{rid}/proposer", json={"cible": "une", "description": "Camille au marché"})
    assert r.status_code == 503 and "trouve pas le modèle" in r.json()["detail"] and "not found" in r.json()["detail"]



def test_rumeurs_de_la_redaction(monter):
    c = monter()
    lire = _faux_ollama(["1. Selon nos sources, Camille aurait adopté un rond-point.\n2. Il se murmure que Camille parle aux tomates.\n"
                         "3. Une rumeur beaucoup trop longue pour tenir dans la rubrique, qui dépasse largement les cent trente caractères autorisés par la rédaction en chef\n"
                         "4. Exclusif : Camille détiendrait le record de siestes assises."])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    props = c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": "aime le jardinage"}).json()["propositions"]
    assert len(props) == 3 and all(len(x) <= 130 for x in props)
    assert "aime le jardinage" in lire.appels[-1][1]["prompt"]
    ed = c.get(f"/api/recidives/{rid}").json()
    assert ed["edition"]["propositions_rumeurs"] == props and ed["rumeurs_maxi"] == 4
    assert "rumeurs de la rédaction" not in c.get(f"/api/recidives/{rid}/apercu").text      # rien choisi : rien imprimé
    c.put(f"/api/recidives/{rid}", json={"rumeurs": props[:2] + ["Ma rumeur à moi", "", "5", "6"]})
    gardees = c.get(f"/api/recidives/{rid}").json()["edition"]["rumeurs"]
    assert gardees == props[:2] + ["Ma rumeur à moi", "5"]                                  # 4 au plus, vides retirées
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert "Les rumeurs de la rédaction" in html and "Ma rumeur à moi" in html and "tout est inventé" in html



def test_numeros_de_l_ia_retires():
    brut = "1 - Il se murmure que Camille parle aux arbres.\n2) Exclusif : Camille cache un dragon.\n3 – Selon nos sources, Camille vole.\n4. Camille et le rond-point"
    assert O.nettoyer(brut, "femme", 130) == ["Il se murmure que Camille parle aux arbres.", "Exclusif : Camille cache un dragon.",
                                             "Selon nos sources, Camille vole.", "Camille et le rond-point"]
    assert O.sans_numero("2 - Il se murmure que…") == "Il se murmure que…"
    assert O.sans_numero("Camille 2 fois plus drôle") == "Camille 2 fois plus drôle"



def test_indices_gardes_dans_carnet_et_deja_paru(monter):
    c = monter()
    ecrits = []
    main.ETAT["carnet"]._ecrire = lambda url, jeton, pid, texte: ecrits.append((pid, texte))
    for p in main.ETAT["carnet"].personnes(forcer=True):
        p["personne_id"], p["journaux"] = "p-camille0001", "aime le jardin"
    a = "1. Selon nos sources, Camille parle aux tomates.\n2. Camille aurait adopté un rond-point."
    b = "1. Selon nos sources, Camille parle aux tomates !\n2. Camille dresse des escargots de course."
    lire = _faux_ollama([a, a, a, a, a, a, b, b, b])          # 3 essais par demande (moins de 8 rumeurs)
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=lire)
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    assert c.get(f"/api/recidives/{rid}").json()["indices_carnet"] == "aime le jardin"
    r = c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": "aime le jardin, fan de pétanque"}).json()
    assert r["carnet"] == "gardé dans carnet" and ecrits == [("p-camille0001", "aime le jardin, fan de pétanque")]
    assert c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": "aime le jardin, fan de pétanque"}).json()["carnet"] == "déjà dans carnet"
    # Une rumeur imprimée dans le N° 2 n'est plus reproposée au N° 3 (même presque identique)
    c.put(f"/api/recidives/{rid}", json={"rumeurs": ["Selon nos sources, Camille parle aux tomates."]})
    c.post(f"/api/recidives/{rid}/approuver")
    deja = main._deja_paru(pid, 0)
    assert "Selon nos sources, Camille parle aux tomates." in deja
    props = main.ETAT["ollama"].rumeurs("", "femme", "Camille", [], deja=deja)
    assert props == ["Camille dresse des escargots de course."] and "Déjà parus" in lire.appels[-1][1]["prompt"]
    assert O.proche_de("SELON NOS SOURCES, Camille parle aux tomates !", deja)


def test_indices_pas_gardes_en_lecture_seule(monter):
    c = monter()
    main.ETAT["cfg"] = main.ETAT["cfg"].__class__(**{**main.ETAT["cfg"].__dict__, "lecture_seule": True})
    for p in main.ETAT["carnet"].personnes(forcer=True):
        p["personne_id"] = "p-camille0001"
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux_ollama(["1. Camille aurait adopté un rond-point."]))
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    assert c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": "fan de pétanque"}).json()["carnet"] == "pas gardé : lecture seule"
