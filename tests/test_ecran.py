"""Tests d'écran : le serveur de démonstration (tools/demo.py) dans un vrai navigateur, sur PC et iPhone.

À chaque écran : aucune erreur de page, aucun débordement horizontal. Sautés si Playwright, Chromium ou
l'interface compilée manquent (la CI les installe : voir .github/workflows/tests.yml).
"""
from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIQUE = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"
pytestmark = pytest.mark.skipif(not STATIQUE.exists(), reason="interface non compilée (cd frontend && npx vite build)")
TAILLES = {"pc": {"width": 1366, "height": 900}, "iphone": {"width": 390, "height": 844}}


@pytest.fixture(scope="module")
def adresse(tmp_path_factory):
    from tools import demo
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    threading.Thread(target=demo.lancer, args=(port, tmp_path_factory.mktemp("demo")), daemon=True).start()
    import httpx
    url = f"http://127.0.0.1:{port}"
    for _ in range(300):
        try:
            with httpx.Client(base_url=url) as c:
                if c.get("/health", timeout=1).json().get("livrets", 0) >= 2:
                    break
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.1)
    return url


@pytest.fixture(scope="module")
def navigateur():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--no-sandbox"])
        except Exception as ex:  # noqa: BLE001
            pytest.skip(f"Chromium absent : {ex}")
        yield b
        b.close()


def ouvrir(navigateur, adresse, taille, chemin=""):
    page = navigateur.new_page(viewport=TAILLES[taille])
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.goto(adresse + "/")
    page.fill("#mot-de-passe", "demo-demo-demo")
    page.click("button[type=submit]")
    page.locator("ul[aria-label=Livrets] li").first.wait_for()
    if chemin:
        page.goto(adresse + "/" + chemin)
        page.reload()
    return page, erreurs


def sans_debordement(page):
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")


@pytest.mark.parametrize("taille", TAILLES)
def test_livrets(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    assert page.locator("ul[aria-label=Livrets] li").count() == 3       # deux fiches + une créée d'après carnet (démo)
    page.get_by_text("Sacha Exemple").first.wait_for()               # séjour annoncé, invité sans fiche
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_livret_relecture_et_apercu(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/livret/1")
    page.get_by_role("heading", name="Camille Fabre").wait_for()
    page.get_by_text("Anniversaire en avance :").wait_for()
    page.get_by_label("Gros titre").wait_for()
    cadre = page.frame_locator("iframe[title='Aperçu du livret']")
    cadre.get_by_text("Camille Fabre").first.wait_for()
    # Les propositions s'ouvrent et montrent les faits sensibles seulement sur demande
    page.get_by_role("button", name="Changer").click()
    page.get_by_placeholder("Chercher…").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_a_traiter(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/a-traiter")
    page.get_by_role("button", name="Invités sans fiche").wait_for()
    page.get_by_role("button", name="Anniversaires proches").click()
    page.get_by_text("Ajouter au mot des hôtes").first.wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
@pytest.mark.parametrize("chemin, titre", [("#/connexion", "Connexion"), ("#/reglages", "Réglages")])
def test_connexion_et_reglages(navigateur, adresse, taille, chemin, titre):
    page, erreurs = ouvrir(navigateur, adresse, taille, chemin)
    page.get_by_role("heading", name=titre, exact=True).wait_for()
    if titre == "Réglages":
        page.get_by_role("heading", name="Top 5 culturel").wait_for()
        page.get_by_role("button", name="Copier le prompt").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_a_traiter_avec_carnet(navigateur, adresse, taille):
    """Invité sans fiche : ce que carnet sait est dit ; la fiche propose le contact de carnet."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/a-traiter")
    page.get_by_text("Carnet : le 3 mai, année inconnue").wait_for()
    page.get_by_role("button", name="Créer la fiche").first.click()
    page.get_by_role("group", name="Contacts de carnet").get_by_role("button").first.click()
    page.get_by_text("année inconnue : complète la date").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_reglages_restaurer(navigateur, adresse, taille):
    """Restaurer les réglages : dates de l'Anneau simulé, différences avant → sauvegardé (rien n'est confirmé ici)."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/reglages")
    page.get_by_role("heading", name="Restaurer les réglages").wait_for()
    page.get_by_role("button", name="Restaurer les réglages").click()
    page.get_by_label("Sauvegarde du").wait_for()
    page.get_by_role("list", name="Différences").get_by_text("La Gazette d'avant").wait_for()
    page.get_by_role("button", name="Remettre ces réglages").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_la_recidive(navigateur, adresse, taille):
    """0.9 : Lou Martin revient (démo) : La Récidive N° 2 dans Livrets, puis sa relecture et son aperçu."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.get_by_text("La Récidive N° 2").first.wait_for()
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    assert page.locator("textarea[aria-label^='Légende']").count() == 7          # 3 récentes + 4 anciens scandales
    page.locator("button:has-text('Retirer')").first.click()
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.get_by_text("Enregistré.").wait_for()
    assert page.frame_locator("iframe[title='Aperçu de La Récidive']").get_by_text("Elle est revenue, nous aussi").first.is_visible()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_titres_proposes_par_l_ia(navigateur, adresse, taille):
    """0.9.1 : décrire la photo de la une, demander 5 titres, en choisir un."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    page.fill("input[aria-label='Description de la photo de la une']", "Lou sur une plage, lunettes de soleil")
    page.locator("button:has-text('5 titres')").first.click()
    page.get_by_text("« Les vacances secrètes de Lou »").wait_for()
    page.get_by_text("« Les vacances secrètes de Lou »").click()
    assert page.locator("input[placeholder='Lou Martin revient !']").input_value() == "Les vacances secrètes de Lou"
    sans_debordement(page)
    assert erreurs == []
