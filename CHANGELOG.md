# Journal des versions

## 0.9.4 — 17 novembre 2026
- **IA du PC** : quand Ollama répond par une erreur, Gazette affiche son message (ex. « model 'qwen2.5:7b' not found ») et la marche à suivre qui va avec, au lieu de « injoignable ». Vu chez Julien le 17/11 : 404 sur `/api/generate`.

## 0.9.3 — 17 novembre 2026 (La Récidive : bouton « IA » en haut)
- **En haut à droite de l'édition** : « IA », « Enregistrer », « Approuver », toujours visibles (la barre reste en haut quand on fait défiler).
- **« IA »** lance les propositions pour **tous les textes décrits** d'un coup (la une et chaque photo gardée qui a une description), l'un après l'autre, avec l'avancement (« IA 2/5… ») ; il s'arrête au premier « PC injoignable ». On choisit ensuite les titres, puis Enregistrer.
- Cases plus claires : « Décris la photo de la une (l'IA proposera 5 gros titres) », « Décris cette photo (l'IA proposera 5 légendes) ».

## 0.9.2 — 17 novembre 2026 (La Récidive : macaron et cadrage)
- **Macaron « Exclusif ! »** : sa place se choisit dans l'édition (en haut à gauche, en haut à droite, en bas à gauche, en bas à droite, ou sans macaron). Il est posé dans la photo de la une, plus en travers de la page, et un peu plus petit.
- **Cadrage de chaque photo** : rogner en gardant le haut (par défaut, les têtes ne sont plus coupées), le centre ou le bas, ou **photo entière** (sans rognage, bandes sombres autour). Gardé par « Compléter ».
- Écran : le bouton « 5 titres » ne dépasse plus de son cadre (description sur toute la largeur, bouton dessous).
- Tests : 111.

## 0.9.1 — 17 novembre 2026 (La Récidive : titres proposés par l'IA du PC)
- **Titres par l'IA, d'après ta description** (choix de Julien du 17/11) : dans l'édition, sous la photo de la une et sous chaque photo, on écrit en quelques mots ce qu'on voit, puis « 5 titres » : l'IA du PC (Ollama, `qwen2.5:7b`) propose cinq titres façon presse à scandale, **60 caractères au plus**. Un toucher en prend un pour le **gros titre de la une** ou pour la **légende** ; on peut toujours écrire le sien. Rien n'est choisi à ta place.
- **Pas de modèle de vision** : la photo ne quitte pas Gazette, seule la description part vers le PC (fin du plantage du pilote AMD sur les grandes photos).
- Filtres du code : 60 caractères, refus, anglais, doublons, « elle / il » écartés quand le genre est inconnu ; jusqu'à trois demandes pour en avoir cinq. Description et propositions gardées avec l'édition (et par « Compléter »).
- **Gros titre de la une** modifiable (vide : « [Nom] revient ! » ; le nom reste surligné s'il est dans le titre).
- **PC éteint ou Ollama fermé** : un message avec la marche à suivre (ouvrir Ollama ; une fois : `OLLAMA_HOST=0.0.0.0`, port 11434 ouvert dans le pare-feu) ; la légende de gabarit reste. **Connexion** : tuile « IA du PC » (modèle présent ?).
- Variable : `GAZETTE_OLLAMA_URL` (`http://<adresse du PC>:11434` ; vide : pas de propositions).
- Tests : 109. **Jamais essayé sur la vraie installation.**

## 0.9.0 — 17 novembre 2026 (La Récidive, journal à scandale)
- **La Récidive** : à partir du deuxième séjour d'une personne, une édition par séjour remplace la Gazette. Numéro = numéro du séjour (séjours connus + « séjours d'avant Gazette » de la fiche), corrigeable. Photos d'Immich où la personne (liée dans carnet) est reconnue, de l'arrivée du séjour précédent à l'arrivée du nouveau : la plus récente en une, six en page 2 ; s'il en manque, ses photos taguées « scandale » (rubrique « Anciens scandales », jamais parues d'abord, réparties sur les décennies). Aucune photo récente : la Gazette sert. Immich pas réglé : la Gazette sert, comme avant.
- **Relecture** (`#/recidive/<id>`) : N°, accroche (« Elle est revenue / Il est revenu / Prénom est de retour, nous aussi », d'après le genre de carnet), légendes de gabarit modifiables, retirer une photo, « Compléter », « Tout refaire », mot des hôtes (« Droit de réponse »), aperçu, PDF à imprimer et lecture, approbation refusée si une page déborde. Pas d'IA en 0.9.0.
- **Mise en page** tabloïd (maquette S) : polices Anton, Oswald, Special Elite embarquées.
- **Livrets** : le séjour à venir montre « La Récidive N° n » et son état ; liste des éditions. **À traiter** : « Récidives à relire », « Photos « scandale » à trouver », erreurs (Immich, personne non liée, séjour précédent inconnu). **Fiche** : « Séjours d'avant Gazette » (nombre, arrivée du dernier). **Connexion** : tuile Immich.
- **Home Assistant** : `/ha/sejour` rend `journal`, `numero` et le lien de l'édition ; `/ha/etat` compte les éditions à relire.
- **Séjours** : un séjour commencé n'est plus oublié quand la chambre est libérée (il compte comme visite) ; seuls les séjours pas commencés le sont.
- **Variables** : `GAZETTE_IMMICH_URL` (défaut `http://immich_server:2283`), `GAZETTE_IMMICH_CLE` (clé d'API Immich dédiée : asset.read, asset.view, tag.read ; vide : pas de Récidive). Lit `genre` et `immich_id` de carnet ≥ 2.27.
- Tests : 104 (dont 13 pour La Récidive et l'écran de relecture sur PC et iPhone). **Jamais essayé sur la vraie installation.**

## 0.8.0 — 16 novembre 2026 (réglages dans l'appli, sauvegarde et restauration ; anciens noms retirés)
- **Réglages dans l'appli** : le titre du journal, le sous-titre, le lieu, la ligne sous le lieu, « chez vous », la signature des hôtes, le mot par défaut, la couleur d'accent et Larousse sont les réglages de Gazette. Ils restent gardés dans `gazette.db` (Réglages › Le journal) ; `GET /api/reglages` les rend, `PUT /api/reglages` les change (valeur du mauvais type : refus 400 avec un message clair).
- **Reprise unique** : au premier démarrage de la 0.8, un réglage encore absent de la base prend la valeur de son ancienne variable si elle est posée (`GAZETTE_TITRE`, `GAZETTE_SIGNATURE`, `GAZETTE_LIEU`, `GAZETTE_LAROUSSE`) ; une ligne au journal de l'appli le dit. Ensuite ces variables ne sont plus jamais lues. Un réglage déjà enregistré dans l'appli n'est jamais écrasé.
- **Sauvegarde par l'Anneau** : `GET /externe/sauvegarde` rend les réglages et la version (contrat de sauvegarde 1). Porte ouverte par le jeton commun `MAISON_JETON` seul ; jeton commun vide : porte fermée (404). Ni mot de passe, ni jeton, ni variable, ni chemin dans la réponse.
- **Restaurer les réglages** (Réglages) : choisir une date gardée par l'Anneau, voir ce qui changerait (avant → sauvegardé), confirmer. Seuls les réglages du journal changent (ni fiches ni livrets) ; permis même en lecture seule ; une ligne au journal. Anneau injoignable ou rien à restaurer : un message, pas d'erreur.
- **Anciens noms retirés** : `GAZETTE_PASSWORD` n'est plus lu (sans `MAISON_PASSWORD`, Gazette ne démarre pas : « MAISON_PASSWORD est absent ou trop court… ») ; carnet est lu avec `MAISON_JETON` seul (`GAZETTE_CARNET_JETON` n'est plus lu) ; l'adresse de Gazette dans les liens vient seulement de l'Anneau (`GAZETTE_ADRESSE` n'est plus lue ; sans tuile « Gazette », les liens sont relatifs comme avant la 0.7). `GAZETTE_IMPRIMANTE` n'est plus lue non plus : l'impression (temps 3) n'existe pas encore, son adresse se réglera dans Réglages.
- **Restent dans la stack** : `MAISON_PASSWORD`, `MAISON_JETON`, `MAISON_LECTURE_SEULE`, `GAZETTE_LECTURE_SEULE` (forçage pour Gazette seule), `GAZETTE_JETON_HA` (inchangé, n'ouvre que `/ha/…`) et `GAZETTE_CARNET_URL`.
- Module commun `app/maison.py` : contrat 2 (copie du socle, non retouchée).

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
