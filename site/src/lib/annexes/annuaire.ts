// L'annuaire des données, première version : des jeux de données publiés sur Hugging
// Face, en trois groupes (textes en français, code, évaluation), avec leur taille, leur
// licence, leur accès et leur usage par « ton IA ». Seulement les jeux de la recherche du
// plan 5 (docs/superpowers/plans/2026-11-08-forge-ia-v1-p5-partie-1.md, « Recherche faite
// avant ce plan ») ; `stack-edu`, qui n'y avait pas été lu, n'y est pas.
//
// Relevé du 9 novembre 2026. Pour chaque jeu, `source` est la réponse de l'API de Hugging
// Face (`/api/datasets/<dépôt>`) qui donne son accès (`gated` : false, « auto » pour des
// conditions à accepter, « manual » pour un accord) et sa licence (`cardData.license`).
// Les tailles viennent de `sourceTaille`, que la page donne en lien (« taille ») à côté de la
// date, comme `source` (« fiche »). Une taille est annoncée (par une carte, une page ou
// l'API `size` de datasets-server), ou calculée : la somme, à l'API `tree`, des seuls
// fichiers de données d'un dossier (parquet ou zst), sans ses autres fichiers (sommes de
// contrôle, README). Ainsi :
// - FineWeb-2 : « 502.82GB », colonne « Disk size » de sa ligne fra_Latn sur la carte ; sa
//   valeur en Gio vient de la somme de ses fichiers parquet (sources-1-2.ts, chapitre 1.2) ;
// - Wikipédia et github-code-clean : les sommes de leurs fichiers parquet (sources-1-2.ts),
//   relues le même jour ;
// - Common Corpus : sa carte (2 267 302 720 836 jetons, dont 283 227 402 898 de code) ;
// - Lucie : le tableau de sa carte (2 314,862 milliards de jetons, dont 928,618 en français) ;
// - CulturaX : la somme de ses 512 fichiers parquet du dossier fr (sans fr/checksum.sha256) ;
// - OSCAR : la somme de ses 294 fichiers .jsonl.zst du dossier fr_meta (sans
//   fr_meta/checksum.sha256), une taille compressée ;
// - The Stack v2 : sa page (« The total uncompressed size of all files is 67.53TB ») ;
// - HellaSwag, ARC-Challenge et MMMLU : l'API `size` de datasets-server, partie par partie.
// La taille de Croissant n'a pas été relevée : ses fichiers sont trop nombreux pour une
// seule réponse de l'API, et sa carte n'en donne pas.
//
// Ce module n'importe que des modules sans import propre à Vite : un parcours Playwright
// peut le lire.
import { nombre, pourcent } from '../nombres';
import { MELANGE } from '../partie-1/donnees';
import {
  enGio,
  FICHES_DES_SOURCES,
  FINEWEB_2,
  LICENCES,
  LICENCES_DE_GITHUB_CODE,
  TAILLES_DES_SOURCES,
  WIKIPEDIA_EN_4_0,
} from '../partie-1/sources-1-2';

/** Les trois groupes de l'annuaire. */
export type Groupe = 'francais' | 'code' | 'evaluation';

/** L'accès à un jeu : sans formulaire, conditions à accepter, ou accord des auteurs. */
export type Acces = 'libre' | 'conditions' | 'accord';

/** Une licence, ou ce qui en tient lieu : son nom court, et le lien vers son texte. */
export interface LienDeLicence {
  nom: string;
  url: string;
}

/** Ce qu'une note de bas de tableau précise d'une fiche : la cellule qui l'appelle. */
export type Cellule = 'taille' | 'licence' | 'acces';

/** Un jeu de données de l'annuaire. */
export interface Fiche {
  /** Identifiant court, pour les tests et les ancres. */
  id: string;
  /** Le nom affiché. */
  nom: string;
  /** Le dépôt Hugging Face : « HuggingFaceFW/fineweb-2 ». */
  depot: string;
  /** La partie du jeu dont parle la fiche (une langue, une configuration), ou null. */
  partie: string | null;
  groupe: Groupe;
  /** Ce que c'est, en une phrase. */
  description: string;
  /** La page du jeu sur Hugging Face. */
  url: string;
  /** La taille annoncée, dans l'unité de sa source ; null si elle n'a pas été relevée. */
  taille: string | null;
  /** Sous la taille : sa valeur en Gio, ce qu'elle compte. */
  tailleDetails?: readonly string[];
  /** La licence annoncée ; null si la page n'en indique aucune. */
  licence: LienDeLicence | null;
  /** D'autres licences ou conditions annoncées en même temps. */
  autresLicences?: readonly LienDeLicence[];
  /** Ce que couvre la licence, en peu de mots. */
  licencePrecision?: string;
  acces: Acces;
  /** Le chapitre où ton IA s'en sert, ou null si elle ne s'en sert pas. */
  tonIA: string | null;
  /** Sa part dans le mélange de ton IA, pour une source d'entraînement. */
  tonIAPart?: number;
  /** Ce que ton IA en fait, dit avant « en <chapitre> ». */
  tonIAUsage?: string;
  /** Le jour du relevé, AAAA-MM-JJ. */
  releveLe: string;
  /** La réponse de l'API de Hugging Face qui donne la licence et l'accès. */
  source: string;
  /** D'où vient la taille (carte, page ou réponse de l'API), quand elle est donnée. */
  sourceTaille?: string;
  /** Les notes qu'appellent ses cellules, par identifiant de note. */
  appels?: Partial<Record<Cellule, string>>;
}

/** Un morceau du texte d'une note : du texte, ou un lien. */
export type Morceau = string | { texte: string; url: string };

/** Une note de bas de tableau, propre à un groupe. */
export interface Note {
  id: string;
  groupe: Groupe;
  morceaux: readonly Morceau[];
}

/** Un groupe de l'annuaire : son titre et sa phrase d'introduction. */
export interface DescriptionDeGroupe {
  id: Groupe;
  titre: string;
  intro: string;
}

const RELEVE = '2026-11-09';
const HF = 'https://huggingface.co/datasets/';
const API = 'https://huggingface.co/api/datasets/';
const TAILLES = 'https://datasets-server.huggingface.co/size?dataset=';

/** « 4 614 488 286 octets » : une taille en octets, telle que la donne l'API. */
const octets = (n: number) => `${nombre(n)} octets`;
/** Entre un nombre et son unité : une espace insécable, comme le calculateur. */
const INSECABLE = '\u00A0';
/** « soit 4,30 Gio » : la même taille en Gio, avec deux décimales sous 10 Gio, une au-dessus. */
const soitGio = (n: number) => `soit ${nombre(enGio(n), enGio(n) < 10 ? 2 : 1)}${INSECABLE}Gio`;
/** Un lien de licence, d'après les licences relevées pour le chapitre 1.2. */
const licenceDe = (l: { nom: string; source: { url: string } }): LienDeLicence => ({ nom: l.nom, url: l.source.url });

const CROISSANT = 'https://arxiv.org/abs/2402.00786';

// Les tailles relevées hors de sources-1-2.ts (voir l'en-tête).
const COMMON_CORPUS = { jetons: 2267302720836, code: 283227402898 };
const LUCIE = { milliardsDeJetons: 2314.862, francais: 928.618 };
const CULTURAX_FR = 794485956703;
const OSCAR_FR = 183213490696;
const WIKIPEDIA_FR_ARTICLES = 2564646;
const HELLASWAG_VALIDATION = 9338;
const ARC = { lignes: 2585, test: 1169 };
const MMMLU_FR = 14042;

export const GROUPES: readonly DescriptionDeGroupe[] = [
  {
    id: 'francais',
    titre: 'Textes en français',
    intro: `Le gros de ce que lit ton IA : le web en français et Wikipédia font ${pourcent(MELANGE.web_fr + MELANGE.wikipedia_fr)} de son mélange.`,
  },
  {
    id: 'code',
    titre: 'Code',
    intro: `Ton IA lit aussi du Python, pour ${pourcent(MELANGE.code_python)} de son mélange.`,
  },
  {
    id: 'evaluation',
    titre: 'Évaluation',
    intro:
      "Des tests tout prêts, pour mesurer ce que sait un modèle. Ils ne servent jamais à l'entraîner : il les apprendrait par cœur.",
  },
];

/** Les fiches, groupe par groupe ; dans un groupe, les jeux de ton IA d'abord. */
export const ANNUAIRE: readonly Fiche[] = [
  {
    id: 'fineweb-2',
    nom: 'FineWeb-2',
    depot: FICHES_DES_SOURCES.web_fr.depot,
    partie: 'fra_Latn',
    groupe: 'francais',
    description: 'Des pages web de Common Crawl, triées par langue, filtrées et dédoublonnées. Ici, la part en français.',
    url: TAILLES_DES_SOURCES.web_fr.page.url,
    taille: `502,82${INSECABLE}GB`,
    tailleDetails: [
      soitGio(TAILLES_DES_SOURCES.web_fr.octets),
      `${nombre(FINEWEB_2.francais.mots / 1e9, 1)} milliards de mots`,
    ],
    licence: licenceDe(LICENCES.odcBy),
    autresLicences: [licenceDe(LICENCES.commonCrawl)],
    acces: FICHES_DES_SOURCES.web_fr.libre ? 'libre' : 'conditions',
    tonIA: '1.2',
    tonIAPart: MELANGE.web_fr,
    tonIAUsage: 'de son mélange',
    releveLe: RELEVE,
    source: FICHES_DES_SOURCES.web_fr.api.url,
    sourceTaille: FINEWEB_2.source.url,
    appels: { taille: 'fineweb-gb' },
  },
  {
    id: 'wikipedia',
    nom: 'Wikipédia',
    depot: FICHES_DES_SOURCES.wikipedia_fr.depot,
    partie: FICHES_DES_SOURCES.wikipedia_fr.configuration,
    groupe: 'francais',
    description: 'Les articles de Wikipédia en français, dans la seule copie proposée, celle de novembre 2023.',
    url: TAILLES_DES_SOURCES.wikipedia_fr.page.url,
    taille: octets(TAILLES_DES_SOURCES.wikipedia_fr.octets),
    tailleDetails: [
      soitGio(TAILLES_DES_SOURCES.wikipedia_fr.octets),
      `${nombre(WIKIPEDIA_FR_ARTICLES / 1e6, 2)} millions d'articles`,
    ],
    licence: licenceDe(LICENCES.ccBySa3),
    autresLicences: [licenceDe(LICENCES.gfdl)],
    acces: FICHES_DES_SOURCES.wikipedia_fr.libre ? 'libre' : 'conditions',
    tonIA: '1.2',
    tonIAPart: MELANGE.wikipedia_fr,
    tonIAUsage: 'de son mélange',
    releveLe: RELEVE,
    source: FICHES_DES_SOURCES.wikipedia_fr.api.url,
    sourceTaille: TAILLES_DES_SOURCES.wikipedia_fr.api.url,
    appels: { licence: 'wikipedia-licences' },
  },
  {
    id: 'common-corpus',
    nom: 'Common Corpus',
    depot: 'PleIAs/common_corpus',
    partie: null,
    groupe: 'francais',
    description: 'Des textes libres de droits ou sous licence libre, surtout en anglais et en français, code compris.',
    url: `${HF}PleIAs/common_corpus`,
    taille: `${nombre(Math.round(COMMON_CORPUS.jetons / 1e9))} milliards de jetons`,
    tailleDetails: [`dont ${nombre(Math.round(COMMON_CORPUS.code / 1e9))} milliards de code`],
    licence: { nom: 'libres, selon la carte', url: `${HF}PleIAs/common_corpus` },
    licencePrecision: 'usage commercial compris',
    acces: 'libre',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}PleIAs/common_corpus`,
    sourceTaille: `${HF}PleIAs/common_corpus`,
  },
  {
    id: 'croissant',
    nom: 'Croissant',
    depot: 'croissantllm/croissant_dataset',
    partie: null,
    groupe: 'francais',
    description: "Les données d'entraînement de CroissantLLM, un modèle français et anglais.",
    url: `${HF}croissantllm/croissant_dataset`,
    taille: null,
    licence: { nom: 'celle de chaque source', url: CROISSANT },
    acces: 'libre',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}croissantllm/croissant_dataset`,
  },
  {
    id: 'culturax',
    nom: 'CulturaX',
    depot: 'uonlp/CulturaX',
    partie: 'fr',
    groupe: 'francais',
    description: 'Un corpus web en 167 langues, nettoyé et dédoublonné. Ici, la part en français.',
    url: `${HF}uonlp/CulturaX`,
    taille: octets(CULTURAX_FR),
    tailleDetails: [soitGio(CULTURAX_FR)],
    licence: { nom: "celles de mC4 et d'OSCAR", url: `${HF}uonlp/CulturaX` },
    acces: 'conditions',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}uonlp/CulturaX`,
    sourceTaille: `${API}uonlp/CulturaX/tree/main/fr`,
  },
  {
    id: 'lucie',
    nom: 'Lucie',
    depot: 'OpenLLM-France/Lucie-Training-Dataset',
    partie: null,
    groupe: 'francais',
    description: "Les données d'entraînement du modèle Lucie, d'OpenLLM France.",
    url: `${HF}OpenLLM-France/Lucie-Training-Dataset`,
    taille: `${nombre(Math.round(LUCIE.milliardsDeJetons))} milliards de jetons`,
    tailleDetails: [`dont ${nombre(Math.round(LUCIE.francais))} milliards en français`],
    licence: { nom: 'CC BY-NC-SA 4.0', url: 'https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr' },
    licencePrecision: "pas d'usage commercial",
    acces: 'libre',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}OpenLLM-France/Lucie-Training-Dataset`,
    sourceTaille: `${HF}OpenLLM-France/Lucie-Training-Dataset`,
  },
  {
    id: 'oscar-2301',
    nom: 'OSCAR 23.01',
    depot: 'oscar-corpus/OSCAR-2301',
    partie: 'fr_meta',
    groupe: 'francais',
    description: 'Un corpus web en de nombreuses langues, tiré de Common Crawl. Ici, la part en français.',
    url: `${HF}oscar-corpus/OSCAR-2301`,
    taille: octets(OSCAR_FR),
    tailleDetails: [`${soitGio(OSCAR_FR)}, compressés`],
    licence: { nom: 'CC0 1.0', url: 'https://creativecommons.org/publicdomain/zero/1.0/deed.fr' },
    licencePrecision: 'pour les métadonnées seulement',
    acces: 'accord',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}oscar-corpus/OSCAR-2301`,
    sourceTaille: `${API}oscar-corpus/OSCAR-2301/tree/main/fr_meta`,
    appels: { licence: 'oscar', acces: 'oscar' },
  },
  {
    id: 'github-code-clean',
    nom: 'GitHub Code Clean',
    depot: FICHES_DES_SOURCES.code_python.depot,
    partie: null,
    groupe: 'code',
    description:
      'Du code de GitHub, nettoyé : lignes courtes en moyenne, assez de lettres et de chiffres, fichiers générés retirés.',
    url: TAILLES_DES_SOURCES.code_python.page.url,
    taille: octets(TAILLES_DES_SOURCES.code_python.octets),
    tailleDetails: [soitGio(TAILLES_DES_SOURCES.code_python.octets)],
    licence: licenceDe(LICENCES.apache),
    licencePrecision: FICHES_DES_SOURCES.code_python.precision ?? undefined,
    acces: FICHES_DES_SOURCES.code_python.libre ? 'libre' : 'conditions',
    tonIA: '1.2',
    tonIAPart: MELANGE.code_python,
    tonIAUsage: 'le Python sous licence permissive',
    releveLe: RELEVE,
    source: FICHES_DES_SOURCES.code_python.api.url,
    sourceTaille: TAILLES_DES_SOURCES.code_python.api.url,
    appels: { taille: 'github-code-clean', licence: 'github-code-clean' },
  },
  {
    id: 'the-stack-v2',
    nom: 'The Stack v2',
    depot: 'bigcode/the-stack-v2',
    partie: null,
    groupe: 'code',
    description: 'Le grand corpus de code source du projet BigCode, en plus de 600 langages.',
    url: `${HF}bigcode/the-stack-v2`,
    taille: `67,53${INSECABLE}TB`,
    tailleDetails: ['tous les fichiers, décompressés'],
    licence: { nom: 'celle de chaque fichier', url: `${HF}bigcode/the-stack-v2` },
    licencePrecision: "et des conditions d'utilisation",
    acces: 'conditions',
    tonIA: null,
    releveLe: RELEVE,
    source: `${API}bigcode/the-stack-v2`,
    sourceTaille: `${HF}bigcode/the-stack-v2`,
  },
  {
    id: 'french-bench-hellaswag',
    nom: 'FrenchBench HellaSwag',
    depot: 'manu/french_bench_hellaswag',
    partie: null,
    groupe: 'evaluation',
    description: "Un test de FrenchBench, traduit automatiquement : choisir la suite la plus plausible d'un court texte.",
    url: `${HF}manu/french_bench_hellaswag`,
    taille: `${nombre(HELLASWAG_VALIDATION)} lignes`,
    tailleDetails: ['de validation'],
    licence: null,
    acces: 'libre',
    tonIA: '1.6',
    tonIAUsage: "pour l'évaluer",
    releveLe: RELEVE,
    source: `${API}manu/french_bench_hellaswag`,
    sourceTaille: `${TAILLES}manu/french_bench_hellaswag`,
    appels: { licence: 'frenchbench' },
  },
  {
    id: 'french-bench-arc-challenge',
    nom: 'FrenchBench ARC-Challenge',
    depot: 'manu/french_bench_arc_challenge',
    partie: null,
    groupe: 'evaluation',
    description: 'Un test de FrenchBench, traduit automatiquement : des questions de sciences à choix multiples.',
    url: `${HF}manu/french_bench_arc_challenge`,
    taille: `${nombre(ARC.lignes)} lignes`,
    tailleDetails: [`dont ${nombre(ARC.test)} de test`],
    licence: null,
    acces: 'libre',
    tonIA: '1.6',
    tonIAUsage: "pour l'évaluer",
    releveLe: RELEVE,
    source: `${API}manu/french_bench_arc_challenge`,
    sourceTaille: `${TAILLES}manu/french_bench_arc_challenge`,
    appels: { licence: 'frenchbench' },
  },
  {
    id: 'mmmlu',
    nom: 'MMMLU',
    depot: 'openai/MMMLU',
    partie: 'FR_FR',
    groupe: 'evaluation',
    description: 'Les questions à choix multiples de MMLU, traduites par des traducteurs professionnels.',
    url: `${HF}openai/MMMLU`,
    taille: `${nombre(MMMLU_FR)} lignes`,
    tailleDetails: ['en français'],
    licence: licenceDe(LICENCES.mit),
    acces: 'libre',
    tonIA: '1.6',
    tonIAUsage: "pour l'atelier des QCM",
    releveLe: RELEVE,
    source: `${API}openai/MMMLU`,
    sourceTaille: `${TAILLES}openai/MMMLU`,
  },
];

const gioFineweb = nombre(enGio(TAILLES_DES_SOURCES.web_fr.octets), 1);
const codeOctets = TAILLES_DES_SOURCES.code_python.octets;

/** Les notes de bas de tableau, dans l'ordre de la page ; la page les numérote. */
export const NOTES: readonly Note[] = [
  {
    id: 'fineweb-gb',
    groupe: 'francais',
    morceaux: [
      'Les « GB » de la carte de FineWeb-2 sont des Gio, de 2³⁰ octets : ',
      { texte: 'son arbre de fichiers', url: TAILLES_DES_SOURCES.web_fr.api.url },
      ` donne ${octets(TAILLES_DES_SOURCES.web_fr.octets)} pour le français, soit ${gioFineweb}${INSECABLE}Gio.`,
    ],
  },
  {
    id: 'wikipedia-licences',
    groupe: 'francais',
    morceaux: [
      'Les licences annoncées par la page. Wikipédia publie en CC BY-SA 4.0 les modifications faites depuis juin 2023 (',
      { texte: 'billet de Creative Commons', url: WIKIPEDIA_EN_4_0.source.url },
      ') : à notre lecture, la copie de novembre 2023 mêle donc les deux versions.',
    ],
  },
  {
    id: 'oscar',
    groupe: 'francais',
    morceaux: [
      "Ses auteurs ont suspendu l'accès à OSCAR : ils n'accordent aucune demande tant que la situation n'est pas éclaircie, dit ",
      { texte: 'sa page', url: `${HF}oscar-corpus/OSCAR-2301` },
      ". CC0 1.0 n'y couvre que les métadonnées et les annotations : le texte vient de Common Crawl, et ses auteurs n'en ont pas les droits.",
    ],
  },
  {
    id: 'github-code-clean',
    groupe: 'code',
    morceaux: [
      'Sa carte ne donne pas de taille : celle-ci vient de ',
      { texte: "l'API de Hugging Face", url: TAILLES_DES_SOURCES.code_python.api.url },
      `, qui compte ${octets(codeOctets)} dans son dossier de données, soit ${nombre(codeOctets / 1e9, 1)}${INSECABLE}GB de 10⁹ octets, ou ${nombre(enGio(codeOctets), 1)}${INSECABLE}Gio. Sa carte annonce Apache-2.0 ; celle de `,
      { texte: 'github-code', url: LICENCES_DE_GITHUB_CODE.source.url },
      ", dont il est tiré, note pour chaque fichier la licence de son dépôt. Ton IA ne garde que le Python sous licence permissive. La carte ne parle pas de dédoublonnage et ne date pas les données.",
    ],
  },
  {
    id: 'frenchbench',
    groupe: 'evaluation',
    morceaux: [
      "Les pages de HellaSwag et d'ARC-Challenge n'indiquent aucune licence, et la carte de HellaSwag n'a pas de texte. FrenchBench vient de l'article de CroissantLLM (",
      { texte: 'arXiv 2402.00786', url: CROISSANT },
      "). Ton IA passe les questions de validation de HellaSwag et celles de test d'ARC-Challenge.",
    ],
  },
];

/** Ce que dit la cellule « Licence » sans lien : le nom de la licence, ou « non indiquée ». */
export function texteLicence(fiche: Fiche): string {
  return fiche.licence?.nom ?? 'non indiquée';
}

/** Ce que dit la cellule « Taille annoncée » : la taille, ou « pas relevée ». */
export function texteTaille(fiche: Fiche): string {
  return fiche.taille ?? 'pas relevée';
}

/** Les mots de l'accès, tels que la page et sa légende les écrivent. */
export const MOTS_DE_L_ACCES: Readonly<Record<Acces, string>> = {
  libre: 'libre',
  conditions: 'conditions à accepter',
  accord: 'accord manuel',
};
