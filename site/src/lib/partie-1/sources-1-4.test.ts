// Les articles du chapitre 1.4 : chacun a son adresse arXiv et sa date de lecture.

import { describe, expect, it } from 'vitest';
import { ARTICLES_1_4, SHAZEER_2020, SU_2021, VASWANI_2017, ZHANG_SENNRICH_2019 } from './sources-1-4';

describe('les articles du chapitre 1.4', () => {
  it('ont chacun un titre, une adresse arXiv et la date de leur lecture', () => {
    expect(ARTICLES_1_4).toStrictEqual([VASWANI_2017, SU_2021, SHAZEER_2020, ZHANG_SENNRICH_2019.source]);
    for (const a of ARTICLES_1_4) {
      expect(a.url, a.titre).toMatch(/^https:\/\/arxiv\.org\/abs\/\d{4}\.\d{5}$/);
      // Le numéro arXiv du titre est celui de l'adresse.
      expect(a.titre, a.url).toContain(`arXiv ${a.url.split('/').at(-1)}`);
      expect(a.verifieLe, a.titre).toBe('2026-11-09');
    }
  });

  it('le temps gagné par RMSNorm, d’après le résumé : de 7 à 64 %', () => {
    expect(ZHANG_SENNRICH_2019.tempsGagne).toStrictEqual({ min: 0.07, max: 0.64 });
  });
});
