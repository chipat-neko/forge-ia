// Le comparateur par point de code vit dans un module sans effet de bord.
//
// Les démos (le Worker du mini-modèle, ses tests) l'importent sans charger le
// tokenizer du chapitre 1.3, que bpe.ts apprend dès qu'on l'importe. bpe.ts le
// ré-exporte : son interface ne change pas. Les cas du comparateur lui-même
// sont dans bpe.test.ts.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { comparerPointsDeCode as depuisBpe } from './bpe';
import { comparerPointsDeCode } from './points-de-code';

describe('points-de-code.ts', () => {
  it('compare par point de code, pas par unité UTF-16', () => {
    expect(['\u{1F642}', '\uFFFD', 'é', 'e', 'z'].sort(comparerPointsDeCode)).toEqual(['e', 'z', 'é', '\uFFFD', '\u{1F642}']);
    expect(comparerPointsDeCode('a', 'ab')).toBeLessThan(0);
    expect(comparerPointsDeCode('ab', 'ab')).toBe(0);
  });

  it('est ré-exporté par bpe.ts, sans que l’interface de bpe.ts change', () => {
    expect(depuisBpe).toBe(comparerPointsDeCode);
  });

  it('n’importe rien : aucun effet de bord au chargement', () => {
    const texte = readFileSync(new URL('./points-de-code.ts', import.meta.url), 'utf8');
    expect(/^\s*import\b|\brequire\(|\bimport\(/m.test(texte)).toBe(false);
  });
});
