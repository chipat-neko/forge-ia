// Le noyau de calcul exact du mini-modèle, en TypeScript.
//
// C'est le jumeau exact de projets/mini-modele/mini_modele/calcul.py : mêmes
// fonctions, mêmes boucles, même ordre des opérations. Le fichier
// projets/mini-modele/tests/attendus-calcul.json, écrit par le Python, le
// prouve au bit près dans calcul.test.ts. Si l'un des deux change, l'autre
// doit suivre.
//
// La norme IEEE 754 ne fixe le dernier bit que des + − × ÷ et de la racine
// carrée : les exp, log et cos du navigateur peuvent différer d'un moteur à
// l'autre. D'où ce module :
//  - exp, log et cos écrits avec des + − × ÷ seulement, dans un ordre fixé ;
//  - des sommes en boucle, dans l'ordre des indices, sans compensation ;
//  - un hasard maison (SplitMix32), qui donne la même suite partout ;
//  - des motifs hexadécimaux et des empreintes, pour comparer les deux langages.
// Ce fichier est vérifié par sources.test.ts.

// ln 2 coupé en deux morceaux, comme dans fdlibm : la partie haute n'a que 32
// bits significatifs, donc k × LN2_HAUT est exact pour tous les k de exp et log.
export const LN2_HAUT = 0.6931471803691238; // 3fe62e42fee00000
export const LN2_BAS = 1.9082149292705877e-10; // 3dea39ef35793c76
export const INV_LN2 = 1.4426950408889634; // 3ff71547652b82fe : 1 / ln 2
export const SQRT_DEMI = 0.7071067811865476; // 3fe6a09e667f3bcd : la racine de 1/2
export const PI = 3.141592653589793; // 400921fb54442d18

// Coefficients des séries, calculés par des divisions (les mêmes en Python ;
// leurs motifs sont dans les attendus, clé « coefficients »). Exportés en
// lecture seule, pour que calcul.test.ts les compare à ceux du Python.
// exp(r) = 1 + r + r^2/2! + … + r^13/13! : C_EXP[n] = 1/n!
const cExp: number[] = [1.0];
for (let n = 1; n < 14; n++) cExp.push(cExp[n - 1] / n);
export const C_EXP: readonly number[] = Object.freeze(cExp);
// ln m = 2s × (1 + z/3 + z^2/5 + … + z^11/23), avec s = (m − 1)/(m + 1) et z = s × s.
export const C_LOG: readonly number[] = Object.freeze(Array.from({ length: 12 }, (_, n) => 1.0 / (2 * n + 1)));
// cos t = 1 − t^2/2! + t^4/4! − … + t^24/24! : C_COS[n] = (−1)^n / (2n)!
const cCos: number[] = [1.0];
for (let n = 1; n < 13; n++) cCos.push(-cCos[n - 1] / ((2 * n - 1) * (2 * n)));
export const C_COS: readonly number[] = Object.freeze(cCos);

// 2^k pour k de -1074 à 1023 (indice k + 1074), construits depuis 1,0 par des
// ×2 et des ÷2 : chacun est exact. C'est ce que fait math.ldexp(1.0, k) en Python.
const DEUX_PUISSANCES = new Float64Array(1074 + 1024);
DEUX_PUISSANCES[1074] = 1.0;
for (let k = 1; k <= 1023; k++) DEUX_PUISSANCES[1074 + k] = DEUX_PUISSANCES[1074 + k - 1] * 2.0;
for (let k = -1; k >= -1074; k--) DEUX_PUISSANCES[1074 + k] = DEUX_PUISSANCES[1074 + k + 1] / 2.0;

/** 2^k exact, pour k de -1074 à 1023. */
export function deuxPuissance(k: number): number {
  if (!(Number.isInteger(k) && k >= -1074 && k <= 1023)) {
    throw new RangeError(`deux_puissance : k doit aller de -1074 à 1023 (reçu ${k}).`);
  }
  return DEUX_PUISSANCES[k + 1074];
}

// Une vue sur 8 octets, pour lire et écrire les bits d'un flottant. Les
// méthodes de DataView sont gros-boutistes par défaut.
const VUE = new DataView(new ArrayBuffer(8));

/**
 * Comme math.frexp en Python, pour x > 0 fini : [m, e] avec x = m × 2^e et m
 * dans [0,5 ; 1[. Exact : on lit l'exposant dans les bits, et on remplace
 * l'exposant par celui de 0,5. Un sous-normal est d'abord multiplié par 2^64
 * (exact), pour avoir un exposant à lire.
 */
function decomposer(x: number): [number, number] {
  let decalage = 0;
  if (x < deuxPuissance(-1022)) {
    x = x * deuxPuissance(64);
    decalage = 64;
  }
  VUE.setFloat64(0, x);
  const haut = VUE.getUint32(0);
  const exposant = (haut >>> 20) & 0x7ff;
  VUE.setUint32(0, ((haut & 0x000fffff) | (1022 << 20)) >>> 0);
  return [VUE.getFloat64(0), exposant - 1022 - decalage];
}

/**
 * e^x, avec seulement des + − × ÷ (région `exp` de calcul.py).
 *
 * 1. On écrit x = k × ln 2 + r, avec k entier et r entre -0,35 et 0,35.
 * 2. e^r est la série de Taylor jusqu'à r^13, calculée par Horner.
 * 3. e^x = e^r × 2^k, et multiplier par 2^k est exact.
 */
export function exp(x: number): number {
  if (x !== x) return x; // NaN
  if (x > 709.782712893384) return Infinity; // au-delà, e^x dépasse le plus grand flottant
  if (x < -745.1332191019411) return 0.0; // en deçà, e^x s'arrondit à 0
  const k = Math.floor(x * INV_LN2 + 0.5);
  const r = (x - k * LN2_HAUT) - k * LN2_BAS;
  let p = C_EXP[13];
  for (let n = 12; n >= 0; n--) {
    p = p * r + C_EXP[n];
  }
  if (k > 1023) return (p * 2.0) * deuxPuissance(k - 1); // 2^1024 n'est pas un flottant
  if (k < -1022) return (p * deuxPuissance(k + 64)) * deuxPuissance(-64); // sous-normal : un seul arrondi
  return p * deuxPuissance(k);
}

/**
 * ln x, avec seulement des + − × ÷ (région `log` de calcul.py).
 *
 * 1. On écrit x = m × 2^e, avec m entre √½ et √2 (décomposition exacte).
 * 2. ln x = e × ln 2 + ln m.
 * 3. ln m = 2s × (1 + s^2/3 + s^4/5 + …), avec s = (m − 1)/(m + 1) : la
 *    série converge vite, car |s| reste sous 0,18.
 */
export function log(x: number): number {
  if (x !== x || x < 0.0) return NaN;
  if (x === 0.0) return -Infinity;
  if (x === Infinity) return x;
  let [m, e] = decomposer(x); // m dans [0,5 ; 1[
  if (m < SQRT_DEMI) {
    m = m * 2.0;
    e = e - 1;
  }
  const f = m - 1.0;
  const s = f / (2.0 + f);
  const z = s * s;
  let q = C_LOG[11];
  for (let n = 10; n >= 0; n--) {
    q = q * z + C_LOG[n];
  }
  return e * LN2_HAUT + (2.0 * s * q + e * LN2_BAS);
}

/** cos x, pour x de 0 à π seulement : c'est tout ce qu'il faut au mini-modèle. */
export function cos(x: number): number {
  if (!(x >= 0.0 && x <= PI)) {
    // rejette aussi NaN
    throw new RangeError(`cos n'est définie ici que de 0 à π (reçu ${x}).`);
  }
  if (x > PI * 0.5) return -cosNoyau(PI - x); // cos x = −cos(π − x), et PI − x est exact
  return cosNoyau(x);
}

/** La série de Taylor de cos jusqu'à t^24, calculée par Horner, pour t de 0 à π/2. */
function cosNoyau(t: number): number {
  const z = t * t;
  let p = C_COS[12];
  for (let n = 11; n >= 0; n--) {
    p = p * z + C_COS[n];
  }
  return p;
}

/** √x : la racine carrée est arrondie correctement, en pratique partout (math.sqrt en Python). */
export function racine(x: number): number {
  if (x < 0.0) {
    throw new RangeError(`racine d'un nombre négatif (${x}) : vérifie le calcul qui a produit ce nombre.`);
  }
  return Math.sqrt(x);
}

/** La somme dans l'ordre des indices, par une simple boucle, sans compensation. */
export function somme(valeurs: ArrayLike<number>): number {
  let s = 0.0;
  for (let i = 0; i < valeurs.length; i++) {
    s += valeurs[i];
  }
  return s;
}

/** a[0] × b[0] + a[1] × b[1] + …, dans l'ordre des indices. */
export function produitScalaire(a: ArrayLike<number>, b: ArrayLike<number>): number {
  if (a.length !== b.length) {
    throw new RangeError(
      `produit_scalaire : les deux listes n'ont pas la même longueur (${a.length} et ${b.length}). ` +
        'Donne deux listes de même longueur.',
    );
  }
  let s = 0.0;
  for (let i = 0; i < a.length; i++) {
    s += a[i] * b[i];
  }
  return s;
}

/** La plus grande valeur, par une boucle « if v > m » : à égalité, la première gagne (même −0 face à 0). */
export function maximum(valeurs: ArrayLike<number>): number {
  if (valeurs.length === 0) {
    throw new RangeError('maximum : la liste est vide. Donne au moins une valeur.');
  }
  let m = valeurs[0];
  for (let i = 1; i < valeurs.length; i++) {
    if (valeurs[i] > m) m = valeurs[i];
  }
  return m;
}

// Tous les NaN s'écrivent avec ce motif : celui d'un NaN calculé varie d'une machine à l'autre.
export const NAN_HEX = '7ff8000000000000';

// Les mêmes 8 octets que VUE, lus un par un.
const OCTETS = new Uint8Array(VUE.buffer);

/** Range dans VUE les 8 octets du flottant, du plus fort au plus faible ; tous les NaN avec le motif NAN_HEX. */
function rangerOctets(x: number): void {
  if (x !== x) {
    VUE.setUint32(0, 0x7ff80000);
    VUE.setUint32(4, 0);
  } else {
    VUE.setFloat64(0, x);
  }
}

/** Les 8 octets du flottant, du plus fort au plus faible, en 16 chiffres hexadécimaux minuscules. */
export function versHex(x: number): string {
  rangerOctets(x);
  return VUE.getUint32(0).toString(16).padStart(8, '0') + VUE.getUint32(4).toString(16).padStart(8, '0');
}

/** Le flottant écrit par versHex. */
export function depuisHex(h: string): number {
  if (!/^[0-9a-f]{16}$/.test(h)) {
    throw new RangeError(`depuis_hex attend 16 chiffres hexadécimaux minuscules (reçu « ${h} »).`);
  }
  VUE.setUint32(0, parseInt(h.slice(0, 8), 16));
  VUE.setUint32(4, parseInt(h.slice(8), 16));
  return VUE.getFloat64(0);
}

// FNV-1a sur 32 bits : une empreinte courte, pour comparer de longues listes de nombres.
const FNV_DEPART = 0x811c9dc5;
const FNV_PREMIER = 0x01000193;

/** Les octets de plus dans l'empreinte : pour chacun, (h xor o) × FNV_PREMIER, modulo 2^32. */
function fnv1a(h: number, octets: ArrayLike<number>): number {
  for (let i = 0; i < octets.length; i++) {
    h = Math.imul(h ^ octets[i], FNV_PREMIER) >>> 0;
  }
  return h;
}

/** FNV-1a 32 bits sur les 8 octets de chaque flottant (ceux de versHex), en 8 chiffres hexadécimaux. */
export function empreinte(valeurs: ArrayLike<number>): string {
  let h = FNV_DEPART;
  for (let i = 0; i < valeurs.length; i++) {
    rangerOctets(valeurs[i]);
    h = fnv1a(h, OCTETS);
  }
  return h.toString(16).padStart(8, '0');
}

/** FNV-1a 32 bits sur les octets UTF-8 du texte, en 8 chiffres hexadécimaux. */
export function empreinteTexte(texte: string): string {
  return fnv1a(FNV_DEPART, new TextEncoder().encode(texte)).toString(16).padStart(8, '0');
}

/**
 * Le hasard reproductible du mini-modèle : SplitMix32.
 *
 * Une même graine donne la même suite en Python et en TypeScript, dans tous
 * les navigateurs. La graine est un entier, ramené à 32 bits (de 0 à 2^32 − 1).
 * Les graines refusées sont les mêmes qu'en Python : ce qui n'est pas un nombre
 * entier (true compris), et les entiers au-delà des entiers sûrs (2^53 − 1).
 * Math.imul multiplie modulo 2^32, et « >>> 0 » relit le résultat sans signe.
 */
export class Hasard {
  etat: number;

  constructor(graine: number) {
    if (typeof graine !== 'number' || !Number.isInteger(graine)) {
      throw new TypeError(`La graine du hasard doit être un entier (reçu ${graine}). Donne un entier de 0 à 2^32 − 1.`);
    }
    if (!Number.isSafeInteger(graine)) {
      throw new RangeError(
        `La graine du hasard dépasse les entiers sûrs de JavaScript (reçu ${graine}). Donne un entier de 0 à 2^32 − 1.`,
      );
    }
    this.etat = graine >>> 0;
  }

  /** Le prochain entier sur 32 bits, de 0 à 2^32 − 1. */
  suivant32(): number {
    this.etat = (this.etat + 0x9e3779b9) >>> 0;
    let z = this.etat;
    z = Math.imul(z ^ (z >>> 16), 0x21f0aaad) >>> 0;
    z = Math.imul(z ^ (z >>> 15), 0x735a2d97) >>> 0;
    return (z ^ (z >>> 15)) >>> 0;
  }

  /** Un flottant de [0, 1[ : suivant32 divisé par 2^32 (une division exacte). */
  uniforme(): number {
    return this.suivant32() / 4294967296.0;
  }

  /** Un entier de 0 à n − 1. */
  entier(n: number): number {
    return Math.floor(this.uniforme() * n);
  }

  /** Presque une loi normale : 12 uniformes additionnées, moins 6 (moyenne 0, variance 1), fois l'écart-type. */
  gaussienne(ecartType: number): number {
    let s = 0.0;
    for (let i = 0; i < 12; i++) {
      s += this.uniforme();
    }
    return (s - 6.0) * ecartType;
  }

  /** Mélange la liste (tableau ou tableau typé) sur place : Fisher-Yates, de la fin vers le début. */
  melanger<T>(liste: { length: number; [i: number]: T }): void {
    for (let i = liste.length - 1; i > 0; i--) {
      const j = this.entier(i + 1);
      const t = liste[i];
      liste[i] = liste[j];
      liste[j] = t;
    }
  }
}
