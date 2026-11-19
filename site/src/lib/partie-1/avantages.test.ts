// Le jumeau des avantages d'un groupe et de la chance d'un groupe sans signal (chapitre 1.9) retrouve le Python.
//
// Les deux fonctions refont les mêmes opérations dans le même ordre que `avantages_a_la_main` et `sans_signal`
// (projets/1.9-raisonnement/raisonnement_pas_a_pas/avantages.py) : une somme en boucle, une division, deux produits
// en boucle. Les flottants sont donc ceux du Python, à l'identique : les attendus se comparent sans tolérance
// (toStrictEqual), comme la page de parité.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { avantages, sansSignal } from './avantages';
import { FICHIERS_PARTIE_1 } from './fichiers';

interface Attendus {
  avantages: { recompenses: number[]; avantages: number[] }[];
  sans_signal: { p: number; n: number; chance: number }[];
}

const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.raisonnement}`, 'utf8')) as Attendus;

describe('les avantages d’un groupe', () => {
  it('égalent ceux du Python sur les dix groupes, à l’identique', () => {
    expect(ATTENDUS.avantages).toHaveLength(10);
    for (const { recompenses, avantages: attendus } of ATTENDUS.avantages) {
      expect(avantages([recompenses])[0], JSON.stringify(recompenses)).toStrictEqual(attendus);
    }
  });

  it('chaque groupe est indépendant des autres', () => {
    const groupes = ATTENDUS.avantages.map((g) => g.recompenses);
    expect(avantages(groupes)).toStrictEqual(ATTENDUS.avantages.map((g) => g.avantages));
  });

  it('la récompense moins la moyenne du groupe', () => {
    expect(avantages([[1, 0, 0, 1]])).toStrictEqual([[0.5, -0.5, -0.5, 0.5]]);
    expect(avantages([[1, 0, 0, 0]])).toStrictEqual([[0.75, -0.25, -0.25, -0.25]]);
  });

  it('un groupe sans signal a des avantages nuls, et aucun n’est NaN', () => {
    for (const groupe of [[0, 0, 0, 0], [1, 1, 1, 1], [0.25, 0.25, 0.25]]) {
      expect(avantages([groupe])[0].every((a) => a === 0)).toBe(true);
    }
    for (const { recompenses } of ATTENDUS.avantages) expect(avantages([recompenses])[0].every((a) => Number.isFinite(a))).toBe(true);
  });

  it('les avantages d’un groupe somment à zéro, à 10⁻¹² près', () => {
    for (const g of [[1, 0, 0, 1, 1], [0, 1], [1, 1, 0], [0.1, 0.2, 0.3, 0.4]]) {
      expect(Math.abs(avantages([g])[0].reduce((s, a) => s + a, 0))).toBeLessThan(1e-12);
    }
  });

  it('refuse un groupe vide, et accepte aucun groupe', () => {
    expect(() => avantages([[1], []])).toThrow(/Un groupe sans aucune réponse/);
    expect(avantages([])).toStrictEqual([]);
  });
});

describe('la chance qu’un groupe n’apprenne rien', () => {
  it('égale celle du Python sur les 54 points de la grille, à l’identique', () => {
    expect(ATTENDUS.sans_signal).toHaveLength(54);
    for (const { p, n, chance } of ATTENDUS.sans_signal) expect(sansSignal(p, n), `p ${p}, n ${n}`).toBe(chance);
  });

  it('une réponse seule est toujours sans signal ; deux réponses à égalité, une chance sur deux', () => {
    expect(sansSignal(0.5, 1)).toBe(1);
    expect(sansSignal(0.5, 2)).toBe(0.5);
    expect(sansSignal(0, 8)).toBe(1);
    expect(sansSignal(1, 8)).toBe(1);
  });

  it('vaut pⁿ + (1 − p)ⁿ, à 10⁻¹² près en relatif', () => {
    for (const [p, n] of [[0.2, 8], [0.05, 16], [0.9, 4]] as const) {
      expect(Math.abs(sansSignal(p, n) - (p ** n + (1 - p) ** n)) / sansSignal(p, n)).toBeLessThan(1e-12);
    }
  });

  it('refuse une chance ou une taille impossibles', () => {
    for (const p of [-0.1, 1.5, Number.NaN]) expect(() => sansSignal(p, 4)).toThrow(/entre 0 et 1/);
    for (const n of [0, -2, 2.5, Number.NaN]) expect(() => sansSignal(0.5, n)).toThrow(/au moins une réponse/);
  });
});
