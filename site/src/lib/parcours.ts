// Le parcours du site : les parties, les chapitres, leur ordre et leurs liens.
// Les titres sont ceux de la section 4 de la spécification, mot pour mot.
// Ce sont des titres bruts : la typographie française (espaces fines) est
// appliquée à l'affichage, pas ici.

export interface Chapitre {
  /** « partie.rang », par exemple « 1.3 ». */
  numero: string;
  titre: string;
  /** Seule la Partie 1 range ses chapitres en groupes. */
  groupe?: string;
}

export interface Partie {
  numero: 0 | 1 | 2 | 3;
  titre: string;
  chapitres: Chapitre[];
}

// Chapitres de la Partie 1, par groupe : le groupe est écrit une seule fois.
function groupe(nom: string, depart: number, titres: string[]): Chapitre[] {
  return titres.map((titre, i) => ({ numero: `1.${depart + i}`, titre, groupe: nom }));
}

export const PARCOURS: Partie[] = [
  {
    numero: 0,
    titre: 'Les bases',
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
    chapitres: [
      ...groupe('Le cœur : un modèle de langage', 1, [
        "Ce qu'est vraiment un modèle de langage",
        'Les données : où les trouver, les nettoyer, les licences',
        'Le tokenizer (BPE)',
        'Le transformer, pièce par pièce',
        'Le pré-entraînement sur ton GPU',
        'Évaluer son modèle',
      ]),
      ...groupe('Le rendre utile', 7, [
        'Apprendre à converser (instructions, format chat)',
        "L'aligner : préférences et récompenses",
        'Le faire raisonner',
        'Le faire coder',
      ]),
      ...groupe('Voir et créer des images', 11, [
        'Compresser les images (autoencodeur)',
        'Générer des images par diffusion',
        "Guider l'image par le texte",
        'Passer à la vidéo',
        'Comprendre les images (vision)',
      ]),
      ...groupe('Agir seul', 16, [
        'Les outils (appeler des fonctions)',
        "La boucle d'agent et la mémoire",
        'Plusieurs agents qui coopèrent',
        'Gérer un projet de A à Z en autonomie',
      ]),
      ...groupe('Le mettre en service', 20, [
        'Accélérer, compresser, servir le modèle',
        'Sécurité et garde-fous',
      ]),
    ],
  },
  {
    numero: 2,
    titre: 'Hybride',
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
    chapitres: [
      { numero: '3.1', titre: 'Faire tourner des modèles en local' },
      { numero: '3.2', titre: 'Brancher texte, image et vidéo' },
      { numero: '3.3', titre: 'Agents et outils (MCP…)' },
      { numero: '3.4', titre: 'Un système qui mène des projets seul' },
    ],
  },
];

// Tous les chapitres dans l'ordre du parcours, de 0.1 à 3.4.
const TOUS: Chapitre[] = PARCOURS.flatMap((partie) => partie.chapitres);

/**
 * Lien d'un chapitre, avec la base du site : « /forge-ia/partie-1/1-3/ ».
 * Une seule barre oblique entre la base et le reste, que la base se termine
 * par une barre ou non.
 */
export function hrefChapitre(numero: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/+$/, '');
  const [partie] = numero.split('.');
  return `${base}/partie-${partie}/${numero.replace('.', '-')}/`;
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
