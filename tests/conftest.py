"""0.23 : aucun test ne sort sur le réseau vers carnet (fiche complète) ni vers Sillage. Par défaut, carnet répond comme
une version d'avant 2.33 (route de la fiche absente : 404 « Not Found ») et Sillage ne connaît personne ; les tests de la
fiche injectent leurs propres simulations (`ETAT["carnet_fiche"]`, `ETAT["sillage_lire"]`)."""
import pytest

from app import carnet, sillage


@pytest.fixture(autouse=True)
def _sans_reseau_fiche(monkeypatch):
    monkeypatch.setattr(carnet, "_fiche_http", lambda url, jeton, methode, chemin, corps: (404, {"detail": "Not Found"}))
    monkeypatch.setattr(sillage, "_lire_http", lambda url, jeton, immich_id: {"contrat": 1, "etapes": []})
