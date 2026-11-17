"""0.12 : aides de l'IA pour la Gazette classique ; contexte Immich (albums parlants, personnes) pour La Récidive."""
from app import immich as I
from app import main
from app import ollama as O
from tests.test_recidive import IMMICH_CAMILLE, _deux_sejours, _faux_immich, _faux_ollama, _photos_camille, monter  # noqa: F401


def test_versions_separateur_ou_numeros():
    brut = "Version 1 : Le maire inaugure le pont.\n---\n**Le pont est ouvert, dit le maire.**\n---\nJe ne peux pas écrire cela\n---\nx"
    assert O.versions(brut, "journal", 200) == ["Le maire inaugure le pont.", "Le pont est ouvert, dit le maire."]
    assert O.versions("1. Premier texte assez long\n2. Second texte assez long", "raccourcir", 100) == [
        "Premier texte assez long", "Second texte assez long"]
    assert O.versions("1. Un titre\n2. Un titre beaucoup trop long pour tenir", "titres", 20) == ["Un titre"]
    prompt, n, maxi = O.consigne_gazette("raccourcir", "a" * 400, 1988, 120, "Camille", "femme", "", "")
    assert n == 3 and maxi == 135 and "120 caractères au plus" in prompt
    assert "de 1988" in O.consigne_gazette("journal", "Un texte.", 1988, None, "", "", "", "")[0]


def test_route_ia_du_livret(monter):
    c = monter()
    pid, _ = _deux_sejours(c)
    assert c.post(f"/api/livrets/{pid}/ia", json={"action": "titres", "texte": "Un long texte d'article."}).status_code == 503
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux_ollama(["1. Le pont inauguré\n2. Fête au village"]))
    r = c.post(f"/api/livrets/{pid}/ia", json={"action": "titres", "texte": "Le maire a inauguré le pont du village."})
    assert r.json()["propositions"] == ["Le pont inauguré", "Fête au village"]
    assert c.post(f"/api/livrets/{pid}/ia", json={"action": "autre", "texte": "xxxxxxxxxxxx"}).status_code == 422
    assert c.post(f"/api/livrets/{pid}/ia", json={"action": "journal", "texte": "court"}).status_code == 422


def test_albums_generiques():
    for nom in ("2019", "Photos 2019", "Divers", "Pense-bête", "Pense bêtes", "Août 2021", "À trier", "WhatsApp Images", "  "):
        assert I.album_generique(nom), nom
    for nom in ("Noël 2019", "Mariage de Léa", "Vendanges 2023", "Week-end à Biarritz"):
        assert not I.album_generique(nom), nom


def _immich_albums(base, albums, gens):
    """Immich simulé avec albums (/albums?assetId=) et personnes (/assets/{id})."""
    def lire(methode, chemin, corps=None):
        if chemin.startswith("/albums?assetId="):
            return albums.get(chemin.split("=", 1)[1], [])
        if chemin == "/search/metadata" and corps and "albumIds" in corps:
            return {"assets": {"items": [{"id": "cccccccc-0001"}, {"id": "cccccccc-0002"}], "nextPage": None}}
        if chemin.startswith("/assets/") and "/thumbnail" not in chemin:
            return {"people": gens.get(chemin.rsplit("/", 1)[1], [])}
        return base(methode, chemin, corps)
    return lire


def test_contexte_d_une_photo(tmp_path):
    albums = {"aaaaaaaa-0001": [{"id": "al-1", "albumName": "Vendanges 2023"}, {"id": "al-2", "albumName": "2023"},
                                {"id": "al-3", "albumName": "Divers"}]}
    gens = {"aaaaaaaa-0001": [{"id": IMMICH_CAMILLE, "name": "Camille Fabre"}, {"id": "p-yves", "name": "Bastien Martin"},
                              {"id": "p-x", "name": ""}],
            "cccccccc-0001": [{"id": "p-lea", "name": "Léa"}], "cccccccc-0002": [{"id": "p-yves", "name": "Bastien Martin"}]}
    im = I.Immich("http://immich", "cle", tmp_path, lire=_immich_albums(lambda *a: None, albums, gens))
    assert im.contexte("aaaaaaaa-0001", IMMICH_CAMILLE) == {"albums": ["Vendanges 2023"], "personnes": ["Bastien", "Léa"]}
    assert im.contexte("aaaaaaaa-0009", IMMICH_CAMILLE) == {"albums": [], "personnes": []}

    def refus(methode, chemin, corps=None):
        raise RuntimeError("clé refusée")
    assert I.Immich("http://immich", "cle", tmp_path, lire=refus).contexte("aaaaaaaa-0001") == {"albums": [], "personnes": []}
    texte = O.texte_contexte({"albums": ["Vendanges 2023"], "personnes": ["Bastien", "Léa"]})
    assert texte == "album « Vendanges 2023 » ; avec Bastien, Léa"
    prompt = O.consigne("", "photo", "femme", "Camille", contexte={"albums": ["Vendanges 2023"], "personnes": ["Bastien"]})
    assert "Vendanges 2023" in prompt and "ceux des personnes citées (Bastien)" in prompt and "Ce que montre" not in prompt


def test_proposer_avec_le_contexte_sans_description(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    photo = ed["photos"][1]["id"]
    assert ed["photos"][1]["contexte"] == {"albums": [], "personnes": []}         # Immich simulé sans albums
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=_faux_ollama([]))
    assert c.post(f"/api/recidives/{rid}/proposer", json={"cible": photo, "description": ""}).status_code == 422
    # Un album parlant et une personne : la description devient facultative
    albums = {photo: [{"id": "al-1", "albumName": "Vendanges 2023"}]}
    main.ETAT["immich"]._lire = _immich_albums(_faux_immich(_photos_camille()), albums, {photo: [{"id": "p-y", "name": "Bastien"}]})
    eds = main.ETAT["base"].recidive(rid)
    main.ETAT["base"].maj_recidive(rid, photos=[{k: v for k, v in x.items() if k != "contexte"} for x in eds["photos"]])
    faux = _faux_ollama(["1. Bastien et Camille, complices aux vendanges"])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    props = c.post(f"/api/recidives/{rid}/proposer", json={"cible": photo, "description": ""}).json()["propositions"]
    assert props == ["Bastien et Camille, complices aux vendanges"]
    assert "Vendanges 2023" in faux.appels[-1][1]["prompt"]
    gardee = next(x for x in c.get(f"/api/recidives/{rid}").json()["edition"]["photos"] if x["id"] == photo)
    assert gardee["contexte"] == {"albums": ["Vendanges 2023"], "personnes": ["Bastien"]}
    # Les rumeurs reçoivent albums et prénoms permis
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=(f2 := _faux_ollama(["1. Selon nos sources, Camille parle aux ceps."])))
    c.post(f"/api/recidives/{rid}/rumeurs", json={"indices": ""})
    assert "Vendanges 2023" in f2.appels[-1][1]["prompt"] and "(Bastien)" in f2.appels[-1][1]["prompt"]


def test_chiffres_en_emoji_retires():
    """0.14.1 : « 1️⃣ Sagittaire : … » (vu chez Julien le 17/11) → « Sagittaire : … »."""
    assert O.sans_numero("1️⃣ Sagittaire : Jupiter vous invite à sortir") == "Sagittaire : Jupiter vous invite à sortir"
    assert O.sans_numero("🔟 Dix sur dix ✨ pour Camille 🎉") == "Dix sur dix pour Camille"
    assert O.sans_numero("3. Le nombre 3 est votre sésame") == "Le nombre 3 est votre sésame"
    assert O.nettoyer("1️⃣ Camille encore prise la main dans le sac\n2️⃣ Scandale au barbecue", "femme") == [
        "Camille encore prise la main dans le sac", "Scandale au barbecue"]


def test_horoscope_brode_sur_l_evenement(monter):
    """0.15 : l'événement du séjour (case de l'édition, jamais imprimé) est donné à l'IA pour l'horoscope, et gardé pour
    les séjours suivants."""
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    faux = _faux_ollama(["1. Les astres prédisent une victoire de la Suède grâce à votre costume de tigre."])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    ev = "soirée Eurovision, dort à la maison pour ne pas rentrer trop tard"
    props = c.post(f"/api/recidives/{rid}/horoscope", json={"evenement": ev}).json()["propositions"]
    assert props and "costume de tigre" in props[0]
    prompt = faux.appels[-1][1]["prompt"]
    assert ev in prompt and "brode dessus" in prompt and "Séjours précédents" not in prompt
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["evenement"] == ev
    c.put(f"/api/recidives/{rid}", json={"horoscope": props[0]})
    assert ev not in c.get(f"/api/recidives/{rid}/apercu").text                 # jamais imprimé
    # Sans événement : consigne d'avant
    assert "brode dessus" not in O.consigne_horoscope("Cancer", "", "femme", "Camille")
    assert "2025 : mariage" in O.consigne_horoscope("Cancer", "", "femme", "Camille", avant=["2025 : mariage"])


def test_approuver_envoie_tout_a_carnet(monter):
    """0.16 : à l'approbation, indices, événement, descriptions et textes imprimés partent sur la fiche de carnet
    (« Journaux parus ») ; les numéros suivants les relisent depuis carnet."""
    envois, indices = [], []
    c = monter()
    main.ETAT["carnet_paru"] = lambda url, jeton, pid, cle, corps: envois.append((pid, cle, corps))
    main.ETAT["carnet_ecrire"] = lambda url, jeton, pid, texte: indices.append(texte)
    main.ETAT["carnet"]._paru = main.ETAT["carnet_paru"]
    main.ETAT["carnet"]._ecrire = main.ETAT["carnet_ecrire"]
    for x in main.ETAT["carnet"].personnes(forcer=True):
        x["personne_id"] = "p-camille0001"
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    photo = ed["photos"][1]["id"]
    c.put(f"/api/recidives/{rid}", json={"titre_une": "Camille récidive !", "evenement": "soirée Eurovision",
                                         "indices_rumeurs": "fan de pétanque", "rumeurs": ["Selon nos sources, Camille parle aux ceps."],
                                         "horoscope": "Pluton percute le Cancer.",
                                         "photos": [{"id": photo, "legende": "Flagrant délit", "description": "Camille en tigre"}]})
    r = c.post(f"/api/recidives/{rid}/approuver").json()
    assert r["carnet"] == "rangé sur la fiche de carnet"
    pid_c, cle, corps = envois[-1]
    assert cle == f"recidive-{ed['sejour_du']}" and corps["numero"] == 2 and corps["evenement"] == "soirée Eurovision"
    assert corps["descriptions"] == ["Camille en tigre"] and corps["indices"] == "fan de pétanque"
    assert {"Camille récidive !", "Flagrant délit", "Selon nos sources, Camille parle aux ceps.", "Pluton percute le Cancer."} <= set(corps["textes"])
    assert indices == ["fan de pétanque"]
    # Le numéro suivant relit la fiche de carnet : événement et textes, même sans la base de Gazette
    x = main.ETAT["carnet"].personnes()[0]
    assert x["parus"][0]["evenement"] == "soirée Eurovision"
    main.ETAT["base"].maj_recidive(rid, evenement="", etat="a_relire")
    autre = {**main.ETAT["base"].recidive(rid), "id": -1, "sejour_du": "2099-01-01"}
    assert main._evenements_avant(pid, autre) == [f"{ed['sejour_du'][:4]} : soirée Eurovision"]
    assert "Flagrant délit" in main._deja_paru(pid, 0)
    # Carnet injoignable : l'approbation reste faite, un message le dit
    def panne(*a):
        raise ConnectionError("carnet arrêté")
    main.ETAT["carnet"]._paru = panne
    r = c.post(f"/api/recidives/{rid}/approuver").json()
    assert r["ok"] and r["carnet"].startswith("pas envoyé à carnet")


def test_reglages_de_la_recidive(monter):
    """0.18 : titre du magazine, accroches et droit de réponse par défaut réglables (Réglages › La Récidive)."""
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    reg = c.get("/api/reglages").json()
    assert reg["journal"]["r_titre"] == "La Récidive" and "r_mot_modele" in reg["champs"]
    assert c.put("/api/reglages/journal", json={"r_titre": ""}).status_code == 422
    r = c.put("/api/reglages/journal", json={"r_titre": "Le Fouineur", "r_accroche_femme": "{prenom} a encore frappé",
                                              "r_mot_modele": "{salut}, on recommence quand vous voulez."})
    assert r.status_code == 200
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["accroche_defaut"] == "Camille a encore frappé"
    assert ed["mot_defaut"] == "Chère Camille, on recommence quand vous voulez."
    c.put(f"/api/recidives/{rid}", json={"accroche": "", "mot": ""})
    html = c.get(f"/api/recidives/{rid}/apercu").text
    assert "Le Fouineur</h1>" in html and "Camille a encore frappé" in html and "on recommence quand vous voulez" in html


def test_filtres_017_1():
    """0.18.1 : « 1°) » retiré ; rien sur le corps ; l'exemple de broderie n'est plus l'Eurovision."""
    assert O.sans_numero("1°) Camille, la Sagittaire joueuse") == "Camille, la Sagittaire joueuse"
    assert O.sans_numero("2°. Saturne suggère") == "Saturne suggère"
    assert O.nettoyer("1. Ses seins rebondis font scandale\n2. Camille dresse des escargots", "femme", 130) == ["Camille dresse des escargots"]
    brut = ("Lettre : Depuis l'arrivée de cette humaine aux seins rebondis, notre chat miaule.\nSignature : Une voisine\n"
            "Réponse : Demande en mariage.\n\nLettre : Mes robinets chantent depuis son passage.\nSignature : Les robinets\nRéponse : Playback.")
    assert [x["lettre"] for x in O.lettres(brut, "femme")] == ["Mes robinets chantent depuis son passage."]
    p = O.consigne_horoscope("Sagittaire", "", "femme", "Camille", evenement="apéro avec le travail")
    assert "Eurovision" not in p and "apéro avec le travail" in p and "n'en reprends AUCUN mot" in p


def test_droit_de_reponse_par_l_ia(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    faux = _faux_ollama(["Chère Camille, nous assumons tout.\n---\nChère Camille, coupables et ravis.\n---\nx"])
    main.ETAT["ollama"] = O.Ollama("http://pc:11434", lire=faux)
    c.put(f"/api/recidives/{rid}", json={"evenement": "apéro avec le travail"})
    props = c.post(f"/api/recidives/{rid}/mot", json={"texte": ""}).json()["propositions"]
    assert props == ["Chère Camille, nous assumons tout.", "Chère Camille, coupables et ravis."]
    assert "apéro avec le travail" in faux.appels[-1][1]["prompt"] and "Droit de réponse" in faux.appels[-1][1]["prompt"]
