// Les données du calculateur : matériel, prix de location, taux de change,
// électricité, efficacités publiées, formes des modèles publics et sources
// des formules.
//
// Chaque chiffre a sa source primaire : son adresse et la date où on l'a lu
// (`releveLe`). Seules les sources primaires entrent dans un calcul de prix :
// les pages des loueurs eux-mêmes, l'API des prix d'Azure, la BCE et la grille
// d'EDF, jamais un comparateur. Les prix de location changent souvent : la page
// les montre en fourchette, avec leur lien et la date de leur relevé.
//
// Relevés : le 3 novembre 2026 pour le matériel, les prix, le taux, le tarif et
// les formules (recherche du plan 3, prix et pages de NVIDIA revus le 4
// novembre, inchangés) ; le 4 novembre 2026 pour les formes des modèles
// publics, lues dans leurs articles, et pour la bande passante de la B200
// (page du DGX B200).
//
// La grille d'EDF a été relue le 4 novembre 2026 (texte extrait du PDF) :
// « Applicable au 1er aout 2026 », option Base TTC, 20,01 centimes le kWh à
// 3 kVA (abonnement 12,13 € par mois) et à 6 kVA (15,86 €), 19,85 centimes de
// 9 à 36 kVA (puissances « mises en extinction »). Le prix retenu n'a pas
// changé.
//
// Ce module est en TypeScript pur, sans import propre à Vite : les parcours
// Playwright l'importent directement.

import type { Forme } from './formules';

const FINE = '\u202F';

/** Une source primaire : son titre, son adresse et la date du relevé (AAAA-MM-JJ). */
export interface Source {
  titre: string;
  url: string;
  releveLe: string;
  statut: 'primaire';
}

export type Categorie = 'grand-public' | 'colab' | 'centre-de-donnees';

export interface Materiel {
  id: string;
  nom: string;
  categorie: Categorie;
  /** La crête des cœurs tensoriels en bf16, dense (sans sparsité), en TFLOPS. */
  creteTflops: number;
  /** La mémoire d'une carte, en Go. */
  memoireGo: number;
  /** La bande passante de la mémoire, en Go/s décimaux (par carte) ; null si la source ne la donne pas. */
  bandePassanteGoS: number | null;
  /** La puissance maximale d'une carte, en W ; null si la source ne la donne pas. */
  puissanceW: number | null;
  /** Comment le chiffre de crête se lit dans la source, quand ce n'est pas direct. */
  note?: string;
  source: Source;
  /** Les sources d'autres chiffres de la même carte (la mémoire et la bande passante de la B200). */
  autresSources?: readonly Source[];
}

/** Un prix de location, par carte et par heure, hors taxes. */
export interface PrixLocation {
  /** L'identifiant d'un matériel de MATERIELS. */
  materiel: string;
  fournisseur: string;
  offre: string;
  usdParHeure: number;
  source: Source;
}

/** Une efficacité (MFU) publiée, de min à max. */
export interface RepereEfficacite {
  modele: string;
  materiel: string;
  min: number;
  max: number;
  /**
   * Vrai si la source compte l'attention dans les opérations (6N + 12·L·h·s
   * par jeton, PaLM annexe B), faux si elle ne compte que 6N. Le calculateur,
   * lui, compte 6N : pour comparer à ces chiffres, il faut l'efficacité « en
   * comptant l'attention » de ton IA.
   */
  compteAttention: boolean;
  /** Où et comment la source dit compter les opérations. */
  definition: string;
  /** Ce que la phrase de comparaison ajoute après les pourcentages, quand la définition n'est pas celle de la source elle-même ; null sinon. */
  noteCourte: string | null;
  source: Source;
}

export type ModelePublic = Forme & {
  id: string;
  nom: string;
  /** Les jetons de l'entraînement d'origine. */
  jetonsOrigine: number;
  /** Ce qui s'écarte du plan ou ne se lit pas directement dans la source. */
  note?: string;
  source: Source;
  autresSources?: readonly Source[];
};

const RELEVE = '2026-11-03';
const RELEVE_MODELES = '2026-11-04';

function primaire(titre: string, url: string, releveLe = RELEVE): Source {
  return Object.freeze({ titre, url, releveLe, statut: 'primaire' as const });
}

// --- Le matériel ------------------------------------------------------------

const LIVRE_BLANC = 'https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf';

function livreBlanc(tableau: number, carte: string): Source {
  return primaire(`NVIDIA, livre blanc de l’architecture RTX Blackwell (v1.1), tableau ${tableau}${FINE}: ${carte}`, LIVRE_BLANC);
}

/** La note des cartes GeForce : quelle ligne du tableau donne la crête. */
function noteGeForce(dense: string, sparse: string, horloge: string): string {
  return (
    `${dense} TFLOPS${FINE}: ligne «${FINE}Peak BF16 Tensor TFLOPS with FP32 Accumulate${FINE}» du tableau, ` +
    `sans sparsité (${sparse} avec), calculée à l’horloge boost de ${horloge} MHz. ` +
    'Le bf16 n’y existe qu’avec accumulation FP32. Le FP16 avec accumulation FP16 donne le double, ' +
    'mais il ne compte pas pour un entraînement en bf16.'
  );
}

/** Le matériel proposé, relevé le 3 novembre 2026. */
export const MATERIELS: readonly Materiel[] = Object.freeze([
  {
    id: 'rtx-5070-ti',
    nom: 'RTX 5070 Ti',
    categorie: 'grand-public',
    creteTflops: 87.9,
    memoireGo: 16,
    bandePassanteGoS: 896,
    puissanceW: 300,
    note: noteGeForce('87,9', '175,8', `2${FINE}452`),
    source: livreBlanc(5, 'GeForce RTX 5070 Ti'),
  },
  {
    id: 'rtx-5080',
    nom: 'RTX 5080',
    categorie: 'grand-public',
    creteTflops: 112.6,
    memoireGo: 16,
    bandePassanteGoS: 960,
    puissanceW: 360,
    note: noteGeForce('112,6', '225,1', `2${FINE}617`),
    source: livreBlanc(4, 'GeForce RTX 5080'),
  },
  {
    id: 'rtx-5090',
    nom: 'RTX 5090',
    categorie: 'grand-public',
    creteTflops: 209.5,
    memoireGo: 32,
    bandePassanteGoS: 1792,
    puissanceW: 575,
    note: noteGeForce('209,5', '419', `2${FINE}407`),
    source: livreBlanc(3, 'GeForce RTX 5090'),
  },
  {
    id: 'rtx-4090',
    nom: 'RTX 4090',
    categorie: 'grand-public',
    creteTflops: 165.2,
    memoireGo: 24,
    bandePassanteGoS: 1008,
    puissanceW: 450,
    note: noteGeForce('165,2', '330,4', `2${FINE}520`),
    source: livreBlanc(3, 'GeForce RTX 4090'),
  },
  {
    id: 't4',
    nom: 'T4 (Colab gratuit)',
    categorie: 'colab',
    creteTflops: 65,
    memoireGo: 16,
    bandePassanteGoS: 320,
    puissanceW: 70,
    note:
      `Pas de bf16 sur cette carte${FINE}: 65 TFLOPS en FP16 mixte (FP16 et FP32), le seul chiffre des cœurs ` +
      'tensoriels que NVIDIA donne pour elle. La bande passante est annoncée «' +
      `${FINE}320+ GB/s${FINE}».`,
    source: primaire('NVIDIA, page de la T4 (spécifications)', 'https://www.nvidia.com/en-us/data-center/tesla-t4/'),
  },
  {
    id: 'l4',
    nom: 'L4 (Colab)',
    categorie: 'colab',
    creteTflops: 121,
    memoireGo: 24,
    bandePassanteGoS: 300,
    puissanceW: 72,
    note: `242 TFLOPS en bf16 «${FINE}avec sparsité${FINE}» sur la page de NVIDIA, et moitié moins sans, comme elle l’indique.`,
    source: primaire('NVIDIA, page de la L4 (spécifications)', 'https://www.nvidia.com/en-us/data-center/l4/'),
  },
  {
    id: 'a100-80',
    nom: 'A100 80 Go SXM',
    categorie: 'centre-de-donnees',
    creteTflops: 312,
    memoireGo: 80,
    bandePassanteGoS: 2039,
    puissanceW: 400,
    note: '312 TFLOPS en bf16 sans sparsité (624 avec). 400 W en configuration standard, jusqu’à 500 W dans certains serveurs HGX.',
    source: primaire('NVIDIA, page de l’A100 (spécifications, A100 80 Go SXM)', 'https://www.nvidia.com/en-us/data-center/a100/'),
  },
  {
    id: 'h100-sxm',
    nom: 'H100 SXM',
    categorie: 'centre-de-donnees',
    creteTflops: 989,
    memoireGo: 80,
    bandePassanteGoS: 3350,
    puissanceW: 700,
    note: `989 TFLOPS en bf16 sans sparsité${FINE}: la page de NVIDIA affiche 1${FINE}979 TFLOPS «${FINE}avec sparsité${FINE}», divisés par 2.`,
    source: primaire('NVIDIA, page de la H100 (spécifications, H100 SXM)', 'https://www.nvidia.com/en-us/data-center/h100/'),
  },
  {
    id: 'h200',
    nom: 'H200 SXM',
    categorie: 'centre-de-donnees',
    creteTflops: 989,
    memoireGo: 141,
    bandePassanteGoS: 4800,
    puissanceW: 700,
    note:
      `989 TFLOPS en bf16 sans sparsité${FINE}: la page de NVIDIA affiche 1${FINE}979 TFLOPS «${FINE}avec sparsité${FINE}», ` +
      'divisés par 2. NVIDIA dit ses spécifications préliminaires.',
    source: primaire('NVIDIA, page de la H200 (spécifications, H200 SXM)', 'https://www.nvidia.com/en-us/data-center/h200/'),
  },
  {
    id: 'b200',
    nom: 'B200',
    categorie: 'centre-de-donnees',
    creteTflops: 2250,
    memoireGo: 180,
    // Chiffre dérivé : la page du DGX B200 donne « 64 TB/s » pour ses 8 cartes (décision du 4 novembre 2026).
    bandePassanteGoS: 64_000 / 8,
    puissanceW: null,
    note:
      `36 PFLOPS en FP16 et bf16 pour les 8 cartes d’un HGX B200, chiffre «${FINE}en sparse${FINE}» (le dense en vaut la moitié)${FINE}: ` +
      `36${FINE}000 ÷ 8 ÷ 2 = 2${FINE}250 TFLOPS par carte. Mémoire${FINE}: 1${FINE}440 Go pour les 8 cartes d’un DGX B200, soit 180 Go. ` +
      `Bande passante${FINE}: «${FINE}64 TB/s${FINE}» de HBM3e pour les mêmes 8 cartes, soit 8${FINE}000 Go/s par carte, ` +
      `un chiffre dérivé (divisé par 8), pas lu tel quel. Pas de puissance par carte${FINE}: NVIDIA ne donne que celle du système entier.`,
    source: primaire('NVIDIA, page des HGX (spécifications du HGX B200)', 'https://www.nvidia.com/en-us/data-center/hgx/'),
    autresSources: Object.freeze([
      primaire(
        `NVIDIA, page du DGX B200 (spécifications${FINE}: mémoire totale et bande passante HBM3e)`,
        'https://www.nvidia.com/en-us/data-center/dgx-b200/',
        '2026-11-04',
      ),
    ]),
  },
] satisfies Materiel[]);

/** Le matériel d'identifiant `id`. */
export function materiel(id: string): Materiel {
  const m = MATERIELS.find((x) => x.id === id);
  if (m === undefined) {
    throw new RangeError(`Matériel inconnu${FINE}: ${id}. Les identifiants sont ${MATERIELS.map((x) => x.id).join(', ')}.`);
  }
  return m;
}

// --- Les prix de location ---------------------------------------------------

const RUNPOD = primaire(
  `RunPod, page des prix (mise à jour du 28 octobre 2026), prix «${FINE}Community${FINE}» et «${FINE}Secure${FINE}» par carte et par heure`,
  'https://www.runpod.io/pricing',
);
const LAMBDA = primaire('Lambda, page des prix des instances, par carte et par heure, hors taxes', 'https://lambda.ai/pricing');
const AZURE = primaire(
  'Microsoft, API des prix de détail d’Azure (Standard_ND96isr_H100_v5, East US, à la demande)',
  'https://prices.azure.com/api/retail/prices?$filter=' +
    encodeURIComponent("armSkuName eq 'Standard_ND96isr_H100_v5' and armRegionName eq 'eastus' and priceType eq 'Consumption'"),
);

function runpod(materielId: string, community: number, secure: number): PrixLocation[] {
  return [
    { materiel: materielId, fournisseur: 'RunPod', offre: 'Community Cloud', usdParHeure: community, source: RUNPOD },
    { materiel: materielId, fournisseur: 'RunPod', offre: 'Secure Cloud', usdParHeure: secure, source: RUNPOD },
  ];
}

/** Les prix de location relevés le 3 novembre 2026, par carte et par heure, hors taxes. */
export const PRIX_LOCATION: readonly PrixLocation[] = Object.freeze(
  [
    ...runpod('rtx-4090', 0.34, 0.89),
    ...runpod('rtx-5090', 0.69, 1.19),
    ...runpod('a100-80', 1.39, 1.79),
    ...runpod('h100-sxm', 2.69, 3.99),
    ...runpod('h200', 3.59, 5.29),
    ...runpod('b200', 5.98, 7.99),
    { materiel: 'b200', fournisseur: 'Lambda', offre: 'instance de 8 cartes (HGX B200)', usdParHeure: 6.69, source: LAMBDA },
    { materiel: 'b200', fournisseur: 'Lambda', offre: 'instance d’une carte', usdParHeure: 6.99, source: LAMBDA },
    { materiel: 'h100-sxm', fournisseur: 'Lambda', offre: 'instance de 8 cartes (HGX H100)', usdParHeure: 3.99, source: LAMBDA },
    { materiel: 'h100-sxm', fournisseur: 'Lambda', offre: 'instance d’une carte', usdParHeure: 4.29, source: LAMBDA },
    { materiel: 'a100-80', fournisseur: 'Lambda', offre: 'instance de 8 cartes (HGX A100)', usdParHeure: 2.79, source: LAMBDA },
    {
      materiel: 'h100-sxm',
      fournisseur: 'Azure',
      offre: 'ND96isr H100 v5, 8 cartes à 98,32 $ de l’heure, East US, Linux, à la demande',
      usdParHeure: 98.32 / 8,
      source: AZURE,
    },
  ].map((p) => Object.freeze(p)),
);

/**
 * Les prix d'une carte, rangés du plus bas au plus haut (à égalité, dans
 * l'ordre du relevé), avec le plus bas et le plus haut ; null si aucun prix
 * n'a été relevé pour elle.
 */
export function fourchettePrix(materielId: string): { min: number; max: number; prix: readonly PrixLocation[] } | null {
  // sort est stable : deux prix égaux gardent l'ordre de PRIX_LOCATION.
  const prix = PRIX_LOCATION.filter((p) => p.materiel === materielId).sort((a, b) => a.usdParHeure - b.usdParHeure);
  if (prix.length === 0) return null;
  return { min: prix[0].usdParHeure, max: prix[prix.length - 1].usdParHeure, prix: Object.freeze(prix) };
}

// --- Le taux de change et l'électricité -------------------------------------

/** Le taux de référence de la BCE : 1 euro = 1,1179 dollar, le 3 novembre 2026. */
export const TAUX_DE_CHANGE = Object.freeze({
  usdPourUnEur: 1.1179,
  source: primaire(
    'Banque centrale européenne, taux de change de référence de l’euro du 3 novembre 2026',
    'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
  ),
});

/** Le prix du kWh au Tarif Bleu d'EDF, option Base : 20,01 centimes TTC (3 et 6 kVA). */
export const ELECTRICITE = Object.freeze({
  eurParKwh: 0.2001,
  libelle: 'EDF, Tarif Bleu, option Base, 6 kVA, TTC, applicable au 1er août 2026',
  source: primaire(
    'EDF, grille de prix de l’offre Tarif Bleu, applicable au 1er août 2026',
    'https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille_prix_Tarif_Bleu.pdf',
  ),
});

// --- Les efficacités --------------------------------------------------------

/** L'efficacité proposée au départ, selon la catégorie de la carte. */
export const EFFICACITE_PAR_DEFAUT: Readonly<Record<Categorie, number>> = Object.freeze({
  'grand-public': 0.5,
  colab: 0.4,
  'centre-de-donnees': 0.4,
});

/** Des efficacités (MFU) publiées pour de grands entraînements. */
export const REPERES_EFFICACITE: readonly RepereEfficacite[] = Object.freeze([
  {
    modele: 'PaLM 540B',
    materiel: `6${FINE}144 puces TPU v4`,
    min: 0.462,
    max: 0.462,
    compteAttention: true,
    definition:
      `Annexe B${FINE}: 6N + 12·L·H·Q·T opérations par jeton, l’attention comprise (sans remise pour le masque causal), ` +
      'rapportées à la crête des puces.',
    noteCourte: null,
    source: primaire(
      `Chowdhery et al., «${FINE}PaLM: Scaling Language Modeling with Pathways${FINE}» (arXiv 2204.02311), section 4.1 et tableau 3`,
      'https://arxiv.org/abs/2204.02311',
    ),
  },
  {
    modele: 'Llama 3 405B',
    materiel: `de 8${FINE}192 à 16${FINE}384 H100`,
    min: 0.38,
    max: 0.43,
    compteAttention: true,
    definition:
      `Section 3.3.2${FINE}: l’article définit son efficacité («${FINE}BF16 Model FLOPs Utilization${FINE}») par renvoi à ` +
      `PaLM (Chowdhery et al., 2023), sans donner sa propre formule${FINE}: il compte donc l’attention, comme PaLM.`,
    noteCourte: 'avec la définition de PaLM',
    source: primaire(
      `Llama Team (Meta), «${FINE}The Llama 3 Herd of Models${FINE}» (arXiv 2407.21783), section 3.3.2 et tableau 4`,
      'https://arxiv.org/abs/2407.21783',
    ),
  },
]);

// --- Les modèles publics ----------------------------------------------------

const GPT3 = primaire(
  `Brown et al., «${FINE}Language Models are Few-Shot Learners${FINE}» (arXiv 2005.14165), tableaux 2.1 et D.1, section 2.1`,
  'https://arxiv.org/abs/2005.14165',
  RELEVE_MODELES,
);
const GPT2 = primaire(
  `Radford et al., «${FINE}Language Models are Unsupervised Multitask Learners${FINE}» (GPT-2), section 2.3`,
  'https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf',
  RELEVE_MODELES,
);
const LLAMA3 = primaire(
  `Llama Team (Meta), «${FINE}The Llama 3 Herd of Models${FINE}» (arXiv 2407.21783), tableau 3, sections 1, 3.2 et 3.4`,
  'https://arxiv.org/abs/2407.21783',
  RELEVE_MODELES,
);

const NOTE_PETITS_LLAMA =
  `Environ 15${FINE}000 milliards de jetons${FINE}: l’article ne donne pas le compte exact pour cette taille. Il dit «${FINE}a corpus ` +
  `of about 15T multilingual tokens${FINE}» (section 1) et «${FINE}similar recipes${FINE}» pour 8B et 70B (section 3.4).`;

/** Les modèles publics, formes lues dans leurs articles le 4 novembre 2026. */
export const MODELES_PUBLICS: readonly ModelePublic[] = Object.freeze([
  {
    id: 'gpt-3-175b',
    nom: 'GPT-3 175B',
    parametres: 175e9,
    couches: 96,
    dim: 12_288,
    tetes: 96,
    tetesKv: 96,
    contexte: 2048,
    vocabulaire: 50_257,
    jetonsOrigine: 300e9,
    note:
      `Le vocabulaire de 50${FINE}257 jetons n’est pas écrit dans l’article de GPT-3${FINE}: GPT-3 reprend la tokenisation ` +
      `de GPT-2 (section 2.1), dont l’article donne 50${FINE}257 (section 2.3).`,
    source: GPT3,
    autresSources: Object.freeze([GPT2]),
  },
  {
    id: 'llama-3-8b',
    nom: 'Llama 3 8B',
    parametres: 8e9,
    couches: 32,
    dim: 4096,
    tetes: 32,
    tetesKv: 8,
    contexte: 8192,
    vocabulaire: 128_000,
    jetonsOrigine: 15e12,
    note: NOTE_PETITS_LLAMA,
    source: LLAMA3,
  },
  {
    id: 'llama-3-70b',
    nom: 'Llama 3 70B',
    parametres: 70e9,
    couches: 80,
    dim: 8192,
    tetes: 64,
    tetesKv: 8,
    contexte: 8192,
    vocabulaire: 128_000,
    jetonsOrigine: 15e12,
    note: NOTE_PETITS_LLAMA,
    source: LLAMA3,
  },
  {
    id: 'llama-3-405b',
    nom: 'Llama 3 405B',
    parametres: 405e9,
    couches: 126,
    dim: 16_384,
    tetes: 128,
    tetesKv: 8,
    contexte: 8192,
    vocabulaire: 128_000,
    jetonsOrigine: 15.6e12,
    source: LLAMA3,
  },
] satisfies ModelePublic[]);

/** Le modèle public d'identifiant `id`. */
export function modelePublic(id: string): ModelePublic {
  const m = MODELES_PUBLICS.find((x) => x.id === id);
  if (m === undefined) {
    throw new RangeError(`Modèle public inconnu${FINE}: ${id}. Les identifiants sont ${MODELES_PUBLICS.map((x) => x.id).join(', ')}.`);
  }
  return m;
}

// --- Les sources des formules -----------------------------------------------

export type NomFormule = 'operations' | 'attention' | 'etats' | 'activations' | 'cacheKv' | 'generation' | 'efficacite';

const KIPPLY = 'https://kipp.ly/transformer-inference-arithmetic/';
const PALM_ANNEXE_B = primaire(
  `Chowdhery et al., «${FINE}PaLM: Scaling Language Modeling with Pathways${FINE}» (arXiv 2204.02311), annexe B${FINE}: 6N + 12·L·H·Q·T`,
  'https://arxiv.org/abs/2204.02311',
);

/** Les sources de chaque formule de formules.ts (le nom entre crochets dans ses commentaires). */
export const SOURCES_FORMULES: Readonly<Record<NomFormule, readonly Source[]>> = Object.freeze({
  operations: Object.freeze([
    primaire(`Kaplan et al., «${FINE}Scaling Laws for Neural Language Models${FINE}» (arXiv 2001.08361), section 2.1`, 'https://arxiv.org/abs/2001.08361'),
    primaire(
      `Hoffmann et al., «${FINE}Training Compute-Optimal Large Language Models${FINE}» (Chinchilla, arXiv 2203.15556), tableau 3`,
      'https://arxiv.org/abs/2203.15556',
    ),
  ]),
  attention: Object.freeze([
    PALM_ANNEXE_B,
    primaire('Karpathy, nanoGPT, model.py, fonction estimate_mfu', 'https://github.com/karpathy/nanoGPT/blob/master/model.py'),
  ]),
  etats: Object.freeze([
    primaire(
      `Rajbhandari et al., «${FINE}ZeRO: Memory Optimizations Toward Training Trillion Parameter Models${FINE}» (arXiv 1910.02054), section 3.1`,
      'https://arxiv.org/abs/1910.02054',
    ),
  ]),
  activations: Object.freeze([
    primaire(
      `Korthikanti et al., «${FINE}Reducing Activation Recomputation in Large Transformer Models${FINE}» (arXiv 2205.05198), ` +
        'équations 1 et 5, tableau 2',
      'https://arxiv.org/abs/2205.05198',
    ),
  ]),
  cacheKv: Object.freeze([
    primaire(`kipply, «${FINE}Transformer Inference Arithmetic${FINE}» (30 mars 2022), section kv cache`, KIPPLY),
  ]),
  generation: Object.freeze([
    primaire(`kipply, «${FINE}Transformer Inference Arithmetic${FINE}» (30 mars 2022), section latency calculations`, KIPPLY),
  ]),
  efficacite: Object.freeze([
    primaire(
      `Chowdhery et al., «${FINE}PaLM: Scaling Language Modeling with Pathways${FINE}» (arXiv 2204.02311), section 4.1 et annexe B`,
      'https://arxiv.org/abs/2204.02311',
    ),
  ]),
});
