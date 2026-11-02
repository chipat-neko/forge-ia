import { describe, expect, it } from 'vitest';
import {
  NB_FUSIONS,
  assemblagesIntrouvable,
  caracteresAccueil,
  choixAccueil,
  choixIntrouvable,
  enLettres,
  enumerer,
  jetons404,
  jetonsAccueil,
  jetonsIntrouvable,
} from './exemples';

// Les valeurs des maquettes validées (tâche 11), calculées alors sur une
// copie du moteur : le site doit retrouver les mêmes en les calculant.
describe('exemples de l’accueil et de la 404', () => {
  it('utilise les 165 fusions du chapitre 1.3', () => {
    expect(NB_FUSIONS).toBe(165);
  });

  it('découpe « Construis ton IA de zéro. » en 17 jetons, comme la maquette', () => {
    expect(jetonsAccueil.map((j) => [j.texte, j.id, j.mot])).toEqual([
      ['C', 8, 0], ['ons', 136, 0], ['t', 34, 0], ['r', 32, 0], ['uis', 108, 0],
      [' t', 112, 1], ['on', 49, 1], [' ', 1, 2], ['I', 9, 2], ['A', 7, 2],
      [' de', 76, 3], [' ', 1, 4], ['z', 39, 4], ['é', 42, 4], ['r', 32, 4], ['o', 29, 4],
      ['.', 5, 5],
    ]);
    expect(caracteresAccueil).toBe(25);
  });

  it('propose 5, 17 et 25 jetons, 17 étant juste', () => {
    expect(choixAccueil).toEqual([
      { texte: '5 jetons', juste: false },
      { texte: '17 jetons', juste: true },
      { texte: '25 jetons', juste: false },
    ]);
  });

  it('lit « 404 » comme trois jetons inconnus', () => {
    expect(jetons404.map((j) => [j.texte, j.id])).toEqual([
      ['4', null],
      ['0', null],
      ['4', null],
    ]);
  });

  it('découpe « introuvable » en 8 jetons, avec « ou », « ab » et « le »', () => {
    expect(jetonsIntrouvable.map((j) => [j.texte, j.id])).toEqual([
      ['i', 23], ['n', 28], ['t', 34], ['r', 32], ['ou', 65], ['v', 36], ['ab', 181], ['le', 72],
    ]);
    expect(assemblagesIntrouvable).toEqual(['ou', 'ab', 'le']);
    expect(choixIntrouvable).toEqual([
      { texte: '1 jeton', juste: false },
      { texte: '8 jetons', juste: true },
      { texte: '11 jetons', juste: false },
    ]);
  });
});

describe('enLettres et enumerer', () => {
  it('écrit les petits nombres en lettres', () => {
    expect(enLettres(3)).toBe('trois');
    expect(enLettres(1)).toBe('un');
    expect(enLettres(12)).toBe('12');
  });

  it('énumère à la française', () => {
    expect(enumerer([])).toBe('');
    expect(enumerer(['a'])).toBe('a');
    expect(enumerer(['a', 'b'])).toBe('a et b');
    expect(enumerer(['a', 'b', 'c'])).toBe('a, b et c');
  });
});
