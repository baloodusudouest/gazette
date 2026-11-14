# Journal des versions

## 0.4.0 — 14/11/2026 (texte complet, plus de « … »)
- **Plus aucun texte coupé** : la une, les brèves, la page 2 et la chronologie gardent la phrase de la source en entier. Un titre n'est pris que s'il se détache naturellement (phrase courte, « : », « ; », tiret) ou s'il vient de la rubrique de la source (« Serbie », « ONU ») ; sinon pas de titre, juste le paragraphe (« chapo seul » en une, texte seul en page 2).
- **Taille du texte ajustée page par page** : si une page est trop pleine, le texte des articles baisse par petits pas (jusqu'à 84 %, corps ≥ 9 pt imprimé) au lieu d'être tronqué ; même calcul dans l'aperçu et le PDF. Le contrôle des débordements regarde maintenant chaque élément de la page.
- Choix des articles selon la place : la page 2 et les brèves prennent des faits qui tiennent ensemble (les très longs écartés d'abord) ; une semaine trop maigre passe au mois (celui de la naissance d'abord) au lieu de répéter les brèves de la une ; un même fait venu de deux sources n'apparaît qu'une fois.
- Wikipédia : les modèles cachés dans un lien sont rendus (« Mgr Lefebvre » n'est plus perdu) ; renvois « (chrono. 4/02) » retirés ; lignes sans fait (« Grande-Bretagne » seul) écartées.

## 0.3.0 — 14/11/2026 (le journal se règle dans l'appli)
- **Réglages › Le journal** : titre, sous-titre, nom du lieu et sa ligne de détail (colophon), « chez vous » avec l'article (« Imprimé au … », mot des hôtes), signature des hôtes, mot des hôtes par défaut (`{date}`, `{prenom}`, `{chez}`), couleur d'accent, Larousse oui ou non. Gardés dans la base, valables aussitôt pour tous les aperçus et PDF ; un mot déjà écrit dans un livret est gardé.
- Les variables `GAZETTE_TITRE`, `GAZETTE_SIGNATURE`, `GAZETTE_LIEU`, `GAZETTE_LAROUSSE` ne donnent plus que la valeur de départ ; retirées de `docker-compose.yml` et `.env.example`.
- « Imprimé à la maison » et le sous-titre de la une ne sont plus écrits en dur.

## 0.2.0 — 14/11/2026 (top 5 culturel)
- **Top 5 culturel** (films, séries, musique, 1900 à aujourd'hui) livré avec l'appli (`app/donnees/top5_culture_annuel.csv`) : la page 3 remplit Musique et Cinéma toute seule (2 titres, 2 films, la série n°1). « Le titre de l'année » et « en tête du box-office » seulement quand la source le mesure ; lignes « PROVISOIRE » et « à vérifier » signalées à la relecture.
- **Réglages › Top 5 culturel** : télécharger le fichier, copier le prompt de mise à jour (`app/donnees/prompt_culture.md`, à utiliser dans Claude), importer le fichier rendu (contrôlé avant d'être gardé : colonnes, catégories, rangs, doublons), revenir à la version livrée.
- Livret : bouton « Remplir depuis le top 5 » et liste du top 5 de l'année ; un texte écrit à la main est gardé par une nouvelle préparation.
- Chronologie ramenée à 6 repères (3 du pays, 3 du monde) pour laisser la place à la culture : rien ne déborde sur les dates d'essai.

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
