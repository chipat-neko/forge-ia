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
// .json, ni astro:* (P8). Le chapitre leur passe TEXTE_DU_SITE et PERPLEXITES
// (texte-1-1.ts), les parcours de test le texte et les attendus lus sur le
// disque. L'atelier (AtelierModeleDeLangage.svelte) y prend ses réglages, ses
// messages et son défi.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { comparerPointsDeCode } from '../points-de-code';
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

/** Ce que le pari « suivant » montre d'un contexte. */
export interface FaitsDuPariSuivant {
  contexte: string;
  /** Les caractères qui suivent le contexte dans le texte d'apprentissage, et leurs comptes, du plus fréquent au moins fréquent. */
  suivants: [string, number][];
  /** Le nombre de fois que le contexte est suivi d'un caractère. */
  total: number;
  /** Le nombre de caractères de l'alphabet. */
  v: number;
  /** Les deux premiers caractères de la distribution lissée, avec leur probabilité. */
  premier: [string, number];
  deuxieme: [string, number];
  /** Le caractère le plus fréquent du texte d'apprentissage qui ne suit jamais le contexte, et son compte. */
  troisieme: { caractere: string; fois: number };
}

/** Les faits du pari pour un contexte, ou null s'il ne passe pas les gardes. */
function faitsDuContexte(
  contexte: string,
  comptes: Comptes,
  frequences: Map<string, number>,
  lettres: readonly string[],
): FaitsDuPariSuivant | null {
  // Garde 1 : le contexte apparaît dans le texte d'apprentissage.
  const vus = comptes.get(contexte);
  if (vus === undefined) return null;
  const d = distribution(comptes, lettres, contexte, N_DU_PARI);
  // Garde 2 : le premier caractère de la distribution est seul en tête.
  if (d.length < 2 || !(d[0][1] > d[1][1])) return null;
  const premier = d[0];
  const deuxieme = d[1];
  // Le troisième choix : le plus fréquent du texte qui ne suit jamais le contexte (à égalité, le plus petit point de code).
  const candidats = [...frequences]
    .filter(([c]) => !vus.has(c) && c !== premier[0] && c !== deuxieme[0])
    .sort(([a, na], [b, nb]) => nb - na || comparerPointsDeCode(a, b));
  if (candidats.length === 0) return null;
  let total = 0;
  for (const k of vus.values()) total += k;
  return {
    contexte,
    suivants: [...vus].sort(([a, na], [b, nb]) => nb - na || comparerPointsDeCode(a, b)),
    total,
    v: lettres.length,
    premier,
    deuxieme,
    troisieme: { caractere: candidats[0][0], fois: candidats[0][1] },
  };
}

function faitsDuTexte(texte: string): FaitsDuPariSuivant {
  const { entrainement, lettres } = modele(texte);
  const comptes = compter(entrainement, N_DU_PARI);
  const frequences = compter(entrainement, 0).get('') ?? new Map<string, number>();
  const faits = faitsDuContexte(CONTEXTE_DU_PARI, comptes, frequences, lettres);
  if (faits !== null) return faits;
  // CONTEXTE_DU_PARI ne passe plus les gardes (le texte a changé) : on prend le
  // premier contexte de N_DU_PARI caractères du texte d'apprentissage qui les
  // passe toutes. La page reste juste, avec un autre contexte ; ses phrases
  // propres à « ton I » sont gardées par exiger dans le chapitre.
  const points = Array.from(entrainement);
  for (let i = N_DU_PARI; i <= points.length; i++) {
    const autre = faitsDuContexte(points.slice(i - N_DU_PARI, i).join(''), comptes, frequences, lettres);
    if (autre !== null) return autre;
  }
  exiger(false, `aucun contexte de ${N_DU_PARI} caractères n’a un premier suivant seul en tête, avec un troisième choix`);
  throw new Error('jamais atteint : exiger a levé l’erreur');
}

/** Le contexte du pari « suivant » : CONTEXTE_DU_PARI s'il passe les gardes, sinon le premier qui les passe. */
export function contexteDuPari(texte: string): string {
  return faitsDuTexte(texte).contexte;
}

/** Les faits du pari « suivant », pour son explication. */
export function faitsDuPariSuivant(texte: string): FaitsDuPariSuivant {
  return faitsDuTexte(texte);
}

/**
 * Le pari « Quel caractère suit le plus souvent « ton I » ? ». Les choix : le
 * premier caractère de la distribution (le juste), le deuxième, et le
 * caractère le plus fréquent du texte qui ne suit jamais ce contexte. Ils sont
 * rangés par point de code : la bonne réponse n'a pas de place fixe.
 */
export function choixSuivant(texte: string): Choix[] {
  const { premier, deuxieme, troisieme } = faitsDuTexte(texte);
  const choix = [premier[0], deuxieme[0], troisieme.caractere]
    .sort(comparerPointsDeCode)
    .map((c) => ({ texte: `« ${visible(c)} »`, juste: c === premier[0] }));
  exiger(new Set(choix.map((c) => c.texte)).size === 3, 'deux choix du pari « suivant » s’affichent de la même façon');
  return choix;
}

/** « un retour à la ligne », « une espace » : le nom d'un blanc avec son article. */
export function unBlanc(nom: string): string {
  return `${nom === 'retour à la ligne' ? 'un' : 'une'} ${nom}`;
}

/**
 * Ce que sont les choix du pari « suivant » qui ne se voient pas, dans l'ordre
 * des choix : « « ↵ » est un retour à la ligne, et « ␣ » une espace. », ou
 * null s'il n'y en a pas. Le texte est brut : la page le typographie.
 */
export function blancsDuPariSuivant(texte: string): string | null {
  const { premier, deuxieme, troisieme } = faitsDuTexte(texte);
  const blancs = [premier[0], deuxieme[0], troisieme.caractere]
    .sort(comparerPointsDeCode)
    .flatMap((c) => {
      const nom = nomDuBlanc(c);
      return nom === null ? [] : [`« ${visible(c)} »`, unBlanc(nom)];
    });
  if (blancs.length === 0) return null;
  const [premierBlanc, premierNom, ...autres] = blancs;
  let phrase = `${premierBlanc} est ${premierNom}`;
  for (let i = 0; i < autres.length; i += 2) phrase += `${i === autres.length - 2 ? ', et' : ','} ${autres[i]} ${autres[i + 1]}`;
  return `${phrase}.`;
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

/** Une ligne des perplexités du Python (PERPLEXITES, texte-1-1.ts). */
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
