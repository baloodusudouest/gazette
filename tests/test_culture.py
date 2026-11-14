"""Top 5 culturel : lecture contrôlée, import, textes de la page 3."""
import pytest

from app.culture import Culture, FichierCultureInvalide, lire_texte, textes
from tests.test_api import MDP, client, connecter  # noqa: F401  (fixture partagée)

ENTETE = "Annee;Categorie;Rang;Titre;Createur_Artiste;Metrique_Cles\n"
PETIT = ("﻿" + ENTETE
         + "1988;Film;1;Film Inventé;Réalisatrice Test;N°1 mondial - 300 M$\n"
         + "1988;Film;2;Second Film;X;200 M$ monde\n"
         + "1988;Serie;1;Série Test;Chaîne;Nielsen #1\n"
         + "1988;Musique;1;Chanson Test;Groupe Test;Billboard Year-End #1\n"
         + "1988;Musique;2;Autre Chanson;Chanteur;Billboard Year-End #2\n")


def test_le_fichier_livre_se_lit():
    l = lire_texte(open("app/donnees/top5_culture_annuel.csv", encoding="utf-8-sig").read())
    assert len(l) > 1000 and {x["categorie"] for x in l} == {"Film", "Serie", "Musique"}


@pytest.mark.parametrize("mauvais, raison", [
    ("A;B\n1;2\n", "Colonnes"),
    (ENTETE + "1988;Livre;1;X;Y;Z\n", "catégorie"),
    (ENTETE + "1988;Film;7;X;Y;Z\n", "rang"),
    (ENTETE + "1988;Film;1;X;Y;Z\n1988;Film;2;x;Y;Z\n", "doublon"),
])
def test_refus(mauvais, raison):
    with pytest.raises(FichierCultureInvalide, match=raison):
        lire_texte(mauvais)


def test_textes():
    c = lire_texte(PETIT)
    top = {k: [x for x in c if x["categorie"] == k] for k in ("Film", "Serie", "Musique")}
    t = textes(top)
    assert t["musique"] == "« Chanson Test » (Groupe Test), le titre de l'année, devant « Autre Chanson » (Chanteur)."
    assert t["cinema"] == "« Film Inventé » (Réalisatrice Test) en tête du box-office, devant « Second Film ». À la télé : « Série Test »."


def test_import_et_retour(tmp_path):
    c = Culture(tmp_path)
    assert c.etat()["source"] == "livré avec l'appli"
    e = c.importer(PETIT)
    assert e["source"] == "importé" and e["lignes"] == 5 and c.annee(1988)["Film"][0]["titre"] == "Film Inventé"
    with pytest.raises(FichierCultureInvalide):
        c.importer("n'importe quoi")
    assert c.etat()["lignes"] == 5                       # un mauvais fichier ne remplace rien
    assert c.revenir()["source"] == "livré avec l'appli"


def test_livret_et_routes(client):  # noqa: F811
    connecter(client)
    assert client.post("/api/culture/import", json={"texte": "faux"}).status_code == 422
    assert client.post("/api/culture/import", json={"texte": PETIT}).json()["lignes"] == 5
    pid = client.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    c = client.get(f"/api/livrets/{pid}").json()["livret"]["contenu"]
    assert "Chanson Test" in c["musique"] and "Film Inventé" in c["cinema"]
    # Écrit à la main : gardé par une nouvelle préparation, remplacé par « Remplir depuis le top 5 »
    client.put(f"/api/livrets/{pid}", json={"contenu": {"musique": "Ma chanson à moi"}})
    client.post(f"/api/livrets/{pid}/preparer", json={})
    assert client.get(f"/api/livrets/{pid}").json()["livret"]["contenu"]["musique"] == "Ma chanson à moi"
    client.post(f"/api/livrets/{pid}/culture")
    assert "Chanson Test" in client.get(f"/api/livrets/{pid}").json()["livret"]["contenu"]["musique"]
    html = client.get(f"/api/livrets/{pid}/apercu").text
    assert "Film Inventé" in html and "Billboard" in html
    assert "Annee;Categorie" in client.get("/api/culture/fichier").text
    assert "Data Engineer" in client.get("/api/culture").json()["prompt"]
