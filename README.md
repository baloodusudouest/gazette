# Gazette

Un petit journal imprimé, « le monde le jour de votre naissance », pour les proches qui viennent dormir à la maison : un livret A5 de 4 pages, une feuille A4 paysage pliée en deux.

- **Une fiche par personne** (nom, date de naissance) et **un livret**, préparé une fois depuis les sources libres, relu, approuvé, puis réimprimé à chaque visite.
- **Rédaction par règles, sans IA** : Gazette choisit, trie et raccourcit des faits datés ; elle n'invente rien. Tout bloc se remplace par une autre proposition ou se corrige à la main.
- **Sources** : Wikipédia FR (pages du mois, de l'année, du jour), Wikidata (notoriété, personnes), Wikipédia EN en repli (proposé en anglais, jamais choisi seul) et, pour 1966-2003, les Journaux de l'année de Larousse (usage familial privé, rien n'en sort du NAS, mention « d'après Larousse »).
- **Home Assistant** annonce les séjours (`POST /ha/sejour`, jeton) : Gazette retrouve le livret de chaque invité, signale les fiches manquantes, les livrets à relire et les anniversaires à 14 jours ou moins du séjour (avec trois phrases à ajouter au mot des hôtes).
- **Rendu** : HTML puis PDF par Chromium ; « à imprimer » (A4 paysage, recto-verso bord court) et « lecture » (4 pages A5). Aucune page ne doit déborder : contrôlé avant l'approbation.

Installation : service `gazette` de `docker-compose.yml` dans la stack, variables dans `.env.example`. Dossier : `docs/dossier.md`. Reprise : `REPRISE.md`.

Polices embarquées (`app/polices/`) : Playfair Display, Source Serif 4, UnifrakturMaguntia, sous licence SIL OFL 1.1 (fichiers de licence à côté). Textes de Wikipédia : CC BY-SA 4.0.

Modèle commun des applis maison : [socle](https://github.com/baloodusudouest/socle).
