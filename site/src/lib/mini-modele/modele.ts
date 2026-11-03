// Le mini-transformer : une couche d'attention causale et un MLP, qui lit des prénoms.
//
// C'est le jumeau exact de projets/mini-modele/mini_modele/modele.py : mêmes
// fonctions, mêmes boucles, même ordre des opérations (les noms passent en
// camelCase ; les noms des matrices et des attendus restent ceux du Python).
// Les attendus (tests/attendus-modele.json, clé « modele ») le prouvent au
// bit près dans modele.test.ts : la perte d'un lot, tout son gradient, la
// perte de validation et les prénoms inventés.
//
// Le modèle lit un prénom numéro par numéro, et à chaque position il donne un
// score à chaque numéro du vocabulaire. Ses pièces sont celles des grands
// modèles, en tout petit : un plongement par numéro et un par position, une
// attention causale à plusieurs têtes, un MLP (élargir, ReLU, revenir), une
// norme RMS sans poids avant l'attention, avant le MLP et avant la sortie,
// des connexions résiduelles, et une tête de lecture séparée du plongement.
//
// Tous les paramètres vivent dans un seul Float64Array (voir disposition). La
// passe arrière est écrite à la main, dans l'ordre inverse exact de la passe
// avant. Ce fichier est vérifié par sources.test.ts.

import { melangerValeurs, poidsAttention, softmax } from './attention';
import { exp, Hasard, log, maximum, produitScalaire, racine, somme } from './calcul';

export const ECART_TYPE_INIT = 0.08; // l'écart-type des paramètres au départ
export const EPSILON_NORME = 1e-5; // ajouté sous la racine de la norme : jamais de division par 0
export const LONGUEUR_GENEREE_MAX = 15; // un prénom inventé s'arrête à 15 caractères, comme ceux de la liste

/** Une place dans le tableau des paramètres : [début, lignes, colonnes], rangée ligne par ligne. */
export type Place = readonly [debut: number, lignes: number, colonnes: number];

/** Les matrices, dans l'ordre du tableau des paramètres (les noms du Python). */
export type NomMatrice =
  | 'plongement'
  | 'positions'
  | 'requetes'
  | 'cles'
  | 'valeurs'
  | 'sortie_attention'
  | 'mlp_haut'
  | 'mlp_bas'
  | 'tete_de_lecture';

/** La forme du mini-modèle. Seule la taille du vocabulaire change d'une liste de mots à l'autre. */
export interface ConfigMini {
  readonly tailleVocabulaire: number;
  readonly dim: number;
  readonly tetes: number;
  readonly contexte: number;
  readonly largeurMlp: number;
}

/**
 * La configuration du mini-modèle pour un vocabulaire de tailleVocabulaire
 * numéros : dim 16, 4 têtes, contexte 16, MLP de 64, sauf ce que autres change.
 * Elle est vérifiée comme ConfigMini en Python, et figée.
 */
export function configMini(
  tailleVocabulaire: number,
  autres: Partial<Omit<ConfigMini, 'tailleVocabulaire'>> = {},
): ConfigMini {
  const c = {
    tailleVocabulaire,
    dim: autres.dim ?? 16,
    tetes: autres.tetes ?? 4,
    contexte: autres.contexte ?? 16,
    largeurMlp: autres.largeurMlp ?? 64,
  };
  for (const [nom, valeur] of Object.entries(c)) {
    if (!Number.isInteger(valeur) || valeur < 1) {
      throw new RangeError(`ConfigMini : ${nom} doit être un entier positif (reçu ${valeur}).`);
    }
  }
  if (c.dim % c.tetes !== 0) {
    throw new RangeError(
      `ConfigMini : dim (${c.dim}) doit être un multiple de tetes (${c.tetes}), pour couper ` +
        'chaque vecteur en têtes de même taille. Change dim ou tetes (par exemple dim=16 et tetes=4).',
    );
  }
  return Object.freeze(c);
}

/** Le nombre de composantes de chaque tête : dim / tetes (4 avec les valeurs par défaut). */
export function tailleTete(c: ConfigMini): number {
  return Math.floor(c.dim / c.tetes);
}

/**
 * La place de chaque matrice dans le tableau des paramètres, dans l'ordre du tableau.
 *
 * La case (i, j) d'une matrice rangée à [début, lignes, colonnes] est params[début + i × colonnes + j].
 */
export function disposition(c: ConfigMini): Record<NomMatrice, Place> {
  const formes: [NomMatrice, number, number][] = [
    ['plongement', c.tailleVocabulaire, c.dim],
    ['positions', c.contexte, c.dim],
    ['requetes', c.dim, c.dim],
    ['cles', c.dim, c.dim],
    ['valeurs', c.dim, c.dim],
    ['sortie_attention', c.dim, c.dim],
    ['mlp_haut', c.dim, c.largeurMlp],
    ['mlp_bas', c.largeurMlp, c.dim],
    ['tete_de_lecture', c.dim, c.tailleVocabulaire],
  ];
  const places = {} as Record<NomMatrice, Place>;
  let debut = 0;
  for (const [nom, lignes, colonnes] of formes) {
    places[nom] = [debut, lignes, colonnes];
    debut += lignes * colonnes;
  }
  return places;
}

/** V·d + T·d + 4d² + 2·d·m + d·V : 32·V + 3 328 avec les valeurs par défaut. */
export function nombreParametres(c: ConfigMini): number {
  const v = c.tailleVocabulaire;
  const d = c.dim;
  const t = c.contexte;
  const m = c.largeurMlp;
  return v * d + t * d + 4 * d * d + 2 * d * m + d * v;
}

/** Les paramètres de départ : une gaussienne d'écart-type ECART_TYPE_INIT pour chacun, dans l'ordre. */
export function initialiser(c: ConfigMini, hasard: Hasard): Float64Array {
  const params = new Float64Array(nombreParametres(c));
  for (let i = 0; i < params.length; i++) {
    params[i] = hasard.gaussienne(ECART_TYPE_INIT);
  }
  return params;
}

/** x · W, pour la matrice W rangée à place : y[j] = Σ_i x[i] × W[i][j], sommé par i croissant. */
export function produit(x: ArrayLike<number>, params: Float64Array, place: Place): number[] {
  const [debut, lignes, colonnes] = place;
  const y = new Array<number>(colonnes).fill(0.0);
  for (let i = 0; i < lignes; i++) {
    const xi = x[i];
    const base = debut + i * colonnes;
    for (let j = 0; j < colonnes; j++) {
      y[j] += xi * params[base + j];
    }
  }
  return y;
}

/**
 * La norme RMS, sans poids : y_i = x_i × inv, avec inv = 1 / √(moyenne des x_i² + EPSILON_NORME).
 *
 * Renvoie y, et inv pour la passe arrière.
 */
export function norme(x: ArrayLike<number>): [number[], number] {
  const inv = 1.0 / racine(somme(Array.from(x, (v) => v * v)) / x.length + EPSILON_NORME);
  return [Array.from(x, (v) => v * inv), inv];
}

/** u s'il est positif, 0 sinon. */
export function relu(u: number): number {
  return u > 0.0 ? u : 0.0;
}

/** Ce que la passe avant a calculé à une position : la perte lit logits, la passe arrière relit le reste. */
export interface Position {
  readonly h0: number[];
  readonly a: number[];
  readonly invA: number;
  readonly q: number[];
  readonly k: number[];
  readonly v: number[];
  /** poids[tête][j] : le poids donné à la position j, pour j de 0 à t. */
  readonly poids: number[][];
  readonly o: number[];
  readonly h1: number[];
  readonly b: number[];
  readonly invB: number;
  readonly u: number[];
  readonly r: number[];
  readonly h2: number[];
  readonly f: number[];
  readonly invF: number;
  readonly logits: number[];
}

/** Chaque numéro est un entier du vocabulaire, de 0 à V − 1. */
export function verifierNumeros(c: ConfigMini, ids: readonly number[]): void {
  for (const numero of ids) {
    if (!Number.isInteger(numero) || numero < 0 || numero >= c.tailleVocabulaire) {
      throw new RangeError(
        `Numéro hors du vocabulaire : ${String(numero)} (il y a ${c.tailleVocabulaire} caractères, ` +
          `numérotés de 0 à ${c.tailleVocabulaire - 1}).`,
      );
    }
  }
}

/** Le modèle ne lit pas plus de positions que son contexte. */
export function verifierContexte(c: ConfigMini, nbPositions: number): void {
  if (nbPositions > c.contexte) {
    throw new RangeError(
      `${nbPositions} positions à lire, mais le contexte n'en a que ${c.contexte} : ` +
        'raccourcis la séquence, ou agrandis contexte dans ConfigMini.',
    );
  }
}

/** Le bon nombre de paramètres, et des numéros que la passe avant sait lire. */
export function verifierEntree(c: ConfigMini, params: Float64Array, ids: readonly number[]): void {
  if (params.length !== nombreParametres(c)) {
    throw new RangeError(
      `avant : ${params.length} paramètres, mais cette configuration en a ${nombreParametres(c)}. ` +
        'Crée-les avec initialiser(c, hasard).',
    );
  }
  if (ids.length === 0) {
    throw new RangeError('avant : il faut au moins un numéro à lire (le bord, 0, pour commencer).');
  }
  verifierContexte(c, ids.length);
  verifierNumeros(c, ids);
}

/** La passe avant, position par position : du numéro lu en t aux scores du numéro suivant (région `avant`). */
export function avant(c: ConfigMini, params: Float64Array, ids: readonly number[]): Position[] {
  verifierEntree(c, params, ids);
  const places = disposition(c);
  const tt = tailleTete(c);
  const echelle = 1.0 / racine(tt);
  const passe: Position[] = [];
  const cles: number[][] = [];
  const valeurs: number[][] = [];
  for (let t = 0; t < ids.length; t++) {
    // 1. Le vecteur de départ : le plongement du numéro lu, plus celui de la position.
    const lu = places.plongement[0] + ids[t] * c.dim;
    const ici = places.positions[0] + t * c.dim;
    const h0: number[] = [];
    for (let i = 0; i < c.dim; i++) h0.push(params[lu + i] + params[ici + i]);
    // 2. Normer, puis la requête, la clé et la valeur de cette position.
    const [a, invA] = norme(h0);
    const q = produit(a, params, places.requetes);
    const k = produit(a, params, places.cles);
    const v = produit(a, params, places.valeurs);
    cles.push(k);
    valeurs.push(v);
    // 3. Chaque tête regarde les positions 0 à t, jamais les suivantes : c'est le masque causal.
    const poids: number[][] = [];
    const o: number[] = [];
    for (let h = 0; h < c.tetes; h++) {
      const de = h * tt;
      const jusqua = (h + 1) * tt;
      const p = poidsAttention(
        q.slice(de, jusqua),
        Array.from({ length: t + 1 }, (_, j) => cles[j].slice(de, jusqua)),
        echelle,
      );
      o.push(...melangerValeurs(p, Array.from({ length: t + 1 }, (_, j) => valeurs[j].slice(de, jusqua))));
      poids.push(p);
    }
    // 4. Ajouter ce que l'attention a trouvé (connexion résiduelle).
    let z = produit(o, params, places.sortie_attention);
    const h1: number[] = [];
    for (let i = 0; i < c.dim; i++) h1.push(h0[i] + z[i]);
    // 5. Le MLP : normer, élargir, ReLU, revenir à dim, ajouter.
    const [b, invB] = norme(h1);
    const u = produit(b, params, places.mlp_haut);
    const r = u.map((x) => relu(x));
    z = produit(r, params, places.mlp_bas);
    const h2: number[] = [];
    for (let i = 0; i < c.dim; i++) h2.push(h1[i] + z[i]);
    // 6. Normer, puis un score par numéro du vocabulaire.
    const [f, invF] = norme(h2);
    const logits = produit(f, params, places.tete_de_lecture);
    passe.push({ h0, a, invA, q, k, v, poids, o, h1, b, invB, u, r, h2, f, invF, logits });
  }
  return passe;
}

/**
 * L'erreur à une position : −ln de la probabilité que le modèle donne au bon numéro (région `perte`).
 *
 * Avec m le plus grand score : −ln(e^(l_cible) / Σ e^(l_i)) = ln Σ e^(l_i − m) − (l_cible − m).
 * Retirer m ne change pas le résultat, et exp ne déborde jamais.
 */
export function entropieCroisee(logits: readonly number[], cible: number): number {
  const m = maximum(logits);
  const e = logits.map((l) => exp(l - m));
  return log(somme(e)) - (logits[cible] - m);
}

/**
 * La dérivée de y = x · W, pour W rangée à place.
 *
 * Ajoute x[i] × dy[j] à la case (i, j) de W dans gradient, et renvoie
 * dx[i] = Σ_j W[i][j] × dy[j], sommé par j croissant.
 */
export function produitArriere(
  x: ArrayLike<number>,
  dy: ArrayLike<number>,
  params: Float64Array,
  gradient: Float64Array,
  place: Place,
): number[] {
  const [debut, lignes, colonnes] = place;
  const dx: number[] = [];
  for (let i = 0; i < lignes; i++) {
    const xi = x[i];
    const base = debut + i * colonnes;
    let s = 0.0;
    for (let j = 0; j < colonnes; j++) {
      gradient[base + j] += xi * dy[j];
      s += params[base + j] * dy[j];
    }
    dx.push(s);
  }
  return dx;
}

/** La dérivée de la norme : dx_i = inv × (dy_i − y_i × (dy · y) / dim), avec y et inv de la passe avant. */
export function normeArriere(y: readonly number[], inv: number, dy: readonly number[]): number[] {
  const moyenne = produitScalaire(dy, y) / y.length;
  const dx: number[] = [];
  for (let i = 0; i < y.length; i++) dx.push(inv * (dy[i] - y[i] * moyenne));
  return dx;
}

/** Un tableau de n zéros (+0,0), comme [0.0] * n en Python. */
function zeros(n: number): number[] {
  return new Array<number>(n).fill(0.0);
}

/**
 * La passe arrière d'une séquence : la passe avant à l'envers, de la dernière position à la première.
 *
 * Ajoute à gradient les dérivées de la perte moyenne (nombre : les positions prédites de tout le lot).
 * Une clé et une valeur servent à leur position et à toutes les suivantes : quand on arrive à la
 * position t, en descendant, dk[t] et dv[t] ont reçu tout ce qui leur revient.
 */
export function arriere(
  c: ConfigMini,
  params: Float64Array,
  ids: readonly number[],
  cibles: readonly number[],
  passe: readonly Position[],
  nombre: number,
  gradient: Float64Array,
): void {
  const places = disposition(c);
  const tt = tailleTete(c);
  const echelle = 1.0 / racine(tt);
  const n = ids.length;
  const dk = Array.from({ length: n }, () => zeros(c.dim));
  const dv = Array.from({ length: n }, () => zeros(c.dim));
  for (let t = n - 1; t >= 0; t--) {
    const ici = passe[t];
    // 7. La perte : softmax des scores, moins 1 sur la cible, divisé par le nombre de positions.
    const probas = softmax(ici.logits);
    const dlogits: number[] = [];
    for (let i = 0; i < probas.length; i++) {
      let g = probas[i];
      if (i === cibles[t]) {
        g = g - 1.0;
      }
      dlogits.push(g / nombre);
    }
    // 6. logits = f · tete_de_lecture, avec f = norme(h2).
    const df = produitArriere(ici.f, dlogits, params, gradient, places.tete_de_lecture);
    const dh2 = normeArriere(ici.f, ici.invF, df);
    // 5. h2 = h1 + relu(u) · mlp_bas, avec u = b · mlp_haut et b = norme(h1).
    const dr = produitArriere(ici.r, dh2, params, gradient, places.mlp_bas);
    const du: number[] = [];
    for (let i = 0; i < c.largeurMlp; i++) du.push(ici.u[i] > 0.0 ? dr[i] : 0.0);
    const db = produitArriere(ici.b, du, params, gradient, places.mlp_haut);
    const dnb = normeArriere(ici.b, ici.invB, db);
    const dh1: number[] = [];
    for (let i = 0; i < c.dim; i++) dh1.push(dh2[i] + dnb[i]);
    // 4. h1 = h0 + o · sortie_attention.
    const doTetes = produitArriere(ici.o, dh1, params, gradient, places.sortie_attention);
    // 3. Les têtes, de la dernière à la première.
    const dq = zeros(c.dim);
    for (let h = c.tetes - 1; h >= 0; h--) {
      const de = h * tt;
      const jusqua = (h + 1) * tt;
      const p = ici.poids[h];
      // Le mélange : o_h = Σ_j p[j] × v_h(j).
      const dp: number[] = [];
      for (let j = 0; j < t + 1; j++) {
        dp.push(produitScalaire(doTetes.slice(de, jusqua), passe[j].v.slice(de, jusqua)));
        for (let x = de; x < jusqua; x++) {
          dv[j][x] += p[j] * doTetes[x];
        }
      }
      // Le softmax : la dérivée du score j est p[j] × (dp[j] − Σ_l p[l] × dp[l]).
      const moyenne = produitScalaire(p, dp);
      // Les scores : score_j = (q · k_j) × échelle.
      for (let j = 0; j < t + 1; j++) {
        const ds = p[j] * (dp[j] - moyenne) * echelle;
        for (let x = de; x < jusqua; x++) {
          dq[x] += ds * passe[j].k[x];
          dk[j][x] += ds * ici.q[x];
        }
      }
    }
    // 2. q, k, v = a · requetes, a · cles, a · valeurs, avec a = norme(h0).
    const daQ = produitArriere(ici.a, dq, params, gradient, places.requetes);
    const daK = produitArriere(ici.a, dk[t], params, gradient, places.cles);
    const daV = produitArriere(ici.a, dv[t], params, gradient, places.valeurs);
    const da: number[] = [];
    for (let i = 0; i < c.dim; i++) da.push(daQ[i] + daK[i] + daV[i]);
    const dna = normeArriere(ici.a, ici.invA, da);
    const dh0: number[] = [];
    for (let i = 0; i < c.dim; i++) dh0.push(dh1[i] + dna[i]);
    // 1. h0 = plongement[ids[t]] + positions[t].
    const lu = places.plongement[0] + ids[t] * c.dim;
    const position = places.positions[0] + t * c.dim;
    for (let i = 0; i < c.dim; i++) {
      gradient[lu + i] += dh0[i];
      gradient[position + i] += dh0[i];
    }
  }
}

/**
 * La perte moyenne du lot et, si gradient est donné, sa dérivée par rapport à chaque paramètre.
 *
 * Une séquence vaut [0, …, 0] : on lit seq[:-1] et on prédit seq[1:]. La
 * perte est la moyenne de l'entropie croisée sur toutes les positions
 * prédites de toutes les séquences. Le gradient (de même longueur que
 * params) est remis à 0,0, puis rempli séquence par séquence.
 */
export function perteEtGradient(
  c: ConfigMini,
  params: Float64Array,
  sequences: readonly (readonly number[])[],
  gradient: Float64Array | null = null,
): number {
  if (gradient !== null && gradient.length !== nombreParametres(c)) {
    throw new RangeError(
      `perte_et_gradient : le gradient a ${gradient.length} cases, il en faut une par paramètre ` +
        `(${nombreParametres(c)}).`,
    );
  }
  let nombre = 0;
  for (const seq of sequences) {
    if (seq.length < 2) {
      throw new RangeError(
        "perte_et_gradient : chaque séquence a au moins deux numéros, le bord puis ce qu'on prédit " +
          `(reçu une séquence de ${seq.length} numéro).`,
      );
    }
    verifierContexte(c, seq.length - 1);
    verifierNumeros(c, seq);
    nombre += seq.length - 1;
  }
  if (nombre === 0) {
    throw new RangeError('perte_et_gradient : aucune séquence. Donne au moins une séquence de deux numéros ou plus.');
  }
  if (gradient !== null) {
    gradient.fill(0.0);
  }
  const pertes: number[] = [];
  for (const seq of sequences) {
    const ids = seq.slice(0, -1);
    const cibles = seq.slice(1);
    const passe = avant(c, params, ids);
    for (let t = 0; t < ids.length; t++) {
      pertes.push(entropieCroisee(passe[t].logits, cibles[t]));
    }
    if (gradient !== null) {
      arriere(c, params, ids, cibles, passe, nombre, gradient);
    }
  }
  return somme(pertes) / nombre;
}

/** La perte moyenne du lot, sans gradient. */
export function perte(c: ConfigMini, params: Float64Array, sequences: readonly (readonly number[])[]): number {
  return perteEtGradient(c, params, sequences, null);
}

/** Les scores du numéro qui suit ids : ceux de la dernière position de la passe avant. */
export function logitsSuivants(c: ConfigMini, params: Float64Array, ids: readonly number[]): number[] {
  const passe = avant(c, params, ids);
  return passe[passe.length - 1].logits;
}

/**
 * Tire un numéro selon les scores : le numéro i a la chance e_i = exp(logits[i] − m), m le plus grand score.
 *
 * seuil = uniforme × somme des chances. On cumule les chances par numéro
 * croissant, et on prend le premier numéro où le seuil passe sous le cumul
 * (le dernier, si l'arrondi l'en empêche).
 */
export function tirerNumero(logits: readonly number[], hasard: { uniforme(): number }): number {
  const m = maximum(logits);
  const e = logits.map((l) => exp(l - m));
  const seuil = hasard.uniforme() * somme(e);
  let cumul = 0.0;
  for (let i = 0; i < e.length; i++) {
    cumul += e[i];
    if (seuil < cumul) {
      return i;
    }
  }
  return e.length - 1;
}

/**
 * nb prénoms inventés, sans les bords.
 *
 * On part du bord [0], puis on refait la passe avant et on tire un numéro,
 * caractère après caractère. Le tirage d'un 0 arrête le prénom, comme
 * LONGUEUR_GENEREE_MAX caractères écrits (ou un contexte plein, s'il est plus court).
 */
export function generer(c: ConfigMini, params: Float64Array, hasard: Hasard, nb: number): number[][] {
  let limite = LONGUEUR_GENEREE_MAX;
  if (c.contexte < limite) {
    limite = c.contexte;
  }
  const prenoms: number[][] = [];
  for (let k = 0; k < nb; k++) {
    const ids = [0];
    while (ids.length - 1 < limite) {
      const numero = tirerNumero(logitsSuivants(c, params, ids), hasard);
      if (numero === 0) {
        break;
      }
      ids.push(numero);
    }
    prenoms.push(ids.slice(1));
  }
  return prenoms;
}
