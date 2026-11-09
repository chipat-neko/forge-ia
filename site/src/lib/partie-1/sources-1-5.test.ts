// Les chiffres de labo du chapitre 1.5 : chacun a son adresse et sa date de lecture, et ceux que
// le calculateur a aussi relevés (les opérations de Llama 3 405B, ses cartes H100) y sont les mêmes.

import { describe, expect, it } from 'vitest';
import { modelePublic, REPERES_EFFICACITE } from '../calculateur/donnees';
import { nombre } from '../nombres';
import { ARTICLE_LLAMA_3, CARTE_LLAMA_31, LLAMA_31_405B, SOURCES_LABO_1_5 } from './sources-1-5';

describe('les chiffres de Llama 3.1 405B', () => {
  it('chacun a sa valeur, son adresse, l’endroit de la source et sa date de lecture', () => {
    const chiffres = Object.values(LLAMA_31_405B);
    expect(chiffres).toHaveLength(7);
    for (const c of chiffres) {
      expect(Number.isFinite(c.valeur) && c.valeur > 0, c.ou).toBe(true);
      expect([ARTICLE_LLAMA_3.url, CARTE_LLAMA_31.url], c.ou).toContain(c.url);
      expect(c.releveLe, c.ou).toBe('2026-11-09');
      expect(c.ou.length, c.ou).toBeGreaterThan(5);
    }
  });

  it('les valeurs relevées à la source le 9 novembre 2026', () => {
    expect(Object.fromEntries(Object.entries(LLAMA_31_405B).map(([cle, c]) => [cle, c.valeur]))).toStrictEqual({
      heuresH100: 30.84e6,
      cartesMax: 16_384,
      joursObserves: 54,
      interruptions: 466,
      interruptionsPrevues: 47,
      interruptionsImprevues: 419,
      operations: 3.8e25,
    });
    // Les heures viennent de la carte de modèle de Llama 3.1, le reste de l'article de Meta.
    expect(LLAMA_31_405B.heuresH100.url).toBe(CARTE_LLAMA_31.url);
    for (const cle of ['cartesMax', 'joursObserves', 'interruptions', 'interruptionsPrevues', 'interruptionsImprevues', 'operations'] as const) {
      expect(LLAMA_31_405B[cle].url, cle).toBe(ARTICLE_LLAMA_3.url);
    }
  });

  it('les interruptions prévues et imprévues font le total', () => {
    expect(LLAMA_31_405B.interruptionsPrevues.valeur + LLAMA_31_405B.interruptionsImprevues.valeur).toBe(LLAMA_31_405B.interruptions.valeur);
  });

  it('les opérations et les cartes sont celles que le calculateur a relevées dans le même article', () => {
    const llama = modelePublic('llama-3-405b');
    expect(llama.operationsPubliees).toBe(LLAMA_31_405B.operations.valeur);
    expect(llama.source.url).toBe(ARTICLE_LLAMA_3.url);
    const repere = REPERES_EFFICACITE.find((r) => r.modele === 'Llama 3 405B');
    expect(repere?.materiel).toContain(`${nombre(LLAMA_31_405B.cartesMax.valeur)} H100`);
  });

  it('les sources de l’encadré : la carte de modèle et l’article, avec leur date', () => {
    expect(SOURCES_LABO_1_5).toStrictEqual([
      { titre: CARTE_LLAMA_31.titre, url: CARTE_LLAMA_31.url, verifieLe: '2026-11-09' },
      { titre: ARTICLE_LLAMA_3.titre, url: ARTICLE_LLAMA_3.url, verifieLe: '2026-11-09' },
    ]);
    expect(ARTICLE_LLAMA_3.url).toBe('https://arxiv.org/abs/2407.21783');
    expect(CARTE_LLAMA_31.url).toBe('https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md');
  });
});
