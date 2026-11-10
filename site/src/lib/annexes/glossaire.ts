// Le glossaire du site : les mots du parcours, de la Partie 0 au chapitre 1.6, chacun
// défini en deux phrases au plus et renvoyé aux chapitres qui l'expliquent.
//
// Chaque définition a été relue dans son chapitre (9 novembre 2026, puis de 1.1 à 1.6 au
// bilan de la Partie 1, le 10) et ne le contredit pas. Pour 1.5 et 1.6, pas encore parus,
// elle suit leurs brouillons (src/brouillons/chapitres/) et le code de forge qu'ils
// montrent : planning.py, boucle.py et sauvegarde.py pour 1.5, perte.py et qcm.py pour
// 1.6. La page affiche leurs renvois « à venir », sans lien, tant que chapitresParus()
// ne les connaît pas.
//
// Les textes sont bruts, comme ceux de parcours.ts : des espaces ordinaires devant
// « ; : ! ? » et dans les guillemets, des apostrophes droites. La page leur applique
// typographier() à l'affichage. La plupart des nombres sont laissés aux chapitres, qui
// les tirent de leurs sources : une définition dit ce qu'est un mot, pas une mesure.
//
// Ce module n'importe rien : un parcours Playwright peut le lire.

/** Un chapitre qui parle du terme, et ce qu'il en fait. */
export interface Renvoi {
  /** Le numéro du chapitre : « 0.2 ». */
  chapitre: string;
  /** Ce que le chapitre fait du terme, dit avant « en » : « expliqué », « calculé », « rangé en tenseur ». */
  verbe: string;
}

/** Un terme du glossaire. */
export interface Terme {
  /** L'ancre du terme dans la page (« #perplexite ») : minuscules sans accents et tirets. */
  id: string;
  /** Le mot tel qu'il s'écrit, en minuscules sauf s'il s'écrit en capitales (« BPE »). */
  terme: string;
  /** Son nom en anglais, quand il diffère : on le croise dans la documentation. */
  anglais?: string;
  /** Un autre nom français, dit dans les chapitres : « poids » pour « paramètre ». */
  aussi?: string;
  /** Pour un mot anglais gardé tel quel, son nom français : « découpeur » pour « tokenizer ». */
  enFrancais?: string;
  /** Deux phrases au plus, 300 caractères au plus. */
  definition: string;
  /**
   * Les chapitres qui en parlent, dans l'ordre où la page les cite : en général celui qui
   * l'explique d'abord (AdamW, « citée en 0.5, expliquée en 1.5 », fait exception).
   */
  renvois: readonly Renvoi[];
  /** Des termes voisins du glossaire, par leur identifiant. */
  voirAussi?: readonly string[];
}

const r = (chapitre: string, verbe: string): Renvoi => ({ chapitre, verbe });

/** Les termes, dans l'ordre alphabétique français (Intl.Collator('fr')). */
export const GLOSSAIRE: readonly Terme[] = [
  {
    id: 'adamw',
    terme: 'AdamW',
    definition:
      "La recette qui corrige les poids de ton IA à chaque pas. Au lieu de reculer chaque poids du taux fois sa pente, elle règle la longueur de son pas d'après ses pentes passées.",
    renvois: [r('0.5', 'citée'), r('1.5', 'expliquée')],
    voirAussi: ['optimiseur', 'descente-de-gradient', 'taux-d-apprentissage', 'pas-d-entrainement'],
  },
  {
    id: 'attention',
    terme: 'attention',
    definition:
      "La pièce du transformer où les jetons se parlent : chacun puise, dans ceux qui le précèdent et en lui-même, ce qui l'aide à prédire la suite. Le produit scalaire de sa requête avec chaque clé, passé dans softmax, pèse la moyenne des valeurs qu'il reçoit.",
    renvois: [r('1.4', 'expliquée')],
    voirAussi: ['tete-d-attention', 'masque', 'produit-scalaire', 'softmax'],
  },
  {
    id: 'bf16',
    terme: 'bf16',
    anglais: 'bfloat16',
    definition:
      "Une façon d'écrire les nombres à virgule sur 16 bits au lieu des 32 de float32 : chacun prend deux fois moins de place, avec moins de chiffres significatifs. Sur la carte, ton IA calcule en bf16 et garde ses poids en float32.",
    renvois: [r('0.4', 'expliqué')],
    voirAussi: ['tenseur', 'carte-graphique'],
  },
  {
    id: 'biais',
    terme: 'biais',
    anglais: 'bias',
    definition:
      "Le nombre qu'un neurone ajoute à sa somme pondérée avant de décider. Il déplace la frontière du neurone sans la tourner, et l'entraînement le règle comme les autres poids.",
    renvois: [r('0.5', 'expliqué')],
    voirAussi: ['neurone', 'parametre'],
  },
  {
    id: 'bits-par-octet',
    terme: 'bits par octet',
    anglais: 'bits per byte',
    definition:
      "La perte ramenée à un octet de texte plutôt qu'à un jeton, et comptée en bits. Deux tokenizers ne découpent pas le même texte en autant de jetons : c'est cette mesure qui compare leurs modèles.",
    renvois: [r('1.6', 'expliqués')],
    voirAussi: ['nat', 'perte', 'perplexite', 'tokenizer'],
  },
  {
    id: 'bloc',
    terme: 'bloc',
    anglais: 'block',
    definition:
      "Un étage du transformer : l'attention, puis le MLP, chacun précédé d'une RMSNorm et ajouté au vecteur par une connexion résiduelle. Ton IA empile plusieurs blocs de même forme.",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['transformer', 'attention', 'mlp', 'connexion-residuelle', 'rmsnorm'],
  },
  {
    id: 'bpe',
    terme: 'BPE',
    anglais: 'byte pair encoding',
    definition:
      'La méthode de découpage de presque tous les grands modèles : on part des lettres, puis on fusionne, encore et encore, la paire de voisins la plus fréquente. Le nom veut dire « encodage par paires ».',
    renvois: [r('1.3', 'expliqué')],
    voirAussi: ['fusion', 'tokenizer', 'vocabulaire'],
  },
  {
    id: 'carte-d-un-jeu-de-donnees',
    terme: "carte d'un jeu de données",
    anglais: 'dataset card',
    definition:
      "La page qui présente un jeu de données sur Hugging Face : ce qu'il contient, d'où il vient, sous quelle licence. Un modèle a aussi la sienne, sa carte de modèle ; rien à voir avec la carte graphique.",
    renvois: [r('1.2', 'présentée')],
    voirAussi: ['jeu-de-donnees', 'licence'],
  },
  {
    id: 'carte-graphique',
    terme: 'carte graphique',
    aussi: 'GPU',
    anglais: 'graphics card',
    definition:
      'Une puce faite de milliers de petits calculateurs, qui font la même opération en même temps, avec une mémoire très rapide. Elle entraîne ton IA bien plus vite que le processeur.',
    renvois: [r('0.3', 'expliquée')],
    voirAussi: ['cuda', 'pytorch', 'efficacite'],
  },
  {
    id: 'connexion-residuelle',
    terme: 'connexion résiduelle',
    anglais: 'residual connection',
    definition:
      "Le « x + » d'un bloc : chaque pièce ajoute sa correction au vecteur au lieu de le remplacer. Sans lui, la trace de chaque jeton s'efface de bloc en bloc, dès le départ de l'entraînement.",
    renvois: [r('1.4', 'expliquée')],
    voirAussi: ['bloc'],
  },
  {
    id: 'contamination',
    terme: 'contamination',
    definition:
      "Quand les questions d'un test se trouvent déjà dans les textes d'entraînement d'un modèle. Il a pu en retenir les réponses par cœur, et son score ne dit plus ce qu'il sait.",
    renvois: [r('1.6', 'expliquée')],
    voirAussi: ['qcm', 'validation'],
  },
  {
    id: 'contexte',
    terme: 'contexte',
    anglais: 'context',
    definition:
      "Les morceaux du texte déjà écrit qu'un modèle regarde pour deviner le suivant. Le modèle de 1.1 en voit quelques caractères ; ton IA voit beaucoup plus loin, en jetons.",
    renvois: [r('1.1', 'expliqué')],
    voirAussi: ['modele-de-langage', 'malediction-de-la-dimension', 'jeton'],
  },
  {
    id: 'cuda',
    terme: 'CUDA',
    definition:
      "La boîte à outils de NVIDIA pour calculer sur ses cartes graphiques. Les versions de PyTorch pour la carte embarquent la leur : il suffit d'installer le pilote de la carte.",
    renvois: [r('0.3', 'expliqué')],
    voirAussi: ['carte-graphique', 'pytorch'],
  },
  {
    id: 'decroissance-des-poids',
    terme: 'décroissance des poids',
    anglais: 'weight decay',
    definition:
      "Un réglage de l'optimiseur : à chaque pas, il tire doucement chaque poids vers 0. Forge ne l'applique qu'aux matrices de ton IA, pas aux poids de ses RMSNorm.",
    renvois: [r('1.5', 'expliquée')],
    voirAussi: ['adamw', 'optimiseur'],
  },
  {
    id: 'descente-de-gradient',
    terme: 'descente de gradient',
    anglais: 'gradient descent',
    definition:
      "La règle d'apprentissage : à chaque pas, chaque poids recule du taux fois sa pente. Avec un taux bien choisi, l'erreur baisse pas après pas.",
    renvois: [r('0.2', 'expliquée'), r('0.5', 'appliquée')],
    voirAussi: ['gradient', 'taux-d-apprentissage', 'perte'],
  },
  {
    id: 'diffusion',
    terme: 'diffusion',
    anglais: 'broadcasting',
    definition:
      "La règle par laquelle PyTorch calcule entre deux tenseurs de formes différentes : il les aligne par la droite, puis étire les tailles 1 pour suivre l'autre. Rien n'est recopié en mémoire.",
    renvois: [r('0.4', 'expliquée')],
    voirAussi: ['tenseur', 'forme'],
  },
  {
    id: 'doublon',
    terme: 'doublon',
    anglais: 'duplicate',
    definition:
      "Un texte présent plusieurs fois dans les données, comme une dépêche reprise par dix sites. Lu dix fois, il pèserait dix fois plus : forge ne garde chaque texte qu'une fois, reconnu par son empreinte.",
    renvois: [r('1.2', 'expliqué')],
    voirAussi: ['empreinte', 'jeu-de-donnees'],
  },
  {
    id: 'echauffement',
    terme: 'échauffement',
    anglais: 'warmup',
    definition:
      "Les premiers pas d'un entraînement, où le taux d'apprentissage monte en ligne droite, de 0 à son maximum. Au début, les poids sont tirés au hasard et les gradients partent dans tous les sens : de grands pas déstabiliseraient le modèle.",
    renvois: [r('1.5', 'expliqué')],
    voirAussi: ['planning-du-taux', 'taux-d-apprentissage'],
  },
  {
    id: 'ecretage',
    terme: 'écrêtage',
    anglais: 'gradient clipping',
    definition:
      "Une sécurité de l'entraînement : quand la norme du gradient dépasse un seuil, toutes ses pentes sont réduites dans la même proportion. Un lot bizarre ne fait plus faire de saut énorme aux poids.",
    renvois: [r('1.5', 'expliqué')],
    voirAussi: ['gradient', 'adamw'],
  },
  {
    id: 'efficacite',
    terme: 'efficacité',
    definition:
      "La part de la crête de calcul d'une carte qu'un entraînement utilise vraiment. Aucun ne l'atteint : il faut aussi lire la mémoire, et des milliers de cartes doivent s'attendre.",
    renvois: [r('0.4', 'expliquée')],
    voirAussi: ['carte-graphique'],
  },
  {
    id: 'empreinte',
    terme: 'empreinte',
    anglais: 'hash',
    definition:
      "Un code tiré d'un texte, toujours le même pour le même texte : forge la calcule avec SHA-1, en 40 chiffres hexadécimaux. Elle reconnaît les doublons, et choisit sans tirage les textes de validation.",
    renvois: [r('1.2', 'expliquée')],
    voirAussi: ['doublon', 'validation'],
  },
  {
    id: 'entropie-croisee',
    terme: 'entropie croisée',
    anglais: 'cross-entropy',
    definition:
      "L'erreur d'un modèle qui donne des probabilités : −ln de la chance qu'il donnait à la bonne réponse, en moyenne sur ses prédictions. C'est elle que ton IA fait baisser pendant son entraînement.",
    renvois: [r('0.2', 'expliquée'), r('0.5', 'binaire')],
    voirAussi: ['perte', 'probabilite', 'perplexite'],
  },
  {
    id: 'exactitude-normalisee',
    terme: 'exactitude normalisée',
    anglais: 'normalized accuracy',
    definition:
      "La part des questions d'un QCM où le modèle préfère la bonne réponse, une fois chaque score divisé par les octets de sa réponse. Sans cette division, les réponses courtes, qui ont moins de jetons à deviner, gagneraient trop souvent.",
    renvois: [r('1.6', 'expliquée')],
    voirAussi: ['qcm', 'marge-du-hasard'],
  },
  {
    id: 'forge',
    terme: 'forge',
    definition:
      "Le moteur de ton IA, écrit en Python : il télécharge et nettoie ses textes, apprend son tokenizer, l'entraîne, la sauvegarde et l'évalue. Les chapitres de la Partie 1 en lisent le code, pièce par pièce.",
    renvois: [r('1.2', 'présenté')],
    voirAussi: ['melange', 'tokenizer', 'sauvegarde'],
  },
  {
    id: 'forme',
    terme: 'forme',
    anglais: 'shape',
    definition:
      'La liste des tailles d\'un tenseur, une par dimension : (3, 4) pour une matrice de 3 lignes et 4 colonnes. Elle dit ce qui se multiplie avec quoi, et ce qui en sort.',
    renvois: [r('0.2', 'vue'), r('0.4', 'expliquée')],
    voirAussi: ['tenseur', 'matrice', 'diffusion'],
  },
  {
    id: 'fusion',
    terme: 'fusion',
    anglais: 'merge',
    definition:
      "Une étape de l'apprentissage du BPE : la paire de symboles voisins la plus fréquente devient un seul symbole. Chaque fusion apprise ajoute un morceau au vocabulaire.",
    renvois: [r('1.3', 'expliquée')],
    voirAussi: ['bpe', 'vocabulaire'],
  },
  {
    id: 'gradient',
    terme: 'gradient',
    definition:
      "La liste des pentes de la perte, une par poids. Elle dit, pour chaque poids, dans quel sens il ferait monter l'erreur.",
    renvois: [r('0.2', 'expliqué'), r('0.5', 'calculé')],
    voirAussi: ['descente-de-gradient', 'retropropagation', 'regle-de-la-chaine'],
  },
  {
    id: 'graine',
    terme: 'graine',
    anglais: 'seed',
    definition:
      "Le nombre dont part le hasard d'un ordinateur : la même graine donne toujours la même suite de tirages, sur toutes les machines. C'est ce qui permet de refaire exactement un calcul tiré au hasard.",
    renvois: [r('0.2', 'expliquée')],
    voirAussi: ['probabilite'],
  },
  {
    id: 'jeton',
    terme: 'jeton',
    anglais: 'token',
    definition:
      "Un morceau de texte, avec son numéro : c'est ce que lit vraiment un modèle de langage. Un mot courant tient souvent en un seul jeton, un mot rare en plusieurs.",
    renvois: [r('1.3', 'expliqué')],
    voirAussi: ['tokenizer', 'vocabulaire', 'plongement'],
  },
  {
    id: 'jeu-de-donnees',
    terme: 'jeu de données',
    anglais: 'dataset',
    definition:
      "Un ensemble de textes, de code ou de questions, rassemblé et publié pour entraîner ou évaluer des modèles. Chacun a sa licence : l'annuaire des données en liste quelques-uns.",
    renvois: [r('1.2', 'expliqué')],
    voirAussi: ['licence', 'melange'],
  },
  {
    id: 'licence',
    terme: 'licence',
    anglais: 'license',
    definition:
      "Le texte qui dit ce qu'on a le droit de faire d'un jeu de données ou d'un code : s'en servir, le partager, et à quelles conditions. Un texte publié n'est pas pour autant libre de droits.",
    renvois: [r('1.2', 'expliquée')],
    voirAussi: ['jeu-de-donnees'],
  },
  {
    id: 'lissage-de-laplace',
    terme: 'lissage de Laplace',
    anglais: 'Laplace smoothing',
    definition:
      'Ajouter 1 au compte de chaque caractère possible avant de passer aux probabilités, pour qu\'aucun ne soit jugé impossible. Sans lui, un seul caractère jamais vu rendrait la perplexité infinie.',
    renvois: [r('1.1', 'expliqué')],
    voirAussi: ['probabilite', 'perplexite'],
  },
  {
    id: 'log-vraisemblance',
    terme: 'log-vraisemblance',
    anglais: 'log-likelihood',
    definition:
      "La somme des ln p des jetons d'un texte déjà écrit, chacun sachant tout ce qui le précède : c'est par elle qu'on mesure sa vraisemblance. Plus elle est haute, plus le modèle croit à ce texte.",
    renvois: [r('1.6', 'expliquée')],
    voirAussi: ['vraisemblance', 'qcm', 'perte'],
  },
  {
    id: 'logits',
    terme: 'logits',
    definition:
      'Les scores que le modèle donne à chaque jeton possible, à chaque position du texte, calculés avec la table du plongement. Softmax les change ensuite en probabilités.',
    renvois: [r('1.4', 'expliqués'), r('1.6', 'repris')],
    voirAussi: ['softmax', 'plongement', 'poids-lies'],
  },
  {
    id: 'lot',
    terme: 'lot',
    anglais: 'batch',
    definition:
      "Les exemples qu'un pas d'entraînement traite ensemble, tirés au hasard parmi les données. Rangés dans un tenseur, ils ajoutent une dimension : un lot de matrices en a trois.",
    renvois: [r('0.5', 'expliqué'), r('0.4', 'rangé en tenseur')],
    voirAussi: ['micro-lot', 'tenseur', 'descente-de-gradient'],
  },
  {
    id: 'malediction-de-la-dimension',
    terme: 'malédiction de la dimension',
    anglais: 'curse of dimensionality',
    definition:
      'Plus le contexte est long, plus le texte à prédire contient de suites jamais vues pendant l\'entraînement. Yoshua Bengio et ses collègues l\'ont décrite en 2003, avec une réponse : un réseau qui rapproche les contextes qui se ressemblent.',
    renvois: [r('1.1', 'expliquée')],
    voirAussi: ['contexte'],
  },
  {
    id: 'marge-du-hasard',
    terme: 'marge du hasard',
    definition:
      "L'écart au hasard qu'un score de QCM doit dépasser pour dire quelque chose du modèle : un modèle qui répondrait au hasard s'en écarte moins, 95 fois sur 100. Elle rétrécit quand le nombre de questions grandit.",
    renvois: [r('1.6', 'expliquée')],
    voirAussi: ['qcm'],
  },
  {
    id: 'masque',
    terme: 'masque',
    anglais: 'causal mask',
    definition:
      "Dans l'attention, ce qui interdit à un jeton de regarder ceux qui le suivent : il ne voit que lui-même et ceux d'avant. Sans lui, pendant l'entraînement, il suffirait de lire le jeton à deviner.",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['attention'],
  },
  {
    id: 'matrice',
    terme: 'matrice',
    anglais: 'matrix',
    definition:
      "Un tableau de nombres rangés en lignes et en colonnes. La multiplier par un vecteur, c'est faire un produit scalaire par ligne.",
    renvois: [r('0.2', 'expliquée')],
    voirAussi: ['vecteur', 'produit-scalaire', 'forme'],
  },
  {
    id: 'melange',
    terme: 'mélange',
    anglais: 'data mixture',
    definition:
      'Les parts de chaque source dans ce que lit ton IA, comptées en octets de texte : du web en français, Wikipédia en français et du code Python. Il est écrit une seule fois, dans forge.',
    renvois: [r('1.2', 'expliqué')],
    voirAussi: ['jeu-de-donnees'],
  },
  {
    id: 'micro-lot',
    terme: 'micro-lot',
    anglais: 'micro-batch',
    definition:
      "La part d'un lot que la carte traite d'un coup, quand le lot entier ne tient pas dans sa mémoire. Les gradients des micro-lots s'additionnent jusqu'à faire celui du lot : c'est l'accumulation de gradient.",
    renvois: [r('0.4', 'vu'), r('1.5', 'expliqué')],
    voirAussi: ['lot', 'gradient'],
  },
  {
    id: 'mlp',
    terme: 'MLP',
    anglais: 'multilayer perceptron',
    definition:
      "Le petit réseau par lequel passe chaque jeton, seul, après l'attention : une matrice élargit son vecteur, une fonction le plie, une autre matrice le ramène à sa taille. Celui de ton IA est un SwiGLU.",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['bloc', 'neurone'],
  },
  {
    id: 'modele-de-langage',
    terme: 'modèle de langage',
    anglais: 'language model',
    definition:
      "Un programme qui donne une probabilité à chaque suite possible d'un texte. Pour écrire, il tire la suite au sort, l'ajoute au texte, et recommence.",
    renvois: [r('1.1', 'expliqué')],
    voirAussi: ['contexte', 'jeton', 'perplexite'],
  },
  {
    id: 'nat',
    terme: 'nat',
    definition:
      "L'unité d'une perte calculée avec ln, le logarithme naturel. Divisée par ln 2, la même perte se compte en bits.",
    renvois: [r('1.6', 'expliqué')],
    voirAussi: ['bits-par-octet', 'perte'],
  },
  {
    id: 'neurone',
    terme: 'neurone',
    anglais: 'neuron',
    definition:
      'Un petit calcul : il multiplie chacune de ses entrées par un poids, additionne le tout, ajoute son biais, puis décide. Des neurones rangés en couches forment un réseau.',
    renvois: [r('0.5', 'expliqué')],
    voirAussi: ['biais', 'sigmoide', 'parametre'],
  },
  {
    id: 'notebook',
    terme: 'notebook',
    definition:
      "Un cahier de code qui s'ouvre dans Colab, le service de Google qui fait tourner Python dans ton navigateur. Les chapitres en ont un, pour refaire leurs calculs sans rien installer.",
    renvois: [r('0.1', 'présenté')],
  },
  {
    id: 'optimiseur',
    terme: 'optimiseur',
    anglais: 'optimizer',
    definition:
      "La recette qui corrige les poids à chaque pas, d'après leur gradient : la descente de gradient en est la plus simple. Celui de ton IA est AdamW.",
    renvois: [r('1.5', 'expliqué')],
    voirAussi: ['adamw', 'descente-de-gradient', 'taux-d-apprentissage'],
  },
  {
    id: 'parametre',
    terme: 'paramètre',
    aussi: 'poids',
    anglais: 'parameter',
    definition:
      "Un des nombres que le modèle règle en apprenant. Les chapitres de la Partie 0 l'appellent un poids, biais compris.",
    renvois: [r('0.2', 'expliqué sous le nom de poids'), r('1.4', 'compté pour ton IA')],
    voirAussi: ['gradient', 'biais', 'sauvegarde'],
  },
  {
    id: 'pas-d-entrainement',
    terme: "pas d'entraînement",
    anglais: 'training step',
    definition:
      "Un tour de la boucle d'entraînement : le modèle lit un lot, mesure son erreur, la remonte jusqu'au gradient, puis corrige ses poids. Un entraînement en enchaîne des milliers.",
    renvois: [r('0.5', 'expliqué'), r('1.5', 'détaillé pour ton IA')],
    voirAussi: ['lot', 'descente-de-gradient', 'retropropagation'],
  },
  {
    id: 'perplexite',
    terme: 'perplexité',
    anglais: 'perplexity',
    definition:
      "L'exponentielle de la perte moyenne sur un texte jamais lu. Elle se lit comme un nombre de choix : le modèle hésite autant que s'il tirait au hasard entre autant de caractères, ou de jetons.",
    renvois: [r('1.1', 'expliquée'), r('1.6', 'mesurée sur ton IA')],
    voirAussi: ['perte', 'bits-par-octet', 'validation'],
  },
  {
    id: 'perte',
    terme: 'perte',
    anglais: 'loss',
    definition:
      "Le nombre qui mesure à quel point le modèle se trompe, en moyenne sur les exemples : pour ton IA, l'entropie croisée. C'est lui que l'entraînement fait baisser.",
    renvois: [r('0.5', 'expliquée')],
    voirAussi: ['entropie-croisee', 'gradient', 'perplexite'],
  },
  {
    id: 'planning-du-taux',
    terme: 'planning du taux',
    anglais: 'learning rate schedule',
    definition:
      "La règle qui donne le taux d'apprentissage de chaque pas, d'après son seul numéro. Celui de ton IA monte pendant l'échauffement, puis redescend en demi-vague de cosinus jusqu'au dernier pas.",
    renvois: [r('1.5', 'expliqué')],
    voirAussi: ['taux-d-apprentissage', 'echauffement'],
  },
  {
    id: 'plongement',
    terme: 'plongement',
    anglais: 'embedding',
    definition:
      "Le vecteur qui représente un jeton à l'entrée du modèle : sa ligne dans une table, tirée au hasard au départ et réglée par l'entraînement. Ton IA se sert de la même table à la sortie, pour noter chaque jeton possible.",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['jeton', 'vecteur', 'transformer'],
  },
  {
    id: 'poids-lies',
    terme: 'poids liés',
    anglais: 'tied weights',
    definition:
      "Une même table qui sert deux fois : à l'entrée, pour donner son vecteur à chaque jeton, et à la sortie, pour noter chaque jeton possible. Ton IA s'épargne ainsi une seconde table et tous ses paramètres.",
    renvois: [r('1.4', 'expliqués')],
    voirAussi: ['plongement', 'logits', 'parametre'],
  },
  {
    id: 'pre-entrainement',
    terme: 'pré-entraînement',
    anglais: 'pretraining',
    definition:
      "Le premier entraînement d'un modèle de langage, sur une grande quantité de textes, où il apprend à prédire le jeton suivant. C'est là que ton IA naît, avant d'apprendre à converser.",
    renvois: [r('1.5', 'expliqué')],
    voirAussi: ['modele-de-langage', 'pas-d-entrainement', 'sauvegarde'],
  },
  {
    id: 'probabilite',
    terme: 'probabilité',
    anglais: 'probability',
    definition:
      'Un nombre entre 0 et 1 qui dit la chance qu\'une chose arrive ; celles de tous les cas possibles font 1 ensemble. Elle dit ce qui arrive en moyenne, pas à chaque fois.',
    renvois: [r('0.2', 'expliquée')],
    voirAussi: ['softmax', 'graine', 'entropie-croisee'],
  },
  {
    id: 'produit-scalaire',
    terme: 'produit scalaire',
    anglais: 'dot product',
    definition:
      "Multiplier deux listes de nombres case par case, puis tout additionner : il en sort un seul nombre. L'essentiel des calculs d'une IA en est fait.",
    renvois: [r('0.2', 'expliqué')],
    voirAussi: ['vecteur', 'matrice', 'attention'],
  },
  {
    id: 'pytorch',
    terme: 'PyTorch',
    definition:
      'La bibliothèque de Python qui range les nombres en tenseurs, les calcule sur le processeur ou la carte graphique, et trouve seule les pentes. Ton IA est écrite avec elle.',
    renvois: [r('0.3', 'installé'), r('0.4', 'manipulé')],
    voirAussi: ['tenseur', 'cuda', 'retropropagation'],
  },
  {
    id: 'qcm',
    terme: 'QCM',
    definition:
      "Un questionnaire à choix multiples. Pour le faire passer à un modèle sans qu'il écrive un mot, on mesure la vraisemblance de chaque réponse écrite à la suite de la question, et il choisit la plus vraisemblable.",
    renvois: [r('1.6', 'expliqué')],
    voirAussi: ['vraisemblance', 'exactitude-normalisee', 'marge-du-hasard', 'contamination'],
  },
  {
    id: 'regle-de-la-chaine',
    terme: 'règle de la chaîne',
    anglais: 'chain rule',
    definition:
      "La pente d'une chaîne d'opérations est le produit des pentes de ses maillons. C'est elle qui donne à une IA la pente de son erreur pour chacun de ses poids.",
    renvois: [r('0.2', 'expliquée'), r('0.5', 'appliquée')],
    voirAussi: ['retropropagation', 'gradient'],
  },
  {
    id: 'retropropagation',
    terme: 'rétropropagation',
    anglais: 'backpropagation',
    definition:
      "Le calcul qui remonte l'erreur du réseau, de la sortie vers l'entrée, pour trouver la pente de chaque poids. Il applique la règle de la chaîne, maillon par maillon.",
    renvois: [r('0.5', 'expliquée')],
    voirAussi: ['gradient', 'regle-de-la-chaine', 'pytorch'],
  },
  {
    id: 'rmsnorm',
    terme: 'RMSNorm',
    anglais: 'root mean square normalization',
    definition:
      'La normalisation de ton IA : elle divise chaque vecteur par la racine de la moyenne de ses carrés, puis multiplie chacun de ses nombres par un poids appris. Après elle, tous les vecteurs ont à peu près la même échelle.',
    renvois: [r('1.4', 'expliquée')],
    voirAussi: ['bloc'],
  },
  {
    id: 'rope',
    terme: 'RoPE',
    anglais: 'rotary position embedding',
    definition:
      "La façon dont ton IA sait où sont les jetons : chaque paire de valeurs d'une requête ou d'une clé tourne d'un angle proportionnel à la position. Le score d'attention dépend alors de l'écart entre deux positions.",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['attention', 'tete-d-attention'],
  },
  {
    id: 'sauvegarde',
    terme: 'sauvegarde',
    anglais: 'checkpoint',
    definition:
      "L'état de l'entraînement écrit sur le disque : les poids, l'optimiseur, le numéro du pas, la position dans les données et l'état du hasard. Elle permet de mettre l'entraînement en pause, puis de le reprendre au même point.",
    renvois: [r('1.5', 'expliquée')],
    voirAussi: ['parametre', 'pre-entrainement', 'graine'],
  },
  {
    id: 'sigmoide',
    terme: 'sigmoïde',
    anglais: 'sigmoid',
    definition:
      'La fonction qui change une somme en un nombre entre 0 et 1, en douceur : 0,5 pour une somme nulle, presque 1 pour une grande somme positive. Contrairement au seuil, elle a une pente partout.',
    renvois: [r('0.5', 'expliquée')],
    voirAussi: ['neurone'],
  },
  {
    id: 'softmax',
    terme: 'softmax',
    definition:
      "Change des scores quelconques en probabilités qui font 1 ensemble. Elle prend l'exponentielle de chaque score, puis divise chacune par la somme de ces exponentielles.",
    renvois: [r('0.2', 'expliquée')],
    voirAussi: ['temperature', 'probabilite', 'attention'],
  },
  {
    id: 'taux-d-apprentissage',
    terme: "taux d'apprentissage",
    anglais: 'learning rate',
    definition:
      "Le réglage qui fixe la longueur de chaque pas de descente. Trop grand, il fait sauter par-dessus le fond, ou s'en éloigner.",
    renvois: [r('0.2', 'expliqué'), r('1.5', 'planifié')],
    voirAussi: ['descente-de-gradient', 'planning-du-taux', 'adamw'],
  },
  {
    id: 'temperature',
    terme: 'température',
    anglais: 'temperature',
    definition:
      'Le réglage qui divise les scores avant softmax. Sous 1, le mot le plus probable sort plus souvent ; au-dessus de 1, le modèle ose des mots moins probables.',
    renvois: [r('0.2', 'expliquée'), r('1.1', 'essayée')],
    voirAussi: ['softmax'],
  },
  {
    id: 'tenseur',
    terme: 'tenseur',
    anglais: 'tensor',
    definition:
      'Un tableau de nombres rangés selon un certain nombre de dimensions : aucune pour un nombre seul, une pour un vecteur, deux pour une matrice. Tout ce que calcule ton IA passe par des tenseurs.',
    renvois: [r('0.4', 'expliqué')],
    voirAussi: ['forme', 'lot', 'bf16'],
  },
  {
    id: 'tete-d-attention',
    terme: "tête d'attention",
    anglais: 'attention head',
    definition:
      'Une des attentions qui travaillent côte à côte dans un bloc, chacune sur sa tranche du vecteur, avec ses propres requêtes, clés et valeurs. Leurs résultats se recollent, puis une dernière matrice les mélange.',
    renvois: [r('1.4', 'expliquée')],
    voirAussi: ['attention'],
  },
  {
    id: 'tokenizer',
    terme: 'tokenizer',
    enFrancais: 'découpeur',
    definition:
      "L'outil qui découpe le texte en jetons numérotés, puis refait le chemin inverse pour afficher la réponse. Celui de ton IA est appris par BPE, sur les octets.",
    renvois: [r('1.3', 'expliqué')],
    voirAussi: ['jeton', 'bpe'],
  },
  {
    id: 'transformer',
    terme: 'transformer',
    definition:
      "L'architecture des grands modèles de langage, décrite en 2017 : des blocs empilés, chacun fait d'une attention et d'un MLP. Ton IA en est un, dans sa forme qui écrit la suite d'un texte, le « décodeur seul ».",
    renvois: [r('1.4', 'expliqué')],
    voirAussi: ['bloc', 'attention', 'mlp'],
  },
  {
    id: 'uv',
    terme: 'uv',
    definition:
      "L'outil qui installe Python et les paquets dont chaque projet a besoin, dans un dossier à part pour chaque projet. Les projets du site se lancent avec lui.",
    renvois: [r('0.1', 'présenté'), r('0.3', 'expliqué')],
    voirAussi: ['pytorch'],
  },
  {
    id: 'validation',
    terme: 'validation',
    definition:
      "Les textes mis de côté, que le modèle ne lit jamais pour apprendre : on le juge dessus. Sur ce qu'il a lu, il pourrait avoir retenu les réponses par cœur.",
    renvois: [r('1.1', 'expliquée'), r('1.2', 'mise de côté pour ton IA')],
    voirAussi: ['perplexite', 'empreinte', 'contamination'],
  },
  {
    id: 'vecteur',
    terme: 'vecteur',
    anglais: 'vector',
    definition:
      "Une liste de nombres, qu'on dessine comme une flèche quand elle en a deux. Dans ton IA, chaque jeton devient un vecteur, bien trop long pour se dessiner.",
    renvois: [r('0.2', 'expliqué')],
    voirAussi: ['produit-scalaire', 'matrice', 'plongement'],
  },
  {
    id: 'vocabulaire',
    terme: 'vocabulaire',
    anglais: 'vocabulary',
    definition:
      'La liste de tous les jetons que connaît un tokenizer, chacun avec son numéro. Chaque fusion du BPE y ajoute un morceau, et les suites de jetons raccourcissent.',
    renvois: [r('1.3', 'expliqué')],
    voirAussi: ['jeton', 'fusion', 'tokenizer'],
  },
  {
    id: 'vraisemblance',
    terme: 'vraisemblance',
    anglais: 'likelihood',
    definition:
      "La chance qu'un modèle donne à un texte déjà écrit, comme une réponse de QCM à la suite de sa question. On la mesure par sa log-vraisemblance.",
    renvois: [r('1.6', 'expliquée')],
    voirAussi: ['log-vraisemblance', 'qcm', 'probabilite'],
  },
];

/** La lettre sous laquelle le glossaire range un terme : sa première lettre, en capitale et sans accent. */
export function lettreDuTerme(terme: string): string {
  return terme.normalize('NFD').replace(/\p{M}/gu, '').charAt(0).toUpperCase();
}
