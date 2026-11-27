"""0.23 : aucun test ne sort sur le réseau vers carnet (fiche complète) ni vers Sillage. Par défaut, carnet répond comme
une version d'avant 2.33 (route de la fiche absente : 404 « Not Found ») et Sillage ne connaît personne ; les tests de la
fiche injectent leurs propres simulations (`ETAT["carnet_fiche"]`, `ETAT["sillage_lire"]`)."""
import pytest

from app import carnet, douze_points, sillage


@pytest.fixture(autouse=True)
def _sans_reseau_fiche(monkeypatch):
    monkeypatch.setattr(carnet, "_fiche_http", lambda url, jeton, methode, chemin, corps: (404, {"detail": "Not Found"}))
    monkeypatch.setattr(sillage, "_lire_http", lambda url, jeton, immich_id: {"contrat": 1, "etapes": []})
    # 0.31 : nouveautés de Sillage pour La Récidive : rien par défaut (les tests injectent `ETAT["sillage_nouveautes"]`)
    monkeypatch.setattr(sillage, "_lire_nouveautes_http", lambda url, jeton, immich_id, depuis: {"contrat": 1, "etapes": []})


def _douze_hors_reseau(url, jeton, chemin):
    raise RuntimeError("test : aucun accès réseau à Douze points")


@pytest.fixture(autouse=True)
def _sans_reseau_douze(monkeypatch):
    """0.28 : aucun test ne sort vers Douze points ; les tests d'Eurovision injectent `ETAT["douze_lire"]`."""
    monkeypatch.setattr(douze_points, "_lire_http", _douze_hors_reseau)
