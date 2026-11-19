// Les problèmes de calcul du chapitre 1.9, et la lecture d'une réponse : le jumeau TypeScript de
// `forge.raisonnement.problemes` (le générateur) et de `forge.raisonnement.verification` (`extraire_nombre`, `est_juste`).
//
// Chaque problème se génère d'une graine, tout en entiers : la même graine donne le même problème, avec sa réponse et
// sa trace (une étape de calcul par ligne, « a op b = c »). Le Python (projets/forge/forge/raisonnement/problemes.py)
// dit ce que ce jumeau doit reproduire, et le fait vérifier :
//
// 1. le hasard est SplitMix32 (`Hasard` de mini-modele/calcul.ts), mais le tirage d'un entier de a à b est celui de
//    forge : `a + suivant32() % (b − a + 1)`, en entiers (pas `entier(n)` du mini-modèle, qui passe par un flottant) ;
// 2. `genererProbleme` crée le hasard de la graine et jette son premier tirage (réservé au choix du couple famille et
//    difficulté de `generer_problemes`), puis les tirages suivent dans l'ordre exact du Python ;
// 3. les 30 prénoms (avec leur genre) et les 20 objets sont dans le même ordre, et problemes.test.ts relit
//    problemes.py pour comparer ces listes ;
// 4. le français : l'accord (`quantite`, `euros`, `ans`), l'élision (`de`, `que`), l'article (`un`), les gabarits de
//    phrases, caractère pour caractère.
//
// La lecture d'une réponse (`extraireNombre`) rend le dernier nombre du texte en fraction exacte (des BigInt, sans
// flottant), comme `Fraction` en Python ; l'expression régulière est celle de verification.py, avec des classes de
// caractères explicites (jamais `\w` ni `\d`) : une lettre ou un chiffre est une catégorie Unicode (`\p{L}`, `\p{N}`).
//
// Les attendus (projets/1.9-raisonnement/tests/attendus.json) sont comparés sans tolérance : tout y est entier, texte
// ou booléen. Ce module n'importe que le hasard du mini-modèle.

import { Hasard } from '../mini-modele/calcul';

export type Genre = 'f' | 'm';

export interface Objet {
  singulier: string;
  pluriel: string;
  genre: Genre;
  prixMin: number;
  prixMax: number;
}

export interface Probleme {
  /** « famille-difficulté-graine » : de quoi le régénérer. */
  id: string;
  famille: string;
  difficulte: number;
  enonce: string;
  /** « a op b = c », une par opération. */
  etapes: string[];
  reponse: number;
}

export const FAMILLES = ['addition', 'soustraction', 'multiplication', 'partage', 'achats', 'ages'] as const;
export const DIFFICULTES = [1, 2, 3] as const;

/** Les difficultés de chaque famille. */
export const FORMES: Readonly<Record<string, readonly number[]>> = Object.freeze({
  addition: [1, 2, 3],
  soustraction: [1, 2, 3],
  multiplication: [1, 2],
  partage: [1, 2],
  achats: [2, 3],
  ages: [2, 3],
});

// Chaque usage a sa plage de graines, de un million de graines.
export const GRAINES_ENTRAINEMENT = 0;
export const GRAINES_EVALUATION = 1_000_000;
export const GRAINES_RL = 2_000_000;
export const GRAINES_PREFERENCES = 3_000_000;
export const GRAINES_VICTOIRE = 4_000_000;
export const GRAINES_VALIDATION_RL = 5_000_000;
const LARGEUR_DES_PLAGES = 1_000_000;
const GRAINE_MAX = 2 ** 32 - 1;

/** Les 30 prénoms avec leur genre : 20 pour l'entraînement, 4 pour la validation du RL, 6 pour l'évaluation. */
export const GENRES_DES_PRENOMS: readonly (readonly [string, Genre])[] = [
  ['Léa', 'f'], ['Lucas', 'm'], ['Alice', 'f'], ['Hugo', 'm'], ['Chloé', 'f'], ['Thomas', 'm'],
  ['Emma', 'f'], ['Nathan', 'm'], ['Inès', 'f'], ['Théo', 'm'], ['Jade', 'f'], ['Louis', 'm'],
  ['Lina', 'f'], ['Arthur', 'm'], ['Manon', 'f'], ['Jules', 'm'], ['Camille', 'f'], ['Adam', 'm'],
  ['Sarah', 'f'], ['Enzo', 'm'], ['Zoé', 'f'], ['Maxime', 'm'], ['Louise', 'f'], ['Paul', 'm'],
  ['Éva', 'f'], ['Émile', 'm'], ['Océane', 'f'], ['Ethan', 'm'], ['Clara', 'f'], ['Gabriel', 'm'],
];
export const PRENOMS: readonly string[] = GENRES_DES_PRENOMS.map(([nom]) => nom);
export const PRENOMS_ENTRAINEMENT: readonly string[] = PRENOMS.slice(0, 20);
export const PRENOMS_VALIDATION_RL: readonly string[] = PRENOMS.slice(20, 24);
export const PRENOMS_EVALUATION: readonly string[] = PRENOMS.slice(24);
const GENRE_DU_PRENOM: ReadonlyMap<string, Genre> = new Map(GENRES_DES_PRENOMS);

export const OBJETS: readonly Objet[] = [
  { singulier: 'pomme', pluriel: 'pommes', genre: 'f', prixMin: 1, prixMax: 3 },
  { singulier: 'orange', pluriel: 'oranges', genre: 'f', prixMin: 1, prixMax: 4 },
  { singulier: 'abricot', pluriel: 'abricots', genre: 'm', prixMin: 1, prixMax: 3 },
  { singulier: 'gâteau', pluriel: 'gâteaux', genre: 'm', prixMin: 2, prixMax: 6 },
  { singulier: 'crayon', pluriel: 'crayons', genre: 'm', prixMin: 1, prixMax: 3 },
  { singulier: 'stylo', pluriel: 'stylos', genre: 'm', prixMin: 2, prixMax: 5 },
  { singulier: 'cahier', pluriel: 'cahiers', genre: 'm', prixMin: 2, prixMax: 6 },
  { singulier: 'livre', pluriel: 'livres', genre: 'm', prixMin: 5, prixMax: 20 },
  { singulier: 'gomme', pluriel: 'gommes', genre: 'f', prixMin: 1, prixMax: 3 },
  { singulier: 'bille', pluriel: 'billes', genre: 'f', prixMin: 1, prixMax: 2 },
  { singulier: 'carte', pluriel: 'cartes', genre: 'f', prixMin: 1, prixMax: 5 },
  { singulier: 'bougie', pluriel: 'bougies', genre: 'f', prixMin: 2, prixMax: 6 },
  { singulier: 'ballon', pluriel: 'ballons', genre: 'm', prixMin: 3, prixMax: 12 },
  { singulier: 'fleur', pluriel: 'fleurs', genre: 'f', prixMin: 1, prixMax: 5 },
  { singulier: 'sucette', pluriel: 'sucettes', genre: 'f', prixMin: 1, prixMax: 3 },
  { singulier: 'jouet', pluriel: 'jouets', genre: 'm', prixMin: 5, prixMax: 25 },
  { singulier: 'autocollant', pluriel: 'autocollants', genre: 'm', prixMin: 1, prixMax: 3 },
  { singulier: 'chaussette', pluriel: 'chaussettes', genre: 'f', prixMin: 2, prixMax: 8 },
  { singulier: 'tasse', pluriel: 'tasses', genre: 'f', prixMin: 3, prixMax: 10 },
  { singulier: 'œuf', pluriel: 'œufs', genre: 'm', prixMin: 1, prixMax: 2 },
];

export const VOYELLES = 'aeiouyhàâäéèêëîïôöùûüœæ';
export const BILLETS: readonly number[] = [10, 20, 50, 100, 200, 500];
export const LIEUX: readonly string[] = ['dans une boîte', 'dans un sac', 'dans un panier', 'dans un carton'];

// --- Le hasard de forge : des entiers seulement ---

/** Un entier de a à b, bornes comprises : a + suivant32() % (b − a + 1), comme `Hasard.entier` de forge. */
function entier(h: Hasard, a: number, b: number): number {
  if (b < a) throw new Error(`Hasard.entier : l’intervalle est vide (de ${a} à ${b}). Donne a inférieur ou égal à b.`);
  return a + (h.suivant32() % (b - a + 1));
}

/** Un élément de la suite, au hasard : suite[entier(0, len − 1)], comme `Hasard.choisir` de forge. */
function choisir<T>(h: Hasard, suite: readonly T[]): T {
  if (suite.length === 0) throw new Error('Hasard.choisir : la suite est vide. Donne au moins un élément à choisir.');
  return suite[entier(h, 0, suite.length - 1)];
}

/** k éléments distincts : à chaque fois, un indice dans ce qui reste, que l'on retire ensuite. */
function tirerDistincts<T>(h: Hasard, suite: readonly T[], k: number): T[] {
  const restants = [...suite];
  const pris: T[] = [];
  for (let i = 0; i < k; i++) pris.push(restants.splice(entier(h, 0, restants.length - 1), 1)[0]);
  return pris;
}

// --- Le français : accords, élision, pronoms ---

/** « 1 pomme », « 2 pommes » : le singulier jusqu'à 1 (0 compris), le pluriel au-delà. */
export function quantite(n: number, objet: Objet): string {
  return `${n} ${n < 2 ? objet.singulier : objet.pluriel}`;
}

/** « 1 euro », « 2 euros ». */
export function euros(n: number): string {
  return n < 2 ? `${n} euro` : `${n} euros`;
}

/** « 1 an », « 2 ans ». */
export function ans(n: number): string {
  return n < 2 ? `${n} an` : `${n} ans`;
}

function premierEnMinuscule(mot: string): string {
  return Array.from(mot)[0].toLowerCase();
}

/** « de pommes », mais « d'oranges » et « d'Hugo » : l'élision devant une voyelle ou un « h » muet. */
export function de(mot: string): string {
  return (VOYELLES.includes(premierEnMinuscule(mot)) ? "d'" : 'de ') + mot;
}

/** « que Léa », mais « qu'Alice » et « qu'Hugo ». */
export function que(mot: string): string {
  return (VOYELLES.includes(premierEnMinuscule(mot)) ? "qu'" : 'que ') + mot;
}

/** « un stylo », « une pomme » : l'article indéfini suit le genre. */
export function un(objet: Objet): string {
  return (objet.genre === 'm' ? 'un ' : 'une ') + objet.singulier;
}

function il(prenom: string): string {
  return GENRE_DU_PRENOM.get(prenom) === 'm' ? 'il' : 'elle';
}

/** « Elle », « Il » : la première lettre en majuscule (les deux pronoms sont ASCII). */
function majuscule(mot: string): string {
  return mot.charAt(0).toUpperCase() + mot.slice(1);
}

/** « a », « a et b », « a, b et c ». */
function liste(morceaux: readonly string[]): string {
  if (morceaux.length === 1) return morceaux[0];
  return morceaux.slice(0, -1).join(', ') + ' et ' + morceaux[morceaux.length - 1];
}

const MOINS = '\u2212';

function etape(a: number, op: string, b: number, c: number): string {
  return `${a} ${op} ${b} = ${c}`;
}

/** Le résultat d'un générateur de famille : l'énoncé, les étapes, la réponse. */
type Generation = [string, string[], number];

// --- Les familles : chacune rend (énoncé, étapes, réponse). L'ordre des tirages est celui du Python. ---

function addition(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const [n] = tirerDistincts(h, prenoms, 1);
  const o = choisir(h, OBJETS);
  const v: number[] = [];
  for (let i = 0; i < d + 1; i++) v.push(entier(h, 10, 99));
  const variante = entier(h, 0, 1);
  const etapes: string[] = [];
  let total = v[0];
  for (const x of v.slice(1)) {
    etapes.push(etape(total, '+', x, total + x));
    total += x;
  }
  const lui = il(n);
  let enonce: string;
  if (variante === 0) {
    const recu = d === 1 ? `${v[1]} de plus` : v.slice(1).map(String).join(', puis ');
    enonce = `${n} a ${quantite(v[0], o)}. ${majuscule(lui)} en reçoit ${recu}. Combien ${de(o.pluriel)} ${n} a-t-${lui} en tout ?`;
  } else {
    const parties = [`${quantite(v[0], o)} ${LIEUX[0]}`, ...v.slice(1).map((x, i) => `${x} ${LIEUX[i + 1]}`)];
    enonce = `${n} met ${liste(parties)}. Combien y a-t-il ${de(o.pluriel)} en tout ?`;
  }
  return [enonce, etapes, total];
}

function soustraction(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const [n] = tirerDistincts(h, prenoms, 1);
  const o = choisir(h, OBJETS);
  let depart: number;
  let retraits: number[];
  if (d === 1) {
    depart = entier(h, 20, 99);
    retraits = [entier(h, 10, depart - 1)];
  } else {
    retraits = [];
    for (let i = 0; i < d; i++) retraits.push(entier(h, 10, 50));
    let somme = 0;
    for (const x of retraits) somme += x;
    depart = somme + entier(h, 10, 99);
  }
  const variante = entier(h, 0, 1);
  const etapes: string[] = [];
  let reste = depart;
  for (const x of retraits) {
    etapes.push(etape(reste, MOINS, x, reste - x));
    reste -= x;
  }
  const enumeration = retraits.map(String).join(', puis ');
  const lui = il(n);
  const enonce =
    variante === 0
      ? `${n} a ${quantite(depart, o)}. ${majuscule(lui)} en donne ${enumeration}. Combien ${de(o.pluriel)} ${n} a-t-${lui} maintenant ?`
      : `Dans une boîte, il y a ${quantite(depart, o)}. ${n} en prend ${enumeration}. Combien en reste-t-il dans la boîte ?`;
  return [enonce, etapes, reste];
}

function multiplication(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const [n] = tirerDistincts(h, prenoms, 1);
  const o = choisir(h, OBJETS);
  const a = entier(h, 2, 9);
  const b = entier(h, 10, 99);
  const variante = entier(h, 0, 1);
  const c = a * b;
  const etapes = [etape(a, '×', b, c)];
  const lui = il(n);
  let enonce = variante === 0 ? `${n} a ${a} boîtes de ${quantite(b, o)} chacune.` : `${n} remplit ${a} sacs avec ${quantite(b, o)} dans chaque sac.`;
  let reponse = c;
  let question: string;
  if (d === 1) {
    question = 'en tout';
  } else {
    const signe = entier(h, 0, 1);
    if (signe === 0) {
      const extra = entier(h, 10, 99);
      etapes.push(etape(c, '+', extra, c + extra));
      reponse = c + extra;
      enonce += ` ${majuscule(lui)} en ajoute encore ${extra}.`;
    } else {
      const extra = entier(h, 2, Math.min(99, c - 1));
      etapes.push(etape(c, MOINS, extra, c - extra));
      reponse = c - extra;
      enonce += ` ${majuscule(lui)} en donne ${extra}.`;
    }
    question = 'maintenant';
  }
  return [`${enonce} Combien ${de(o.pluriel)} ${n} a-t-${lui} ${question} ?`, etapes, reponse];
}

function partage(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const [n] = tirerDistincts(h, prenoms, 1);
  const o = choisir(h, OBJETS);
  const b = entier(h, 2, 9);
  const c = d === 1 ? entier(h, 2, 25) : entier(h, 3, 30);
  const total = b * c;
  const t0 = d === 2 ? entier(h, 1, total - 1) : 0;
  const variante = entier(h, 0, 1);
  const lui = il(n);
  const pl = o.pluriel;
  let etapes: string[];
  let enonce: string;
  if (d === 1) {
    etapes = [etape(total, '÷', b, c)];
    enonce =
      variante === 0
        ? `${n} a ${quantite(total, o)}. ${majuscule(lui)} les partage en parts égales entre ${b} amis. Combien ${de(pl)} reçoit chaque ami ?`
        : `${n} range ${quantite(total, o)} dans ${b} boîtes, avec autant ${de(pl)} dans chaque boîte. Combien ${de(pl)} y a-t-il dans chaque boîte ?`;
  } else {
    const t1 = total - t0;
    etapes = [etape(t0, '+', t1, total), etape(total, '÷', b, c)];
    enonce =
      variante === 0
        ? `${n} a ${quantite(t0, o)}. ${majuscule(lui)} en reçoit ${t1} de plus, puis ${lui} partage le tout en parts égales entre ${b} amis. Combien ${de(pl)} reçoit chaque ami ?`
        : `${n} range ${quantite(t0, o)} dans une boîte et ${t1} dans une autre. ${majuscule(lui)} répartit ensuite le tout dans ${b} sacs, avec autant ${de(pl)} dans chaque sac. Combien ${de(pl)} y a-t-il dans chaque sac ?`;
  }
  return [enonce, etapes, c];
}

function achats(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const [n] = tirerDistincts(h, prenoms, 1);
  const [o1, o2] = tirerDistincts(h, OBJETS, 2);
  const q1 = entier(h, 2, 9);
  const p1 = entier(h, o1.prixMin, o1.prixMax);
  const c1 = q1 * p1;
  const etapes = [etape(q1, '×', p1, c1)];
  const lui = il(n);
  if (d === 2) {
    const variante = entier(h, 0, 1);
    if (variante === 0) {
      const p2 = entier(h, o2.prixMin, o2.prixMax);
      etapes.push(etape(c1, '+', p2, c1 + p2));
      const enonce = `${n} achète ${quantite(q1, o1)} à ${euros(p1)} pièce et ${un(o2)} à ${euros(p2)}. Combien ${n} paie-t-${lui} en tout ?`;
      return [enonce, etapes, c1 + p2];
    }
    const billet = BILLETS.find((b) => b > c1) as number;
    etapes.push(etape(billet, MOINS, c1, billet - c1));
    const enonce = `${n} achète ${quantite(q1, o1)} à ${euros(p1)} pièce. ${majuscule(lui)} paie avec un billet de ${billet} euros. Combien d'euros ${n} reçoit-${lui} en monnaie ?`;
    return [enonce, etapes, billet - c1];
  }
  const q2 = entier(h, 2, 9);
  const p2 = entier(h, o2.prixMin, o2.prixMax);
  const c2 = q2 * p2;
  etapes.push(etape(q2, '×', p2, c2), etape(c1, '+', c2, c1 + c2));
  const enonce = `${n} achète ${quantite(q1, o1)} à ${euros(p1)} pièce et ${quantite(q2, o2)} à ${euros(p2)} pièce. Combien ${n} paie-t-${lui} en tout ?`;
  return [enonce, etapes, c1 + c2];
}

function ages(h: Hasard, d: number, prenoms: readonly string[]): Generation {
  const noms = tirerDistincts(h, prenoms, d); // d = 2 ou 3 : le nombre de personnes
  const a = entier(h, 15, 60);
  let etapes: string[];
  let presentation: string;
  let actuel: number;
  if (d === 2) {
    const sens = entier(h, 0, 1); // 0 : de plus, 1 : de moins
    const e = entier(h, 1, 9);
    const b = sens === 0 ? a + e : a - e;
    etapes = [etape(a, sens === 0 ? '+' : MOINS, e, b)];
    presentation = `${noms[0]} a ${ans(a)}. ${noms[1]} a ${ans(e)} ${sens === 0 ? 'de plus' : 'de moins'} ${que(noms[0])}.`;
    actuel = b;
  } else {
    const e1 = entier(h, 1, 9);
    const e2 = entier(h, 1, 9);
    const b = a + e1;
    actuel = b - e2;
    etapes = [etape(a, '+', e1, b), etape(b, MOINS, e2, actuel)];
    presentation = `${noms[0]} a ${ans(a)}. ${noms[1]} a ${ans(e1)} de plus ${que(noms[0])}, et ${noms[2]} a ${ans(e2)} de moins ${que(noms[1])}.`;
  }
  const futur = entier(h, 0, 1) === 0;
  const k = futur ? entier(h, 1, 10) : entier(h, 1, Math.min(10, actuel - 1));
  etapes.push(etape(actuel, futur ? '+' : MOINS, k, futur ? actuel + k : actuel - k));
  const cible = noms[noms.length - 1];
  const question = futur ? `Quel âge aura ${cible} dans ${ans(k)} ?` : `Quel âge avait ${cible} il y a ${ans(k)} ?`;
  return [`${presentation} ${question}`, etapes, futur ? actuel + k : actuel - k];
}

const GENERATEURS: Readonly<Record<string, (h: Hasard, d: number, prenoms: readonly string[]) => Generation>> = {
  addition,
  soustraction,
  multiplication,
  partage,
  achats,
  ages,
};

/** « evaluation » de [GRAINES_EVALUATION, GRAINES_RL[, « validation_rl » de [GRAINES_VALIDATION_RL, +1 000 000[, « entrainement » sinon. */
export function usageDeLaGraine(graine: number): 'entrainement' | 'evaluation' | 'validation_rl' {
  if (GRAINES_EVALUATION <= graine && graine < GRAINES_RL) return 'evaluation';
  if (GRAINES_VALIDATION_RL <= graine && graine < GRAINES_VALIDATION_RL + LARGEUR_DES_PLAGES) return 'validation_rl';
  return 'entrainement';
}

const PRENOMS_DE_L_USAGE: Readonly<Record<string, readonly string[]>> = {
  entrainement: PRENOMS_ENTRAINEMENT,
  validation_rl: PRENOMS_VALIDATION_RL,
  evaluation: PRENOMS_EVALUATION,
};

/**
 * Le problème de cette famille et de cette difficulté, tiré de cette graine (la même graine, le même problème).
 * Un couple (famille, difficulté) qui n'existe pas, ou une graine qui n'est pas un entier de 0 à 2³² − 1, lève une erreur.
 */
export function genererProbleme(famille: string, difficulte: number, graine: number): Probleme {
  if (!Object.hasOwn(FORMES, famille)) {
    throw new Error(`Famille inconnue : « ${famille} ». Les familles sont ${FAMILLES.join(', ')}.`);
  }
  if (!FORMES[famille].includes(difficulte)) {
    throw new Error(
      `La difficulté ${difficulte} n’existe pas pour la famille « ${famille} » : ses difficultés sont ${FORMES[famille].join(', ')}.`,
    );
  }
  if (!Number.isInteger(graine) || graine < 0 || graine > GRAINE_MAX) {
    throw new Error(`La graine ${graine} doit être un entier de 0 à 2^32 − 1 (4 294 967 295) : donne une autre graine.`);
  }
  const h = new Hasard(graine);
  h.suivant32(); // réservé au choix du couple (famille, difficulté) de `generer_problemes`
  const [enonce, etapes, reponse] = GENERATEURS[famille](h, difficulte, PRENOMS_DE_L_USAGE[usageDeLaGraine(graine)]);
  return { id: `${famille}-${difficulte}-${graine}`, famille, difficulte, enonce, etapes, reponse };
}

// --- Lire une réponse : le dernier nombre du texte, en fraction exacte ---

/** Une fraction exacte, réduite, au dénominateur positif : `Fraction` de Python, avec des BigInt. */
export interface Fraction {
  numerateur: bigint;
  denominateur: bigint;
}

// Les séparateurs de milliers : espace, espace insécable, espace fine insécable.
const SEPARATEURS = ' \u00a0\u202f';
const MOINS_LUS = '\\-\u2212';

// Un nombre : un signe facultatif (jamais collé à une lettre ou un chiffre qui le précède), des chiffres (par groupes de
// trois séparés par une espace, ou d'une traite), une partie décimale facultative après « , » ou « . ». Le « (?![0-9]) »
// de la fin d'un groupe empêche « 12 3456 » de se lire « 12 345 » suivi de « 6 ».
const NOMBRE = new RegExp(
  `(?<![0-9])(?<signe>(?<![\\p{L}\\p{N}])[${MOINS_LUS}])?` +
    `(?<entier>[0-9]{1,3}(?:[${SEPARATEURS}][0-9]{3})+(?![0-9])|[0-9]+)` +
    '(?:[,.](?<decimales>[0-9]+))?',
  'gu',
);

function pgcd(a: bigint, b: bigint): bigint {
  while (b !== 0n) [a, b] = [b, a % b];
  return a;
}

function fraction(numerateur: bigint, denominateur: bigint): Fraction {
  const g = pgcd(numerateur < 0n ? -numerateur : numerateur, denominateur);
  return g === 0n ? { numerateur, denominateur } : { numerateur: numerateur / g, denominateur: denominateur / g };
}

/**
 * Le dernier nombre du texte, ou null s'il n'y en a pas : milliers séparés par une espace, une espace insécable ou
 * une espace fine insécable (« 1 234 567 », exactement trois chiffres après chaque séparateur), virgule décimale
 * (« 12,5 » vaut 25/2 ; un point entre deux chiffres compte aussi), signe moins « - » ou « − » s'il n'est pas collé à
 * une lettre ou un chiffre qui le précède (« 5-3 » est 5 puis 3).
 */
export function extraireNombre(texte: string): Fraction | null {
  let dernier: RegExpMatchArray | null = null;
  for (const lu of texte.matchAll(NOMBRE)) dernier = lu;
  if (dernier === null) return null;
  const groupes = dernier.groups as { signe?: string; entier: string; decimales?: string };
  let chiffres = '';
  for (const c of groupes.entier) if (c >= '0' && c <= '9') chiffres += c;
  let numerateur = BigInt(chiffres);
  let denominateur = 1n;
  if (groupes.decimales !== undefined) {
    denominateur = 10n ** BigInt(groupes.decimales.length);
    numerateur = numerateur * denominateur + BigInt(groupes.decimales);
  }
  if (groupes.signe !== undefined) numerateur = -numerateur;
  return fraction(numerateur, denominateur);
}

/** « 25/2 » ou « -7 » : une fraction écrite comme les attendus du Python (le dénominateur est omis quand il vaut 1). */
export function ecrireFraction(f: Fraction): string {
  return f.denominateur === 1n ? `${f.numerateur}` : `${f.numerateur}/${f.denominateur}`;
}

/**
 * Vrai si la réponse est terminée et si le nombre lu dans son texte (après la pensée) égale `attendu`. `attendu` est un
 * entier, ou une chaîne lue comme `extraireNombre`. Une réponse coupée, une réponse sans nombre, ou un `attendu` chaîne
 * qui n'est pas un nombre, ne sont jamais justes. Un autre type d'`attendu` (booléen, flottant) lève une erreur.
 */
export function estJuste(texte: string, terminee: boolean, attendu: number | string): boolean {
  if (typeof attendu === 'number' ? !Number.isInteger(attendu) : typeof attendu !== 'string') {
    throw new TypeError(`L’attendu doit être un entier ou une chaîne (reçu ${String(attendu)}).`);
  }
  if (!terminee) return false;
  const lu = extraireNombre(texte);
  if (lu === null) return false;
  const voulu = typeof attendu === 'string' ? extraireNombre(attendu) : fraction(BigInt(attendu), 1n);
  return voulu !== null && lu.numerateur === voulu.numerateur && lu.denominateur === voulu.denominateur;
}
