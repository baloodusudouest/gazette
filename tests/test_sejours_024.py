"""0.24 : séjours annulés restés dans Gazette (Home Assistant n'annonce que le prochain séjour d'une chambre), bouton
« Séjour annulé », ménage des numéros orphelins au démarrage, et essais choisis parmi les contacts de carnet.
Personnes inventées."""

from app import main
from app.base import ESSAI_GAZETTE, ESSAI_PORTEUR
from tests.test_recidive import IMMICH_CAMILLE, _deux_sejours, ha, j, monter  # noqa: F401  (fixture)


def _rid(r):
    return int(r["invites"][0]["lien"].rsplit("/", 1)[1])


def _a_venir(c):
    return [(s["chambre"], s["du"]) for s in c.get("/api/livrets").json()["sejours"]]


# ---------------------------------------------------------------- séjour annulé remplacé par un plus tardif

def test_sejour_plus_tardif_annonce_l_ancien_part(monter):
    """Réservation du j+10 annulée, la chambre est ensuite réservée au j+30 : HA annonce le j+30 seulement ; le j+10
    (pas commencé, plus tôt) disparaît, avec sa Récidive."""
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    rep = ha(c, {"chambre": "ami", "noms": ["Paul Essai"], "du": j(30), "jusqu_au": j(32)}).json()
    assert rep["annules"] == [f"Camille Fabre ({j(10)})"]
    assert ("ami", j(10)) not in _a_venir(c) and ("ami", j(30)) in _a_venir(c)
    assert c.get(f"/api/recidives/{rid}").status_code == 404
    assert main.ETAT["base"].personne(pid)


def test_sejour_plus_tardif_deja_connu_reste(monter):
    """Une réservation plus proche s'intercale : HA annonce le j+5 ; le j+20 connu avant reste."""
    c = monter()
    c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(20), "jusqu_au": j(22)})
    rep = ha(c, {"chambre": "ami", "noms": ["Paul Essai"], "du": j(5), "jusqu_au": j(7)}).json()
    assert rep["annules"] == []
    assert {("ami", j(5)), ("ami", j(20))} <= set(_a_venir(c))


def test_autre_chambre_jamais_touchee(monter):
    c = monter()
    c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    ha(c, {"chambre": "bleue", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(7)})
    ha(c, {"chambre": "ami", "noms": ["Paul Essai"], "du": j(30), "jusqu_au": j(32)})
    assert ("bleue", j(5)) in _a_venir(c)


# ---------------------------------------------------------------- bouton « Séjour annulé »

def test_bouton_sejour_annule(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    sid = next(s["id"] for s in c.get("/api/livrets").json()["sejours"] if s["du"] == j(10))
    rep = c.delete(f"/api/sejours/{sid}")
    assert rep.status_code == 200 and rep.json()["annules"] == [f"Camille Fabre ({j(10)})"]
    assert c.get(f"/api/recidives/{rid}").status_code == 404 and ("ami", j(10)) not in _a_venir(c)
    assert c.delete(f"/api/sejours/{sid}").status_code == 404


def test_bouton_refuse_un_sejour_commence(monter):
    c = monter()
    c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-1), "jusqu_au": j(2)})
    sid = c.get("/api/livrets").json()["sejours"][0]["id"]
    assert c.delete(f"/api/sejours/{sid}").status_code == 409


def test_jour_d_arrivee_annulable(monter):
    """0.24.1 : séjour qui arrive aujourd'hui (invité sans fiche) : le bouton le retire ; HA qui annonce un séjour plus
    tardif ou la chambre libre le retire aussi."""
    c = monter()
    ha(c, {"chambre": "ado", "noms": ["Nico Essai"], "du": j(0), "jusqu_au": j(1)})
    sid = c.get("/api/livrets").json()["sejours"][0]["id"]
    assert c.delete(f"/api/sejours/{sid}").status_code == 200 and _a_venir(c) == []
    ha(c, {"chambre": "ado", "noms": ["Nico Essai"], "du": j(0), "jusqu_au": j(1)})
    ha(c, {"chambre": "ado", "noms": ["Paul Essai"], "du": j(9), "jusqu_au": j(11)})
    assert _a_venir(c) == [("ado", j(9))]
    ha(c, {"chambre": "bleue", "noms": ["Nico Essai"], "du": j(0), "jusqu_au": j(1)})
    ha(c, {"chambre": "bleue", "noms": []})
    assert ("bleue", j(0)) not in _a_venir(c)


def test_jour_d_arrivee_recidive_supprimee_par_ha(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(0), "jusqu_au": j(2)})
    assert len(main.ETAT["base"].recidives(pid)) == 1
    rep = ha(c, {"chambre": "ami", "noms": []}).json()
    assert rep["annules"] == [f"Camille Fabre ({j(0)})"] and main.ETAT["base"].recidives(pid) == []


def test_premier_sejour_annule_au_bouton_gazette_a_zero(monter):
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(7)})
    b.maj_livret(pid, mot="Un mot écrit.", etat="a_relire")
    sid = c.get("/api/livrets").json()["sejours"][0]["id"]
    c.delete(f"/api/sejours/{sid}")
    assert b.livret(pid)["etat"] == "a_preparer" and b.livret(pid)["mot"] == ""


# ---------------------------------------------------------------- ménage au démarrage

def test_menage_des_recidives_orphelines_au_demarrage(monter):
    """Séjour retiré avant la 0.22.1 : la Récidive restait. Au démarrage elle part (copie de la base avant)."""
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    b = main.ETAT["base"]
    with b._c:                                          # séjour effacé comme le faisait la 0.22.0
        b._c.execute("DELETE FROM sejours WHERE du = ?", (j(10),))
    assert [x["id"] for x in b.recidives_orphelines()] == [rid]
    assert main._menage_orphelines() == [f"Camille Fabre ({j(10)})"]
    assert b.recidives(pid) == [] and b.personne(pid)
    assert list((main.ETAT["cfg"].data / "sauvegardes").glob("gazette-*-avant-menage.db"))
    assert main._menage_orphelines() == []


def test_menage_ne_touche_ni_essais_ni_passes(monter):
    c = monter()
    pid, _ = _deux_sejours(c)
    c.post("/api/essais", json={"personne_id": pid, "journal": "recidive"})
    assert main.ETAT["base"].recidives_orphelines() == []


# ---------------------------------------------------------------- essais depuis carnet

def _carnet_deux():
    return lambda url, jeton: [
        {"carnet_id": "C-1", "nom": "Camille Fabre", "nom_carnet": "Camille Fabre", "prenom": "Camille",
         "naissance": "1988-07-07", "jour": 7, "mois": 7, "annee": 1988, "genre": "femme", "immich_id": IMMICH_CAMILLE},
        {"carnet_id": "C-9", "nom": "Lou Exemple", "nom_carnet": "Lou Exemple", "prenom": "Lou",
         "naissance": "1990-03-03", "jour": 3, "mois": 3, "annee": 1990, "genre": "femme", "immich_id": IMMICH_CAMILLE},
        {"carnet_id": "C-7", "nom": "Max Sansdate", "nom_carnet": "Max Sansdate", "prenom": "Max",
         "naissance": None, "jour": 4, "mois": 5, "annee": None, "genre": "homme", "immich_id": IMMICH_CAMILLE}]


def _relancer_avec(c, lire):
    main.ETAT["carnet"]._lire = lire
    main.ETAT["carnet"]._liste = None


def test_suggestions_rendent_l_identifiant_carnet(monter):
    c = monter()
    s = c.get("/api/carnet/suggestions?q=cam").json()["suggestions"]
    assert s[0]["carnet_id"] == "C-1"


def test_essai_d_un_contact_qui_a_une_fiche(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    lien = c.post("/api/essais", json={"carnet_id": "C-1", "journal": "gazette"}).json()["lien"]
    gid = int(lien.rsplit("/", 1)[1])
    assert main.ETAT["base"].personne(gid)["essai_de"] == pid                          # copie de la vraie fiche


def test_essai_gazette_d_un_contact_sans_fiche(monter):
    c = monter()
    _relancer_avec(c, _carnet_deux())
    b = main.ETAT["base"]
    lien = c.post("/api/essais", json={"carnet_id": "C-9", "journal": "gazette"}).json()["lien"]
    gid = int(lien.rsplit("/", 1)[1])
    p = b.personne(gid)
    assert p["essai_de"] == ESSAI_GAZETTE and p["naissance"] == "1990-03-03" and p["nom"] == "Lou Exemple (essai)"
    assert b.trouver("Lou Exemple") is None                                            # jamais reliée à HA
    assert all(x["id"] != gid for x in c.get("/api/livrets").json()["livrets"])
    essais = c.get("/api/essais").json()["essais"]
    assert [(x["journal"], x["id"]) for x in essais] == [("gazette", gid)]
    assert c.delete(f"/api/essais/gazette/{gid}").status_code == 200 and b.personne(gid) is None


def test_essai_gazette_refuse_sans_date_complete(monter):
    c = monter()
    _relancer_avec(c, _carnet_deux())
    rep = c.post("/api/essais", json={"carnet_id": "C-7", "journal": "gazette"})
    assert rep.status_code == 422 and "date de naissance" in rep.json()["detail"]


def test_essai_recidive_d_un_contact_sans_fiche(monter):
    c = monter()
    _relancer_avec(c, _carnet_deux())
    b = main.ETAT["base"]
    lien = c.post("/api/essais", json={"carnet_id": "C-7", "journal": "recidive"}).json()["lien"]   # date incomplète : permis
    rid = int(lien.rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["essai"] == 1 and ed["photos"]                                           # contact retrouvé (immich_id)
    porteur = b.personne(b.recidive(rid)["personne_id"])
    assert porteur["essai_de"] == ESSAI_PORTEUR
    assert [x["journal"] for x in c.get("/api/essais").json()["essais"]] == ["recidive"]   # pas une Gazette d'essai
    assert c.delete(f"/api/essais/gazette/{porteur['id']}").status_code == 404
    assert c.delete(f"/api/essais/recidive/{rid}").status_code == 200
    assert b.personne(porteur["id"]) is None                                           # la fiche d'essai part avec


def test_essai_contact_inconnu(monter):
    c = monter()
    assert c.post("/api/essais", json={"carnet_id": "C-404", "journal": "gazette"}).status_code == 404


def test_ancienne_forme_personne_id_toujours_acceptee(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    assert c.post("/api/essais", json={"personne_id": pid, "journal": "gazette"}).status_code == 200


