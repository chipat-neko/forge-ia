import { describe, expect, it } from 'vitest';
import { libelleDesLignes, lignesVisees } from './lignes';

describe('lignesVisees', () => {
  it('lit un numéro', () => {
    expect(lignesVisees('7')).toEqual([7]);
  });

  it('lit une plage, bornes comprises', () => {
    expect(lignesVisees('2-4')).toEqual([2, 3, 4]);
  });

  it('lit une liste séparée par des espaces ou des virgules', () => {
    expect(lignesVisees('1 5')).toEqual([1, 5]);
    expect(lignesVisees('1, 3-4,6')).toEqual([1, 3, 4, 6]);
  });

  it('ne répète pas une ligne visée deux fois', () => {
    expect(lignesVisees('2-3 3')).toEqual([2, 3]);
  });

  it('refuse ce qui n’est pas un numéro ou une plage', () => {
    for (const faux of ['', ' ', 'a', '0', '-3', '3-', '4-2', '1.5', '1--2']) {
      expect(() => lignesVisees(faux), `« ${faux} »`).toThrow('Lignes invalides');
    }
  });
});

describe('libelleDesLignes', () => {
  it('écrit « Ligne » au singulier et « Lignes » au pluriel', () => {
    expect(libelleDesLignes('7')).toBe('Ligne 7');
    expect(libelleDesLignes('2-6')).toBe('Lignes 2 à 6');
    expect(libelleDesLignes('1 5')).toBe('Lignes 1 et 5');
    expect(libelleDesLignes('1, 3-4, 6')).toBe('Lignes 1, 3 à 4 et 6');
  });
});
