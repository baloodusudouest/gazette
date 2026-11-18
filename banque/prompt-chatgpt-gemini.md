# Prompt pour remplir la banque d'inspiration de Gazette (ChatGPT, Gemini…)

## Mode d'emploi

1. Ouvre une nouvelle conversation dans ChatGPT ou Gemini et colle le prompt ci-dessous en entier.
2. L'IA répond par un lot de 100 textes. Écris **« continue »** pour le lot suivant, jusqu'à avoir ce que tu veux (environ 10 lots par sorte pour 1000 textes).
3. Copie les réponses les unes à la suite des autres dans un fichier texte, par exemple `banque-chatgpt.txt`. Garde les lignes `# RUMEURS`, `# HOROSCOPES`… : c'est grâce à elles que Gazette sait de quelle sorte est chaque texte.
4. Dans Gazette, va dans **Réglages › Banque d'inspiration › Importer un fichier**. Tu peux importer plusieurs fichiers d'un coup, et réimporter le même sans risque : les doublons sont ignorés, et les textes trop longs ou avec une balise inconnue sont écartés (Gazette dit combien et pourquoi).

Astuce : fais une conversation par sorte (une pour les rumeurs, une pour les horoscopes…), les textes sont plus variés. Pour ça, remplace dans le prompt la ligne « Sorte à écrire » par une seule sorte.

---

## Le prompt à coller

```
Tu écris pour « La Gazette » et « La Récidive », deux petits journaux humoristiques imprimés à un seul exemplaire pour les invités d'une maison de campagne près d'Agen (Lot-et-Garonne). La Gazette accueille un invité pour son premier séjour ; La Récidive est un faux journal à scandale pour les invités qui reviennent. Le ton est celui d'une presse people parodique, tendre, loufoque et absurde. On se moque des situations, jamais des personnes.

Sorte à écrire : RUMEURS, puis HOROSCOPES, puis MOTS, puis TITRES (100 textes par réponse ; quand une sorte atteint 1000, passe à la suivante).

FORMAT DE SORTIE, à respecter strictement (le fichier est lu par un programme) :
- Une ligne de section avant chaque lot : « # RUMEURS », « # HOROSCOPES », « # MOTS » ou « # TITRES ».
- Puis un texte par ligne, chaque ligne commençant par « - » (tiret puis espace).
- Aucun autre texte : pas d'introduction, pas de commentaire, pas de numérotation, pas de gras, pas de guillemets autour des textes, pas d'emoji.
- Chaque texte tient sur une seule ligne.

BALISES : écris-les exactement comme ceci, avec les accolades, sans accent ni majuscule :
- {prenom} : le prénom de l'invité (ex. « Audrey »).
- {salut} : la formule d'appel (« Chère Audrey », « Cher Paul »). Pour les MOTS uniquement, en début de texte.
- {chez} : le lieu, par exemple « à la maison ».
- {il} : « il » ou « elle » selon l'invité.
- {e} : la marque du féminin, à coller au mot (« arrivé{e} », « pris{e} », « surpris{e} »).
N'utilise aucune autre balise. Utilise {il} et {e} avec modération (un texte sur cinq au plus) : sans eux, le texte sert aussi quand on ne connaît pas le genre de l'invité.

LES QUATRE SORTES :
1. RUMEURS : une seule phrase, 130 signes au plus (espaces compris), avec {prenom}. Une fausse information absurde, au conditionnel, introduite par une source farfelue. Exemples :
   - Selon nos informations, {prenom} aurait tenté d'adopter un rond-point.
   - D'après le facteur, {prenom} parlerait couramment le langage des chèvres.
2. HOROSCOPES : 240 signes au plus, deux ou trois phrases : une configuration astrale absurde, une prédiction loufoque et bienveillante, un conseil saugrenu. {prenom} facultatif. Exemples :
   - Mercure entre dans votre valise : un pigeon vous apportera une excellente nouvelle. Évitez les ronds-points le mardi.
   - {prenom}, la Lune vous regarde de travers : vos chaussettes retrouveront enfin leur moitié. Portez du jaune, même en pensée.
3. MOTS : le mot des hôtes, 700 signes au plus, de deux à quatre phrases, qui commence par {salut}. Chaleureux et drôle, il accueille l'invité dans la maison et dans ce journal fait pour lui. Il ne dit pas si c'est un premier séjour ou un retour : il doit convenir aux deux. Exemple :
   - {salut}, les draps sont frais et les ragots sont prêts. Tout ce que vous lirez ici est rigoureusement inventé, à part notre joie de vous recevoir. Faites comme chez vous, et même un peu mieux.
4. TITRES : un gros titre de presse à scandale, 50 signes au plus, avec {prenom}. Exemples :
   - {prenom} démasqué{e} au rayon fromages
   - EXCLUSIF : {prenom} fuit avec la télécommande

RÈGLES :
- Jamais de moquerie sur le physique, le poids, l'âge, la santé, l'argent, le couple, la sexualité, la religion ou la politique. Rien de vulgaire, rien de méchant, rien qui puisse blesser. Les enfants peuvent lire ces journaux.
- N'invente aucun fait grave (accident, maladie, crime, décès).
- Aucune personne réelle, aucune marque, aucune célébrité.
- Couleur locale bienvenue mais pas systématique : Agen, la Garonne, les pruneaux, le marché, la campagne, les poules, le rugby.
- Varie tout : sources, situations, objets, animaux, débuts de phrase. Ne commence jamais deux textes de suite par les mêmes mots, et ne reprends pas un texte déjà écrit dans cette conversation, même légèrement modifié.
- Écris en français correct, avec les accents.

Commence maintenant par le premier lot de 100 RUMEURS.
```

---

## Si l'IA dérape

- **Elle numérote ou met des guillemets** : pas grave, Gazette retire numéros, puces et guillemets à l'import.
- **Elle écrit {Prénom}, [prenom] ou {{prenom}}** : Gazette corrige ces formes toutes seules. Une autre balise, par exemple {nom}, fait écarter le texte.
- **Elle s'arrête au milieu d'un lot** : écris « continue », la suite vient sans titre de section. Ajoute toi-même la ligne `# RUMEURS` (ou la bonne sorte) au début du morceau collé si elle manque, sinon Gazette reprend la dernière section lue dans le fichier.
- **Les textes se ressemblent** : relance avec « Change complètement de registre : d'autres sources, d'autres objets, d'autres situations ».
