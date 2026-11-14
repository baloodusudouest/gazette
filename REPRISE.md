# Reprise — Gazette

À lire en premier ; mis à jour dans le même commit que le code.

## État (14/11/2026) — 0.1.0, temps 1 livré, jamais essayé sur le NAS
- Appli complète : fiches, livrets, relecture, aperçu, PDF à imprimer et lecture, À traiter, Connexion, Réglages, porte HA (`/ha/sejour`, `/ha/etat`).
- Moteur essayé en vrai (réseau) sur trois dates maigres du banc (1964, 1983, 1997) : une, brèves, semaine, chronologie, nés et disparus remplis ; rendu PDF contrôlé à l'œil (aucun débordement).
- 33 tests (`python -m pytest -q`), sans réseau : pages de sources inventées (`tests/fixtures.py`).
- Package HA `chambres/gazette.yaml` v1.0 : pas dans ce dépôt (il nomme les chambres et le téléphone de la maison) ; sa copie de référence est décrite dans le master doc Home Assistant (§ 6.1 et § 10). Contrat de la porte : `docs/dossier.md`, section « Temps 1 tel que construit ».

## Prochaine étape
1. Installer : service `gazette` ajouté à `homelab.yml` le 14/11 (port **8089** sur le NAS, 8099 dans le conteneur : 8099 est pris par la vérification des dates), variables `GAZETTE_*`, dossier `${DOCKER_ROOT}/gazette` ; vérifier `/health` puis la tuile « Rendu PDF » de Connexion.
2. Créer les fiches des proches attendus, relire, approuver, imprimer un livret à la main (recto-verso bord court) : c'est l'essai demandé avant l'impression IPP.
3. Installer le package HA, vérifier au premier séjour : noms reçus, dates (`sejour_fin` − 1 h = dernier jour), notification.
4. Temps 3 : impression IPP (`GAZETTE_IMPRIMANTE`), seulement après l'essai du recto-verso.

## Pièges
- Dépôt public : aucun nom réel, aucune date de naissance réelle, aucun lieu ni adresse. Titre, signature et lieu par variables. Rien de Larousse dans le dépôt (ni texte ni page en cache).
- Wikipédia : User-Agent descriptif obligatoire, pauses entre deux pages ; une première préparation prend une à deux minutes. Le cache (`sources` dans `gazette.db`) rend les suivantes instantanées.
- Le PDF demande Chromium dans l'image (≈ 400 Mo) : sans lui, l'aperçu marche, le PDF répond 503 et l'approbation ne contrôle plus les débordements.
- Impression recto-verso « bord court » pour l'imposition paysage.
