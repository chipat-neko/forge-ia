// Les paris du mini-modèle : leurs bonnes réponses sont calculées par le
// moteur, et une phrase devenue fausse arrête la construction.

import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import * as nombres from '../nombres';
import { etatInitial } from './apercu';
import { PRESETS_MINI, TAUX_PROPOSES } from './reglages';
import {
  choixErreurDeDepart,
  choixTauxTropGrand,
  explicationTauxTropGrand,
  formaterPerte,
  PAS_COMPARES,
  questionTauxTropGrand,
  resultatTauxTropGrand,
  TAUX_GRAND,
  VERDICT_ATTENDU,
  type ResultatTauxTropGrand,
} from './paris';

const FINE = '\u202F';

/** La règle de Pari.astro : exactement un choix juste. */
function unSeulJuste(choix: Choix[]): Choix {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes).toHaveLength(1);
  return justes[0];
}

describe('le pari « erreur de départ »', { timeout: 60_000 }, () => {
  it('0, l’erreur du pas 0 (la bonne) et V, dans l’ordre croissant', () => {
    const depart = etatInitial('complet');
    expect(choixErreurDeDepart().map((c) => c.texte)).toEqual(['0', formaterPerte(depart.perteValidation), String(depart.tailleVocabulaire)]);
    expect(choixErreurDeDepart().filter((c) => c.juste)).toHaveLength(1);
    expect(unSeulJuste(choixErreurDeDepart()).texte).toBe(formaterPerte(depart.perteValidation));
  });

  it('formaterPerte est celle de nombres.ts (la page la prend là, sans le moteur)', () => {
    expect(formaterPerte).toBe(nombres.formaterPerte);
  });

  it('garde-fou : une erreur de départ loin de ln V arrête tout', () => {
    const depart = etatInitial('complet');
    expect(() => choixErreurDeDepart({ ...depart, perteValidation: depart.perteHasard + 0.2 })).toThrow(/Exemple devenu faux/);
    expect(() => choixErreurDeDepart({ ...depart, perteValidation: NaN })).toThrow(/Exemple devenu faux/);
    expect(choixErreurDeDepart({ ...depart, perteValidation: depart.perteHasard + 0.1 })).toHaveLength(3);
  });
});

describe('le pari « taux trop grand »', { timeout: 60_000 }, () => {
  it('le juste suit le verdict du moteur, et le verdict est celui que dit le texte', () => {
    const r = resultatTauxTropGrand();
    expect(choixTauxTropGrand().map((c) => c.texte)).toEqual([
      'Il apprend plus vite',
      'À peu près pareil',
      'Il apprend moins bien, ou plus du tout',
    ]);
    expect(choixTauxTropGrand().find((c) => c.juste)?.texte).toBe(
      { 'plus-vite': 'Il apprend plus vite', pareil: 'À peu près pareil', 'moins-bien': 'Il apprend moins bien, ou plus du tout' }[r.verdict],
    );
    unSeulJuste(choixTauxTropGrand());
    // Le texte de la page affirme « moins bien, ou plus du tout » : le moteur doit le confirmer.
    expect(VERDICT_ATTENDU).toBe('moins-bien');
    expect(r.verdict).toBe('moins-bien');
  });

  it('les taux comparés : celui du préréglage complet, et 0,3', () => {
    const r = resultatTauxTropGrand();
    expect(PAS_COMPARES).toBe(200);
    expect(TAUX_GRAND).toBe(0.3);
    expect(TAUX_PROPOSES).toContain(TAUX_GRAND);
    expect(r.tauxNormal).toBe(PRESETS_MINI.complet.tauxMax);
    expect(r.tauxGrand).toBe(0.3);
    expect(Number.isFinite(r.normal)).toBe(true);
    expect(r.normal).toBeLessThan(etatInitial('complet').perteValidation); // le taux normal apprend
  });

  it('calculé une fois et gardé', () => {
    expect(resultatTauxTropGrand()).toBe(resultatTauxTropGrand());
  });

  it('une explosion vaut Infinity, avec son pas ; sinon, pas de pas d’explosion', () => {
    const r = resultatTauxTropGrand();
    if (r.explosionAuPas === null) {
      expect(Number.isFinite(r.grand)).toBe(true);
    } else {
      expect(r.grand).toBe(Infinity);
      expect(Number.isInteger(r.explosionAuPas)).toBe(true);
      expect(r.explosionAuPas).toBeGreaterThan(0);
      expect(r.explosionAuPas).toBeLessThanOrEqual(PAS_COMPARES);
    }
  });

  it('garde-fou : un verdict différent de celui du texte arrête tout', () => {
    const r = resultatTauxTropGrand();
    for (const verdict of ['plus-vite', 'pareil'] as const) {
      const faux: ResultatTauxTropGrand = { ...r, verdict };
      expect(() => choixTauxTropGrand(faux)).toThrow(/Exemple devenu faux/);
      expect(() => explicationTauxTropGrand(faux)).toThrow(/Exemple devenu faux/);
    }
  });

  it('la question calcule le rapport des taux : « trente fois plus grand (0,3) »', () => {
    expect(PRESETS_MINI.complet.tauxMax).toBe(0.01);
    expect(questionTauxTropGrand()).toBe(
      `Avec un taux trente fois plus grand (0,3), que se passe-t-il pendant les 200 premiers pas${FINE}?`,
    );
  });

  it('l’explication cite les nombres calculés, jamais NaN ni Infinity', () => {
    const r = resultatTauxTropGrand();
    const texte = explicationTauxTropGrand();
    expect(texte).not.toMatch(/NaN|Infinity|∞|e\+/);
    expect(texte).not.toMatch(/ [:;?!»]|« /); // espaces fines, jamais d'espace ordinaire
    expect(texte).toContain(formaterPerte(r.normal));
    if (r.explosionAuPas !== null) {
      expect(texte).toContain(`l’erreur a explosé au pas ${r.explosionAuPas}`);
    } else {
      expect(texte).toContain(formaterPerte(r.grand));
    }
  });

  it('l’explication d’une explosion ne cite aucune erreur du grand taux', () => {
    const r: ResultatTauxTropGrand = { ...resultatTauxTropGrand(), grand: Infinity, explosionAuPas: 37, verdict: 'moins-bien' };
    const texte = explicationTauxTropGrand(r);
    expect(texte).toContain(`l’erreur a explosé au pas 37`);
    expect(texte).not.toMatch(/NaN|Infinity|∞|hors échelle/);
  });

  it('l’explication sans explosion cite les deux erreurs', () => {
    const r: ResultatTauxTropGrand = { ...resultatTauxTropGrand(), grand: 3.4567, explosionAuPas: null, verdict: 'moins-bien' };
    const texte = explicationTauxTropGrand(r);
    expect(texte).toContain('3,457');
    expect(texte).toContain(formaterPerte(r.normal));
    expect(texte).not.toMatch(/explosé/);
  });
});
