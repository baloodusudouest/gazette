from datetime import date

from app import extraction as x
from tests import fixtures as F


def test_puces_datees():
    ev = x.evenements_fr(F.MOIS_PUCES, 1988, "wikipedia")
    dates = [e["date"] for e in ev]
    assert "1988-07-01" in dates and "1988-07-04" in dates and dates.count("1988-07-07") == 4   # la sous-puce hérite de la date
    pont = next(e for e in ev if "Pont" in e["texte"])
    assert pont["rubrique"] == "Testland" and pont["texte"].startswith("Ouverture du Pont")
    assert "Pont de Testville" in pont["liens"]
    assert not any("quelqu'un" in e["texte"] for e in ev)          # section Naissances ignorée


def test_sections_par_jour():
    ev = x.evenements_fr(F.MOIS_JOURS, 2000, "wikipedia")
    assert [e["date"] for e in ev] == ["2000-05-01", "2000-05-02", "2000-05-02", "2000-05-03"]


def test_page_annuelle_et_prefixe_virgule():
    ev = x.evenements_fr(F.ANNEE_FRANCE, 1988, "wikipedia-france")
    salon = next(e for e in ev if "salon" in e["texte"])
    assert salon["date"] == "1988-09-17" and salon["texte"].startswith("Paris") is False
    assert any(e["date"] == "1988-12-01" for e in ev)


def test_personnes_du_jour():
    nes = x.personnes_du_jour(F.JOUR, "Naissances")
    assert [p["titre"] for p in nes][:2] == ["Gustav Exemple", "Ringo Exemple"]
    morts = x.personnes_du_jour(F.JOUR, "Décès")
    assert {p["annee"] for p in morts} == {1930, 1890}


def test_anglais():
    ev = x.evenements_en(F.EN_MOIS, 1988)
    assert len(ev) == 3 and ev[1]["date"] == "1988-07-07" and ev[1]["langue"] == "en"


def test_larousse():
    ev = x.evenements_larousse(F.LAROUSSE)
    assert ev[0] == {"date": "1988-07-06", "texte": "Les jardiniers de Testville obtiennent un label national.",
                     "rubrique": "Jardins", "liens": [], "source": "larousse"}
    assert ev[1]["rubrique"] == "France : Testville" and "1er festival" in ev[1]["texte"]


def test_texte_modeles():
    assert x.texte("Le {{s-|XX}} et {{1er}} mai, {{formatnum:12000}} personnes<ref>x</ref>") == "Le XXe siècle et 1er mai, 12000 personnes"
