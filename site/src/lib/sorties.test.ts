import { describe, expect, it } from 'vitest';
import { legendeSortie, lireSortie } from './sorties';

const FICHIER = 'projets/0.3-poste/sorties/processeur.txt';

describe('lireSortie', () => {
  it('retire la ligne « # relevé le » et en garde la date', () => {
    expect(lireSortie('# relevé le 2026-11-04\nPython 3.12\nfin\n', FICHIER)).toEqual({
      releveLe: '2026-11-04',
      contenu: 'Python 3.12\nfin',
    });
  });

  it('garde tout le reste, sans retour chariot ni lignes vides à la fin', () => {
    expect(lireSortie('a\r\n  b\r\n\r\n', FICHIER)).toEqual({ releveLe: null, contenu: 'a\n  b' });
    expect(lireSortie('# un commentaire\nb\n', FICHIER)).toEqual({ releveLe: null, contenu: '# un commentaire\nb' });
    expect(lireSortie('b\n# relevé le 2026-11-04\n', FICHIER)).toEqual({
      releveLe: null,
      contenu: 'b\n# relevé le 2026-11-04',
    });
  });

  it('retire un BOM (U+FEFF) en tête du fichier', () => {
    expect(lireSortie('\uFEFF# relevé le 2026-11-04\nPython 3.12\n', FICHIER)).toEqual({
      releveLe: '2026-11-04',
      contenu: 'Python 3.12',
    });
    expect(lireSortie('\uFEFFa\n', FICHIER)).toEqual({ releveLe: null, contenu: 'a' });
  });

  it('n’a rien à afficher pour un fichier vide, ou réduit à sa ligne de date', () => {
    for (const texte of ['', '\n\n', '\uFEFF', ' \n\t\n', '# relevé le 2026-11-04', '# relevé le 2026-11-04\n  \n\n']) {
      expect(lireSortie(texte, FICHIER), JSON.stringify(texte)).toBeNull();
    }
  });

  it('refuse une date de relevé impossible, en nommant le fichier', () => {
    const lire = () => lireSortie('# relevé le 2026-02-30\nPython 3.12\n', FICHIER);
    expect(lire).toThrow(FICHIER);
    expect(lire).toThrow('2026-02-30');
  });
});

describe('legendeSortie', () => {
  it('ajoute la date du relevé en toutes lettres, ou seulement un point', () => {
    expect(legendeSortie('Le diagnostic de ce PC', '2026-11-04')).toBe(
      'Le diagnostic de ce PC, relevée le 4\u00A0novembre 2026.',
    );
    expect(legendeSortie('Le diagnostic de ce PC', null)).toBe('Le diagnostic de ce PC.');
  });
});
