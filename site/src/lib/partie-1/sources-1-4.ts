// Les articles que cite le chapitre 1.4, « Le transformer, pièce par pièce », avec leur adresse
// et la date de leur lecture. Chaque article a été lu le 9 novembre 2026 sur sa page arXiv (son
// résumé) : le chapitre ne leur prête rien de plus que ce que dit ce résumé, et aucun chiffre
// qu'il ne donne. Les chiffres de Llama 3 405B viennent des modèles publics du calculateur
// (MODELES_PUBLICS, calculateur/donnees.ts), avec leur source.
//
// Ce module n'importe rien (ni .json, ni astro:*) : un parcours Playwright peut l'importer.

import type { SourceVerifiee } from './sources-1-2';

const LU_LE = '2026-11-09';

function article(titre: string, url: string): SourceVerifiee {
  return Object.freeze({ titre, url, verifieLe: LU_LE });
}

/**
 * Vaswani et al., 2017 : le transformer, « fondé seulement sur l'attention », sans récurrence
 * ni convolution (résumé, première soumission le 12 juin 2017).
 */
export const VASWANI_2017 = article(
  'Vaswani et al., « Attention Is All You Need », arXiv 1706.03762, 2017',
  'https://arxiv.org/abs/1706.03762',
);

/**
 * Su et al., 2021 : RoPE, qui code la position absolue par une matrice de rotation et fait
 * entrer la position relative dans l'attention (résumé, première soumission le 20 avril 2021).
 */
export const SU_2021 = article(
  'Su et al., « RoFormer: Enhanced Transformer with Rotary Position Embedding », arXiv 2104.09864, 2021',
  'https://arxiv.org/abs/2104.09864',
);

/**
 * Shazeer, 2020 : les variantes de GLU dans le MLP du transformer. Le résumé dit : un GLU est le
 * produit, composante par composante, de deux projections linéaires, dont l'une passe d'abord
 * par une sigmoïde ; on peut mettre une autre fonction à la place de la sigmoïde ; ces
 * variantes, essayées dans les sous-couches « feed-forward » du transformer, donnent pour
 * certaines une meilleure qualité que ReLU ou GELU. Il ne donne aucun chiffre (première
 * soumission le 12 février 2020).
 */
export const SHAZEER_2020 = article('Noam Shazeer, « GLU Variants Improve Transformer », arXiv 2002.05202, 2020', 'https://arxiv.org/abs/2002.05202');

/**
 * Zhang et Sennrich, 2019 : RMSNorm, présenté à NeurIPS 2019. Le résumé dit que LayerNorm
 * recentre et remet à l'échelle, que le recentrage n'est sans doute pas nécessaire, et que
 * RMSNorm, qui divise par la racine de la moyenne des carrés, fait aussi bien que LayerNorm en
 * réduisant le temps de calcul de 7 % à 64 % selon les modèles (première soumission le
 * 16 octobre 2019).
 */
export const ZHANG_SENNRICH_2019 = Object.freeze({
  source: article('Biao Zhang et Rico Sennrich, « Root Mean Square Layer Normalization », arXiv 1910.07467, 2019', 'https://arxiv.org/abs/1910.07467'),
  /** « reduces the running time by 7%~64% on different models » (résumé). */
  tempsGagne: Object.freeze({ min: 0.07, max: 0.64 }),
});

/** Les articles du chapitre, dans l'ordre où il les cite. */
export const ARTICLES_1_4: readonly SourceVerifiee[] = Object.freeze([VASWANI_2017, SU_2021, SHAZEER_2020, ZHANG_SENNRICH_2019.source]);
