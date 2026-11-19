// Les chiffres et les faits sourcés du chapitre 1.8, « L'aligner : préférences et récompenses » : la perte DPO et son
// piège (étapes 5 et 6), le jeu de préférences écarté pour sa licence (étape 2), et l'encadré « Et chez un grand
// labo ? » (étape 9). Chacun a l'adresse de sa source, l'endroit où il s'y lit, la date de la lecture et son
// étiquette : **publié** (donné par les auteurs), **dérivé** (un calcul fait ici, sur des chiffres publiés, écrit à
// côté) ou **tiers** (lu ailleurs qu'à la source primaire).
//
// Tous ont été relus à la source le 19 novembre 2026, dans le texte des pages (versions HTML d'arXiv) :
//
// - DPO (Rafailov et al., arXiv 2305.18290, v3) : résumé, « allowing us to solve the standard RLHF problem with only a
//   simple classification loss » ; section 1, « without explicit reward modeling or reinforcement learning » ; section
//   3, « where β is a parameter controlling the deviation from the base reference policy π_ref, namely the initial SFT
//   model π_SFT » ; section 4, « What does the DPO update do? » : « the gradient of the loss function ℒ_DPO increases
//   the likelihood of the preferred completions y_w and decreases the likelihood of dispreferred completions y_l » ;
//   « DPO outline » : « Sample completions y1, y2 ∼ π_ref(·|x) for every prompt x, label with human preferences » ;
// - DPOP (Pal et al., « Smaug », arXiv 2402.13228, v2) : résumé, « the standard DPO loss can lead to a reduction of
//   the model's likelihood of the preferred examples, as long as the relative probability between the preferred and
//   dispreferred classes increases », « especially datasets in which the edit distance between pairs of completions
//   is low » ; section 4, « DPOP adds the penalty term max(0, log π_ref(y_w|x)/π_θ(y_w|x)) to the loss within the
//   log-sigmoid to incentivise maintaining a high log-likelihood of the preferred completions » ;
// - InstructGPT (Ouyang et al., arXiv 2203.02155, v1) : section 3.2, « the RM dataset has 33k training prompts (from
//   the API and labeler-written), and the PPO dataset has 31k training prompts (only from the API) » ; section 3.4,
//   « we hired a team of about 40 contractors » ; section 3.5, « Reward modeling (RM) » : « In this paper we only use
//   6B RMs », « we present labelers with anywhere between K = 4 and K = 9 responses to rank » ; section 5.1,
//   « training our 175B PPO-ptx model requires 60 petaflops/s-days, compared to 3,640 petaflops/s-days for GPT-3 » ;
// - Llama 2 (Touvron et al., arXiv 2307.09288, v2) : section 3.2.1, « We chose a binary comparison protocol » ;
//   tableau 6, « Meta (Safety & Helpfulness) 1,418,091 », « Total 2,919,326 » ; section 3.2.2, « we train two separate
//   reward models, one optimized for helpfulness (referred to as Helpfulness RM) and another for safety (Safety RM) » ;
//   section 3.2.3, « RLHF-V1, …, RLHF-V5 », « Rejection Sampling fine-tuning. We sample K outputs from the model and
//   select the best candidate with our reward » ;
// - Qwen2.5 (Qwen Team, arXiv 2412.15115, v2) : section 4.2, « Offline Reinforcement Learning » : « employing the SFT
//   model to resample responses for a new set of queries. Responses that pass our quality checks are used as positive
//   examples, while those that fail are treated as negative examples for Direct Preference Optimization (DPO)
//   training », « we make use of both human and automated review processes », « approximately 150,000 training
//   pairs », « trained for one epoch […] with a learning rate of 7 × 10−7 » ;
// - Tülu 3 (Lambert et al., arXiv 2411.15124, v5) : section 2.3, « Tülu 3 Recipe », « 354,192 instances for preference tuning », « used
//   length-normalized DPO throughout the development process and training our final models » ; section 5.2.1,
//   « Stage 3: Preference Annotation » : « After generating four responses for each prompt, we use an
//   LLM-as-a-judge […], specifically GPT-4o-2024-0806, to rate each response from 1 to 5 » ; tableau 15, total 354,192,
//   colonne 8B 271,409 ; tableau 7, colonne des préférences, total 425,145 (marqué γ : « not all prompts are used in
//   both the 8B and 70B mixes ») ; tableau 20, 8B : « Learning Rate 5 × 10-7 », « KL penalty coefficient β 5 »,
//   « Number of Epochs 1 » ; section 5.4, « The 8B DPO model is trained for 10 hours on 8 Nvidia H100 GPUs » ;
// - la fiche de CATIE-AQ/facebook-community-alignment-dataset_french_dpo : « license: cc-by-4.0 », « num_examples:
//   71525 », « cleaned up to keep only the French datas (+ deduplication) and reformatted for DPO finetuning » ;
// - la fiche de facebook/community-alignment-dataset : « >200,000 comparisons of LLM responses, collected from >3,500
//   unique annotators », licence CC-BY-4.0 ;
// - l'article de Community Alignment (Zhang et al., arXiv 2507.09650, v3), annexe I, « Community Alignment codebook »,
//   variable first_turn_responses : « Candidate responses were generated simultaneously by Llama-3.3-70B-Instruct » ;
// - la licence de Llama 3.3, section 1.b.i : « If you use the Llama Materials or any outputs or results of the Llama
//   Materials to create, train, fine tune, or otherwise improve an AI model, which is distributed or made available,
//   you shall also include "Llama" at the beginning of any such AI model name ».
//
// Deux chiffres sont dérivés, calculés ici sur des chiffres publiés : la part du PPO d'InstructGPT dans le calcul de
// GPT-3 (60 ÷ 3 640), et les 80 heures de carte de la DPO de Tülu 3 8B (8 cartes × 10 heures).
//
// Ce module n'importe que les sources de 1.7 et des types : l'atelier, dans le navigateur, et les parcours Playwright
// peuvent l'importer.

import type { SourceVerifiee } from './sources-1-2';
import { ARTICLE_INSTRUCTGPT, ARTICLE_LLAMA_2, ARTICLE_TULU_3, LICENCE_LLAMA_33, type ChiffreSource, type Etiquette, type SourceLue } from './sources-1-7';

/** La date de la lecture de toutes les sources du chapitre 1.8. */
export const LU_LE_1_8 = '2026-11-19';

function source(titre: string, url: string): SourceLue {
  return Object.freeze({ titre, url });
}

function chiffre<T>(valeur: T, s: SourceLue, endroit: string, etiquette: Etiquette = 'publié'): ChiffreSource<T> {
  return Object.freeze({ valeur, url: s.url, endroit, lu_le: LU_LE_1_8, etiquette });
}

// ---------- Les sources ----------

export const ARTICLE_DPO = source(
  'Rafailov et al., « Direct Preference Optimization: Your Language Model is Secretly a Reward Model », arXiv 2305.18290',
  'https://arxiv.org/abs/2305.18290',
);
export const ARTICLE_DPOP = source(
  'Pal et al., « Smaug: Fixing Failure Modes of Preference Optimisation with DPO-Positive », arXiv 2402.13228',
  'https://arxiv.org/abs/2402.13228',
);
export const ARTICLE_QWEN_25 = source('Qwen Team, « Qwen2.5 Technical Report », arXiv 2412.15115', 'https://arxiv.org/abs/2412.15115');
export const FICHE_COMMUNITY_ALIGNMENT_FR = source(
  'CATIE-AQ/facebook-community-alignment-dataset_french_dpo, sur Hugging Face',
  'https://huggingface.co/datasets/CATIE-AQ/facebook-community-alignment-dataset_french_dpo',
);
export const FICHE_COMMUNITY_ALIGNMENT = source(
  'facebook/community-alignment-dataset, sur Hugging Face',
  'https://huggingface.co/datasets/facebook/community-alignment-dataset',
);
export const ARTICLE_COMMUNITY_ALIGNMENT = source(
  'Zhang et al., « Cultivating Pluralism In Algorithmic Monoculture: The Community Alignment Dataset », arXiv 2507.09650',
  'https://arxiv.org/abs/2507.09650',
);

// ---------- La perte DPO et son piège (étapes 5 et 6) ----------

/** DPO (Rafailov et al., 2023) : une perte de classification sur des paires, sans modèle de récompense. */
export const DPO = Object.freeze({
  sansModeleDeRecompense: chiffre(true, ARTICLE_DPO, 'section 1 (« without explicit reward modeling or reinforcement learning »)'),
  pertedeClassification: chiffre(true, ARTICLE_DPO, 'résumé (« with only a simple classification loss »)'),
  /** β dit jusqu'où le modèle peut s'éloigner de la référence, le modèle affiné de départ. */
  betaEtReference: chiffre(
    true,
    ARTICLE_DPO,
    'section 3 (« β is a parameter controlling the deviation from the base reference policy π_ref, namely the initial SFT model »)',
  ),
  /** Le gradient monte la choisie et baisse la rejetée. */
  gradient: chiffre(
    true,
    ARTICLE_DPO,
    'section 4, « What does the DPO update do? » (« increases the likelihood of the preferred completions y_w and decreases the likelihood of dispreferred completions y_l »)',
  ),
  /** Les deux réponses d'une paire sont tirées du modèle de référence lui-même. */
  reponsesDeLaReference: chiffre(true, ARTICLE_DPO, 'section 4, « DPO outline » (« Sample completions y1, y2 ∼ π_ref(·|x) for every prompt x »)'),
});

/** DPOP (Pal et al., 2024) : la choisie peut devenir moins probable pendant la DPO, et un remède. */
export const DPOP = Object.freeze({
  baisseDeLaChoisie: chiffre(
    true,
    ARTICLE_DPOP,
    'résumé (« the standard DPO loss can lead to a reduction of the model’s likelihood of the preferred examples, as long as the relative probability between the preferred and dispreferred classes increases »)',
  ),
  reponsesProches: chiffre(true, ARTICLE_DPOP, 'résumé (« especially datasets in which the edit distance between pairs of completions is low »)'),
  penalite: chiffre(
    true,
    ARTICLE_DPOP,
    'section 4 (« DPOP adds the penalty term max(0, log π_ref(y_w|x)/π_θ(y_w|x)) to the loss within the log-sigmoid »)',
  ),
});

// ---------- Le jeu de préférences écarté (étape 2) ----------

/** Community Alignment, de Meta : des choix humains, mais des réponses écrites par Llama 3.3. */
export const COMMUNITY_ALIGNMENT = Object.freeze({
  licence: chiffre('CC BY 4.0', FICHE_COMMUNITY_ALIGNMENT_FR, 'en-tête de la fiche (« license: cc-by-4.0 »)'),
  /** Les paires en français, dédoublonnées et préparées pour la DPO par CATIE-AQ. */
  pairesFr: chiffre(71_525, FICHE_COMMUNITY_ALIGNMENT_FR, 'en-tête de la fiche (« num_examples: 71525 »)'),
  annotateurs: chiffre(3_500, FICHE_COMMUNITY_ALIGNMENT, 'section « Dataset » (« collected from >3,500 unique annotators »)'),
  modeleDesReponses: chiffre(
    'Llama-3.3-70B-Instruct',
    ARTICLE_COMMUNITY_ALIGNMENT,
    'annexe I, « Community Alignment codebook », first_turn_responses (« Candidate responses were generated simultaneously by Llama-3.3-70B-Instruct »)',
  ),
  clauseLlama: chiffre(
    'include "Llama" at the beginning of any such AI model name',
    LICENCE_LLAMA_33,
    'section 1.b.i (« any outputs or results of the Llama Materials to create, train, fine tune »)',
  ),
});

// ---------- Les chiffres de l'encadré (étape 9) ----------

/** InstructGPT (OpenAI, 2022) : un modèle de récompense appris sur des classements d'étiqueteurs, puis du PPO. */
export const INSTRUCTGPT_RM = Object.freeze({
  invitesRm: chiffre(33_000, ARTICLE_INSTRUCTGPT, 'section 3.2 (« the RM dataset has 33k training prompts »)'),
  invitesPpo: chiffre(31_000, ARTICLE_INSTRUCTGPT, 'section 3.2 (« the PPO dataset has 31k training prompts (only from the API) »)'),
  reponsesAClasserMin: chiffre(4, ARTICLE_INSTRUCTGPT, 'section 3.5, « Reward modeling (RM) » (« anywhere between K = 4 and K = 9 responses to rank »)'),
  reponsesAClasserMax: chiffre(9, ARTICLE_INSTRUCTGPT, 'section 3.5, « Reward modeling (RM) » (« anywhere between K = 4 and K = 9 responses to rank »)'),
  parametresRm: chiffre(6e9, ARTICLE_INSTRUCTGPT, 'section 3.5, « Reward modeling (RM) » (« In this paper we only use 6B RMs »)'),
  /** Le modèle de récompense lit une question et une réponse, et rend un seul nombre. */
  noteScalaire: chiffre(true, ARTICLE_INSTRUCTGPT, 'section 3.5, « Reward modeling (RM) » (« to take in a prompt and response, and output a scalar reward »)'),
  etiqueteurs: chiffre(40, ARTICLE_INSTRUCTGPT, 'section 3.4 (« a team of about 40 contractors »)'),
  petaflopsPpo: chiffre(60, ARTICLE_INSTRUCTGPT, 'section 5.1 (« our 175B PPO-ptx model requires 60 petaflops/s-days »)'),
  petaflopsGpt3: chiffre(3_640, ARTICLE_INSTRUCTGPT, 'section 5.1 (« compared to 3,640 petaflops/s-days for GPT-3 »)'),
  /** Dérivé : la part du PPO dans le calcul du pré-entraînement de GPT-3, 60 pétaflops/s-jours sur 3 640. */
  partDuPreEntrainement: chiffre(60 / 3_640, ARTICLE_INSTRUCTGPT, 'section 5.1 : 60 ÷ 3 640 pétaflops/s-jours, calcul fait ici', 'dérivé'),
});

/** Llama 2 (Meta, 2023) : plus d'un million de comparaisons, deux modèles de récompense, cinq tours. */
export const LLAMA_2_RLHF = Object.freeze({
  protocoleBinaire: chiffre(true, ARTICLE_LLAMA_2, 'section 3.2.1 (« We chose a binary comparison protocol »)'),
  comparaisonsMeta: chiffre(1_418_091, ARTICLE_LLAMA_2, 'tableau 6, ligne « Meta (Safety & Helpfulness) »'),
  comparaisonsTotal: chiffre(2_919_326, ARTICLE_LLAMA_2, 'tableau 6, ligne « Total » (avec des jeux ouverts)'),
  modelesDeRecompense: chiffre(2, ARTICLE_LLAMA_2, 'section 3.2.2 (« we train two separate reward models, one optimized for helpfulness […] and another for safety »)'),
  versionsRlhf: chiffre(5, ARTICLE_LLAMA_2, 'section 3.2.3 (« RLHF-V1, …, RLHF-V5 »)'),
  echantillonnageParRejet: chiffre(true, ARTICLE_LLAMA_2, 'section 3.2.3 (« We sample K outputs from the model and select the best candidate with our reward »)'),
});

/** Qwen2.5 (Alibaba, 2024) : des réponses du modèle affiné, triées par des contrôles, en paires pour la DPO. */
export const QWEN_25 = Object.freeze({
  controles: chiffre(
    true,
    ARTICLE_QWEN_25,
    'section 4.2, « Offline Reinforcement Learning » (« Responses that pass our quality checks are used as positive examples, while those that fail are treated as negative examples »)',
  ),
  revueHumaineEtAutomatique: chiffre(true, ARTICLE_QWEN_25, 'section 4.2 (« we make use of both human and automated review processes »)'),
  /** Les domaines où une réponse se vérifie : mathématiques, code, consignes, raisonnement logique. */
  domaines: chiffre(
    true,
    ARTICLE_QWEN_25,
    'section 4.2 (« we focus on objective query domains such as mathematics, coding, instruction following, and logical reasoning »)',
  ),
  paires: chiffre(150_000, ARTICLE_QWEN_25, 'section 4.2 (« approximately 150,000 training pairs »)'),
  epoques: chiffre(1, ARTICLE_QWEN_25, 'section 4.2 (« trained for one epoch »)'),
  taux: chiffre(7e-7, ARTICLE_QWEN_25, 'section 4.2 (« with a learning rate of 7 × 10−7 »)'),
});

/** Tülu 3 (Ai2, 2024) : la DPO normalisée par la longueur, des paires jugées par un autre modèle. */
export const TULU_3_DPO = Object.freeze({
  pairesTotal: chiffre(354_192, ARTICLE_TULU_3, 'section 2.3, « Tülu 3 Recipe » (« 354,192 instances for preference tuning ») et tableau 15, total'),
  paires8B: chiffre(271_409, ARTICLE_TULU_3, 'tableau 15, colonne 8B'),
  invitesTableau7: chiffre(425_145, ARTICLE_TULU_3, 'tableau 7, colonne des préférences, total (marqué γ)'),
  reponsesParInvite: chiffre(4, ARTICLE_TULU_3, 'section 5.2.1, « Stage 3: Preference Annotation » (« After generating four responses for each prompt »)'),
  juge: chiffre('GPT-4o', ARTICLE_TULU_3, 'section 5.2.1, « Stage 3: Preference Annotation » (« specifically GPT-4o-2024-0806, to rate each response from 1 to 5 »)'),
  normaliseeParLaLongueur: chiffre(true, ARTICLE_TULU_3, 'section 2.3, « Tülu 3 Recipe » (« used length-normalized DPO throughout the development process and training our final models »)'),
  beta: chiffre(5, ARTICLE_TULU_3, 'tableau 20 (« KL penalty coefficient β 5 »)'),
  taux8B: chiffre(5e-7, ARTICLE_TULU_3, 'tableau 20, colonne 8B (« Learning Rate 5 × 10-7 »)'),
  epoques: chiffre(1, ARTICLE_TULU_3, 'tableau 20 (« Number of Epochs 1 »)'),
  cartes8B: chiffre(8, ARTICLE_TULU_3, 'section 5.4 (« The 8B DPO model is trained for 10 hours on 8 Nvidia H100 GPUs »)'),
  heures8B: chiffre(10, ARTICLE_TULU_3, 'section 5.4 (« trained for 10 hours »)'),
  /** Dérivé : 8 cartes pendant 10 heures. */
  heuresDeCartes8B: chiffre(80, ARTICLE_TULU_3, 'section 5.4 : 8 cartes × 10 heures, calcul fait ici', 'dérivé'),
});

function verifiee(s: SourceLue): SourceVerifiee {
  return Object.freeze({ titre: s.titre, url: s.url, verifieLe: LU_LE_1_8 });
}

/** Les sources de l'encadré « Et chez un grand labo ? », dans l'ordre où il les cite. */
export const SOURCES_LABO_1_8: readonly SourceVerifiee[] = Object.freeze([ARTICLE_INSTRUCTGPT, ARTICLE_LLAMA_2, ARTICLE_QWEN_25, ARTICLE_TULU_3].map(verifiee));

/** Les sources de la perte DPO et de son piège (étapes 5 et 6), dans l'ordre où le chapitre les cite. */
export const SOURCES_DPO_1_8: readonly SourceVerifiee[] = Object.freeze([ARTICLE_DPO, ARTICLE_DPOP].map(verifiee));

/** Les sources du jeu écarté (étape 2), dans l'ordre où le chapitre les cite. */
export const SOURCES_DONNEES_1_8: readonly SourceVerifiee[] = Object.freeze(
  [FICHE_COMMUNITY_ALIGNMENT_FR, FICHE_COMMUNITY_ALIGNMENT, ARTICLE_COMMUNITY_ALIGNMENT, LICENCE_LLAMA_33].map(verifiee),
);
