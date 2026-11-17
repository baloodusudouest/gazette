# Gazette

Un petit journal imprimé, « le monde le jour de votre naissance », pour les proches qui viennent dormir à la maison : un livret A5 de 4 pages, une feuille A4 paysage pliée en deux.

- **Une fiche par personne** (nom, date de naissance) et **un livret** pour son premier séjour, préparé depuis les sources libres, relu, approuvé, imprimé.
- **La Récidive** (0.9) : à partir du deuxième séjour, un journal à scandale remplace la Gazette, avec les photos d'Immich où l'invité est reconnu depuis son séjour précédent (complétées par ses photos taguées « scandale »), des légendes à relire, et un numéro : celui du séjour. Aucune date de naissance dedans. Lecture seule d'Immich (clé `GAZETTE_IMMICH_CLE`). 0.9.1 : on décrit une photo en quelques mots, l'IA du PC (Ollama, `GAZETTE_OLLAMA_URL`) propose cinq titres de 60 caractères au plus, on en choisit un ou on écrit le sien. 0.12 : l'IA tient compte aussi des albums parlants où se trouve la photo et des personnes reconnues ; et la Gazette classique a ses aides d'IA (titres, raccourcir, version journal, traduire, mot des hôtes). 0.13 : la Gazette classique peut imprimer en page 4 une photo d'Immich choisie parmi six (noir et blanc, légende façon presse de l'époque proposée par l'IA) et un code-barres clin d'œil.
- **Rédaction par règles, sans IA** : Gazette choisit et trie des faits datés, cités en entier ; elle n'invente rien. Tout bloc se remplace par une autre proposition ou se corrige à la main.
- **Sources** : Wikipédia FR (pages du mois, de l'année, du jour), Wikidata (notoriété, personnes), Wikipédia EN en repli (proposé en anglais, jamais choisi seul), un top 5 culturel annuel (films, séries, musique) pour la page 3 et, pour 1966-2003, les Journaux de l'année de Larousse (usage familial privé, rien n'en sort du NAS, mention « d'après Larousse »).
- **Home Assistant** annonce les séjours (`POST /ha/sejour`, jeton) : Gazette retrouve le livret de chaque invité, signale les fiches manquantes, les livrets à relire et les anniversaires à 14 jours ou moins du séjour (avec trois phrases à ajouter au mot des hôtes).
- **Carnet** (l'appli de contacts de la maison, ≥ 2.25) donne les dates de naissance (`GET /gazette/personnes`, jeton commun) : la fiche d'un invité connu se crée seule, la saisie propose les contacts, une date différente est signalée. Gazette n'y écrit rien.
- **Rendu** : HTML puis PDF par Chromium ; « à imprimer » (A4 paysage, recto-verso bord court) et « lecture » (4 pages A5). Aucune page ne doit déborder : contrôlé avant l'approbation.
- **Réglages** : titre du journal, lieu, hôtes, mot par défaut, couleur et Larousse se règlent dans l'appli ; l'Anneau les sauvegarde chaque nuit (`GET /externe/sauvegarde`, jeton commun de la maison) et « Restaurer les réglages » les remet. Aucun secret n'en sort.

Installation : service `gazette` de `docker-compose.yml` dans la stack, variables dans `.env.example`. Dossier : `docs/dossier.md`. Reprise : `REPRISE.md`.

Polices embarquées (`app/polices/`) : Playfair Display, Source Serif 4, UnifrakturMaguntia, sous licence SIL OFL 1.1 (fichiers de licence à côté). Textes de Wikipédia : CC BY-SA 4.0.

Modèle commun des applis maison : [socle](https://github.com/baloodusudouest/socle).
