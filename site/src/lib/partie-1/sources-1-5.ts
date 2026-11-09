// Les chiffres de labo du chapitre 1.5, « Le pré-entraînement sur ton GPU » : l'entraînement de
// Llama 3.1 405B, de Meta, chacun avec son adresse, l'endroit de la source où il se lit et la date
// de la lecture. Tous ont été relus à la source le 9 novembre 2026 :
//
// - la carte de modèle de Llama 3.1 (MODEL_CARD.md, « Hardware and Software », « Training Energy
//   Use ») : « Training utilized a cumulative of 39.3M GPU hours of computation on H100-80GB »,
//   dont 30,84 millions pour le 405B (tableau, colonne « Training Time (GPU hours) ») ;
// - l'article « The Llama 3 Herd of Models » (arXiv 2407.21783), qui appelle ce modèle Llama 3
//   405B :
//   - section 1 : « our flagship language model was pre-trained using 3.8 × 10^25 FLOPs » ;
//   - section 3.3.1 : « Llama 3 405B is trained on up to 16K H100 GPUs », et son tableau 4 :
//     8 192 cartes, puis 16 384 (le « 16K » du texte) ;
//   - section 3.3.4 : « During a 54-day snapshot period of pre-training, we experienced a total of
//     466 job interruptions. Of these, 47 were planned interruptions due to automated maintenance
//     operations », les 419 autres imprévues. Les 54 jours sont une période observée du
//     pré-entraînement, pas sa durée entière : le chapitre le dit ainsi.
//
// La fiche du plan écrivait « jusqu'à 16 000 cartes » : la source dit « 16K », et son tableau 4
// donne 16 384. Le chapitre écrit 16 384, comme le calculateur (REPERES_EFFICACITE).
//
// Ce module n'importe rien (ni .json, ni astro:*) : un parcours Playwright peut l'importer.

import type { SourceVerifiee } from './sources-1-2';

const LU_LE = '2026-11-09';

/** Une source lue : son titre et son adresse. */
interface SourceLue {
  titre: string;
  url: string;
}

/** Un chiffre de labo : sa valeur, l'adresse de sa source, où il s'y lit, et la date de la lecture. */
export interface ChiffreDeLabo {
  valeur: number;
  url: string;
  /** Où le chiffre se lit dans la source : la section, le tableau. */
  ou: string;
  /** AAAA-MM-JJ. */
  releveLe: string;
}

/** La carte de modèle de Llama 3.1, sur le dépôt llama-models de Meta. */
export const CARTE_LLAMA_31: SourceLue = Object.freeze({
  titre: 'Meta, carte de modèle de Llama 3.1 (llama-models, MODEL_CARD.md)',
  url: 'https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md',
});

/** L'article de Meta sur Llama 3, qui décrit l'entraînement du 405B. */
export const ARTICLE_LLAMA_3: SourceLue = Object.freeze({
  titre: 'Llama Team (Meta), « The Llama 3 Herd of Models », arXiv 2407.21783',
  url: 'https://arxiv.org/abs/2407.21783',
});

function chiffre(valeur: number, source: SourceLue, ou: string): ChiffreDeLabo {
  return Object.freeze({ valeur, url: source.url, ou, releveLe: LU_LE });
}

/** L'entraînement de Llama 3.1 405B, chiffre par chiffre. */
export const LLAMA_31_405B = Object.freeze({
  /** Les heures de calcul de cartes H100 (80 Go) de son entraînement. */
  heuresH100: chiffre(30.84e6, CARTE_LLAMA_31, 'Hardware and Software, tableau des heures de calcul (Training Time, GPU hours)'),
  /** Le plus grand nombre de cartes H100 qui l'ont entraîné ensemble. */
  cartesMax: chiffre(16_384, ARTICLE_LLAMA_3, 'section 3.3.1 (« up to 16K H100 GPUs ») et tableau 4'),
  /** La durée de la période observée du pré-entraînement, en jours. */
  joursObserves: chiffre(54, ARTICLE_LLAMA_3, 'section 3.3.4 (« a 54-day snapshot period of pre-training »)'),
  /** Les interruptions pendant cette période. */
  interruptions: chiffre(466, ARTICLE_LLAMA_3, 'section 3.3.4 (« 466 job interruptions »)'),
  /** Celles qui étaient prévues : de la maintenance automatique. */
  interruptionsPrevues: chiffre(47, ARTICLE_LLAMA_3, 'section 3.3.4 (« 47 were planned interruptions »)'),
  /** Celles qui ne l'étaient pas. */
  interruptionsImprevues: chiffre(419, ARTICLE_LLAMA_3, 'section 3.3.4 (« 419 were unexpected interruptions »)'),
  /** Les opérations de son pré-entraînement. */
  operations: chiffre(3.8e25, ARTICLE_LLAMA_3, 'section 1 (« pre-trained using 3.8 × 10^25 FLOPs »)'),
});

/** Les sources de l'encadré « Et chez un grand labo ? », dans l'ordre où il les cite. */
export const SOURCES_LABO_1_5: readonly SourceVerifiee[] = Object.freeze(
  [CARTE_LLAMA_31, ARTICLE_LLAMA_3].map((s) => Object.freeze({ titre: s.titre, url: s.url, verifieLe: LU_LE })),
);
