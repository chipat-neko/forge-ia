// La géométrie de la courbe de perte : l'échelle, la réduction des points et
// le chemin SVG. Le chemin ne contient jamais NaN ni Infinity : un point non
// fini coupe le tracé, une perte trop grande est ramenée au bord.

import { describe, expect, it } from 'vitest';
import {
  cheminCourbe,
  echelleCourbe,
  graduations,
  moyennesParPaquets,
  reduirePoints,
  sortieDeLEchelle,
  taillePaquet,
} from './courbe';

describe('echelleCourbe', () => {
  it('de 0 à 1,25 fois l’erreur du hasard, sur 640 × 280 par défaut', () => {
    expect(echelleCourbe(3000, 3.7)).toEqual({ largeur: 640, hauteur: 280, xMax: 3000, yMin: 0, yMax: 1.25 * 3.7 });
    expect(echelleCourbe(600, 2, 320, 100)).toEqual({ largeur: 320, hauteur: 100, xMax: 600, yMin: 0, yMax: 2.5 });
  });

  it('refuse une échelle vide ou non finie', () => {
    expect(() => echelleCourbe(0, 3.7)).toThrow(/pasTotal/);
    expect(() => echelleCourbe(3000, 0)).toThrow(/perteHasard/);
    expect(() => echelleCourbe(3000, NaN)).toThrow(/perteHasard/);
    expect(() => echelleCourbe(3000, 3.7, 0)).toThrow(/largeur/);
  });
});

describe('reduirePoints', () => {
  it('le test du brief : 3 000 pertes en 600 points', () => {
    expect(reduirePoints(Array(3000).fill(2), 600)).toHaveLength(600);
  });

  it('peu de pertes : un point par pas (le pas p est à l’indice p − 1)', () => {
    expect(reduirePoints([3, 2.5, 2])).toEqual([
      { pas: 1, perte: 3 },
      { pas: 2, perte: 2.5 },
      { pas: 3, perte: 2 },
    ]);
  });

  it('des moyennes par paquets égaux, posées au milieu de leur paquet', () => {
    // 6 pertes, 3 points au plus : des paquets de 2.
    expect(reduirePoints([1, 3, 2, 2, 5, 7], 3)).toEqual([
      { pas: 1.5, perte: 2 },
      { pas: 3.5, perte: 2 },
      { pas: 5.5, perte: 6 },
    ]);
    // 7 pertes, 3 points au plus : des paquets de 3, le dernier incomplet.
    expect(reduirePoints([1, 1, 1, 2, 2, 2, 9], 3)).toEqual([
      { pas: 2, perte: 1 },
      { pas: 5, perte: 2 },
      { pas: 7, perte: 9 },
    ]);
  });

  it('les valeurs non finies sont ignorées ; un paquet tout entier non fini donne NaN', () => {
    const points = reduirePoints([2, NaN, 4, Infinity, NaN, -Infinity], 3);
    expect(points[0]).toEqual({ pas: 1.5, perte: 2 });
    expect(points[1]).toEqual({ pas: 3.5, perte: 4 });
    expect(points[2].pas).toBe(5.5);
    expect(points[2].perte).toBeNaN();
  });

  it('aucune perte : aucun point ; maxPoints doit être un entier positif', () => {
    expect(reduirePoints([])).toEqual([]);
    expect(() => reduirePoints([1], 0)).toThrow(/maxPoints/);
    expect(() => reduirePoints([1], 2.5)).toThrow(/maxPoints/);
  });
});

describe('moyennesParPaquets et taillePaquet', () => {
  it('des paquets de taille fixe : la courbe ne change pas de lissage en cours d’entraînement', () => {
    expect(taillePaquet(3000, 600)).toBe(5);
    expect(taillePaquet(600, 600)).toBe(1);
    expect(taillePaquet(601, 600)).toBe(2);
    const debut = moyennesParPaquets([1, 2, 3, 4, 5, 6, 7], 5);
    expect(debut).toEqual([
      { pas: 3, perte: 3 },
      { pas: 6.5, perte: 6.5 },
    ]);
    // Les mêmes paquets complets, avec plus de pertes : le début ne bouge pas.
    expect(moyennesParPaquets([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)[0]).toEqual(debut[0]);
    expect(() => moyennesParPaquets([1], 0)).toThrow(/taille/);
  });
});

describe('cheminCourbe', () => {
  const e = echelleCourbe(3000, 3.7);

  it('les tests du brief', () => {
    expect(
      cheminCourbe(
        [
          { pas: 0, perte: 1 },
          { pas: 1, perte: NaN },
          { pas: 2, perte: 1 },
        ],
        e,
      ).d.match(/M/g),
    ).toHaveLength(2);
    expect(cheminCourbe([{ pas: 0, perte: 99 }], e)).toMatchObject({ horsEchelle: true });
    expect(cheminCourbe([{ pas: 0, perte: Infinity }], e).d).not.toMatch(/NaN|Infinity/);
  });

  it('des coordonnées à une décimale : le pas va à droite, l’erreur vers le haut', () => {
    const { d, horsEchelle } = cheminCourbe(
      [
        { pas: 0, perte: 0 },
        { pas: 1500, perte: 1.25 * 3.7 * 0.5 },
        { pas: 3000, perte: 1.25 * 3.7 },
      ],
      e,
    );
    expect(d).toBe('M0.0,280.0L320.0,140.0L640.0,0.0');
    expect(horsEchelle).toBe(false);
    expect(cheminCourbe([{ pas: 1, perte: 3 }], e).d).toBe('M0.2,98.4');
  });

  it('un point fini et un point au-dessus du haut : le tracé existe, ramené au bord, et il est hors échelle', () => {
    const { d, horsEchelle } = cheminCourbe(
      [
        { pas: 100, perte: 3 },
        { pas: 200, perte: 50 },
      ],
      e,
    );
    expect(horsEchelle).toBe(true);
    expect(d).toBe('M21.3,98.4L42.7,0.0');
    expect(d).not.toMatch(/NaN|Infinity/);
  });

  it('une erreur infinie est hors échelle, sans entrer dans le tracé ; NaN coupe seulement', () => {
    const infini = cheminCourbe(
      [
        { pas: 100, perte: 3 },
        { pas: 200, perte: Infinity },
      ],
      e,
    );
    expect(infini).toEqual({ d: 'M21.3,98.4', horsEchelle: true });
    const nan = cheminCourbe(
      [
        { pas: 100, perte: 3 },
        { pas: 200, perte: NaN },
      ],
      e,
    );
    expect(nan).toEqual({ d: 'M21.3,98.4', horsEchelle: false });
  });

  it('une erreur sous zéro est ramenée au bas, sans être hors échelle (une erreur n’est jamais négative)', () => {
    expect(cheminCourbe([{ pas: 0, perte: -1 }], e)).toEqual({ d: 'M0.0,280.0', horsEchelle: false });
  });

  it('un pas non fini coupe aussi le tracé, et rien ne sort du cadre en largeur', () => {
    const { d } = cheminCourbe(
      [
        { pas: 0, perte: 1 },
        { pas: NaN, perte: 1 },
        { pas: 6000, perte: 1 },
      ],
      e,
    );
    expect(d).toBe('M0.0,219.5M640.0,219.5');
  });

  it('aucun point : un chemin vide', () => {
    expect(cheminCourbe([], e)).toEqual({ d: '', horsEchelle: false });
  });
});

describe('graduations', () => {
  it('des valeurs rondes de 0 au maximum, au plus nbMax intervalles', () => {
    expect(graduations(3000, 3)).toEqual([0, 1000, 2000, 3000]);
    expect(graduations(600, 3)).toEqual([0, 200, 400, 600]);
    expect(graduations(1.25 * Math.LN10 * 1.6, 5)).toEqual([0, 1, 2, 3, 4]);
    expect(graduations(100, 4)).toEqual([0, 50, 100]);
    expect(graduations(0.9, 4)).toEqual([0, 0.2, 0.4, 0.6, 0.8]);
  });

  it('refuse un maximum ou un nombre d’intervalles impossible', () => {
    expect(() => graduations(0, 3)).toThrow(/maximum/);
    expect(() => graduations(Infinity, 3)).toThrow(/maximum/);
    expect(() => graduations(10, 0)).toThrow(/nbMax/);
  });
});

describe('sortieDeLEchelle : le premier pas hors échelle, lu sur les pertes brutes', () => {
  const e = echelleCourbe(3000, 3.7); // yMax = 4,625

  it('un pas qui explose dans un paquet : la moyenne le noie, pas sortieDeLEchelle', () => {
    const pertes = Array<number>(30).fill(2);
    pertes[20] = 50; // le pas 21, dans le premier paquet de 25 pas : (24 × 2 + 50) / 25 = 3,92
    // Les moyennes par paquets de 25 restent sous le haut du cadre…
    expect(moyennesParPaquets(pertes, 25).every((p) => p.perte <= e.yMax)).toBe(true);
    expect(cheminCourbe(moyennesParPaquets(pertes, 25), e).horsEchelle).toBe(false);
    // … mais la perte brute du pas 21 en sort.
    expect(sortieDeLEchelle(pertes, [], e)).toBe(21);
  });

  it('un NaN ou un infini sort de l’échelle, même ignoré par les moyennes', () => {
    expect(sortieDeLEchelle([2, 2, NaN, 2], [], e)).toBe(3);
    expect(cheminCourbe(moyennesParPaquets([2, 2, NaN, 2], 25), e).horsEchelle).toBe(false);
    expect(sortieDeLEchelle([2, Infinity], [], e)).toBe(2);
    expect(sortieDeLEchelle([2, -Infinity], [], e)).toBe(2);
  });

  it('les points de validation comptent aussi ; c’est le premier pas qui gagne', () => {
    const validations = [
      { pas: 0, perte: 3.6 },
      { pas: 100, perte: Infinity },
    ];
    expect(sortieDeLEchelle(Array<number>(150).fill(2), validations, e)).toBe(100);
    const pertes = Array<number>(150).fill(2);
    pertes[49] = 9;
    expect(sortieDeLEchelle(pertes, validations, e)).toBe(50);
  });

  it('tout dans le cadre, y compris yMax pile : null', () => {
    expect(sortieDeLEchelle([3, e.yMax, 0], [{ pas: 0, perte: 3.6 }], e)).toBeNull();
    expect(sortieDeLEchelle([], [], e)).toBeNull();
  });
});
