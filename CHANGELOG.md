# Journal des versions

## 0.7.0 — 16/11/2026 (variables communes de la maison)
- **Module commun** `app/maison.py` (contrat 1 du socle 0.5.0), copié tel quel ; un test refuse une copie retouchée.
- **Mot de passe** : `MAISON_PASSWORD`, sinon `GAZETTE_PASSWORD` comme avant. Message d'erreur : « MAISON_PASSWORD (ou GAZETTE_PASSWORD) ».
- **Lecture seule** : `MAISON_LECTURE_SEULE=oui` met toute la maison en lecture seule ; `GAZETTE_LECTURE_SEULE` (« oui » ou « non »), si elle est posée, l'emporte pour Gazette. Le bandeau et Réglages disent d'où elle vient (« toute la maison » ou « cette appli »).
- **Jeton envoyé à carnet** (`/gazette/personnes`) : `GAZETTE_CARNET_JETON` d'abord tant qu'il est posé, sinon le jeton commun `MAISON_JETON` (carnet ≥ 2.25 l'accepte). Le jeton de Home Assistant (`GAZETTE_JETON_HA`) ne change pas : `MAISON_JETON` n'ouvre pas `/ha/…`.
- **Adresse de Gazette** dans les liens des notifications (`/ha/sejour`, `/ha/etat`) : lue dans l'Anneau (tuile « Gazette », adresse locale, car les liens partent vers Home Assistant), sinon `GAZETTE_ADRESSE`.
- **Correction** : une adresse avec un chemin (ex. `…:8089/ha/sejour`) donnait des liens faux (`…/ha/sejour/#/livret/3`, refusés sans jeton). Gazette ne garde plus que schéma, hôte et port.
- Rien ne change tant que la stack n'a pas les nouvelles variables : les anciens noms restent lus. `docker-compose.yml` et `.env.example` montrent les nouveaux noms.

## 0.6.0 — 14/11/2026 (dates de naissance lues dans carnet)
- **Fiche créée seule** : quand Home Assistant annonce un invité sans fiche et que carnet connaît un seul contact à ce nom avec une date de naissance complète, Gazette crée la fiche (nom de carnet, nom de la réservation gardé en « autre nom ») et prépare le livret. Il reste à relire et approuver ; la notification de HA dit « livret à relire » au lieu de « pas de fiche ».
- **À traiter › Invités sans fiche** dit ce que carnet sait (« né·e le … », « le 3 mai, année inconnue », « plusieurs contacts à ce nom ») ; bouton « Créer d'après carnet » quand la date est complète.
- **Saisie assistée** : en tapant un nom dans une nouvelle fiche, les contacts de carnet sont proposés ; un toucher remplit nom, prénom, date et autres noms.
- **Dates à vérifier** (nouvelle tuile d'À traiter) : une fiche dont la date diffère de celle de carnet ; « Prendre celle de carnet » (le livret est refait) ou « Garder la fiche ».
- **Connexion › Carnet** : nombre de contacts et de dates complètes, erreur claire (jeton refusé, carnet arrêté). Lecture seule : Gazette n'écrit rien dans carnet. Liste gardée 10 minutes, et la dernière bonne dans la base si carnet est en panne.
- Variables : `GAZETTE_CARNET_JETON` (même valeur que `CARNET_JETON_GAZETTE` de carnet 2.20) et `GAZETTE_CARNET_URL` (par défaut `http://carnet:8096`).

## 0.5.0 — 14/11/2026 (page trop pleine : on voit quoi changer)
- **Blocs en rouge** : quand une page déborde, ses blocs sont encadrés de rouge dans l'éditeur, avec un bandeau « Page 2 trop pleine : il manque environ 6 lignes ».
- **Compteur qui suit la frappe** : sous chaque bloc, le nombre de signes et ce qu'il faudrait retirer (« en retirer environ 316 suffirait ») ; tout passe au vert dès que la page devrait tenir (« enregistre pour vérifier »). Masquer un bloc compte aussi.
- **Remplacements en vert** : dans « Remplacer », les propositions qui feraient tenir la page sont en vert, en tête de liste, avec leur nombre de signes.
- Mesure faite par Chromium sur le livret enregistré (`GET /api/livrets/{id}/mesure` : hauteur de chaque bloc et place qui manque, page par page) ; l'estimation pendant la frappe vient de `frontend/src/lib/place.js` et la nouvelle mesure après « Enregistrer » tranche. Sans Chromium, l'éditeur marche sans ce contrôle.
- Zones de texte qui s'agrandissent avec leur contenu (navigateurs qui le permettent).

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
