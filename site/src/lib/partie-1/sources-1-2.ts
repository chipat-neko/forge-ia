// Les chiffres de labo du chapitre 1.2, « Les données », avec leurs sources : les tailles des
// trois sources de « ton IA » sur Hugging Face, leurs licences et leur accès, FineWeb-2,
// Llama 3 et le règlement européen sur l'IA. Chaque lien a été relu le 9 novembre 2026, et
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

/** Une licence citée par le chapitre : son nom court, et son texte (le lien). */
export interface Licence {
  nom: string;
  source: SourceVerifiee;
}

function licence(nom: string, titre: string, url: string): Licence {
  return Object.freeze({ nom, source: source(titre, url) });
}

/** Les licences que le chapitre décrit, chacune avec le lien vers son texte (relu le 9 novembre 2026). */
export const LICENCES = Object.freeze({
  // Section 2.4 : la licence couvre la base, pas les contenus ; section 3.1 : usage commercial compris ;
  // section 4 : citer la base quand on la diffuse publiquement.
  odcBy: licence('ODC-By 1.0', 'Open Data Commons, ODC-By 1.0', 'https://opendatacommons.org/licenses/by/1-0/'),
  commonCrawl: licence('conditions de Common Crawl', 'Common Crawl, conditions d’utilisation', 'https://commoncrawl.org/terms-of-use'),
  ccBySa3: licence('CC BY-SA 3.0', 'Creative Commons, CC BY-SA 3.0', 'https://creativecommons.org/licenses/by-sa/3.0/deed.fr'),
  ccBySa4: licence('CC BY-SA 4.0', 'Creative Commons, CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/deed.fr'),
  gfdl: licence('GFDL', 'Free Software Foundation, GNU Free Documentation License', 'https://www.gnu.org/licenses/fdl-1.3.html'),
  apache: licence('Apache-2.0', 'Apache Software Foundation, Apache License 2.0', 'https://www.apache.org/licenses/LICENSE-2.0'),
  // Section 5 c : l'œuvre modifiée, transmise, l'est tout entière sous la même licence.
  gpl3: licence('GPL-3.0', 'Free Software Foundation, GNU General Public License v3.0', 'https://www.gnu.org/licenses/gpl-3.0.html'),
  // Garder la mention de l'auteur et la licence dans toute copie.
  mit: licence('MIT', 'SPDX, MIT License', 'https://spdx.org/licenses/MIT.html'),
});

/** Le billet de Creative Commons du 29 juin 2023 : les nouvelles modifications de Wikipédia passent en CC BY-SA 4.0, les anciennes restent en 3.0. */
export const WIKIPEDIA_EN_4_0 = Object.freeze({
  annonceLe: '2023-06-29',
  source: source('Creative Commons, « Wikipedia Moves to CC 4.0 Licenses »', 'https://creativecommons.org/2023/06/29/wikipedia-moves-to-cc-4-0-licenses/'),
});

/**
 * La carte de github-code, dont github-code-clean est tiré : chaque fichier porte la licence
 * du dépôt GitHub d'où il vient (section « Licenses »), parmi 15, dans 30 langages.
 */
export const LICENCES_DE_GITHUB_CODE = Object.freeze({
  licences: 15,
  langages: 30,
  source: source('Hugging Face, carte de codeparrot/github-code', 'https://huggingface.co/datasets/codeparrot/github-code'),
});

/** Ce que le tableau des sources dit de chacune : son nom, son dépôt, ses licences et son accès. */
export interface FicheDeSource {
  /** Le nom affiché. */
  nom: string;
  /** Le dépôt Hugging Face : `depot` de forge.donnees.sources. */
  depot: string;
  /** La partie lue : le dossier ou la configuration de forge.donnees.sources. */
  dossier: string | null;
  configuration: string | null;
  /** Les licences annoncées par le jeu, la première étant `url_licence` de forge. */
  licences: readonly Licence[];
  /** Ce que la licence annoncée couvre, dit en peu de mots, ou null. */
  precision: string | null;
  /** Vrai si le jeu se lit sans formulaire ni accord (`gated: false` de l'API). */
  libre: boolean;
  /** La réponse de l'API qui donne la licence et l'accès (`cardData.license`, `gated`). */
  api: SourceVerifiee;
}

/** Les fiches des trois sources, dans l'ordre du mélange. */
export const FICHES_DES_SOURCES = Object.freeze({
  web_fr: Object.freeze<FicheDeSource>({
    nom: 'FineWeb-2, en français',
    depot: 'HuggingFaceFW/fineweb-2',
    dossier: 'data/fra_Latn/train',
    configuration: null,
    licences: Object.freeze([LICENCES.odcBy, LICENCES.commonCrawl]),
    precision: null,
    libre: true,
    api: source('API de Hugging Face, HuggingFaceFW/fineweb-2', 'https://huggingface.co/api/datasets/HuggingFaceFW/fineweb-2'),
  }),
  wikipedia_fr: Object.freeze<FicheDeSource>({
    nom: 'Wikipédia, en français',
    depot: 'wikimedia/wikipedia',
    dossier: null,
    configuration: '20231101.fr',
    licences: Object.freeze([LICENCES.ccBySa3, LICENCES.gfdl]),
    precision: null,
    libre: true,
    api: source('API de Hugging Face, wikimedia/wikipedia', 'https://huggingface.co/api/datasets/wikimedia/wikipedia'),
  }),
  code_python: Object.freeze<FicheDeSource>({
    nom: 'github-code-clean, du code',
    depot: 'codeparrot/github-code-clean',
    dossier: 'data',
    configuration: null,
    licences: Object.freeze([LICENCES.apache]),
    precision: 'pour la compilation ; chaque fichier garde la sienne',
    libre: true,
    api: source('API de Hugging Face, codeparrot/github-code-clean', 'https://huggingface.co/api/datasets/codeparrot/github-code-clean'),
  }),
});

/**
 * FineWeb-2, d'après sa carte (version 2.1.1 du 27 octobre 2025) : le français seul, et
 * toutes les langues. 96 copies du web de Common Crawl, de l'été 2013 à avril 2024 ; la
 * langue de chaque page repérée, les doublons retirés langue par langue (un document gardé
 * par groupe de copies), puis des filtres de qualité, langue par langue.
 */
export const FINEWEB_2 = Object.freeze({
  francais: Object.freeze({ mots: 220662584640, documents: 360058973 }),
  total: Object.freeze({ mots: 3339271691958, documents: 5018505566 }),
  copiesDuWeb: 96,
  source: source('Hugging Face, carte de HuggingFaceFW/fineweb-2', 'https://huggingface.co/datasets/HuggingFaceFW/fineweb-2'),
});

/**
 * Llama 3, d'après l'article de Meta (arXiv 2407.21783, version 3) : environ 15 000
 * milliards de jetons (« about 15T multilingual tokens », section 1) ; des connaissances
 * jusqu'à la fin de 2023 (section 3.1) ; le mélange final (section 3.1.2) ; trois
 * dédoublonnages, par adresse, par document (MinHash) et par ligne, une ligne étant
 * retirée si elle revient plus de 6 fois dans un paquet de 30 millions de documents
 * (section 3.1.1).
 */
export const LLAMA_3 = Object.freeze({
  jetons: 15e12,
  connaissancesJusqua: 2023,
  melange: Object.freeze({ connaissances: 0.5, mathsEtRaisonnement: 0.25, code: 0.17, multilingue: 0.08 }),
  ligneRepetee: Object.freeze({ fois: 6, documents: 30e6 }),
  source: source('Llama Team, AI @ Meta, « The Llama 3 Herd of Models », arXiv 2407.21783', 'https://arxiv.org/abs/2407.21783'),
});

/**
 * Le règlement (UE) 2024/1689 sur l'IA, dans sa version consolidée du 27 juillet 2026 (EUR-Lex).
 * Article 53, paragraphe 1 : points c) (politique sur le droit d'auteur, réserves de droits
 * de la directive 2019/790) et d) (résumé suffisamment détaillé du contenu d'entraînement).
 * Article 113, point b) : le chapitre V, qui contient l'article 53, s'applique à partir du
 * 2 août 2025. Article 111, paragraphe 3 : un modèle mis sur le marché avant cette date a
 * jusqu'au 2 août 2027. Lu le 9 novembre 2026 ; le règlement 2026/1744, qui a modifié le
 * texte, n'a changé ni l'article 53, ni l'article 113 b), ni l'article 111, paragraphe 3.
 */
export const REGLEMENT_IA = Object.freeze({
  article: 53,
  appliqueDepuis: '2025-08-02',
  modelesAnterieurs: '2027-08-02',
  source: source(
    'EUR-Lex, règlement (UE) 2024/1689, version consolidée du 27 juillet 2026',
    'https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689-20260727',
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
  licences: Object.freeze([LICENCES.odcBy.source, LICENCES.ccBySa3.source, LICENCES.apache.source]),
  /** Les licences et l'accès de chaque source, à l'API. */
  fiches: Object.freeze(Object.values(FICHES_DES_SOURCES).map((f) => f.api)),
  /** L'encadré « chez un grand labo ». */
  labo: Object.freeze([LLAMA_3.source, FINEWEB_2.source, REGLEMENT_IA.source]),
});
