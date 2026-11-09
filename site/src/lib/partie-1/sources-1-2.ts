// Les chiffres de labo du chapitre 1.2, « Les données », avec leurs sources : les tailles des
// trois sources de « ton IA » sur Hugging Face. Chaque lien a été relu le 9 novembre 2026, et
// chaque nombre du chapitre qui ne vient ni des attendus du projet, ni des mesures
// (MESURES_PARTIE_1), ni de forge, est ici, à côté de sa source.
//
// Relevé du 9 novembre 2026, à l'API de Hugging Face (points `tree` du dossier lu, somme du
// champ `size` de ses fichiers parquet) :
// - FineWeb-2, dossier data/fra_Latn/train : 135 fichiers, 539 897 427 722 octets (3,72 Gio
//   par fichier en moyenne) ;
// - Wikipédia, configuration 20231101.fr : 17 fichiers, 4 614 488 286 octets ;
// - github-code-clean, dossier data : 880 fichiers, 313 663 761 086 octets. Le dépôt entier
//   (883 fichiers, avec .gitattributes, README.md et le script de chargement) pèse
//   313 663 770 241 octets : le dossier lu est celui de `data`.
// Hugging Face écrit ces tailles en GB décimaux (539,9 GB, 4,61 GB, 313,7 GB) ; le site écrit
// les siennes en Gio (2³⁰ octets), comme les annexes : le chapitre le dit une fois.
//
// Le dossier lu pour le code compte aussi les fichiers qu'on écarte : le Python permissif ne
// fait que 4,1 % des fichiers et 3,9 % des octets de code, mesuré le 3 novembre 2026 sur 7
// fichiers parquet répartis dans tout le jeu (docs/donnees.md).
//
// Ce module n'importe rien (ni .json, ni astro:*) : un parcours Playwright peut l'importer.

/** Une source relue : son titre, son adresse et la date de la vérification (AAAA-MM-JJ). */
export interface SourceVerifiee {
  titre: string;
  url: string;
  verifieLe: string;
}

const VERIFIE = '2026-11-09';

/** Les octets d'un Gio : 2³⁰, l'unité du site pour les tailles. */
export const OCTETS_PAR_GIO = 1073741824;

/** Une taille en Gio (2³⁰ octets), pas arrondie. */
export function enGio(octets: number): number {
  return octets / OCTETS_PAR_GIO;
}

function source(titre: string, url: string, verifieLe: string = VERIFIE): SourceVerifiee {
  return Object.freeze({ titre, url, verifieLe });
}

/** La taille du dossier que lit « ton IA » dans une source, et d'où vient le chiffre. */
export interface TailleDeSource {
  /** Les fichiers parquet du dossier lu. */
  fichiers: number;
  /** Leur taille en octets, somme du champ `size` de l'API de Hugging Face. */
  octets: number;
  /** La page du jeu sur Hugging Face. */
  page: SourceVerifiee;
  /** La réponse de l'API qui donne la liste des fichiers du dossier et leur taille. */
  api: SourceVerifiee;
}

/** Les tailles des trois sources, dans l'ordre du mélange (web_fr, wikipedia_fr, code_python). */
export const TAILLES_DES_SOURCES = Object.freeze({
  web_fr: Object.freeze<TailleDeSource>({
    fichiers: 135,
    octets: 539897427722,
    page: source('Hugging Face, HuggingFaceFW/fineweb-2', 'https://huggingface.co/datasets/HuggingFaceFW/fineweb-2'),
    api: source(
      'API de Hugging Face, fichiers de FineWeb-2 (dossier data/fra_Latn/train)',
      'https://huggingface.co/api/datasets/HuggingFaceFW/fineweb-2/tree/main/data/fra_Latn/train',
    ),
  }),
  wikipedia_fr: Object.freeze<TailleDeSource>({
    fichiers: 17,
    octets: 4614488286,
    page: source('Hugging Face, wikimedia/wikipedia', 'https://huggingface.co/datasets/wikimedia/wikipedia'),
    api: source(
      'API de Hugging Face, fichiers de Wikipédia (configuration 20231101.fr)',
      'https://huggingface.co/api/datasets/wikimedia/wikipedia/tree/main/20231101.fr',
    ),
  }),
  code_python: Object.freeze<TailleDeSource>({
    fichiers: 880,
    octets: 313663761086,
    page: source('Hugging Face, codeparrot/github-code-clean', 'https://huggingface.co/datasets/codeparrot/github-code-clean'),
    api: source(
      'API de Hugging Face, fichiers de github-code-clean (dossier data)',
      'https://huggingface.co/api/datasets/codeparrot/github-code-clean/tree/main/data',
    ),
  }),
});

/** La part du Python permissif dans github-code-clean : un chiffre du projet, mesuré le 3 novembre 2026. */
export const PART_PYTHON_PERMISSIF = Object.freeze({
  /** Part des fichiers (4,1 %). */
  fichiers: 0.041,
  /** Part des octets de code (3,9 %). */
  octets: 0.039,
  /** Combien de fichiers parquet répartis dans le jeu ont servi à la mesure. */
  fichiersMesures: 7,
  mesureLe: '2026-11-03',
  source: source(
    'docs/donnees.md, « Combien il faut lire »',
    'https://github.com/chipat-neko/forge-ia/blob/main/docs/donnees.md',
    '2026-11-03',
  ),
});

/** Les sources que cite le chapitre, par fait. Le chapitre les cite toutes, chacune près de son fait. */
export const SOURCES_1_2 = Object.freeze({
  /** Les tailles des trois dossiers lus. */
  tailles: Object.freeze([
    TAILLES_DES_SOURCES.web_fr.api,
    TAILLES_DES_SOURCES.wikipedia_fr.api,
    TAILLES_DES_SOURCES.code_python.api,
  ]),
  /** Les licences des trois sources. */
  licences: Object.freeze([
    source('Open Data Commons, ODC-By 1.0', 'https://opendatacommons.org/licenses/by/1-0/'),
    source('Creative Commons, CC BY-SA 3.0', 'https://creativecommons.org/licenses/by-sa/3.0/deed.fr'),
    source('Apache Software Foundation, Apache License 2.0', 'https://www.apache.org/licenses/LICENSE-2.0'),
  ]),
});
