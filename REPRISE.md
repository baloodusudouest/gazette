# Reprise — Gazette

À lire en premier ; mis à jour dans le même commit que le code.

## État (14/11/2026) — 0.5.0, temps 1 livré + top 5 culturel + journal réglé dans l'appli + texte complet + aide à la place + carnet, installé sur le NAS le 14/11 (pas encore de vrai livret)
- Appli complète : fiches, livrets, relecture, aperçu, PDF à imprimer et lecture, À traiter, Connexion, Réglages, porte HA (`/ha/sejour`, `/ha/etat`).
- Moteur essayé en vrai (réseau) sur trois dates maigres du banc (1964, 1983, 1997) : une, brèves, semaine, chronologie, nés et disparus remplis ; rendu PDF contrôlé à l'œil (aucun débordement).
- Top 5 culturel : fichier livré dans `app/donnees/`, remplaçable depuis Réglages (fichier importé gardé dans `/data/culture.csv`) ; prompt de mise à jour annuelle dans `app/donnees/prompt_culture.md` (il nomme les années 2026 et 2027 : à adapter chaque année).
- Texte complet (0.4.0) : rien n'est coupé ; la taille du texte baisse page par page (variable CSS `--k`, script `AJUSTER` de `rendu.py`, plancher 0,84) ; la place est tenue en amont par `BUDGET_P2`, `LONG_P2`, `BUDGET_BREVES` (`regles.py`). Essayé sur six dates (1953, 1964, 1972, 1983, 1988, 1997) : aucun débordement.
- Page trop pleine (0.5.0) : chaque bloc du rendu porte `data-bloc` (`une`, `breve:i`, `p2:i`, `chrono:i`, `musique`, `cinema`, `mot`) ; `window.mesure()` (script `AJUSTER`) rend hauteurs et excès ; `lib/place.js` estime en direct (partie fixe `FIXE` + part proportionnelle aux signes, relevée sur des mesures) et dit quelles propositions tiennent.
- Carnet (0.6.0) : `app/carnet.py` lit `GET /gazette/personnes` de carnet ≥ 2.20 (jeton `GAZETTE_CARNET_JETON`) ; `_fiche_depuis_carnet` (main.py) à l'annonce de HA et depuis À traiter ; `a_traiter()` rend `dates` ; `/api/carnet/suggestions` pour `FicheForm`. Tests : carnet simulé (`ETAT["carnet_lire"]`), aussi dans la démo.
- 62 tests (`python -m pytest -q`), sans réseau : pages de sources inventées (`tests/fixtures.py`) ; écrans sur PC et iPhone par le serveur de démonstration (`python -m tools.demo`, mot de passe demo-demo-demo).
- Tuile de l'Anneau : `/health` donne `livrets` et `a_traiter` ; sa ligne du `services.yaml` de l'Anneau est dans Atlas (`data/anneau-services.yaml`, dépôt privé, qui fait foi), comme la stack (`data/homelab.yml`).
- Package HA `chambres/gazette.yaml` v1.0 : pas dans ce dépôt (il nomme les chambres et le téléphone de la maison) ; sa copie de référence est décrite dans le master doc Home Assistant (§ 6.1 et § 10). Contrat de la porte : `docs/dossier.md`, section « Temps 1 tel que construit ».

## Prochaine étape
1. Après l'installation, remplir Réglages › Le journal (titre, lieu, hôtes, mot par défaut).
1. Installé le 14/11 (port **8089** sur le NAS, 8099 dans le conteneur) : vérifier la version (0.5.0) et la tuile « Rendu PDF » de Connexion.
2. Créer les fiches des proches attendus, relire, approuver, imprimer un livret à la main (recto-verso bord court) : c'est l'essai demandé avant l'impression IPP.
3. Installer le package HA, vérifier au premier séjour : noms reçus, dates (`sejour_fin` − 1 h = dernier jour), notification.
4. Temps 3 : impression IPP (`GAZETTE_IMPRIMANTE`), seulement après l'essai du recto-verso.

## Pièges
- Dépôt public : aucun nom réel, aucune date de naissance réelle, aucun lieu ni adresse. Titre, lieu, hôtes et mot par défaut se règlent dans l'appli (gardés dans `gazette.db`), jamais dans le code. Rien de Larousse dans le dépôt (ni texte ni page en cache).
- Wikipédia : User-Agent descriptif obligatoire, pauses entre deux pages ; une première préparation prend une à deux minutes. Le cache (`sources` dans `gazette.db`) rend les suivantes instantanées.
- L'aperçu exécute un petit script (ajustement de la taille) : le CSP de `/apercu` autorise `script-src 'unsafe-inline'`, rien d'autre.
- Le PDF demande Chromium dans l'image (≈ 400 Mo) : sans lui, l'aperçu marche, le PDF répond 503 et l'approbation ne contrôle plus les débordements.
- Impression recto-verso « bord court » pour l'imposition paysage.
