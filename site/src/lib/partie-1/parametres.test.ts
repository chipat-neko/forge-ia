// Le jumeau de la répartition des paramètres retrouve exactement les attendus du Python
// (projets/1.4-transformer/tests/attendus.json, section repartitions), pour chaque preset de
// forge. Des entiers : toStrictEqual.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CLES_FORGE, PRESETS_FORGE, nombreParametres } from '../calculateur/ton-ia';
import { nombresDeTetes, repartitionParametres } from './parametres';

interface LigneAttendue {
  preset: string;
  taille_vocabulaire: number;
  dim: number;
  couches: number;
  tetes: number;
  longueur_contexte: number;
  plongement: number;
  attention: number;
  mlp: number;
  normes: number;
  total: number;
}

const ATTENDUS = (JSON.parse(readFileSync('../projets/1.4-transformer/tests/attendus.json', 'utf8')) as { repartitions: LigneAttendue[] }).repartitions;

describe('repartitionParametres', () => {
  it('couvre les cinq presets de forge, dans l’ordre', () => {
    expect(ATTENDUS.map((a) => a.preset)).toStrictEqual([...CLES_FORGE]);
  });

  for (const cle of CLES_FORGE) {
    it(`retrouve les attendus du Python pour « ${cle} »`, () => {
      const attendu = ATTENDUS.find((a) => a.preset === cle)!;
      const forme = PRESETS_FORGE[cle];
      // La forme du calculateur est celle du Python.
      expect([forme.vocabulaire, forme.dim, forme.couches, forme.tetes, forme.contexte]).toStrictEqual([
        attendu.taille_vocabulaire,
        attendu.dim,
        attendu.couches,
        attendu.tetes,
        attendu.longueur_contexte,
      ]);
      const r = repartitionParametres(forme);
      expect(r).toStrictEqual({ plongement: attendu.plongement, attention: attendu.attention, mlp: attendu.mlp, normes: attendu.normes });
      expect(r.plongement + r.attention + r.mlp + r.normes).toBe(attendu.total);
      expect(attendu.total).toBe(forme.parametres);
      expect(attendu.total).toBe(
        nombreParametres({ tailleVocabulaire: forme.vocabulaire, dim: forme.dim, couches: forme.couches, tetes: forme.tetes, longueurContexte: forme.contexte }),
      );
    });
  }

  it('garde les familles dans l’ordre du Python', () => {
    expect(Object.keys(repartitionParametres(PRESETS_FORGE.mini))).toStrictEqual(['plongement', 'attention', 'mlp', 'normes']);
  });

  it('ne dépend pas du nombre de têtes', () => {
    const a = repartitionParametres({ ...PRESETS_FORGE.petit, tetes: 4 });
    const b = repartitionParametres({ ...PRESETS_FORGE.petit, tetes: 16 });
    expect(a).toStrictEqual(b);
  });

  it('refuse une forme que forge refuserait', () => {
    expect(() => repartitionParametres({ ...PRESETS_FORGE.mini, tetes: 7 })).toThrow(/divisible/);
    expect(() => repartitionParametres({ ...PRESETS_FORGE.mini, dim: 12, tetes: 4 })).toThrow(/pair/);
  });
});

describe('nombresDeTetes', () => {
  it('ne garde que les t où dim % t === 0 et (dim / t) % 2 === 0', () => {
    expect(nombresDeTetes(8)).toStrictEqual([1, 2, 4]);
    expect(nombresDeTetes(12)).toStrictEqual([1, 2, 3, 6]);
    expect(nombresDeTetes(7)).toStrictEqual([]);
    expect(nombresDeTetes(2)).toStrictEqual([1]);
  });

  it('propose, pour chaque preset, un nombre de têtes que forge accepte, dont celui du preset', () => {
    for (const cle of CLES_FORGE) {
      const f = PRESETS_FORGE[cle];
      const propositions = nombresDeTetes(f.dim);
      expect(propositions).toContain(f.tetes);
      for (const t of propositions) {
        expect(() => repartitionParametres({ ...f, tetes: t })).not.toThrow();
      }
    }
  });

  it('exclut exactement les nombres que forge refuserait', () => {
    const dim = 48;
    const accepte = (t: number): boolean => {
      try {
        repartitionParametres({ ...PRESETS_FORGE.mini, dim, tetes: t });
        return true;
      } catch {
        return false;
      }
    };
    const attendu = Array.from({ length: dim }, (_, i) => i + 1).filter(accepte);
    expect(nombresDeTetes(dim)).toStrictEqual(attendu);
  });

  it('refuse une largeur qui n’est pas un entier positif', () => {
    expect(() => nombresDeTetes(0)).toThrow(RangeError);
    expect(() => nombresDeTetes(2.5)).toThrow(RangeError);
  });
});
