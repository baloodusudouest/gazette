# Journal des versions

## 0.1.1 — 14/11/2026 (alignement sur le socle et l'Anneau)
- `/health` donne aussi le nombre de livrets et de cas à traiter (aucun nom), comme Comptoir, pour la tuile de l'Anneau.
- Tests d'écran sur PC et iPhone (`tests/test_ecran.py`) avec un serveur de démonstration inventé (`python -m tools.demo`) : aucune erreur de page, aucun débordement horizontal.
- Preuve de la lecture seule des sources (leçons du socle, § 6) : seules des lectures partent, le cache évite toute nouvelle demande, le client ne contient aucune écriture.
- À traiter : un seul bouton plein par bloc (« Créer la fiche » en contour).

## 0.1.0 — complément du 14/11/2026
- Port publié sur le NAS : 8089 (8099 est pris par la vérification des dates) ; l'appli écoute toujours sur 8099 dans le conteneur.

## 0.1.0 — 14/11/2026 (temps 1)
- Copie du socle (FastAPI, Svelte 5, Tailwind 4), port 8099, couleur vert anis `#b5c94f`, mot de passe commun et cookie `maison_session`.
- Fiche personne (nom, prénom, date de naissance, autres noms) et un livret par personne, gardés dans `gazette.db`.
- Moteur sans IA : Wikipédia FR (trois formats de pages mensuelles, pages annuelles, pages du jour), Wikidata (notoriété de toutes les pages liées, personnes = P31 Q5), Wikipédia EN en repli (proposé, jamais choisi seul), Larousse 1966-2003 ; cache sans limite de durée.
- Règles revues d'après le banc d'essai : une jour → veille → semaine → mois avec la portée imprimée ; mots forts, pénalité du sport, bonus du pays ; drames repérés par mots entiers sur tous les blocs et marqués « sensibles » ; titres coupés à une frontière ; chronologie 4 repères du pays + 3 du monde.
- Relecture : chaque bloc se corrige, se masque ou se remplace par une proposition ; mot des hôtes libre ; musique et cinéma saisis à la main.
- Rendu HTML → PDF (Chromium) : à imprimer (A4 paysage imposé) et lecture (A5) ; contrôle des débordements avant « Approuver ».
- Porte Home Assistant `/ha/sejour` et `/ha/etat` (jeton `GAZETTE_JETON_HA`) ; À traiter : invités sans fiche, livrets à relire, anniversaires proches du séjour (± 14 jours, 3 phrases par cas), préparations en échec.
