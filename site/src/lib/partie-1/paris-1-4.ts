// Les paris du chapitre 1.4, « Le transformer, pièce par pièce », et les phrases de son atelier
// des paramètres.
//
// Leurs bonnes réponses sont calculées : le pari « rope » par le jumeau des angles (rope.ts), le
// pari « parametres » et l'atelier par celui du comptage (parametres.ts, sur les tailles de
// PRESETS_FORGE), et le pari « residus » par le Python lui-même (pieces.bloc, avec et sans ses
// `x +`), dont il lit la section residus des attendus sans refaire le calcul. Si une valeur
// change et qu'une phrase de la page devient fausse, la construction s'arrête (« Exemple
// devenu faux : … »).
//
// Les fonctions reçoivent leurs données en argument (la section residus, la taille de forge) :
// ce module n'importe ni ?raw, ni .json, ni astro:* (P8). Le chapitre leur passe les attendus
// du projet (projet-1-4.ts), les parcours de test le même fichier lu sur le disque. L'atelier
// (AtelierParametres.svelte) y prend ses phrases.

import type { Choix } from '../choix';
import { formaterQuantite } from '../calculateur/formats';
import type { Forme } from '../calculateur/formules';
import { CLES_FORGE, largeurCachee, NOMS_TAILLES, nombreParametres, PRESETS_FORGE, VOCABULAIRE_FORGE, type CleForge } from '../calculateur/ton-ia';
import { exigeur } from '../exiger';
import { nombre, pourcent } from '../nombres';
import { nombresDeTetes, repartitionParametres, type RepartitionParametres } from './parametres';
import { anglesRope } from './rope';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-4.ts et le texte des paris du chapitre 1.4');

/** « «␣très grand␣» » : un nom cité, entre guillemets à espaces fines. */
function cite(nom: string): string {
  return `«${FINE}${nom}${FINE}»`;
}

// ---------- Étape 5 : la figure et le pari « rope » ----------

/** La base des fréquences de RoPE dans forge (`base_rope` de ConfigModele). */
export const BASE_ROPE = 10_000;

/**
 * La tête de la figure : 8 valeurs, donc 4 paires, et les positions de 0 à 32, comme la
 * section rope des attendus du Python. Une tête de ton IA en a 64 : quatre cadrans se lisent
 * mieux que trente-deux.
 */
export const FIGURE_ROPE = Object.freeze({ dimTete: 8, positionMax: 32 });

/**
 * Un angle en radians, écrit en degrés sous chaque cadran : sans décimale à partir de 10°, une
 * de 1 à 10°, deux en dessous (la dernière paire bouge à peine).
 */
export function texteDegres(radians: number): string {
  const degres = (radians * 180) / Math.PI;
  if (degres === 0) return '0°';
  return `${nombre(degres, degres >= 10 ? 0 : degres >= 1 ? 1 : 2)}°`;
}

/** La position du jeton à l'arrivée sur la figure : les aiguilles ont déjà bougé. */
export const POSITION_INITIALE = 3;

/**
 * Le pari « Quelle aiguille tourne le plus vite quand le jeton avance ? ». La bonne réponse
 * vient de anglesRope : l'angle dont chaque paire tourne quand le jeton avance d'une position
 * (son angle à la position 1). Garde : la plus rapide est la première ou la dernière paire, ou
 * toutes vont au même pas, sans quoi aucun choix ne serait juste.
 */
export function choixRopeRapide(dimTete: number = FIGURE_ROPE.dimTete, base: number = BASE_ROPE): Choix[] {
  const pas = anglesRope(1, dimTete, base);
  const n = pas.length;
  exiger(n >= 2, `une tête de ${dimTete} valeurs n’a qu’une paire : « la paire 1 » et « la paire ${n} » seraient la même`);
  let rapide = 0;
  for (let i = 1; i < n; i++) if (pas[i] > pas[rapide]) rapide = i;
  const egales = pas.every((a) => a === pas[0]);
  exiger(egales || rapide === 0 || rapide === n - 1, `la paire la plus rapide est la ${rapide + 1}e, ni la première ni la dernière`);
  return [
    { texte: 'La paire 1', juste: !egales && rapide === 0 },
    { texte: `La paire ${n}`, juste: !egales && rapide === n - 1 },
    { texte: 'Toutes au même pas', juste: egales },
  ];
}

/**
 * Les faits de l'explication du pari « rope » : de combien la paire 1 tourne à chaque position
 * (en radians), combien de fois la dernière paire de la figure est plus lente, et la même chose
 * pour une tête de ton IA (preset très grand : 1 280 ÷ 20 = 64 valeurs, 32 paires).
 */
export function faitsDuPariRope(): {
  radiansPaire1: number;
  degresPaire1: number;
  rapport: number;
  dimTeteTonIA: number;
  pairesTonIA: number;
  rapportTonIA: number;
} {
  const pas = anglesRope(1, FIGURE_ROPE.dimTete, BASE_ROPE);
  const tonIA = PRESETS_FORGE.tres_grand;
  const dimTeteTonIA = tonIA.dim / tonIA.tetes;
  const pasTonIA = anglesRope(1, dimTeteTonIA, BASE_ROPE);
  exiger(pas[0] === 1, 'la paire 1 ne tourne plus d’un radian par position');
  return {
    radiansPaire1: pas[0],
    degresPaire1: (pas[0] * 180) / Math.PI,
    rapport: Math.round(pas[0] / pas[pas.length - 1]),
    dimTeteTonIA,
    pairesTonIA: dimTeteTonIA / 2,
    rapportTonIA: Math.round(pasTonIA[0] / pasTonIA[pasTonIA.length - 1]),
  };
}

// ---------- Étape 8 : le pari « parametres » ----------

/** Les trois grandes familles du pari, et leur nom dans les phrases du chapitre. */
const FAMILLES = ['plongement', 'attention', 'mlp'] as const;
type Famille = (typeof FAMILLES)[number];
const NOMS_DES_FAMILLES: Readonly<Record<keyof RepartitionParametres, string>> = Object.freeze({
  plongement: 'le plongement',
  attention: 'l’attention',
  mlp: 'les MLP',
  normes: 'les RMSNorm',
});

/** La plus lourde des trois grandes familles ; garde : les RMSNorm pèsent moins que chacune. */
function plusLourde(r: RepartitionParametres): Famille {
  let plus: Famille = FAMILLES[0];
  for (const f of FAMILLES) if (r[f] > r[plus]) plus = f;
  exiger(FAMILLES.every((f) => r.normes < r[f]), 'les RMSNorm pèsent plus qu’une des trois grandes familles');
  exiger(FAMILLES.filter((f) => r[f] === r[plus]).length === 1, 'deux familles pèsent exactement autant : le pari n’a plus une seule réponse');
  return plus;
}

/**
 * Le pari « Dans ton IA, où sont la plupart des paramètres ? ». La bonne réponse est la plus
 * grande part de repartitionParametres, pour la taille donnée (très grand, ton IA, par défaut).
 */
export function choixOuSontLesParametres(preset: CleForge = 'tres_grand'): Choix[] {
  const plus = plusLourde(repartitionParametres(PRESETS_FORGE[preset]));
  return [
    { texte: 'Le plongement', juste: plus === 'plongement' },
    { texte: 'L’attention', juste: plus === 'attention' },
    { texte: 'Les MLP', juste: plus === 'mlp' },
  ];
}

/** Les faits de l'explication du pari « parametres » : le total, la répartition et la largeur cachée du MLP. */
export function faitsDuPariParametres(preset: CleForge = 'tres_grand'): {
  total: number;
  repartition: RepartitionParametres;
  largeurCachee: number;
} {
  const f = PRESETS_FORGE[preset];
  const repartition = repartitionParametres(f);
  const total = repartition.plongement + repartition.attention + repartition.mlp + repartition.normes;
  exiger(total === f.parametres, `la répartition de ${preset} ne fait plus son nombre de paramètres`);
  return { total, repartition, largeurCachee: largeurCachee(f.dim) };
}

// ---------- Étape 7 : le pari « residus » ----------

/** Ce que deviennent deux textes après un bloc : la ressemblance de leurs sorties, avec et sans le `x +`. */
export interface RessemblanceParBloc {
  bloc: number;
  avec: number;
  sans: number;
}

/** La section residus des attendus du projet 1.4 (transformer_pas_a_pas/attendus.py). */
export interface ResidusDuPari {
  preset: string;
  couches: number;
  dim: number;
  jetons: number;
  graine: number;
  /** La ressemblance (cosinus) des vecteurs des deux derniers jetons, à l'entrée. */
  entrees: number;
  /** Le plus petit et le plus grand poids d'attention de la dernière position, au premier bloc. */
  poids_attention_min: number;
  poids_attention_max: number;
  par_bloc: RessemblanceParBloc[];
}

/** Les trois tranches du pari « residus », de la ressemblance la plus faible à la plus forte. */
export const TRANCHES_RESIDUS: readonly string[] = Object.freeze([
  `Elle passe${FINE}: on voit toujours quel jeton c’était`,
  'Elle s’estompe, sans disparaître',
  `Elle se perd${FINE}: les deux textes sortent pareils`,
]);

/** La tranche d'une ressemblance : 0 sous 0,5 ; 1 de 0,5 (compris) à 0,999 ; 2 à partir de 0,999. */
export function trancheDeLaRessemblance(r: number): number {
  if (r >= 0.999) return 2;
  if (r >= 0.5) return 1;
  return 0;
}

/**
 * Le pari « Sans le `x +`, que devient l'entrée ? ». La bonne réponse est la tranche de la
 * ressemblance des deux sorties, sans le `x +`, après le dernier bloc, lue dans les attendus.
 */
export function choixResidus(residus: ResidusDuPari): Choix[] {
  exiger(residus.par_bloc.length > 0, 'la section residus n’a aucun bloc');
  const juste = trancheDeLaRessemblance(residus.par_bloc.at(-1)!.sans);
  return TRANCHES_RESIDUS.map((texte, i) => ({ texte, juste: i === juste }));
}

/**
 * Les faits de l'explication du pari « residus », et ses gardes : deux entrées qui ne se
 * ressemblent pas ; sans le `x +`, deux sorties pareilles au dernier bloc, mais pas encore au
 * premier ; avec, deux sorties qui restent distinctes ; et au premier bloc, une attention
 * presque égale entre les jetons (chaque poids entre la moitié et le double de 1 / jetons).
 */
export function faitsDuPariResidus(residus: ResidusDuPari): {
  couches: number;
  premier: RessemblanceParBloc;
  dernier: RessemblanceParBloc;
  milliardieme: boolean;
  uniforme: number;
} {
  const { par_bloc: blocs, jetons } = residus;
  exiger(blocs.length === residus.couches, `la section residus a ${blocs.length} blocs pour ${residus.couches} couches`);
  const premier = blocs[0];
  const dernier = blocs.at(-1)!;
  exiger(Math.abs(residus.entrees) < 0.5, 'les vecteurs des deux derniers jetons se ressemblent déjà à l’entrée');
  exiger(dernier.sans >= 0.999, 'sans le x +, les deux textes ne sortent plus pareils');
  exiger(premier.sans < 0.999, 'sans le x +, les deux textes sortent déjà pareils après le premier bloc');
  exiger(dernier.avec < 0.999, 'avec le x +, les deux textes sortent pareils eux aussi');
  const uniforme = 1 / jetons;
  exiger(
    residus.poids_attention_min > uniforme / 2 && residus.poids_attention_max < 2 * uniforme,
    'au premier bloc, l’attention n’est plus presque égale entre les jetons',
  );
  return { couches: blocs.length, premier, dernier, milliardieme: 1 - dernier.sans < 1e-9, uniforme };
}

// ---------- Étape 8 : l'atelier des paramètres ----------

/** La largeur des vecteurs se règle de 64 en 64, de 64 à 2 048 nombres par jeton. */
export const DIM_MIN = 64;
export const DIM_MAX = 2048;
export const PAS_DIM = 64;
/** De 1 à 48 blocs. */
export const COUCHES_MIN = 1;
export const COUCHES_MAX = 48;
/** Le défi : une taille sous 100 millions de paramètres. */
export const SEUIL_DU_DEFI = 100_000_000;

/** Ce que l'atelier sait d'un réglage. */
export interface EtatDeLAtelier {
  forme: Forme;
  /** Les nombres de têtes possibles pour cette largeur (nombresDeTetes). */
  tetesPossibles: number[];
  repartition: RepartitionParametres;
  /** Le nombre de paramètres, celui de nombreParametres. */
  total: number;
  /** Le total, écrit à la française : « 433 573 120 ». */
  totalTexte: string;
  /** La taille de forge qui a exactement ces réglages, ou null. */
  preset: CleForge | null;
}

/**
 * L'état de l'atelier pour une largeur, un nombre de blocs et un nombre de têtes. Le vocabulaire
 * et le contexte sont ceux de ton IA. Refuse un nombre de têtes que forge refuserait.
 */
export function etatDeLAtelier(dim: number, couches: number, tetes: number): EtatDeLAtelier {
  const tetesPossibles = nombresDeTetes(dim);
  if (!tetesPossibles.includes(tetes)) {
    throw new RangeError(
      `etatDeLAtelier${FINE}: ${tetes} têtes ne partagent pas ${dim} nombres en parts paires. ` +
        `Choisis parmi ${tetesPossibles.join(', ')} (tetesVoisines donne le plus proche).`,
    );
  }
  const contexte = PRESETS_FORGE.tres_grand.contexte;
  const total = nombreParametres({ tailleVocabulaire: VOCABULAIRE_FORGE, dim, couches, tetes, longueurContexte: contexte });
  const forme: Forme = { parametres: total, couches, dim, tetes, tetesKv: tetes, contexte, vocabulaire: VOCABULAIRE_FORGE };
  const repartition = repartitionParametres(forme);
  const preset = CLES_FORGE.find((cle) => {
    const f = PRESETS_FORGE[cle];
    return f.dim === dim && f.couches === couches && f.tetes === tetes;
  });
  return { forme, tetesPossibles, repartition, total, totalTexte: nombre(total), preset: preset ?? null };
}

/**
 * Le nombre de têtes à garder quand la largeur change : le même s'il est encore possible, sinon
 * le possible le plus proche, le plus petit des deux à égalité.
 */
export function tetesVoisines(dim: number, tetes: number): number {
  const possibles = nombresDeTetes(dim);
  exiger(possibles.length > 0, `aucun nombre de têtes ne partage ${dim} nombres en parts paires`);
  let meilleur = possibles[0];
  for (const t of possibles) {
    if (Math.abs(t - tetes) < Math.abs(meilleur - tetes)) meilleur = t;
  }
  return meilleur;
}

/** La fin de la phrase de l'atelier : « ton IA aurait 433 573 120 paramètres : 60 % dans les MLP, … ». */
export function phraseDeLAtelier(etat: EtatDeLAtelier): string {
  const r = etat.repartition;
  const familles = [...FAMILLES].sort((a, b) => r[b] - r[a]);
  const parts = familles.map((f) => `${pourcent(r[f] / etat.total)} dans ${NOMS_DES_FAMILLES[f]}`);
  return `ton IA aurait ${etat.totalTexte} paramètres${FINE}: ${parts.join(', ')}.`;
}

/** Le nom d'une famille dans le tableau de l'atelier, avec une majuscule. */
export function nomDeLaFamille(famille: keyof RepartitionParametres): string {
  const nom = NOMS_DES_FAMILLES[famille];
  return nom.charAt(0).toUpperCase() + nom.slice(1);
}

/** Le défi : une taille sous 100 millions de paramètres où les MLP pèsent plus que le plongement. */
export function etatDuDefi(etat: EtatDeLAtelier): { reussi: boolean; texte: string } {
  const { mlp, plongement } = etat.repartition;
  const quantite = formaterQuantite(etat.total);
  if (etat.total >= SEUIL_DU_DEFI) {
    return { reussi: false, texte: `Pas encore${FINE}: ${quantite} de paramètres, c’est plus de 100 millions.` };
  }
  if (mlp <= plongement) {
    return {
      reussi: false,
      texte: `Pas encore${FINE}: les MLP portent ${formaterQuantite(mlp)} de paramètres, le plongement ${formaterQuantite(plongement)}.`,
    };
  }
  return { reussi: true, texte: `Défi réussi${FINE}: ${quantite} de paramètres, et les MLP en portent plus que le plongement.` };
}

/** Où se place le réglage parmi les cinq tailles de forge, rangées de la plus petite à la plus grande. */
export function placeParmiLesTailles(etat: EtatDeLAtelier): string {
  if (etat.preset !== null) return `C’est la taille ${cite(NOMS_TAILLES[etat.preset])} de forge.`;
  const meme = CLES_FORGE.find((cle) => PRESETS_FORGE[cle].parametres === etat.total);
  if (meme !== undefined) return `Autant de paramètres que ${cite(NOMS_TAILLES[meme])}, avec d’autres têtes.`;
  const premier = CLES_FORGE[0];
  const dernier = CLES_FORGE[CLES_FORGE.length - 1];
  if (etat.total < PRESETS_FORGE[premier].parametres) return `Plus petite que ${cite(NOMS_TAILLES[premier])}.`;
  if (etat.total > PRESETS_FORGE[dernier].parametres) return `Plus grande que ${cite(NOMS_TAILLES[dernier])}.`;
  for (let i = 1; i < CLES_FORGE.length; i++) {
    if (etat.total < PRESETS_FORGE[CLES_FORGE[i]].parametres) {
      return `Entre ${cite(NOMS_TAILLES[CLES_FORGE[i - 1]])} et ${cite(NOMS_TAILLES[CLES_FORGE[i]])}.`;
    }
  }
  throw new Error('placeParmiLesTailles : les tailles de forge ne sont plus rangées de la plus petite à la plus grande.');
}
