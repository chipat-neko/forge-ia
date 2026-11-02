import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  effacer,
  lireChapitre,
  nettoyer,
  noterAcquis,
  noterEtape,
  noterPari,
} from './progression';

const CLE = 'forge-ia:progression:v1';
const VIDE = { paris: {}, acquis: [], etapes: [] };

// Faux stockage en mémoire, avec la même interface que localStorage.
function fauxStockage(): Storage {
  const donnees = new Map<string, string>();
  return {
    get length() {
      return donnees.size;
    },
    clear: () => donnees.clear(),
    getItem: (cle: string) => donnees.get(cle) ?? null,
    key: (i: number) => [...donnees.keys()][i] ?? null,
    removeItem: (cle: string) => void donnees.delete(cle),
    setItem: (cle: string, valeur: string) => void donnees.set(cle, String(valeur)),
  };
}

// Stockage dont toutes les opérations échouent (navigation privée, accès refusé).
const casse = {
  getItem() {
    throw new Error('x');
  },
  setItem() {
    throw new Error('x');
  },
} as unknown as Storage;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('progression', () => {
  let faux: Storage;
  beforeEach(() => {
    faux = fauxStockage();
  });

  it("garde les paris, les acquis et les étapes d'un chapitre", () => {
    noterPari('1.3', 'prediction', 1, faux);
    noterAcquis('1.3', 'nombres', faux);
    noterEtape('1.3', 'etape-2', faux);
    expect(lireChapitre('1.3', faux)).toEqual({
      paris: { prediction: 1 },
      acquis: ['nombres'],
      etapes: ['etape-2'],
    });
  });

  it('range tout sous la clé forge-ia:progression:v1, chapitre par chapitre', () => {
    noterPari('1.3', 'prediction', 1, faux);
    noterAcquis('1.4', 'tete', faux);
    const brut = JSON.parse(faux.getItem(CLE) as string);
    expect(Object.keys(brut).sort()).toEqual(['1.3', '1.4']);
    expect(brut['1.3'].paris).toEqual({ prediction: 1 });
  });

  it('garde les chapitres séparés', () => {
    noterPari('1.3', 'a', 0, faux);
    noterPari('1.4', 'a', 2, faux);
    expect(lireChapitre('1.3', faux).paris).toEqual({ a: 0 });
    expect(lireChapitre('1.4', faux).paris).toEqual({ a: 2 });
    expect(lireChapitre('1.5', faux)).toEqual(VIDE);
  });

  it("remplace le choix d'un pari noté deux fois", () => {
    noterPari('1.3', 'prediction', 1, faux);
    noterPari('1.3', 'prediction', 2, faux);
    expect(lireChapitre('1.3', faux).paris).toEqual({ prediction: 2 });
  });

  it('ne note pas deux fois le même acquis ou la même étape', () => {
    noterAcquis('1.3', 'nombres', faux);
    noterAcquis('1.3', 'nombres', faux);
    noterEtape('1.3', 'etape-1', faux);
    noterEtape('1.3', 'etape-1', faux);
    noterEtape('1.3', 'etape-2', faux);
    expect(lireChapitre('1.3', faux).acquis).toEqual(['nombres']);
    expect(lireChapitre('1.3', faux).etapes).toEqual(['etape-1', 'etape-2']);
  });

  it('accepte un identifiant de pari inhabituel, y compris __proto__', () => {
    noterPari('1.3', '__proto__', 1, faux);
    expect(Object.keys(lireChapitre('1.3', faux).paris)).toEqual(['__proto__']);
    expect(({} as Record<string, unknown>).polluee).toBeUndefined();
  });

  it('renvoie un état neuf à chaque lecture (pas de partage avec la mémoire interne)', () => {
    noterPari('1.3', 'p', 1, faux);
    const etat = lireChapitre('1.3', faux);
    etat.paris.p = 99;
    etat.acquis.push('intrus');
    expect(lireChapitre('1.3', faux)).toEqual({ paris: { p: 1 }, acquis: [], etapes: [] });
  });

  describe('stockage indisponible, plein ou corrompu', () => {
    it("ne lève aucune erreur quand la lecture et l'écriture échouent", () => {
      expect(() => noterPari('1.3', 'p', 0, casse)).not.toThrow();
      expect(() => noterAcquis('1.3', 'a', casse)).not.toThrow();
      expect(() => noterEtape('1.3', 'e', casse)).not.toThrow();
      expect(() => lireChapitre('1.3', casse)).not.toThrow();
      expect(() => nettoyer('1.3', {}, casse)).not.toThrow();
      expect(() => effacer('1.3', casse)).not.toThrow();
      expect(() => effacer(undefined, casse)).not.toThrow();
    });

    it('garde la progression en mémoire quand le stockage échoue', () => {
      effacer(undefined, casse);
      noterPari('7.1', 'p', 2, casse);
      noterAcquis('7.1', 'a', casse);
      expect(lireChapitre('7.1', casse)).toEqual({ paris: { p: 2 }, acquis: ['a'], etapes: [] });
      effacer('7.1', casse);
      expect(lireChapitre('7.1', casse)).toEqual(VIDE);
    });

    it("garde la progression en mémoire quand il n'y a pas de stockage du tout", () => {
      effacer(undefined, null);
      expect(() => noterPari('7.2', 'p', 1, null)).not.toThrow();
      noterEtape('7.2', 'e', null);
      expect(lireChapitre('7.2', null)).toEqual({ paris: { p: 1 }, acquis: [], etapes: ['e'] });
      effacer(undefined, null);
      expect(lireChapitre('7.2', null)).toEqual(VIDE);
    });

    it("garde tout en mémoire quand seule l'écriture échoue (stockage plein)", () => {
      const plein = fauxStockage();
      plein.setItem = () => {
        throw new DOMException('quota', 'QuotaExceededError');
      };
      noterPari('7.3', 'a', 0, plein);
      noterPari('7.3', 'b', 1, plein);
      noterAcquis('7.3', 'c', plein);
      expect(lireChapitre('7.3', plein)).toEqual({
        paris: { a: 0, b: 1 },
        acquis: ['c'],
        etapes: [],
      });
    });

    it("revient au stockage dès qu'une écriture réussit de nouveau", () => {
      const capricieux = fauxStockage();
      const vraiSetItem = capricieux.setItem.bind(capricieux);
      capricieux.setItem = () => {
        throw new Error('plein');
      };
      noterPari('7.4', 'a', 0, capricieux);
      capricieux.setItem = vraiSetItem;
      noterPari('7.4', 'b', 1, capricieux);
      expect(lireChapitre('7.4', capricieux).paris).toEqual({ a: 0, b: 1 });
      expect(JSON.parse(capricieux.getItem(CLE) as string)['7.4'].paris).toEqual({ a: 0, b: 1 });
    });

    it("donne un état vide pour un JSON corrompu, puis se répare à l'écriture suivante", () => {
      faux.setItem(CLE, '{pas du json');
      expect(lireChapitre('1.3', faux)).toEqual(VIDE);
      noterPari('1.3', 'p', 1, faux);
      expect(lireChapitre('1.3', faux).paris).toEqual({ p: 1 });
      expect(() => JSON.parse(faux.getItem(CLE) as string)).not.toThrow();
    });

    it('donne un état vide pour un JSON valide mais de mauvaise forme', () => {
      for (const brut of ['null', '[]', '42', '"texte"', '{"1.3": 5}', '{"1.3": []}']) {
        faux.setItem(CLE, brut);
        expect(lireChapitre('1.3', faux)).toEqual(VIDE);
      }
    });

    it('écarte les morceaux de mauvaise forme et garde les bons', () => {
      faux.setItem(
        CLE,
        JSON.stringify({
          '1.3': {
            paris: { bon: 1, texte: 'x', nul: null, liste: [1] },
            acquis: ['nombres', 3, null, 'tete'],
            etapes: 'pas une liste',
          },
        }),
      );
      expect(lireChapitre('1.3', faux)).toEqual({
        paris: { bon: 1 },
        acquis: ['nombres', 'tete'],
        etapes: [],
      });
    });

    it("utilise globalThis.localStorage quand aucun stockage n'est donné", () => {
      vi.stubGlobal('localStorage', faux);
      noterPari('1.3', 'p', 2);
      expect(JSON.parse(faux.getItem(CLE) as string)['1.3'].paris).toEqual({ p: 2 });
      expect(lireChapitre('1.3')).toEqual({ paris: { p: 2 }, acquis: [], etapes: [] });
    });

    it("ne lève aucune erreur quand l'accès à localStorage lui-même est refusé", () => {
      const avant = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
      Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        get() {
          throw new DOMException('refusé', 'SecurityError');
        },
      });
      try {
        effacer(undefined);
        expect(() => noterPari('7.5', 'p', 1)).not.toThrow();
        expect(lireChapitre('7.5')).toEqual({ paris: { p: 1 }, acquis: [], etapes: [] });
        effacer(undefined);
      } finally {
        if (avant) Object.defineProperty(globalThis, 'localStorage', avant);
        else Reflect.deleteProperty(globalThis, 'localStorage');
      }
    });

    it("garde la progression en mémoire quand localStorage n'existe pas", () => {
      vi.stubGlobal('localStorage', undefined);
      effacer(undefined);
      expect(() => noterPari('7.6', 'p', 1)).not.toThrow();
      expect(lireChapitre('7.6')).toEqual({ paris: { p: 1 }, acquis: [], etapes: [] });
      effacer(undefined);
    });
  });

  describe('nettoyer (progression devenue obsolète)', () => {
    it('retire les paris inconnus ou hors limites', () => {
      noterPari('1.3', 'disparu', 0, faux);
      noterPari('1.3', 'prediction', 7, faux);
      expect(nettoyer('1.3', { prediction: 3 }, faux).paris).toEqual({});
      expect(lireChapitre('1.3', faux).paris).toEqual({});
    });

    it("garde les paris valides et renvoie l'état propre", () => {
      noterPari('1.3', 'prediction', 2, faux);
      noterPari('1.3', 'disparu', 0, faux);
      noterAcquis('1.3', 'nombres', faux);
      noterEtape('1.3', 'etape-1', faux);
      expect(nettoyer('1.3', { prediction: 3, autre: 2 }, faux)).toEqual({
        paris: { prediction: 2 },
        acquis: ['nombres'],
        etapes: ['etape-1'],
      });
      expect(lireChapitre('1.3', faux).paris).toEqual({ prediction: 2 });
    });

    it('traite 0 comme valide et le nombre de choix comme hors limites', () => {
      noterPari('1.3', 'a', 0, faux);
      noterPari('1.3', 'b', 3, faux);
      noterPari('1.3', 'c', 2, faux);
      expect(nettoyer('1.3', { a: 3, b: 3, c: 3 }, faux).paris).toEqual({ a: 0, c: 2 });
    });

    it('retire les choix négatifs ou non entiers', () => {
      noterPari('1.3', 'neg', -1, faux);
      noterPari('1.3', 'frac', 1.5, faux);
      expect(nettoyer('1.3', { neg: 3, frac: 3 }, faux).paris).toEqual({});
    });

    it("retire un pari dont l'identifiant n'est qu'un nom hérité d'Object", () => {
      noterPari('1.3', 'toString', 0, faux);
      expect(nettoyer('1.3', {}, faux).paris).toEqual({});
    });

    it('ne touche pas aux autres chapitres', () => {
      noterPari('1.3', 'a', 9, faux);
      noterPari('1.4', 'a', 9, faux);
      nettoyer('1.3', { a: 3 }, faux);
      expect(lireChapitre('1.4', faux).paris).toEqual({ a: 9 });
    });

    it('rend un état vide pour un chapitre sans progression', () => {
      expect(nettoyer('1.9', { a: 3 }, faux)).toEqual(VIDE);
    });

    it("n'écrit rien quand il n'y a rien à retirer", () => {
      noterPari('1.3', 'a', 1, faux);
      const setItem = vi.spyOn(faux, 'setItem');
      nettoyer('1.3', { a: 3 }, faux);
      expect(setItem).not.toHaveBeenCalled();
    });
  });

  describe('effacer', () => {
    it('efface un chapitre sans toucher aux autres', () => {
      noterPari('1.3', 'p', 1, faux);
      noterPari('1.4', 'p', 2, faux);
      effacer('1.3', faux);
      expect(lireChapitre('1.3', faux).paris).toEqual({});
      expect(lireChapitre('1.4', faux).paris).toEqual({ p: 2 });
    });

    it('efface toute la progression sans numéro', () => {
      noterPari('1.3', 'p', 1, faux);
      noterAcquis('1.4', 'a', faux);
      effacer(undefined, faux);
      expect(lireChapitre('1.3', faux)).toEqual(VIDE);
      expect(lireChapitre('1.4', faux)).toEqual(VIDE);
      expect(faux.getItem(CLE)).toBeNull();
    });

    it('ne lève aucune erreur pour un chapitre sans progression', () => {
      expect(() => effacer('1.9', faux)).not.toThrow();
    });
  });
});
