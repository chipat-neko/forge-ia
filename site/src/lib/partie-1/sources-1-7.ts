// Les chiffres et les faits sourcés du chapitre 1.7, « Apprendre à converser » : l'encadré « Et chez un
// grand labo ? » (étape 9), ce qu'on peut attendre d'un affinage (étape 8) et les sources des conversations
// (étape 5). Chacun a l'adresse de sa source, l'endroit où il s'y lit, la date de la lecture et l'étiquette de
// la recherche du 17/11/2026 (docs/superpowers/recherche/2026-11-17-vague-2-echelle.md, partie B1) :
// **publié** (donné par les auteurs), **dérivé** (un calcul fait ici, sur des chiffres publiés, écrit à côté) ou
// **tiers** (lu ailleurs qu'à la source primaire).
//
// Tous ont été relus à la source le 18 novembre 2026, dans le texte des pages :
//
// - InstructGPT (Ouyang et al., arXiv 2203.02155, version HTML v1) : section 3.2, « The SFT dataset contains
//   about 13k training prompts (from the API and labeler-written) » (tableau 6 : 11 295 écrites par les
//   étiqueteurs et 1 430 venues de l'API) ; section 3.5, « We trained for 16 epochs » ; section 5.1, « training
//   our 175B SFT model requires 4.9 petaflops/s-days […] compared to 3,640 petaflops/s-days for GPT-3 » (le modèle de
//   175 milliards de paramètres) ;
// - Llama 2 (Touvron et al., arXiv 2307.09288, version HTML v2) : section 3.1, « Quality Is All You Need » :
//   « We stopped annotating SFT after collecting a total of 27,540 annotations », après avoir mis de côté
//   « millions of examples from third-party datasets » ; « Fine-Tuning Details » : « a sequence length of 4096
//   tokens », « we concatenate all the prompts and answers from the training set », « zero-out the loss on
//   tokens from the user prompt, so as a result, we backpropagate only on answer tokens », « we fine-tune the
//   model for 2 epochs » ;
// - Tülu 3 (Lambert et al., arXiv 2411.15124, version HTML v5) : tableau 7, colonne « # Prompts used in SFT »,
//   total 939,344 ; section 4.3, « The final 8B model is trained on 32 GPUs for 6 hours » (des H100 : « between
//   4 and 16 8xH100 nodes »), « a maximum sequence length of 4,096 tokens », « We trained for two epochs » ;
// - SmolLM3 (billet de Hugging Face du 8 juillet 2025) : « 3B model trained on 11T tokens » ; section
//   « Supervised Finetuning » : « The resulting SFT dataset contains 1.8B tokens: 1B in non-reasoning mode and
//   0.8B in reasoning mode », « We trained for 4 epochs (~8B tokens) using BFD (best-fit decreasing) packing
//   with the loss masked on user turns and the results from tool calls » ;
// - nanochat (Karpathy, discussion GitHub n° 1, 13 octobre 2025), le modèle d20 : « Number of parameters:
//   560,988,160 » ; la fiche finale (« Report card ») : ARC-Challenge 0.2875 après la phase intermédiaire
//   (MID), 0.2807 après l'affinage (SFT) ; « This again only runs for about 7 minutes » ;
// - la fiche de kurakurai/Luth-2-Post-Training-SFT : « license: cc-by-4.0 » ; section « Provenance » : « Prompts
//   were translated to French where the source was English, and assistant turns were regenerated with a strong
//   open-source teacher rather than translated » ; encadré « IMPORTANT » : « StackOverflow-derived rows from
//   Nemotron remain CC-BY-SA-4.0 » ;
// - la fiche de CohereLabs/aya_dataset : « license: apache-2.0 », « 204k human-annotated prompt-completion
//   pairs », « This dataset can be used for any purpose, whether academic or commercial » ;
// - la fiche d'OpenAssistant/oasst2 : « license: apache-2.0 » ; « This version of the dataset contains data
//   collected on the open-assistant.io website until Nov 5 2023 » ;
// - la licence de Llama 3.3, section 1.b.i : « If you use the Llama Materials or any outputs or results of the
//   Llama Materials to create, train, fine tune, or otherwise improve an AI model, which is distributed or made
//   available, you shall also include "Llama" at the beginning of any such AI model name » ;
// - les conditions d'utilisation d'OpenAI du 11 décembre 2024, « What you cannot do » : « Use Output to develop
//   models that compete with OpenAI ». La page d'OpenAI refuse les lecteurs automatiques (403) : elles ont été
//   lues dans une copie (Wind River), d'où l'étiquette tiers.
//
// La fiche du plan écrivait « environ 13 000 invites de SFT » pour InstructGPT : l'article dit « about 13k ».
// Le chapitre dit « environ 13 000 ». Les 192 heures de cartes de Tülu 3 sont dérivées : 32 cartes × 6 heures.
//
// Ce module n'importe que des types : l'atelier, dans le navigateur, et les parcours Playwright peuvent l'importer.

import type { SourceVerifiee } from './sources-1-2';

/** La date de la lecture de toutes les sources du chapitre 1.7. */
export const LU_LE_1_7 = '2026-11-18';

/** Les étiquettes de la recherche : publié par les auteurs, dérivé ici d'un calcul écrit, ou lu chez un tiers. */
export const ETIQUETTES = Object.freeze(['publié', 'dérivé', 'tiers'] as const);
export type Etiquette = (typeof ETIQUETTES)[number];

/** Une source lue : son titre et son adresse. */
export interface SourceLue {
  titre: string;
  url: string;
}

/** Un chiffre (ou un fait) sourcé : sa valeur, l'adresse de la source, l'endroit où il s'y lit, la date de lecture, son étiquette. */
export interface ChiffreSource<T = number> {
  valeur: T;
  url: string;
  endroit: string;
  lu_le: string;
  etiquette: Etiquette;
}

function source(titre: string, url: string): SourceLue {
  return Object.freeze({ titre, url });
}

function chiffre<T>(valeur: T, s: SourceLue, endroit: string, etiquette: Etiquette = 'publié'): ChiffreSource<T> {
  return Object.freeze({ valeur, url: s.url, endroit, lu_le: LU_LE_1_7, etiquette });
}

// ---------- Les sources ----------

export const ARTICLE_INSTRUCTGPT = source(
  'Ouyang et al., « Training language models to follow instructions with human feedback » (InstructGPT), arXiv 2203.02155',
  'https://arxiv.org/abs/2203.02155',
);
export const ARTICLE_LLAMA_2 = source(
  'Touvron et al., « Llama 2: Open Foundation and Fine-Tuned Chat Models », arXiv 2307.09288',
  'https://arxiv.org/abs/2307.09288',
);
export const ARTICLE_TULU_3 = source(
  'Lambert et al., « Tülu 3: Pushing Frontiers in Open Language Model Post-Training », arXiv 2411.15124',
  'https://arxiv.org/abs/2411.15124',
);
export const BILLET_SMOLLM3 = source('Hugging Face, « SmolLM3: smol, multilingual, long-context reasoner »', 'https://huggingface.co/blog/smollm3');
export const DISCUSSION_NANOCHAT = source(
  'Karpathy, « Introducing nanochat: The best ChatGPT that $100 can buy », discussion GitHub n° 1',
  'https://github.com/karpathy/nanochat/discussions/1',
);
export const FICHE_LUTH_2 = source(
  'kurakurai/Luth-2-Post-Training-SFT, sur Hugging Face',
  'https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-SFT',
);
export const FICHE_AYA = source('CohereLabs/aya_dataset, sur Hugging Face', 'https://huggingface.co/datasets/CohereLabs/aya_dataset');
export const FICHE_OASST2 = source('OpenAssistant/oasst2, sur Hugging Face', 'https://huggingface.co/datasets/OpenAssistant/oasst2');
export const LICENCE_LLAMA_33 = source('Meta, licence de Llama 3.3 (Llama 3.3 Community License Agreement)', 'https://www.llama.com/llama3_3/license/');
export const COPIE_CONDITIONS_OPENAI = source(
  'OpenAI, conditions d’utilisation du 11 décembre 2024 (copie de Wind River)',
  'https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html',
);

// ---------- Les chiffres de l'encadré (étape 9) ----------

/** InstructGPT (OpenAI, 2022) : l'affinage supervisé de GPT-3, avec des réponses écrites par des étiqueteurs. */
export const INSTRUCTGPT = Object.freeze({
  /** La taille de son plus grand modèle, celui dont l'affinage est chiffré : 175 milliards de paramètres. */
  parametres: chiffre(175e9, ARTICLE_INSTRUCTGPT, 'section 5.1 (« our 175B SFT model »)'),
  /** Les invites de son jeu d'affinage supervisé : « about 13k ». */
  invitesSft: chiffre(13_000, ARTICLE_INSTRUCTGPT, 'section 3.2 (« about 13k training prompts ») ; tableau 6 : 11 295 + 1 430'),
  /** Le calcul de l'affinage du modèle de 175 milliards de paramètres, en pétaflops/s-jours. */
  petaflopsSft: chiffre(4.9, ARTICLE_INSTRUCTGPT, 'section 5.1 (« our 175B SFT model requires 4.9 petaflops/s-days »)'),
  /** Celui du pré-entraînement de GPT-3. */
  petaflopsGpt3: chiffre(3_640, ARTICLE_INSTRUCTGPT, 'section 5.1 (« compared to 3,640 petaflops/s-days for GPT-3 »)'),
  /** Les époques de l'affinage. */
  epoques: chiffre(16, ARTICLE_INSTRUCTGPT, 'section 3.5, « Supervised fine-tuning (SFT) » (« We trained for 16 epochs »)'),
});

/** Llama 2 (Meta, 2023) : des dizaines de milliers d'exemples écrits à la main, et la perte sur les seules réponses. */
export const LLAMA_2 = Object.freeze({
  annotationsSft: chiffre(27_540, ARTICLE_LLAMA_2, 'section 3.1, « Quality Is All You Need » (« a total of 27,540 annotations »)'),
  longueur: chiffre(4096, ARTICLE_LLAMA_2, 'section 3.1, « Fine-Tuning Details » (« a sequence length of 4096 tokens »)'),
  epoques: chiffre(2, ARTICLE_LLAMA_2, 'section 3.1, « Fine-Tuning Details » (« for 2 epochs »)'),
  /** Les questions et les réponses mises bout à bout, et la perte sur les réponses seulement. */
  perteSurLesReponses: chiffre(
    true,
    ARTICLE_LLAMA_2,
    'section 3.1, « Fine-Tuning Details » (« zero-out the loss on tokens from the user prompt », « we concatenate all the prompts and answers »)',
  ),
});

/** Tülu 3 (Ai2, 2024) : un affinage ouvert, données et code publiés. */
export const TULU_3 = Object.freeze({
  invitesSft: chiffre(939_344, ARTICLE_TULU_3, 'tableau 7, colonne « # Prompts used in SFT », total'),
  parametres8B: chiffre(8e9, ARTICLE_TULU_3, 'section 4.3, « Training Settings » (« The final 8B model »)'),
  cartes8B: chiffre(32, ARTICLE_TULU_3, 'section 4.3, « Training Settings » (« The final 8B model is trained on 32 GPUs for 6 hours », des H100)'),
  heures8B: chiffre(6, ARTICLE_TULU_3, 'section 4.3, « Training Settings » (« 32 GPUs for 6 hours »)'),
  /** Dérivé : 32 cartes pendant 6 heures. */
  heuresDeCartes8B: chiffre(192, ARTICLE_TULU_3, 'section 4.3 : 32 cartes × 6 heures, calcul fait ici', 'dérivé'),
  longueur: chiffre(4096, ARTICLE_TULU_3, 'section 4.3, « Training Settings » (« a maximum sequence length of 4,096 tokens »)'),
  epoques: chiffre(2, ARTICLE_TULU_3, 'section 4.3, « Training Settings » (« We trained for two epochs »)'),
});

/** SmolLM3 (Hugging Face, 2025) : 3 milliards de paramètres, et les mêmes outils que ton IA, BFD et le masque. */
export const SMOLLM3 = Object.freeze({
  parametres: chiffre(3e9, BILLET_SMOLLM3, 'résumé du modèle (« 3B model trained on 11T tokens »)'),
  jetonsSft: chiffre(1.8e9, BILLET_SMOLLM3, 'section « Supervised Finetuning » (« The resulting SFT dataset contains 1.8B tokens »)'),
  jetonsRaisonnement: chiffre(0.8e9, BILLET_SMOLLM3, 'section « Supervised Finetuning » (« 0.8B in reasoning mode »)'),
  epoques: chiffre(4, BILLET_SMOLLM3, 'section « Supervised Finetuning » (« We trained for 4 epochs (~8B tokens) »)'),
  bfd: chiffre(true, BILLET_SMOLLM3, 'section « Supervised Finetuning » (« using BFD (best-fit decreasing) packing »)'),
  perteMasquee: chiffre(true, BILLET_SMOLLM3, 'section « Supervised Finetuning » (« with the loss masked on user turns »)'),
});

// ---------- Ce qu'on peut attendre d'un affinage (étape 8) ----------

/** nanochat d20 (Karpathy, 2025) : 561 millions de paramètres, le comparable le plus proche de ton IA. */
export const NANOCHAT_D20 = Object.freeze({
  parametres: chiffre(560_988_160, DISCUSSION_NANOCHAT, 'journal du pré-entraînement (« Number of parameters: 560,988,160 »)'),
  /** ARC-Challenge avant l'affinage (après la phase intermédiaire, qui apprend déjà le format de conversation)… */
  arcAvant: chiffre(0.2875, DISCUSSION_NANOCHAT, 'fiche finale (« Report card »), ARC-Challenge, colonne MID'),
  /** … et après. */
  arcApres: chiffre(0.2807, DISCUSSION_NANOCHAT, 'fiche finale (« Report card »), ARC-Challenge, colonne SFT'),
  minutesSft: chiffre(7, DISCUSSION_NANOCHAT, 'section « Supervised Finetuning (SFT) » (« only runs for about 7 minutes »)'),
});

// ---------- Les sources des conversations (étape 5) ----------

/** Les licences des sources gardées, et les clauses des modèles dont forge écarte les réponses. */
export const DONNEES_1_7 = Object.freeze({
  licenceLuth2: chiffre('CC BY 4.0', FICHE_LUTH_2, 'en-tête de la fiche (« license: cc-by-4.0 »)'),
  /** Les questions traduites en français quand elles étaient anglaises, les réponses réécrites par un modèle. */
  provenanceLuth2: chiffre(
    true,
    FICHE_LUTH_2,
    'section « Provenance » (« Prompts were translated to French […], and assistant turns were regenerated with a strong open-source teacher »)',
  ),
  /** Les lignes de Luth-2 tirées de StackOverflow (par Nemotron) restent sous CC BY-SA 4.0. */
  stackoverflowLuth2: chiffre('CC BY-SA 4.0', FICHE_LUTH_2, 'encadré « IMPORTANT » (« StackOverflow-derived rows from Nemotron remain CC-BY-SA-4.0 »)'),
  /** OASST2 : des arbres de messages écrits sur le site d'Open Assistant, jusqu'au 5 novembre 2023. */
  oasst2Collecte: chiffre('2023-11-05', FICHE_OASST2, 'section « Dataset Structure » (« collected on the open-assistant.io website until Nov 5 2023 »)'),
  licenceAya: chiffre('Apache-2.0', FICHE_AYA, 'en-tête et section « Licensing Information » (« license: apache-2.0 »)'),
  ayaHumain: chiffre(true, FICHE_AYA, 'description (« human-annotated prompt-completion pairs », bénévoles)'),
  licenceOasst2: chiffre('Apache-2.0', FICHE_OASST2, 'en-tête de la fiche (« license: apache-2.0 »)'),
  llama: chiffre(
    'include "Llama" at the beginning of any such AI model name',
    LICENCE_LLAMA_33,
    'section 1.b.i (« any outputs or results of the Llama Materials to create, train, fine tune »)',
  ),
  openai: chiffre('Use Output to develop models that compete with OpenAI', COPIE_CONDITIONS_OPENAI, 'section « What you cannot do »', 'tiers'),
});

function verifiee(s: SourceLue): SourceVerifiee {
  return Object.freeze({ titre: s.titre, url: s.url, verifieLe: LU_LE_1_7 });
}

/** Les sources de l'encadré « Et chez un grand labo ? », dans l'ordre où il les cite. */
export const SOURCES_LABO_1_7: readonly SourceVerifiee[] = Object.freeze(
  [ARTICLE_INSTRUCTGPT, ARTICLE_LLAMA_2, ARTICLE_TULU_3, BILLET_SMOLLM3].map(verifiee),
);

/** Les sources de l'étape des données, dans l'ordre où elle les cite. */
export const SOURCES_DONNEES_1_7: readonly SourceVerifiee[] = Object.freeze(
  [FICHE_LUTH_2, FICHE_AYA, FICHE_OASST2, LICENCE_LLAMA_33, COPIE_CONDITIONS_OPENAI].map(verifiee),
);
