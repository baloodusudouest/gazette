# Gazette — dossier v0.1

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

**Variables** (noms seulement) : `GAZETTE_PASSWORD` (= mot de passe commun), `GAZETTE_JETON_HA`, `GAZETTE_TITRE` (titre du journal), `GAZETTE_SIGNATURE` (le mot des hôtes), `GAZETTE_LIEU` (colophon), `GAZETTE_IMPRIMANTE` (adresse IPP), `GAZETTE_CARNET_URL` et `GAZETTE_CARNET_JETON` (si (a)), `GAZETTE_IMMICH_URL` et `GAZETTE_IMMICH_CLE` (plus tard), `GAZETTE_LECTURE_SEULE`.

### Règles de rédaction (sans IA)

- **Une** : les événements datés du jour exact dans la page « <mois> <année> » ; repli sur la veille (un quotidien du jour parle de la veille), puis la semaine. Gros titre = l'événement le mieux classé (notoriété de la page liée, priorité France puis monde) ; listes d'exclusion : décès, attentats, catastrophes ne sont jamais en gros titre.
- **Encart** : un nombre tiré de l'événement s'il y en a un (score, nombre, mesure), sinon la rubrique.
- **Semaine / dossiers** : 4 à 5 entrées des 7 jours précédents ; si la semaine est pauvre, les sujets qui courent sur plusieurs semaines.
- **Chronologie** : 6 à 8 repères de l'année, France et monde, plus la naissance.
- **Musique** : n°1 de la semaine de naissance, celui d'avant et celui d'après.
- **Personnes** : nés et disparus le même jour, triés par notoriété, 5 et 4 au plus, sans âge.
- **Reformulation** : la phrase vient de la source, raccourcie par règles (première proposition, longueur plafonnée) ; tout reste modifiable à la main avant approbation.
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
- Le livret : masthead gothique, titres Playfair Display, texte Source Serif 4, corps ≥ 10 pt une fois imprimé, marges ≥ 10 mm, rien qui déborde (contrôlé au rendu).

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
