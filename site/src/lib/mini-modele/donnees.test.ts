// Les prénoms : vocabulaire, encodage, et partage entraînement/validation.
//
// Jumeau de projets/mini-modele/tests/test_donnees.py. Le partage doit être
// identique à celui du Python, prénom par prénom : les attendus sont écrits
// par le Python (tests/attendus-donnees.json), et les mêmes vingt prénoms sont
// partagés ici à la main, avec le résultat écrit en toutes lettres.

import { readFileSync } from 'node:fs';
import { describe, expect, expectTypeOf, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-donnees.json';
import prenomsBrut from '../../../../projets/mini-modele/donnees/prenoms.txt?raw';
import { comparerPointsDeCode } from '../points-de-code';
import { empreinteTexte, Hasard } from './calcul';
import {
  BORD,
  chargerPrenoms,
  decoder,
  donneesParDefaut,
  encoder,
  GRAINE_PARTAGE,
  preparer,
  prenomsDuTexte,
  tailleVocabulaire,
  vocabulaireDe,
  type Donnees,
} from './donnees';

const FICHIER_PRENOMS = new URL('../../../../projets/mini-modele/donnees/prenoms.txt', import.meta.url);
const CARACTERES_PERMIS = '-abcdefghijklmnopqrstuvwxyzàâäæçèéêëîïôöùûüÿœ';

// Les vingt prénoms de test_donnees.py, et ce que le partage en fait (tiré de Hasard(20261103).melanger).
const VINGT = ['an', 'bo', 'ci', 'du', 'el', 'fa', 'gu', 'hi', 'in', 'jo', 'ka', 'lu', 'ma', 'ne', 'ol', 'pa', 'qu', 'ro', 'su', 'ti'];
const VINGT_VALIDATION = ['bo', 'ti'];
const VINGT_ENTRAINEMENT = ['qu', 'an', 'ka', 'ro', 'ma', 'el', 'ci', 'gu', 'ol', 'du', 'ne', 'in', 'fa', 'lu', 'su', 'jo', 'pa', 'hi'];

function decodes(d: Donnees, suites: readonly (readonly number[])[]): string[] {
  return suites.map((s) => decoder(s, d.vocabulaire));
}

describe('les attendus du Python', () => {
  const d = donneesParDefaut();
  const prenoms = chargerPrenoms();

  it('le nombre de prénoms, l’empreinte du fichier et le vocabulaire', () => {
    expect(prenoms.length).toBe(attendus.nb_prenoms);
    expect(empreinteTexte(prenomsBrut)).toBe(attendus.empreinte_fichier);
    expect(d.vocabulaire).toBe(attendus.vocabulaire);
  });

  it('la taille de l’entraînement et de la validation', () => {
    expect(d.entrainement.length).toBe(attendus.nb_entrainement);
    expect(d.validation.length).toBe(attendus.nb_validation);
  });

  it('les dix premiers prénoms de chaque partie', () => {
    expect(decodes(d, d.entrainement.slice(0, 10))).toEqual(attendus.entrainement_10);
    expect(decodes(d, d.validation.slice(0, 10))).toEqual(attendus.validation_10);
  });

  it('l’empreinte de toute la suite, dans l’ordre', () => {
    expect(empreinteTexte(decodes(d, d.entrainement).join('\n'))).toBe(attendus.empreinte_entrainement);
    expect(empreinteTexte(decodes(d, d.validation).join('\n'))).toBe(attendus.empreinte_validation);
  });

  it('toutes les clés des attendus sont comparées', () => {
    expect(Object.keys(attendus).sort()).toEqual(
      [
        'empreinte_entrainement',
        'empreinte_fichier',
        'empreinte_validation',
        'entrainement_10',
        'nb_entrainement',
        'nb_prenoms',
        'nb_validation',
        'validation_10',
        'vocabulaire',
      ].sort(),
    );
  });
});

describe('le fichier des prénoms', () => {
  it('n’a pas de \\r, finit par \\n et est tel que sur le disque', () => {
    expect(prenomsBrut.includes('\r')).toBe(false);
    expect(prenomsBrut.endsWith('\n')).toBe(true);
    expect(prenomsBrut).toBe(readFileSync(FICHIER_PRENOMS).toString('utf8'));
  });

  it('suit la recette : triés par point de code, sans doublon, de 2 à 15 lettres permises', () => {
    const prenoms = chargerPrenoms();
    expect(prenoms.length).toBeGreaterThanOrEqual(3_000);
    expect(prenoms.length).toBeLessThanOrEqual(30_000);
    expect(prenoms).toEqual([...new Set(prenoms)].sort(comparerPointsDeCode));
    for (const p of prenoms) {
      const lettres = Array.from(p);
      expect(lettres.length >= 2 && lettres.length <= 15, p).toBe(true);
      expect(
        lettres.every((c) => CARACTERES_PERMIS.includes(c)),
        p,
      ).toBe(true);
      expect(p.normalize('NFC'), p).toBe(p);
      expect(p.startsWith('-') || p.endsWith('-') || p.includes('--'), p).toBe(false);
    }
    expect(prenomsBrut).toBe(prenoms.join('\n') + '\n');
  });

  it('contient des prénoms connus, avec leurs accents et leurs traits d’union', () => {
    const prenoms = new Set(chargerPrenoms());
    for (const connu of ['léa', 'zoé', 'mathéo', 'maël', 'anaïs', 'jean-pierre', 'marie-claire', 'françois', 'noël']) {
      expect(prenoms.has(connu), connu).toBe(true);
    }
    expect(prenoms.has("m'hamed")).toBe(false);
    expect(prenoms.has('_prenoms_rares')).toBe(false);
  });
});

describe('prenomsDuTexte', () => {
  it('coupe aux « \\n » et ignore le dernier saut de ligne', () => {
    expect(prenomsDuTexte('ana\nbea\n')).toEqual(['ana', 'bea']);
    expect(prenomsDuTexte('ana\nbea')).toEqual(['ana', 'bea']);
    expect(prenomsDuTexte('')).toEqual([]);
    expect(prenomsDuTexte('\n')).toEqual(['']);
    expect(prenomsDuTexte('ana\n\nbea\n')).toEqual(['ana', '', 'bea']);
    expect(prenomsDuTexte('ana\r\nbea\r\n')).toEqual(['ana\r', 'bea\r']);
  });
});

describe('les constantes', () => {
  it('le bord et la graine', () => {
    expect(BORD).toBe('.');
    expect(GRAINE_PARTAGE).toBe(20261103);
  });
});

describe('vocabulaireDe', () => {
  it('le bord, puis les caractères distincts par point de code', () => {
    expect(vocabulaireDe(['élodie', 'zoé', 'ab'])).toBe('.abdeilozé');
    expect(vocabulaireDe([])).toBe('.');
    expect(vocabulaireDe(['a-b', 'ab'])).toBe('.-ab');
    expect(vocabulaireDe(['œ', 'ÿ', 'z'])).toBe('.zÿœ');
    expect(vocabulaireDe(['\u{1F642}', '\uFFFD'])).toBe('.\uFFFD\u{1F642}');
  });

  it('refuse le bord dans un prénom', () => {
    expect(() => vocabulaireDe(['ana', 'a.b'])).toThrow(/réservé/);
  });
});

describe('encoder et decoder', () => {
  it('encodent entre deux bords, et décodent en les ignorant', () => {
    expect(encoder('ba', '.ab')).toEqual([0, 2, 1, 0]);
    expect(encoder('', '.ab')).toEqual([0, 0]);
    expect(decoder([0, 2, 1, 0], '.ab')).toBe('ba');
    expect(decoder([0, 0, 0], '.ab')).toBe('');
    expect(decoder([2, 0, 1, 2], '.ab')).toBe('bab');
    expect(encoder('\u{1F642}a', '.a\u{1F642}')).toEqual([0, 2, 1, 0]);
    expect(decoder([0, 2, 1, 0], '.a\u{1F642}')).toBe('\u{1F642}a');
  });

  it('refusent un caractère inconnu, et le bord dans un prénom', () => {
    expect(() => encoder('abc', '.ab')).toThrow('Caractère inconnu du vocabulaire : « c »');
    expect(() => encoder('a.b', '.ab')).toThrow('Caractère inconnu du vocabulaire : « . »');
    expect(() => encoder('ø', donneesParDefaut().vocabulaire)).toThrow(/Caractère inconnu/);
  });

  it('decoder refuse un numéro hors du vocabulaire', () => {
    for (const numero of [3, 4, -1, -3, 1.5, Number.NaN, true as unknown as number]) {
      expect(() => decoder([0, 1, numero], '.ab'), String(numero)).toThrow(/Numéro hors du vocabulaire.*de 0 à 2/);
    }
  });

  it('les prénoms par défaut font un aller-retour exact', () => {
    const d = donneesParDefaut();
    expect(decoder(encoder('élodie', d.vocabulaire), d.vocabulaire)).toBe('élodie');
    for (const p of chargerPrenoms().slice(0, 500)) {
      expect(decoder(encoder(p, d.vocabulaire), d.vocabulaire)).toBe(p);
    }
  });
});

describe('preparer', () => {
  it('partage vingt prénoms comme le Python', () => {
    const d = preparer(VINGT);
    expect(d.vocabulaire).toBe(vocabulaireDe(VINGT));
    expect(decodes(d, d.validation)).toEqual(VINGT_VALIDATION);
    expect(decodes(d, d.entrainement)).toEqual(VINGT_ENTRAINEMENT);
    expect(d.connus).toEqual(new Set(VINGT));
  });

  it('refait le partage avec Hasard(GRAINE_PARTAGE) et len / 10', () => {
    // À l'envers, donc pas dans l'ordre trié : le mélange part de l'ordre de la liste donnée.
    const prenoms = [...'abcdefghij'].flatMap((a) => [...'klmnopqrst'].map((b) => a + b)).slice(0, 57).reverse();
    const melanges = [...prenoms];
    new Hasard(GRAINE_PARTAGE).melanger(melanges);
    const d = preparer(prenoms);
    expect(d.validation.length).toBe(5);
    expect(decodes(d, d.validation)).toEqual(melanges.slice(0, 5));
    expect(decodes(d, d.entrainement)).toEqual(melanges.slice(5));
  });

  it('la taille de la validation est len / 10, arrondie vers le bas', () => {
    const tailles = [0, 1, 9, 10, 19, 20, 29].map((n) => preparer(Array<string>(n).fill('ab')).validation.length);
    expect(tailles).toEqual([0, 0, 0, 1, 1, 2, 2]);
  });

  it('ne modifie pas la liste donnée et se répète', () => {
    const prenoms = [...VINGT];
    const d1 = preparer(prenoms);
    expect(prenoms).toEqual(VINGT);
    expect(preparer(prenoms)).toEqual(d1);
  });

  it('partage tous les prénoms, sans perte ni doublon', () => {
    const prenoms = chargerPrenoms();
    const d = preparer(prenoms);
    const entrainement = decodes(d, d.entrainement);
    const validation = decodes(d, d.validation);
    expect([...entrainement, ...validation].sort(comparerPointsDeCode)).toEqual(prenoms);
    expect(d.connus).toEqual(new Set(prenoms));
    expect(validation.some((p) => new Set(entrainement).has(p))).toBe(false);
  });
});

describe('donneesParDefaut', () => {
  it('est mise en cache, et ses numéros sont ceux du vocabulaire', () => {
    const d = donneesParDefaut();
    expect(donneesParDefaut()).toBe(d);
    const toutes = [...d.entrainement, ...d.validation];
    expect(toutes.every((s) => s[0] === 0 && s[s.length - 1] === 0 && !s.slice(1, -1).includes(0))).toBe(true);
    expect(toutes.every((s) => s.length - 1 <= 16)).toBe(true);
    const vus = new Set(toutes.flat());
    expect(vus.size).toBe(Array.from(d.vocabulaire).length);
    expect(Math.max(...vus)).toBe(Array.from(d.vocabulaire).length - 1);
    expect(d.validation.length).toBe(Math.floor(chargerPrenoms().length / 10));
  });
});

describe('tailleVocabulaire', () => {
  it('compte les points de code, comme len() en Python', () => {
    expect(tailleVocabulaire('.ab')).toBe(3);
    expect(tailleVocabulaire('.a\u{1F642}')).toBe(3);
    expect('.a\u{1F642}'.length).toBe(4);
  });

  it('pour les prénoms, V vaut aussi la longueur du texte du vocabulaire', () => {
    // Tous les caractères des prénoms sont sous U+FFFF : une unité UTF-16 chacun. Le modèle lit V
    // avec tailleVocabulaire, et ce test dit que les deux façons de compter tombent d'accord ici.
    const d = donneesParDefaut();
    expect(d.vocabulaire.length).toBe(Array.from(d.vocabulaire).length);
    expect(tailleVocabulaire(d.vocabulaire)).toBe(d.vocabulaire.length);
    expect(tailleVocabulaire(d.vocabulaire)).toBe(Array.from(attendus.vocabulaire).length);
  });
});

describe('les données partagées ne changent pas', () => {
  it('les suites sont figées : un mélange sur place lève une erreur', () => {
    const d = donneesParDefaut();
    expect(Object.isFrozen(d.entrainement) && Object.isFrozen(d.validation)).toBe(true);
    expect(Object.isFrozen(d.entrainement[0]) && Object.isFrozen(d.validation[0])).toBe(true);
    expect(() => (d.entrainement as number[][]).reverse()).toThrow(TypeError);
    expect(() => {
      (d.validation[0] as number[])[0] = 5;
    }).toThrow(TypeError);
  });

  it('et leurs types sont en lecture seule : les mélanger sur place ne compile pas', () => {
    const d = donneesParDefaut();
    expectTypeOf(d.entrainement).toEqualTypeOf<readonly (readonly number[])[]>();
    expectTypeOf(d.validation).toEqualTypeOf<readonly (readonly number[])[]>();
    expectTypeOf(d.connus).toEqualTypeOf<ReadonlySet<string>>();
    // Jamais appelée : seul le contrôle des types (astro check) la lit.
    const melangerSurPlace = (): void => {
      // @ts-expect-error : les suites sont partagées (la valeur par défaut est en cache), on mélange des indices
      new Hasard(1).melanger(d.entrainement);
      // @ts-expect-error : idem pour la validation
      d.validation.reverse();
    };
    expect(typeof melangerSurPlace).toBe('function');
  });
});
