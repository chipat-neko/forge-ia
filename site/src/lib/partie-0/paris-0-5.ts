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
// chapitre l'importe. Il prend à paris-0-4.ts l'explication du pari « petite »,
// à laquelle renvoie la phrase de l'étape 8 ; de mesures.ts, seulement un type. Les fonctions qui lisent les attendus ou la sortie du
// script les reçoivent en argument : le MDX les importe, les parcours et
// Vitest les lisent sur le disque.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { decimalesUtiles, nombre } from '../nombres';
import { ecrirePoint } from './atelier-neurone';
import type { MesuresChrono } from './mesures';
import { meilleurReglage, POINTS, PORTES } from './neurone';
import { explicationPetite } from './paris-0-4';

const FINE = '\u202F';
/** L'espace insécable ordinaire, dans un point du tableau (« (0, 1) ») : la case ne s'y coupe pas. */
const INSECABLE = '\u00A0';
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
 * et 1 − p (la chance que le réseau donne à la réponse 0 : ici la bonne
 * réponse, pas la pente). Tous écrits avec les décimales de p.
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
 * exclusif, la réponse du réseau à 3 décimales, et son arrondi. Le point est
 * écrit pour l'affichage, avec une espace insécable après la virgule : sa case
 * ne se coupe pas sur un téléphone.
 */
export function lignesPredictions(e: AttendusEntrainement): string[][] {
  verifierEntrainement(e);
  return POINTS.map((x, i) => [
    ecrirePoint(x).replace(', ', `,${INSECABLE}`),
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

// ---------- Les durées des sorties : la carte contre le processeur ----------

/** La carte est « la plus lente » si elle met au moins 10 % de temps de plus que le processeur. */
export const SEUIL_PLUS_LENTE = 1.1;

/** La durée de l'entraînement PyTorch dans une sortie du script, telle qu'il l'écrit et en nombre. */
export interface DureeDeSortie {
  /** Le nombre de pas, tel que le script l'écrit (« 3 000 », l'espace fine comprise). */
  pas: string;
  appareil: 'cpu' | 'cuda';
  /** La durée telle que le script l'écrit, sans « ms » : « 439 », « 2 307 », « 0,50 ». */
  texte: string;
  millisecondes: number;
}

/**
 * La durée de l'entraînement PyTorch dans une sortie enregistrée du script
 * (sorties/*.txt), lue sur la ligne « 3 000 pas sur … (cpu) : 439 ms. ». Le
 * nombre est celui du script (au moins 2 chiffres significatifs, espace fine
 * entre les milliers, virgule) : il n'est jamais recalculé.
 */
export function dureeDeLaSortie(texte: string): DureeDeSortie {
  const ligne = new RegExp(
    `^ {2}(\\d[\\d${FINE}]*) pas sur .+ \\((cpu|cuda)\\)${FINE}: (\\d[\\d${FINE}]*(?:,\\d+)?) ms\\.$`,
    'm',
  );
  const m = ligne.exec(texte.replace(/\r\n?/g, '\n'));
  if (m === null) {
    throw new Error(
      'La sortie du projet 0.5 n’a plus sa ligne de durée (« … pas sur … (cpu) : … ms. »). Relance ' +
        '« uv run --extra cpu python -m premier_reseau entrainer --appareil cpu --enregistrer sorties/processeur.txt », ' +
        'ou avec --extra gpu et --appareil cuda pour sorties/rtx-5070-ti.txt, dans projets/0.5-reseau.',
    );
  }
  return {
    pas: m[1],
    appareil: m[2] as 'cpu' | 'cuda',
    texte: m[3],
    millisecondes: Number(m[3].replaceAll(FINE, '').replace(',', '.')),
  };
}

/**
 * La phrase de l'étape 8 : les deux durées, telles que les sorties les
 * écrivent, la carte plus lente, et pourquoi. Elle ne vaut que si la carte met
 * au moins 10 % de temps de plus, pour les mêmes pas : sinon la garde tombe,
 * et la phrase est à revoir. Le renvoi aux petites matrices du chapitre 0.4
 * est gardé par le chapitre 0.5 lui-même (explicationPetite des mesures de 0.4).
 *
 * La boucle de entrainer_pytorch n'attend pas la carte à chaque pas (la perte
 * reste sur l'appareil) : la phrase ne parle donc que du prix pour envoyer
 * chaque calcul. Ce prix n'est pas mesuré à part, et le chrono compte aussi le
 * premier pas, sans tour d'échauffement (paris-0-5.test.ts le vérifie dans le
 * code) : d'où « surtout ».
 */
export function phraseDurees(processeur: DureeDeSortie, carte: DureeDeSortie): string {
  exiger(
    processeur.appareil === 'cpu' && carte.appareil === 'cuda',
    'la phrase des durées attend la sortie du processeur, puis celle de la carte',
  );
  exiger(
    processeur.pas === carte.pas,
    `les deux sorties n’ont pas fait les mêmes pas (${processeur.pas} et ${carte.pas}) : relance-les avec le même projet`,
  );
  exiger(
    carte.millisecondes >= processeur.millisecondes * SEUIL_PLUS_LENTE,
    `la carte (${carte.texte} ms) n’est plus plus lente que le processeur (${processeur.texte} ms) d’au moins 10${FINE}% : ` +
      'la phrase de l’étape 8 (« la carte est la plus lente », le prix fixe) est à revoir',
  );
  return (
    `Pour les mêmes ${processeur.pas} pas, la carte a mis ${carte.texte}${INSECABLE}ms, et le processeur ${processeur.texte}${INSECABLE}ms${FINE}: ` +
    'ici, la carte est la plus lente. ' +
    'Comme sur les petites matrices du chapitre 0.4, c’est surtout que ce petit réseau ne fait que de tout petits calculs' +
    `${FINE}: le prix pour envoyer chacun à la carte dépasse le calcul lui-même. ` +
    'Les deux chronos comptent aussi le premier pas, qui prépare le calcul, alors que le chronomètre du chapitre 0.4 ' +
    'écarte ses premiers tours.'
  );
}

/**
 * La phrase de l'étape 8 renvoie aux « petites matrices du chapitre 0.4 » : leur
 * explication, tirée des mesures de 0.4, doit tenir encore (le processeur au
 * moins aussi rapide au plus petit produit, et le prix fixe de la carte montré
 * par le tableau). Si elle tombe, le message nomme aussi la phrase de 0.5.
 */
export function renvoiAuxPetitesMatrices(cpu: MesuresChrono, carte: MesuresChrono): void {
  try {
    explicationPetite(cpu, carte);
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    exiger(
      false,
      'la phrase des durées de l’étape 8 renvoie aux petites matrices du chapitre 0.4, dont l’explication ne tient ' +
        `plus : revois-la avec elles (${raison})`,
    );
  }
}
