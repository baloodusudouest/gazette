"""Gazette ne fait que lire ses sources (socle, leçons § 6) : trois preuves."""
import re
from pathlib import Path

import httpx
import pytest

from app.base import Base
from app.sources import Sources, SourceIndisponible


@pytest.fixture()
def src(tmp_path):
    demandes = []

    def faux(req: httpx.Request) -> httpx.Response:
        demandes.append(req)
        if "query.wikidata.org" in req.url.host:
            return httpx.Response(200, json={"results": {"bindings": [
                {"t": {"value": "Exemple"}, "n": {"value": "12"}, "h": {"value": "true"}}]}})
        if "larousse" in req.url.host:
            return httpx.Response(200, text='<li date="01/07/1988"><div class="complet"><b>Test.</b> Un fait.</div></li>')
        return httpx.Response(200, text="== Événements ==")

    b = Base(tmp_path / "t.db")
    s = Sources(b, pause=0)
    s._client = httpx.Client(transport=httpx.MockTransport(faux), headers={"User-Agent": "test"})
    yield s, demandes
    b.fermer()


def test_seules_des_lectures_sont_envoyees(src):
    s, demandes = src
    s.wikipedia("Juillet 1988")
    s.wikipedia("July 1988", "en")
    s.larousse(1988, 7)
    assert s.wikidata(["Exemple"]) == {"Exemple": {"n": 12, "humain": True}}
    # Tout est GET, sauf la requête SPARQL (une lecture envoyée en POST, adresse fixe)
    for r in demandes:
        assert r.method == "GET" or (r.method == "POST" and str(r.url) == "https://query.wikidata.org/sparql")
    # Le cache évite toute nouvelle demande
    n = len(demandes)
    s.wikipedia("Juillet 1988"); s.larousse(1988, 7); s.wikidata(["Exemple"])
    assert len(demandes) == n


def test_lecture_coupee(tmp_path):
    s = Sources(Base(tmp_path / "v.db"), actives=False)
    with pytest.raises(SourceIndisponible):
        s.wikipedia("Juillet 1988")


def test_le_client_ne_contient_aucune_ecriture():
    code = Path(__file__).resolve().parents[1].joinpath("app", "sources.py").read_text()
    assert not re.search(r"\.(put|patch|delete)\(", code)
    assert len(re.findall(r"\.post\(", code)) == 1 and "query.wikidata.org/sparql" in code
