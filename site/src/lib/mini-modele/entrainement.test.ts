// L'entraînement : le taux, l'écrêtage, AdamW, et l'Entraineur.
//
// Jumeau de projets/mini-modele/tests/test_entrainement.py. Les attendus sont
// écrits par le Python (tests/attendus-modele.json, clé « entrainement ») :
// 20 pas du préréglage complet (la perte de chaque lot, le taux de chaque pas,
// l'empreinte de tous les paramètres), le planning du taux et une divergence
// doivent être les mêmes, au bit près. Le test long (3 000 pas) est dans
// entrainement-long.test.ts.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-modele.json';
import { depuisHex, empreinte, Hasard, log, versHex } from './calcul';
import { decoder, donneesParDefaut, preparer, tailleVocabulaire } from './donnees';
import {
  Entraineur,
  PRESETS_MINI,
  reglagesMini,
  TAUX_PROPOSES,
  taux,
  verifierReglages,
  type ReglagesMini,
} from './entrainement';
import * as reglages from './reglages';
import { generer, initialiser, nombreParametres, perte } from './modele';

const REGLAGES_TS = new URL('./reglages.ts', import.meta.url);

// Vingt prénoms de deux lettres : 18 vont en entraînement, 2 en validation (comme test_entrainement.py).
const VINGT = ['an', 'bo', 'ci', 'du', 'el', 'fa', 'gu', 'hi', 'in', 'jo', 'ka', 'lu', 'ma', 'ne', 'ol', 'pa', 'qu', 'ro', 'su', 'ti'];

function hex(valeurs: ArrayLike<number>): string[] {
  return Array.from(valeurs, (v) => versHex(v));
}

// Les noms Python des champs des réglages (ceux des attendus).
const NOMS_PYTHON: Record<keyof ReglagesMini, string> = {
  pasTotal: 'pas_total',
  echauffement: 'echauffement',
  tauxMax: 'taux_max',
  lot: 'lot',
  ratioMin: 'ratio_min',
  beta1: 'beta1',
  beta2: 'beta2',
  epsilon: 'epsilon',
  poidsDecroissance: 'poids_decroissance',
  ecretage: 'ecretage',
  graine: 'graine',
  validationTous: 'validation_tous',
  nbValidation: 'nb_validation',
  nbEchantillons: 'nb_echantillons',
};
const ENTIERS = new Set<keyof ReglagesMini>(['pasTotal', 'echauffement', 'lot', 'graine', 'validationTous', 'nbValidation', 'nbEchantillons']);

/** Les réglages comme le Python les écrit : noms Python, entiers tels quels, flottants en motifs. */
function reglagesEnAttendus(r: ReglagesMini): Record<string, number | string> {
  const sortie: Record<string, number | string> = {};
  for (const cle of Object.keys(NOMS_PYTHON) as (keyof ReglagesMini)[]) {
    sortie[NOMS_PYTHON[cle]] = ENTIERS.has(cle) ? r[cle] : versHex(r[cle]);
  }
  return sortie;
}

describe('jumeau du Python : attendus-modele.json, clé « entrainement », au bit près', { timeout: 60_000 }, () => {
  const a = attendus.entrainement;
  const e = new Entraineur(PRESETS_MINI.complet);
  const validation0 = versHex(e.perteValidation());
  const echantillons0 = e.echantillons();
  const pertes: string[] = [];
  const tauxDesPas: string[] = [];
  for (let i = 0; i < a.nb_pas; i++) {
    pertes.push(versHex(e.faireUnPas()));
    tauxDesPas.push(versHex(e.tauxCourant()));
  }

  it('le préréglage et le nombre de pas', () => {
    expect(a.preset).toBe('complet');
    expect(a.nb_pas).toBe(20);
    expect(e.pas).toBe(20);
    expect(e.diverge).toBe(false);
  });

  it('la validation au départ, puis la perte et le taux de chaque pas', () => {
    expect(validation0).toBe(a.validation_0);
    expect(pertes).toEqual(a.pertes);
    expect(tauxDesPas).toEqual(a.taux);
  });

  it('la validation et tous les paramètres après 20 pas', () => {
    expect(versHex(e.perteValidation())).toBe(a.validation_20);
    expect(empreinte(e.params)).toBe(a.params_empreinte_20);
    expect(hex(e.params.slice(0, 8))).toEqual(a.params_premiers_20);
  });

  it('les prénoms inventés au départ et au pas 20', () => {
    expect(echantillons0).toEqual(a.echantillons_0);
    expect(e.echantillons()).toEqual(a.echantillons_20);
  });

  it('le départ est le modèle de la clé « modele » : même validation, mêmes prénoms', () => {
    expect(a.validation_0).toBe(attendus.modele.perte_validation_256);
    expect(a.echantillons_0).toEqual(attendus.modele.generes);
  });

  it('le taux du préréglage complet : montée, sommet, cosinus et fin', () => {
    const r = PRESETS_MINI.complet;
    for (const [pas, motif] of a.taux_planning as [number, string][]) {
      expect(versHex(taux(pas, r.pasTotal, r.tauxMax, r.echauffement, r.ratioMin)), `pas ${pas}`).toBe(motif);
    }
  });

  it('un taux de 1 000 diverge au même pas, avec la même erreur', () => {
    const tauxMax = depuisHex(a.divergence.taux_max);
    expect(tauxMax).toBe(1000);
    const fou = new Entraineur({ ...PRESETS_MINI.complet, tauxMax });
    let derniere = 0;
    while (!fou.diverge && fou.pas < 50) derniere = fou.faireUnPas();
    expect(fou.diverge).toBe(true);
    expect(fou.pas).toBe(a.divergence.pas);
    expect(versHex(derniere)).toBe(a.divergence.perte);
  });

  it('les préréglages et les taux proposés', () => {
    expect(Object.keys(a.presets)).toEqual(Object.keys(PRESETS_MINI));
    for (const [nom, r] of Object.entries(PRESETS_MINI)) {
      expect(reglagesEnAttendus(r), nom).toEqual(a.presets[nom as keyof typeof a.presets]);
    }
    expect(hex(TAUX_PROPOSES)).toEqual(a.taux_proposes);
  });

  it('toutes les clés des attendus sont comparées', () => {
    expect(Object.keys(attendus).sort()).toEqual(['entrainement', 'modele']);
    expect(Object.keys(a).sort()).toEqual(
      [
        'preset',
        'nb_pas',
        'pertes',
        'taux',
        'validation_0',
        'validation_20',
        'params_empreinte_20',
        'params_premiers_20',
        'echantillons_0',
        'echantillons_20',
        'taux_planning',
        'divergence',
        'presets',
        'taux_proposes',
      ].sort(),
    );
  });
});

describe('les réglages', { timeout: 60_000 }, () => {
  it('les taux proposés et les deux préréglages', () => {
    expect(TAUX_PROPOSES).toEqual([0.001, 0.003, 0.01, 0.03, 0.1, 0.3]);
    expect(Object.keys(PRESETS_MINI)).toEqual(['complet', 'avant-gout']);
    expect(PRESETS_MINI.complet).toEqual(reglagesMini(3000, 100));
    expect(PRESETS_MINI['avant-gout']).toEqual(reglagesMini(600, 50));
    expect(TAUX_PROPOSES).toContain(PRESETS_MINI.complet.tauxMax);
    expect(Object.isFrozen(PRESETS_MINI)).toBe(true);
    expect(Object.isFrozen(PRESETS_MINI.complet)).toBe(true);
    expect(Object.isFrozen(TAUX_PROPOSES)).toBe(true);
  });

  it('les valeurs par défaut', () => {
    expect(reglagesMini(10, 2)).toEqual({
      pasTotal: 10,
      echauffement: 2,
      tauxMax: 0.01,
      lot: 8,
      ratioMin: 0.1,
      beta1: 0.9,
      beta2: 0.95,
      epsilon: 1e-8,
      poidsDecroissance: 0.1,
      ecretage: 1.0,
      graine: 1234,
      validationTous: 100,
      nbValidation: 256,
      nbEchantillons: 8,
    });
    expect(reglagesMini(10, 2, { lot: 4 }).lot).toBe(4);
  });

  it('reglages.ts n’importe rien, et entrainement.ts réexporte les mêmes objets', () => {
    const source = readFileSync(REGLAGES_TS, 'utf8');
    expect(source).not.toMatch(/^\s*import\b|\bimport\s*\(|\brequire\s*\(/m);
    expect(TAUX_PROPOSES).toBe(reglages.TAUX_PROPOSES);
    expect(PRESETS_MINI).toBe(reglages.PRESETS_MINI);
    expect(reglagesMini).toBe(reglages.reglagesMini);
    expect(verifierReglages).toBe(reglages.verifierReglages);
  });

  it('refuse les mauvais réglages, avec les messages du Python', () => {
    const mauvais: Partial<Record<keyof ReglagesMini, number>>[] = [
      { pasTotal: 0 },
      { pasTotal: 2.5 },
      { echauffement: -1 },
      { lot: 0 },
      { tauxMax: 0 },
      { tauxMax: -0.01 },
      { tauxMax: Infinity },
      { tauxMax: NaN },
      { ratioMin: 1.5 },
      { beta1: 1 },
      { beta2: -0.1 },
      { epsilon: 0 },
      { poidsDecroissance: -0.1 },
      { ecretage: 0 },
      { graine: -1 },
      { graine: 4294967296 },
      { validationTous: 0 },
      { nbValidation: 0 },
      { nbEchantillons: -1 },
    ];
    for (const champ of mauvais) {
      const nom = Object.keys(champ)[0];
      expect(() => verifierReglages({ ...reglagesMini(10, 2), ...champ }), nom).toThrow(
        new RegExp(`ReglagesMini : ${nom} doit`),
      );
      expect(() => new Entraineur({ ...reglagesMini(10, 2), ...champ }), nom).toThrow(/ReglagesMini/);
    }
    expect(() => verifierReglages({ ...reglagesMini(10, 2), tauxMax: '0.01' as unknown as number })).toThrow(
      /ReglagesMini : tauxMax doit/,
    );
  });

  it('refuse un lot plus grand que la liste d’entraînement', () => {
    expect(() => new Entraineur(reglagesMini(5, 1, { lot: 19 }), preparer(VINGT))).toThrow(
      /lot de 19 prénoms.*18 prénoms d'entraînement/,
    );
  });
});

describe('le taux', { timeout: 60_000 }, () => {
  it('comme forge', () => {
    expect(taux(50, 1000, 1e-3, 100)).toBeCloseTo(5e-4, 15);
    expect(taux(100, 1000, 1e-3, 100)).toBeCloseTo(1e-3, 15);
    expect(taux(550, 1000, 1e-3, 100)).toBeCloseTo(5.5e-4, 15);
    expect(taux(1000, 1000, 1e-3, 100)).toBeCloseTo(1e-4, 15);
  });

  it('monte, puis descend en cosinus jusqu’à ratioMin × tauxMax', () => {
    const r = PRESETS_MINI.complet;
    const valeurs = Array.from({ length: r.pasTotal + 2 }, (_, p) =>
      taux(p, r.pasTotal, r.tauxMax, r.echauffement, r.ratioMin),
    );
    expect(valeurs[0]).toBe(0);
    expect(Math.abs(valeurs[r.echauffement] - r.tauxMax)).toBeLessThanOrEqual(1e-15 * r.tauxMax);
    expect(valeurs[r.pasTotal]).toBe(r.ratioMin * r.tauxMax);
    expect(valeurs[r.pasTotal + 1]).toBe(r.ratioMin * r.tauxMax);
    for (let p = 1; p <= r.echauffement; p++) expect(valeurs[p]).toBeGreaterThan(valeurs[p - 1]);
    for (let p = r.echauffement + 1; p <= r.pasTotal; p++) expect(valeurs[p]).toBeLessThanOrEqual(valeurs[p - 1]);
  });
});

describe('l’Entraineur', { timeout: 60_000 }, () => {
  it('au départ', () => {
    const r = PRESETS_MINI.complet;
    const e = new Entraineur(r);
    const v = tailleVocabulaire(e.donnees.vocabulaire);
    expect(e.config.tailleVocabulaire).toBe(v);
    expect(e.params.length).toBe(nombreParametres(e.config));
    expect(e.params.length).toBe(32 * v + 3328);
    expect(e.pas).toBe(0);
    expect(e.diverge).toBe(false);
    expect(e.tauxCourant()).toBe(0);
    expect(e.limiteDivergence).toBe(3.0 * log(v));
    expect(e.reglages).toEqual(r);
    expect(Object.isFrozen(e.reglages)).toBe(true);
  });

  it('vingt pas : l’erreur baisse, et les prénoms inventés restent dans le vocabulaire', () => {
    const e = new Entraineur(PRESETS_MINI.complet);
    const pertes = Array.from({ length: 20 }, () => e.faireUnPas());
    expect(e.pas).toBe(20);
    expect(e.diverge).toBe(false);
    const moyenne = (t: number[]): number => t.reduce((s, x) => s + x, 0) / t.length;
    expect(moyenne(pertes.slice(-5))).toBeLessThan(moyenne(pertes.slice(0, 5)));
    const lettres = new Set(Array.from(e.donnees.vocabulaire).slice(1));
    for (const p of e.echantillons()) {
      expect(Array.from(p).length).toBeLessThanOrEqual(15);
      expect(Array.from(p).every((c) => lettres.has(c)), p).toBe(true);
    }
  });

  it('100 pas en moins de 3 s', () => {
    const t0 = performance.now();
    const v = new Entraineur(PRESETS_MINI.complet);
    for (let i = 0; i < 100; i++) v.faireUnPas();
    expect(performance.now() - t0).toBeLessThan(3000);
  });

  it('les hasards sont séparés : poids, ordre des prénoms, prénoms inventés', () => {
    const r = PRESETS_MINI.complet;
    const e = new Entraineur(r);
    const voc = e.donnees.vocabulaire;
    expect(hex(e.params)).toEqual(hex(initialiser(e.config, new Hasard(r.graine))));
    const inventes = (graine: number): string[] =>
      generer(e.config, e.params, new Hasard(graine), r.nbEchantillons).map((p) => decoder(p, voc));
    expect(e.echantillons()).toEqual(inventes(r.graine + 2));
    expect(e.echantillons()).toEqual(e.echantillons());
    e.faireUnPas();
    expect(e.echantillons()).toEqual(inventes(r.graine + 3));
    // Inventer des prénoms ou mesurer la validation ne change rien à l'entraînement.
    const a = new Entraineur(r);
    const b = new Entraineur(r);
    a.echantillons();
    a.perteValidation();
    for (let i = 0; i < 3; i++) {
      expect(versHex(a.faireUnPas())).toBe(versHex(b.faireUnPas()));
      a.echantillons();
    }
    expect(empreinte(a.params)).toBe(empreinte(b.params));
  });

  it('la perte de validation : les nbValidation premiers prénoms de validation', () => {
    const r = PRESETS_MINI.complet;
    const e = new Entraineur(r);
    e.faireUnPas();
    expect(versHex(e.perteValidation())).toBe(versHex(perte(e.config, e.params, e.donnees.validation.slice(0, r.nbValidation))));
    const petit = new Entraineur(reglagesMini(5, 1, { lot: 4 }), preparer(VINGT));
    expect(versHex(petit.perteValidation())).toBe(versHex(perte(petit.config, petit.params, petit.donnees.validation)));
  });

  it('l’ordre des lots, et un nouveau mélange quand il ne reste pas assez de prénoms', () => {
    const d = preparer(VINGT);
    expect(d.entrainement.length).toBe(18);
    for (const [lot, groupes] of [
      [4, [[0, 4], [4, 8], [8, 12], [12, 16], [18, 22], [22, 26]]],
      [6, [[0, 6], [6, 12], [12, 18], [18, 24]]],
    ] as const) {
      const r = reglagesMini(50, 5, { lot });
      const e = new Entraineur(r, d);
      // Hasard(graine + 1) mélange [0, …, n − 1] au départ, puis à chaque nouvel ordre.
      const h = new Hasard(r.graine + 1);
      const premier = Array.from({ length: 18 }, (_, i) => i);
      h.melanger(premier);
      const second = Array.from({ length: 18 }, (_, i) => i);
      h.melanger(second);
      expect(premier).not.toEqual(second);
      const ordres = [...premier, ...second]; // le second ordre commence à l'indice 18
      for (const [de, jusqua] of groupes) {
        const attendu = ordres.slice(de, jusqua).map((i) => d.entrainement[i]);
        expect(e['prochainLot'](), `lot ${lot}, ${de}`).toEqual(attendu);
      }
      expect(e.donnees).toBe(d);
    }
  });

  it('un taux trop grand diverge, sans toucher aux paramètres', () => {
    const fou = new Entraineur({ ...PRESETS_MINI.complet, tauxMax: 1000 });
    let copie: string[] = [];
    let perteDuPas = 0;
    for (let i = 0; i < 50 && !fou.diverge; i++) {
      copie = hex(fou.params);
      perteDuPas = fou.faireUnPas();
    }
    expect(fou.diverge).toBe(true);
    // Le premier pas part du hasard (erreur proche de ln V) : il ne diverge pas.
    expect(fou.pas).toBeGreaterThanOrEqual(2);
    expect(!Number.isFinite(perteDuPas) || perteDuPas > fou.limiteDivergence).toBe(true);
    expect(hex(fou.params)).toEqual(copie);
    const pas = fou.pas;
    for (let i = 0; i < 3; i++) expect(versHex(fou.faireUnPas())).toBe(versHex(perteDuPas));
    expect(fou.pas).toBe(pas);
    expect(hex(fou.params)).toEqual(copie);
  });

  it('une erreur non numérique diverge aussi', () => {
    const e = new Entraineur(PRESETS_MINI.complet);
    e.params[0] = NaN; // le plongement du bord, lu au début de chaque prénom
    expect(e.faireUnPas()).toBeNaN();
    expect(e.diverge).toBe(true);
    expect(e.pas).toBe(1);
    expect(e.faireUnPas()).toBeNaN();
    expect(e.pas).toBe(1);
  });

  it('les prénoms par défaut sont ceux de donneesParDefaut', () => {
    expect(new Entraineur(PRESETS_MINI['avant-gout']).donnees).toBe(donneesParDefaut());
  });
});
