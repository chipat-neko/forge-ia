// L'atelier des formes du chapitre 0.4 : ses résultats sont ceux du jumeau des
// formes (formes.ts, vérifié contre PyTorch), et ses phrases, sa grille et son
// défi viennent d'atelier-formes.ts. On les vérifie ici sur toutes les paires
// de formes de 1 à 3 dimensions, puis sur les phrases exactes des cas du
// chapitre.

import { describe, expect, it } from 'vitest';
import { ecrireForme, formeDiffusee, formeProduit } from './formes';
import {
  A_DEPART,
  B_DEPART,
  DEFI_FORMES_REUSSI,
  defiReussi,
  DIMENSIONS_MAX,
  DIMENSIONS_MIN,
  ecrireResultat,
  etatDuDefi,
  expliquer,
  forme,
  gagneFormes,
  grille,
  resultat,
  TAILLE_MAX,
  TAILLE_MIN,
  TAILLES_A,
  TAILLES_B,
  type Case,
  type Operation,
} from './atelier-formes';

const FINE = '\u202F';

/** Toutes les formes de 1 à 3 dimensions dont chaque taille est dans `tailles`. */
function toutesLesFormes(tailles: number[]): number[][] {
  const formes: number[][] = [];
  const etendre = (debut: number[]) => {
    if (debut.length > 0) formes.push(debut);
    if (debut.length === DIMENSIONS_MAX) return;
    for (const t of tailles) etendre([...debut, t]);
  };
  etendre([]);
  return formes;
}

/** Les tailles d'une rangée de la grille, de gauche à droite (null pour une case vide). */
const tailles = (cases: Case[]) => cases.map((c) => c.taille);

/** Une forme alignée par la droite sur les DIMENSIONS_MAX colonnes de la grille. */
function alignee(f: readonly number[]): (number | null)[] {
  return [...new Array<null>(DIMENSIONS_MAX - f.length).fill(null), ...f];
}

describe('atelier des formes : le départ et les bornes', () => {
  it('A = (3, 1) et B = (4,) à l’arrivée, et les tailles cachées sont dans les bornes', () => {
    expect(A_DEPART).toEqual([3, 1]);
    expect(B_DEPART).toEqual([4]);
    expect(TAILLES_A).toHaveLength(DIMENSIONS_MAX);
    expect(TAILLES_B).toHaveLength(DIMENSIONS_MAX);
    // Les premières tailles des canaux sont celles du départ.
    expect(forme(TAILLES_A, A_DEPART.length)).toEqual([...A_DEPART]);
    expect(forme(TAILLES_B, B_DEPART.length)).toEqual([...B_DEPART]);
    for (const t of [...TAILLES_A, ...TAILLES_B]) {
      expect(t).toBeGreaterThanOrEqual(TAILLE_MIN);
      expect(t).toBeLessThanOrEqual(TAILLE_MAX);
    }
    expect([DIMENSIONS_MIN, DIMENSIONS_MAX, TAILLE_MIN, TAILLE_MAX]).toEqual([1, 3, 1, 6]);
    expect(A_DEPART.length).toBeGreaterThanOrEqual(DIMENSIONS_MIN);
  });

  it('(3, 1) + (4,) donne (3, 4) : la page arrive avec ce résultat', () => {
    expect(ecrireResultat(resultat(A_DEPART, B_DEPART, 'plus'))).toBe('(3, 4)');
    expect(ecrireResultat(resultat(A_DEPART, B_DEPART, 'produit'))).toBe('impossible');
  });

  it('forme() prend les n premières tailles, et refuse un n hors des bornes', () => {
    expect(forme([5, 6, 2], 1)).toEqual([5]);
    expect(forme([5, 6, 2], 3)).toEqual([5, 6, 2]);
    expect(() => forme([5, 6, 2], 0)).toThrow(/dimensions/);
    expect(() => forme([5, 6, 2], 4)).toThrow(/dimensions/);
  });
});

describe('atelier des formes : le résultat et la grille suivent le jumeau, sur toutes les paires', () => {
  // 39 formes de tailles 1 à 3 (les paires des attendus), plus des tailles 4 à 6 pour les bords de l'atelier.
  const formes = [...toutesLesFormes([1, 2, 3]), [6], [6, 6], [6, 6, 6], [1, 6, 1], [5, 4, 6], [4, 1]];
  const operations: Operation[] = ['plus', 'produit'];

  it('le résultat est celui de formeDiffusee ou de formeProduit, écrit comme Python', () => {
    for (const a of formes) {
      for (const b of formes) {
        const plus = formeDiffusee(a, b);
        const fois = formeProduit(a, b);
        expect(resultat(a, b, 'plus')).toStrictEqual(plus);
        expect(resultat(a, b, 'produit')).toStrictEqual(fois);
        expect(ecrireResultat(resultat(a, b, 'plus'))).toBe(plus === null ? 'impossible' : ecrireForme(plus));
        expect(ecrireResultat(resultat(a, b, 'produit'))).toBe(fois === null ? 'impossible' : ecrireForme(fois));
      }
    }
  });

  it('la grille : A, B et le résultat alignés par la droite, avec les cases étirées, soulignées et en conflit', () => {
    for (const a of formes) {
      for (const b of formes) {
        for (const op of operations) {
          const nom = `${ecrireForme(a)} ${op} ${ecrireForme(b)}`;
          const g = grille(a, b, op);
          const r = resultat(a, b, op);
          expect(g.a, nom).toHaveLength(DIMENSIONS_MAX);
          expect(g.b, nom).toHaveLength(DIMENSIONS_MAX);
          // Le résultat, aligné par la droite ; rien s'il est impossible.
          if (r === null) expect(g.resultat, nom).toBeNull();
          else expect(tailles(g.resultat!), nom).toEqual(alignee(r));
          // Les cases en conflit n'existent que si l'opération est impossible.
          const conflits = [...g.a, ...g.b].filter((c) => c.conflit).length;
          expect(conflits > 0, nom).toBe(r === null);
          if (op === 'plus') {
            // Une dimension qui manque compte pour 1 : la case montre 1, en fantôme.
            const n = Math.max(a.length, b.length);
            const pleine = (f: number[]) => [...new Array<null>(DIMENSIONS_MAX - n).fill(null), ...new Array<number>(n - f.length).fill(1), ...f];
            expect(tailles(g.a), nom).toEqual(pleine(a));
            expect(tailles(g.b), nom).toEqual(pleine(b));
            expect(g.a.filter((c) => c.manque).length, nom).toBe(n - a.length);
            expect(g.b.filter((c) => c.manque).length, nom).toBe(n - b.length);
            // Étirée : une taille 1 (ou absente) sous un résultat plus grand que 1.
            for (const rangee of [g.a, g.b]) {
              rangee.forEach((c, i) => {
                const attendu = r !== null && c.taille === 1 && (alignee(r)[i] ?? 0) > 1;
                expect(c.etire, `${nom}, colonne ${i}`).toBe(attendu);
              });
            }
            expect([...g.a, ...g.b].some((c) => c.souligne), nom).toBe(false);
          } else {
            // Pour @ : les vraies tailles seulement, et deux cases soulignées, l'une dans A, l'autre dans B.
            expect(tailles(g.a), nom).toEqual(alignee(a));
            expect(tailles(g.b), nom).toEqual(alignee(b));
            expect([...g.a, ...g.b].some((c) => c.manque), nom).toBe(false);
            const soulignees = [g.a.findIndex((c) => c.souligne), g.b.findIndex((c) => c.souligne)];
            expect(g.a.filter((c) => c.souligne).length + g.b.filter((c) => c.souligne).length, nom).toBe(2);
            // La dernière de A, et l'avant-dernière de B (la seule d'un vecteur).
            expect(soulignees, nom).toEqual([DIMENSIONS_MAX - 1, DIMENSIONS_MAX - (b.length === 1 ? 1 : 2)]);
          }
        }
      }
    }
  });

  it('chaque explication est une phrase, sans NaN ni undefined, et dit « refuse » ou « il en faut autant » quand c’est impossible', () => {
    for (const a of formes) {
      for (const b of formes) {
        for (const op of operations) {
          const texte = expliquer(a, b, op);
          const nom = `${ecrireForme(a)} ${op} ${ecrireForme(b)}`;
          expect(texte, nom).toMatch(/^[A-Z0-9].*\.$/);
          expect(texte, nom).not.toMatch(/NaN|undefined|null|Infinity| [;:!?]/);
          if (resultat(a, b, op) === null) expect(texte, nom).toMatch(/PyTorch refuse\.$|il en faut autant\.$/);
          else expect(texte, nom).not.toMatch(/refuse|il en faut autant/);
        }
      }
    }
  });
});

describe('atelier des formes : les phrases exactes', () => {
  it('diffusion : ce qui s’étire, et pourquoi PyTorch refuse', () => {
    expect(expliquer([3, 1], [4], 'plus')).toBe(
      'Dans la dernière dimension, le 1 de A s’étire jusqu’à 4. ' +
        `Dans l’avant-dernière dimension, B n’a rien${FINE}: la dimension qui lui manque compte pour 1, et s’étire jusqu’à 3.`,
    );
    expect(expliquer([3, 2], [4, 2], 'plus')).toBe(
      `3 et 4 diffèrent dans l’avant-dernière dimension, et aucun ne vaut 1${FINE}: PyTorch refuse.`,
    );
    // Deux conflits : la phrase nomme celui de droite.
    expect(expliquer([2, 3], [3, 2], 'plus')).toBe(`3 et 2 diffèrent dans la dernière dimension, et aucun ne vaut 1${FINE}: PyTorch refuse.`);
    expect(expliquer([2, 3], [2, 3], 'plus')).toBe(`Rien ne s’étire${FINE}: A + B additionne case par case.`);
    // L'exercice du notebook : (2, 1, 3) + (4, 1) donne (2, 4, 3).
    expect(ecrireResultat(resultat([2, 1, 3], [4, 1], 'plus'))).toBe('(2, 4, 3)');
    expect(expliquer([2, 1, 3], [4, 1], 'plus')).toBe(
      'Dans la dernière dimension, le 1 de B s’étire jusqu’à 3. ' +
        'Dans l’avant-dernière dimension, le 1 de A s’étire jusqu’à 4. ' +
        `Dans la troisième dimension en partant de la droite, B n’a rien${FINE}: la dimension qui lui manque compte pour 1, et s’étire jusqu’à 2.`,
    );
  });

  it('produit : les colonnes de A contre les lignes de B, puis ce que garde le résultat', () => {
    expect(expliquer([2, 3], [2, 3], 'produit')).toBe(`A a 3 colonnes et B 2 lignes${FINE}: pour A @ B, il en faut autant.`);
    expect(expliquer([3, 1], [4], 'produit')).toBe(`A a 1 colonne et B 4 lignes${FINE}: pour A @ B, il en faut autant.`);
    expect(expliquer([2, 3], [3, 4], 'produit')).toBe(
      `A a 3 colonnes et B 3 lignes${FINE}: chaque ligne de A rencontre chaque colonne de B. ` +
        'Le résultat a 2 lignes, comme A, et 4 colonnes, comme B.',
    );
    expect(expliquer([3], [3], 'produit')).toBe(
      `A a 3 colonnes et B 3 lignes${FINE}: chaque ligne de A rencontre chaque colonne de B. ` +
        `A et B sont deux vecteurs${FINE}: le résultat est un nombre seul, leur produit scalaire.`,
    );
    expect(ecrireResultat(resultat([3], [3], 'produit'))).toBe('()');
    expect(expliquer([4], [4, 2], 'produit')).toBe(
      `A a 4 colonnes et B 4 lignes${FINE}: chaque ligne de A rencontre chaque colonne de B. ` +
        `A, un vecteur, compte pour une seule ligne, que le résultat n’a pas${FINE}: il garde 2 colonnes, comme B.`,
    );
    expect(expliquer([3, 1, 4], [4], 'produit')).toBe(
      `A a 4 colonnes et B 4 lignes${FINE}: chaque ligne de A rencontre chaque colonne de B. ` +
        `B, un vecteur, compte pour une seule colonne, que le résultat n’a pas${FINE}: il garde 1 ligne, comme A. ` +
        `B n’a pas de lot${FINE}: il sert à chacune des 3 matrices de A.`,
    );
  });

  it('produit : les lots se diffusent comme pour A + B', () => {
    const debut = `A a 3 colonnes et B 3 lignes${FINE}: chaque ligne de A rencontre chaque colonne de B. Le résultat a 2 lignes, comme A, et 4 colonnes, comme B.`;
    expect(expliquer([5, 2, 3], [5, 3, 4], 'produit')).toBe(`${debut} Et cela pour chacune des 5 matrices du lot.`);
    expect(expliquer([1, 2, 3], [1, 3, 4], 'produit')).toBe(`${debut} Le lot ne compte qu’une matrice.`);
    expect(expliquer([1, 2, 3], [5, 3, 4], 'produit')).toBe(`${debut} Le lot de A, de taille 1, s’étire jusqu’à 5, comme celui de B.`);
    expect(expliquer([2, 3], [5, 3, 4], 'produit')).toBe(`${debut} A n’a pas de lot${FINE}: il sert à chacune des 5 matrices de B.`);
    expect(expliquer([1, 2, 3], [3, 4], 'produit')).toBe(`${debut} B n’a pas de lot, et celui de A ne compte qu’une matrice.`);
    expect(expliquer([2, 2, 3], [5, 3, 4], 'produit')).toBe(
      `A a 3 colonnes et B 3 lignes, comme il faut. Mais leurs lots, 2 et 5, diffèrent, et aucun ne vaut 1${FINE}: PyTorch refuse.`,
    );
  });

  it('la grille de (3, 1) + (4,) : le 1 de A et la dimension qui manque à B s’étirent', () => {
    const g = grille([3, 1], [4], 'plus');
    expect(g.a.map((c) => [c.taille, c.manque, c.etire])).toEqual([
      [null, false, false],
      [3, false, false],
      [1, false, true],
    ]);
    expect(g.b.map((c) => [c.taille, c.manque, c.etire])).toEqual([
      [null, false, false],
      [1, true, true],
      [4, false, false],
    ]);
    expect(tailles(g.resultat!)).toEqual([null, 3, 4]);
  });

  it('la grille de (3, 1) @ (4,) : les deux tailles soulignées diffèrent, en conflit', () => {
    const g = grille([3, 1], [4], 'produit');
    expect(g.a.map((c) => [c.taille, c.souligne, c.conflit])).toEqual([
      [null, false, false],
      [3, false, false],
      [1, true, true],
    ]);
    expect(g.b.map((c) => [c.taille, c.souligne, c.conflit])).toEqual([
      [null, false, false],
      [null, false, false],
      [4, true, true],
    ]);
    expect(g.resultat).toBeNull();
  });

  it('la grille d’un produit à lots : le lot de taille 1 s’étire, des lots différents sont en conflit', () => {
    const etire = grille([1, 2, 3], [5, 3, 4], 'produit');
    expect(etire.a.map((c) => c.etire)).toEqual([true, false, false]);
    expect(etire.b.map((c) => c.etire)).toEqual([false, false, false]);
    expect(etire.b.map((c) => c.souligne)).toEqual([false, true, false]);
    const conflit = grille([2, 2, 3], [5, 3, 4], 'produit');
    expect(conflit.a.map((c) => c.conflit)).toEqual([true, false, false]);
    expect(conflit.b.map((c) => c.conflit)).toEqual([true, false, false]);
  });
});

describe('atelier des formes : l’acquis et le défi', () => {
  it('l’acquis : un produit @ possible avec un A de 3 dimensions', () => {
    expect(gagneFormes([3, 1, 4], [4], 'produit')).toBe(true);
    expect(gagneFormes([2, 3, 4], [4, 5], 'produit')).toBe(true);
    expect(gagneFormes([3, 1, 2], [4], 'produit')).toBe(false);
    expect(gagneFormes([3, 1, 4], [4], 'plus')).toBe(false);
    expect(gagneFormes([3, 4], [4], 'produit')).toBe(false);
  });

  it('le défi : deux formes à 3 dimensions qui se multiplient', () => {
    expect(defiReussi([2, 3, 4], [2, 4, 5], 'produit')).toBe(true);
    expect(defiReussi([1, 3, 4], [6, 4, 5], 'produit')).toBe(true);
    expect(defiReussi([2, 3, 4], [4, 5], 'produit')).toBe(false);
    expect(defiReussi([2, 3, 4], [3, 4, 5], 'produit')).toBe(false);
    expect(defiReussi([2, 3, 4], [2, 4, 5], 'plus')).toBe(false);
    expect(etatDuDefi([2, 3, 4], [2, 4, 5], 'produit')).toBe(DEFI_FORMES_REUSSI);
    expect(DEFI_FORMES_REUSSI).toBe(`Défi réussi${FINE}: deux formes à 3 dimensions qui se multiplient.`);
    expect(etatDuDefi(A_DEPART, B_DEPART, 'plus')).toBe(`Pas encore${FINE}: A et B doivent avoir 3 dimensions.`);
    expect(etatDuDefi([2, 3, 4], [2, 4, 5], 'plus')).toBe(`Pas encore${FINE}: choisis A @ B.`);
    expect(etatDuDefi([2, 3, 4], [3, 4, 5], 'produit')).toBe(`Pas encore${FINE}: A @ B est impossible avec ces deux formes.`);
  });
});
