// Le parcours du site : les parties, les chapitres, leur ordre et leurs liens.
// Les titres sont ceux de la section 4 de la spécification, mot pour mot.
// Ce sont des titres bruts : la typographie française (espaces fines) est
// appliquée à l'affichage, pas ici.
//
// Les autres textes (résumés des chapitres de la Partie 1, présentations des
// parties et des groupes, jalons de « ton IA », savoirs, embranchements des
// Parties 2 et 3 après 1.7 et 1.16, annexes) viennent des maquettes de
// l'accueil et de la page de partie, validées par l'utilisateur le 02/11/2026
// (docs/maquettes/accueil-c.html et partie.html). Bruts eux aussi.

export interface Chapitre {
  /** « partie.rang », par exemple « 1.3 ». */
  numero: string;
  titre: string;
  /** Seule la Partie 1 range ses chapitres en groupes. */
  groupe?: string;
  /** Résumé d'une ligne, sous le titre sur la page de partie. */
  resume?: string;
  /** Une grande étape de « ton IA », dite sous le chapitre sur le plan de l'accueil. */
  jalon?: string;
}

/** Un groupe de chapitres de la Partie 1 (une « étape » de sa page). */
export interface Groupe {
  nom: string;
  /** Sous le nom du groupe, dans la marge du plan de l'accueil. */
  resume: string;
  /** Ce que ton IA y gagne, en tête de l'étape sur la page de partie. */
  gain: string;
  /** Note de marge de l'étape, sur la page de partie. */
  note: string;
}

/** Ce que ton IA saura faire à la fin d'une partie, et le chapitre où elle l'apprend. */
export interface Savoir {
  texte: string;
  chapitre: string;
}

export interface Partie {
  numero: 0 | 1 | 2 | 3;
  titre: string;
  chapitres: Chapitre[];
  /** Sous le titre de la partie, sur le plan de l'accueil. */
  resume: string;
  /** Chapeau de la page de partie ; à défaut, le résumé. */
  chapeau?: string;
  /** Note de marge à côté du titre, sur la page de partie. */
  note?: string;
  /** Chapitre de la Partie 1 après lequel la partie se détache (embranchement). */
  depart?: string;
  /** Les groupes de la Partie 1, dans l'ordre de ses chapitres. */
  groupes?: Groupe[];
  savoirs?: Savoir[];
}

/** Une annexe du site, annoncée sur l'accueil. */
export interface Annexe {
  titre: string;
  resume: string;
}

type Brouillon = Omit<Chapitre, 'numero' | 'groupe'>;

// Chapitres de la Partie 1, par groupe : le groupe est écrit une seule fois.
function groupe(nom: string, depart: number, chapitres: Brouillon[]): Chapitre[] {
  return chapitres.map((chapitre, i) => ({ numero: `1.${depart + i}`, groupe: nom, ...chapitre }));
}

export const PARCOURS: Partie[] = [
  {
    numero: 0,
    titre: 'Les bases',
    resume:
      'Python, les maths utiles, ton poste de travail et un premier réseau de neurones. ' +
      'Si tu les connais déjà, passe directement à la Partie 1.',
    chapitres: [
      { numero: '0.1', titre: "Python pour l'IA" },
      { numero: '0.2', titre: 'Les maths utiles (vecteurs, matrices, dérivées, probabilités)' },
      { numero: '0.3', titre: 'Installer son poste : GPU, CUDA, PyTorch' },
      { numero: '0.4', titre: 'Tenseurs et calcul sur GPU' },
      { numero: '0.5', titre: 'Premier réseau de neurones, à la main puis avec PyTorch' },
    ],
  },
  {
    numero: 1,
    titre: 'Créer son IA de zéro',
    resume:
      'La ligne principale. Une seule IA, la tienne, que tu fais grandir de chapitre en chapitre : ' +
      'elle naît en 1.5, apprend à converser, à raisonner et à coder, puis à voir et à agir.',
    chapeau:
      'La partie principale du site. Tu y fabriques une seule IA, « ton IA », et tu la fais grandir ' +
      'de chapitre en chapitre : elle naît en 1.5 avec le découpeur de 1.3, puis elle apprend à ' +
      'converser, à raisonner, à coder, à voir et à agir.',
    note:
      'Tout se fait pour de vrai, en petit, sur ton PC : une carte graphique de 16 Go suffit. ' +
      'Chaque chapitre montre aussi ce que la même étape demande chez un grand labo.',
    groupes: [
      {
        nom: 'Le cœur : un modèle de langage',
        resume: 'Les données, le découpeur, le transformer, puis le premier entraînement : ton IA naît.',
        gain:
          'Les données, le découpeur, le transformer, puis le premier entraînement : à la fin, ' +
          'ton IA complète un texte, jeton après jeton.',
        note:
          'Ton IA naît en 1.5, avec le découpeur de 1.3. Son entraînement peut durer des heures : ' +
          'il se met en pause et reprend au même point.',
      },
      {
        nom: 'Le rendre utile',
        resume: 'Le même modèle apprend à converser, à préférer les bonnes réponses, à raisonner et à coder.',
        gain: 'Le même modèle apprend à converser, à préférer les bonnes réponses, à raisonner et à coder.',
        note: "Ces quatre chapitres reprennent le même modèle et l'affinent : rien n'est refait de zéro.",
      },
      {
        nom: 'Voir et créer des images',
        resume: "De petits modèles d'images et de vidéo, entraînés de zéro, puis des yeux pour ton IA.",
        gain: "De petits modèles d'images et de vidéo, entraînés de zéro, puis des yeux pour ton IA.",
        note: "Les images et la vidéo ont leurs propres petits modèles. En 1.15, ton IA apprend à s'en servir.",
      },
      {
        nom: 'Agir seul',
        resume: "Des outils, une boucle d'agent, une mémoire : toute la mécanique, essayée sur des tâches simples.",
        gain: "Des outils, une boucle d'agent, une mémoire : toute la mécanique pour agir seule.",
        note:
          'Un modèle entraîné sur un PC ne mènera pas seul un vrai projet. Ces chapitres en construisent ' +
          'toute la mécanique, sur des tâches simples. La version vraiment capable vient avec les Parties 2 et 3.',
      },
      {
        nom: 'Le mettre en service',
        resume: 'Plus rapide, plus léger, et sûr.',
        gain: 'Plus rapide, plus légère, et sûre.',
        note: 'Pour servir le modèle, certains outils demandent WSL2 : son installation est expliquée à ce moment-là.',
      },
    ],
    savoirs: [
      { texte: 'découper un texte en jetons', chapitre: '1.3' },
      { texte: 'compléter un texte', chapitre: '1.5' },
      { texte: 'converser', chapitre: '1.7' },
      { texte: 'préférer les bonnes réponses', chapitre: '1.8' },
      { texte: 'raisonner', chapitre: '1.9' },
      { texte: 'coder', chapitre: '1.10' },
      { texte: 'voir les images', chapitre: '1.15' },
      { texte: "se servir d'outils", chapitre: '1.16' },
      { texte: 'mener seule une tâche simple', chapitre: '1.19' },
    ],
    chapitres: [
      ...groupe('Le cœur : un modèle de langage', 1, [
        {
          titre: "Ce qu'est vraiment un modèle de langage",
          resume: 'Un programme qui prédit le morceau de texte suivant. Tout le reste part de là.',
        },
        {
          titre: 'Les données : où les trouver, les nettoyer, les licences',
          resume: "Choisir des textes qu'on a le droit d'utiliser, puis les préparer pour l'entraînement.",
        },
        {
          titre: 'Le tokenizer (BPE)',
          resume:
            "Une IA ne lit pas des lettres : elle lit des nombres. Tu construis l'outil qui découpe " +
            'le texte en morceaux numérotés.',
        },
        {
          titre: 'Le transformer, pièce par pièce',
          resume: "L'architecture du modèle, montée pièce par pièce, avec l'attention en animation.",
        },
        {
          titre: 'Le pré-entraînement sur ton GPU',
          resume:
            'Le premier entraînement de ton IA. Un tout petit modèle apprend aussi sous tes yeux, dans la page.',
          jalon: 'Ici, ton IA naît.',
        },
        { titre: 'Évaluer son modèle', resume: "Mesurer ce qu'il sait faire, et repérer ce qu'il ne sait pas." },
      ]),
      ...groupe('Le rendre utile', 7, [
        {
          titre: 'Apprendre à converser (instructions, format chat)',
          resume: "Le format d'une conversation, et l'habitude de suivre une consigne.",
          jalon: 'Elle apprend à te répondre.',
        },
        {
          titre: "L'aligner : préférences et récompenses",
          resume: "Lui faire préférer les réponses que l'on juge meilleures.",
        },
        { titre: 'Le faire raisonner', resume: "L'entraîner à écrire ses étapes avant de répondre." },
        { titre: 'Le faire coder', resume: "L'entraîner à écrire du code qui tourne." },
      ]),
      ...groupe('Voir et créer des images', 11, [
        {
          titre: 'Compresser les images (autoencodeur)',
          resume: 'Résumer une image en peu de nombres, puis la reconstruire.',
        },
        {
          titre: 'Générer des images par diffusion',
          resume: 'Partir du bruit et le retirer pas à pas, en animation.',
        },
        { titre: "Guider l'image par le texte", resume: 'Faire dessiner ce que décrit une phrase.' },
        { titre: 'Passer à la vidéo', resume: 'Des images qui se suivent et restent cohérentes.' },
        {
          titre: 'Comprendre les images (vision)',
          resume: 'Brancher ces modèles à ton IA : elle apprend à voir.',
          jalon: 'Elle voit les images.',
        },
      ]),
      ...groupe('Agir seul', 16, [
        {
          titre: 'Les outils (appeler des fonctions)',
          resume: 'Lui apprendre à demander un calcul, une recherche, un fichier.',
        },
        {
          titre: "La boucle d'agent et la mémoire",
          resume: 'Observer, décider, agir, recommencer : la boucle, en animation.',
        },
        { titre: 'Plusieurs agents qui coopèrent', resume: 'Répartir une tâche entre plusieurs agents.' },
        {
          titre: 'Gérer un projet de A à Z en autonomie',
          resume: "Toute la mécanique d'un projet, essayée sur des tâches simples.",
          jalon: 'Elle mène seule une tâche simple.',
        },
      ]),
      ...groupe('Le mettre en service', 20, [
        {
          titre: 'Accélérer, compresser, servir le modèle',
          resume: 'La rendre plus rapide et plus légère, puis la servir depuis ton PC.',
        },
        { titre: 'Sécurité et garde-fous', resume: "Ce qu'elle doit refuser, et comment le vérifier." },
      ]),
    ],
  },
  {
    numero: 2,
    titre: 'Hybride',
    resume: "Partir d'un modèle ouvert et l'affiner sur ta carte de 16 Go.",
    depart: '1.7',
    chapitres: [
      { numero: '2.1', titre: 'Choisir un modèle ouvert' },
      { numero: '2.2', titre: "L'affiner sur 16 Go (LoRA, QLoRA)" },
      { numero: '2.3', titre: "Affiner un générateur d'images" },
      { numero: '2.4', titre: 'La vidéo à partir de modèles ouverts' },
    ],
  },
  {
    numero: 3,
    titre: 'Assemblage',
    resume: "Brancher des modèles existants entre eux, jusqu'à un système qui mène des projets.",
    depart: '1.16',
    chapitres: [
      { numero: '3.1', titre: 'Faire tourner des modèles en local' },
      { numero: '3.2', titre: 'Brancher texte, image et vidéo' },
      { numero: '3.3', titre: 'Agents et outils (MCP…)' },
      { numero: '3.4', titre: 'Un système qui mène des projets seul' },
    ],
  },
];

/** Les annexes de la spécification, dans son ordre. */
export const ANNEXES: Annexe[] = [
  {
    titre: 'Glossaire',
    resume: 'Les mots du parcours, expliqués simplement : jeton, fusion, gradient, attention…',
  },
  {
    titre: 'Annuaire des données, modèles et outils',
    resume: 'Où trouver chaque jeu de données, chaque modèle ouvert et chaque outil, avec sa licence.',
  },
  {
    titre: 'Calculateur de coût',
    resume:
      'Choisis une taille de modèle, une quantité de données et un matériel : il estime la mémoire, ' +
      'la durée et le prix.',
  },
  {
    titre: 'Matériel',
    resume: "Quoi acheter, quoi louer, et ce qu'une carte graphique de 16 Go permet vraiment.",
  },
];

// Tous les chapitres dans l'ordre du parcours, de 0.1 à 3.4.
const TOUS: Chapitre[] = PARCOURS.flatMap((partie) => partie.chapitres);

// La base du site sans barre oblique finale : « /forge-ia », ou « » à la racine.
function base(): string {
  return import.meta.env.BASE_URL.replace(/\/+$/, '');
}

/**
 * Lien d'un chapitre, avec la base du site : « /forge-ia/partie-1/1-3/ ».
 * Une seule barre oblique entre la base et le reste, que la base se termine
 * par une barre ou non.
 */
export function hrefChapitre(numero: string): string {
  const [partie] = numero.split('.');
  return `${base()}/partie-${partie}/${numero.replace('.', '-')}/`;
}

/** Lien de la page d'une partie : « /forge-ia/partie-1/ ». */
export function hrefPartie(numero: number): string {
  return `${base()}/partie-${numero}/`;
}

/** Retrouve un chapitre, sa partie et son rang dans la partie (à partir de 1). */
export function trouverChapitre(numero: string): {
  partie: Partie;
  chapitre: Chapitre;
  rang: number;
  total: number;
} {
  for (const partie of PARCOURS) {
    const i = partie.chapitres.findIndex((c) => c.numero === numero);
    if (i >= 0) {
      return { partie, chapitre: partie.chapitres[i], rang: i + 1, total: partie.chapitres.length };
    }
  }
  throw new Error(`Chapitre inconnu : « ${numero} ».`);
}

/** Chapitres voisins, dans l'ordre de tout le parcours (de 0.1 à 3.4). */
export function voisins(numero: string): { precedent?: Chapitre; suivant?: Chapitre } {
  const i = TOUS.findIndex((c) => c.numero === numero);
  if (i < 0) throw new Error(`Chapitre inconnu : « ${numero} ».`);
  return { precedent: TOUS[i - 1], suivant: TOUS[i + 1] };
}

/** Les chapitres d'un groupe d'une partie, dans l'ordre. */
export function chapitresDuGroupe(partie: Partie, groupe: Groupe): Chapitre[] {
  return partie.chapitres.filter((c) => c.groupe === groupe.nom);
}

/**
 * Titre court, comme dans les maquettes : « Les données » plutôt que
 * « Les données : où les trouver, les nettoyer, les licences », et
 * « Le tokenizer » plutôt que « Le tokenizer (BPE) ».
 */
export function titreCourt(titre: string): string {
  return titre.split(/ : | \(/)[0];
}

/**
 * Où en est la parution d'une série de chapitres : « à venir », « 1 paru sur
 * 6 », « 2 parus sur 6 ».
 */
export function etatParution(parus: number, total: number): string {
  return parus === 0 ? 'à venir' : `${parus} paru${parus > 1 ? 's' : ''} sur ${total}`;
}
