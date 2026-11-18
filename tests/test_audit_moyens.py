"""0.20.9 (constats moyens de l'audit du 17/11/2026) : redirections Wikipédia bornées (M19), rendu sans réseau (M16)."""
from __future__ import annotations

import http.server
import socket
import threading

import httpx
import pytest

from app import rendu
from app.base import Base
from app.sources import REDIRECTIONS_MAXI, Sources


# ------------------------------------------------------------ M19 : boucle de redirections
def test_boucle_de_redirections_bornee(tmp_path):
    """Deux pages inventées qui se renvoient l'une à l'autre : trois redirections suivies, puis on s'arrête."""
    demandes = []

    def faux(req: httpx.Request) -> httpx.Response:
        demandes.append(str(req.url))
        cible = "Page Beta" if "Page_Alpha" in str(req.url) else "Page Alpha"
        return httpx.Response(200, text=f"#REDIRECTION [[{cible}]]")

    b = Base(tmp_path / "t.db")
    s = Sources(b, pause=0)
    s._client = httpx.Client(transport=httpx.MockTransport(faux), headers={"User-Agent": "test"})
    try:
        assert s.wikipedia("Page Alpha") == ""
        assert len(demandes) == REDIRECTIONS_MAXI + 1 == 4
        s.wikipedia("Page Alpha")                 # gardé : aucune nouvelle demande
        assert len(demandes) == 4
    finally:
        b.fermer()


def test_une_redirection_simple_reste_suivie(tmp_path):
    def faux(req: httpx.Request) -> httpx.Response:
        if "Ancien_nom" in str(req.url):
            return httpx.Response(200, text="#REDIRECTION [[Nouveau nom]]")
        return httpx.Response(200, text="== Événements ==")

    b = Base(tmp_path / "t.db")
    s = Sources(b, pause=0)
    s._client = httpx.Client(transport=httpx.MockTransport(faux), headers={"User-Agent": "test"})
    try:
        assert s.wikipedia("Ancien nom") == "== Événements =="
    finally:
        b.fermer()


# ------------------------------------------------------------ M16 : aucune requête sortante pendant le rendu
def test_adresses_permises():
    assert rendu.permise("data:image/png;base64,AAAA")
    assert not rendu.permise("file:///data/gazette.db")
    assert rendu.permise("about:blank")
    for url in ("http://127.0.0.1:9/x.png", "https://exemple.invalid/a.css", "ws://exemple.invalid/", "//exemple.invalid/x"):
        assert not rendu.permise(url), url


@pytest.fixture
def serveur_espion():
    """Petit serveur local qui note chaque demande reçue (il joue le rôle d'un site extérieur)."""
    recues = []

    class Espion(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            recues.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()

        def log_message(self, *a):
            pass

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Espion)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}", recues
    srv.shutdown()


def test_le_rendu_ne_sort_pas_sur_le_reseau(serveur_espion):
    url, recues = serveur_espion
    doc = (f'<!doctype html><html><head><link rel="stylesheet" href="{url}/style.css"></head><body>'
           f'<div class="page" data-page="1"><img src="{url}/image.png"><p>Texte inventé</p></div>'
           f'<script>fetch("{url}/fetch").catch(()=>{{}});window.deborde=()=>false;window.mesure=()=>[]</script>'
           f'</body></html>')
    try:
        contenu, _ = rendu.pdf(doc, "lecture")
        rendu.mesurer(doc)
    except rendu.RenduImpossible as ex:
        pytest.skip(f"Chromium absent : {ex}")
    assert contenu.startswith(b"%PDF")
    assert recues == []
