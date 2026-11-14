Agis en tant que Data Engineer spécialisé dans les médias et la culture.

Je joins mon fichier existant `top5_culture_annuel.csv` (séparateur `;`, UTF-8 avec BOM, colonnes :
Annee;Categorie;Rang;Titre;Createur_Artiste;Metrique_Cles). Il couvre 1900 à 2026.
Tu dois le METTRE À JOUR, pas le reconstruire.

Règles strictes :
1. Charge le fichier joint en Python (encodage utf-8-sig, sep=";"). Conserve à l'identique toutes
   les lignes des années <= 2025 : même ordre, même orthographe, aucune réécriture.
2. Supprime toutes les lignes de l'année 2026 (elles contiennent "PROVISOIRE" dans Metrique_Cles)
   et remplace-les par les données DÉFINITIVES de 2026, vérifiées par recherche web :
   - Film : top 5 box-office mondial des films sortis en 2026 (The Numbers / Box Office Mojo),
     métrique du type "N°1 mondial - 2,52 Md$" puis "1,80 Md$ monde".
   - Serie : top 5 des séries du classement annuel Nielsen streaming US 2026 (ARTEY Awards,
     publié fin janvier), films exclus, métrique "Nielsen streaming US 2026 : XX,X Md min".
   - Musique : top 5 du Billboard Year-End Hot 100 2026, métrique "Billboard Year-End #n" ;
     ajoute " - Single #1 mondial IFPI 2026" sur le titre concerné, ou la mention entre
     parenthèses sur le rang 1 si le n°1 IFPI n'est pas dans le top 5.
3. Ajoute l'année 2027 (année en cours) avec les mêmes sources. Tout ce qui n'est pas définitif
   doit commencer par "PROVISOIRE (JJ/MM/AAAA) - " dans Metrique_Cles.
4. Valeurs strictes de Categorie : Film, Serie, Musique. Rang de 1 à 5. Nombres au format
   français (virgule décimale, "M$", "Md$", "Md min").
5. Ne fabrique aucune donnée : si un rang ou un chiffre n'est pas confirmé par une source,
   écris "(à vérifier)" dans la métrique plutôt que d'inventer.
6. Avant d'écrire le fichier, contrôle : aucun doublon (Annee, Categorie, Titre), aucun champ
   vide, 5 lignes par catégorie pour 2026 et 2027, nombre de lignes <= 2025 inchangé par
   rapport au fichier joint. Affiche le résultat de ces contrôles.
7. Trie par Annee, puis Categorie (Film, Serie, Musique), puis Rang. Exporte sous le même nom
   `top5_culture_annuel.csv`, séparateur `;`, UTF-8 avec BOM, et donne-moi le fichier complet
   à télécharger.
8. Termine par un tableau des lignes ajoutées ou remplacées, avec la source de chacune, et
   signale les lignes de mon fichier marquées "(à vérifier)" que tu as pu corriger au passage
   (liste-les, ne les modifie qu'avec une source).

Commence immédiatement par charger le fichier et lancer les recherches.
