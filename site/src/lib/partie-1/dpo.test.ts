// Le jumeau de la perte DPO retrouve les attendus du Python (la section grille_dpo de
// projets/1.8-alignement/tests/attendus.json : 27 points, β et les deux écarts de gain) à 10⁻¹² près.
//
// Pas à l'identique : Math.exp et Math.log1p ne sont pas exacts d'un moteur à l'autre (V8, SpiderMonkey, JavaScriptCore
// et la bibliothèque de Python n'arrondissent pas toujours pareil au dernier chiffre). Le jumeau fait les mêmes opérations
// dans le même ordre, et l'écart reste de l'ordre de 10⁻¹⁶ ; la tolérance de 10⁻¹² est celle du test Python contre PyTorch.
// C'est aussi pourquoi cette section est retirée de la page de parité (CLES_NON_REFAITES), qui compare à l'identique.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { deriveeDpo, moinsLogSigmoide, perteDpo, sigmoide } from './dpo';
import { FICHIERS_PARTIE_1 } from './fichiers';

interface Point {
  beta: number;
  ecart_choisie: number;
  ecart_rejetee: number;
  perte: number;
  derivee: number;
}

const GRILLE = (JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.notes}`, 'utf8')) as { grille_dpo: Point[] }).grille_dpo;

describe('la perte DPO', () => {
  it('égale celle du Python à 10⁻¹² près sur les 27 points de la grille', () => {
    expect(GRILLE).toHaveLength(27);
    for (const p of GRILLE) {
      expect(Math.abs(perteDpo(p.beta, p.ecart_choisie, p.ecart_rejetee) - p.perte), `perte ${JSON.stringify(p)}`).toBeLessThanOrEqual(1e-12);
    }
  });

  it('sa dérivée égale celle du Python à 10⁻¹² près', () => {
    for (const p of GRILLE) {
      expect(Math.abs(deriveeDpo(p.beta, p.ecart_choisie, p.ecart_rejetee) - p.derivee), `dérivée ${JSON.stringify(p)}`).toBeLessThanOrEqual(1e-12);
    }
  });

  it('vaut ln 2 sans écart de gain, quel que soit β', () => {
    for (const beta of [0.05, 0.1, 0.5, 3]) expect(perteDpo(beta, 1.5, 1.5)).toBeCloseTo(Math.LN2, 15);
  });

  it('baisse autant quand la choisie monte que quand la rejetée descend', () => {
    expect(perteDpo(0.1, 5, 0)).toBeLessThan(perteDpo(0.1, 0, 0));
    expect(perteDpo(0.1, 5, 0)).toBeCloseTo(perteDpo(0.1, 0, -5), 15);
    expect(perteDpo(0.1, -5, 0)).toBeGreaterThan(perteDpo(0.1, 0, 0));
  });

  it('ne déborde pas aux extrêmes, et ne rend jamais NaN', () => {
    expect(perteDpo(0.1, -4000, 4000)).toBeCloseTo(800, 10);
    expect(perteDpo(0.1, 4000, -4000)).toBe(0);
    expect(moinsLogSigmoide(-1e6)).toBe(1e6);
    expect(moinsLogSigmoide(1e6)).toBe(0);
    expect(sigmoide(-800)).toBe(0);
    expect(sigmoide(800)).toBe(1);
    for (const x of [0, -0, 1e-300, -1e-300, 1e300, -1e300, 12345.678]) {
      expect(Number.isNaN(perteDpo(0.1, x, 0))).toBe(false);
      expect(Number.isNaN(deriveeDpo(0.1, x, 0))).toBe(false);
    }
  });

  it('a une dérivée négative, égale à la pente de la perte', () => {
    for (const p of GRILLE) {
      const h = 1e-6;
      const pente = (perteDpo(p.beta, p.ecart_choisie + h, p.ecart_rejetee) - perteDpo(p.beta, p.ecart_choisie - h, p.ecart_rejetee)) / (2 * h);
      expect(deriveeDpo(p.beta, p.ecart_choisie, p.ecart_rejetee)).toBeLessThan(0);
      expect(deriveeDpo(p.beta, p.ecart_choisie, p.ecart_rejetee)).toBeCloseTo(pente, 6);
    }
  });
});
