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
    assert page.locator("ul[aria-label=Livrets] li").count() == 2
    page.get_by_text("Dominique Inconnu").wait_for()                 # séjour annoncé, invité sans fiche
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
    page.get_by_role("heading", name=titre).wait_for()
    sans_debordement(page)
    assert erreurs == []
