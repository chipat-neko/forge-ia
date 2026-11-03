// Les formats français des nombres, partagés par les démos.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { decimalesUtiles, formaterPerte, nombre, pourcent } from './nombres';

const FINE = '\u202F';

describe('nombre', () => {
  it('les milliers séparés par une espace fine, la virgule décimale', () => {
    expect(nombre(12345.678, 1)).toBe('12\u202F345,7');
    expect(nombre(3000)).toBe(`3${FINE}000`);
    expect(nombre(1234)).toBe(`1${FINE}234`);
    expect(nombre(17_855)).toBe(`17${FINE}855`);
    expect(nombre(999)).toBe('999');
  });

  it('exactement le nombre de décimales demandé', () => {
    expect(nombre(2, 3)).toBe('2,000');
    expect(nombre(0.01, 2)).toBe('0,01');
    expect(nombre(0.3, 1)).toBe('0,3');
    expect(nombre(2.4567)).toBe('2');
    expect(nombre(20.6)).toBe('21');
  });

  it('jamais de « e+ » : les très grands nombres restent écrits en entier', () => {
    expect(nombre(1e21)).toBe(['1', ...Array(7).fill('000')].join(FINE));
  });

  it('les négatifs gardent leur signe, mais un zéro arrondi n’en a pas', () => {
    expect(nombre(-5)).toBe('-5');
    expect(nombre(-0)).toBe('0');
    expect(nombre(-0.0001, 3)).toBe('0,000');
    expect(nombre(-0.4)).toBe('0');
    expect(nombre(-0.6)).toBe('-1');
  });

  it('refuse une valeur non finie, ou un nombre de décimales impossible', () => {
    for (const x of [NaN, Infinity, -Infinity]) {
      expect(() => nombre(x), String(x)).toThrow(/n'est pas un nombre fini/);
    }
    for (const d of [-1, 1.5, 21, NaN]) {
      expect(() => nombre(1, d), String(d)).toThrow(/décimales/);
    }
  });
});

describe('pourcent', () => {
  it('une fraction en pourcentage, une espace fine avant %', () => {
    expect(pourcent(0.528, 1)).toBe('52,8\u202F%');
    expect(pourcent(0.528426, 1)).toBe(`52,8${FINE}%`);
    expect(pourcent(0.5)).toBe(`50${FINE}%`);
    expect(pourcent(12.5)).toBe(`1${FINE}250${FINE}%`);
    expect(pourcent(-0.0001, 1)).toBe(`0,0${FINE}%`);
  });

  it('arrondit la valeur décimale exacte (0,0285 donne 2,9 %, pas 2,8 %)', () => {
    // 0,0285 × 100 vaut 2,8499999999999996 en flottant : pourcent ne multiplie pas lui-même.
    expect(pourcent(0.0285, 1)).toBe(`2,9${FINE}%`);
  });

  it('refuse une valeur non finie', () => {
    expect(() => pourcent(NaN)).toThrow(/n'est pas un nombre fini/);
    expect(() => pourcent(Infinity, 1)).toThrow(/n'est pas un nombre fini/);
  });
});

describe('decimalesUtiles', () => {
  it('juste ce qu’il faut pour écrire la valeur, sans zéro inutile', () => {
    expect([0.001, 0.003, 0.01, 0.03, 0.1, 0.3].map((x) => nombre(x, decimalesUtiles(x)))).toEqual([
      '0,001',
      '0,003',
      '0,01',
      '0,03',
      '0,1',
      '0,3',
    ]);
    expect(decimalesUtiles(150)).toBe(0);
    expect(decimalesUtiles(2.5)).toBe(1);
    expect(decimalesUtiles(1 / 3)).toBe(6);
    expect(decimalesUtiles(1 / 3, 2)).toBe(2);
    expect(() => decimalesUtiles(NaN)).toThrow(/n'est pas un nombre fini/);
  });
});

describe('formaterPerte', () => {
  it('trois décimales', () => {
    expect(formaterPerte(3.7419)).toBe('3,742');
    expect(formaterPerte(2.4)).toBe('2,400');
    expect(formaterPerte(1234.5)).toBe(`1${FINE}234,500`);
  });

  it('une erreur qui a explosé s’écrit « hors échelle », jamais NaN ni ∞', () => {
    expect(formaterPerte(NaN)).toBe('hors échelle');
    expect(formaterPerte(Infinity)).toBe('hors échelle');
    expect(formaterPerte(-Infinity)).toBe('hors échelle');
  });
});

describe('le module', () => {
  it('n’importe rien : la page peut s’en servir sans rien embarquer d’autre', () => {
    const source = readFileSync(new URL('./nombres.ts', import.meta.url), 'utf8');
    expect(source).not.toMatch(/^\s*import\b|\bimport\s*\(|\brequire\s*\(/m);
  });
});
