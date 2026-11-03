// L'attention : scores, softmax et mélange des valeurs.
//
// Jumeau de projets/mini-modele/tests/test_attention.py : les mêmes cas, avec
// les mêmes valeurs. La parité au bit près avec le Python passe par les
// attendus du modèle (modele.test.ts), qui appellent ces fonctions à chaque
// tête et à chaque position.

import { describe, expect, it } from 'vitest';
import { melangerValeurs, poidsAttention, scoresAttention, softmax } from './attention';
import { exp, Hasard, somme, versHex } from './calcul';

describe('scoresAttention', () => {
  it('requête · clé, fois l’échelle, dans l’ordre des clés', () => {
    expect(scoresAttention([1.0, 2.0], [[3.0, 4.0], [5.0, 6.0]], 0.5)).toEqual([5.5, 8.5]);
    expect(scoresAttention([1.0, -2.0], [[0.5, 0.25]], 2.0)).toEqual([0.0]);
    expect(scoresAttention([1.0, 2.0], [], 0.5)).toEqual([]);
    expect(() => scoresAttention([1.0, 2.0], [[1.0, 2.0, 3.0]], 0.5)).toThrow(/même longueur/);
    const cles = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]];
    expect(scoresAttention([2.0, 3.0], cles, 1.0)).toEqual([2.0, 3.0, 5.0]);
    expect(scoresAttention([2.0, 3.0], [...cles].reverse(), 1.0)).toEqual([5.0, 3.0, 2.0]);
  });
});

describe('softmax', () => {
  it('des poids égaux pour des scores égaux, sans débordement', () => {
    expect(softmax([0.0])).toEqual([1.0]);
    expect(softmax([2.0, 2.0, 2.0, 2.0])).toEqual([0.25, 0.25, 0.25, 0.25]);
    expect(softmax([1000.0, 1000.0])).toEqual([0.5, 0.5]);
    expect(softmax([-1000.0, 0.0])).toEqual([0.0, 1.0]);
    expect(() => softmax([])).toThrow(/vide/);
  });

  it('suit la définition, opération par opération', () => {
    const scores = [0.3, -1.2, 2.5, 0.0];
    const e = scores.map((s) => exp(s - 2.5));
    const total = somme(e);
    expect(softmax(scores).map(versHex)).toEqual(e.map((v) => versHex(v / total)));
  });

  it('reste proche de la libm (précision, pas parité)', () => {
    const h = new Hasard(11);
    for (let essai = 0; essai < 200; essai++) {
      const scores = Array.from({ length: 7 }, () => (h.uniforme() - 0.5) * 20);
      let m = scores[0];
      for (const s of scores) if (s > m) m = s;
      const temoin = scores.map((s) => Math.exp(s - m));
      const total = temoin.reduce((a, b) => a + b, 0);
      softmax(scores).forEach((p, i) => expect(Math.abs(p - temoin[i] / total)).toBeLessThanOrEqual(1e-15));
    }
  });
});

describe('poidsAttention', () => {
  it('des poids égaux pour des scores égaux, et une somme de 1', () => {
    expect(poidsAttention([0.0, 0.0], [[1.0, 2.0], [3.0, 4.0]], 0.5)).toEqual([0.5, 0.5]);
    const p = poidsAttention([1.0, -2.0], [[0.3, 0.1], [2.0, -1.0], [-0.5, 0.5]], 0.5);
    expect(Math.abs(somme(p) - 1.0)).toBeLessThanOrEqual(1e-15);
  });

  it('est le softmax des scores, et une seule clé visible prend tout le poids', () => {
    const requete = [0.7, -0.4, 1.1];
    const cles = [[0.2, 0.5, -0.3], [1.5, -0.2, 0.4], [-0.6, 0.9, 0.0]];
    expect(poidsAttention(requete, cles, 0.5).map(versHex)).toEqual(softmax(scoresAttention(requete, cles, 0.5)).map(versHex));
    expect(poidsAttention(requete, cles.slice(0, 1), 0.5)).toEqual([1.0]);
  });
});

describe('melangerValeurs', () => {
  it('mélange les valeurs selon les poids', () => {
    expect(melangerValeurs([0.25, 0.75], [[1.0, 2.0], [3.0, 4.0]])).toEqual([2.5, 3.5]);
    expect(melangerValeurs([1.0], [[-1.5, 0.0, 2.0]])).toEqual([-1.5, 0.0, 2.0]);
    expect(melangerValeurs([0.0, 1.0], [[9.0], [-3.0]])).toEqual([-3.0]);
  });

  it('refuse des poids et des valeurs qui ne vont pas ensemble', () => {
    expect(() => melangerValeurs([0.5, 0.5], [[1.0, 2.0]])).toThrow(/autant de poids que de valeurs/);
    expect(() => melangerValeurs([], [])).toThrow(/au moins une valeur/);
    expect(() => melangerValeurs([0.5, 0.5], [[1.0, 2.0], [3.0]])).toThrow(/même longueur/);
  });

  it('somme par j croissant, comme le Python', () => {
    const valeurs = [[1e16], [1.0], [1.0]];
    expect(melangerValeurs([1.0, 1.0, 1.0], valeurs)).toEqual([1e16]);
    expect(melangerValeurs([1.0, 1.0, 1.0], [...valeurs].reverse())).toEqual([1e16 + 2.0]);
  });
});
