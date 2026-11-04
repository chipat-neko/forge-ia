// La parité : parite.ts refait en TypeScript tous les attendus du Python.
//
// Chaque fonction attendus*() doit rendre exactement le contenu du fichier
// projets/mini-modele/tests/attendus-<nom>.json : mêmes clés (celles du
// Python, en snake_case), mêmes motifs hexadécimaux, au bit près. La page
// d'essai de parité (ControleParite.svelte) appelle les mêmes fonctions dans le
// navigateur, et e2e/parite.spec.ts compare ce qu'elle écrit aux mêmes fichiers.

import { readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { depuisHex, versHex } from './calcul';
import { cheminsDesCles } from './cles-json';
import { detaillerTete } from './exemple-attention';
import {
  attendusAttention,
  attendusCalcul,
  attendusDonnees,
  attendusModele,
  CALCULS_ATTENDUS,
  EXEMPLE_FLOTTANT,
  versJson,
} from './parite';

// Le chemin est relatif à site/, d'où Vitest est lancé (comme e2e/atelier.spec.ts).
const DOSSIER_ATTENDUS = '../projets/mini-modele/tests';

function lireAttendus(nom: string): unknown {
  return JSON.parse(readFileSync(`${DOSSIER_ATTENDUS}/attendus-${nom}.json`, 'utf8'));
}

/** Les noms des fichiers attendus-<nom>.json que le Python a écrits, triés. */
function nomsDesFichiersAttendus(): string[] {
  return readdirSync(DOSSIER_ATTENDUS)
    .flatMap((fichier) => /^attendus-(.+)\.json$/.exec(fichier)?.[1] ?? [])
    .sort();
}

const CALCULS = {
  calcul: attendusCalcul,
  donnees: attendusDonnees,
  modele: attendusModele,
  attention: attendusAttention,
} as const;

describe('parite.ts refait chaque fichier d’attendus du Python', { timeout: 60_000 }, () => {
  it('un calcul par fichier, dans l’ordre de CALCULS en Python', () => {
    expect(Object.keys(CALCULS_ATTENDUS)).toEqual(['calcul', 'donnees', 'modele', 'attention']);
    expect(Object.keys(CALCULS)).toEqual(Object.keys(CALCULS_ATTENDUS));
    for (const [nom, calcul] of Object.entries(CALCULS)) {
      expect(CALCULS_ATTENDUS[nom as keyof typeof CALCULS_ATTENDUS], nom).toBe(calcul);
    }
  });

  it('chaque fichier attendus-<nom>.json du Python est refait ici, et aucun calcul n’est sans fichier', () => {
    // Sans cela, un nouveau fichier d'attendus pourrait échapper à la parité dans les navigateurs :
    // la page d'essai (ControleParite.svelte) ne refait que les calculs de CALCULS_ATTENDUS.
    expect(nomsDesFichiersAttendus(), 'fichiers projets/mini-modele/tests/attendus-*.json').toEqual(
      Object.keys(CALCULS_ATTENDUS).sort(),
    );
  });

  for (const nom of ['calcul', 'donnees', 'modele', 'attention'] as const) {
    it(`attendus-${nom}.json : les mêmes clés, ni plus ni moins, et les mêmes valeurs`, () => {
      const fichier = lireAttendus(nom);
      // Par JSON, comme la page : ce qui ne s'écrit pas en JSON (undefined, NaN) ne passerait pas.
      const calcule = JSON.parse(versJson(CALCULS[nom]()));
      expect(cheminsDesCles(calcule), `clés de attendus-${nom}.json`).toEqual(cheminsDesCles(fichier));
      expect(calcule, `attendus-${nom}.json`).toStrictEqual(fichier);
    });
  }
});

describe('cheminsDesCles', () => {
  it('liste chaque clé, à toute profondeur, tableaux compris', () => {
    expect(cheminsDesCles({ b: 1, a: { c: [{ d: null }, 2] } })).toEqual(['a', 'a.c', 'a.c[0]', 'a.c[0].d', 'a.c[1]', 'b']);
    expect(cheminsDesCles([])).toEqual([]);
    expect(cheminsDesCles('x')).toEqual([]);
  });

  it('voit une clé en trop ou en moins, même profonde', () => {
    const fichier = lireAttendus('modele') as { entrainement: { court: Record<string, unknown> } };
    const abime = structuredClone(fichier);
    abime.entrainement.court.en_trop = 1;
    expect(cheminsDesCles(abime)).not.toEqual(cheminsDesCles(fichier));
    delete abime.entrainement.court.en_trop;
    delete abime.entrainement.court.validation;
    expect(cheminsDesCles(abime)).not.toEqual(cheminsDesCles(fichier));
  });
});

describe('la comparaison voit un seul ulp d’écart', () => {
  it('un bit de moins sur une perte du modèle, et la comparaison échoue', () => {
    const fichier = lireAttendus('modele') as { modele: { perte_lot: string } };
    const calcule = JSON.parse(versJson(attendusModele())) as typeof fichier;
    const motif = calcule.modele.perte_lot;
    expect(depuisHex(motif)).toBeGreaterThan(0);
    // Le flottant positif juste en dessous : le motif moins 1, un ulp d'écart.
    calcule.modele.perte_lot = (BigInt(`0x${motif}`) - 1n).toString(16).padStart(16, '0');
    expect(depuisHex(calcule.modele.perte_lot)).toBeLessThan(depuisHex(motif));
    expect(calcule.modele.perte_lot).not.toBe(fichier.modele.perte_lot);
    expect(() => expect(calcule).toStrictEqual(fichier)).toThrow();
  });
});

describe('l’exemple à virgule de l’attention', () => {
  it('ses entrées sont des nombres à virgule, et sa tête fait 3 de large', () => {
    for (const cle of ['x', 'wq', 'wk', 'wv'] as const) {
      expect(EXEMPLE_FLOTTANT[cle].flat().some((v) => !Number.isInteger(v)), cle).toBe(true);
    }
    expect(EXEMPLE_FLOTTANT.x.length).toBe(5);
    expect(EXEMPLE_FLOTTANT.wq[0].length).toBe(3);
    expect(EXEMPLE_FLOTTANT.wv[0].length).toBe(4);
  });

  it('detaillerTete le calcule avec les fonctions du mini-modèle (aucune valeur recopiée)', () => {
    const e = EXEMPLE_FLOTTANT;
    const d = detaillerTete(e.x, e.wq, e.wk, e.wv);
    const a = (lireAttendus('attention') as { flottant: { requetes: string[][]; sorties: string[][] } }).flottant;
    expect(d.requetes.map((ligne) => ligne.map(versHex))).toEqual(a.requetes);
    expect(d.sorties.map((ligne) => ligne.map(versHex))).toEqual(a.sorties);
  });
});
