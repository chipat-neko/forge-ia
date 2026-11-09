// Les paris du chapitre 1.1, « Ce qu'est vraiment un modèle de langage », son
// ouverture, et les réglages, les messages et le défi de son atelier.
//
// Leurs bonnes réponses sont calculées par le jumeau du Python (ngrammes.ts),
// sur le texte du site : rien n'est recopié. Si le texte ou le jumeau change et
// qu'une phrase de la page devient fausse, la construction s'arrête
// (« Exemple devenu faux : … »).
//
// Les fonctions qui lisent le texte le reçoivent en argument, et
// choixPerplexite reçoit les perplexités : ce module n'importe ni ?raw, ni
// .json, ni astro:* (P8). Le chapitre leur passe TEXTE_DU_SITE (texte-1-1.ts)
// et PERPLEXITES (perplexites-1-1.ts), les parcours de test le texte et les attendus lus sur le
// disque. L'atelier (AtelierModeleDeLangage.svelte) y prend ses réglages, ses
// messages et son défi.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import {
  alphabet,
  compter,
  compterParOrdre,
  couper,
  distribution,
  generer,
  ORDRE_MAX,
  partJamaisVue,
  tirage,
  tourneEnRond,
  type Comptes,
} from './ngrammes';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-1.ts et le texte des paris du chapitre 1.1');

/** « 1 caractère », « 0 caractère », « 4 caractères » : le singulier pour 0 et 1, comme en français. */
export function caracteres(n: number): string {
  return `${n} ${n > 1 ? 'caractères' : 'caractère'}`;
}

/** Un texte lisible : l'espace devient « ␣ », le retour à la ligne « ↵ », comme les jetons de 1.3 (bpe.ts). */
export function visible(s: string): string {
  return s.replace(/ /g, '␣').replace(/\n/g, '↵');
}

/** Le nom d'un caractère qui ne se voit pas (« espace »), ou null pour un caractère qui se voit. */
export function nomDuBlanc(c: string): string | null {
  if (c === ' ') return 'espace';
  if (c === '\n') return 'retour à la ligne';
  if (c === '\u202F') return 'espace fine';
  if (c === '\u00A0') return 'espace insécable';
  return null;
}

/** Le modèle du chapitre : il apprend sur les 90 premiers % du texte (couper), avec l'alphabet du texte entier. */
function modele(texte: string): { entrainement: string; validation: string; lettres: string[] } {
  const [entrainement, validation] = couper(texte);
  return { entrainement, validation, lettres: alphabet(texte) };
}

// ---------- L'atelier ----------

/** Le contexte écrit dans l'atelier à l'arrivée, et celui de l'ouverture. */
export const CONTEXTE_INITIAL = 'Le forgeron frappe';
/** Le nombre de caractères de contexte de l'atelier : de 0 à 6, 4 à l'arrivée. */
export const N_MIN = 0;
export const N_MAX = ORDRE_MAX;
export const N_INITIAL = 4;
/** Les températures de l'atelier, dans l'ordre des bascules, et celle de l'arrivée. */
export const TEMPERATURES_ATELIER: readonly number[] = Object.freeze([0, 0.5, 1, 2]);
export const TEMPERATURE_INITIALE = 1;
/** La graine de la suite à l'arrivée ; « Tirer encore » l'augmente de 1. */
export const GRAINE_INITIALE = 0;
/** La longueur de la suite écrite par l'atelier, et par le pari « temperature ». */
export const LONGUEUR_SUITE = 200;
/** L'atelier montre au plus ce nombre de barres : les premières, celles qui comptent. */
export const BARRES_MONTREES = 10;
/** Le défi : un contexte de N_DU_DEFI caractères dont le suivant le plus probable est une espace. */
export const N_DU_DEFI = 4;

/** Le message d'un contexte plus court que n caractères. */
export function messageCourt(n: number): string {
  return `Il faut au moins ${caracteres(n)} de contexte${FINE}: écris-en un peu plus.`;
}

/** Le message d'un contexte jamais vu : le modèle a reculé à k caractères. */
export function messageRecul(k: number): string {
  return (
    `Ce contexte n’apparaît jamais dans le texte${FINE}: le modèle raccourcit son contexte à ${caracteres(k)}, ` +
    'le plus long qu’il connaît.'
  );
}

/** Le message d'une suite qui tourne en rond, à température 0. */
export function messageBoucle(): string {
  return `La suite revient sur ses pas${FINE}: à température 0, elle tourne en rond.`;
}

/** Ce que montre l'atelier pour un contexte, un n, une température et une graine. */
export interface EtatAtelier {
  /** Vrai si le contexte a moins de n caractères : rien n'est tiré. */
  court: boolean;
  /** L'ordre que le modèle utilise vraiment, après le recul (n s'il connaît les n derniers caractères). */
  ordre: number;
  /** Les caractères que le modèle regarde : les `ordre` derniers du contexte. */
  regarde: string;
  /** La chance de chaque caractère au tirage (tirage du jumeau), du plus probable au moins probable. */
  chances: [string, number][];
  /** Le contexte, suivi des LONGUEUR_SUITE caractères tirés (generer du jumeau) ; vide si le contexte est trop court. */
  suite: string;
  /** Les messages à montrer, dans l'ordre. */
  messages: string[];
  /** Vrai si le défi est réussi. */
  defi: boolean;
}

/**
 * L'état de l'atelier : le tirage (les barres) et la suite racontent le même
 * tirage, celui du jumeau, avec le même recul du contexte.
 */
export function etatDeLAtelier(
  comptesParOrdre: readonly Comptes[],
  lettres: readonly string[],
  contexte: string,
  n: number,
  temperature: number,
  graine: number,
): EtatAtelier {
  const points = Array.from(contexte);
  if (points.length < n) {
    return { court: true, ordre: n, regarde: '', chances: [], suite: '', messages: [messageCourt(n)], defi: false };
  }
  const [ordre, chances] = tirage(comptesParOrdre, lettres, contexte, n, temperature);
  const suite = generer(comptesParOrdre, lettres, n, contexte, LONGUEUR_SUITE, temperature, graine);
  const messages: string[] = [];
  if (ordre < n) messages.push(messageRecul(ordre));
  if (temperature === 0 && tourneEnRond(suite)) messages.push(messageBoucle());
  return {
    court: false,
    ordre,
    regarde: points.slice(points.length - ordre).join(''),
    chances,
    suite,
    messages,
    defi: n === N_DU_DEFI && ordre === N_DU_DEFI && chances[0][0] === ' ',
  };
}

/** Ce que dit le défi : réussi, ou ce qui manque encore. */
export function etatDuDefi(etat: EtatAtelier, n: number): string {
  if (n !== N_DU_DEFI) return `Pas encore${FINE}: règle le nombre jaune sur ${N_DU_DEFI}.`;
  if (etat.court) return `Pas encore${FINE}: écris au moins ${caracteres(N_DU_DEFI)}.`;
  const vus = `«${FINE}${visible(etat.regarde)}${FINE}»`;
  if (etat.defi) return `Défi réussi${FINE}: après ${vus}, le caractère le plus probable est une espace.`;
  if (etat.ordre < N_DU_DEFI) return `Pas encore${FINE}: ces ${N_DU_DEFI} derniers caractères n’apparaissent jamais dans le texte.`;
  const premier = etat.chances[0][0];
  const nom = nomDuBlanc(premier);
  const cite = nom === null ? `«${FINE}${premier}${FINE}»` : unBlanc(nom);
  return `Pas encore${FINE}: après ${vus}, le plus probable est ${cite}.`;
}

// ---------- L'ouverture ----------

/** L'ouverture regarde le dernier caractère de CONTEXTE_INITIAL, et montre ses cinq suites les plus probables. */
export const N_OUVERTURE = 1;
export const SUITES_OUVERTURE = 5;

/**
 * L'ouverture du chapitre : les SUITES_OUVERTURE caractères les plus probables
 * après CONTEXTE_INITIAL, avec leur probabilité lissée (distribution), ce qui
 * reste aux autres caractères, et combien ils sont.
 */
export function ouvertureDuChapitre(texte: string): {
  contexte: string;
  regarde: string;
  suites: [string, number][];
  reste: number;
  autres: number;
} {
  const { entrainement, lettres } = modele(texte);
  const comptes = compter(entrainement, N_OUVERTURE);
  const points = Array.from(CONTEXTE_INITIAL);
  const regarde = points.slice(points.length - N_OUVERTURE).join('');
  const d = distribution(comptes, lettres, CONTEXTE_INITIAL, N_OUVERTURE);
  const suivants = comptes.get(regarde) ?? new Map<string, number>();
  const suites = d.slice(0, SUITES_OUVERTURE);
  exiger(
    suites.length === SUITES_OUVERTURE && suites.every(([c]) => (suivants.get(c) ?? 0) > 0),
    `les ${SUITES_OUVERTURE} caractères les plus probables après « ${regarde} » ne sont plus tous vus dans le texte : ` +
      'l’ouverture montrerait des égalités du lissage',
  );
  let reste = 0;
  for (const [, p] of d.slice(SUITES_OUVERTURE)) reste += p;
  return { contexte: CONTEXTE_INITIAL, regarde, suites, reste, autres: lettres.length - SUITES_OUVERTURE };
}

// ---------- Étape 2 : le pari « suivant » ----------

/** Le contexte du pari « suivant » et son nombre de caractères. */
export const CONTEXTE_DU_PARI = 'ton I';
export const N_DU_PARI = 5;

/** Ce que le pari « suivant » montre : le seul suivant de « ton I », ses comptes et sa chance lissée. */
export interface FaitsDuPariSuivant {
  contexte: string;
  /** Le seul caractère qui suit le contexte dans le texte d'entraînement. */
  caractere: string;
  /** Combien de fois il le suit : toutes les fois où le contexte est suivi d'un caractère. */
  fois: number;
  /** Le nombre de caractères de l'alphabet. */
  v: number;
  /** Sa chance lissée (distribution), et celle de chacun des autres caractères. */
  p: number;
  pAutre: number;
  /** « Environ une fois sur N » : N = round(1 / p). */
  uneSur: number;
}

/**
 * Les faits du pari « suivant ». Gardes : CONTEXTE_DU_PARI est vu dans le
 * texte d'entraînement, suivi d'un seul caractère (« A ») ; et N = round(1 / p)
 * vaut au moins 3, pour que la bonne réponse ne se confonde pas avec « environ
 * une fois sur deux ».
 */
export function faitsDuPariSuivant(texte: string): FaitsDuPariSuivant {
  const { entrainement, lettres } = modele(texte);
  const comptes = compter(entrainement, N_DU_PARI);
  const suivants = comptes.get(CONTEXTE_DU_PARI);
  exiger(
    suivants !== undefined && suivants.size === 1,
    `« ${CONTEXTE_DU_PARI} » n’est plus suivi d’un seul caractère dans le texte d’entraînement : le pari « suivant » est à revoir`,
  );
  const [[caractere, fois]] = [...suivants!];
  const d = distribution(comptes, lettres, CONTEXTE_DU_PARI, N_DU_PARI);
  exiger(d[0][0] === caractere, 'le premier caractère de la distribution n’est plus le seul suivant vu');
  const p = d[0][1];
  const uneSur = Math.round(1 / p);
  exiger(uneSur >= 3, `la chance lissée de « ${caractere} » vaut environ une fois sur ${uneSur} : le pari « suivant » est à revoir`);
  return { contexte: CONTEXTE_DU_PARI, caractere, fois, v: lettres.length, p, pAutre: d[1][1], uneSur };
}

/**
 * Le pari « Avec le lissage, quelle chance le modèle donne-t-il à « A » après
 * « ton I » ? ». La réponse naïve (« A » le suit à chaque fois : 100 %), une
 * autre fausse (une fois sur deux), et la juste, calculée : environ une fois
 * sur N.
 */
export function choixSuivant(texte: string): Choix[] {
  const { uneSur } = faitsDuPariSuivant(texte);
  return [
    // Pas « 100 % » en tête : Pari.astro afficherait « 100 » en grand, séparé de « % » par une espace ordinaire.
    { texte: `À chaque fois${FINE}: 100${FINE}%`, juste: false },
    { texte: 'Environ une fois sur deux', juste: false },
    { texte: `Environ une fois sur ${uneSur}`, juste: true },
  ];
}

/** « un retour à la ligne », « une espace » : le nom d'un blanc avec son article. */
export function unBlanc(nom: string): string {
  return `${nom === 'retour à la ligne' ? 'un' : 'une'} ${nom}`;
}

// ---------- Étape 3 : le pari « temperature » ----------

/** La suite du pari : LONGUEUR_SUITE caractères après CONTEXTE_INITIAL, avec N_INITIAL caractères de contexte, à température 0. */
export function suiteDuPariTemperature(texte: string): string {
  const { entrainement, lettres } = modele(texte);
  return generer(compterParOrdre(entrainement, N_INITIAL), lettres, N_INITIAL, CONTEXTE_INITIAL, LONGUEUR_SUITE, 0, GRAINE_INITIALE);
}

/**
 * Le pari « À température 0, que donne la suite ? ». Un seul choix juste par
 * construction : la suite tourne en rond, ou elle invente sans fin ; elle ne
 * s'arrête jamais (generer écrit toujours ses LONGUEUR_SUITE caractères).
 */
export function choixTemperature(texte: string): Choix[] {
  const boucle = tourneEnRond(suiteDuPariTemperature(texte));
  return [
    { texte: `Il tourne en rond${FINE}: les mêmes morceaux reviennent`, juste: boucle },
    { texte: 'Il invente sans fin des mots nouveaux', juste: !boucle },
    { texte: 'Il s’arrête au premier point', juste: false },
  ];
}

// ---------- Étape 5 : le pari « contexte » ----------

/** Le n du pari « contexte ». */
export const N_DU_PARI_CONTEXTE = 6;
/** Les trois tranches du pari « contexte ». */
export const TRANCHES: readonly string[] = Object.freeze([
  'Moins d’un sur dix',
  'Entre un sur dix et la moitié',
  'Plus de la moitié',
]);

/** La tranche d'une part : 0 sous un dixième, 1 d'un dixième à la moitié (bornes comprises), 2 au-delà. */
export function trancheDeLaPart(part: number): number {
  if (part < 0.1) return 0;
  if (part <= 0.5) return 1;
  return 2;
}

/**
 * Les faits du pari « contexte » : combien de contextes de N_DU_PARI_CONTEXTE
 * caractères du texte de validation le modèle n'a jamais vus, et combien de
 * contextes différents il a vus dans le texte d'apprentissage.
 */
export function faitsDuPariContexte(texte: string): { n: number; absents: number; total: number; differents: number; v: number } {
  const { entrainement, validation, lettres } = modele(texte);
  const comptes = compter(entrainement, N_DU_PARI_CONTEXTE);
  const [absents, total] = partJamaisVue(comptes, validation, N_DU_PARI_CONTEXTE);
  exiger(total > 0, 'le texte de validation est plus court que le contexte du pari « contexte »');
  return { n: N_DU_PARI_CONTEXTE, absents, total, differents: comptes.size, v: lettres.length };
}

/** Le pari « Quelle part des contextes du texte jamais lu le modèle n'a-t-il jamais vus ? ». */
export function choixContexte(texte: string): Choix[] {
  const { absents, total } = faitsDuPariContexte(texte);
  const juste = trancheDeLaPart(absents / total);
  return TRANCHES.map((t, i) => ({ texte: t, juste: i === juste }));
}

// ---------- Étape 7 : le pari « perplexite » ----------

/** Une ligne des perplexités du Python (PERPLEXITES, perplexites-1-1.ts). */
interface Perplexite {
  n: number;
  entrainement: number;
  validation: number;
}

/** Les n du pari « perplexite ». */
export const NS_DU_PARI_PERPLEXITE: readonly number[] = Object.freeze([1, 3, 6]);

/** Le n de la plus petite perplexité de validation parmi `ns`, qui doit être seule en tête. */
function plusPetite(perplexites: readonly Perplexite[], ns: readonly number[]): Perplexite {
  const parmi = ns.map((n) => {
    const p = perplexites.find((x) => x.n === n);
    exiger(p !== undefined, `la perplexité de n = ${n} manque dans les attendus`);
    return p!;
  });
  const tries = [...parmi].sort((a, b) => a.validation - b.validation);
  exiger(
    tries.length < 2 || tries[0].validation < tries[1].validation,
    `la plus petite perplexité de validation parmi n = ${ns.join(', ')} n’est pas seule en tête`,
  );
  return tries[0];
}

/** Le pari « Avec combien de caractères de contexte le modèle est-il le moins surpris ? », parmi 1, 3 et 6. */
export function choixPerplexite(perplexites: readonly Perplexite[]): Choix[] {
  const meilleur = plusPetite(perplexites, NS_DU_PARI_PERPLEXITE);
  return NS_DU_PARI_PERPLEXITE.map((n) => ({ texte: caracteres(n), juste: n === meilleur.n }));
}

/** Le minimum de toute la courbe de validation (n = 0 à 6), seul en tête. */
export function minimumDesPerplexites(perplexites: readonly Perplexite[]): { n: number; valeur: number } {
  const p = plusPetite(
    perplexites,
    perplexites.map((x) => x.n),
  );
  return { n: p.n, valeur: p.validation };
}
