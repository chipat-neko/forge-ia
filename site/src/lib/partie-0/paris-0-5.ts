// Les paris du chapitre 0.5, « Premier réseau de neurones », et ce que le
// chapitre écrit de l'entraînement du réseau 2-2-1.
//
// Les bonnes réponses sont calculées, jamais écrites à la main : par le jumeau
// du neurone (neurone.ts) pour le OU exclusif, par les attendus du Python
// (projets/0.5-reseau/tests/attendus.json) pour les prédictions et les
// graines. Ces attendus passent par exp et log, dont le dernier chiffre change
// d'un système à l'autre : ils sont seulement mis en forme ici, à 3 décimales
// (S1), jamais recalculés. Chaque pari a sa garde : si les données changent au
// point qu'une phrase devienne fausse, la construction s'arrête et dit quoi
// revoir (« Exemple devenu faux : … »).
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* (B1) : le parcours du
// chapitre l'importe. Les fonctions qui lisent les attendus ou la sortie du
// script les reçoivent en argument : le MDX les importe, les parcours et
// Vitest les lisent sur le disque.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { decimalesUtiles, nombre } from '../nombres';
import { ecrirePoint } from './atelier-neurone';
import { meilleurReglage, POINTS, PORTES } from './neurone';

const FINE = '\u202F';
/** Le signe moins de la typographie (U+2212), plus long que le trait d'union. */
const MOINS = '−';
const exiger = exigeur('src/lib/partie-0/paris-0-5.ts et le texte des paris du chapitre 0.5');

/** Les décimales des pertes et des prédictions affichées : les valeurs du fichier, arrondies (S1). */
export const DECIMALES = 3;

/** La section « entrainement » des attendus : le réseau 2-2-1 entraîné à la main sur le OU exclusif. */
export interface AttendusEntrainement {
  graine: number;
  taux: number;
  nb_pas: number;
  /** Le nombre de poids, compté par le Python sur le réseau lui-même. */
  nb_poids: number;
  /** L'entraînement a réussi si la perte finale passe sous ce seuil, et si les réponses arrondies sont justes. */
  seuil_perte: number;
  depart: { w1: number[][]; b1: number[]; w2: number[]; b2: number };
  /** La perte avant le premier pas, puis après chacun : nb_pas + 1 valeurs. */
  pertes: number[];
  /** La réponse du réseau entraîné pour chaque point, dans l'ordre de POINTS. */
  predictions: number[];
}

/** Une ligne de la section « graines » des attendus : un départ au hasard, et s'il apprend. */
export interface AttenduGraine {
  graine: number;
  reussit: boolean;
}

// ---------- Les nombres écrits ----------

/** x en français, avec `decimales` décimales et le signe moins U+2212 ; jamais « −0 ». */
export function ecrireNombre(x: number, decimales = 0): string {
  return nombre(x, decimales).replace(/^[-−]/, MOINS);
}

/** Une perte ou une prédiction des attendus, à 3 décimales : « 0,844 », « 0,997 ». */
export function ecrireValeur(x: number): string {
  return ecrireNombre(x, DECIMALES);
}

/** Vérifie la forme de la section « entrainement » : autant de pertes que de pas plus une, une prédiction par point. */
function verifierEntrainement(e: AttendusEntrainement): void {
  exiger(
    Array.isArray(e.pertes) && e.pertes.length === e.nb_pas + 1 && e.pertes.every(Number.isFinite),
    `la section « entrainement » des attendus n’a pas ${e.nb_pas} + 1 pertes finies (régénère-la : uv run --extra cpu python -m premier_reseau.attendus)`,
  );
  exiger(
    Array.isArray(e.predictions) && e.predictions.length === POINTS.length && e.predictions.every(Number.isFinite),
    `la section « entrainement » des attendus n’a pas une prédiction finie pour chacun des ${POINTS.length} points`,
  );
}

// ---------- Le pari « xor » ----------

/**
 * « Un seul neurone peut-il classer les 4 points du OU exclusif ? » Les choix :
 * oui, ou au mieux 3, ou au mieux 2 points sur 4. Le juste est le meilleur
 * compte de la grille (meilleurReglage, le jumeau du Python). Une droite ne
 * sépare jamais les deux diagonales du carré : 3 est le maximum, quelle que
 * soit la grille. Si le jumeau changeait au point de donner 4 ou moins de 2,
 * la garde tomberait : le pari et l'explication de l'étape 2 seraient à revoir.
 */
export function choixXor(): Choix[] {
  const meilleur = meilleurReglage('ou_exclusif')[0];
  const n = POINTS.length;
  exiger(
    meilleur >= n - 2 && meilleur <= n,
    `le meilleur réglage du OU exclusif classe ${meilleur} points sur ${n} : aucun choix du pari « xor » ne le dit plus`,
  );
  return [
    { texte: 'Oui, avec les bons poids', juste: meilleur === n },
    { texte: `Non${FINE}: au mieux ${n - 1} points sur ${n}`, juste: meilleur === n - 1 },
    { texte: `Non${FINE}: au mieux ${n - 2} points sur ${n}`, juste: meilleur === n - 2 },
  ];
}

// ---------- Le pari « gradient » ----------

/** La sortie du réseau dans le pari « gradient ». */
export const P_DU_PARI = 0.9;
/** La bonne réponse dans le pari « gradient ». */
export const Y_DU_PARI = 0;

/** « La sortie vaut 0,9, la bonne réponse 0 : que vaut p − y ? » */
export function questionGradient(): string {
  const d = decimalesUtiles(P_DU_PARI);
  return `La sortie vaut ${ecrireNombre(P_DU_PARI, d)}, la bonne réponse ${ecrireNombre(Y_DU_PARI)}${FINE}: que vaut p ${MOINS} y${FINE}?`;
}

/**
 * Les choix du pari « gradient » : y − p (le signe à l'envers), p − y (juste),
 * et 1 − p (la chance donnée à la mauvaise réponse). Tous écrits avec les
 * décimales de p.
 */
export function choixGradientSortie(): Choix[] {
  const d = decimalesUtiles(P_DU_PARI);
  const juste = P_DU_PARI - Y_DU_PARI;
  const candidats = [Y_DU_PARI - P_DU_PARI, juste, 1 - P_DU_PARI];
  const textes = candidats.map((x) => ecrireNombre(x, d));
  exiger(new Set(textes).size === candidats.length, `les choix du pari « gradient » (${textes.join(', ')}) ne sont plus tous différents`);
  return candidats.map((x, i) => ({ texte: textes[i], juste: x === juste }));
}

// ---------- Le pari « exact » ----------

/** La plus petite et la plus grande réponse du réseau entraîné, et leur écriture à 3 décimales. */
export function bornesPredictions(e: AttendusEntrainement): { min: number; max: number; texteMin: string; texteMax: string } {
  verifierEntrainement(e);
  let min = e.predictions[0];
  let max = e.predictions[0];
  for (const p of e.predictions) {
    if (p < min) min = p;
    if (p > max) max = p;
  }
  return { min, max, texteMin: ecrireValeur(min), texteMax: ecrireValeur(max) };
}

/** « Après 3 000 pas, le réseau répond-il exactement 0 et 1 ? » */
export function questionExact(e: AttendusEntrainement): string {
  return `Après ${nombre(e.nb_pas)} pas, le réseau répond-il exactement 0 et 1${FINE}?`;
}

/**
 * Les choix du pari « exact ». « Oui » est juste si toutes les prédictions
 * valent exactement 0 ou 1, « Non » si aucune. Un mélange fait tomber la
 * garde : le pari n'aurait plus de bonne réponse simple. Avec « Non » juste,
 * ses bornes, à 3 décimales, ne doivent pas s'écrire 0,000 ni 1,000 : la phrase
 * dirait « il s'en approche » avec des nombres qui ont l'air exacts.
 */
export function choixExact(e: AttendusEntrainement): Choix[] {
  verifierEntrainement(e);
  const exactes = e.predictions.every((p) => p === 0 || p === 1);
  const aucune = e.predictions.every((p) => p !== 0 && p !== 1);
  exiger(
    exactes || aucune,
    'certaines prédictions des attendus valent exactement 0 ou 1, d’autres non : le pari « exact » n’a plus de bonne réponse simple',
  );
  const { texteMin, texteMax } = bornesPredictions(e);
  if (aucune) {
    exiger(
      texteMin !== ecrireValeur(0) && texteMax !== ecrireValeur(1),
      `les prédictions extrêmes s’écrivent ${texteMin} et ${texteMax} à ${DECIMALES} décimales : « il s’en approche » aurait l’air faux`,
    );
  }
  return [
    { texte: 'Oui, exactement', juste: exactes },
    { texte: `Non${FINE}: il s’en approche, de ${texteMin} à ${texteMax}`, juste: aucune },
  ];
}

// ---------- Le pari « coince » ----------

/** Le nombre de départs au hasard (graines) avec lesquels le réseau reste coincé. */
export function nbCoinces(graines: readonly AttenduGraine[]): number {
  return graines.filter((g) => !g.reussit).length;
}

/** « Sur 20 départs au hasard, combien de fois le réseau reste-t-il coincé ? » */
export function questionCoince(graines: readonly AttenduGraine[]): string {
  return `Sur ${nombre(graines.length)} départs au hasard, combien de fois le réseau reste-t-il coincé${FINE}?`;
}

/**
 * Les choix du pari « coince » : jamais, k fois (juste, compté dans les
 * graines), ou à chaque départ. Garde : 1 ≤ k < le nombre de graines, sinon
 * le juste serait l'un des deux autres choix, et l'explication fausse.
 */
export function choixCoince(graines: readonly AttenduGraine[]): Choix[] {
  const k = nbCoinces(graines);
  exiger(
    k >= 1 && k < graines.length,
    `${k} départs coincés sur ${graines.length} : le pari « coince » veut au moins un départ coincé, et pas tous`,
  );
  return [
    { texte: 'Jamais', juste: false },
    { texte: `${nombre(k)} fois`, juste: true },
    { texte: 'À chaque départ', juste: false },
  ];
}

// ---------- La courbe et les prédictions ----------

/** Le nom accessible de la courbe : « Erreur du réseau : 0,844 au pas 0, 0,004 au pas 3 000. », depuis les vraies pertes. */
export function etiquetteCourbe(pertes: readonly number[]): string {
  if (pertes.length < 2 || !pertes.every((p) => Number.isFinite(p) && p >= 0)) {
    throw new RangeError(
      'etiquetteCourbe : il faut au moins deux pertes, finies et positives. Régénère les attendus du projet 0.5 ' +
        '(uv run --extra cpu python -m premier_reseau.attendus).',
    );
  }
  const dernier = pertes.length - 1;
  return `Erreur du réseau${FINE}: ${ecrireValeur(pertes[0])} au pas 0, ${ecrireValeur(pertes[dernier])} au pas ${nombre(dernier)}.`;
}

/**
 * Les lignes du tableau des prédictions : le point, la bonne réponse du OU
 * exclusif, la réponse du réseau à 3 décimales, et son arrondi.
 */
export function lignesPredictions(e: AttendusEntrainement): string[][] {
  verifierEntrainement(e);
  return POINTS.map((x, i) => [
    ecrirePoint(x),
    String(PORTES.ou_exclusif[i]),
    ecrireValeur(e.predictions[i]),
    String(Math.round(e.predictions[i])),
  ]);
}

// ---------- La sortie du script ----------

/** Un écart tel que le script l'écrit (« 2,8 × 10⁻¹⁷ », ou « 0 »), en nombre. */
function lireEcart(texte: string): number {
  if (texte === '0') return 0;
  const m = /^(\d+(?:,\d+)?) × 10([⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)$/.exec(texte);
  if (m === null) throw new RangeError(`L’écart « ${texte} » n’est pas écrit comme « 2,8 × 10⁻¹⁷ ».`);
  const exposant = [...m[2]].map((c) => (c === '⁻' ? '-' : String('⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(c)))).join('');
  return Number(`${m[1].replace(',', '.')}e${exposant}`);
}

/**
 * Les deux écarts que le script affiche (sorties/*.txt) : celui des dérivées
 * de départ, à la main et par autograd, et celui des poids finaux, à la main et
 * par PyTorch. Tels qu'il les écrit, et en nombres.
 */
export function ecartsDeLaSortie(texte: string): { gradients: string; valeurGradients: number; poids: string; valeurPoids: number } {
  const g = new RegExp(`à la main et par autograd${FINE}: plus grand écart ([^\\n]+)\\.\\n`).exec(`${texte}\n`);
  const p = new RegExp(`plus grand écart des poids finaux avec la main${FINE}: ([^\\n]+)\\.\\n`).exec(`${texte}\n`);
  if (g === null || p === null) {
    throw new Error(
      'La sortie du projet 0.5 n’a plus ses deux lignes d’écart (dérivées de départ, poids finaux). Relance ' +
        '« uv run --extra cpu python -m premier_reseau entrainer --appareil cpu --enregistrer sorties/processeur.txt » ' +
        'dans projets/0.5-reseau.',
    );
  }
  return { gradients: g[1], valeurGradients: lireEcart(g[1]), poids: p[1], valeurPoids: lireEcart(p[1]) };
}
