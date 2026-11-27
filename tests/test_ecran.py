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
    page.get_by_role("button", name="Un autre événement : La une").click()           # 0.17 : geste « Changer » de l'élément
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
    assert page.locator("textarea[aria-label^='Légende']").count() >= 6          # 3 récentes + 4 anciens scandales (une retirée au 1er passage)
    page.locator("button[aria-label^='Refuser : Photo']").first.click()           # 0.17 : geste « Refuser »
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.get_by_text("Enregistré.").wait_for()
    page.frame_locator("iframe[title='Aperçu de La Récidive']").get_by_text("Elle est revenue, nous aussi").first.wait_for()   # l'aperçu se recharge
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_titres_proposes_par_l_ia(navigateur, adresse, taille):
    """0.9.1 : décrire la photo de la une, demander 5 titres, en choisir un."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    page.fill("input[aria-label='Description de la photo de la une']", "Lou sur une plage, lunettes de soleil")
    page.get_by_role("button", name="IA", exact=True).click()            # bouton du haut : tous les textes décrits
    # 0.12 : les photos ont un album parlant dans la démo, l'IA leur propose aussi des légendes : la une d'abord
    une = page.get_by_role("region", name="Une").get_by_text("« Les vacances secrètes de Lou »")
    une.wait_for()
    une.click()
    assert page.locator("input[placeholder='Lou Martin revient !']").input_value() == "Les vacances secrètes de Lou"
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_photo_page_4_de_la_gazette(navigateur, adresse, taille):
    """0.13 : choisir une des photos d'Immich proposées pour la page 4, demander 5 légendes, en prendre une."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/livret/2")
    page.get_by_role("heading", name="Lou Martin").wait_for()
    photos = page.get_by_role("radiogroup", name="Photo de la page 4")
    if not photos.is_visible():
        page.get_by_role("button", name="Chercher dans Immich").click()
    photos.locator("[aria-checked='false']").first.click()          # une autre que celle déjà choisie
    page.get_by_role("radiogroup", name="Cadrage").wait_for()
    page.get_by_role("button", name="5 légendes").click()
    leg = page.get_by_role("list", name="Légendes proposées").get_by_role("button").first
    leg.wait_for()
    leg.click()
    assert page.get_by_placeholder("(vide : pas de légende)").input_value() != ""
    page.get_by_placeholder("Bienvenue, Lou !").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_bouton_ia_de_la_gazette(navigateur, adresse, taille):
    """0.14 : le bouton « IA » du haut demande les aides de tous les blocs ; les propositions s'affichent sous chacun."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/livret/1")
    page.get_by_role("heading", name="Camille Fabre").wait_for()
    page.get_by_role("button", name="IA", exact=True).click()
    page.get_by_text("Propositions prêtes").wait_for(timeout=60000)
    titres = page.get_by_role("list", name="Propositions de l'IA : Titres").first
    titres.wait_for()
    titres.get_by_role("button").nth(1).click()                 # la première ligne est « Fermer »
    page.get_by_role("button", name="Enregistrer", exact=True).wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_page_trop_pleine_encadree_en_rouge(navigateur, adresse, taille):
    """0.15.2 : une page de La Récidive qui déborde à l'impression : ses réglages sont encadrés en rouge, avec un message."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    mot = page.get_by_role("textbox", name="Mot des hôtes")
    mot.fill(("Un très long mot des hôtes qui ne tiendra jamais sur la page, même en tout petit. " * 30).strip())
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.get_by_role("alert").filter(has_text="Page 4 trop pleine").wait_for()
    assert "border-destructive" in page.get_by_role("region", name="Page 4").get_attribute("class")
    sans_debordement(page)
    assert erreurs == []



@pytest.mark.parametrize("taille", TAILLES)
def test_valider_chaque_element_puis_approuver(navigateur, adresse, taille):
    """0.17 : chaque élément a Valider, IA, Changer (et Refuser s'il est facultatif) ; validé, il disparaît ;
    tout validé, il ne reste que le gros bouton Approuver."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    page.get_by_text("Montrer aussi les validés").or_(page.get_by_text("Revoir les éléments validés")).first.wait_for()
    if page.get_by_text("Revoir les éléments validés").is_visible():
        page.get_by_text("Revoir les éléments validés").click()
    else:
        page.get_by_label("Montrer aussi les validés").check()
    # Un mot court (un autre essai a pu remplir la page 4 jusqu'à déborder)
    page.get_by_role("textbox", name="Mot des hôtes").fill("Bienvenue, Lou.")
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.get_by_text("Enregistré.").wait_for()
    une = page.get_by_role("group", name="La une : N°, accroche, gros titre, macaron")
    assert une.locator("button[aria-label^='Refuser']").count() == 0                       # obligatoire : pas de Refuser
    assert une.locator("button[aria-label^='Un autre gros titre']").count() == 1
    page.get_by_label("Montrer aussi les validés").evaluate("e => { if (e.checked) e.click() }")
    for _ in range(40):                                  # valider tout ce qui reste, un élément après l'autre
        boutons = page.locator("button[aria-label^='Valider :']")
        if boutons.count() == 0:
            break
        n = boutons.count()
        nom = boutons.first.get_attribute("aria-label")
        boutons.first.click()
        try:
            page.wait_for_function(f"document.querySelectorAll(\"button[aria-label^='Valider :']\").length < {n}", timeout=8000)
        except Exception:
            restes = [b.get_attribute("aria-label") for b in page.locator("button[aria-label^='Valider :']").all()]
            raise AssertionError(f"reste après validation : {nom} ; {restes}")
    page.get_by_text("Tout est validé.").wait_for()
    assert page.get_by_role("button", name="Approuver La Récidive").is_visible()
    page.get_by_text("Revoir les éléments validés").click()
    page.get_by_role("group", name="La une : N°, accroche, gros titre, macaron").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_archives_et_simulation(navigateur, adresse, taille):
    """0.20 : la page Archives s'ouvre ; Réglages › Simuler crée une Récidive d'essai, qu'on supprime."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/archives")
    page.get_by_role("heading", name="Archives").wait_for()
    page.get_by_label("Chercher un nom").wait_for()
    page.goto(adresse + "/#/reglages")
    page.get_by_role("heading", name="Simuler un journal").wait_for()
    page.get_by_label("Contact de carnet").fill("lou")             # 0.24 : choisi dans les contacts de carnet
    page.get_by_role("list", name="Contacts de carnet").get_by_role("button", name="Lou Martin").click()
    page.get_by_role("button", name="Simuler", exact=True).click()
    page.get_by_text("Récidive d'essai (simulation)").wait_for()
    page.get_by_role("button", name="Supprimer l'essai").click()
    page.get_by_role("heading", name="Simuler un journal").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_livrets_sans_nouvelle_fiche_avec_sejour_annule(navigateur, adresse, taille):
    """0.24 : plus de bouton « Nouvelle fiche » ; « Séjour annulé » sur les séjours pas encore commencés."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.get_by_role("region", name="Séjours à venir").wait_for()
    assert page.get_by_role("button", name="Nouvelle fiche").count() == 0
    assert page.get_by_role("button", name="Séjour annulé").count() >= 1
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_connexion_ia_du_pc(navigateur, adresse, taille):
    """0.20.2 : la tuile « IA du PC » ouvre la marche à suivre : réglages, démarrage normal, pannes avec commandes.
    0.29 : fiche commune (contrat 3) ; le guide est celui d'ollama.guide, tel quel."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/connexion")
    page.get_by_role("button", name="IA du PC").click()
    panneau = page.get_by_role("article", name="IA du PC")
    panneau.get_by_role("heading", name="Allumer normalement").wait_for()
    panneau.get_by_role("heading", name="En cas de problème").wait_for()
    panneau.get_by_text("PC joignable, mais le modèle").click()            # une panne se déplie
    panneau.get_by_text("ollama list").first.wait_for()
    panneau.get_by_text("Installation (une seule fois").click()
    panneau.get_by_text("setx OLLAMA_HOST 0.0.0.0").wait_for()
    panneau.scroll_into_view_if_needed()
    if __import__("os").environ.get("CAPTURES"):
        page.screenshot(path=f"{__import__('os').environ['CAPTURES']}/gazette-ia-{taille}.png", full_page=True)
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_autres_propositions_second_modele(navigateur, adresse, taille):
    """0.22 : après 5 titres (modèle habituel), « Autres propositions (qwen) » refait la demande avec le second modèle :
    les nouvelles propositions remplacent les anciennes et le modèle utilisé est indiqué dessous."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    # un essai précédent a pu tout valider : montrer aussi les éléments validés
    page.get_by_text("Montrer aussi les validés").or_(page.get_by_text("Revoir les éléments validés")).first.wait_for()
    if page.get_by_text("Revoir les éléments validés").is_visible():
        page.get_by_text("Revoir les éléments validés").click()
    else:
        page.get_by_label("Montrer aussi les validés").check()
    une = page.get_by_role("region", name="Une")
    une.locator("input[aria-label='Description de la photo de la une']").fill("Lou sur une plage, lunettes de soleil")
    une.get_by_role("button", name="5 titres").click()
    une.get_by_text("« Les vacances secrètes de Lou »").wait_for()
    une.get_by_text("Modèle : mistral-nemo").wait_for()
    une.get_by_role("button", name="Autres propositions (qwen)").click()
    une.get_by_text("« La vérité éclate sur la plage »").wait_for()
    une.get_by_text("Modèle : qwen2.5:14b").wait_for()
    assert une.get_by_text("« Les vacances secrètes de Lou »").count() == 0          # remplacées, comme une nouvelle demande
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_autres_propositions_absent_sans_reglage(navigateur, adresse, taille):
    """0.22 : réglage « Second modèle de l'IA » vide : pas de bouton « Autres propositions » (Gazette, légende de la photo)."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/livret/2")
    page.get_by_role("heading", name="Lou Martin").wait_for()
    poser = "async (v) => (await fetch('/api/reglages', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({modele_second: v})})).status"
    assert page.evaluate(poser, "") == 200
    try:
        page.reload()
        page.get_by_role("heading", name="Lou Martin").wait_for()
        photos = page.get_by_role("radiogroup", name="Photo de la page 4")
        if not photos.is_visible():
            page.get_by_role("button", name="Chercher dans Immich").click()
        if not page.get_by_role("radiogroup", name="Cadrage").is_visible():
            photos.locator("[aria-checked='false']").first.click()
        page.get_by_role("button", name="5 légendes").click()
        legendes = page.get_by_role("list", name="Légendes proposées")
        legendes.get_by_text("Modèle : mistral-nemo").wait_for()
        assert legendes.get_by_role("button", name="Autres propositions").count() == 0
    finally:
        assert page.evaluate(poser, "qwen2.5:14b") == 200
    sans_debordement(page)
    assert erreurs == []


# ---------------------------------------------------------------- 0.23 : fiche complète d'une personne

def _ouvrir_fiche_de_lou(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    page.get_by_role("link", name="Fiche complète").first.click()
    page.get_by_text("Fiche complète · pour les journaux").wait_for()
    page.get_by_role("region", name="Jauge").wait_for()
    return page, erreurs


def _jauge(page) -> int:
    return int(page.get_by_role("progressbar", name="Pépites").get_attribute("aria-valuenow"))


@pytest.mark.parametrize("taille", TAILLES)
def test_fiche_complete(navigateur, adresse, taille):
    """Depuis La Récidive : rubriques repliables, exemples, suggestion → pépite, vrac rangé, jauge, interdits masqués."""
    from app import main
    page, erreurs = _ouvrir_fiche_de_lou(navigateur, adresse, taille)
    for famille in ("Vie et entourage", "Goûts et passions", "Caractère et manies", "Histoires", "Pour les journaux"):
        page.get_by_role("region", name=famille).wait_for()
    # sujets interdits masqués par défaut
    interdits = page.get_by_role("region", name="Sujets interdits")
    assert interdits.get_by_text("Le concours de chant raté").count() == 0
    interdits.get_by_role("button", name="Afficher").click()
    interdits.get_by_text("Le concours de chant raté").wait_for()
    interdits.get_by_role("button", name="Masquer").click()
    # déjà connu (carnet, Sillage) : une suggestion grisée devient une pépite d'un geste
    connu = page.get_by_role("region", name="Déjà connu")
    connu.get_by_text("Tour de Corse à vélo (2018)").or_(page.get_by_text("Tour de Corse à vélo (2018)")).first.wait_for()
    avant = _jauge(page)
    connu.get_by_role("button", name="Ajouter").first.click()
    page.wait_for_function(f"document.querySelector('[aria-label=Pépites]').getAttribute('aria-valuenow') == '{avant + 1}'")
    # une rubrique repliable : un exemple à toucher remplit le champ
    page.get_by_role("region", name="Caractère et manies").get_by_text("Peurs et phobies", exact=True).click()
    page.get_by_role("group", name="Exemples pour Peurs et phobies").get_by_role("button").first.click()
    assert page.get_by_label("Nouvelle pépite : Peurs et phobies").input_value() == "Peur des araignées"
    # vrac : rangé par mots-clés, modifiable avant d'ajouter
    texte = f"Déteste les endives ({taille})"
    page.get_by_label("Ligne vrac").fill(texte)
    page.wait_for_function("document.querySelector('[aria-label=\"Rubrique de la ligne vrac\"]')?.value === 'plats-detestes'")
    page.get_by_role("region", name="Vrac").get_by_role("button", name="Ajouter").click()
    page.get_by_text("Ajouté dans « Plats détestés ».").wait_for()
    page.wait_for_function(f"document.querySelector('[aria-label=Pépites]').getAttribute('aria-valuenow') == '{avant + 2}'")
    assert any(p["texte"] == texte for p in main.ETAT["carnet"]._fiche.personnes["pm-demo-lou"]["pepites"])
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_fiche_contact_introuvable(navigateur, adresse, taille):
    """Camille Fabre n'est pas dans carnet : message clair, rien à écrire."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/fiche/1")
    page.get_by_text("carnet ne trouve pas cette personne").wait_for()
    assert page.get_by_label("Ligne vrac").count() == 0
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_fiche_carnet_arrete_lecture_seule(navigateur, adresse, taille):
    """carnet arrêté : la dernière fiche lue s'affiche en lecture seule, « carnet injoignable »."""
    from app import main
    page, erreurs = _ouvrir_fiche_de_lou(navigateur, adresse, taille)
    faux = main.ETAT["carnet"]._fiche
    faux.arrete = True
    try:
        page.reload()
        page.get_by_text("carnet injoignable : fiche en lecture seule").wait_for()
        page.get_by_role("region", name="Goûts et passions").get_by_text("Plats aimés", exact=True).click()
        page.get_by_text("Adore les cannelés").wait_for()
        assert page.get_by_label("Ligne vrac").count() == 0 and page.get_by_role("button", name="Ajouter").count() == 0
        sans_debordement(page)
    finally:
        faux.arrete = False
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_banque_d_inspiration(navigateur, adresse, taille):
    """0.25 : Réglages › Banque d'inspiration (import d'un fichier), puis « Banque » dans La Récidive."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/reglages")
    zone = page.get_by_role("region", name="Banque d'inspiration")
    zone.wait_for()
    contenu = ("# RUMEURS\n- Selon nos informations, {prenom} aurait tenté d'adopter un rond-point.\n"
               "- D'après le facteur, {prenom} parlerait couramment le langage des chèvres.\n"
               "# TITRES\n- {prenom} démasqué{e} au rayon fromages\n")
    zone.get_by_label("Fichier de la banque").set_input_files(
        files=[{"name": "banque.txt", "mimeType": "text/plain", "buffer": contenu.encode()}])
    zone.get_by_text("banque.txt :").wait_for()
    sans_debordement(page)
    page.goto(page.url.split("#")[0] + "#/livrets")
    page.locator("a[href^='#/recidive/']").first.click()
    page.get_by_role("heading", name="Lou Martin").wait_for()
    rumeurs = page.get_by_role("region", name="Rumeurs")
    if not rumeurs.is_visible():                      # validées par un test précédent : les montrer
        revoir = page.get_by_role("button", name="Revoir les éléments validés")
        if revoir.count():
            revoir.click()
        else:
            page.get_by_label("Montrer aussi les validés").check()
    rumeurs.get_by_role("button", name="Banque").click()
    page.get_by_text("aurait tenté d'adopter un rond-point").first.wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_edition_speciale_eurovision(navigateur, adresse, taille):
    """0.28 : À traiter › Good Evening Europe! ouvre le numéro de la finale ; relecture, aperçu, nouveau tirage."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/a-traiter")
    page.get_by_role("button", name="Good Evening Europe!").click()
    page.get_by_role("link", name="Finale de démonstration · N° 2027 · Eurovision · Finale").click()
    page.get_by_role("heading", name="Finale de démonstration").wait_for()
    page.get_by_text("Le plus proche du vrai : Barnabé, à 4 places en moyenne du vrai classement").wait_for()
    page.get_by_role("group", name="Images de l'évènement").wait_for()
    page.get_by_title("Aperçu de l'édition spéciale").wait_for()
    page.get_by_role("button", name="Nouveau tirage").click()
    page.get_by_text("Entendu dans le salon").wait_for()
    sans_debordement(page)
    # La demi-finale : livret « qualifiés »
    page.goto(adresse + "/#/a-traiter")
    page.get_by_role("button", name="Good Evening Europe!").click()
    page.get_by_role("link", name="Première demi-finale de démonstration · N° 2027 · Eurovision · 1re demi-finale").click()
    page.get_by_text("livret « qualifiés »").first.wait_for()
    page.get_by_role("group", name="Rendez-vous samedi").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_eurovision_simuler_et_connexion(navigateur, adresse, taille):
    """0.28 : Réglages › Simuler fait un numéro d'essai d'une soirée de Douze points ; Connexion montre Douze points."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/reglages")
    page.get_by_role("button", name="Lire les soirées de Douze points").click()
    page.get_by_label("Soirée Douze points", exact=True).select_option("1")
    page.get_by_role("button", name="Simuler", exact=True).last.click()
    page.get_by_text("Numéro d'essai (simulation)").wait_for()
    page.get_by_role("button", name="Supprimer l'essai").click()
    page.get_by_role("heading", name="Simuler un journal").wait_for()
    page.get_by_text("Édition spéciale Eurovision", exact=True).wait_for()
    page.goto(adresse + "/#/connexion")
    page.get_by_role("button", name="Douze points").click()
    page.get_by_text("soirées Eurovision clôturées").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_reglages_paperless(navigateur, adresse, taille):
    """0.30 : section Paperless des Réglages (Paperless simulé dans la démo), sans erreur ni débordement."""
    page, erreurs = ouvrir(navigateur, adresse, taille, "#/reglages")
    sec = page.locator("section[aria-label=Paperless]")
    sec.wait_for()
    sec.get_by_text("Envoyer les numéros déjà approuvés").wait_for()
    sans_debordement(page)
    assert not erreurs


@pytest.mark.parametrize("taille", TAILLES)
def test_livret_pas_prepare_sans_ecran_fige(navigateur, adresse, taille):
    """0.31.4 : un livret vide (jamais préparé, ou remis à zéro par une annulation) montrait « Lecture… » sans fin
    (erreur de page) : il dit maintenant qu'il n'est pas préparé et propose de le préparer ou de supprimer la fiche."""
    from app import main
    b = main.ETAT["base"]
    pid = b.creer_personne("Noé Vide", "Noé", "1991-05-05")
    try:
        page, erreurs = ouvrir(navigateur, adresse, taille, f"#/livret/{pid}")
        page.get_by_text("Cette Gazette n'est pas préparée.").wait_for()
        page.get_by_role("button", name="Préparer la Gazette").wait_for()
        page.get_by_role("button", name="Supprimer la fiche").wait_for()
        sans_debordement(page)
        assert erreurs == []
    finally:
        b.supprimer_personne(pid)
