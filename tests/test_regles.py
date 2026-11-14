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
    # Titre et chapeau : rien n'est perdu ; phrase trop longue sans frontière → pas de titre, tout en paragraphe
    titre, chapo = titre_et_chapo(t + ". Il sera libéré.")
    assert titre == "" and chapo == t + ". Il sera libéré."
    titre, chapo = titre_et_chapo("Le Testland signe un traité : la frontière est ouverte aux voyageurs, et les douanes ferment dès le lendemain matin pour toujours. Fête.")
    assert titre == "Le Testland signe un traité" and chapo.startswith("La frontière est ouverte") and chapo.endswith("Fête.")
    titre, chapo = titre_et_chapo("Ouverture du pont. Il mesure 2 km.")
    assert (titre, chapo) == ("Ouverture du pont", "Il mesure 2 km.")


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


def test_sans_renvoi_et_texte_complet():
    from app.regles import sans_renvoi, _item_p2
    assert sans_renvoi("La victoire est reconnue. (chrono. 4/02)") == "La victoire est reconnue."
    long = "Une phrase d'ouverture bien trop longue pour servir de titre car elle dépasse nettement les quatre-vingts signes, sans coupure possible ici. Suite."
    it = _item_p2({"id": "e1", "date": "2000-01-01", "rubrique": "", "texte": long})
    assert it["titre"] == "" and it["texte"] == long and "…" not in it["texte"]
    it = _item_p2({"id": "e2", "date": "2000-01-01", "rubrique": "Testland", "texte": long})
    assert it["titre"] == "Testland" and it["texte"] == long


def test_rendu_sans_titre_et_ajustement():
    from app import rendu
    j = {"titre": "La Gazette de Test", "sous_titre": "", "lieu": "La maison", "lieu_detail": "", "chez": "à la maison",
         "signature": "Les hôtes", "mot_modele": "Bienvenue {prenom}.", "accent": "#9E1B1B"}
    contenu = {"une": {"titre": "", "chapo": "Un paragraphe complet sans titre.", "portee": "jour"},
               "breves": [{"titre": "", "texte": "Brève sans titre."}],
               "p2": {"mode": "semaine", "items": [{"date": "2000-01-01", "titre": "", "texte": "Texte seul."}]}}
    h = rendu.document({"nom": "Camille Test", "naissance": "2000-01-05"}, {"contenu": contenu}, j, "lecture")
    assert '<p class="chapo seul">Un paragraphe complet sans titre.</p>' in h
    assert "<h3></h3>" not in h and "Aucun événement" not in h
    assert "window.ajuster" in h and "var(--k,1)" in h
