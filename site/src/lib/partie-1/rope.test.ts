// Le jumeau des angles de RoPE retrouve les attendus du Python (section rope de
// projets/1.4-transformer/tests/attendus.json) à 10⁻¹² près : Math.pow n'est pas exacte entre
// moteurs, ni face à la bibliothèque mathématique de Python, donc pas de toStrictEqual ici.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { anglesRope } from './rope';

const { rope } = JSON.parse(readFileSync('../projets/1.4-transformer/tests/attendus.json', 'utf8')) as {
  rope: { dim_tete: number; base: number; positions: number; angles: number[][] };
};

const TOLERANCE = 1e-12;

describe('anglesRope', () => {
  it('retrouve les angles des attendus à 10⁻¹² près, sur les 33 positions', () => {
    expect(rope.angles).toHaveLength(rope.positions);
    for (let position = 0; position < rope.positions; position++) {
      const angles = anglesRope(position, rope.dim_tete, rope.base);
      expect(angles).toHaveLength(rope.dim_tete / 2);
      angles.forEach((angle, i) => {
        const attendu = rope.angles[position][i];
        expect(Math.abs(angle - attendu), `position ${position}, paire ${i}`).toBeLessThanOrEqual(TOLERANCE * Math.max(1, Math.abs(attendu)));
      });
    }
  });

  it('ne tourne pas à la position 0, et tourne le plus vite avec la première paire', () => {
    expect(anglesRope(0, 8, 10000)).toStrictEqual([0, 0, 0, 0]);
    const a = anglesRope(5, 8, 10000);
    expect(a[0]).toBe(5);
    expect(a[0]).toBeGreaterThan(a[1]);
    expect(a[1]).toBeGreaterThan(a[2]);
    expect(a[2]).toBeGreaterThan(a[3]);
  });

  it('refuse une tête impaire, une position négative et une base trop petite', () => {
    expect(() => anglesRope(1, 7, 10000)).toThrow(/pair/);
    expect(() => anglesRope(-1, 8, 10000)).toThrow(/position/);
    expect(() => anglesRope(1, 8, 1)).toThrow(/base/);
  });
});
