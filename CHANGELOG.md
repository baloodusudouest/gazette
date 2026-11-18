# Journal des versions

## 0.23.0 — 18 novembre 2026 (fiche complète d'une personne)
- **Fiche complète** (demande de Julien du 18/11, version retenue après le conseil) : un écran `#/fiche/<id>` demande le plus de détails possible sur une personne, pour que l'IA du PC écrive des textes plus justes et plus drôles. On l'ouvre par le bouton **« Fiche complète »** de La Récidive (en-tête et bloc « Pour l'IA » des rumeurs) et du Livret (sous le mot des hôtes).
  - **Toutes les rubriques** (39, en cinq familles et « Autre ») en amorces repliables, chacune avec 3 à 6 exemples à toucher ; chaque réponse est une **pépite** (200 caractères au plus), modifiable, déplaçable d'une rubrique à l'autre, effaçable.
  - **Ligne « vrac »** en haut : un détail en texte libre, rangé dans la rubrique la plus probable par mots-clés (sans IA ; « Autre » sinon), modifiable avant d'ajouter.
  - **Jauge** = nombre de pépites (paliers : 5 « de quoi rire », 15 « bien fournie », 30 « inépuisable »).
  - **Déjà connu, à valider** : métier, conjoint, enfants, animaux, aliments (fiche de carnet), événements et indices des anciennes Récidives, étapes du chemin de Sillage (nom et année) ; en gris, rien n'est recopié sans « Ajouter ».
  - **Sujets interdits** à part, masqués par défaut (« Afficher ») ; une pépite y passe d'un geste (« Interdire »).
  - Rangée dans **carnet 2.33** (une seule fiche, modifiable dans les deux applis), écrite pépite par pépite : une pépite changée ailleurs entre-temps est refusée (409) et la fiche est relue. **Brouillon local** (navigateur) tant qu'un ajout n'a pas réussi.
  - carnet **pas réglé, pas à jour (avant 2.33) ou personne introuvable** : la page le dit et n'écrit rien ; carnet **arrêté** : la dernière fiche lue s'affiche en lecture seule (« carnet injoignable »). La Gazette et La Récidive marchent comme avant dans tous ces cas.
- **L'IA reçoit la fiche** : rumeurs, horoscope, courrier, gros titre et légendes de La Récidive, mot d'accueil du Livret reçoivent à chaque demande **3 à 5 pépites tirées au hasard** (d'abord celles jamais parues) et le **ton souhaité** ; la ligne d'indices du séjour reste et part toujours. Avec la fiche, l'ancien texte libre « Pour les journaux » n'est plus envoyé ni repris dans la ligne d'indices (il est versé dans la fiche par carnet).
- **Sujets interdits** : jamais envoyés à l'IA ; toute proposition qui contient un de leurs mots (4 lettres au moins, hors mots vides ; « divorce » écarte aussi « divorcée ») est écartée, pour **toutes les personnes du numéro** (Récidive : la personne, les autres invités du séjour et les proches reconnus sur les photos ; Gazette : la personne, mot des hôtes et légende de la photo). Tout écarté : « Propositions écartées par les sujets interdits, relance. »
- **Pépites parues** : Gazette garde quelles pépites ont servi à quelles propositions ; à l'approbation d'un numéro (pas d'un essai), celles des textes retenus (même retouchés) reçoivent la date du jour comme `parue_le` dans carnet.
- Réglage de la stack **`GAZETTE_SILLAGE_URL`** (facultatif, défaut `http://sillage:8093`, jeton commun `MAISON_JETON`) : Sillage ≥ 0.20 pour les étapes. Sans Sillage, la fiche marche sans ces suggestions.
- API : `GET /api/fiches/{id}` (rubriques avec exemples, pépites, jauge, suggestions, état de carnet et de Sillage), `POST /api/fiches/{id}/pepites` {texte, rubrique (« vrac » : rangée), source}, `PUT` et `DELETE /api/fiches/{id}/pepites/{pépite}` (corps avec `le` ; 409 si changée), `POST /api/fiches/ranger` {texte}. `GET /api/recidives/{id}` rend `fiche_complete` ; `POST /api/livrets/{id}/approuver` et `/api/recidives/{id}/approuver` rendent `fiche`. Vers carnet : `GET /gazette/personnes/{personne_id}/fiche`, `POST …/fiche/pepites`, `PUT`/`DELETE …/fiche/pepites/{id}`, `POST …/fiche/parues` {ids, date}. Vers Sillage : `GET /externe/personnes/{immich_id}/etapes`. `app/rubriques_journaux.json` : copie à l'identique de celui de carnet.
- Tests : `tests/test_fiche.py` (19 : rubriques identiques à carnet par empreinte, tirage, interdits, filtre d'un autre invité, rangement du vrac, pré-remplissage, 409, contact introuvable, carnet arrêté ou pas à jour, IA, pépites parues, clients carnet et Sillage), carnet 2.33 simulé (`tests/carnet_simule.py`, aussi dans la démo) ; écrans PC et iPhone : `test_fiche_complete`, `test_fiche_contact_introuvable`, `test_fiche_carnet_arrete_lecture_seule`. 206 tests.
- Jamais essayé sur la vraie installation.

## 0.22.1 — 18 novembre 2026 (séjour annulé : les journaux partent)
- **Séjour annulé dans Home Assistant** (signalé par Julien le 18/11 : « la gazette reste alors qu'elle devrait être supprimée »). Quand un séjour **pas encore commencé** disparaît (chambre remise à libre avant l'arrivée, invité retiré de la liste, séjour remplacé), Gazette fait le ménage selon les choix de Julien :
  - **La Récidive** de ce séjour est **supprimée, même approuvée** (« toujours supprimé ») ;
  - si l'invité **n'a plus aucun séjour**, sa **Gazette repart à zéro** (état « à préparer », contenu, propositions, mot, photo et validations vidés) ; une Gazette **approuvée est gardée** et notée au journal ;
  - la **fiche de la personne reste** (rubriques, photo Immich, alias) ;
  - **dates seulement déplacées** (le séjour chevauche l'ancien) : rien n'est supprimé, le numéro de La Récidive suit le séjour ; un séjour déplacé loin (sans chevauchement) est traité comme une annulation puis un nouveau séjour (numéro refait) ;
  - un séjour **commencé ou fini** n'est jamais touché : la chambre libérée au départ garde tout.
- Une copie de la base est faite avant le ménage (`/data/sauvegardes/gazette-…-avant-annulation.db`, 10 gardées). Chaque suppression est notée au journal de Gazette ; la réponse à `/ha/sejour` dit `annules` (noms et dates).
- Tests : `tests/test_annulation.py` (6).
- Jamais essayé sur la vraie installation.

## 0.22.0 — 18 novembre 2026 (régénérer avec un second modèle)
- **« Autres propositions (qwen) »** (choix de Julien du 18/11 : « on génère avec mistral, on régénère avec qwen ») : le premier jet garde le modèle de la stack (`GAZETTE_OLLAMA_MODELE`, aujourd'hui **mistral-nemo**) ; sous chaque série de propositions, un bouton redemande la même chose au second modèle, **qwen2.5:14b** par défaut (essai du 18/11 : plus sage, plus lent, 2 titres sur 5 retenus en Récidive). Les nouvelles propositions remplacent les anciennes, comme une nouvelle demande. Le modèle utilisé est indiqué discrètement sous les propositions.
  - Partout où l'on demande des propositions : aides de la Gazette (titres, raccourcir, version journal, traduire, mot des hôtes), légende de la photo de la page 4, et dans La Récidive gros titre et légendes, rumeurs, courrier, horoscope, droit de réponse.
- **Réglage `modele_second`** (Réglages › Le journal › L'IA du PC ; un réglage de Gazette, pas une variable de la stack) : nom tel que dans « ollama list », sans espace ; vide = bouton caché. Il part avec les autres réglages dans la sauvegarde de l'Anneau (ce n'est pas un secret).
- API : les 7 routes qui appellent l'IA (`/api/livrets/{pid}/photo/proposer`, `/api/livrets/{pid}/ia`, `/api/recidives/{rid}/proposer`, `/rumeurs`, `/courrier`, `/horoscope`, `/mot`) acceptent `"second": true` dans le corps → second modèle ; réglage vide → 400 avec un message clair. Elles rendent aussi `modele`. `ollama.Ollama` : `proposer`, `rumeurs`, `courrier`, `horoscope` et `gazette` (dont la légende et le droit de réponse) prennent `modele=None` (None = modèle habituel) ; filtres, essais et longueurs inchangés.
- **Connexion › Vérifier les sources** dit si le second modèle est sur le PC (`second_present`, d'après `/api/tags`), sans changer le voyant de l'IA ; « IA du PC » montre le second modèle dans les réglages lus.
- Tests : `tests/test_second_modele.py` (8) ; écrans : `test_autres_propositions_second_modele`, `test_autres_propositions_absent_sans_reglage` (PC et iPhone). Démo : l'IA simulée répond d'autres titres avec qwen2.5:14b.
- Jamais essayé sur la vraie installation (ni qwen2.5:14b appelé depuis le NAS, ni sa durée réelle sous les 120 s d'attente).

## 0.21.0 — 18 novembre 2026 (santé des tâches de fond)
- **Tâches suivies dans `/health`** (module commun `maison.py` du socle 0.9.1) : `/health` garde tous ses champs et ajoute `version_socle`, `taches` et `copie_base`. Les messages d'erreur des tâches n'y paraissent qu'avec le jeton commun `MAISON_JETON` ou une session.
  - À la demande (jamais d'orange dans l'Anneau) : `preparation` (livret de la Gazette) et `recidive` (édition de La Récidive), une préparation par tour de la file. Une préparation qui finit avec une erreur notée sur le livret ou l'édition compte comme ratée.
  - Gazette n'a pas de boucle régulière à elle : la seule tâche régulière est la copie de la base.
- **Copie cohérente de la base chaque nuit à 01:10, heure de Paris** (`copie-des-bases`, 24 h) : `gazette.db` copiée par l'API de sauvegarde de SQLite et vérifiée vers `/data/copies/gazette-derniere.db` (écrasée chaque nuit ; Hyper Backup tient l'historique). Les copies d'avant suppression (`/data/sauvegardes`) ne changent pas.
- Rien d'autre ne change : les erreurs sont traitées comme avant.

## 0.20.9 — 18 novembre 2026 (constats moyens de l'audit)
- **M16** : pendant le rendu (PDF, mesure), Chromium ne sort plus sur le réseau : toute demande autre que `data:` ou la page elle-même (`about:`) est coupée, `file:` compris (aucun fichier du conteneur ne peut entrer dans le PDF ; `page.route`), les WebSocket aussi (`rendu.permise`, `_page_sans_reseau`). Le navigateur reste lancé à chaque rendu : l'API synchrone de Playwright est liée à son fil et les routes tournent dans plusieurs fils.
- **M17** : supprimer une fiche exige maintenant `{"confirmation": true}` dans le corps de `DELETE /api/personnes/{id}` (400 sinon) ; l'écran de la fiche l'envoie après sa question. La copie de la base avant suppression existait déjà (0.20.6).
- **M19** : trois redirections Wikipédia suivies au plus ; deux pages qui se renvoient l'une à l'autre ne font plus des centaines de requêtes (la page est tenue pour vide).
- `maison.py` du socle 0.8.2 (réglages secrets reconnus par mots, champ `ecartes` dans la sauvegarde).

## 0.20.8 — 18 novembre 2026 (cookies Secure)
- **Cookies `Secure` en https** (audit du 17/11/2026, même correctif dans toutes les applis maison) : ouverte en https (directement, derrière Tailscale Serve qui le dit par `X-Forwarded-Proto`, ou d'après l'origine de la page), l'appli pose ses cookies de session avec l'attribut `Secure` : ils ne partent jamais en clair. En http (adresse locale), rien ne change.
- `entrypoint.sh` refuse de lancer l'appli en root quand `/data` appartient à root (dossier créé par Docker) et dit le remède ; dépannage seulement : `MAISON_ROOT_ACCEPTE=oui`.

## 0.20.7 — 18 novembre 2026 (révocation du cookie commun)
- **« Se déconnecter » dans l'Anneau ferme vraiment la connexion commune** (audit du 17/11/2026, même correctif dans toutes les applis maison) : le cookie commun `maison_session` porte maintenant la génération tenue par l'Anneau (« génération.expiration.signature ») ; « Se déconnecter » l'augmente, et chaque appli la lit dans l'annuaire de l'Anneau (`/externe/services`, au plus une minute de retard) : un cookie commun d'avant la déconnexion ne vaut plus nulle part. Si l'Anneau ne répond pas, le cookie reste accepté comme avant (rien ne se bloque). **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour.
- Module commun `maison.py` (socle 0.8.0) : `generation_commune()`, `definir_generation_commune()` ; l'annuaire lit aussi `generation_commune` (une ancienne réponse de l'Anneau, liste seule, reste lue).

## 0.20.6 — 17 novembre 2026 (corrections de l'audit, suite)
- Supprimer une fiche fait d'abord une copie de la base dans `sauvegardes/` (livret, Récidives approuvées et mémoire des scandales partent avec la fiche) ; les 10 dernières copies sont gardées.
- `/health` (public, appelé chaque minute) ne recalcule plus « À traiter » qu'une fois par minute.

## 0.20.5 — 17 novembre 2026 (connexion plus sûre)
- **Connexion plus sûre** (audit du 17/11/2026, même correctif dans toutes les applis maison) :
  - un cookie portant un caractère non ASCII donnait une erreur 500 sur toute l'API ; il est maintenant simplement refusé ;
  - les clés qui signent les cookies (celui de l'appli et le cookie commun `maison_session` posé par l'Anneau) sont tirées du mot de passe par PBKDF2 : un cookie capté sur le réseau local ne permet plus de chercher le mot de passe à grande vitesse. **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour ;
  - des essais de mot de passe lancés en parallèle ne contournent plus le délai : au-delà de 30 essais en 5 minutes, tout est refusé sans comparer.
- Module commun `maison.py` (socle 0.7.0) : l'annuaire de l'Anneau est relu 30 s après un échec (avant : 10 min sans adresses après un redémarrage de la stack) ; un réglage `nan` ou infini est refusé ; un `reglages.json` abîmé est mis de côté (`.corrompu`) au lieu d'être écrasé.

## 0.20.4 — 17 novembre 2026 (corrections de l'audit)
- **Bug** : une erreur inattendue pendant la préparation d'un livret ou d'une Récidive tuait le fil de préparation, sans trace ; les livrets suivants restaient « en préparation » jusqu'au redémarrage du conteneur. Le fil continue maintenant : la fiche repasse « à préparer » avec l'erreur affichée, et la ligne va au journal.
- Intégration continue : l'image n'est plus publiée si les tests échouent (`docker.yml` appelle `tests.yml` avant de construire).
- Tests : 154 (dont `test_ouvrier.py`).

## 0.20.3 — 17 novembre 2026 (vérification de l'IA avec un modèle sans étiquette)
- **Bug** : avec `GAZETTE_OLLAMA_MODELE=mistral-nemo` (nom sans « : »), « Vérifier les sources » plantait (le nom était coupé sur « : ») et l'écran n'en disait rien : la tuile « IA du PC » restait sur « à vérifier » alors que le PC répondait. Trouvé sur le PC de Julien le 17/11 (journal d'Ollama : `GET /api/tags` du NAS en 200). `ollama.meme_modele` : « mistral-nemo » = « mistral-nemo:latest ».
- Une sonde qui plante ne fait plus tomber toute la vérification (Immich, IA) ; une vérification qui échoue s'affiche en rouge en haut de Connexion.
- Tests : 153.

## 0.20.2 — 17 novembre 2026 (marche à suivre de l'IA du PC)
- **Connexion › IA du PC** (demande de Julien du 17/11) : le panneau donne maintenant la marche à suivre complète, mise en forme : réglages lus (adresse appelée, modèle, nombre de titres, attente), « Allumer normalement » en cinq étapes, « En cas de problème » (six pannes connues, chacune avec ses gestes et ses commandes PowerShell à copier : PC injoignable, modèle introuvable, `ollama list` refusé dans le terminal, Ollama qui se ferme seul, lenteur, pas de titres), et « Installation » repliée. La dernière erreur s'affiche en tête. `ollama.guide(url)`, rendu par `etat()["guide"]`.
- Le texte suit le modèle réglé (`GAZETTE_OLLAMA_MODELE`) : il disait toujours `qwen2.5:7b`. Messages d'erreur raccourcis, renvoyant au panneau. Règle de pare-feu proposée limitée au réseau local (`-RemoteAddress LocalSubnet`).
- Tests : 151 (guide, écran du panneau sur PC et iPhone).

## 0.20.1 — 17 novembre 2026 (tuile « IA du PC »)
- **Connexion, tuile « IA du PC »** : avant « Vérifier les sources », elle disait « rien de lu pour l'instant » avec un voyant gris, même réglée. Elle dit maintenant « réglée, à vérifier (PC allumé ?) » (ou « pas réglée : écris les titres toi-même », ou l'erreur de la dernière demande), avec le voyant qui va avec. Le texte était rangé dans `voyant()` au lieu de `detail()` (`pages/Services.svelte`). Relevé par Julien le 17/11 en branchant Ollama.

## 0.20.0 — 17 novembre 2026 (archives ; simuler un journal)
- **Archives** (nouvel onglet, demande de Julien du 17/11) : chaque Gazette et chaque Récidive approuvée dont le séjour est fini y est rangée, par année, avec recherche par nom, filtre par année et par journal, lecture et PDF (à imprimer, lecture). Elles quittent la liste Livrets (« n anciens numéros rangés dans les Archives »).
- **Simuler un journal** (Réglages, tout en haut) : choisir une personne et La Gazette ou La Récidive → un numéro d'essai à part, ouvert dans l'éditeur. Gazette d'essai : fiche copiée « (essai) », le vrai livret n'est pas touché. Récidive d'essai : date du jour, photos depuis le séjour précédent (ou la dernière année). Un essai ne compte jamais (N°, déjà paru, scandales publiés, carnet, archives, Home Assistant, À traiter) ; bandeau « essai » et « Supprimer l'essai » dans l'éditeur, liste des essais en cours dans Réglages.
- Tests : 149.

## 0.19.0 — 17 novembre 2026 (livre d'or ; allusions permises)
- **Livre d'or** (demande de Julien du 17/11) : les mots que la personne a laissés dans le livre d'or de la maison (carte de Home Assistant → fiche de carnet ≥ 2.31) sont donnés à l'IA pour les rumeurs, le courrier des lecteurs et le droit de réponse de La Récidive (les trois derniers mots). Jamais imprimés tels quels ; jamais mêlés aux indices gardés dans « Pour les journaux ».
- **Allusions coquines permises** (choix de Julien du 17/11) : le filtre de la 0.18.1 n'écarte plus que les moqueries sur l'apparence ; les consignes disent « allusions coquines permises, avec esprit ».
- Tests : 145.

## 0.18.1 — 17 novembre 2026 (corrections vues sur l'édition d'Camille)
- **« 1°) 2°) 3°) »** laissés par l'IA dans l'horoscope : retirés (propositions, enregistré, impression).
- **L'horoscope parlait d'Eurovision** pour un séjour « apéro avec le travail » : l'exemple de broderie de la consigne était recopié. Nouvel exemple sur un événement imaginaire, avec « n'en reprends aucun mot » et « n'invente aucun autre événement ».
- **Rien sur le corps** (une lettre de lecteur parlait de « seins rebondis ») : consignes plus nettes et filtre qui écarte toute proposition sur le corps ou le sexe (titres, légendes, rumeurs, lettres, horoscopes), y compris les propositions déjà gardées.
- **Droit de réponse de La Récidive : bouton IA** (comme les autres éléments) — 3 versions d'après les indices, l'événement du séjour, le gros titre et les rumeurs.
- Les cases « Pour l'IA » du courrier et de l'horoscope se replient quand leurs éléments sont validés.
- Tests : 144.

## 0.18.0 — 17 novembre 2026 (réglages généraux de La Récidive)
- **Réglages › Le journal › La Récidive** (demande de Julien du 17/11) : titre du magazine (« La Récidive » par défaut ; un titre plus long s'imprime plus petit pour tenir dans le bandeau), accroche sous le titre en trois versions selon le genre de la fiche carnet (femme, homme, inconnu ; {prenom} remplacé), droit de réponse par défaut ({salut} et {prenom} remplacés).
- Ce sont des valeurs par défaut : chaque édition reste modifiable. L'accroche est fixée à la préparation d'une édition ; vider la case de l'édition reprend le réglage.
- Réglages d'usage comme les autres : sauvegardés chaque nuit par l'Anneau, remis par « Restaurer les réglages ».
- Tests : 142.

## 0.17.0 — 17 novembre 2026 (relecture élément par élément, la même pour la Gazette et La Récidive)
- **Quatre gestes sur chaque élément** (paragraphe, photo, rumeur, lettre, horoscope, mot, code-barres, culture…), pareils dans les deux journaux (demande de Julien du 17/11) :
  - **Valider** : l'élément disparaît (la validation est enregistrée ; il revient s'il change ensuite) ;
  - **IA** : l'IA du PC propose sous l'élément, tu choisis ; si une analyse tourne déjà, la demande s'ajoute à la file en cours (« IA : … , puis n en file ») ;
  - **Changer** : d'autres données selon l'élément — Gazette : un autre événement des sources, le top 5 pour musique et cinéma, une autre photo, le mot ou le message par défaut ; Récidive : une autre photo d'Immich (« Compléter »), une autre proposition déjà faite pour le titre, la rumeur, la lettre ou l'horoscope (sinon l'IA), le mot ou le message par défaut ;
  - **Refuser** : l'élément est supprimé (brève, article, repère, photo, rumeur, lettre, horoscope, musique, cinéma) ; pas de Refuser pour les éléments obligatoires (une, gros titre, mot des hôtes, code-barres).
- **Tout validé : il ne reste qu'un gros bouton Approuver** (et « Revoir les éléments validés »). Un bandeau dit combien d'éléments restent ; « Montrer aussi les validés » les fait revenir.
- **Page trop pleine** : ses éléments réapparaissent, encadrés en rouge, même validés, jusqu'à ce qu'elle tienne.
- **Mot des hôtes de la Gazette** : l'IA s'appuie sur les événements racontés dans la Gazette (une, brèves, page 2) pour un ou deux clins d'œil (demande de Julien du 17/11).
- Une validation ne fait plus repasser un journal approuvé « à relire » ; seul un contenu qui change le fait.
- Tests : 141.

## 0.16.0 — 17 novembre 2026 (tout part sur la fiche de carnet à l'approbation)
- **Approuver une Récidive envoie tout à carnet** (choix de Julien du 17/11 : tout centraliser sur la fiche contact) : le numéro (date du séjour, N°, gros titre, événement du séjour, indices, descriptions des photos écrites pour l'IA, textes imprimés : titre, légendes, rumeurs, horoscope, courrier) est rangé dans « Journaux parus » de la fiche (carnet ≥ 2.30), et les indices dans « Pour les journaux ». Un numéro réapprouvé remplace le précédent. Le message d'approbation dit si c'est fait ; carnet injoignable ou en lecture seule : l'approbation reste faite, le message le dit.
- **Les numéros suivants relisent la fiche** : textes déjà imprimés (pour ne pas les répéter), événements des séjours précédents (horoscope), descriptions des photos des trois derniers numéros (clin d'œil des rumeurs) — même si la base de Gazette a été perdue.
- Tests : 139.

## 0.15.2 — 17 novembre 2026
- **Page trop pleine encadrée en rouge** (demande de Julien du 17/11) : dans l'édition de La Récidive, les réglages d'une page qui déborde à l'impression (Une, Photos, Rumeurs, Page 4) sont encadrés en rouge, avec « Page n trop pleine à l'impression (il manque environ x mm) : raccourcis un texte de cette page, puis Enregistrer pour revérifier ». Mesure de Chromium sur l'édition enregistrée, refaite à chaque enregistrement.
- Gazette classique : mêmes encadrés rouges sur les réglages de la page qui déborde (en plus des blocs en rouge), jusqu'à ce que les changements la fassent tenir.
- Tests : 138.

## 0.15.1 — 17 novembre 2026
- **Page 4 de l'édition dans l'ordre de l'impression** (demande de Julien du 17/11) : courrier des lecteurs, puis horoscope du séjour, puis droit de réponse (le mot des hôtes), puis le message du code-barres, comme sur le papier depuis la 0.11.3.

## 0.15.0 — 17 novembre 2026 (l'horoscope brode sur l'événement du séjour)
- **Événement du séjour** (choix de Julien du 17/11) : une case dans l'encart « Pour l'IA » de l'horoscope de La Récidive (« soirée Eurovision, dort à la maison pour ne pas rentrer trop tard »). Quand elle est remplie, les 3 horoscopes brodent dessus, chacun sous un angle différent (« les astres prédisent une victoire de la Suède grâce à votre costume de tigre », « Pluton percute le Cancer : migraine carabinée le lendemain »). Jamais imprimé : seul l'horoscope choisi l'est.
- **Gardé pour les séjours suivants** : l'événement reste dans l'édition ; les horoscopes des éditions suivantes reçoivent les événements des séjours précédents (« 2026 : soirée Eurovision ») pour un clin d'œil.
- Tests : 136.

## 0.14.1 — 17 novembre 2026
- **Chiffres en émoji retirés** : l'IA numérotait l'horoscope avec « 1️⃣ 2️⃣ 3️⃣ » (vu chez Julien le 17/11) et le chiffre restait dans le texte imprimé. Les chiffres en émoji et tous les émojis (interdits par la consigne) sont retirés des propositions, de ce qui est enregistré, de ce qui était déjà gardé et de l'impression (horoscope, rumeurs, courrier, titres). Tests : 135.

## 0.14.0 — 17 novembre 2026 (bouton « IA » en haut de la Gazette)
- **Bouton « IA » à côté d'Enregistrer et Approuver** dans la relecture de la Gazette classique (demande de Julien du 17/11, choix « Tout ») : l'IA du PC relit tous les textes et propose, sous chaque bloc, des titres, une version journal et une version raccourcie (une, brèves, page 2), version journal et raccourcie (chronologie), 3 mots des hôtes et une version raccourcie (mot), et 5 légendes pour la photo de la page 4 si elle est choisie. « Traduire » seulement pour un texte qui a l'air anglais. Avancement « IA 3/14 » ; arrêt net si le PC est injoignable. Compter une à deux minutes.
- Les propositions de chaque aide restent affichées ensemble sous le bloc (Titres, Version journal, Raccourcir…), chacune avec « Fermer ». Rien n'est appliqué sans un toucher ; rien n'est enregistré sans Enregistrer.
- L'en-tête de la relecture reste en haut de l'écran au défilement (comme La Récidive).
- Tests : 134.

## 0.13.0 — 17 novembre 2026 (une photo d'Immich en page 4 de la Gazette)
- **Photo en page 4 de la Gazette classique** (choix de Julien du 17/11) : Gazette propose 6 photos d'Immich où l'invité est reconnu, réparties dans le temps (cherchées à la préparation, ou « Chercher dans Immich »). Julien en choisit une à la relecture (ou aucune) ; elle est imprimée **en noir et blanc au-dessus du mot des hôtes**, cadrage réglable (haut, centre, bas, entière), légende en italique dessous. Toucher la photo choisie la retire.
- **Légende proposée par l'IA du PC**, façon presse de l'année de naissance (« Mlle…, photographiée lors de… », 90 caractères au plus) : d'après la description de Julien, l'album parlant et les personnes d'Immich (comme La Récidive 0.12) ; 5 propositions, rien choisi à sa place.
- **Code-barres clin d'œil** comme La Récidive : un vrai Code 128 dans le colophon, message réglable (« Bienvenue, {prénom} ! » par défaut, 30 caractères), barre la plus fine à 0,25 mm pour se scanner.
- Sans Immich, sans personne liée dans carnet ou sans photo : page 4 comme avant, aucune erreur. Avec une photo, le mot passe en 12 pt et l'ornement disparaît ; un mot trop long passe en rouge comme les autres blocs.
- Tests : 132.

## 0.12.0 — 17 novembre 2026 (l'IA du PC aide aussi la Gazette ; La Récidive lit les albums)
- **Gazette classique : aides de l'IA du PC** (choix de Julien du 17/11), sous chaque bloc de la relecture (une, brèves, page 2, chronologie, mot des hôtes) : **Titres** (5 titres dans le style des journaux de l'année de naissance), **Raccourcir** (3 versions qui tiennent : vise ce qu'il faut retirer quand le bloc déborde), **Version journal** (3 réécritures façon presse de l'époque, mêmes faits), **Traduire** (un extrait Wikipédia anglais en français journalistique), **3 mots** (mot des hôtes personnalisé d'après les indices de carnet). Rien n'est changé sans un toucher sur une proposition ; rien d'inventé hors du mot des hôtes. Route `POST /api/livrets/{id}/ia`.
- **La Récidive : albums et personnes d'Immich** (demande de Julien du 17/11) : pour chaque photo, Gazette lit les albums où elle se trouve et les personnes reconnues sur la photo et dans ces albums, et les donne à l'IA (titres, légendes, rumeurs). Les albums génériques sont écartés (une année seule, « Photos 2019 », un mois, « Divers », « Pense-bête », « À trier », captures, WhatsApp…). Les prénoms de ces personnes sont permis dans les propositions (complices, témoins, rivaux). Affiché sous la case « Pour l'IA » (« Immich · Album : … · Avec : … ») ; avec un album parlant ou une personne connue, la description devient facultative. Jamais imprimé.
- **Clé Immich** : ajouter les permissions **album.read** et **person.read** à la clé « gazette ». Sans elles, le contexte reste vide et tout marche comme avant.
- Tests : 127.

## 0.11.4 — 17 novembre 2026
- **Code-barres clin d'œil** (page 4 seulement, choix de Julien) : un vrai Code 128, lisible par n'importe quelle appli de scan, qui cache un message réglable dans l'édition (« Reviens vite, {prénom} ! » par défaut, 30 caractères, accents retirés à l'encodage). Aucun texte sous les barres : c'est la surprise. Le faux code-barres de la page 3 est retiré.

## 0.11.3 — 17 novembre 2026
- **Page 4 réordonnée** (choix de Julien) : courrier des lecteurs et horoscope en haut (bandeau « Le courrier »), « Droit de réponse » (mot des hôtes, tampon, signature) tout en bas, puis l'encart sur les photos pour finir. Sans courrier ni horoscope, la page reste « Droit de réponse » comme avant. Code-barres qui ne s'écrase plus.

## 0.11.2 — 17 novembre 2026
- **Courrier des lecteurs** (toujours « rien d'utilisable » chez Julien) : le filtre anti-refus écartait toute lettre contenant « je ne peux » ou « désolé », fréquents dans une lettre écrite à la première personne. Seul un vrai refus en tête est maintenant écarté. Lettre 400 et réponse 200 caractères au plus. Si rien n'est gardé, le message montre le début de la réponse de l'IA, pour diagnostiquer.

## 0.11.1 — 17 novembre 2026
- **Courrier des lecteurs** : l'IA ne suivait pas le format sur une ligne (« lettre ::: signature ::: réponse ») et rien n'était gardé (« rien proposé d'utilisable », vu chez Julien le 17/11). Consigne à étiquettes (« Lettre : … / Signature : … / Réponse : … ») ; la lecture accepte les deux formes, le gras, les numéros, une signature ou une réponse absente ; un peu plus de place (lettre 300, réponse 160 caractères).

## 0.11.0 — 17 novembre 2026 (page 4 : courrier des lecteurs et horoscope)
- **Courrier des lecteurs** (page 4, sous la signature) : l'IA du PC propose 4 fausses lettres de correspondants loufoques (« Un voisin inquiet », « Une tomate du jardin »…) avec la réponse de la rédaction, d'après les indices des rumeurs ; on en prend jusqu'à 2, on les modifie ou on écrit les siennes.
- **Horoscope du séjour** (encadré jaune) : 3 horoscopes loufoques proposés d'après le signe, calculé à partir de la date de naissance ; seul le signe est imprimé, jamais la date. On en choisit un ou on écrit le sien.
- Rien de choisi : rubrique absente. Le bouton « IA » du haut les demande aussi quand ils sont vides. Ce qui a paru dans un numéro précédent n'est pas reproposé.
- Choix de Julien du 17/11 pour remplir la page 4 (sans photo de plus). Tests : 118.

## 0.10.0 — 17 novembre 2026 (indices gardés dans carnet, l'IA se souvient des numéros précédents)
- **Indices des rumeurs gardés dans carnet** (choix de Julien du 17/11) : ce que tu écris sur la personne pour les rumeurs est enregistré dans carnet (fiche › « Pour les journaux », carnet ≥ 2.29) quand tu demandes les rumeurs, et repris tout seul à l'édition suivante. carnet le recopie dans la note de la personne de son coffre « Contacts ». Seule écriture de Gazette chez carnet ; pas en lecture seule ; carnet injoignable : un message, rien de bloqué.
- **Ce qui a déjà paru** : les gros titres, légendes écrites ou choisies et rumeurs des éditions approuvées précédentes de la personne sont donnés à l'IA (« ne les reprends pas, un clin d'œil façon feuilleton est bienvenu ») ; une proposition trop proche d'un texte déjà imprimé est écartée. Liste « Déjà paru dans les numéros précédents » dans l'édition.
- Tests : 116.

## 0.9.8 — 17 novembre 2026
- **Numéros retirés** : l'IA numérotait ses propositions à sa façon (« 2 - Il se murmure… ») et le numéro restait dans le texte. Toutes les formes (« 2 - », « 3) », « 4 – », « - ») sont retirées des propositions, des rumeurs enregistrées et de l'impression (les rumeurs déjà choisies sont corrigées à l'affichage). Vu chez Julien le 17/11.

## 0.9.7 — 17 novembre 2026 (les rumeurs de la rédaction)
- **Page 3 : « Les rumeurs de la rédaction »** pour remplir l'espace libre : l'IA du PC propose 8 rumeurs loufoques et inventées sur l'invité (130 caractères au plus, « Selon nos sources… », jamais méchant, rien de grave), d'après des indices facultatifs (« ce qu'on sait d'elle ») et les descriptions des photos. On en prend jusqu'à 4, on les modifie, ou on écrit les siennes. Imprimées dans un encadré avec « Rumeurs non vérifiées, et pour cause : tout est inventé. » Rien choisi : rien d'imprimé.
- Le bouton « IA » du haut demande aussi les rumeurs quand aucune n'est encore choisie.
- Tests : 113.

## 0.9.6 — 17 novembre 2026 (titres qui ne se chevauchent plus, IA plus piquante)
- **Gros titre de la une** : interligne élargi (les accents et le surlignage jaune ne chevauchent plus la ligne du dessus) et taille selon la longueur (58 px jusqu'à 22 signes, puis 50, 42, 36 px) ; accroche longue en plus petit. Vu chez Julien le 17/11 (« Soirée apéro : Camille dézingue l'Eurovision Asie »).
- **IA plus piquante** : consigne de rédacteur en chef de tabloïd (faux scoop, exagération, jeux de mots, vocabulaire people, toujours affectueux, rien de grave ni de vulgaire), cinq exemples du ton voulu, « ne décris pas la photo, transforme-la en scandale », cinq angles différents ; température 1,05, pénalité de répétition. Les propositions trop descriptives (« Camille sourit avec son iPhone ») venaient de l'ancienne consigne.
- **Modèle changeable** : `GAZETTE_OLLAMA_MODELE` (facultative ; défaut `qwen2.5:7b`), pour essayer un modèle plus drôle en français sans nouvelle version.

## 0.9.5 — 17 novembre 2026
- Édition de La Récidive : petits titres « Légende imprimée » et « Pour l'IA (non imprimé) » au-dessus des deux cadres de chaque photo ; « Gros titre de la une (imprimé) ». Demande de Julien.

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
