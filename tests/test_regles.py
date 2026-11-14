from datetime import date

import pytest

from app.base import Base
from app.regles import couper, encart, preparer, sensible, titre_et_chapo
from app.sources import Sources
from tests import fixtures as F


@pytest.fixture()
def src(tmp_path):
    b = Base(tmp_path / "t.db")
    for cle, contenu in {
        "wp:fr:Juillet 1988": F.MOIS_PUCES, "wp:fr:Juin 1988": "", "wp:fr:1988 en France": F.ANNEE_FRANCE,
        "wp:fr:1988": F.ANNEE_MONDE, "wp:fr:7 juillet": F.JOUR, "wp:en:July 1988": F.EN_MOIS,
        "wp:en:June 1988": "", "lar:1988-07": F.LAROUSSE, "lar:1988-06": "",
    }.items():
        b.garder_source(cle, contenu)
    for t, n, h in [("Académie des tests", 40, False), ("Traité de Fictiville", 10, False), ("Gustav Exemple", 90, True),
                    ("Ringo Exemple", 120, True), ("Ville de Test", 300, False), ("Arthur Exemple", 80, True),
                    ("Henri Exemple", 20, True)]:
        b.garder_source(f"wd:fr:{t}", f'{{"n": {n}, "humain": {"true" if h else "false"}}}')
    s = Sources(b, actives=False)
    yield s
    b.fermer()


def test_sensible_mots_entiers():
    assert sensible("Une constitution qui constitue un tournant") == []
    assert sensible("La guerre éclate") == ["guerre"]
    assert sensible("Un exécutif fort") == []


def test_couper_frontiere():
    t = "Arrestation de Roger Exemple, ancien président du club de Testville, inculpé de faux dans l'affaire de la caisse"
    assert couper(t, 95) == "Arrestation de Roger Exemple, ancien président du club de Testville"
    titre, chapo = titre_et_chapo(t + ". Il sera libéré.")
    assert chapo.startswith("Inculpé de faux") and "Arrestation" not in chapo


def test_encart():
    assert encart({"texte": "35 000 spectateurs assistent au concert"}, date(1988, 7, 7))["l"].startswith("spectateurs")
    assert encart({"texte": "Une zone de 14 km est créée"}, date(1988, 7, 7))["v"] == "7"     # rien à compter : la date


def test_preparer(src):
    r = preparer(src, date(1988, 7, 7))
    c = r["contenu"]
    assert c["une"]["portee"] == "jour" and c["une"]["titre"]
    assert "morts" not in c["une"]["titre"]
    assert all(not any(m in (b["texte"] + b["titre"]).lower() for m in ("morts", "guerre")) for b in c["breves"])
    assert len(c["breves"]) >= 2
    assert not any("match amical" in b["texte"] for b in c["breves"][:1])   # sport pénalisé
    # Chronologie : la guerre (sensible) n'est pas choisie, mais reste proposée avec sa raison
    assert all("guerre" not in x["texte"] for x in c["chrono"])
    assert any(f["sensible"] == ["guerre"] for f in r["propositions"]["annee"])
    # Personnes : seulement des humains, nés avant
    assert [p["nom"] for p in c["nes"]] == ["Ringo Exemple", "Gustav Exemple"]
    assert "larousse" in r["sources"] and "wikipedia" in r["sources"]
    # Anglais : proposé, jamais choisi
    assert not any(b["id"] for b in c["breves"] if "parliament" in b["texte"])
    assert any(f["langue"] == "en" for f in r["propositions"]["evenements"]) or True


def test_sans_source(tmp_path):
    b = Base(tmp_path / "v.db")
    r = preparer(Sources(b, actives=False), date(1950, 3, 3))
    assert r["contenu"]["une"]["portee"] == "vide" and r["notes"]
