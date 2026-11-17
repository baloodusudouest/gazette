"""0.20 : archives (numéros approuvés, séjour fini) et essais (Réglages › Simuler, jamais comptés)."""
from datetime import date, timedelta

from app import main
from tests.test_recidive import _deux_sejours, ha, j, monter  # noqa: F401


def test_essai_de_recidive_et_de_gazette(monter):
    c = monter()
    pid, r = _deux_sejours(c)
    vraie = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    lien = c.post("/api/essais", json={"personne_id": pid, "journal": "recidive"}).json()["lien"]
    rid = int(lien.rsplit("/", 1)[1])
    ed = c.get(f"/api/recidives/{rid}").json()["edition"]
    assert ed["essai"] == 1 and ed["photos"] and rid != vraie
    assert all(x["id"] != rid for x in c.get("/api/livrets").json()["recidives"])          # jamais dans les livrets
    assert all(x.get("recidive") != rid for x in c.get("/api/a-traiter").json().get("recidives", []))
    r2 = c.post(f"/api/recidives/{rid}/approuver").json()
    assert r2["carnet"].startswith("essai") and main.ETAT["base"].publies(pid) == set()     # rien de publié
    assert {x["journal"] for x in c.get("/api/essais").json()["essais"]} == {"recidive"}
    # Gazette d'essai : une fiche à part, jamais reliée à Home Assistant ni dans la liste des livrets
    lien = c.post("/api/essais", json={"personne_id": pid, "journal": "gazette"}).json()["lien"]
    gid = int(lien.rsplit("/", 1)[1])
    assert c.get(f"/api/livrets/{gid}").json()["personne"]["essai_de"] == pid
    assert all(x["id"] != gid for x in c.get("/api/livrets").json()["livrets"])
    assert main.ETAT["base"].trouver("Camille Fabre")["id"] == pid
    assert len(c.get("/api/essais").json()["essais"]) == 2
    assert c.delete(f"/api/essais/gazette/{gid}").status_code == 200
    assert c.delete(f"/api/essais/recidive/{rid}").status_code == 200
    assert c.get("/api/essais").json()["essais"] == []
    assert c.delete(f"/api/essais/recidive/{vraie}").status_code == 404                      # jamais une vraie édition


def test_archives(monter):
    c = monter()
    pid = c.post("/api/personnes", json={"nom": "Camille Fabre", "naissance": "1988-07-07"}).json()["id"]
    ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(-40), "jusqu_au": j(-38)})
    r = ha(c, {"chambre": "ami", "noms": ["Camille Fabre"], "du": j(10), "jusqu_au": j(12)}).json()
    rid = int(r["invites"][0]["lien"].rsplit("/", 1)[1])
    assert c.get("/api/archives").json()["archives"] == []                                   # Gazette pas approuvée
    main.ETAT["base"].maj_livret(pid, etat="approuve", approuve_le="2026-01-01")
    a = c.get("/api/archives").json()["archives"]
    assert [x["journal"] for x in a] == ["gazette"] and a[0]["sejour"]["du"] == j(-40)
    d = c.get("/api/livrets").json()
    assert d["archives"] == 1 and all(x["id"] != pid for x in d["livrets"])                  # quitte la liste
    main.ETAT["base"].maj_recidive(rid, etat="approuve")
    assert [x["journal"] for x in c.get("/api/archives").json()["archives"]] == ["gazette"]   # séjour à venir : pas encore
    with main.ETAT["base"]._verrou, main.ETAT["base"]._c:
        main.ETAT["base"]._c.execute("UPDATE sejours SET jusqu_au = ? WHERE du = ?", ((date.today() - timedelta(days=1)).isoformat(), j(10)))
    a = c.get("/api/archives").json()["archives"]
    assert [x["journal"] for x in a] == ["recidive", "gazette"] and a[0]["numero"] == 2
