// L'atelier du neurone du chapitre 0.5 : un neurone à seuil à deux entrées,
// réglé par trois nombres jaunes (w1, w2 et b, de −2 à 2 par pas de 0,5), et
// une porte logique à imiter (ET, OU ou OU exclusif). Ce module dit ce que
// l'atelier affiche : chaque point du carré (sa somme, la réponse du neurone,
// la bonne réponse), le bilan, le dessin (la droite où la somme vaut 0, et le
// côté où le neurone répond 1), l'acquis et le défi.
//
// Les réponses et les comptes ne sont jamais calculés ici : ils viennent du
// jumeau du Python (neurone.ts, comparé au bit près aux attendus de
// projets/0.5-reseau). atelier-neurone.test.ts vérifie le reste sur les 729
// réglages de la grille, pour les trois portes.
//
// Ce module n'importe que neurone.ts et nombres.ts : l'îlot de l'atelier
// l'emporte dans le navigateur, et un parcours de test peut l'importer (aucun
// ?raw, aucun .json, aucun astro:*).

import { decimalesUtiles, nombre } from '../nombres';
import { bienClasses, GRILLE, POINTS, PORTES, sortieSeuil, type Point, type Porte } from './neurone';

const FINE = '\u202F';
/** Le signe moins de la typographie (U+2212), plus long que le trait d'union. */
const MOINS = '−';

/** Les réglages de w1, w2 et b : ceux de la grille du Python, de −2 à 2 par pas de 0,5. */
export const REGLAGE_MIN = GRILLE[0];
export const REGLAGE_MAX = GRILLE[GRILLE.length - 1];
export const REGLAGE_PAS = GRILLE[1] - GRILLE[0];

/**
 * Le réglage à l'arrivée : w1 = w2 = 1 et b = 0, sur la porte ET. Il classe 2
 * points sur 4 : le lecteur a quelque chose à régler (b = −1,5 les classe tous).
 */
export const W1_DEPART = 1;
export const W2_DEPART = 1;
export const B_DEPART = 0;
export const PORTE_DEPART: Porte = 'et';

/** Les trois portes de l'atelier, dans l'ordre des bascules, avec leur nom affiché. */
export const PORTES_ATELIER: readonly { porte: Porte; nom: string }[] = Object.freeze([
  { porte: 'et', nom: 'ET' },
  { porte: 'ou', nom: 'OU' },
  { porte: 'ou_exclusif', nom: 'OU exclusif' },
]);

/** Le nombre de points du carré. */
export const NB_POINTS = POINTS.length;

/** Le dessin montre le plan de −0,5 à 1,5 dans les deux sens : le carré de 0 à 1, avec de l'air autour. */
export const DOMAINE_MIN = -0.5;
export const DOMAINE_MAX = 1.5;

// ---------- Les nombres et les phrases ----------

/** Un réglage tel qu'il est, avec le signe moins U+2212 : « −1,5 », « 0 », « 2 ». */
export function ecrireReglage(x: number): string {
  return nombre(x, decimalesUtiles(x)).replace(/^[-−]/, MOINS);
}

/** Un point du carré, écrit comme Python écrit un tuple : « (0, 1) ». */
export function ecrirePoint(x: readonly number[]): string {
  return `(${x.join(', ')})`;
}

/** « 2 points sur 4 bien classés. », « Les 4 points sont bien classés. », « Aucun point n'est bien classé. » */
export function bilan(compte: number): string {
  if (compte === NB_POINTS) return `Les ${NB_POINTS} points sont bien classés.`;
  if (compte === 0) return 'Aucun point n’est bien classé.';
  return compte === 1 ? `1 point sur ${NB_POINTS} bien classé.` : `${compte} points sur ${NB_POINTS} bien classés.`;
}

/** L'espace insécable ordinaire, autour du > de « b > 0 » : la ligne ne s'y coupe pas. */
const INSECABLE = '\u00A0';

/** Le message de l'atelier quand w1 et w2 valent 0 : pas de droite. « b > 0 » ne se coupe pas. */
export const SANS_POIDS = `Sans poids, le neurone répond pareil partout${FINE}: 1 si b${INSECABLE}>${INSECABLE}0, sinon 0.`;

// ---------- Les points ----------

/** Un point du carré, vu par le neurone. */
export interface EtatPoint {
  point: Point;
  /** La réponse de la porte en ce point. */
  attendu: number;
  /** La somme pondérée w1 × x1 + w2 × x2 + b, dans l'ordre de sortieSeuil. */
  somme: number;
  /** La réponse du neurone : 1 si la somme est plus grande que 0, 0 sinon (sortieSeuil). */
  reponse: number;
  juste: boolean;
}

/** Les 4 points, dans l'ordre de POINTS, pour ce réglage et cette porte. */
export function etatDesPoints(w1: number, w2: number, b: number, porte: Porte): EtatPoint[] {
  return POINTS.map((point, i) => {
    const reponse = sortieSeuil([w1, w2], b, point);
    const attendu = PORTES[porte][i];
    return { point, attendu, somme: w1 * point[0] + w2 * point[1] + b, reponse, juste: reponse === attendu };
  });
}

/**
 * La phrase d'un point, en morceaux qui ne se coupent pas (« il faut 0, » reste d'un bloc) :
 * « (0, 1) : », « somme 1, », « réponse 1, », « il faut 0, », « mal classé. ».
 */
export function morceauxDuPoint(e: EtatPoint): string[] {
  return [
    `${ecrirePoint(e.point)}${FINE}:`,
    `somme ${ecrireReglage(e.somme)},`,
    `réponse ${e.reponse},`,
    `il faut ${e.attendu},`,
    `${e.juste ? 'bien' : 'mal'} classé.`,
  ];
}

/** « (0, 1) : somme 1, réponse 1, il faut 0, mal classé. » */
export function texteDuPoint(e: EtatPoint): string {
  return morceauxDuPoint(e).join(' ');
}

// ---------- Le dessin ----------

/** Un point du plan (x1, x2). */
export type Coordonnees = readonly [number, number];

/** Les coins du dessin, dans le sens inverse des aiguilles d'une montre (x2 vers le haut). */
const COINS: readonly Coordonnees[] = [
  [DOMAINE_MIN, DOMAINE_MIN],
  [DOMAINE_MAX, DOMAINE_MIN],
  [DOMAINE_MAX, DOMAINE_MAX],
  [DOMAINE_MIN, DOMAINE_MAX],
];

const somme = (w1: number, w2: number, b: number, [x, y]: Coordonnees) => w1 * x + w2 * y + b;
const memePoint = (a: Coordonnees, c: Coordonnees) => Math.abs(a[0] - c[0]) < 1e-12 && Math.abs(a[1] - c[1]) < 1e-12;

/** Le point où la somme s'annule sur le segment de p à q (sp et sq de signes opposés). */
function croisement(p: Coordonnees, q: Coordonnees, sp: number, sq: number): Coordonnees {
  const t = sp / (sp - sq);
  return [p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])];
}

/**
 * Le côté « 1 » du neurone dans le dessin : le polygone convexe où la somme
 * est plus grande que 0, avec son bord, la droite où elle vaut 0, rogné au
 * cadre du dessin. Vide s'il n'a pas d'aire. Sans poids, c'est tout le dessin
 * si b > 0, rien sinon.
 */
export function regionUn(w1: number, w2: number, b: number): Coordonnees[] {
  if (w1 === 0 && w2 === 0) return b > 0 ? [...COINS] : [];
  // Le cadre, rogné par le demi-plan « somme ≥ 0 », son bord compris : c'est l'algorithme de
  // Sutherland et Hodgman.
  const poly: Coordonnees[] = [];
  for (let i = 0; i < COINS.length; i++) {
    const p = COINS[i];
    const q = COINS[(i + 1) % COINS.length];
    const sp = somme(w1, w2, b, p);
    const sq = somme(w1, w2, b, q);
    if (sp >= 0) poly.push(p);
    if ((sp >= 0) !== (sq >= 0) && sp !== 0 && sq !== 0) poly.push(croisement(p, q, sp, sq));
  }
  const sansDoubles = poly.filter((p, i) => !memePoint(p, poly[(i + 1) % poly.length]));
  // L'aire (formule du lacet) : une région réduite à un bord ou à un coin n'est pas dessinée.
  let aire = 0;
  for (let i = 0; i < sansDoubles.length; i++) {
    const [x1, y1] = sansDoubles[i];
    const [x2, y2] = sansDoubles[(i + 1) % sansDoubles.length];
    aire += x1 * y2 - x2 * y1;
  }
  return sansDoubles.length >= 3 && Math.abs(aire) > 1e-12 ? sansDoubles : [];
}

/**
 * La droite où la somme vaut 0, rognée au cadre du dessin : ses deux bouts, ou
 * null sans poids, ou si elle ne traverse pas le dessin (elle peut n'en
 * toucher qu'un coin).
 */
export function droite(w1: number, w2: number, b: number): [Coordonnees, Coordonnees] | null {
  if (w1 === 0 && w2 === 0) return null;
  const points: Coordonnees[] = [];
  for (let i = 0; i < COINS.length; i++) {
    const p = COINS[i];
    const q = COINS[(i + 1) % COINS.length];
    const sp = somme(w1, w2, b, p);
    const sq = somme(w1, w2, b, q);
    if (sp === 0) points.push(p);
    else if (sp * sq < 0) points.push(croisement(p, q, sp, sq));
  }
  const distincts = points.filter((p, i) => points.findIndex((q) => memePoint(p, q)) === i);
  if (distincts.length < 2) return null;
  // Les deux bouts les plus éloignés (deux points distincts, sur un cadre convexe).
  let bouts: [Coordonnees, Coordonnees] = [distincts[0], distincts[1]];
  let loin = -1;
  for (const p of distincts) {
    for (const q of distincts) {
      const d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2;
      if (d > loin) {
        loin = d;
        bouts = [p, q];
      }
    }
  }
  return bouts;
}

/**
 * Ce que l'atelier dit du dessin, en plus du bilan : sans poids, le message du
 * brief ; une droite hors du dessin, la réponse du neurone dans tout le carré
 * de 0 à 1 (il est alors tout entier d'un côté) ; sinon rien.
 */
export function remarque(w1: number, w2: number, b: number): string | null {
  if (w1 === 0 && w2 === 0) return SANS_POIDS;
  if (droite(w1, w2, b) !== null) return null;
  const r = sortieSeuil([w1, w2], b, POINTS[0]);
  return `La droite passe hors du dessin${FINE}: dans tout le carré, le neurone répond ${r}.`;
}

// ---------- L'acquis ----------

/**
 * L'acquis de l'atelier : les 4 points classés, sur ET ou sur OU, par un
 * réglage du lecteur. Le réglage du départ classe déjà OU : il ne compte pas.
 */
export function gagneNeurone(w1: number, w2: number, b: number, porte: Porte): boolean {
  const depart = w1 === W1_DEPART && w2 === W2_DEPART && b === B_DEPART;
  return porte !== 'ou_exclusif' && !depart && bienClasses([w1, w2], b, porte) === NB_POINTS;
}

// ---------- Le défi ----------

/** Les portes déjà classées en entier (ET, OU), pour chaque paire de poids « w1|w2 ». */
export type Reussites = Readonly<Record<string, readonly Porte[]>>;

const cle = (w1: number, w2: number) => `${ecrireReglage(w1)}|${ecrireReglage(w2)}`;

/** Note une porte (ET ou OU) classée en entier avec ces poids ; rend un nouvel objet, ou le même s'il n'y a rien à noter. */
export function noterReussite(r: Reussites, w1: number, w2: number, b: number, porte: Porte): Reussites {
  if (porte === 'ou_exclusif' || bienClasses([w1, w2], b, porte) !== NB_POINTS) return r;
  const k = cle(w1, w2);
  const deja = r[k] ?? [];
  if (deja.includes(porte)) return r;
  return { ...r, [k]: [...deja, porte] };
}

/** Le défi : ET et OU classés avec les mêmes poids, donc en ne changeant que b. */
export function defiReussi(r: Reussites): boolean {
  return Object.values(r).some((portes) => portes.includes('et') && portes.includes('ou'));
}

export const DEFI_NEURONE_REUSSI = `Défi réussi${FINE}: les mêmes poids classent ET et OU, seul b change.`;

/** Où en est le défi, avec les poids du moment. */
export function etatDuDefi(r: Reussites, w1: number, w2: number): string {
  if (defiReussi(r)) return DEFI_NEURONE_REUSSI;
  const faites = r[cle(w1, w2)] ?? [];
  const poids = `w1 = ${ecrireReglage(w1)} et w2 = ${ecrireReglage(w2)}`;
  if (faites.includes('et')) return `ET est classé avec ${poids}${FINE}: garde-les, et trouve b pour OU.`;
  if (faites.includes('ou')) return `OU est classé avec ${poids}${FINE}: garde-les, et trouve b pour ET.`;
  return `Pas encore${FINE}: classe d’abord les ${NB_POINTS} points de ET, ou ceux de OU.`;
}
