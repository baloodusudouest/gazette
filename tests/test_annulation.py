"""0.22.1 : séjour annulé dans Home Assistant. Choix de Julien : le numéro de La Récidive du séjour annulé est
supprimé, même approuvé ; si l'invité n'a plus aucun séjour, sa fiche et sa Gazette sont supprimées (0.31.4 ; une
Gazette approuvée est gardée) ; des dates déplacées : le numéro suit ; un séjour raccourci ne touche à rien ; une
chambre libérée au départ garde tout.
Personnes inventées."""
from tests.test_recidive import _deux_sejours, ha, j, monter  # noqa: F401  (fixture)

from app import main


def _rid(r):
    return int(r["invites"][0]["lien"].rsplit("/", 1)[1])


def _recidives(pid):
    return main.ETAT["base"].recidives(pid)


def test_recidive_supprimee_si_sejour_annule_meme_approuvee(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    assert c.post(f"/api/recidives/{rid}/approuver").status_code == 200
    lv_avant = main.ETAT["base"].livret(pid)["etat"]
    rep = ha(c, {"chambre": "ami", "noms": []}).json()                  # séjour à venir annulé
    assert rep["annules"] == [f"Camille Fabre ({j(10)})"]
    assert _recidives(pid) == [] and c.get(f"/api/recidives/{rid}").status_code == 404
    assert main.ETAT["base"].personne(pid)                               # la fiche reste
    assert main.ETAT["base"].livret(pid)["etat"] == lv_avant             # il reste le premier séjour : Gazette gardée
    assert list((main.ETAT["cfg"].data / "sauvegardes").glob("gazette-*-avant-annulation.db"))


def test_dates_deplacees_le_numero_suit(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = _rid(r)
    r2 = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(11), "jusqu_au": j(13)}).json()
    assert r2["annules"] == [] and _rid(r2) == rid
    assert [x["sejour_du"] for x in _recidives(pid)] == [j(11)]


def test_invite_retire_seul_son_numero_part(monter):
    c = monter()
    pid, _ = _deux_sejours(c)
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre", "Paul Essai"], "du": j(10), "jusqu_au": j(12)})
    assert len(_recidives(pid)) == 1
    rep = ha(c, {"chambre": "ami", "noms": ["Paul Essai"], "du": j(10), "jusqu_au": j(12)}).json()
    assert rep["annules"] == [f"Camille Fabre ({j(10)})"] and _recidives(pid) == []


def test_premier_sejour_annule_la_fiche_et_la_gazette_partent(monter):
    """0.31.4 : plus aucun séjour, Gazette pas approuvée : la fiche est supprimée (copie de la base avant)."""
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(7)})
    b.maj_livret(pid, mot="Un mot écrit.", etat="a_relire")
    rep = ha(c, {"chambre": "ami", "noms": []}).json()
    assert rep["annules"] == [f"Camille Fabre ({j(5)})"]
    assert b.personne(pid) is None and b.livret(pid) is None
    assert pid not in [x["id"] for x in c.get("/api/livrets").json()["livrets"]]
    assert list((main.ETAT["cfg"].data / "sauvegardes").glob("*avant-annulation.db"))


def test_habitue_d_avant_gazette_garde_sa_fiche(monter):
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    c.put(f"/api/personnes/{pid}", json={"sejours_avant": 2})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(7)})
    ha(c, {"chambre": "ami", "noms": []})
    assert b.personne(pid) and b.livret(pid)["etat"] == "a_preparer"


def test_sejour_raccourci_rien_ne_change(monter):
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(9)})
    b.maj_livret(pid, mot="Un mot écrit.", etat="a_relire")
    rep = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(6)}).json()
    assert rep["annules"] == [] and b.livret(pid)["mot"] == "Un mot écrit." and b.livret(pid)["etat"] == "a_relire"


def test_fiches_laissees_par_l_ancienne_annulation_supprimees_au_demarrage(monter):
    """0.31.4 : une fiche « remise à zéro » avant la 0.31.4 (aucun séjour, livret vide) part au démarrage ; une fiche
    créée à la main sans séjour reste."""
    c = monter()
    b = main.ETAT["base"]
    vieille = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    b.remettre_livret(vieille)
    b.noter("livret", vieille, f"séjour du {j(5)} annulé (ami) : Gazette remise à zéro")
    voulue = c.post("/api/personnes", json={"nom": "Léon Martin", "naissance": "1990-03-03"}).json()["id"]
    b.remettre_livret(voulue)                    # vide aussi, mais jamais annulée : gardée
    assert main._menage_remises_a_zero() == ["Camille Fabre"]
    assert b.personne(vieille) is None and b.personne(voulue)
    assert main._menage_remises_a_zero() == []


def test_gazette_approuvee_gardee(monter):
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(5), "jusqu_au": j(7)})
    b.maj_livret(pid, mot="Un mot écrit.", etat="approuve")
    ha(c, {"chambre": "ami", "noms": []})
    assert b.livret(pid)["etat"] == "approuve" and b.livret(pid)["mot"] == "Un mot écrit."


def test_chambre_liberee_au_depart_garde_tout(monter):
    c = monter()
    b = main.ETAT["base"]
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)})
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-1), "jusqu_au": j(2)})   # séjour commencé
    assert len(_recidives(pid)) == 1
    rep = ha(c, {"chambre": "ami", "noms": []}).json()
    assert rep["annules"] == [] and len(_recidives(pid)) == 1 and b.livret(pid)
