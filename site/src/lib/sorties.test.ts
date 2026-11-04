import { describe, expect, it } from 'vitest';
import { legendeSortie, lireSortie } from './sorties';

describe('lireSortie', () => {
  it('retire la ligne « # relevé le » et en garde la date', () => {
    expect(lireSortie('# relevé le 2026-11-04\nPython 3.12\nfin\n')).toEqual({
      releveLe: '2026-11-04',
      contenu: 'Python 3.12\nfin',
    });
  });

  it('garde tout le reste, sans retour chariot ni lignes vides à la fin', () => {
    expect(lireSortie('a\r\n  b\r\n\r\n')).toEqual({ releveLe: null, contenu: 'a\n  b' });
    expect(lireSortie('# un commentaire\nb\n')).toEqual({ releveLe: null, contenu: '# un commentaire\nb' });
    expect(lireSortie('b\n# relevé le 2026-11-04\n')).toEqual({ releveLe: null, contenu: 'b\n# relevé le 2026-11-04' });
  });
});

describe('legendeSortie', () => {
  it('ajoute la date du relevé en toutes lettres, ou seulement un point', () => {
    expect(legendeSortie('Le diagnostic de ce PC', '2026-11-04')).toBe(
      'Le diagnostic de ce PC, relevée le 4\u00A0novembre 2026.',
    );
    expect(legendeSortie('Le diagnostic de ce PC', null)).toBe('Le diagnostic de ce PC.');
  });

  it('refuse une date qui n’existe pas', () => {
    expect(() => legendeSortie('Le diagnostic de ce PC', '2026-02-30')).toThrow('AAAA-MM-JJ');
  });
});
