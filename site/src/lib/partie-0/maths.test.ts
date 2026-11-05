// Le jumeau des maths utiles : maths.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (FICHIERS_PARTIE_0.maths,
// projets/0.2-maths/tests/attendus.json) est écrit par
// `uv run python -m maths_utiles.attendus`. Pour chaque cas des sections
// vecteurs, matrices, descente et tirage, le jumeau doit trouver les mêmes
// nombres, au bit près (toStrictEqual). Les sections pente, chaine, softmax et
// erreur ne sont pas refaites : le site les lit telles quelles.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { Hasard } from '../mini-modele/calcul';
import { versJson } from '../mini-modele/cles-json';
import { FICHIERS_PARTIE_0, SECTIONS_NON_REFAITES, partieRefaite } from './fichiers';
import {
  cosinus,
  descendre,
  erreur,
  EXEMPLE_COMPTES,
  GRAINE_TIRAGE,
  matriceFoisVecteur,
  norme,
  pasPourAtteindre,
  pente,
  probabilites,
  produitScalaire,
  somme,
  TAUX_DESCENTE,
  tirages,
  tirer,
} from './maths';
import { CALCULS_PARTIE_0, refaireMaths } from './parite';

interface CasVecteurs {
  a: number[];
  b: number[];
  produit_scalaire: number;
  norme_a: number;
  norme_b: number;
  cosinus: number | null;
  somme: number[];
}

interface CasMatrice {
  m: number[][];
  v: number[];
  resultat: number[] | null;
  erreur: string | null;
}

interface CasDescente {
  x0: number;
  taux: number;
  positions: number[];
  erreurs: number[];
  pentes: number[];
  pas_pour_atteindre: number | null;
}

interface AttendusMaths {
  vecteurs: CasVecteurs[];
  matrices: CasMatrice[];
  descente: { taux: number[]; nb_pas: number; seuil: number; cas: CasDescente[] };
  tirage: {
    graine_tirage: number;
    exemple_comptes: [string, number][];
    probabilites: number[];
    uniformes: { graine: number; valeurs: number[] };
    tirer: { probas: number[]; u: number; indice: number }[];
    tirages: { n: number; graine: number; comptes: number[] }[];
  };
  messages: { fonction: string; arguments: unknown[]; message: string }[];
  pente: { x: number; exacte: number; approchee: number };
  chaine: { x: number; h: number; exacte: number; approchee: number };
  softmax: { scores: number[]; temperature: number; probabilites: number[] }[];
  erreur: { p: number; erreur: number }[];
}

/** Le fichier d'attendus, lu depuis site/, d'où Vitest est lancé. */
function lireAttendus(): AttendusMaths {
  return JSON.parse(readFileSync(`../${FICHIERS_PARTIE_0.maths}`, 'utf8')) as AttendusMaths;
}

const ATTENDUS = lireAttendus();

/** Le message d'erreur levé par la fonction, ou null si elle n'en lève pas. */
function messageDErreur(f: () => unknown): string | null {
  try {
    f();
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : String(e);
  }
}

describe('jumeau du Python : les attendus partagés de 0.2', () => {
  it('vecteurs : produit scalaire, normes, cosinus et somme de chaque paire', () => {
    expect(ATTENDUS.vecteurs).toHaveLength(169);
    for (const v of ATTENDUS.vecteurs) {
      const nom = `(${v.a}) et (${v.b})`;
      expect(produitScalaire(v.a, v.b), `a · b, ${nom}`).toStrictEqual(v.produit_scalaire);
      expect(norme(v.a), `norme de a, ${nom}`).toStrictEqual(v.norme_a);
      expect(norme(v.b), `norme de b, ${nom}`).toStrictEqual(v.norme_b);
      expect(cosinus(v.a, v.b), `cosinus, ${nom}`).toStrictEqual(v.cosinus);
      expect(somme(v.a, v.b), `somme, ${nom}`).toStrictEqual(v.somme);
    }
  });

  it('matrices : le résultat, ou le même message quand les tailles ne vont pas', () => {
    expect(ATTENDUS.matrices[0]).toStrictEqual({ m: [[1, 2, 3], [0, 1, 0]], v: [1, 1, 1], resultat: [6, 1], erreur: null });
    for (const c of ATTENDUS.matrices) {
      const nom = JSON.stringify([c.m, c.v]);
      if (c.erreur === null) {
        expect(matriceFoisVecteur(c.m, c.v), nom).toStrictEqual(c.resultat);
      } else {
        expect(messageDErreur(() => matriceFoisVecteur(c.m, c.v)), nom).toBe(c.erreur);
      }
    }
    expect(ATTENDUS.matrices.filter((c) => c.erreur !== null).length).toBeGreaterThan(0);
  });

  it('descente : les positions, les erreurs, les pentes et le pas qui passe sous le seuil', () => {
    const d = ATTENDUS.descente;
    expect(TAUX_DESCENTE).toStrictEqual(d.taux);
    expect(d.cas).toHaveLength(4 * TAUX_DESCENTE.length);
    for (const c of d.cas) {
      const nom = `x0 = ${c.x0}, taux = ${c.taux}`;
      const positions = descendre(c.x0, c.taux, d.nb_pas);
      expect(positions, `positions, ${nom}`).toStrictEqual(c.positions);
      expect(positions.map(erreur), `erreurs, ${nom}`).toStrictEqual(c.erreurs);
      expect(positions.map(pente), `pentes, ${nom}`).toStrictEqual(c.pentes);
      expect(pasPourAtteindre(c.x0, c.taux, d.seuil), `pas pour atteindre, ${nom}`).toStrictEqual(
        c.pas_pour_atteindre,
      );
    }
  });

  it('tirage : la graine, les comptes de l’exemple et leurs probabilités sont ceux du Python', () => {
    const t = ATTENDUS.tirage;
    expect(GRAINE_TIRAGE).toBe(t.graine_tirage);
    expect(EXEMPLE_COMPTES).toStrictEqual(t.exemple_comptes);
    expect(probabilites(EXEMPLE_COMPTES)).toStrictEqual(t.probabilites);
  });

  it('new Hasard(1234) redonne les 20 uniformes du Python de 0.2 : la copie de SplitMix32 est celle du mini-modèle', () => {
    const { graine, valeurs } = ATTENDUS.tirage.uniformes;
    expect(graine).toBe(1234);
    expect(valeurs).toHaveLength(20);
    const hasard = new Hasard(1234);
    expect(valeurs.map(() => hasard.uniforme())).toStrictEqual(valeurs);
  });

  it('tirage : chaque tirer et chaque série de tirages', () => {
    const t = ATTENDUS.tirage;
    for (const c of t.tirer) {
      expect(tirer(c.probas, c.u), `tirer(${JSON.stringify(c.probas)}, ${c.u})`).toBe(c.indice);
    }
    const probas = probabilites(EXEMPLE_COMPTES);
    expect(t.tirages.map((c) => [c.n, c.graine])).toStrictEqual(
      [10, 100, 1000, 10_000, 100_000].flatMap((n) => [0, 1, 2].map((i) => [n, GRAINE_TIRAGE + i])),
    );
    for (const c of t.tirages) {
      expect(tirages(probas, c.n, c.graine), `${c.n} tirages, graine ${c.graine}`).toStrictEqual(c.comptes);
    }
  });
});

describe('les messages d’erreur, mot pour mot ceux du Python', () => {
  it('chaque appel refusé de la section messages lève le même message', () => {
    const appels: Record<string, (args: unknown[]) => unknown> = {
      produit_scalaire: ([a, b]) => produitScalaire(a as number[], b as number[]),
      somme: ([a, b]) => somme(a as number[], b as number[]),
      matrice_fois_vecteur: ([m, v]) => matriceFoisVecteur(m as number[][], v as number[]),
      probabilites: ([comptes]) => probabilites(comptes as [string, number][]),
      tirages: ([probas, n, graine]) => tirages(probas as number[], n as number, graine as number),
    };
    expect(ATTENDUS.messages.map((m) => m.fonction)).toStrictEqual([
      'produit_scalaire',
      'produit_scalaire',
      'somme',
      'matrice_fois_vecteur',
      'probabilites',
      'probabilites',
      'tirages',
      'tirages',
    ]);
    for (const m of ATTENDUS.messages) {
      expect(messageDErreur(() => appels[m.fonction](m.arguments)), `${m.fonction}${JSON.stringify(m.arguments)}`).toBe(
        m.message,
      );
    }
  });

  it('des comptes vides ou nuls et une liste d’issues vide s’arrêtent, sans NaN ni case parasite', () => {
    const comptesNuls = 'Aucun compte positif (le total vaut 0)\u202F: il faut au moins un compte plus grand que 0 pour calculer des probabilités.';
    expect(messageDErreur(() => probabilites([]))).toBe(comptesNuls);
    expect(messageDErreur(() => probabilites([['fer', 0], ['feu', 0]]))).toBe(comptesNuls);
    for (const n of [10, 0]) {
      expect(messageDErreur(() => tirages([], n, GRAINE_TIRAGE))).toBe(
        'Aucune issue à tirer\u202F: donne au moins une probabilité.',
      );
    }
  });
});

describe('cas limites du jumeau', () => {
  it('un vecteur nul n’a pas de cosinus, et deux tailles différentes s’arrêtent sur un message', () => {
    expect(cosinus([0, 0], [1, 2])).toBeNull();
    expect(cosinus([3, 1], [0, 0])).toBeNull();
    expect(produitScalaire([], [])).toBe(0);
    expect(messageDErreur(() => produitScalaire([1, 2, 3], [1, 2]))).toBe(
      'Les deux vecteurs n’ont pas la même taille (3 et 2 nombres)\u202F: il en faut autant.',
    );
    expect(messageDErreur(() => somme([1], [1, 2]))).toContain('il en faut autant');
    expect(messageDErreur(() => matriceFoisVecteur([[1, 2, 3, 4]], [1, 2, 3]))).toBe(
      'La matrice a 4 colonnes et le vecteur 3 nombres\u202F: il en faut autant.',
    );
  });

  it('au plus grand taux, la descente s’éloigne du fond sans jamais donner NaN ni l’infini', () => {
    for (const x0 of [-2, 8]) {
      const positions = descendre(x0, TAUX_DESCENTE.at(-1)!, 100);
      expect(positions.every(Number.isFinite)).toBe(true);
      expect(Math.abs(positions.at(-1)! - 3)).toBeGreaterThan(1000);
      expect(positions.map(erreur).every(Number.isFinite)).toBe(true);
    }
    expect(pasPourAtteindre(0, 1.2, 1.01)).toBeNull();
    expect(pasPourAtteindre(3, 0.1, 1.01)).toBe(0);
  });

  it('les constantes ne se modifient pas', () => {
    expect(Object.isFrozen(TAUX_DESCENTE)).toBe(true);
    expect(Object.isFrozen(EXEMPLE_COMPTES)).toBe(true);
    expect(EXEMPLE_COMPTES.every((paire) => Object.isFrozen(paire))).toBe(true);
  });
});

describe('vitesse', () => {
  it('100 000 tirages prennent moins de 200 ms', () => {
    const probas = probabilites(EXEMPLE_COMPTES);
    const t0 = performance.now();
    const comptes = tirages(probas, 100_000, GRAINE_TIRAGE);
    const duree = performance.now() - t0;
    expect(comptes.reduce((s, c) => s + c, 0)).toBe(100_000);
    expect(duree).toBeLessThan(200);
  });
});

describe('parite.ts : la page d’essai refait les sections exactes de 0.2', () => {
  it('le site ne refait ni la pente approchée, ni la chaîne, ni softmax, ni −ln p', () => {
    expect(SECTIONS_NON_REFAITES.maths).toStrictEqual(['pente', 'chaine', 'softmax', 'erreur']);
    // Les sections refaites par la page, plus celles qu'elle ne refait pas, font tout le fichier.
    const refaites = Object.keys(CALCULS_PARTIE_0.maths());
    expect(refaites).toStrictEqual(['vecteurs', 'matrices', 'descente', 'tirage', 'messages']);
    expect([...refaites, ...SECTIONS_NON_REFAITES.maths]).toStrictEqual(Object.keys(ATTENDUS));
  });

  it('par JSON comme la page, le calcul retrouve le fichier sans les sections non refaites', () => {
    const calcule: unknown = JSON.parse(versJson(CALCULS_PARTIE_0.maths()));
    expect(calcule).toStrictEqual(partieRefaite('maths', lireAttendus() as unknown as Record<string, unknown>));
  });

  it('le calcul ne lit que les entrées du fichier : sans ses sorties, il les retrouve toutes', () => {
    // Les sorties du fichier remplacées par null : seul ce que la page recalcule peut les retrouver.
    const a = lireAttendus();
    const entrees = {
      vecteurs: a.vecteurs.map(({ a: va, b }) => ({ a: va, b })),
      matrices: a.matrices.map(({ m, v }) => ({ m, v })),
      descente: { nb_pas: a.descente.nb_pas, seuil: a.descente.seuil, cas: a.descente.cas.map(({ x0, taux }) => ({ x0, taux })) },
      tirage: {
        uniformes: { graine: a.tirage.uniformes.graine, valeurs: a.tirage.uniformes.valeurs.map(() => null) },
        tirer: a.tirage.tirer.map(({ probas, u }) => ({ probas, u })),
        tirages: a.tirage.tirages.map(({ n, graine }) => ({ n, graine })),
      },
      messages: a.messages.map(({ fonction, arguments: args }) => ({ fonction, arguments: args })),
    };
    const refait: unknown = JSON.parse(versJson(refaireMaths(entrees)));
    expect(refait).toStrictEqual(partieRefaite('maths', a as unknown as Record<string, unknown>));
  });

  it('partieRefaite refuse une section non refaite qui manque au fichier', () => {
    expect(() => partieRefaite('maths', { vecteurs: [] })).toThrow(/pente/);
    // Les autres fichiers sont refaits en entier.
    const motSuivant = { textes: [] };
    expect(partieRefaite('mot-suivant', motSuivant)).toStrictEqual(motSuivant);
  });
});
