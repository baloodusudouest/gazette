"""Usage : python tools/banque_gen.py banque/gazette-banque-claude.txt
Fabrique la banque d'inspiration de Gazette : 1000 rumeurs, 1000 horoscopes, 1000 mots des hôtes, 1000 titres.
Fragments écrits à la main, assemblés et mesurés ; chaque texte passe la lecture de Gazette (app/banque.py)."""
import random
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from app import banque as B  # noqa: E402

random.seed(47)
N = 1000

# ------------------------------------------------------------------ RUMEURS (≤ 130 signes, une phrase)
R_OUV = [
    "Selon nos informations,", "D'après une source proche du dossier,", "On murmure au marché d'Agen :",
    "Un voisin l'affirme :", "Notre envoyé spécial est formel :", "Au comptoir, on raconte que, chaque soir,",
    "Selon un pigeon voyageur bien informé,", "Des témoins l'assurent :", "Rumeur persistante :",
    "La rédaction l'a appris de source sûre :", "D'après le facteur,", "Un chien du quartier confirme :",
    "Le bruit court :", "Selon des sources non vérifiées,", "Nos espions rapportent que, depuis l'été,",
    "Le boulanger est formel :", "Le GPS de la voiture a parlé :", "Révélation du rayon fromages :",
    "Les murs de la chambre d'amis chuchotent :", "Il paraîtrait que, certains mardis,",
    "Un sondage mené auprès de trois poules l'indique :", "Info ou intox ?", "On le tient d'une tante éloignée :",
    "Selon la gazette des voisins,", "Un témoin qui souhaite garder l'anonymat le jure :",
    "Le correspondant local de la rédaction l'a vu :", "Dernière minute :", "Selon un sanglier des coteaux,",
    "Le jardinier d'en face le certifie :", "À en croire le répondeur,",
]
R_ACT = [
    "{prenom} aurait tenté d'adopter un rond-point", "{prenom} aurait demandé la main d'un pruneau d'Agen",
    "{prenom} aurait appris l'espagnol pour parler à son aspirateur", "{prenom} collectionnerait les bouchons de cidre",
    "{prenom} aurait nommé sa plante verte « Directrice générale »", "{prenom} saurait imiter le cri du canard colvert",
    "{prenom} aurait fait une offre pour racheter la Garonne", "{prenom} parlerait couramment le langage des chèvres",
    "{prenom} aurait inventé une danse pour accompagner le lave-vaisselle", "{prenom} cacherait une réserve secrète de croissants",
    "{prenom} aurait voulu inscrire son chien au concours de belote", "{prenom} aurait battu le record de sieste du département",
    "{prenom} aurait fait signer un contrat de confidentialité à un hérisson", "{prenom} aurait confondu la boîte aux lettres et le frigo",
    "{prenom} tiendrait un journal intime en alexandrins", "{prenom} aurait offert un bouquet à la machine à café",
    "{prenom} aurait tenté de négocier avec un radar", "{prenom} aurait été aperçu{e} en train de saluer les ronds-points",
    "{prenom} serait l'auteur{e} d'un tube de l'été jamais sorti", "{prenom} aurait gagné un concours de lancer de pantoufle",
    "{prenom} aurait demandé un autographe à un épouvantail", "{prenom} aurait réussi à plier un drap-housse du premier coup",
    "{prenom} aurait fondé un club de fans du pain perdu", "{prenom} aurait voulu repeindre la tour Eiffel en vert pomme",
    "{prenom} aurait appris à jongler avec des pruneaux", "{prenom} aurait inscrit son vélo à un cours de yoga",
    "{prenom} écrirait des lettres d'amour à la Garonne", "{prenom} aurait adopté un escargot nommé Turbo",
    "{prenom} aurait réservé une table pour deux avec un cactus", "{prenom} aurait tenté de traduire le chant des grillons",
    "{prenom} aurait été sacré{e} star du karaoké d'un soir", "{prenom} aurait caché la télécommande dans le congélateur",
    "{prenom} aurait voulu payer sa baguette en pièces de Monopoly", "{prenom} aurait fait la bise à un mannequin de vitrine",
    "{prenom} aurait chanté la Marseillaise à un pigeon", "{prenom} aurait gagné une partie d'échecs contre un grille-pain",
    "{prenom} aurait goûté toutes les confitures d'un marché en une matinée", "{prenom} aurait déposé un brevet pour la chaussette orpheline",
    "{prenom} aurait enseigné le moonwalk à une vache", "{prenom} aurait demandé un remboursement au soleil",
    "{prenom} aurait confié ses secrets à un nain de jardin", "{prenom} aurait battu un écureuil à la course",
    "{prenom} aurait voulu adopter un panneau « Stop »", "{prenom} aurait tricoté un pull à un lampadaire",
    "{prenom} aurait applaudi un coucher de soleil pendant dix minutes", "{prenom} aurait tenté de breveter le bâillement",
    "{prenom} aurait offert des chocolats à son percepteur", "{prenom} saurait réciter l'annuaire de 1998",
    "{prenom} aurait fait passer un entretien d'embauche à un poisson rouge", "{prenom} aurait rebaptisé la cuisine « salle des opérations »",
    "{prenom} aurait installé un péage devant la salle de bains", "{prenom} aurait nommé chaque marche de l'escalier",
    "{prenom} aurait gagné un duel de regards contre un hibou", "{prenom} aurait perdu un débat contre un perroquet",
    "{prenom} aurait voulu acheter un mètre carré de nuage", "{prenom} aurait cuisiné une omelette pour toute la rue",
    "{prenom} aurait donné un concert de casseroles au balcon", "{prenom} aurait demandé au maire un jour férié à son nom",
    "{prenom} aurait mis une cravate à son aspirateur robot", "{prenom} aurait tenté de faire du ski sur la pelouse",
    "{prenom} aurait inventé un sport à base de chaussettes", "{prenom} aurait été vu{e} lisant le dictionnaire pour le plaisir",
    "{prenom} aurait gagné un concours de grimaces sans le faire exprès", "{prenom} aurait offert un parapluie à une statue",
    "{prenom} aurait voulu adopter une montgolfière", "{prenom} aurait engagé un détective pour retrouver une cuillère",
    "{prenom} aurait déclaré la guerre aux moustiques du jardin", "{prenom} aurait fait visiter la maison à une coccinelle",
    "{prenom} aurait demandé un selfie au facteur", "{prenom} aurait tenté de dresser un aspirateur",
    "{prenom} aurait pris des cours de tango avec un portemanteau", "{prenom} aurait voulu vendre des glaces en décembre",
    "{prenom} aurait goûté un pruneau au chocolat et pleuré de joie", "{prenom} aurait voulu inviter la Lune à dîner",
]
R_FIN = [
    "", " en plein mois d'août", " sans prévenir personne", " devant témoins", " un mardi, évidemment",
    " pour une raison que la science ignore", " à trois heures du matin", " entre la poire et le fromage",
    " avec un sérieux déconcertant", " en chaussettes", " sous l'œil des voisins", " au nom de l'art",
    " pour impressionner un pigeon", " avant même le petit-déjeuner", " en sifflotant", " sous la pluie",
    " lors d'un pique-nique", " en toute discrétion", " après un café de trop", " à la stupeur générale",
]


def rumeurs():
    combos = [(o, a, f) for o in R_OUV for a in R_ACT for f in R_FIN]
    random.shuffle(combos)
    res, par_act, par_ouv = [], {}, {}
    for o, a, f in combos:
        if par_act.get(a, 0) >= 14 or par_ouv.get(o, 0) >= 40:
            continue
        t = f"{o} {a}{f}."
        if B.mesurer("rumeur", t):
            continue
        res.append(t)
        par_act[a] = par_act.get(a, 0) + 1
        par_ouv[o] = par_ouv.get(o, 0) + 1
        if len(res) == N:
            break
    return res


# ------------------------------------------------------------------ HOROSCOPES (≤ 240 signes)
H_ASTRE = [
    "Mercure entre dans votre valise", "Vénus traverse votre placard à épices", "Mars campe dans votre jardin",
    "Jupiter fait la sieste dans votre maison", "La Lune vous regarde de travers", "Saturne a égaré ses anneaux chez vous",
    "Uranus joue de l'accordéon dans votre ciel", "Neptune arrose vos plantes à votre place", "Pluton revient de vacances",
    "Une étoile filante a raté son virage au-dessus de chez vous", "La Grande Ourse vous fait un clin d'œil",
    "Le Soleil se lève exprès pour vous", "Une comète passe la tête par la fenêtre", "Les astres font grève",
    "Votre étoile a changé de coiffure", "Mercure rétrograde jusqu'au marché", "Vénus s'est trompée de signe",
    "Mars a emprunté votre parapluie", "La Lune est pleine de bonnes intentions", "Jupiter a oublié ses clés chez vous",
    "La Voie lactée déborde sur votre semaine", "Saturne danse le madison", "Un astéroïde vous envoie ses amitiés",
    "Le ciel de la Garonne s'éclaircit pour vous", "Les planètes se sont donné rendez-vous dans votre cuisine",
    "Orion vise juste cette semaine", "Une nébuleuse vous a pris en affection", "Le Bélier céleste vous cède le passage",
    "Cassiopée a laissé un message sur votre répondeur", "La constellation du Pruneau brille au-dessus d'Agen",
]
H_PRED = [
    "une rencontre parfumée vous attend au détour d'un marché", "un compliment inattendu tombera du ciel",
    "vos chaussettes retrouveront enfin leur moitié", "un pigeon vous apportera une excellente nouvelle",
    "vous gagnerez un débat contre votre grille-pain", "une sieste mémorable se prépare",
    "votre plante verte vous fera enfin confiance", "un fou rire vous guette entre deux portes",
    "vous retrouverez un billet de cinq euros dans une vieille veste", "un voisin vous offrira des tomates",
    "la télécommande sera de votre côté", "votre café aura exactement la bonne température",
    "un inconnu vous demandera votre recette secrète", "vous serez l'invité{e} d'honneur d'un apéritif improvisé",
    "une chanson oubliée vous trottera dans la tête toute la journée", "les feux passeront au vert à votre approche",
    "vous battrez votre record de crêpes retournées", "un chien vous choisira comme humain préféré",
    "vous découvrirez un talent caché pour le yodel", "la boulangerie gardera la dernière baguette pour vous",
    "votre parapluie restera sec, par pure solidarité", "un souvenir d'enfance frappera à la porte",
    "une carte postale arrivera de nulle part", "vous trouverez enfin le bon côté du drap-housse",
    "votre ombre vous suivra avec un enthousiasme inhabituel", "un escargot vous dépassera, sans rancune",
    "vous aurez le dernier mot, pour une fois", "une odeur de gâteau vous guidera jusqu'au bonheur",
    "les étoiles vous prêteront leur éclat pour une soirée", "un cousin éloigné vous écrira en vers",
    "vous serez la vedette incontestée du salon", "un nuage prendra la forme de votre plat préféré",
    "vos clés vous attendront exactement où vous les cherchiez", "le facteur sonnera deux fois, avec le sourire",
    "un pruneau d'Agen changera votre vie", "vous réussirez une mayonnaise du premier coup",
    "une idée lumineuse vous viendra sous la douche", "la chance s'installera dans votre poche gauche",
    "un hérisson traversera votre chemin en vous saluant", "votre réveil oubliera de sonner un dimanche",
]
H_CONSEIL = [
    "Évitez les ronds-points le mardi.", "Portez du jaune, même en pensée.", "Ne contrariez pas le grille-pain.",
    "Buvez un verre d'eau et souriez à un inconnu.", "Méfiez-vous des chaussettes dépareillées.",
    "Dites oui à la deuxième part de tarte.", "Chantez sous la douche, les astres écoutent.",
    "Rangez un tiroir, un seul, c'est déjà héroïque.", "Faites une sieste stratégique vers quinze heures.",
    "Ne prêtez pas votre parapluie à Mars.", "Appelez la personne qui vous fait rire.",
    "Évitez de négocier avec les mouettes.", "Arrosez vos plantes, elles parlent de vous.",
    "Gardez une pièce dans votre poche droite.", "Saluez la Lune avant de dormir.",
    "Ne jouez pas aux cartes contre un chien.", "Prenez le chemin des écoliers.",
    "Offrez un compliment avant midi.", "Dansez trente secondes en cuisine.", "Laissez la dernière olive à quelqu'un d'autre.",
    "Écrivez une carte postale à l'ancienne.", "Goûtez un fruit que vous ne connaissez pas.",
    "Ne lisez pas les petites lignes du ciel.", "Faites confiance à votre premier fou rire.",
    "Évitez de discuter politique avec un perroquet.", "Laissez la fenêtre entrouverte aux bonnes nouvelles.",
    "Marchez le long de la Garonne, même en pensée.", "Ne sous-estimez jamais un pruneau.",
    "Pardonnez au réveil, il fait de son mieux.", "Prenez votre temps, les étoiles ne sont pas pressées.",
]
H_FETICHE = ["", "", "", " Chiffre porte-bonheur : 7.", " Couleur du jour : vert pomme.", " Chiffre porte-bonheur : 47.",
             " Couleur du jour : bordeaux.", " Objet fétiche : une cuillère en bois.", " Animal totem : le hérisson.",
             " Chiffre porte-bonheur : 12.", " Objet fétiche : un pruneau.", " Couleur du jour : jaune soleil."]


def horoscopes():
    combos = [(a, p, c, f) for a in H_ASTRE for p in H_PRED for c in H_CONSEIL for f in H_FETICHE]
    random.shuffle(combos)
    res, vus = [], {}
    for a, p, c, f in combos:
        if vus.get(("a", a), 0) >= 40 or vus.get(("p", p), 0) >= 27 or vus.get(("c", c), 0) >= 36:
            continue
        debut = random.random() < 0.35
        art = a.split(" ")[0] in ("La", "Le", "Les", "Une", "Un", "Votre")
        t = (f"{{prenom}}, {(a[0].lower() + a[1:]) if art else a} : {p}. {c}{f}" if debut else f"{a} : {p}. {c}{f}")
        if B.mesurer("horoscope", t):
            continue
        res.append(t)
        for k in (("a", a), ("p", p), ("c", c)):
            vus[k] = vus.get(k, 0) + 1
        if len(res) == N:
            break
    return res


# ------------------------------------------------------------------ MOTS DES HÔTES (≤ 700 signes)
M_DEBUT = [
    "{salut}, bienvenue {chez} : la maison a fait le ménage, sauf dans ses souvenirs.",
    "{salut}, vous voici {chez}, et la maison s'en réjouit déjà.",
    "{salut}, la porte est ouverte et la bouilloire est chaude.",
    "{salut}, la rédaction vous souhaite la bienvenue {chez}.",
    "{salut}, ce journal est le vôtre : lisez-le en pantoufles.",
    "{salut}, les draps sont frais et les ragots sont prêts.",
    "{salut}, la maison a ciré son parquet pour votre arrivée.",
    "{salut}, nous avons tout préparé, même les excuses pour le bruit du lave-vaisselle.",
    "{salut}, vous êtes ici chez vous, et nous sommes ravis de vous le dire par écrit.",
    "{salut}, la chambre vous attend, et le café aussi.",
    "{salut}, la maison a mis ses plus beaux volets pour vous accueillir.",
    "{salut}, la rédaction a veillé tard pour vous offrir ce numéro.",
    "{salut}, posez vos valises : ici, le temps prend son temps.",
    "{salut}, bienvenue dans la seule maison du Lot-et-Garonne qui imprime ses propres ragots.",
    "{salut}, la maison a compté les jours jusqu'à votre arrivée.",
    "{salut}, nos hôtes de marque ont droit à leur journal : vous voici en première page.",
    "{salut}, la maison vous salue, le jardin aussi, et même le chien, à sa façon.",
    "{salut}, ici, les nouvelles sont fraîches et les confitures maison.",
    "{salut}, prenez place : ce journal se lit mieux avec une tasse à la main.",
    "{salut}, la rédaction a le plaisir de vous accueillir {chez}.",
    "{salut}, nous avons gardé pour vous le meilleur oreiller et les meilleures histoires.",
    "{salut}, les nouvelles vont vite {chez} : la vôtre est la meilleure de la semaine.",
    "{salut}, la maison a rangé ses secrets, il ne reste que les bons.",
    "{salut}, bienvenue : ici, même le réveil est poli.",
    "{salut}, la rédaction vous ouvre ses colonnes et sa cuisine.",
]
M_MILIEU = [
    "Tout ce que vous lirez ici est rigoureusement inventé, à part notre joie de vous recevoir.",
    "Les rumeurs de ce numéro n'engagent que la rédaction, qui assume tout.",
    "Nous avons interrogé les voisins, le facteur et le chien : tous confirment que vous êtes attendu{e}.",
    "Le petit-déjeuner est servi à l'heure qui vous plaira, la rédaction ne juge pas.",
    "Si vous entendez du bruit la nuit, ce n'est que la maison qui raconte des histoires.",
    "Le jardin vous attend pour une promenade, les tomates pour une dégustation.",
    "Ce journal a été tiré à un seul exemplaire : il n'existe que pour vous.",
    "Nos enquêteurs ont travaillé sans relâche, entre deux siestes réglementaires.",
    "Les murs ont des oreilles, mais ils savent garder un secret.",
    "Nous déclinons toute responsabilité pour les fous rires provoqués par la page 3.",
    "La cuisine est ouverte jour et nuit, la rédaction aussi, presque.",
    "Si une rumeur vous semble exagérée, c'est qu'elle est en dessous de la vérité.",
    "Ce numéro a été relu par un comité d'experts composé d'une tasse de café et d'un stylo.",
    "La maison vous prête ses meilleurs coussins et son plus beau coucher de soleil.",
    "Le Wi-Fi est rapide, mais nous vous conseillons la conversation, encore plus rapide.",
    "Ici, on mange bien, on rit fort et on dort tard : vous êtes prévenu{e}.",
    "Toute ressemblance avec des faits réels serait une heureuse coïncidence.",
    "Les pruneaux sont dans le placard de gauche, les histoires dans ce journal.",
    "Nous avons fait de notre mieux pour que chaque page vous ressemble un peu.",
    "Le droit de réponse est ouvert : il se règle autour d'un apéritif.",
    "Les hôtes se tiennent à votre disposition pour toute réclamation, de préférence en terrasse.",
    "Ce journal est garanti sans mauvaise nouvelle, ou presque.",
    "La rédaction remercie ses sources, qui préfèrent rester anonymes et gourmandes.",
    "Le marché d'Agen ouvre tôt, mais rien ne vous oblige à le savoir.",
    "Les volets s'ouvrent quand vous voulez, le soleil s'adapte.",
    "Nous avons caché quelques surprises dans la maison : à vous de les trouver.",
    "Si vous croisez quelqu'un en pyjama dans le couloir, c'est sûrement la rédaction.",
    "Chaque article a été écrit avec amour et un peu de mauvaise foi.",
    "La maison a son règlement : être heureux, et rien d'autre.",
    "Les secrets de ce journal resteront entre nous, et la photocopieuse.",
    "Le calme de la campagne est offert, le chant du coq aussi, sans supplément.",
    "Nous avons réservé pour vous la meilleure place à table et le dernier mot.",
    "La rédaction a vérifié chaque information auprès d'un pigeon digne de confiance.",
    "Le temps d'un séjour, cette maison est la vôtre, ses défauts compris.",
    "Les hôtes ne garantissent ni la météo ni l'exactitude des faits, seulement l'accueil.",
    "Ici, on ne compte ni les parts de gâteau ni les éclats de rire.",
    "La page des rumeurs a été écrite tard le soir, ceci explique cela.",
    "Le chien de la maison a validé votre venue d'un clignement d'yeux.",
    "Si un article vous choque, sachez qu'il en existe une version encore pire, censurée par nos soins.",
    "Nous espérons que ce journal vous fera sourire autant qu'il nous a fait rire en l'écrivant.",
]
M_FIN = [
    "Bon séjour, et que la fête commence.", "Faites comme chez vous, et même un peu mieux.",
    "Nous sommes heureux de vous avoir ici.", "Bonne lecture, et à tout à l'heure en cuisine.",
    "Profitez de chaque instant, nous nous chargeons du reste.", "La maison vous embrasse.",
    "Que ce séjour soit doux, drôle et gourmand.", "Bienvenue, et merci d'être là.",
    "Gardez ce journal : il prendra de la valeur, au moins sentimentale.", "Reposez-vous, riez, revenez.",
    "Nous trinquerons ce soir à votre santé, et à nos rumeurs.", "Belle visite, et douces nuits.",
    "À très vite autour de la table.", "Que les étoiles veillent sur votre sommeil.",
    "Vous êtes ici chez vous, pour de vrai.", "Merci de faire vivre la maison.",
    "Le café sera prêt quand vous le serez.", "Que ce numéro vous accompagne jusqu'au prochain.",
    "Bon séjour parmi nous.", "Avec toute l'affection de la rédaction.",
    "Nous vous souhaitons des jours paisibles et des soirées bruyantes.", "Que la maison vous soit légère.",
    "À vos pantoufles, prêts, partez.", "Bonne lecture, bon appétit, bon séjour.", "Ici, vous êtes toujours attendu{e}.",
]


def mots():
    res, vus = [], set()
    while len(res) < N:
        d, f = random.choice(M_DEBUT), random.choice(M_FIN)
        m1, m2 = random.sample(M_MILIEU, 2)
        corps = f"{m1} {m2}" if random.random() < 0.6 else m1
        t = f"{d} {corps} {f}"
        cle_ = (d, m1, f)
        if cle_ in vus or B.mesurer("mot", t):
            continue
        vus.add(cle_)
        res.append(t)
    return res


# ------------------------------------------------------------------ TITRES (≤ 60 signes)
T_PRE = ["", "", "", "", "EXCLUSIF : ", "Scandale : ", "Révélations : ", "Choc : ", "Incroyable : ", "Dernière heure : ", "Affaire : "]
T_COEUR = [
    "{prenom} démasqué{e} au rayon fromages", "{prenom} fuit avec la télécommande", "{prenom} pris{e} la main dans le pot de confiture",
    "{prenom} avoue tout au chien", "{prenom} et le mystère du dernier croissant", "{prenom} sème la panique au marché",
    "{prenom} surpris{e} en pleine sieste", "{prenom} rafle tous les pruneaux", "{prenom} brise le silence",
    "{prenom} et le pigeon : l'enquête", "{prenom} relance le scandale du gâteau", "{prenom} détourne la playlist",
    "{prenom} pris{e} en flagrant délit de fou rire", "{prenom} et la chaussette disparue", "{prenom} fait trembler la cuisine",
    "{prenom} sort du silence", "{prenom} trahi{e} par un selfie", "{prenom} et l'affaire de la salade",
    "{prenom} piégé{e} par un hérisson", "{prenom} au cœur d'un trafic de cookies", "{prenom} sabote le karaoké",
    "{prenom} ridiculise le grille-pain", "{prenom} et la nuit de tous les excès", "{prenom} squatte le canapé",
    "{prenom} et le secret de la piscine", "{prenom} s'empare du barbecue", "{prenom} en garde à vue chez le boulanger",
    "{prenom} et le complot des chaussons", "{prenom} cité{e} dans l'affaire du fromage", "{prenom} ose tout",
    "{prenom} : la photo qui dérange", "{prenom} et son double maléfique", "{prenom} hypnotise le chien",
    "{prenom} et la fondue de la discorde", "{prenom} change de vie (pour un week-end)", "{prenom} négocie avec un radar",
    "{prenom} et les pruneaux de la honte", "{prenom} perd la tête au loto", "{prenom} démissionne du rangement",
    "{prenom} pris{e} en photo sans maquillage du chien", "{prenom} et le tablier de la discorde", "{prenom} vole la vedette",
    "{prenom} recherché{e} par la brigade du goûter", "{prenom} fait exploser l'audimat du salon", "{prenom} sur la piste du dessert",
    "{prenom} défie la Garonne", "{prenom} et l'énigme du placard", "{prenom} se lâche en terrasse",
    "{prenom} et l'apéritif qui a tout changé", "{prenom} en plein délire", "{prenom} refuse de rendre le plaid",
    "{prenom} et la nuit blanche", "{prenom} au bord de la crise de fou rire", "{prenom} victime d'un sortilège de sieste",
    "{prenom} et la trottinette volée", "{prenom} déchaîne la piste de danse", "{prenom} interdit{e} de buffet",
    "{prenom} et le grand mensonge de la recette", "{prenom} fait scandale au vide-grenier", "{prenom} et la vache mystère",
    "{prenom} pris{e} en défaut de croissants", "{prenom} et la guerre des coussins", "{prenom} enfin démasqué{e}",
    "{prenom} et le coup de la panne", "{prenom} s'invite au mariage du voisin", "{prenom} et l'escargot fugitif",
    "{prenom} jette un froid sur le jardin", "{prenom} prend le pouvoir à table", "{prenom} et le gâteau fantôme",
    "{prenom} fait main basse sur le chocolat", "{prenom} ensorcelle le facteur", "{prenom} et la tarte du siècle",
    "{prenom} dans de beaux draps", "{prenom} et le trésor du grenier", "{prenom} joue les divas au bord de l'eau",
    "{prenom} et la confiture interdite", "{prenom} face à la meute de poules", "{prenom} rattrapé{e} par son passé",
    "{prenom} et la nuit du pyjama", "{prenom} signe son grand retour", "{prenom} affole les compteurs",
    "{prenom} et le crime du canapé", "{prenom} aperçu{e} au bal du village", "{prenom} et le mystère du jardin",
    "{prenom} pris{e} au piège du dessert", "{prenom} contre-attaque", "{prenom} et la vérité sur la soupe",
    "{prenom} renverse la table", "{prenom} et la photo interdite", "{prenom} plus fort{e} que le grille-pain",
    "{prenom} et l'affaire des chaussettes", "{prenom} sous le feu des projecteurs", "{prenom} et la recette volée",
    "{prenom} n'en rate pas une", "{prenom} et les voisins de la honte", "{prenom} ose le maillot à fleurs",
    "{prenom} et le pique-nique maudit", "{prenom} sur tous les fronts", "{prenom} et le bain de minuit",
    "{prenom} séduit la boulangère", "{prenom} et le fromage qui pue", "{prenom} victime de son succès",
    "{prenom} et la randonnée qui tourne mal", "{prenom} squatte la salle de bains", "{prenom} et le gâteau de la colère",
    "{prenom} dans l'œil du cyclone", "{prenom} fait sa loi", "{prenom} et le parapluie de la discorde",
    "{prenom} se mêle de tout", "{prenom} et le pédalo de minuit", "{prenom} électrise la soirée",
    "{prenom} et la crêpe ratée", "{prenom} a encore frappé", "{prenom} et la cave secrète",
    "{prenom} pris{e} la main dans le sac (de chips)", "{prenom} sème le trouble", "{prenom} et la dernière part",
    "{prenom} intouchable", "{prenom} et la tondeuse folle", "{prenom} jure qu'on l'a piégé{e}",
    "{prenom} et la nuit au clair de lune", "{prenom} en roue libre", "{prenom} fait la une, encore",
    "{prenom} et le pique-nique de la honte", "{prenom} dérape au bowling", "{prenom} et la poule savante",
    "{prenom} mène l'enquête", "{prenom} et le pain perdu retrouvé", "{prenom} tient tête au chien",
    "{prenom} et le secret de famille", "{prenom} se fait remarquer", "{prenom} et les bulles de la discorde",
    "{prenom} libère le hamac", "{prenom} et l'orage de minuit", "{prenom} dans la tourmente",
]
T_SUF = ["", "", "", "", " !", " : la photo", " : les preuves", " : la maison sous le choc", " : ce qu'on vous cache", " : le dossier"]


def titres():
    combos = [(p, c, s) for p in T_PRE for c in T_COEUR for s in T_SUF]
    random.shuffle(combos)
    res, par_c, cles = [], {}, set()
    for p, c, s in combos:
        if par_c.get(c, 0) >= 10 or B.cle("titre", f"{p}{c}{s}") in cles:
            continue
        if c.startswith("{prenom} :") and s.startswith(" :"):
            continue
        t = f"{p}{c}{s}"
        if B.mesurer("titre", t):
            continue
        res.append(t)
        cles.add(B.cle("titre", t))
        par_c[c] = par_c.get(c, 0) + 1
        if len(res) == N:
            break
    return res


# ------------------------------------------------------------------ COURRIER DES LECTEURS (lettre ::: signature ::: réponse)
C_LETTRE = [
    "Depuis le départ de {prenom}, mon chien refuse de manger : il réclame ses imitations de mouette.",
    "{prenom} m'a emprunté mon arrosoir et me le rend toujours rempli de confettis.",
    "Chaque fois que {prenom} passe devant chez moi, mes géraniums se mettent à pousser plus vite.",
    "J'ai vu {prenom} saluer le rond-point de la sortie d'Agen avec une révérence parfaite.",
    "Depuis que {prenom} a dormi dans la chambre d'amis, l'oreiller ne veut plus servir à personne d'autre.",
    "{prenom} a appris à mon perroquet une chanson que je n'arrive plus à lui faire oublier.",
    "Mon coq refuse de chanter tant que {prenom} n'est pas réveillé{e}.",
    "{prenom} a gagné notre concours de belote sans jamais regarder ses cartes.",
    "Depuis le passage de {prenom}, la boulangerie ne vend plus que des croissants en forme de cœur.",
    "Ma tondeuse a démarré toute seule en entendant le nom de {prenom}.",
    "{prenom} a laissé un mot sur mon pare-brise : « Bravo pour le créneau ». Je suis ému.",
    "Le chien du voisin ne remue la queue que pour {prenom}, et cela me vexe un peu.",
    "{prenom} a goûté ma confiture de figues et a pleuré de joie. Dois-je en refaire ?",
    "Depuis la visite de {prenom}, mes poules pondent des œufs presque carrés.",
    "J'ai croisé {prenom} au marché en train de négocier le prix d'un melon avec beaucoup d'éloquence.",
    "{prenom} a rangé ma cuisine pendant que je dormais. Je ne retrouve plus rien, mais c'est magnifique.",
    "Mon aspirateur robot suit {prenom} partout comme un petit chien.",
    "{prenom} m'a raconté une histoire si drôle que mon dentier est tombé dans la soupe.",
    "Depuis le séjour de {prenom}, la Garonne coule un peu plus joyeusement, il me semble.",
    "{prenom} a battu mon record de sieste dans le hamac. Je demande une revanche.",
    "La cloche de l'église a sonné treize coups le jour de l'arrivée de {prenom}.",
    "{prenom} a appris la valse à mon épouvantail. Il ne veut plus garder le champ.",
    "J'ai prêté un livre à {prenom} et il m'est revenu avec un marque-page en dentelle.",
    "Mon GPS ne parle plus que de {prenom} depuis qu'il l'a guidé{e} jusqu'ici.",
    "{prenom} a fait rire ma tante, qui n'avait pas ri depuis le Tour de France de 1987.",
    "Depuis que {prenom} est passé{e} au potager, mes tomates se tiennent plus droites.",
    "{prenom} a reconnu à l'aveugle les douze confitures de ma grand-mère.",
    "Je soupçonne {prenom} d'avoir fini le dernier morceau de fromage et d'avoir accusé le chien.",
    "{prenom} a garé sa voiture si droit que le géomètre est venu prendre des photos.",
    "Mon parapluie refuse de s'ouvrir quand {prenom} n'est pas là pour l'admirer.",
    "{prenom} a offert des chouquettes à toute la rue, et maintenant tout le monde attend son retour.",
    "Depuis le passage de {prenom}, mon grille-pain ne brûle plus rien. Est-ce un miracle ?",
    "{prenom} a chanté sous la douche et toute la vallée a applaudi.",
    "Les canards du lac font la queue pour dire bonjour à {prenom}.",
    "{prenom} a appelé ma plante verte par son prénom. Elle a fleuri dans la nuit.",
    "J'ai invité {prenom} à prendre le café et il est resté trois heures à parler de pruneaux.",
    "{prenom} a lu mon horoscope à voix haute et tout s'est réalisé avant midi.",
    "Depuis que {prenom} a dormi ici, le réveil sonne avec plus de douceur.",
    "{prenom} a gagné une partie de pétanque contre le président du club, devant témoins.",
    "Mon chien a déménagé dans la valise de {prenom}. Comment le récupérer ?",
    "{prenom} a fait une tarte si bonne que le facteur a sonné trois fois.",
    "Ma voisine prétend que {prenom} lui a appris à siffler avec deux doigts en une soirée.",
    "{prenom} a trié mes chaussettes par couleur, par taille et par humeur.",
    "Depuis la venue de {prenom}, le Wi-Fi capte même dans la cave.",
    "{prenom} a raconté une blague au marchand de légumes, qui m'a fait une remise de dix pour cent.",
    "Le hérisson du jardin ne sort plus que lorsque {prenom} est sur la terrasse.",
    "{prenom} a fait la vaisselle en chantant de l'opéra. Les assiettes brillent encore.",
    "J'ai trouvé une plume de paon dans ma boîte aux lettres, signée {prenom}.",
    "{prenom} a répondu à toutes les questions du quiz de la radio locale avant l'animateur.",
    "Depuis le départ de {prenom}, la maison paraît bien calme, et le frigo bien plein.",
]
C_QUESTION = ["", "", " Que faire ?", " Est-ce normal ?", " Dois-je m'inquiéter ?", " Faut-il prévenir le maire ?",
              " Qui peut m'aider ?", " Est-ce contagieux ?", " Que me conseillez-vous ?", " Dois-je porter plainte ?",
              " La rédaction peut-elle enquêter ?", " Est-ce un signe ?", " Comment l'en remercier ?", " Faut-il s'en réjouir ?"]
C_SIGNE = [
    "Un voisin inquiet", "Une tomate du jardin", "Le canapé du salon", "Une poule de Moirax", "Le facteur, ému",
    "Une lectrice fidèle d'Agen", "Le hamac de la terrasse", "Un pruneau sous le choc", "La tondeuse du voisin",
    "Un pigeon voyageur", "Le chien de la maison", "Une habituée du marché", "La cafetière, en larmes",
    "Un supporter du SUA", "Le géranium du balcon", "Une cousine éloignée", "Le boulanger du coin",
    "Une grenouille de la mare", "L'épouvantail du champ", "Le grille-pain de la cuisine", "Un lecteur assidu",
    "Le parapluie de l'entrée", "Une voisine curieuse", "Le coq du poulailler", "La boîte aux lettres",
    "Un admirateur discret", "Le hérisson du jardin", "Une confiture de figues", "Le réveil de la chambre d'amis",
    "Le club de belote", "Une fourmi travailleuse", "Le GPS de la voiture", "La cloche de l'église",
    "Un canard du lac", "La plante verte du salon", "Un témoin qui préfère rester anonyme", "La radio locale",
    "Le marchand de légumes", "Une chaise longue fatiguée", "L'oreiller de la chambre d'amis",
]
C_REPONSE = [
    "La rédaction conseille de prolonger le séjour.", "Nous transmettons, sans garantie de résultat.",
    "La rédaction a ouvert une enquête, entre deux siestes.", "Rien d'anormal : c'est l'effet habituel de notre invité{e}.",
    "Nous vous recommandons la patience, et une part de gâteau.", "La rédaction plaide coupable, avec le sourire.",
    "Nos experts se penchent sur votre cas avec le plus grand sérieux.", "C'est un signe, et il est excellent.",
    "Courage : le prochain séjour est déjà dans les tuyaux.", "La rédaction vous remercie pour ce témoignage bouleversant.",
    "Nous n'avons pas les moyens de lutter, et nous n'en avons pas envie.", "La rédaction confirme et en redemande.",
    "Votre lettre a été lue à voix haute au petit-déjeuner.", "Nous classons l'affaire, faute de preuves et de sérieux.",
    "La rédaction décline toute responsabilité, mais pas l'apéritif.", "Nous vous suggérons de vous asseoir et de savourer.",
    "La rédaction a vérifié : tout est vrai, et même pire.", "Gardez cette lettre : elle prendra de la valeur.",
    "C'est contagieux, et c'est tant mieux.", "La rédaction vous envoie tout son soutien et un pot de confiture.",
    "Nous avons posé la question à l'intéressé{e}, qui a éclaté de rire.", "Patience : ce genre de miracle se reproduit souvent ici.",
    "La rédaction ne peut rien pour vous, à part rire avec vous.", "Affaire suivie de près par notre service des rumeurs.",
    "Nous vous conseillons de prévenir les voisins, et de mettre la bouilloire.", "Ne changez rien, c'est parfait.",
    "Le comité de rédaction a voté : c'est une bonne nouvelle.", "Votre cas n'est pas isolé : la maison entière est touchée.",
    "La rédaction prend note et prépare une édition spéciale.", "Rassurez-vous, la science non plus n'a pas d'explication.",
]


def courrier():
    combos = [(l, q, si, r) for l in C_LETTRE for q in C_QUESTION for si in C_SIGNE for r in C_REPONSE]
    random.shuffle(combos)
    res, cles, par = [], set(), {}
    for l, q, si, r in combos:
        if par.get(l, 0) >= 20 or par.get(("s", si), 0) >= 26 or par.get(("r", r), 0) >= 34:
            continue
        if q and l.endswith("?"):
            continue
        t = f"{l}{q} ::: {si} ::: {r}"
        if B.cle("courrier", t) in cles or B.mesurer("courrier", t):
            continue
        res.append(t)
        cles.add(B.cle("courrier", t))
        for k in (l, ("s", si), ("r", r)):
            par[k] = par.get(k, 0) + 1
        if len(res) == N:
            break
    return res


if __name__ == "__main__":
    parts = {"RUMEURS": rumeurs(), "HOROSCOPES": horoscopes(), "MOTS": mots(), "TITRES": titres(), "COURRIER": courrier()}
    lignes = ["# Banque d'inspiration de Gazette — fabriquée par Claude le 18/11/2026",
              "# Balises : {prenom} {salut} {chez} {il} {e} — courrier : lettre ::: signature ::: réponse — à importer dans Réglages › Banque d'inspiration", ""]
    for nom, textes in parts.items():
        print(nom, len(textes))
        lignes += [f"# {nom}", *[f"- {t}" for t in textes], ""]
    open(sys.argv[1], "w", encoding="utf-8").write("\n".join(lignes))
