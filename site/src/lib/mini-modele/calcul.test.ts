// Le jumeau TypeScript du noyau de calcul (projets/mini-modele/mini_modele/calcul.py).
//
// Les attendus sont écrits par le Python : chaque flottant y est un motif de
// 16 chiffres hexadécimaux. Les motifs sont comparés comme des textes, donc un
// écart d'un seul bit (d'un seul « ulp ») fait échouer le test.

import { describe, expect, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-calcul.json';
import {
  cos,
  depuisHex,
  deuxPuissance,
  empreinte,
  empreinteTexte,
  exp,
  Hasard,
  INV_LN2,
  LN2_BAS,
  LN2_HAUT,
  log,
  maximum,
  PI,
  produitScalaire,
  racine,
  somme,
  SQRT_DEMI,
  versHex,
} from './calcul';

const fonctions = { exp, log, cos };

// Les entrées des attendus, refaites comme dans mini_modele/attendus.py.
const FIXES = {
  exp: [
    -745.2, -745.0, -708.5, -50.0, -10.0, -1.0, -0.5, -1e-10, -0.0, 0.0, 1e-300, 1e-10, 0.25, 0.5, 1.0, 2.0,
    10.0, 50.0, 700.0, 709.7, 709.79, 710.0,
  ],
  log: [
    5e-324, 1e-310, 1e-300, 1e-10, 0.1, 0.5, SQRT_DEMI, 0.75, 1.0, 1.0000001, 1.5, 2.0, 10.0, 1e10, 1e300,
    1.7976931348623157e308,
  ],
  cos: [0.0, 1e-8, 0.5, 1.0, PI * 0.25, PI * 0.5, 2.0, 3.0, PI],
};

function tirer(graine: number, n: number, tirage: (h: Hasard) => number): number[] {
  const h = new Hasard(graine);
  return Array.from({ length: n }, () => tirage(h));
}

const ENTREES = {
  exp: [...FIXES.exp, ...tirer(42, 200, (h) => (h.uniforme() - 0.5) * 60)],
  log: [...FIXES.log, ...tirer(43, 200, (h) => h.uniforme() * 100 + 0.001)],
  cos: [...FIXES.cos, ...tirer(44, 100, (h) => h.uniforme() * PI)],
};

/** FNV-1a 32 bits écrit à part, pour vérifier celui de calcul.ts. */
function fnv1aDeReference(octets: Uint8Array): string {
  let h = 0x811c9dc5n;
  for (const o of octets) h = ((h ^ BigInt(o)) * 0x01000193n) % 0x100000000n;
  return h.toString(16).padStart(8, '0');
}

function octetsDepuisHex(h: string): Uint8Array {
  return Uint8Array.from(h.match(/../g) ?? [], (paire) => parseInt(paire, 16));
}

describe('jumeau du Python : attendus-calcul.json, au bit près', () => {
  it('les constantes ont les motifs du Python', () => {
    expect({
      LN2_HAUT: versHex(LN2_HAUT),
      LN2_BAS: versHex(LN2_BAS),
      INV_LN2: versHex(INV_LN2),
      SQRT_DEMI: versHex(SQRT_DEMI),
      PI: versHex(PI),
    }).toEqual(attendus.constantes);
    expect(versHex(LN2_HAUT)).toBe('3fe62e42fee00000');
    expect(versHex(LN2_BAS)).toBe('3dea39ef35793c76');
    expect(versHex(INV_LN2)).toBe('3ff71547652b82fe');
    expect(versHex(SQRT_DEMI)).toBe('3fe6a09e667f3bcd');
    expect(versHex(PI)).toBe('400921fb54442d18');
  });

  it('les entrées sont celles du Python, tirées au hasard de la même façon', () => {
    for (const nom of ['exp', 'log', 'cos'] as const) {
      expect(attendus[nom].map(([x]) => x), nom).toEqual(ENTREES[nom].map(versHex));
    }
  });

  for (const nom of ['exp', 'log', 'cos'] as const) {
    it(`${nom} donne exactement les bits du Python`, () => {
      expect(attendus[nom]).toHaveLength(ENTREES[nom].length);
      for (const [x, y] of attendus[nom]) {
        expect(versHex(fonctions[nom](depuisHex(x))), `${nom}(${depuisHex(x)}), motif ${x}`).toBe(y);
      }
    });
  }

  it('Hasard(1234) tire les mêmes suites que le Python', () => {
    const graine = attendus.hasard.graine;
    expect(graine).toBe(1234);
    const h = new Hasard(graine);
    expect(Array.from({ length: 20 }, () => h.suivant32())).toEqual(attendus.hasard.suivant32);
    expect(tirer(graine, 20, (g) => g.uniforme()).map(versHex)).toEqual(attendus.hasard.uniforme);
    expect(tirer(graine, 20, (g) => g.gaussienne(1.0)).map(versHex)).toEqual(attendus.hasard.gaussienne);
    // Avec l'écart-type 1, la dernière multiplication ne change rien : 0,08 la vérifie aussi.
    expect(tirer(graine, 20, (g) => g.gaussienne(0.08)).map(versHex)).toEqual(attendus.hasard.gaussienne_0_08);
    expect(tirer(graine, 20, (g) => g.entier(10))).toEqual(attendus.hasard.entier_10);
    const liste = Array.from({ length: 20 }, (_, i) => i);
    new Hasard(graine).melanger(liste);
    expect(liste).toEqual(attendus.hasard.melange_20);
  });

  it('les empreintes sont celles du Python', () => {
    expect(empreinte(attendus.empreinte.valeurs.map(depuisHex))).toBe(attendus.empreinte.empreinte);
    expect(attendus.empreinte_texte.texte).toBe('Élodie, Zoé et Maël');
    expect(empreinteTexte(attendus.empreinte_texte.texte)).toBe(attendus.empreinte_texte.empreinte);
  });
});

describe('exp, log et cos : valeurs exactes et cas limites', () => {
  it('donne les valeurs exactes', () => {
    expect(exp(0)).toBe(1);
    expect(log(1)).toBe(0);
    expect(cos(0)).toBe(1);
    expect(cos(PI)).toBe(-1);
    expect(exp(-746)).toBe(0);
    expect(exp(710)).toBe(Infinity);
    expect(log(0)).toBe(-Infinity);
    expect(log(-1)).toBeNaN();
    expect(exp(NaN)).toBeNaN();
  });

  it('traite les infinis, −0 et NaN comme le Python', () => {
    expect(exp(-0)).toBe(1);
    expect(exp(-Infinity)).toBe(0);
    expect(exp(Infinity)).toBe(Infinity);
    expect(log(-0)).toBe(-Infinity);
    expect(log(Infinity)).toBe(Infinity);
    expect(log(NaN)).toBeNaN();
    expect(log(-Infinity)).toBeNaN();
    expect(exp(-745)).toBeGreaterThan(0);
    expect(exp(-745)).toBeLessThan(1e-323);
  });

  it('refuse cos hors de 0 à π, NaN compris', () => {
    expect(() => cos(4)).toThrow('de 0 à π');
    expect(() => cos(4)).toThrow(RangeError);
    for (const x of [-1e-300, -0.5, PI + 1e-15, 4, NaN, Infinity, -Infinity]) {
      expect(() => cos(x), String(x)).toThrow("cos n'est définie ici que de 0 à π (reçu ");
    }
    expect(cos(-0)).toBe(1);
  });
});

describe('sommes, produit scalaire, maximum et racine', () => {
  it('additionne dans l’ordre, sans compensation', () => {
    expect(somme([0.1, 0.2, 0.3])).toBe((0.1 + 0.2) + 0.3);
    expect(somme([])).toBe(0);
    expect(somme([1e16, 1, 1])).toBe(1e16);
    expect(somme(new Float64Array([0.5, 0.25]))).toBe(0.75);
  });

  it('calcule le produit scalaire de deux listes de même longueur', () => {
    expect(produitScalaire([1, 2, 3], [4, 5, 6])).toBe(32);
    expect(produitScalaire([], [])).toBe(0);
    expect(() => produitScalaire([1], [1, 2])).toThrow('même longueur');
    expect(() => produitScalaire([1], [1, 2])).toThrow(RangeError);
  });

  it('garde la première valeur en cas d’égalité, même −0 face à 0', () => {
    expect(maximum([1, 3, 2])).toBe(3);
    expect(maximum([-5])).toBe(-5);
    expect(Object.is(maximum([-0, 0]), -0)).toBe(true);
    expect(Object.is(maximum([0, -0]), 0)).toBe(true);
    expect(() => maximum([])).toThrow('vide');
  });

  it('prend la racine comme Math.sqrt, et refuse un nombre négatif comme le Python', () => {
    expect(racine(2)).toBe(Math.sqrt(2));
    expect(racine(0)).toBe(0);
    expect(racine(Infinity)).toBe(Infinity);
    expect(versHex(racine(-0))).toBe('8000000000000000');
    expect(racine(NaN)).toBeNaN();
    expect(() => racine(-1)).toThrow('négatif');
  });
});

describe('deuxPuissance', () => {
  it('donne 2^k exact pour chaque k de −1074 à 1023', () => {
    for (let k = -1074; k <= 1023; k++) {
      // Motif attendu : l'exposant k + 1023 pour un normal, un seul bit de mantisse pour un sous-normal.
      const motif = k >= -1022 ? BigInt(k + 1023) << 52n : 1n << BigInt(k + 1074);
      expect(versHex(deuxPuissance(k)), `k = ${k}`).toBe(motif.toString(16).padStart(16, '0'));
    }
    expect(deuxPuissance(-1074)).toBe(5e-324);
    expect(deuxPuissance(1023)).toBe(8.98846567431158e307);
  });

  it('refuse un k hors de −1074 à 1023 ou non entier', () => {
    for (const k of [1024, -1075, 1.5, NaN]) {
      expect(() => deuxPuissance(k), String(k)).toThrow('de -1074 à 1023');
    }
  });
});

describe('versHex et depuisHex', () => {
  it('écrit 16 chiffres minuscules, gros-boutistes', () => {
    expect(versHex(-0)).toBe('8000000000000000');
    expect(Object.is(depuisHex(versHex(-0)), -0)).toBe(true);
    expect(versHex(PI)).toBe('400921fb54442d18');
    expect(versHex(1)).toBe('3ff0000000000000');
    expect(versHex(5e-324)).toBe('0000000000000001');
    expect(versHex(Infinity)).toBe('7ff0000000000000');
    expect(versHex(-Infinity)).toBe('fff0000000000000');
    for (const x of [0, 1, -2.5, 0.1, 5e-324, 1.7976931348623157e308, -Infinity]) {
      expect(versHex(depuisHex(versHex(x)))).toBe(versHex(x));
    }
  });

  it('écrit tous les NaN de la même façon, comme le Python', () => {
    expect(versHex(NaN)).toBe('7ff8000000000000');
    expect(versHex(depuisHex('fff8000000000001'))).toBe('7ff8000000000000');
  });

  it('refuse un motif mal formé', () => {
    for (const mauvais of ['3FF0000000000000', '3ff000000000000', '3ff00000000000000', '3ff000000000000g', '']) {
      expect(() => depuisHex(mauvais), mauvais).toThrow('16 chiffres');
    }
  });
});

describe('Hasard', () => {
  it('tire des uniformes dans [0, 1[', () => {
    const tirages = tirer(1234, 10_000, (h) => h.uniforme());
    expect(tirages.every((u) => u >= 0 && u < 1)).toBe(true);
  });

  it('tire des gaussiennes de moyenne 0 et de variance 1', () => {
    const gs = tirer(5, 10_000, (h) => h.gaussienne(1.0));
    expect(Math.abs(somme(gs) / gs.length)).toBeLessThan(0.05);
    expect(Math.abs(somme(gs.map((v) => v * v)) / gs.length - 1)).toBeLessThan(0.05);
  });

  it('tire des entiers de 0 à n − 1, et des suivant32 sur 32 bits', () => {
    expect(new Set(tirer(9, 1_000, (h) => h.entier(10)))).toEqual(new Set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]));
    expect(tirer(3, 1_000, (h) => h.suivant32()).every((v) => Number.isInteger(v) && v >= 0 && v < 4294967296)).toBe(true);
  });

  it('mélange sans perdre ni ajouter d’élément', () => {
    const liste = Array.from({ length: 20 }, (_, i) => i);
    new Hasard(1).melanger(liste);
    expect([...liste].sort((a, b) => a - b)).toEqual(Array.from({ length: 20 }, (_, i) => i));
    expect(liste).not.toEqual(Array.from({ length: 20 }, (_, i) => i));
    // Un tableau typé est mélangé exactement de la même façon.
    const typee = Int32Array.from({ length: 20 }, (_, i) => i);
    new Hasard(1).melanger(typee);
    expect(Array.from(typee)).toEqual(liste);
  });

  it('ramène la graine à 32 bits comme le Python, et refuse une graine non entière', () => {
    expect(new Hasard(-1).suivant32()).toBe(new Hasard(0xffffffff).suivant32());
    expect(new Hasard(4294967296 + 5).suivant32()).toBe(new Hasard(5).suivant32());
    expect(new Hasard(42).suivant32()).not.toBe(new Hasard(43).suivant32());
    expect(() => new Hasard(1.5)).toThrow('entier');
    expect(() => new Hasard(1.5)).toThrow(TypeError);
  });
});

describe('empreintes', () => {
  it('suit FNV-1a 32 bits (valeurs publiées)', () => {
    expect(empreinteTexte('')).toBe('811c9dc5');
    expect(empreinte([])).toBe('811c9dc5');
    expect(empreinteTexte('a')).toBe('e40c292c');
    expect(empreinteTexte('foobar')).toBe('bf9cf968');
    expect(empreinteTexte('é')).toBe(fnv1aDeReference(new TextEncoder().encode('é')));
  });

  it('lit les 8 octets gros-boutistes de chaque flottant, dans l’ordre', () => {
    expect(empreinte([1, -0])).toBe(fnv1aDeReference(octetsDepuisHex('3ff0000000000000' + '8000000000000000')));
    expect(empreinte([1, -0])).not.toBe(empreinte([-0, 1]));
    expect(empreinte(new Float64Array([1, -0]))).toBe(empreinte([1, -0]));
    expect(empreinte([NaN])).toBe(empreinte([depuisHex('fff8000000000000')]));
  });
});
