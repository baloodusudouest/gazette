# Prompt pour remplir la banque d'inspiration de Gazette (ChatGPT, Gemini…)

But : que l'IA te rende **un seul fichier `.txt`, déjà au bon format**, avec les quatre sortes, prêt à importer dans **Gazette › Réglages › Banque d'inspiration › Importer un fichier**.

## Mode d'emploi

1. **ChatGPT** : utilise un modèle qui sait exécuter du code et créer des fichiers (l'outil d'analyse de données ou de code doit être actif). **Gemini** : active l'exécution de code, ou demande un fichier dans Canvas.
2. Colle le prompt ci-dessous en entier dans une nouvelle conversation.
3. L'IA écrit les textes par lots et les ajoute au fichier au fur et à mesure. Si elle s'arrête avant la fin, réponds simplement **« continue »** : elle reprend là où elle en était, dans le même fichier.
4. À la fin, elle te donne le lien de téléchargement de `banque-gazette.txt`. Importe-le dans Gazette.

Gazette garde tout ce que tu importes : un nouvel import agrandit la banque sans rien effacer, et les doublons sont ignorés. Tu peux donc relancer le prompt aussi souvent que tu veux, dans ChatGPT puis dans Gemini, et tout importer.

---

## Le prompt à coller

````
Tu vas produire UN SEUL FICHIER TEXTE nommé banque-gazette.txt, que je téléchargerai à la fin pour l'importer dans une application. Utilise ton outil d'exécution de code (Python) pour créer ce fichier, y ajouter les textes lot par lot, les contrôler, puis me donner le lien de téléchargement.

CONTEXTE
Les textes servent à « La Gazette » et « La Récidive », deux petits journaux humoristiques imprimés à un seul exemplaire pour les invités d'une maison de campagne près d'Agen (Lot-et-Garonne). La Gazette accueille un invité pour son premier séjour ; La Récidive est un faux journal à scandale pour les invités qui reviennent. Le ton est celui d'une presse people parodique, tendre, loufoque et absurde : on se moque des situations, jamais des personnes.

CE QUE TU DOIS ÉCRIRE : 1000 textes de chaque sorte, 4000 en tout.
1. RUMEURS : une seule phrase de 130 signes au plus, avec {prenom}. Une fausse information absurde, au conditionnel, rapportée par une source farfelue.
   Exemples : Selon nos informations, {prenom} aurait tenté d'adopter un rond-point. / D'après le facteur, {prenom} parlerait couramment le langage des chèvres.
2. HOROSCOPES : 240 signes au plus, deux ou trois phrases : une configuration astrale absurde, une prédiction loufoque et bienveillante, un conseil saugrenu. {prenom} facultatif.
   Exemple : Mercure entre dans votre valise : un pigeon vous apportera une excellente nouvelle. Évitez les ronds-points le mardi.
3. MOTS (le mot des hôtes) : 700 signes au plus, de deux à quatre phrases, qui commencent par {salut}. Chaleureux et drôle, le mot accueille l'invité dans la maison et dans ce journal fait pour lui. Il ne dit pas s'il s'agit d'un premier séjour ou d'un retour : il doit convenir aux deux.
   Exemple : {salut}, les draps sont frais et les ragots sont prêts. Tout ce que vous lirez ici est rigoureusement inventé, à part notre joie de vous recevoir. Faites comme chez vous, et même un peu mieux.
4. TITRES : un gros titre de presse à scandale de 50 signes au plus, avec {prenom}.
   Exemples : {prenom} démasqué{e} au rayon fromages / EXCLUSIF : {prenom} fuit avec la télécommande

BALISES (exactement ainsi, avec les accolades, en minuscules, sans accent) :
- {prenom} : le prénom de l'invité.
- {salut} : la formule d'appel (« Chère Audrey », « Cher Paul ») ; uniquement en tête des MOTS.
- {chez} : le lieu, par exemple « à la maison ».
- {il} : « il » ou « elle » selon l'invité.
- {e} : la marque du féminin, collée au mot (arrivé{e}, surpris{e}).
Aucune autre balise. {il} et {e} dans un texte sur cinq au plus.

RÈGLES DE CONTENU
- Jamais de moquerie sur le physique, le poids, l'âge, la santé, l'argent, le couple, la sexualité, la religion ou la politique. Rien de vulgaire ni de méchant : des enfants peuvent lire ces journaux.
- Aucun fait grave (accident, maladie, crime, décès), aucune personne réelle, aucune marque, aucune célébrité.
- Couleur locale bienvenue mais pas systématique : Agen, la Garonne, les pruneaux, le marché, la campagne, les poules, le rugby.
- Écris chaque texte toi-même. Ne fabrique pas les textes en combinant des morceaux par programme : le code sert seulement à écrire le fichier et à le contrôler.
- Varie vraiment : sources, situations, objets, animaux, débuts de phrase. Pas deux textes qui se ressemblent.
- Français correct, avec les accents.

FORMAT EXACT DU FICHIER (il est lu par un programme) :
# RUMEURS
- texte
- texte
# HOROSCOPES
- texte
# MOTS
- texte
# TITRES
- texte
Une ligne de section par sorte (« # RUMEURS », « # HOROSCOPES », « # MOTS », « # TITRES »), puis un texte par ligne commençant par « - » (tiret et espace). Rien d'autre dans le fichier : ni numéros, ni guillemets autour des textes, ni gras, ni emoji, ni commentaire. Chaque texte tient sur une seule ligne.

MÉTHODE (avec l'outil de code)
1. Crée le fichier et un contrôle en Python : pour chaque texte, remplace {prenom} par « Maximilien », {salut} par « Chère Maximilien », {chez} par « à la maison », {il} par « elle », {e} par « e », puis vérifie la longueur (rumeur ≤ 130, horoscope ≤ 240, mot ≤ 700, titre ≤ 60) ; refuse aussi toute autre balise entre accolades, les textes de moins de 12 signes et les doublons (comparés sans accents, sans majuscules et sans ponctuation).
2. Écris les textes par lots de 50 à 100 dans des listes Python, passe-les au contrôle et ajoute au fichier seulement ceux qui passent. Remplace les refusés par de nouveaux textes.
3. Garde les quatre sortes regroupées sous leur section, dans l'ordre RUMEURS, HOROSCOPES, MOTS, TITRES. Le plus simple : quatre listes en mémoire, et le fichier entièrement réécrit après chaque lot.
4. Après chaque lot, affiche seulement le compteur (par exemple « rumeurs 300/1000 · horoscopes 0/1000 · mots 0/1000 · titres 0/1000 »), pas les textes.
5. Continue sans me demander mon avis jusqu'à 1000 textes de chaque sorte. Si tu dois t'arrêter (longueur de réponse), dis-le, et quand j'écris « continue », reprends exactement là où tu en étais, dans le même fichier.
6. À la fin, relis tout le fichier avec le contrôle, affiche le décompte final et donne-moi le lien de téléchargement de banque-gazette.txt.

Commence.
````

---

## Si l'outil de fichier n'est pas disponible

Certains modèles ou comptes ne savent pas créer de fichier. Dans ce cas, remplace le paragraphe MÉTHODE par :

````
Tu ne peux pas créer de fichier : écris le contenu directement dans ta réponse, au format exact ci-dessus, par lots de 100 textes, en commençant chaque lot par sa ligne de section. Quand j'écris « continue », passe au lot suivant. Rien d'autre que le contenu du fichier dans tes réponses.
````

Puis colle toutes les réponses à la suite dans un même fichier texte, que tu importes dans Gazette. Gazette retire tout seul les numéros, puces et guillemets, et corrige les balises mal écrites ({Prénom}, [prenom], {{prenom}}).

## Si l'IA dérape

- **Elle fabrique les textes par combinaison** (même début, même fin partout) : réponds « Écris chaque texte toi-même, sans combiner des morceaux par programme. Recommence ce lot. »
- **Les textes se ressemblent** : « Change complètement de registre : d'autres sources, d'autres objets, d'autres situations. »
- **Elle s'arrête au milieu** : « continue ».
- **Le fichier contient autre chose que les sections et les lignes « - »** : pas grave, Gazette ignore les lignes qu'elle ne reconnaît pas, et indique à l'import combien de textes ont été écartés et pourquoi.
