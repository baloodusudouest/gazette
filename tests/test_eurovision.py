"""0.28 : « Good Evening Europe! » (édition spéciale Eurovision) — règles, lecture de Douze points simulé d'après les
deux fichiers du contrat (finale et demi-finale), relecture, approbation, parution dans carnet, nouvelles versions,
essai, interrupteur, et rendu des 4 pages sans débordement. Aucun réseau, personnes inventées."""
from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from app import eurovision as EV
from app import journal, main, rendu, rendu_eurovision
from app.config import Config
from tests import douze_simule as D

MDP = "mot-de-passe-de-test"


# ---------------------------------------------------------------- règles

def test_ecarts_et_rangs_en_clair():
    assert EV.ecart_clair(2.33) == "à 2,3 places en moyenne"
    assert EV.places(1) == "1 place" and EV.places(4.0) == "4 places" and EV.places(0) == "0 place"
    assert EV.rang(1) == "1er" and EV.rang(3.0) == "3e" and EV.rang(2.5) == "2,5e" and EV.rang(None) == "—"


def test_invite_une_et_haut_du_palmares():
    j = D.exemple()
    assert EV.livret(j) == "finale" and EV.numero_defaut(j) == "2027 · Eurovision · Finale"
    une = EV.invite_une(j)
    assert une["prenom"] == "Barnabé" and une["ecart"] == 4.0
    haut = EV.haut_palmares(j)
    assert [x["prenom"] for x in haut] == ["Célestine", "Désiré", "Aglaé"]      # l'invité en une est retiré
    assert haut[0]["rang"] == 2
    # Invité incomplet : jamais dans le palmarès imprimé
    j["palmares"][1]["complet"] = False
    assert "Célestine" not in [x["prenom"] for x in EV.haut_palmares(j)]
    d = D.exemple(demi=True)
    assert EV.livret(d) == "qualifies" and EV.invite_une(d)["prenom"] == "Désiré"
    assert [x["prenom"] for x in EV.haut_palmares(d)] == ["Aglaé", "Barnabé", "Célestine"]
    assert not EV.avec_jury(d) and EV.avec_jury(j)


def test_commentaires_tires_au_hasard():
    j = D.exemple()
    for graine in range(20):
        t = EV.tirer(j, graine=graine)
        assert 2 <= len(t) <= 3 and len(set(t)) == len(t)
        assert len({k.split("-")[0] for k in t}) == len(t)          # des invités différents tant qu'il y en a
    t = EV.tirer(j, n=3, graine=1)
    autre = EV.changer_commentaire(j, t, t[1], graine=2)
    assert len(autre) == 3 and autre[0] == t[0] and autre[2] == t[2] and autre[1] != t[1]
    assert t[0] not in EV.tirer(j, refuses=[t[0]], n=3, graine=1)
    vus = EV.commentaires_vus(j, t)
    assert vus[0]["prenom"] and vus[0]["pays"].startswith("Pays ")
    # Trop long : jamais tiré
    j["commentaires"] = [{**c, "texte": "x" * 300} for c in j["commentaires"]]
    assert EV.tirer(j) == []


def test_grille_des_jumeaux_et_image_de_la_une():
    assert EV.grille(2)["cols"] == 2 and EV.grille(5)["cols"] == 3 and EV.grille(12)["vignettes"]
    assert EV.grille(3, "qualifies")["cols"] == 3 and EV.grille(8, "qualifies")["vignettes"]
    assert EV.image_une({}, ["apero", "poster", "logo"]) == "apero"
    assert EV.image_une({"apero": False}, ["apero", "poster", "logo"]) == "poster"
    assert EV.image_une({"apero": False, "poster": False}, ["apero", "poster", "logo"]) == "logo"
    assert EV.image_une({}, ["banniere"]) == ""


# ---------------------------------------------------------------- parcours par l'API

@pytest.fixture()
def monter(tmp_path):
    def faire(journaux=None, douze=True, carnet_appels=None):
        main.ETAT.clear()
        main.ETAT["cfg"] = Config(password=MDP, data=tmp_path, static=tmp_path / "static", attente_connexion=False,
                                  sources_actives=False, synchrone=True, carnet_url="http://carnet", carnet_jeton=D.JETON,
                                  immich_url="http://immich", immich_cle="cle",
                                  douze_points_url="http://douze" if douze else "")
        sim = D.DouzeSimule(journaux if journaux is not None else {1: [D.habiller(D.exemple(), 1)]})
        main.ETAT["douze_lire"] = sim
        main.ETAT["immich_lire"] = D.immich_simule
        main.ETAT["carnet_lire"] = lambda url, jeton: [{"carnet_id": "C-9", "nom": "Célestine Essai", "prenom": "Célestine",
                                                        "personne_id": "p-abcdefabcd"}]
        appels = carnet_appels if carnet_appels is not None else []
        main.ETAT["carnet_fiche"] = lambda url, jeton, methode, chemin, corps: (appels.append((methode, chemin, corps)) or (200, {}))
        c = TestClient(main.app)
        c.__enter__()
        assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
        c.sim = sim
        return c
    yield faire
    main.ETAT.clear()


def _premier(c) -> int:
    t = c.get("/api/a-traiter").json()
    return t["eurovisions"][0]["id"]


def test_finale_brouillon_relecture_apercu(monter):
    c = monter()
    t = c.get("/api/a-traiter").json()
    assert len(t["eurovisions"]) == 1 and t["total"] >= 1
    eid = t["eurovisions"][0]["id"]
    assert t["eurovisions"][0]["numero"] == "2027 · Eurovision · Finale" and t["eurovisions"][0]["livret"] == "finale"
    d = c.get(f"/api/eurovisions/{eid}").json()
    vue = d["vue"]
    assert vue["une"]["phrase"] == "Barnabé, à 4 places en moyenne du vrai classement"
    assert vue["image_une"] == "apero" and {i["sorte"] for i in vue["images"]} == {"apero", "poster", "logo", "banniere"}
    assert [x["prenom"] for x in vue["palmares"]] == ["Célestine", "Désiré", "Aglaé"]
    assert 2 <= len(vue["commentaires"]) <= 3 and vue["duos"][0]["photo"] == "40000000-0000"
    assert vue["podium_maison"] == ["Pays 6", "Pays 12", "Pays 8"] and vue["podium_officiel"][0] == "Pays 3"
    assert [x["carnet"] for x in d["carnet"]] == [False, False, True, True]     # ordre du journal : Barnabé, Désiré, Aglaé, Célestine
    html = c.get(f"/api/eurovisions/{eid}/apercu").text
    assert "Good Evening <span class=\"ac\">Europe!</span>" in html and "N° 2027 · Eurovision · Finale" in html
    assert "Barnabé avait tout vu venir" in html and "<b>4 places</b>" in html
    assert "Le salon contre l'Europe" in html and "Les jumeaux <span class=\"ac\">de vote</span>" in html
    assert ">Jury<" in html and "Entendu dans le salon" in html and "Sélection" not in html     # aucune mention d'IA
    assert html.count("data:image/png;base64,") >= 3 and "data:image/jpeg;base64," in html      # images figées + Immich
    assert c.get(f"/api/eurovisions/{eid}/image/logo").content == D.PNG
    assert c.get(f"/api/eurovisions/{eid}/photo/40000000-0000").content.startswith(b"\xff\xd8")
    assert c.get(f"/api/eurovisions/{eid}/photo/inconnue-0000").status_code == 404
    # Relecture : N° corrigé, apéro retiré (la une prend le poster), photo d'un duo retirée, nouveau tirage
    r = c.put(f"/api/eurovisions/{eid}", json={"numero_main": "2027 · Eurovision · Grande finale",
                                               "images": {"apero": False}, "duos": [{"cle": "1-2", "retiree": True}]})
    assert r.status_code == 200
    vue = c.get(f"/api/eurovisions/{eid}").json()["vue"]
    assert vue["image_une"] == "poster" and vue["duos"][0]["retiree"]
    html = c.get(f"/api/eurovisions/{eid}/apercu").text
    assert "Grande finale" in html and "L'apéro de la soirée" not in html
    avant = [x["cle"] for x in vue["commentaires"]]
    apres = c.post(f"/api/eurovisions/{eid}/tirer", json={"remplacer": avant[0]}).json()["commentaires"]
    assert apres[0]["cle"] != avant[0] and len(apres) == len(avant)
    apres = c.post(f"/api/eurovisions/{eid}/tirer", json={"refuser": apres[0]["cle"]}).json()["commentaires"]
    assert len(apres) == len(avant) - 1
    assert len(c.post(f"/api/eurovisions/{eid}/tirer", json={}).json()["commentaires"]) >= 2
    # Les Archives n'ont rien tant que ce n'est pas approuvé
    assert c.get("/api/archives").json()["archives"] == []


def test_reclôture_avant_et_apres_approbation(monter):
    v1 = D.habiller(D.exemple(), 1, 1)
    appels = []
    c = monter({1: [v1]}, carnet_appels=appels)
    eid = _premier(c)
    # Reclôture avant l'approbation : le brouillon prend la nouvelle version
    v2 = D.habiller(D.exemple(), 1, 2)
    v2["soiree"]["nom"] = "Finale de démonstration (reclôturée)"
    c.sim.journaux[1].append(v2)
    c.post("/api/eurovision/relire")
    n = c.get(f"/api/eurovisions/{eid}").json()["numero"]
    assert n["version"] == 2 and n["etat"] == "a_relire"
    # Approbation : parution dans carnet pour les deux invités liés (identifiant maison, ou retrouvé par carnet)
    r = c.post(f"/api/eurovisions/{eid}/approuver").json()
    assert r["ok"] and r["carnet"].startswith("parution notée pour 2 invités")
    chemins = sorted(x[1] for x in appels)
    assert chemins == ["/gazette/personnes/p-0123456789/parus/eurovision-1", "/gazette/personnes/p-abcdefabcd/parus/eurovision-1"]
    assert appels[0][0] == "PUT" and appels[0][2]["journal"] == "eurovision" and appels[0][2]["numero"] == "2027 · Eurovision · Finale"
    arch = c.get("/api/archives").json()["archives"]
    assert arch[0]["journal"] == "eurovision" and arch[0]["pdf"] == f"/api/eurovisions/{eid}/pdf"
    # Nouvelle version après l'approbation : le numéro paru ne change pas, une tuile propose de le refaire
    v3 = D.habiller(D.exemple(), 1, 3)
    v3["soiree"]["nom"] = "Finale v3"
    c.sim.journaux[1].append(v3)
    c.post("/api/eurovision/relire")
    n = c.get(f"/api/eurovisions/{eid}").json()
    assert n["numero"]["version"] == 2 and n["numero"]["version_dispo"] == 3 and n["numero"]["etat"] == "approuve"
    assert n["nouvelle_version"] and c.get("/api/a-traiter").json()["eurovision_versions"][0]["id"] == eid
    assert c.post(f"/api/eurovisions/{eid}/refaire").status_code == 200
    n = c.get(f"/api/eurovisions/{eid}").json()["numero"]
    assert n["version"] == 3 and n["etat"] == "a_relire"
    # Ignorer une nouvelle version
    c.post(f"/api/eurovisions/{eid}/approuver")
    c.sim.journaux[1].append(D.habiller(D.exemple(), 1, 4))
    c.post("/api/eurovision/relire")
    assert c.get("/api/a-traiter").json()["eurovision_versions"]
    c.post(f"/api/eurovisions/{eid}/ignorer-version")
    assert c.get("/api/a-traiter").json()["eurovision_versions"] == []


def test_demi_finale_livret_qualifies(monter):
    demi = D.habiller(D.exemple(demi=True), 7)
    c = monter({7: [demi]})
    eid = _premier(c)
    d = c.get(f"/api/eurovisions/{eid}").json()
    assert d["vue"]["livret"] == "qualifies" and d["vue"]["une"]["prenom"] == "Désiré"
    assert d["vue"]["demi"]["qualifies"][0] == "Pays 1" and d["vue"]["demi"]["pleure"] == ["Pays 7", "Pays 4"]
    html = c.get(f"/api/eurovisions/{eid}/apercu").text
    assert "Désiré a le flair" in html and "Nos 10 contre les 10 de l'Europe" in html
    assert html.count("Pas vu venir") == 2                       # Pays 1 et Pays 2 : absents de notre top 10
    assert "On les pleure" in html and "On les déteste" in html and "Le flair des invités" in html
    assert "Coup de cœur de la maison" in html and "Nul point maison" in html and "13,5 / 20" in html
    assert "Rendez-vous samedi" in html and "fiche PDF de la soirée (Douze points)" in html
    assert ">Jury<" not in html                                  # soirée sans jury : rien sur le jury
    assert "Finale · samedi 15 mai" in html
    # Après la finale, une nouvelle version de la demi ne propose pas de refaire le magazine
    c.post(f"/api/eurovisions/{eid}/approuver")
    c.sim.journaux[7].append(D.habiller(D.exemple(demi=True), 7, 2))
    c.post("/api/eurovision/relire")
    assert c.get("/api/a-traiter").json()["eurovision_versions"] == []


def test_sans_jury_finale_pas_de_colonne(monter):
    j = D.habiller(D.exemple(), 1)
    j["soiree"]["avec_jury_maison"] = False
    c = monter({1: [j]})
    html = c.get(f"/api/eurovisions/{_premier(c)}/apercu").text
    assert ">Jury<" not in html and ">Public<" in html


def test_sans_images_ni_photos(monkeypatch, monter):
    j = D.habiller(D.exemple(), 1, images=(), photos=False)
    c = monter({1: [j]})
    eid = _premier(c)
    vue = c.get(f"/api/eurovisions/{eid}").json()["vue"]
    assert vue["image_une"] == "" and vue["images"] == [] and all(not d["photo"] for d in vue["duos"])
    html = c.get(f"/api/eurovisions/{eid}/apercu").text
    assert "12<br>points" in html and "data:image" not in html      # pastille « 12 points », bandeau bleu nuit


def test_interrupteur_et_reglages(monter):
    c = monter()
    assert c.get("/api/reglages").json()["reglages"]["e_titre"] == "Good Evening Europe!"
    assert c.put("/api/reglages", json={"eurovision": False, "e_titre": "Bonsoir l'Europe"}).status_code == 200
    t = c.get("/api/a-traiter").json()
    assert t["eurovisions"] == [] and main.ETAT["base"].eurovisions() == []      # type éteint : Douze points pas lu
    assert c.put("/api/reglages", json={"eurovision": "oui"}).status_code == 400
    assert c.put("/api/reglages", json={"e_titre": ""}).status_code == 400
    c.put("/api/reglages", json={"eurovision": True})
    eid = _premier(c)
    assert "Bonsoir <span class=\"ac\">l&#x27;Europe</span>" in c.get(f"/api/eurovisions/{eid}/apercu").text
    # Connexion : tuile Douze points
    e = c.get("/api/connexion/etat").json()["douze_points"]
    assert e["regle"] and e["soirees"] == 1 and e["numeros"] == 1
    assert c.post("/api/connexion/verifier").json()["douze_points"]["ok"]


def test_douze_points_absent_ou_jeton_refuse(monter):
    c = monter(douze=False)
    assert c.get("/api/a-traiter").json()["eurovisions"] == []
    assert c.post("/api/connexion/verifier").json()["douze_points"]["ok"] is None
    c = monter()
    main.ETAT["douze"].jeton = "mauvais"
    assert c.post("/api/eurovision/relire").json()["nouveaux"] == 0
    assert c.post("/api/connexion/verifier").json()["douze_points"]["ok"] is False


def test_essai_par_simuler(monter):
    appels = []
    c = monter(carnet_appels=appels)
    soirees = c.get("/api/eurovision/soirees").json()["soirees"]
    assert soirees[0]["id"] == 1
    lien = c.post("/api/essais", json={"journal": "eurovision", "soiree_id": 1}).json()["lien"]
    eid = int(lien.rsplit("/", 1)[1])
    assert c.get(f"/api/eurovisions/{eid}").json()["numero"]["essai"]
    assert any(x["journal"] == "eurovision" for x in c.get("/api/essais").json()["essais"])
    assert c.post(f"/api/eurovisions/{eid}/approuver").json()["carnet"] == "essai : rien envoyé à carnet"
    assert appels == [] and c.get("/api/archives").json()["archives"] == []
    assert all(x["id"] != eid for x in c.get("/api/a-traiter").json()["eurovisions"])
    assert c.delete(f"/api/essais/eurovision/{eid}").status_code == 200
    assert c.post("/api/essais", json={"journal": "eurovision", "soiree_id": 99}).status_code == 404


# ---------------------------------------------------------------- rendu : 4 pages sans débordement

def _rendre(j: dict, duos: list | None = None, comms: int = 3) -> str:
    duos = duos if duos is not None else EV.duos_defaut(j)
    n = {"journal": j, "numero_main": "", "images": {}, "duos": duos, "commentaires": EV.tirer(j, n=comms, graine=3)}
    imgs = {s: D.PNG for s in ("apero", "poster", "logo", "banniere")}
    g = rendu_eurovision.donnees(n, "Good Evening Europe!", imgs, lambda i: D.GRIS)
    return rendu_eurovision.document(g, "impose")


def _verifier(doc: str):
    try:
        contenu, deborde = rendu.pdf(doc, "impose")
    except rendu.RenduImpossible as ex:
        pytest.skip(f"Chromium absent : {ex}")
    assert contenu.startswith(b"%PDF")
    assert deborde == [], f"pages qui débordent : {deborde}"


@pytest.mark.parametrize("demi", [False, True])
def test_rendu_sans_debordement(demi):
    j = D.habiller(D.exemple(demi=demi), 1)
    _verifier(_rendre(j))


@pytest.mark.parametrize("demi", [False, True])
def test_rendu_charge_sans_debordement(demi):
    """Le pire raisonnable : 12 duos (vignettes), noms de pays longs, trois commentaires de 220 signes."""
    j = D.habiller(D.exemple(demi=demi), 1)
    for c in j["chansons"]:
        c["pays"] = f"Macédoine-du-Nord {c['id']}"
    for i in j["invites"]:
        i["prenom"] = "Marie-Bérénice"
    j["commentaires"] = [{**c, "texte": ("Une chanson qui a tout pour plaire, sauf peut-être le costume, la mise en scène, "
                                         "la tonalité du refrain et la machine à fumée. " * 2)[:220]} for c in j["commentaires"]]
    base_duo = copy.deepcopy(j["duos"][0])
    j["duos"] = [{**base_duo, "cle": f"{k}-{k + 1}", "invites": [1, 2]} for k in range(12)]
    _verifier(_rendre(j))
    # Sept duos avec photos (grille de trois colonnes), le cas suivant
    j["duos"] = [{**base_duo, "cle": f"{k}-{k + 1}", "invites": [1, 2], "photos": [{"photo": k, "immich_id": f"5000000{k}-0000"}]}
                 for k in range(5 if demi else 7)]
    _verifier(_rendre(j))
