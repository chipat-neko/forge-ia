// Le jumeau de l'empaquetage BFD retrouve exactement le placement d'`empaqueter` du Python
// (projets/1.7-conversation/tests/attendus.json, section « empaquetages » : cinq listes de longueurs, quatre
// capacités) : mêmes rangées, mêmes exemples dans le même ordre, même nombre d'écartés (toStrictEqual).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { empaqueterLongueurs } from './bfd';
import { FICHIERS_PARTIE_1 } from './fichiers';

interface CasAttendu {
  liste: string;
  longueurs: number[];
  capacite: number;
  rangees: number[][];
  ecartes: number;
}

const CAS = (JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.conversation}`, 'utf8')) as { empaquetages: CasAttendu[] }).empaquetages;

describe('le jumeau de l’empaquetage BFD', () => {
  it('lit cinq listes pour quatre capacités', () => {
    expect(CAS).toHaveLength(20);
    expect(new Set(CAS.map((c) => c.liste)).size).toBe(5);
    expect(CAS.map((c) => c.capacite).slice(0, 4)).toStrictEqual([65, 129, 513, 2049]);
  });

  it.each(CAS.map((c) => [`${c.liste}, capacité ${c.capacite}`, c] as const))('retrouve le placement de forge : %s', (_nom, c) => {
    expect(empaqueterLongueurs(c.longueurs, c.capacite)).toStrictEqual({ rangees: c.rangees, ecartes: c.ecartes });
  });

  it('range d’abord le plus long, puis chaque exemple là où il laisse le moins de place', () => {
    // capacité 10 : 7 ouvre la rangée 0 (3 libres) ; 5 ouvre la 1 (5 libres) ; 3 va dans la 0 (0 libre, pas 2 libres de la 1).
    expect(empaqueterLongueurs([3, 5, 7], 10)).toStrictEqual({ rangees: [[2, 0], [1]], ecartes: 0 });
  });

  it('à égalité de longueur, garde l’ordre d’origine ; à égalité de place, prend la première rangée ouverte', () => {
    expect(empaqueterLongueurs([4, 4, 4, 4], 8)).toStrictEqual({ rangees: [[0, 1], [2, 3]], ecartes: 0 });
    // Deux rangées ont 6 places libres : le 6 va dans la première ouverte.
    expect(empaqueterLongueurs([9, 9, 6], 15)).toStrictEqual({ rangees: [[0, 2], [1]], ecartes: 0 });
  });

  it('écarte ce qui est plus long qu’une rangée, ou vide, et le compte', () => {
    expect(empaqueterLongueurs([3, 11, 0, 10], 10)).toStrictEqual({ rangees: [[3], [0]], ecartes: 2 });
    expect(empaqueterLongueurs([], 10)).toStrictEqual({ rangees: [], ecartes: 0 });
    expect(empaqueterLongueurs([20, 30], 10)).toStrictEqual({ rangees: [], ecartes: 2 });
  });

  it('remplit une rangée pile', () => {
    expect(empaqueterLongueurs([5, 5], 10)).toStrictEqual({ rangees: [[0, 1]], ecartes: 0 });
    expect(empaqueterLongueurs([10], 10)).toStrictEqual({ rangees: [[0]], ecartes: 0 });
  });

  it('refuse une rangée sans contexte, comme le Python', () => {
    expect(() => empaqueterLongueurs([1], 1)).toThrow('La longueur d\'une rangée doit valoir au moins 1, pas 0.');
  });

  it('ne change pas la liste qu’on lui donne', () => {
    const longueurs = [3, 9, 4];
    empaqueterLongueurs(longueurs, 10);
    expect(longueurs).toStrictEqual([3, 9, 4]);
  });

  it('range cent mille exemples sans s’essouffler', () => {
    // Un entier pseudo-aléatoire, sans flottant : le même à chaque fois.
    let x = 1;
    const longueurs = Array.from({ length: 100_000 }, () => {
      x = (1103515245 * x + 12345) % 2 ** 31;
      return 1 + ((x >> 8) % 1500);
    });
    const debut = performance.now();
    const { rangees, ecartes } = empaqueterLongueurs(longueurs, 2049);
    expect(ecartes).toBe(0);
    expect(rangees.flat()).toHaveLength(100_000);
    for (const rangee of rangees) expect(rangee.reduce((somme, rang) => somme + longueurs[rang], 0)).toBeLessThanOrEqual(2049);
    expect(performance.now() - debut).toBeLessThan(20_000);
  });
});
