// Le jumeau du mot suivant : mot-suivant.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (FICHIERS_PARTIE_0['mot-suivant'],
// projets/0.1-python/tests/attendus.json) est écrit par
// `uv run python -m mot_suivant.attendus`. Pour chaque texte de référence, les
// mots, les suivants triés, les prédictions et les suites (avec leur reprise)
// doivent être les mêmes, à l'identique (toStrictEqual).

import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { versJson } from '../mini-modele/cles-json';
import {
  compterSuivants,
  decouperMots,
  generer,
  LETTRES,
  predire,
  premiereReprise,
  suivantsTries,
} from './mot-suivant';
import { FICHIERS_PARTIE_0 } from './fichiers';
import { CALCULS_PARTIE_0, FICHIERS_PARTIE_0 as FICHIERS_DE_PARITE } from './parite';
import { TEXTE_DE_DEPART } from './texte-0-1';

interface SuiteAttendue {
  depart: string;
  longueur: number;
  suite: string[];
  reprise: number | null;
}

interface TexteAttendu {
  texte: string;
  mots: string[];
  suivants: [string, [string, number][]][];
  predictions: [string, string | null][];
  suites: SuiteAttendue[];
}

/** Un fichier du dépôt, lu depuis site/, d'où Vitest est lancé. */
function lire(chemin: string): string {
  return readFileSync(`../${chemin}`, 'utf8');
}

const ATTENDUS = JSON.parse(lire(FICHIERS_PARTIE_0['mot-suivant'])) as { textes: TexteAttendu[] };

/** Un texte court pour les messages d'échec (le texte du projet fait plus de mille caractères). */
function nom(texte: string): string {
  return JSON.stringify(texte.length > 40 ? `${texte.slice(0, 40)}…` : texte);
}

describe('jumeau du Python : les attendus partagés', () => {
  it('le fichier a ses dix textes, dont le texte du projet en premier', () => {
    expect(ATTENDUS.textes).toHaveLength(10);
    expect(ATTENDUS.textes[0].texte).toBe(TEXTE_DE_DEPART);
    expect(TEXTE_DE_DEPART).toBe(readFileSync('../projets/0.1-python/donnees/texte.txt', 'utf8'));
    expect(TEXTE_DE_DEPART).not.toContain('\r');
  });

  for (const t of ATTENDUS.textes) {
    it(`même découpage, mêmes suivants, mêmes prédictions et mêmes suites : ${nom(t.texte)}`, () => {
      const mots = decouperMots(t.texte);
      expect(mots, 'mots').toStrictEqual(t.mots);
      const suivants = compterSuivants(mots);
      expect(
        [...suivants].map(([mot, compte]) => [mot, suivantsTries(compte)]),
        'suivants triés',
      ).toStrictEqual(t.suivants);
      expect(
        t.predictions.map(([mot]) => [mot, predire(suivants, mot)]),
        'prédictions',
      ).toStrictEqual(t.predictions);
      // Les prédictions couvrent chaque mot du texte, dans l'ordre de première apparition.
      expect(t.predictions.map(([mot]) => mot)).toStrictEqual([...new Set(mots)]);
      for (const s of t.suites) {
        const suite = generer(suivants, s.depart, s.longueur);
        expect(suite, `suite depuis « ${s.depart} », ${s.longueur} mots`).toStrictEqual(s.suite);
        expect(premiereReprise(suite), `reprise depuis « ${s.depart} », ${s.longueur} mots`).toStrictEqual(s.reprise);
      }
    });
  }
});

describe('decouperMots', () => {
  it('met en minuscules, garde . ! ? comme mots, et sépare sur tout le reste', () => {
    expect(decouperMots('Le forgeron frappe, le fer !')).toStrictEqual(['le', 'forgeron', 'frappe', 'le', 'fer', '!']);
    expect(decouperMots('L’enclume')).toStrictEqual(['l’enclume']);
    expect(decouperMots('Salut 🙂 ! 2026')).toStrictEqual(['salut', '!']);
    expect(decouperMots('')).toStrictEqual([]);
  });

  it('a les mêmes lettres que le Python', () => {
    const python = readFileSync('../projets/0.1-python/mot_suivant/mots.py', 'utf8');
    expect(python).toContain(`LETTRES = "${LETTRES}"`);
  });
});

describe('predire, generer, premiereReprise', () => {
  it('départage les égalités par point de code, et rend null quand rien ne suit', () => {
    const s = compterSuivants(['a', 'c', 'a', 'b']);
    expect(predire(s, 'a')).toBe('b');
    expect(predire(s, 'b')).toBeNull();
    // « z » (U+007A) passe avant « é » (U+00E9) ; « 🙂 » (U+1F642) après « ｚ » (U+FF5A, z pleine
    // chasse), alors que le « < » de JavaScript, qui compare les unités UTF-16 (D83D contre FF5A),
    // mettrait « 🙂 » devant.
    expect(predire(compterSuivants(['x', 'é', 'x', 'z']), 'x')).toBe('z');
    expect(predire(compterSuivants(['x', '🙂', 'x', 'ｚ']), 'x')).toBe('ｚ');
  });

  it('trie les suivants par compte décroissant, puis par point de code', () => {
    const s = compterSuivants(['le', 'fer', 'le', 'feu', 'le', 'fer', 'le', 'été', 'le', 'axe']);
    expect(suivantsTries(s.get('le') ?? new Map())).toStrictEqual([
      ['fer', 2],
      ['axe', 1],
      ['feu', 1],
      ['été', 1],
    ]);
  });

  it('génère, s’arrête quand rien ne suit, et trouve la reprise', () => {
    const s = compterSuivants('a b a b a'.split(' '));
    expect(generer(s, 'a', 5)).toStrictEqual(['a', 'b', 'a', 'b', 'a']);
    expect(generer(s, 'z', 5)).toStrictEqual(['z']);
    expect(generer(s, 'a', 0)).toStrictEqual([]);
    expect(premiereReprise(['a', 'b', 'a'])).toBe(2);
    expect(premiereReprise(['a', 'b'])).toBeNull();
    expect(generer(compterSuivants(['un', 'deux', 'trois']), 'un', 12)).toStrictEqual(['un', 'deux', 'trois']);
  });
});

describe('vitesse', () => {
  it('découper et compter 10 000 caractères prend moins de 200 ms', () => {
    const texte = TEXTE_DE_DEPART.repeat(Math.ceil(10_000 / TEXTE_DE_DEPART.length)).slice(0, 10_000);
    expect(texte).toHaveLength(10_000);
    const t0 = performance.now();
    const suivants = compterSuivants(decouperMots(texte));
    const duree = performance.now() - t0;
    expect(suivants.size).toBeGreaterThan(0);
    expect(duree).toBeLessThan(200);
  });
});

describe('parite.ts : la page d’essai de la Partie 0 refait les attendus', () => {
  it('un calcul par fichier de FICHIERS_PARTIE_0, et chaque fichier existe', () => {
    expect(Object.keys(CALCULS_PARTIE_0)).toContain('mot-suivant');
    expect(Object.keys(FICHIERS_PARTIE_0)).toStrictEqual(Object.keys(CALCULS_PARTIE_0));
    // parite.ts ré-exporte la même liste : la page et les tests lisent la même.
    expect(FICHIERS_DE_PARITE).toBe(FICHIERS_PARTIE_0);
    for (const chemin of Object.values(FICHIERS_PARTIE_0)) expect(existsSync(`../${chemin}`), chemin).toBe(true);
  });

  for (const [nom, chemin] of Object.entries(FICHIERS_PARTIE_0)) {
    it(`${nom} : le calcul refait ${chemin}, par JSON comme la page`, () => {
      // Par JSON, comme la page : ce qui ne s'écrit pas en JSON (undefined, NaN) ne passerait pas.
      const calcule: unknown = JSON.parse(versJson(CALCULS_PARTIE_0[nom]()));
      expect(calcule).toStrictEqual(JSON.parse(lire(chemin)));
    });
  }
});
