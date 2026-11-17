# Gazette — dossier v0.2 (temps 1 construit, 0.1.0)

Grill du 28/10/2026 et du 14/11/2026 (questions à choix), avec conseil du 28/10/2026 sur l'idée. Premier livret fait à la main le 14/11/2026 avec le prototype (`tools/prototype/`). Format commun : `socle/docs/format.md`. Leçons : `socle/docs/lecons.md`.

**Dépôt public** : aucun nom de proche, aucune date de naissance réelle, aucune adresse du réseau, aucun chemin personnel. Le titre du journal, la signature et le lieu passent par des variables de la stack. Les personnes des exemples et des tests sont inventées.

## 1. Besoin

Quand des proches viennent dormir à la maison, leur offrir un petit journal imprimé : **le monde le jour de leur naissance**. Un livret par invité, posé dans la chambre à l'arrivée.

| Décision | Choix | Source |
|---|---|---|
| Pour qui | Famille et amis seulement (pas de clients) | grill 28/10 |
| Objet | Livret A5 de 4 pages, une feuille A4 paysage recto-verso pliée en deux ; le nom de l'invité bien visible à la une, « façon grand quotidien » | grill 28/10 |
| Style | Pastiche maison d'un grand quotidien (pas de copie d'une marque) | grill 28/10, conseil |
| Page 1, la une | **Événements du jour seulement** (gros titre + encart chiffré + 4 à 6 brèves) | grill 14/11 |
| Page 2 | Revue de presse du jour quand un sommaire de journal a été collé ; sinon, en automatique, « les grands titres de la semaine » ou « les dossiers en cours » | grill 14/11 |
| Page 3 | Chronologie des grands événements de l'année (la naissance y est marquée) ; musique (n°1 des ventes) ; cinéma ; nés et disparus le même jour | grill 14/11 |
| Page 4 | Le mot des hôtes ; plus tard, une photo « dossier » épinglée dans Immich | grill 28/10, 14/11 |
| Vraie une d'archive | Abandonnée : introuvable en libre pour les années récentes | grill 14/11 |
| Rédaction | **Par règles, sans IA** : tri et reformulation déterministes, relecture humaine avant impression | grill 28/10 |
| Sources | **Hybride** : sources libres en automatique (Wikipédia, Wikidata, chronologies) ; un sommaire de journal collé à la main prend le relais pour les pages 1 et 2 | grill 14/11 |
| Déclencheur | **Dès la réservation** de la chambre dans Home Assistant ; rappel la veille si l'édition n'est pas approuvée | grill 14/11 |
| Validation | Aperçu puis bouton **Approuver** ; rien ne s'imprime sans | grill 28/10 |
| Impression | Imprimante A4 en réseau (IPP) | grill 28/10 |
| Où | Appli maison sur le NAS, sur le modèle de Sillage | grill 14/11 |
| Ton | Mi-sérieux ; rubrique perso (mot des hôtes) | grill 28/10 |

Ce que l'appli n'est pas : un générateur d'articles. Elle choisit, trie et met en page des faits datés ; elle n'invente rien.

**Garde-fous venus du conseil du 28/10** : pas de décès ni de drame en gros titre ; l'âge n'est jamais imprimé ; un enfant (chambre Ado) n'a pas de Gazette par défaut ; la relecture avant impression est obligatoire.

## 2. Technique

| Sujet | Choix proposé |
|---|---|
| Base | Copie du socle (FastAPI, Svelte 5, Vite, Tailwind 4), image `ghcr.io/baloodusudouest/gazette`, port **8099** (8091 et 8092 sont promis à Scriptorium et Comptoir) |
| Données | `/data` : `gazette.db` (SQLite), `pdf/` (éditions rendues), `cache/` (réponses des sources) |
| Mise en page | Gabarit HTML/CSS du prototype (polices embarquées : UnifrakturMaguntia, Playfair Display, Source Serif 4, sous-ensembles latin et latin-ext) |
| Rendu PDF | **À trancher au conseil** : Chromium (Playwright) comme le prototype, rendu fidèle mais image lourde (~400 Mo) ; ou WeasyPrint (Python pur, CSS paginé, plus léger, flex et grid moins complets) |
| Imposition | Une feuille A4 paysage : recto p4 \| p1, verso p2 \| p3 ; impression recto-verso « bord court ». L'appli rend aussi un PDF « lecture » (4 pages A5 dans l'ordre) |
| Sources libres | Wikipédia FR (pages « <mois> <année> », « <année> en France », « <année> en musique », listes des n°1 en France, « Box-office France <année> ») ; Wikidata SPARQL (nés / morts un jour donné, notoriété = nombre de liens interlangues) ; flux « ce jour-là » de Wikimédia |
| Cache | Le passé ne change pas : chaque réponse est gardée par date, sans limite de durée ; bouton « Relire » |
| Home Assistant | Porte à jeton `/ha/sejour` (comme Sillage) : `{"chambre", "noms", "du", "jusqu_au"}` ; réponse : éditions créées, manquants. Package HA `chambres/gazette.yaml`, sur le modèle de `sillage_invites.yaml` |
| Dates de naissance | **À trancher au conseil** : (a) carnet donne une porte à jeton `/gazette/personnes` (nom → date), comme `/sillage/personnes` ; (b) en V1, la date se saisit dans Gazette, carnet vient ensuite (leçon : « une première version autonome ») |
| Photo de la page 4 | Plus tard : portrait Immich épinglé (clé Immich en lecture seule) |
| Impression | Gazette envoie le PDF à l'imprimante en IPP (`cups-client` ou bibliothèque IPP), adresse dans `GAZETTE_IMPRIMANTE` ; l'intégration IPP de HA est en échec et n'est pas nécessaire |
| Sécurité | Mot de passe commun et cookie `maison_session` ; jeton `GAZETTE_JETON_HA` ; mode lecture seule `GAZETTE_LECTURE_SEULE` (ici : n'imprime pas, n'écrit chez personne) ; Watchtower désactivé |
| Écritures extérieures | Aucune, sauf l'impression. Gazette n'écrit ni dans carnet, ni dans Immich, ni dans HA |

**Variables** (noms seulement) : `MAISON_PASSWORD` (0.7, repli `GAZETTE_PASSWORD`), `MAISON_JETON` et `MAISON_LECTURE_SEULE` (0.7), `GAZETTE_JETON_HA`, `GAZETTE_TITRE` (titre du journal), `GAZETTE_SIGNATURE` (le mot des hôtes), `GAZETTE_LIEU` (colophon), `GAZETTE_IMPRIMANTE` (adresse IPP), `GAZETTE_CARNET_URL` et `GAZETTE_CARNET_JETON` (si (a)), `GAZETTE_IMMICH_URL` et `GAZETTE_IMMICH_CLE` (plus tard), `GAZETTE_LECTURE_SEULE`.

> **0.8.0 (16/11/2026)** : la stack ne porte plus que `MAISON_PASSWORD`, `MAISON_JETON`, `MAISON_LECTURE_SEULE`, `GAZETTE_LECTURE_SEULE`, `GAZETTE_JETON_HA` et `GAZETTE_CARNET_URL`. Titre, lieu, hôtes, mot par défaut, couleur et Larousse se règlent dans Réglages › Le journal (`GAZETTE_TITRE`, `GAZETTE_SIGNATURE`, `GAZETTE_LIEU`, `GAZETTE_LAROUSSE` repris une fois au premier démarrage) ; l'Anneau les sauvegarde (`GET /externe/sauvegarde`, jeton commun) et Réglages › Restaurer les réglages les remet. `GAZETTE_PASSWORD`, `GAZETTE_CARNET_JETON` et `GAZETTE_ADRESSE` ne sont plus lus ; l'adresse IPP de l'imprimante se réglera dans Réglages au temps 3 (`GAZETTE_IMPRIMANTE` n'est plus lue).

### Règles de rédaction (sans IA)

- **Une** : les événements datés du jour exact dans la page « <mois> <année> » ; repli sur la veille (un quotidien du jour parle de la veille), puis la semaine. Gros titre = l'événement le mieux classé (notoriété de la page liée, priorité France puis monde) ; listes d'exclusion : décès, attentats, catastrophes ne sont jamais en gros titre.
- **Encart** : un nombre tiré de l'événement s'il y en a un (score, nombre, mesure), sinon la rubrique.
- **Semaine / dossiers** : 4 à 5 entrées des 7 jours précédents ; si la semaine est pauvre, les sujets qui courent sur plusieurs semaines.
- **Chronologie** : 6 à 8 repères de l'année, France et monde, plus la naissance.
- **Musique** : n°1 de la semaine de naissance, celui d'avant et celui d'après.
- **Personnes** : nés et disparus le même jour, triés par notoriété, 5 et 4 au plus, sans âge.
- **Reformulation** : la phrase vient de la source, en entier (depuis 0.4.0, jamais coupée) ; un titre seulement s'il se détache naturellement ou vient de la rubrique, sinon un paragraphe seul ; tout reste modifiable à la main avant approbation.
- **Sommaire collé** : le texte d'une page d'archives collée est découpé en titres ; les rubriques sans intérêt (nominations, programmes, agrégations…) sont écartées par une liste ; le haut du tri va en une, la suite en revue de presse.

## 3. Parcours des écrans

Entrées (rail sur PC, pilule sur iPhone) : **Éditions**, **À traiter**, **Connexion**, **Réglages**.

1. **Éditions** (écran d'ouverture : le geste répété). La liste des Gazettes à venir, par séjour (chambre, dates, invités) ; état de chaque édition : *à préparer*, *à relire*, *approuvée*, *imprimée*. Bouton « Nouvelle édition » (nom + date) pour une Gazette hors séjour.
2. **Une édition**. Aperçu des 4 pages (A5, à la taille de l'écran ; sur iPhone, une page à la fois, glissée). Pour chaque bloc : remplacer par une autre proposition, modifier le texte, masquer. « Coller un sommaire » (page 2 et une). Mot des hôtes modifiable (modèle par défaut). Boutons : **Approuver et imprimer** (plein, couleur de l'appli), « Télécharger le PDF », « Régénérer ».
3. **À traiter**. Tuiles : dates de naissance manquantes, éditions à relire, éditions approuvées non imprimées (imprimante injoignable), invités introuvables.
4. **Connexion**. Une tuile par service : Wikipédia, Wikidata, Home Assistant (dernier appel reçu), carnet, Immich, imprimante (voyant, « Imprimer une page d'essai »).
5. **Réglages**. Titre, signature, lieu (lus dans la stack, affichés) ; règles (listes d'exclusion, nombre de brèves) ; journal (éditions approuvées et imprimées) ; version, déconnexion.

Notification HA (par le package) : « La Gazette d'<invité> est prête à relire » avec un lien vers l'édition ; la veille de l'arrivée, rappel si elle n'est pas approuvée.

## 4. Design

- Habillage de l'appli : format commun, toujours sombre, Inter. Couleur proposée : **vert anis** `#b5c94f` (libre : ni or, ni lavande, ni rouges déjà pris).
- Signature de l'appli : l'aperçu du journal lui-même, papier crème `#F7F3EA`, encre `#161616`, une couleur d'accent (rouge `#9E1B1B` par défaut, réglable).
- Le livret : masthead gothique, titres Playfair Display, texte Source Serif 4, corps ≥ 10 pt une fois imprimé (≥ 9 pt quand la page est pleine : la taille s'ajuste page par page plutôt que de couper), marges ≥ 10 mm, rien qui déborde (contrôlé au rendu).

## 5. Schéma de données

| Table | Champs |
|---|---|
| `sejours` | id, chambre, du, jusqu_au, recu_le (venu de HA) |
| `editions` | id, sejour_id (nul si hors séjour), nom, date_naissance, etat, contenu (JSON des blocs choisis et modifiés), mot, accent, approuvee_le, imprimee_le, pdf |
| `sources` | cle (ex. `wp:fr:Novembre_1988`), lu_le, contenu (brut) — le cache |
| `sommaires` | date, texte_colle, titres (JSON), colle_le |
| `journal` | horodatage, geste (approuver, imprimer, modifier), edition_id |

Données personnelles (nom, date de naissance) : seulement dans `gazette.db` sur le NAS ; une édition est gardée pour la réimprimer.

## 6. Plan

| Temps | Contenu | Écrit chez un service ? |
|---|---|---|
| 0 | Prototype (fait le 14/11/2026) : gabarit 4 pages, imposition, deux livrets réels imprimés | non |
| 1 | Socle copié ; moteur de mise en page (gabarit → PDF imposé + PDF lecture) ; sources libres + cache ; écrans Éditions et Édition ; saisie manuelle nom + date ; téléchargement du PDF. Tests sur des dates connues (contenu attendu) | non |
| 2 | Porte `/ha/sejour` + package HA `gazette.yaml` + notifications ; À traiter | non |
| 3 | Impression IPP + « Approuver et imprimer » ; page d'essai | imprimante |
| 4 | Dates de naissance depuis carnet ; photo épinglée Immich en page 4 | non (lecture) |
| 5 | Sommaire collé → revue de presse et une | non |

## Questions pour le conseil

1. Rendu PDF : Chromium (fidèle, lourd) ou WeasyPrint (léger, moins de CSS) ?
2. Dates de naissance : porte carnet dès la V1, ou saisie dans Gazette d'abord ?
3. Le mot des hôtes : écrit dans Gazette (écran d'édition, sans limite) plutôt que dans un champ de la réservation HA (255 caractères) comme prévu au grill ?
4. Faut-il des règles assez bonnes pour se passer de relecture un jour, ou la relecture reste-t-elle la règle ?
5. Périmètre de la V1 (temps 1) : trop large ?

## Conseil du 14/11/2026 (dossier v0.1)

Cinq avis, relecture croisée anonyme, synthèse. Verdict, à valider :

- **D'accord** : Chromium (Q1) ; mot des hôtes écrit dans Gazette, sans limite (Q3) ; relecture humaine pour toujours, rapide (Q4) ; temps 1 trop large (Q5) ; le vrai risque est l'extraction de Wikipédia, pas le rendu.
- **Désaccords** : carnet dès la V1 ou saisie d'abord (Q2) ; construire ou finir le lot au prototype ; une édition par séjour ou une par personne.
- **Angles morts** : l'âge se lit forcément (date en une) → assumer ou « masquer l'année » ; `GAZETTE_SIGNATURE` fixe doublonne le mot des hôtes ; les exclusions ne protègent que le gros titre (brèves, chronologie, disparus) ; « priorité France » suppose un invité né en France ; passer d'une réservation à « telle personne, avec sa date » (surnoms, homonymes, ami sans réservation) ; le deuxième séjour donne le même livret ; recto-verso de l'imprimante non vérifié ; mention CC BY-SA absente ; pages Wikipédia maigres avant 1980.
- **Recommandation** : l'unité de Gazette est **la personne**, pas le séjour. V1 = socle + rendu (PDF imposé et lecture) + fiche personne (nom, date, lieu de naissance, « masquer l'année ») + une, chronologie, nés et disparus filtrés + édition des blocs + PDF téléchargeable + mention des sources ; musique et cinéma saisis à la main ; pas de HA, pas d'IPP. Temps 2 : HA signale un livret manquant ou à relancer (pas une édition par séjour). Temps 3 : IPP après essai du recto-verso à la main. Exclusions sur tous les blocs, avec drapeau « sensible ». Événements choisis selon le pays de naissance.
- **Première chose à faire** : passer l'extraction sur 30 dates tirées au hasard entre 1940 et 2010 et noter blocs vides, phrases bancales et drames qui passent le filtre ; ce banc d'essai devient les tests du temps 1.

## Décisions du 14/11/2026 (après le conseil)

- **Unité = la personne** : un livret préparé une fois, à froid, et réimprimé à chaque visite (0.9 : seulement au premier séjour ; ensuite La Récidive, voir la dernière section). Home Assistant signale qu'un invité attendu n'a pas encore de livret (ou qu'il est à relire) ; le séjour retrouve le livret existant, il n'en crée pas de nouveau.
- **L'année est toujours affichée** : c'est le principe du journal, entre proches. Pas de case « masquer l'année ». Le garde-fou « l'âge n'est jamais imprimé » est retiré ; l'âge en chiffres reste absent.
- **« Disparus le même jour » est gardé.**
- **V1 avec HA** : le temps 1 comprend la fiche personne, le rendu (PDF imposé et lecture), la une, la chronologie, les nés et disparus, l'édition des blocs, le PDF téléchargeable, la mention des sources, **et la porte `/ha/sejour`** avec le package HA (signalement des livrets manquants ou à relire). Musique et cinéma saisis à la main au début ; impression IPP au temps suivant, après un essai du recto-verso à la main.
- Retenus du conseil sans changement : Chromium ; mot des hôtes écrit dans Gazette, sans limite (la signature de la stack ne sert qu'en signature finale par défaut) ; relecture obligatoire et rapide ; exclusions sur tous les blocs avec drapeau « sensible » ; événements choisis selon le pays de naissance (France par défaut) ; banc d'essai sur 30 dates avant de figer les règles.

## Ajout du 14/11/2026 — anniversaire proche du séjour

**Demande** : comparer la date du séjour à l'anniversaire de la personne et, si l'anniversaire tombe **dans les 2 semaines avant ou après le séjour**, alerter dans Gazette et proposer, dans À traiter, des phrases pour le souhaiter en avance, le jour même ou en retard.

**Règle** (temps 1, avec la porte `/ha/sejour`, qui apporte les dates du séjour) :
- Pour chaque invité du séjour qui a une fiche personne avec une date de naissance, on calcule l'anniversaire le plus proche du séjour (l'année du séjour, la précédente ou la suivante : un anniversaire le 2 janvier compte pour un séjour du 28 au 30 décembre). Le 29 février compte le 28 février les années non bissextiles.
- Cas :
  - **pendant le séjour** (de l'arrivée au départ inclus) → « le jour même » ;
  - **1 à 14 jours avant l'arrivée** → « en retard » (l'anniversaire est passé quand l'invité arrive) ;
  - **1 à 14 jours après le départ** → « en avance » ;
  - au-delà de 14 jours → rien.
- **Alerte** : une tuile « Anniversaire proche du séjour » dans **À traiter** (compteur), un badge sur la fiche et sur l'édition, et un rappel dans la notification HA du livret.
- **Propositions de phrases** (par règles, sans IA, 3 par cas, avec `{prenom}` et l'écart en jours ou le jour de la semaine) ; un geste « Ajouter au mot des hôtes » insère la phrase choisie à la fin du mot (modifiable ensuite), un autre « Ignorer » ferme la tuile pour ce séjour. Exemples :
  - en avance : « Et puisque votre anniversaire arrive dans {n} jours : joyeux anniversaire, {prenom}, avec un peu d'avance ! » · « Un petit secret : on sait que vous soufflerez vos bougies {jour}. Joyeux anniversaire en avance ! » · « Bon anniversaire avant l'heure, {prenom} : ce journal en est le premier cadeau. »
  - le jour même / pendant le séjour : « Joyeux anniversaire, {prenom} ! Le fêter ici avec vous est un vrai bonheur. » · « Le {date}, c'est votre jour : bon anniversaire, et merci de le passer avec nous. » · « Votre anniversaire tombe pendant votre séjour : préparez-vous à quelques bougies. »
  - en retard : « Votre anniversaire, c'était il y a {n} jours : joyeux anniversaire en retard, {prenom}, mais de tout cœur ! » · « Mieux vaut tard que jamais : bon anniversaire, {prenom} ! » · « On n'a pas oublié votre anniversaire, on a juste attendu de vous avoir sous la main. »
- L'âge en chiffres n'apparaît jamais dans les phrases.
- Données : la date de naissance vient de la fiche personne (saisie en V1, carnet ensuite). Sans date de naissance, pas d'alerte, mais la fiche manquante est déjà signalée dans À traiter.
- Tests : séjours encadrant l'anniversaire à J-15, J-14, J-1, le jour d'arrivée, pendant, le jour de départ, J+1, J+14, J+15 ; passage d'année ; 29 février.

## Temps 1 tel que construit (0.1.0, 14/11/2026)

Choix du 14/11 : Larousse retenu avec **texte et mention** (« d'après Larousse », cache sur le NAS, rien dans le dépôt) ; Wikipédia EN autorisé (repli) ; go pour le temps 1.

| Sujet | Construit |
|---|---|
| Écrans | **Livrets** (séjours à venir, puis toutes les fiches ; « Nouvelle fiche »), **un livret** (`#/livret/<id>` : blocs à gauche, aperçu à droite, PDF à imprimer et lecture, Approuver), **À traiter** (invités sans fiche, anniversaires proches, livrets à relire, préparations en échec), **Connexion** (Wikipédia FR, EN, Wikidata, Larousse, Home Assistant, rendu PDF ; « Vérifier les sources »), **Réglages** (titre, signature, lieu, règles, journal) |
| Données | `gazette.db` : `personnes`, `livrets` (un par personne : contenu choisi, propositions, mot, état), `sejours` + `invites` (venus de HA), `ignores`, `sources` (cache), `journal` |
| États d'un livret | `a_preparer` → `en_preparation` (une file, un ouvrier) → `a_relire` → `approuve` ; toute modification d'un livret approuvé le remet `a_relire` ; une nouvelle date de naissance le refait |
| Une | jour → veille → semaine → mois ; la portée est imprimée au-dessus du titre (« La veille », « Cette semaine-là », « Ce mois-là ») ; encart = un nombre du texte et ce qu'il compte, sinon la date |
| Brèves | 4, de la semaine, 2 par jour au plus ; titre = rubrique de la source, sinon « Le 5 juillet » |
| Page 2 | 5 titres des 7 jours d'avant (2 par jour au plus) ; moins de 3 → « les grands titres du mois » |
| Page 3 | 4 repères de « <année> en France » + 3 de la page « <année> », un par mois d'abord ; nés et disparus du jour (humains seulement, nés avant l'année de naissance), 5 et 4 ; musique et cinéma à la main (rubrique absente si vide) |
| Sensible | mots entiers (décès, attentat, guerre, accident, enlèvement…) : jamais choisi seul, sur aucun bloc ; visible à la relecture (« voir les sensibles ») avec ses mots |
| Anglais | Wikipédia EN lue quand la semaine a moins de 4 faits propres ; proposé « en anglais, à traduire », jamais choisi seul |
| Porte HA | `POST /ha/sejour` `{chambre, noms[], du, jusqu_au}` → `{invites: [{nom, fiche, livret, lien, anniversaire}], manquants, a_relire, anniversaires}` ; `noms` vide = chambre libre (séjours en cours ou à venir oubliés). Un séjour de la même chambre qui chevauche est remplacé. Les noms sont rapprochés des fiches sans accents ni casse (nom, autres noms, prénom s'il est unique). `GET /ha/etat` → `{a_traiter, fiches_manquantes, a_relire, anniversaires, liste[], adresse}` |
| Contrôle avant approbation | Chromium mesure chaque page : un bloc qui dépasse refuse l'approbation (« la page 1 déborde ») |
| Aide quand une page déborde (0.5.0) | Blocs de la page en rouge, compteur de signes qui suit la frappe et dit combien retirer, propositions de remplacement qui font tenir la page en vert ; vert partout quand la page devrait tenir, nouvelle mesure après « Enregistrer » |
| Carnet (0.6.0) | Lit `/gazette/personnes` (noms, dates complètes) : fiche créée seule pour un invité connu (un seul contact, date complète), saisie assistée, dates différentes dans À traiter ; n'écrit rien dans carnet |
| Pas encore | impression IPP (temps 3), carnet (dates de naissance), photo Immich en page 4, sommaire collé (temps 5), musique et cinéma automatiques |

**Port** (14/11/2026) : 8099 était déjà publié sur le NAS par la vérification des dates. Gazette écoute sur 8099 dans son conteneur et est publiée sur **8089** (`PORT_GAZETTE`).

## Top 5 culturel (14/11/2026)

Un fichier `top5_culture_annuel.csv` (1900 à 2026 : films au box-office, séries en tête des audiences US, titres en tête des ventes / du Billboard), préparé avec Claude, et un prompt pour le tenir à jour chaque année. Gazette le livre (`app/donnees/`) et s'en sert pour la page 3 : Musique et Cinéma ne sont plus saisis à la main. Mise à jour : Réglages › Top 5 culturel (télécharger, copier le prompt, importer). Un fichier importé est contrôlé avant d'être gardé et remplace la version livrée ; « Revenir à la version livrée » le retire. La chronologie passe à 6 repères pour que la page tienne.

## Le journal réglé dans l'appli (14/11/2026)

Titre, sous-titre, lieu (et sa ligne de détail), « chez vous » avec l'article, signature des hôtes, mot par défaut, couleur d'accent et Larousse se règlent dans Réglages › Le journal, gardés dans la base (table `reglages`, clé `journal`). Les variables de la stack ne donnent plus que la valeur de départ.

## La Récidive, journal à scandale (17/11/2026, 0.9.0)

**Demande (17/11/2026)** : un second journal, façon journal à scandale, pour les invités qui reviennent, fait des photos d'Immich où la personne est reconnue entre son dernier séjour et le nouveau.

**Conseil du 17/11/2026** (cinq conseillers, relecture croisée, président). Accord : pas d'IA dans la première version, la chaîne Ollama n'est pas prête ; la relecture est le vrai filtre. Divergences : remplacer ou ajouter, enfants, genre. Angles morts : tag « scandale » jamais compté, aucun essai à blanc, photos de tiers, cas « aucune photo », N° des séjours d'avant Gazette, annulation la veille, mot « Récidive ».

**Arbitrage de Julien après le conseil** :
- retenu : **pas d'IA en 0.9.0** (légendes de gabarit modifiables ; l'IA locale en 0.9.1 après un essai réussi sur le PC) ; **repli** : aucune photo dans la fenêtre = la Gazette ; **N° corrigeable** à la main ;
- gardé malgré le conseil : La Récidive **remplace** la Gazette dès le 2e séjour (pas de choix à chaque séjour) ; **enfants inclus**, la relecture est le seul filtre ; titre **« La Récidive »** ; pas d'essai à blanc : coder directement ;
- genre : **carnet modifié dans le même chantier** (carnet 2.27.0 : `genre` et `immich_id` dans `/gazette/personnes`).

**Règles (0.9.0)** :
- Premier séjour d'une personne : la Gazette. À partir du 2e : une édition de **La Récidive** par séjour, qui la remplace. **N°** = numéro du séjour = séjours connus de Gazette (passés compris) + « séjours d'avant Gazette » notés sur la fiche ; corrigeable dans l'édition (2 à 99).
- **Fenêtre** : de l'arrivée du séjour précédent (compris) à l'arrivée du nouveau ; le séjour précédent est le dernier connu de Gazette, sinon la date « arrivée du dernier séjour d'avant Gazette » de la fiche (sans elle : message dans À traiter).
- **Photos** : Immich, personne liée à la fiche carnet (`immich_id`), photos seulement (pas de vidéo), aperçu « preview » (jamais l'original). **7 places** : la plus récente en une (page 1), six en page 2. Le plus possible de photos récentes, réparties dans le temps ; s'il en manque, photos de la personne taguées **« scandale »** (tag imbriqué accepté), rubrique « Anciens scandales » : jamais parues d'abord, réparties sur les décennies (au hasard dans chaque décennie, tour à tour, années variées), déjà parues seulement s'il n'en reste plus. Une photo « scandale » compte comme parue à l'approbation.
- **Aucune photo récente** : édition « sans photo », le séjour garde la Gazette (préparée au besoin). **Immich pas réglé** (`GAZETTE_IMMICH_CLE` vide) : jamais de Récidive.
- **Pas assez de photos et aucune photo « scandale »** (ou tag absent) : tuile « Photos « scandale » à trouver » dans À traiter (« Ignorer » par personne).
- **Titre** « La Récidive » ; **accroche** selon le genre de la fiche carnet : « Elle est revenue, nous aussi » / « Il est revenu, nous aussi » / « Prénom est de retour, nous aussi » (genre « autre » ou inconnu) ; modifiable. Mot des hôtes (« Droit de réponse ») : « Chère / Cher / Prénom, vous avez lu notre enquête… », modifiable.
- **Légendes de gabarit**, rien d'inventé : « Cliché du [date], versé au dossier. » ; ancien scandale : « Cliché du [date], ressorti pour l'occasion. » ; modifiables.
- **Relecture obligatoire** : retirer une photo (elle ne revient pas), « Compléter » (garde photos et légendes, remplit les places libres), « Tout refaire » ; approbation refusée si une page déborde (Chromium). Ligne imprimée : « Une photo vous gêne ? Dites-le, elle sera retirée de l'édition. »
- **Aucune date de naissance** dans ce journal (ni âge, ni anniversaire).

**Mise en page** (maquette S du 17/11/2026) : même feuille que la Gazette (A4 paysage, recto p4 | p1, verso p2 | p3, recto-verso bord court). P1 bandeau rouge « La Récidive », accroche, « N° n · date d'arrivée », « [Nom] revient ! », photo en une, macaron « Exclusif ! » ; p2 « Les preuves » (pièces à conviction, puis « Anciens scandales » en sépia) ; p3 « Chronologie des faits » (séjour précédent, photos prises, retour) et chiffres (photos récentes, anciens scandales, jours d'absence) ; p4 « Droit de réponse ». Polices embarquées : Anton, Oswald (OFL), Special Elite (Apache 2.0), Source Serif 4.

**Séjours** : un séjour commencé reste en mémoire quand Home Assistant libère la chambre (il finit la veille) : il compte comme une visite. Seuls les séjours pas encore commencés sont oubliés.

**Technique (0.9.0)** : `app/immich.py` (lecture seule : `POST /api/search/metadata`, `GET /api/tags`, `GET /api/assets/{id}/thumbnail?size=preview` ; aperçus gardés dans `/data/photos`), `app/recidive.py` (N°, fenêtre, choix, décennies, accroche, légendes), `app/rendu_recidive.py` (mise en page), tables `recidives` et `scandales_publies`, colonnes `sejours_avant` et `dernier_avant` de `personnes`. Routes `/api/recidives…` (liste, édition, relecture, préparer/compléter, photo, aperçu, PDF, mesure, approuver). `/ha/sejour` rend `journal` (« gazette » ou « recidive »), `numero` et le lien `#/recidive/<id>` ; `/ha/etat` dit « La Récidive N° n à relire ». Variables : `GAZETTE_IMMICH_URL` (défaut `http://immich_server:2283`), `GAZETTE_IMMICH_CLE` (clé d'API dédiée : asset.read, asset.view, tag.read).

**Jamais essayé sur la vraie installation** : la recherche Immich (forme de `search/metadata` avec `tagIds`, permissions de la clé), le tag « scandale », l'impression des photos, carnet 2.27.

**Reste (0.9.1)** : légendes par IA locale (Ollama sur le PC : `qwen2.5vl:7b` décrit, `qwen2.5:7b` propose, filtres, gabarit de secours), seulement si la vision passe 5 photos sur 5 en aperçu et après deux ou trois vrais numéros.

### Titres par l'IA du PC (0.9.1, 17/11/2026)

**Demande de Julien** : écrire soi-même quelques mots sur la photo, les envoyer à l'IA pour 5 propositions de titres en format tabloïd avec un nombre maximum de caractères ; choisir l'une ou écrire sa version. **Choix** : pour le gros titre de la une et pour la légende de chaque photo ; 60 caractères au plus ; IA sur le PC (Ollama, `qwen2.5:7b`), PC éteint : pas de propositions, on écrit soi-même (la légende de gabarit reste).

- Plus de modèle de vision : la photo ne quitte jamais Gazette ; seule la description écrite part vers le PC.
- Consigne : ton tabloïd, drôle et bienveillant, 60 caractères, aucun fait absent de la description, pas de moquerie du physique, aucun autre nom que celui de l'invité, accord selon le genre de carnet (inconnu : rien d'accordé). Filtres du code : longueur, refus, anglais, doublons, « elle / il » sans genre connu ; jusqu'à trois demandes.
- Rien n'est choisi à la place de Julien ; description et propositions gardées avec l'édition.
- Sur le PC, une fois : `OLLAMA_HOST=0.0.0.0` puis rouvrir Ollama, port 11434 ouvert dans le pare-feu. Stack : `GAZETTE_OLLAMA_URL`.
- Jamais essayé sur la vraie installation.
