// Les chiffres et les faits de labo du chapitre 1.6, « Évaluer son modèle », chacun avec l'adresse
// de sa source, l'endroit où il s'y lit et la date de la lecture. Tous ont été relus à la source le
// 10 novembre 2026 :
//
// - l'article « The Llama 3 Herd of Models » (arXiv 2407.21783, version HTML v3) :
//   - section 5.1.1, tableau 8 (« Pre-training benchmarks by category ») : sept catégories de bancs,
//     Reading Comprehension (SQuAD V2, QuaC, RACE), Code (HumanEval, MBPP), Commonsense
//     reasoning/understanding (CommonSenseQA, PiQA, SiQA, OpenBookQA, WinoGrande), Math, reasoning,
//     and problem solving (GSM8K, MATH, ARC Challenge, DROP, WorldSense), Adversarial (Adv SQuAD,
//     Dynabench SQuAD, GSM-Plus, PAWS), Long context (QuALITY, many-shot GSM8K) et Aggregate (MMLU,
//     MMLU-Pro, AGIEval, BIG-Bench Hard) ;
//   - section 5.1.1 : des intervalles de confiance à 95 %, « assuming that benchmark scores are
//     Gaussian distributed », CI(S) = 1.96 × √(S × (1 − S) / N) ; « While this assumption is
//     incorrect (e.g., benchmark scores are bounded), preliminary bootstrap experiments suggest CIs
//     (for discrete metrics) are a good approximation » ;
//   - section 5.1.4 : la contamination se mesure par recouvrement de 8-grammes (un exemple est
//     contaminé quand une part de ses jetons appartient à un 8-gramme vu au moins une fois dans le
//     corpus de pré-entraînement) ; tableau 15 : HellaSwag, 85 % contaminé, gain estimé de 14,8
//     (8B), 14,8 (70B) et 14,3 (405B) ;
// - la carte de modèle de Llama 3.1 (MODEL_CARD.md), tableau « Base pretrained models » : MMLU
//   (5 exemples, macro_avg/acc_char) 85.2 pour Llama 3.1 405B, ARC-Challenge (25 exemples, acc_char)
//   96.1 ;
// - l'article de CroissantLLM (arXiv 2402.00786, version HTML v5), qui a créé FrenchBench :
//   section 4.2.2 (« FrenchBench Multiple Choice ») : « These datasets correspond to machine
//   translations made by GPT3.5 of HellaSwag and Arc-C to French », et « Manual verification of the
//   translation quality indicates the translations to be far from perfect » ; section 4.1 : « In
//   English, we evaluate on standard LLM evaluation benchmarks », dont HellaSwag et Arc-C ;
// - les pages de manu/french_bench_hellaswag et manu/french_bench_arc_challenge sur Hugging Face :
//   aucune licence, et « README.md exists but content is empty » ;
// - la page de openai/MMMLU sur Hugging Face : licence « mit » ; « We translated the MMLU’s test set
//   into 14 languages using professional human translators » ; « 57 different categories ».
//
// La fiche du plan ne donnait pas les noms des catégories du tableau 8 : ils sont ceux de l'article.
// Les autres chiffres de la fiche (MMLU 85,2, ARC-Challenge 96,1, les 8-grammes, FrenchBench sans
// licence et traduit automatiquement, MMMLU traduit par des humains) se lisent tels quels.
//
// Ce module n'importe rien d'autre que des modules sans import (ni .json, ni astro:*) : l'atelier,
// dans le navigateur, et les parcours Playwright peuvent l'importer.

import type { SourceVerifiee } from './sources-1-2';
import { ARTICLE_LLAMA_3, CARTE_LLAMA_31 } from './sources-1-5';

// L'article de Llama 3 et la carte de modèle de Llama 3.1, déjà relevés pour le chapitre 1.5.
export { ARTICLE_LLAMA_3, CARTE_LLAMA_31 } from './sources-1-5';

const LU_LE = '2026-11-10';

/** Une source lue : son titre et son adresse. */
interface SourceLue {
  titre: string;
  url: string;
}

/** Un fait relevé dans une source : sa valeur, l'adresse de la source, où il s'y lit, et la date de la lecture. */
export interface Releve<T> {
  valeur: T;
  url: string;
  /** Où le fait se lit dans la source : la section, le tableau, le champ. */
  ou: string;
  /** AAAA-MM-JJ. */
  releveLe: string;
}

function releve<T>(valeur: T, source: SourceLue, ou: string): Releve<T> {
  return Object.freeze({ valeur, url: source.url, ou, releveLe: LU_LE });
}

/** L'article de CroissantLLM, qui a créé FrenchBench. */
export const ARTICLE_CROISSANT: SourceLue = Object.freeze({
  titre: 'Faysse et al., « CroissantLLM: A Truly Bilingual French-English Language Model », arXiv 2402.00786',
  url: 'https://arxiv.org/abs/2402.00786',
});

/** La page de FrenchBench HellaSwag sur Hugging Face. */
export const PAGE_FRENCHBENCH_HELLASWAG: SourceLue = Object.freeze({
  titre: 'manu/french_bench_hellaswag, sur Hugging Face',
  url: 'https://huggingface.co/datasets/manu/french_bench_hellaswag',
});

/** La page de FrenchBench ARC-Challenge sur Hugging Face. */
export const PAGE_FRENCHBENCH_ARC: SourceLue = Object.freeze({
  titre: 'manu/french_bench_arc_challenge, sur Hugging Face',
  url: 'https://huggingface.co/datasets/manu/french_bench_arc_challenge',
});

/** La page de MMMLU sur Hugging Face. */
export const PAGE_MMMLU: SourceLue = Object.freeze({
  titre: 'openai/MMMLU, sur Hugging Face',
  url: 'https://huggingface.co/datasets/openai/MMMLU',
});

/** Une catégorie du tableau 8 de l'article de Llama 3 : son nom dans l'article, en français, et ses bancs. */
export interface CategorieDeBancs {
  anglais: string;
  francais: string;
  bancs: readonly string[];
}

function categorie(anglais: string, francais: string, bancs: string[]): CategorieDeBancs {
  return Object.freeze({ anglais, francais, bancs: Object.freeze(bancs) });
}

/** Comment Meta a évalué Llama 3 avant tout réglage (article, section 5.1). */
export const LLAMA_3_BANCS = Object.freeze({
  /** Les catégories de bancs du tableau 8, dans son ordre. */
  categories: releve<readonly CategorieDeBancs[]>(
    Object.freeze([
      categorie('Reading Comprehension', 'compréhension de lecture', ['SQuAD V2', 'QuaC', 'RACE']),
      categorie('Code', 'code', ['HumanEval', 'MBPP']),
      categorie('Commonsense reasoning/understanding', 'sens commun', ['CommonSenseQA', 'PiQA', 'SiQA', 'OpenBookQA', 'WinoGrande']),
      categorie('Math, reasoning, and problem solving', 'maths et raisonnement', ['GSM8K', 'MATH', 'ARC Challenge', 'DROP', 'WorldSense']),
      categorie('Adversarial', 'questions piégées', ['Adv SQuAD', 'Dynabench SQuAD', 'GSM-Plus', 'PAWS']),
      categorie('Long context', 'contexte long', ['QuALITY', 'many-shot GSM8K']),
      categorie('Aggregate', 'bancs qui en regroupent beaucoup', ['MMLU', 'MMLU-Pro', 'AGIEval', 'BIG-Bench Hard']),
    ]),
    ARTICLE_LLAMA_3,
    'section 5.1.1, tableau 8 (« Pre-training benchmarks by category »)',
  ),
  /** Le 1,96 de leurs intervalles de confiance à 95 % : CI(S) = 1.96 × √(S × (1 − S) / N). */
  z: releve(1.96, ARTICLE_LLAMA_3, 'section 5.1.1 (« CI(S) = 1.96 × √(S × (1 − S) / N) »)'),
  /** La longueur des suites de jetons que la recherche de contamination compare : des 8-grammes. */
  ngramme: releve(8, ARTICLE_LLAMA_3, 'section 5.1.4 (« 8-gram overlap »)'),
  /** La part des questions de HellaSwag comptées comme contaminées, en pour cent. */
  hellaswagContamine: releve(85, ARTICLE_LLAMA_3, 'section 5.1.4, tableau 15 (HellaSwag, colonne « Contam. »)'),
  /** Le gain de score que la contamination de HellaSwag aurait donné au 405B, estimé en points. */
  gainHellaswag405B: releve(14.3, ARTICLE_LLAMA_3, 'section 5.1.4, tableau 15 (HellaSwag, colonne 405B)'),
});

/** Llama 3.1 405B pré-entraîné, avant tout réglage (carte de modèle, « Base pretrained models »). */
export const LLAMA_31_405B_BASE = Object.freeze({
  /** MMLU, en pour cent. */
  mmlu: releve(85.2, CARTE_LLAMA_31, 'Base pretrained models, ligne MMLU (macro_avg/acc_char), colonne Llama 3.1 405B'),
  /** Le nombre d'exemples résolus donnés avant chaque question de MMLU. */
  mmluExemples: releve(5, CARTE_LLAMA_31, 'Base pretrained models, ligne MMLU, colonne « # Shots »'),
  /** ARC-Challenge, en pour cent. */
  arc: releve(96.1, CARTE_LLAMA_31, 'Base pretrained models, ligne ARC-Challenge (acc_char), colonne Llama 3.1 405B'),
  /** Le nombre d'exemples résolus donnés avant chaque question d'ARC-Challenge. */
  arcExemples: releve(25, CARTE_LLAMA_31, 'Base pretrained models, ligne ARC-Challenge, colonne « # Shots »'),
});

/** Une traduction : faite par des personnes, ou par une machine. */
export type Traduction = 'humaine' | 'automatique';

/** FrenchBench, les QCM qui notent ton IA (HellaSwag et ARC-Challenge en français). */
export const FRENCHBENCH = Object.freeze({
  /** La langue où ses questions ont d'abord été écrites. */
  langueDOrigine: releve('anglais', ARTICLE_CROISSANT, 'section 4.1 (« In English, we evaluate on standard LLM evaluation benchmarks », dont HellaSwag et Arc-C)'),
  /** Comment elles sont passées en français. */
  traduction: releve<Traduction>('automatique', ARTICLE_CROISSANT, 'section 4.2.2 (« machine translations made by GPT3.5 of HellaSwag and Arc-C to French »)'),
  /** Le modèle qui les a traduites. */
  traducteur: releve('GPT-3.5', ARTICLE_CROISSANT, 'section 4.2.2 (« made by GPT3.5 »)'),
  /** Ce que l'équipe de CroissantLLM dit de ces traductions, après les avoir vérifiées à la main. */
  jugement: releve('loin d’être parfaites', ARTICLE_CROISSANT, 'section 4.2.2 (« Manual verification of the translation quality indicates the translations to be far from perfect »)'),
  /** La licence que donnent leurs pages : aucune. */
  licence: releve<string | null>(null, PAGE_FRENCHBENCH_HELLASWAG, 'pages des deux jeux : aucune licence, « README.md exists but content is empty »'),
});

/** MMMLU, les QCM de l'atelier (MMLU traduit, configuration FR_FR). */
export const MMMLU = Object.freeze({
  traduction: releve<Traduction>('humaine', PAGE_MMMLU, '« We translated the MMLU’s test set […] using professional human translators »'),
  /** Le nombre de langues de la traduction. */
  langues: releve(14, PAGE_MMMLU, '« into 14 languages »'),
  /** Le nombre de catégories de questions de MMLU. */
  categories: releve(57, PAGE_MMMLU, '« 57 different categories »'),
  licence: releve<string | null>('MIT', PAGE_MMMLU, 'champ License (« mit »)'),
});

/** Les sources de l'encadré « Et chez un grand labo ? », dans l'ordre où il les cite. */
export const SOURCES_LABO_1_6: readonly SourceVerifiee[] = Object.freeze(
  [ARTICLE_LLAMA_3, CARTE_LLAMA_31].map((s) => Object.freeze({ titre: s.titre, url: s.url, verifieLe: LU_LE })),
);

/** Les sources de l'étape « Ce que les chiffres ne disent pas », dans l'ordre où elle les cite. */
export const SOURCES_LIMITES_1_6: readonly SourceVerifiee[] = Object.freeze(
  [ARTICLE_CROISSANT, PAGE_MMMLU, ARTICLE_LLAMA_3].map((s) => Object.freeze({ titre: s.titre, url: s.url, verifieLe: LU_LE })),
);
