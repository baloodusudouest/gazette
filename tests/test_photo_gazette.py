"""0.13 : Gazette classique — photo d'Immich en page 4 (6 au choix, noir et blanc, légende façon presse de l'époque
proposée par l'IA) et code-barres clin d'œil."""
from app import code_barres, main
from app import ollama as O
from app import rendu
from tests.test_recidive import _faux_ollama, monter  # noqa: F401


def _fiche(c):
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    c.post(f"/api/livrets/{pid}/preparer", json={})
    return pid


def test_six_photos_proposees_et_choix(monter):
    c = monter()
    pid = _fiche(c)
    lv = c.get(f"/api/livrets/{pid}").json()["livret"]
    assert len(lv["photos_choix"]) == 6 and lv["photo"] == {} and lv["immich"]          # 8 photos d'Immich : 6 étalées
    assert lv["code_barres_defaut"] == "Bienvenue, Camille !"
    html = c.get(f"/api/livrets/{pid}/apercu").text
    assert 'class="cliche"' not in html and "<svg" in html and "✦ ✦ ✦" in html          # sans photo : page 4 d'avant
    x = lv["photos_choix"][2]
    assert c.get(f"/api/livrets/{pid}/photos/{x['id']}").status_code == 200
    assert c.get(f"/api/livrets/{pid}/photos/zzzzzzzz-0000").status_code == 404
    # Une photo hors des 6 proposées est refusée (aucune photo)
    c.put(f"/api/livrets/{pid}", json={"photo": {"id": "cccccccc-9999"}})
    assert c.get(f"/api/livrets/{pid}").json()["livret"]["photo"] == {}
    c.put(f"/api/livrets/{pid}", json={"photo": {"id": x["id"], "cadrage": "centre", "legende": "Mlle Fabre, en villégiature."},
                                       "code_barres": "Coucou Camille, bon séjour à vous !"})
    lv = c.get(f"/api/livrets/{pid}").json()["livret"]
    assert lv["photo"]["date"] == x["date"] and lv["photo"]["cadrage"] == "centre"
    assert len(lv["code_barres"]) == code_barres.MAXI
    html = c.get(f"/api/livrets/{pid}/apercu").text
    assert 'class="cliche"' in html and "data:image/jpeg;base64," in html and "Mlle Fabre, en villégiature." in html
    assert "✦ ✦ ✦" not in html and 'img alt="" class="centre"' in html
    # Retirer la photo
    c.put(f"/api/livrets/{pid}", json={"photo": None})
    assert 'class="cliche"' not in c.get(f"/api/livrets/{pid}/apercu").text


def test_legendes_proposees_par_l_ia(monter):
    c = monter()
    pid = _fiche(c)
    x = c.get(f"/api/livrets/{pid}").json()["livret"]["photos_choix"][0]
    assert c.post(f"/api/livrets/{pid}/photo/proposer", json={"description": "à la plage"}).status_code == 409
    c.put(f"/api/livrets/{pid}", json={"photo": {"id": x["id"]}})
    faux = _faux_ollama(["1. Mlle Camille, photographiée sur la côte basque\n2. Notre envoyée spéciale prend le soleil"])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    assert c.post(f"/api/livrets/{pid}/photo/proposer", json={"description": ""}).status_code == 422    # rien pour l'IA
    r = c.post(f"/api/livrets/{pid}/photo/proposer", json={"description": "Camille à la plage, chapeau de paille"}).json()
    assert r["propositions"] == ["Mlle Camille, photographiée sur la côte basque", "Notre envoyée spéciale prend le soleil"]
    prompt = faux.appels[-1][1]["prompt"]
    assert "de 1988" in prompt and "chapeau de paille" in prompt and "90 caractères" in prompt
    lv = c.get(f"/api/livrets/{pid}").json()["livret"]
    assert lv["photo"]["propositions"] == r["propositions"] and lv["photo"]["legende"] == ""    # rien choisi à sa place
    # Enregistrer la légende garde description et propositions
    c.put(f"/api/livrets/{pid}", json={"photo": {"id": x["id"], "legende": r["propositions"][0], "description": "Camille à la plage, chapeau de paille"}})
    assert c.get(f"/api/livrets/{pid}").json()["livret"]["photo"]["propositions"] == r["propositions"]


def test_sans_immich_page_4_inchangee(monter):
    c = monter(immich=False)
    pid = _fiche(c)
    lv = c.get(f"/api/livrets/{pid}").json()["livret"]
    assert lv["photos_choix"] == [] and not lv["immich"]
    assert "pas réglé" in c.post(f"/api/livrets/{pid}/photos").json()["message"]
    assert rendu.message_code_barres("Marie-Christine") == "Bienvenue, Marie-Christine !"
