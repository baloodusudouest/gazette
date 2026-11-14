"""Règle de l'anniversaire proche du séjour : bornes de 14 jours, passage d'année, 29 février."""
from datetime import date, timedelta

import pytest

from app.anniversaire import phrases, proche

NAISSANCE = date(1990, 6, 15)        # personne inventée
ANNIV = date(2027, 6, 15)


def sejour_autour(decalage_arrivee: int, nuits: int = 2):
    du = ANNIV + timedelta(days=decalage_arrivee)
    return du, du + timedelta(days=nuits)


@pytest.mark.parametrize("arrivee, cas, ecart", [
    (1, "en_retard", 1),       # arrive le lendemain de l'anniversaire
    (14, "en_retard", 14),
    (0, "le_jour_meme", 0),    # arrive le jour J
    (-1, "le_jour_meme", 0),   # pendant
    (-2, "le_jour_meme", 0),   # part le jour J
    (-3, "en_avance", 1),      # part la veille
    (-16, "en_avance", 14),
])
def test_bornes(arrivee, cas, ecart):
    du, fin = sejour_autour(arrivee)
    r = proche(NAISSANCE, du, fin)
    assert r is not None and r["cas"] == cas and r["ecart"] == ecart


@pytest.mark.parametrize("arrivee", [15, -17])
def test_au_dela_de_14_jours(arrivee):
    du, fin = sejour_autour(arrivee)
    assert proche(NAISSANCE, du, fin) is None


def test_passage_d_annee():
    r = proche(date(1985, 1, 2), date(2026, 12, 28), date(2026, 12, 30))
    assert r["cas"] == "en_avance" and r["anniversaire"] == "2027-01-02" and r["ecart"] == 3
    r = proche(date(1985, 12, 30), date(2027, 1, 3), date(2027, 1, 5))
    assert r["cas"] == "en_retard" and r["anniversaire"] == "2026-12-30" and r["ecart"] == 4


def test_29_fevrier():
    r = proche(date(1992, 2, 29), date(2027, 2, 28), date(2027, 3, 1))
    assert r["cas"] == "le_jour_meme" and r["anniversaire"] == "2027-02-28"
    r = proche(date(1992, 2, 29), date(2028, 2, 29), date(2028, 3, 1))
    assert r["anniversaire"] == "2028-02-29"


def test_sans_date():
    assert proche(None, date(2027, 1, 1), date(2027, 1, 2)) is None


def test_phrases_sans_age():
    r = proche(NAISSANCE, *sejour_autour(-5))
    ps = phrases(r, "Camille")
    assert len(ps) == 3 and all("{" not in p for p in ps)
    assert "dans 3 jours" in ps[0] and "Camille" in ps[0]
    assert not any(str(2027 - 1990) in p for p in ps)
    r1 = proche(NAISSANCE, *sejour_autour(1))
    assert "il y a un jour" in phrases(r1, "Camille")[0]
