// L'atelier des formes du chapitre 0.4 : deux formes, A et B, de 1 à 3
// dimensions de tailles 1 à 6, et une opération, A + B (la diffusion) ou A @ B
// (le produit matriciel). Ce module dit ce que l'atelier affiche : le résultat,
// la grille des formes alignées par la droite, l'explication en une ou deux
// phrases, et l'état du défi.
//
// Le résultat n'est jamais calculé ici : il vient du jumeau des formes
// (formes.ts), lui-même vérifié contre PyTorch sur toutes les paires de formes
// de 1 à 3 dimensions de tailles 1 à 3. Les phrases et la grille en suivent la
// règle, et atelier-formes.test.ts les vérifie sur toutes ces paires.
//
// Ce module n'importe que formes.ts : l'îlot de l'atelier l'emporte dans le
// navigateur, et un parcours de test peut l'importer (aucun ?raw, aucun .json).

import { ecrireForme, formeDiffusee, formeProduit } from './formes';

const FINE = '\u202F';

/** Le nombre de dimensions de A et de B, de 1 à 3. */
export const DIMENSIONS_MIN = 1;
export const DIMENSIONS_MAX = 3;
/** La taille d'une dimension, de 1 à 6. */
export const TAILLE_MIN = 1;
export const TAILLE_MAX = 6;

/** Les formes à l'arrivée : A = (3, 1) et B = (4,), celles du pari « diffusion ». */
export const A_DEPART: readonly number[] = Object.freeze([3, 1]);
export const B_DEPART: readonly number[] = Object.freeze([4]);

/**
 * Les tailles des trois dimensions possibles, à l'arrivée. Les premières sont
 * celles du départ ; les suivantes apparaissent quand on ajoute une dimension
 * (A, de (3, 1), passe à (3, 1, 2)). Elles sont choisies pour que le défi
 * demande de régler quelque chose : (3, 1, 2) @ (4, 2, 5) est impossible.
 */
export const TAILLES_A: readonly number[] = Object.freeze([...A_DEPART, 2]);
export const TAILLES_B: readonly number[] = Object.freeze([...B_DEPART, 2, 5]);

/** L'opération de l'atelier : A + B, ou A @ B. */
export type Operation = 'plus' | 'produit';

/** La forme réglée : les n premières tailles. */
export function forme(tailles: readonly number[], n: number): number[] {
  if (!Number.isInteger(n) || n < DIMENSIONS_MIN || n > DIMENSIONS_MAX || n > tailles.length) {
    throw new RangeError(`forme : ${n} dimensions, il en faut de ${DIMENSIONS_MIN} à ${DIMENSIONS_MAX}.`);
  }
  return tailles.slice(0, n);
}

/** La forme du résultat, par le jumeau des formes ; null si PyTorch refuse. */
export function resultat(a: readonly number[], b: readonly number[], op: Operation): number[] | null {
  return op === 'plus' ? formeDiffusee(a, b) : formeProduit(a, b);
}

/** Le résultat comme l'atelier l'écrit : « (3, 4) », « () », ou « impossible ». */
export function ecrireResultat(r: readonly number[] | null): string {
  return r === null ? 'impossible' : ecrireForme(r);
}

/** « 3 colonnes », « 1 colonne ». */
function quantite(n: number, mot: string): string {
  return `${n} ${mot}${n > 1 ? 's' : ''}`;
}

/** Le nom d'une dimension, comptée depuis la droite (0 : la dernière). */
const NOMS_DES_DIMENSIONS = [
  'la dernière dimension',
  'l’avant-dernière dimension',
  'la troisième dimension en partant de la droite',
] as const;

/** Une forme alignée par la droite sur n dimensions : null là où une dimension manque. */
function aligner(f: readonly number[], n: number): (number | null)[] {
  return [...new Array<null>(n - f.length).fill(null), ...f];
}

/** Pourquoi A + B a cette forme, ou pourquoi PyTorch refuse. */
function expliquerDiffusion(a: readonly number[], b: readonly number[]): string {
  const n = Math.max(a.length, b.length);
  const rangees = [
    ['A', aligner(a, n)],
    ['B', aligner(b, n)],
  ] as const;
  const r = formeDiffusee(a, b);
  if (r === null) {
    // Le conflit le plus à droite : une dimension qui manque compte pour 1.
    for (let j = 0; j < n; j++) {
      const x = rangees[0][1][n - 1 - j] ?? 1;
      const y = rangees[1][1][n - 1 - j] ?? 1;
      if (x !== y && x !== 1 && y !== 1) {
        return `${x} et ${y} diffèrent dans ${NOMS_DES_DIMENSIONS[j]}, et aucun ne vaut 1${FINE}: PyTorch refuse.`;
      }
    }
  }
  const phrases: string[] = [];
  // De droite à gauche, dans l'ordre où l'on aligne les formes.
  for (let j = 0; j < n; j++) {
    const cible = r![n - 1 - j];
    if (cible === 1) continue;
    for (const [nom, rangee] of rangees) {
      const taille = rangee[n - 1 - j];
      if (taille === null) {
        phrases.push(
          `Dans ${NOMS_DES_DIMENSIONS[j]}, ${nom} n’a rien${FINE}: la dimension qui lui manque compte pour 1, et s’étire jusqu’à ${cible}.`,
        );
      } else if (taille === 1) {
        phrases.push(`Dans ${NOMS_DES_DIMENSIONS[j]}, le 1 de ${nom} s’étire jusqu’à ${cible}.`);
      }
    }
  }
  return phrases.length === 0 ? `Rien ne s’étire${FINE}: A + B additionne case par case.` : phrases.join(' ');
}

/** Pourquoi A @ B a cette forme, ou pourquoi PyTorch refuse. */
function expliquerProduit(a: readonly number[], b: readonly number[]): string {
  // Comme formeProduit : un vecteur à gauche devient une ligne, à droite une colonne.
  const gauche = a.length === 1 ? [1, ...a] : [...a];
  const droite = b.length === 1 ? [...b, 1] : [...b];
  const lignesA = gauche[gauche.length - 2];
  const colonnesA = gauche[gauche.length - 1];
  const lignesB = droite[droite.length - 2];
  const colonnesB = droite[droite.length - 1];
  const tailles = `A a ${quantite(colonnesA, 'colonne')} et B ${quantite(lignesB, 'ligne')}`;
  if (colonnesA !== lignesB) return `${tailles}${FINE}: pour A @ B, il en faut autant.`;
  // Avec 3 dimensions au plus, un lot a au plus une dimension.
  const lotA = gauche.slice(0, -2);
  const lotB = droite.slice(0, -2);
  const lot = formeDiffusee(lotA, lotB);
  if (lot === null) {
    return `${tailles}, comme il faut. Mais leurs lots, ${lotA[0]} et ${lotB[0]}, diffèrent, et aucun ne vaut 1${FINE}: PyTorch refuse.`;
  }
  const phrases = [`${tailles}${FINE}: chaque ligne de A rencontre chaque colonne de B.`];
  if (a.length === 1 && b.length === 1) {
    phrases.push(`A et B sont deux vecteurs${FINE}: le résultat est un nombre seul, leur produit scalaire.`);
  } else if (a.length === 1) {
    phrases.push(
      `A, un vecteur, compte pour une seule ligne, que le résultat n’a pas${FINE}: il garde ${quantite(colonnesB, 'colonne')}, comme B.`,
    );
  } else if (b.length === 1) {
    phrases.push(
      `B, un vecteur, compte pour une seule colonne, que le résultat n’a pas${FINE}: il garde ${quantite(lignesA, 'ligne')}, comme A.`,
    );
  } else {
    phrases.push(`Le résultat a ${quantite(lignesA, 'ligne')}, comme A, et ${quantite(colonnesB, 'colonne')}, comme B.`);
  }
  if (lot.length > 0) {
    const k = lot[0];
    if (lotA.length > 0 && lotB.length > 0) {
      if (lotA[0] === lotB[0]) {
        phrases.push(k > 1 ? `Et cela pour chacune des ${k} matrices du lot.` : 'Le lot ne compte qu’une matrice.');
      } else {
        const [etire, autre] = lotA[0] === 1 ? ['A', 'B'] : ['B', 'A'];
        phrases.push(`Le lot de ${etire}, de taille 1, s’étire jusqu’à ${k}, comme celui de ${autre}.`);
      }
    } else {
      const [sans, avec] = lotA.length > 0 ? ['B', 'A'] : ['A', 'B'];
      phrases.push(
        k > 1
          ? `${sans} n’a pas de lot${FINE}: il sert à chacune des ${k} matrices de ${avec}.`
          : `${sans} n’a pas de lot, et celui de ${avec} ne compte qu’une matrice.`,
      );
    }
  }
  return phrases.join(' ');
}

/** L'explication de l'atelier : ce qui s'étire, ce qui doit être égal, ou pourquoi PyTorch refuse. */
export function expliquer(a: readonly number[], b: readonly number[], op: Operation): string {
  return op === 'plus' ? expliquerDiffusion(a, b) : expliquerProduit(a, b);
}

/** Une case de la grille. */
export interface Case {
  /** La taille ; null pour une case vide. */
  taille: number | null;
  /** A + B : une dimension qui manque, comptée pour 1 (la case montre 1). */
  manque: boolean;
  /** Une taille 1 (ou une dimension qui manque) qui s'étire pour suivre l'autre. */
  etire: boolean;
  /** A @ B : l'une des deux tailles qui doivent être égales. */
  souligne: boolean;
  /** Une taille qui empêche l'opération. */
  conflit: boolean;
}

/** La grille : A, B et le résultat, en DIMENSIONS_MAX colonnes, alignés par la droite. */
export interface Grille {
  a: Case[];
  b: Case[];
  /** Null si l'opération est impossible. */
  resultat: Case[] | null;
}

function caseVide(): Case {
  return { taille: null, manque: false, etire: false, souligne: false, conflit: false };
}

function rangeeDe(f: readonly number[]): Case[] {
  return aligner(f, DIMENSIONS_MAX).map((taille) => ({ ...caseVide(), taille }));
}

/**
 * La grille de l'atelier. Pour A + B, une dimension qui manque montre 1
 * (`manque`), et une taille 1 qui grandit dans le résultat est `etire`. Pour
 * A @ B, seules les vraies tailles sont montrées : la dernière de A et
 * l'avant-dernière de B (la seule d'un vecteur) sont `souligne`, et le lot de
 * taille 1 qui grandit est `etire`. Une taille qui empêche l'opération est
 * `conflit`.
 */
export function grille(a: readonly number[], b: readonly number[], op: Operation): Grille {
  const r = resultat(a, b, op);
  const ga = rangeeDe(a);
  const gb = rangeeDe(b);
  // Colonne de la grille d'une dimension comptée depuis la droite.
  const colonne = (j: number) => DIMENSIONS_MAX - 1 - j;
  if (op === 'plus') {
    const n = Math.max(a.length, b.length);
    for (let j = 0; j < n; j++) {
      const i = colonne(j);
      for (const g of [ga, gb]) {
        if (g[i].taille === null) g[i] = { ...g[i], taille: 1, manque: true };
      }
      const x = ga[i].taille!;
      const y = gb[i].taille!;
      if (r === null) {
        const conflit = x !== y && x !== 1 && y !== 1;
        ga[i].conflit = conflit;
        gb[i].conflit = conflit;
      } else {
        const cible = r[r.length - 1 - j];
        ga[i].etire = x === 1 && cible > 1;
        gb[i].etire = y === 1 && cible > 1;
      }
    }
  } else {
    // La dernière de A ; l'avant-dernière de B, ou la seule d'un vecteur.
    const sa = ga[colonne(0)];
    const sb = gb[colonne(b.length === 1 ? 0 : 1)];
    sa.souligne = true;
    sb.souligne = true;
    if (sa.taille !== sb.taille) {
      sa.conflit = true;
      sb.conflit = true;
    } else if (a.length === DIMENSIONS_MAX && b.length === DIMENSIONS_MAX) {
      // Les lots, quand les deux en ont un : la première colonne.
      const la = ga[0];
      const lb = gb[0];
      if (r === null) {
        la.conflit = true;
        lb.conflit = true;
      } else {
        la.etire = la.taille === 1 && lb.taille! > 1;
        lb.etire = lb.taille === 1 && la.taille! > 1;
      }
    }
  }
  return { a: ga, b: gb, resultat: r === null ? null : rangeeDe(r) };
}

/** L'acquis de l'atelier : un produit A @ B possible, avec un A de 3 dimensions. */
export function gagneFormes(a: readonly number[], b: readonly number[], op: Operation): boolean {
  return op === 'produit' && a.length === DIMENSIONS_MAX && formeProduit(a, b) !== null;
}

/** Le défi : deux formes à 3 dimensions qui se multiplient. */
export function defiReussi(a: readonly number[], b: readonly number[], op: Operation): boolean {
  return op === 'produit' && a.length === DIMENSIONS_MAX && b.length === DIMENSIONS_MAX && formeProduit(a, b) !== null;
}

export const DEFI_FORMES_REUSSI = `Défi réussi${FINE}: deux formes à 3 dimensions qui se multiplient.`;

/** Où en est le défi. */
export function etatDuDefi(a: readonly number[], b: readonly number[], op: Operation): string {
  if (defiReussi(a, b, op)) return DEFI_FORMES_REUSSI;
  if (a.length !== DIMENSIONS_MAX || b.length !== DIMENSIONS_MAX) return `Pas encore${FINE}: A et B doivent avoir 3 dimensions.`;
  if (op !== 'produit') return `Pas encore${FINE}: choisis A @ B.`;
  return `Pas encore${FINE}: A @ B est impossible avec ces deux formes.`;
}
