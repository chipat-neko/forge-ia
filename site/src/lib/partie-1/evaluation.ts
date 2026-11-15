// L'évaluation du chapitre 1.6, « L'évaluation » : les relevés de projets/1.6-evaluation/mesures/
// (evaluation-mini.json, le rapport d'évaluation de la version d'une heure de ton IA, et
// qcm-mini.json, six questions de MMMLU notées par elle), écrits par `python -m evaluation_pas_a_pas`
// (voir le README du projet), et le jumeau TypeScript de la marge et du verdict.
//
// Le chapitre ne refait pas l'évaluation : il lit ces relevés à la construction, avec node:fs, à
// partir de la racine du dépôt qu'on lui donne. Les composants Astro lui passent celle
// d'astro:config/server ; Vitest et les parcours, path.resolve('..') depuis site/. Ce module
// n'importe ni .json ni astro:* : un parcours Playwright peut l'importer.
//
// Le jumeau refait les deux calculs du Python (evaluation_pas_a_pas/pas_a_pas.py, région « marge »),
// avec les mêmes opérations dans le même ordre : marge95 (la marge de Wald, une racine carrée, exacte
// dans les deux langages) et verdictQcm (la règle du rapport de forge : l'exactitude NORMALISÉE comparée
// au hasard, avec la marge du HASARD). Il vit dans marge.ts, sans import, pour que l'atelier des QCM
// (dans le navigateur) s'en serve sans node:fs ; ce module le réexporte. Les tests les comparent, sans
// tolérance, à la grille de projets/1.6-evaluation/tests/attendus.json.
//
// Tant qu'un fichier manque, lireEvaluation, lireQcm et lireEchantillon rendent null : c'était le cas de
// ton IA, la vraie (ton-ia-1.5), jusqu'à son relevé (tâche 15 du plan 5).
//
// Ce module lit aussi les deux sorties de ton IA que montrent les chapitres 1.4 et 1.1 :
// sorties/cartes-ton-ia.json (ses cartes d'attention pour une phrase, la couche et les deux têtes
// choisies par `cartes --choisir`) et sorties/ton-ia-suivants.json (les jetons qu'elle juge les plus
// probables après une phrase). Ces fichiers sont versionnés et ces chapitres ont paru : un fichier
// absent est une erreur, jamais une mesure « à faire ».

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEPOT } from '../depot';
import { marge95, verdictQcm, type Verdict } from './marge';

export { marge95, margeHasard, verdictQcm, Z_95 } from './marge';
export type { Verdict } from './marge';

const FINE = '\u202F';

/** Les deux tests de FrenchBench que le rapport de forge mesure. */
export type NomTestQcm = 'hellaswag' | 'arc';

/** Les mesures d'un test, avec les noms de clés du rapport de forge, plus le verdict. */
export interface MesuresQcm {
  exactitude: number;
  exactitude_normalisee: number;
  hasard: number;
  n: number;
  marge_95: number;
  marge_95_normalisee: number;
  marge_hasard: number;
  total_du_test: number;
  verdict: Verdict;
}

/** Un texte écrit par le modèle à partir d'un début fixe. */
export interface EchantillonEvaluation {
  invite: string;
  suite: string;
  graine: number;
  n_jetons: number;
  s_arrete: boolean;
}

/** Le contenu de mesures/evaluation-<nom>.json. */
export interface Evaluation {
  /** « ton-ia-mini » ou « ton-ia-1.5 ». */
  nom: string;
  /** AAAA-MM-JJ : la date du rapport de forge. */
  releve_le: string;
  pas: number;
  perte_val: number;
  perplexite: number;
  bits_par_octet: number;
  qcm: Record<NomTestQcm, MesuresQcm>;
  echantillons: EchantillonEvaluation[];
}

/** Une question de MMMLU notée par le modèle. */
export interface QuestionQcm {
  contexte: string;
  choix: string[];
  /** Les log-vraisemblances, en nats. */
  scores: number[];
  /** Les mêmes, divisées par les octets de chaque choix. */
  scores_normalises: number[];
  prefere: number;
  bonne: number;
  juste: boolean;
}

/** Le contenu de mesures/qcm-<nom>.json. */
export interface QcmExemples {
  nom: string;
  releve_le: string;
  appareil: string;
  jeu: {
    nom: string;
    configuration: string;
    partie: string;
    adresse: string;
    licence: string;
    licence_verifiee_le: string;
    lu_le: string;
  };
  n: number;
  justes: number;
  hasard: number;
  questions: QuestionQcm[];
}

/** Les relevés d'évaluation, en chemins depuis la racine du dépôt. */
export const FICHIERS_EVALUATION = Object.freeze({
  'ton-ia-mini': 'projets/1.6-evaluation/mesures/evaluation-mini.json',
  'ton-ia-1.5': 'projets/1.6-evaluation/mesures/evaluation-1.5.json',
} as const);

/** Les relevés de QCM notés, en chemins depuis la racine du dépôt. */
export const FICHIERS_QCM = Object.freeze({
  'ton-ia-mini': 'projets/1.6-evaluation/mesures/qcm-mini.json',
  'ton-ia-1.5': 'projets/1.6-evaluation/mesures/qcm-1.5.json',
} as const);

export type NomEvaluation = keyof typeof FICHIERS_EVALUATION;

/** Les sorties de ton IA, la vraie, lues par les chapitres 1.4 et 1.1, en chemins depuis la racine du dépôt. */
export const FICHIERS_SORTIES_TON_IA = Object.freeze({
  cartes: 'projets/1.6-evaluation/sorties/cartes-ton-ia.json',
  suivants: 'projets/1.6-evaluation/sorties/ton-ia-suivants.json',
} as const);

/** La version publiée de ton IA, la vraie : ses poids, sa configuration et son tokenizer, sur GitHub. */
export const VERSION_PUBLIEE = Object.freeze({ nom: 'ton-ia-1.5', adresse: `${DEPOT}/releases/tag/ton-ia-1.5` } as const);

/** Le « début de document » que le modèle a vu avant chaque texte : le premier jeton de chaque carte. */
export const JETON_DE_DEBUT = '<|fin_texte|>';

/** Les deux têtes que `cartes --choisir` garde : celle qui regarde le jeton d'avant, celle qui regarde le plus loin. */
export type RoleDeTete = 'jeton-d-avant' | 'loin';

/** Ce que regarde une tête, en trois nombres (regard_des_tetes du projet 1.6), en moyenne sur la phrase. */
export interface RegardDeTete {
  tete: number;
  /** La part de l'attention donnée au jeton juste avant. */
  jeton_d_avant: number;
  /** Combien de jetons en arrière la tête regarde, sur les mots de la phrase (sans le jeton de début). */
  distance: number;
  /** La part de l'attention posée sur le jeton de début. */
  debut: number;
}

/** Une carte d'attention : une tête, son rôle, son regard, et ses poids, n × n. */
export interface CarteDeTete extends RegardDeTete {
  role: RoleDeTete;
  /** poids[i][j] : la part de l'attention que le jeton i donne au jeton j (0 pour j > i). */
  poids: number[][];
}

/** Le contenu de sorties/cartes-ton-ia.json, écrit par `python -m evaluation_pas_a_pas cartes --choisir`. */
export interface FichierCartes {
  nom: string;
  releve_le: string;
  appareil: string;
  phrase: string;
  /** Le texte de chaque jeton, en commençant par le jeton de début. */
  jetons: string[];
  /** La couche des cartes, à partir de 0, et le nombre de couches et de têtes du modèle. */
  couche: number;
  couches: number;
  tetes: number;
  cartes: CarteDeTete[];
  /** Les chiffres du choix : la meilleure tête de chaque couche pour le jeton d'avant, et le regard de chaque tête de la couche. */
  choix: {
    jeton_d_avant_par_couche: { couche: number; tete: number; jeton_d_avant: number }[];
    regards_de_la_couche: RegardDeTete[];
  };
}

/** Un jeton que le modèle juge probable pour la suite, avec sa probabilité. */
export interface SuivantDuModele {
  jeton: string;
  probabilite: number;
}

/** Le contenu de sorties/ton-ia-suivants.json, écrit par `python -m evaluation_pas_a_pas suivants`. */
export interface FichierSuivants {
  nom: string;
  releve_le: string;
  appareil: string;
  phrase: string;
  /** Du plus probable au moins probable. */
  suivants: SuivantDuModele[];
}

/** Les versions de ton IA que le chapitre 1.6 évalue : « mini », sa version d'une heure, et « 1.5 », ton IA, la vraie. */
export type VersionEvaluee = 'mini' | '1.5';

/** Le relevé de chaque version (les props `nom` de TableauEvaluation et EchantillonsEvaluation). */
export const CLES_DES_VERSIONS: Readonly<Record<VersionEvaluee, NomEvaluation>> = Object.freeze({
  mini: 'ton-ia-mini',
  '1.5': 'ton-ia-1.5',
});

/** Comment le chapitre nomme chaque version, au fil d'une phrase. */
export const QUI_EST_EVALUE: Readonly<Record<VersionEvaluee, string>> = Object.freeze({
  mini: 'la version d’une heure de ton IA',
  '1.5': 'ton IA',
});

const REFAIRE =
  'Relance le relevé avec « python -m evaluation_pas_a_pas » (voir le README de projets/1.6-evaluation), ' +
  'ou corrige le fichier.';
const DOSSIER_DU_PROJET = 'projets/1.6-evaluation';
const TESTS: readonly NomTestQcm[] = ['hellaswag', 'arc'];
const VERDICTS: readonly string[] = ['au-dessus', 'pas-different', 'en-dessous'];

// --- Vérifier un relevé ------------------------------------------------------------------------

function objet(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

function fini(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

function entier(x: unknown, minimum: number): x is number {
  return typeof x === 'number' && Number.isInteger(x) && x >= minimum;
}

function proportion(x: unknown): x is number {
  return fini(x) && x >= 0 && x <= 1;
}

function datee(x: unknown): x is string {
  return typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x);
}

/** Deux nombres qui ne diffèrent que de l'arrondi d'un calcul (relatif ou absolu, au 10⁻⁹ près). */
function proches(a: number, b: number): boolean {
  return Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
}

/**
 * Vérifie qu'une valeur lue a le format d'un relevé d'évaluation, et la rend telle quelle. Un écart
 * lève une erreur qui nomme le fichier, le champ, et dit quoi faire : la construction s'arrête plutôt
 * que d'afficher un verdict faux. Rien n'est recalculé, mais les nombres liés entre eux doivent l'être
 * (le verdict suit la règle de forge, la perplexité est exp(perte), les marges suivent marge95).
 */
export function verifierEvaluation(valeur: unknown, fichier: string): Evaluation {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (typeof valeur.nom !== 'string' || valeur.nom.trim() === '') throw faute('nom est vide');
  if (!datee(valeur.releve_le)) throw faute('releve_le doit être une date AAAA-MM-JJ');
  if (!entier(valeur.pas, 1)) throw faute('pas doit être un entier de 1 ou plus');
  for (const cle of ['perte_val', 'perplexite', 'bits_par_octet'] as const) {
    if (!fini(valeur[cle]) || valeur[cle] <= 0) throw faute(`${cle} doit être un nombre positif`);
  }
  if (!proches(Math.exp(valeur.perte_val as number), valeur.perplexite as number)) {
    throw faute(
      `perplexite (${String(valeur.perplexite)}) n’est pas exp(perte_val) (${String(Math.exp(valeur.perte_val as number))})`,
    );
  }

  const qcm = valeur.qcm;
  if (!objet(qcm)) throw faute('qcm manque');
  for (const test of TESTS) {
    const m = qcm[test];
    if (!objet(m)) throw faute(`qcm.${test} manque`);
    for (const cle of ['exactitude', 'exactitude_normalisee', 'hasard'] as const) {
      if (!proportion(m[cle])) throw faute(`qcm.${test}.${cle} doit être une proportion entre 0 et 1`);
    }
    for (const cle of ['marge_95', 'marge_95_normalisee', 'marge_hasard'] as const) {
      if (!fini(m[cle]) || m[cle] < 0) throw faute(`qcm.${test}.${cle} doit être un nombre positif ou nul`);
    }
    if (!entier(m.n, 1)) throw faute(`qcm.${test}.n doit être un entier de 1 ou plus`);
    if (!entier(m.total_du_test, 1) || (m.n as number) > m.total_du_test) {
      throw faute(`qcm.${test}.total_du_test doit être un entier, au moins égal à qcm.${test}.n`);
    }
    if (!proches(marge95(m.exactitude as number, m.n as number), m.marge_95 as number)) {
      throw faute(`qcm.${test}.marge_95 n’est pas la marge de ${String(m.exactitude)} sur ${String(m.n)} questions`);
    }
    if (!proches(marge95(m.exactitude_normalisee as number, m.n as number), m.marge_95_normalisee as number)) {
      throw faute(`qcm.${test}.marge_95_normalisee n’est pas la marge de ${String(m.exactitude_normalisee)} sur ${String(m.n)} questions`);
    }
    if (typeof m.verdict !== 'string' || !VERDICTS.includes(m.verdict)) {
      throw faute(`qcm.${test}.verdict doit être « au-dessus », « pas-different » ou « en-dessous »`);
    }
    const attendu = verdictQcm(m.exactitude_normalisee as number, m.hasard as number, m.marge_hasard as number);
    if (m.verdict !== attendu) {
      throw faute(`qcm.${test}.verdict vaut « ${m.verdict} », mais la règle de forge donne « ${attendu} »`);
    }
  }

  const echantillons = valeur.echantillons;
  if (!Array.isArray(echantillons) || echantillons.length === 0) throw faute('echantillons est vide');
  echantillons.forEach((e: unknown, i: number) => {
    if (
      !objet(e) ||
      typeof e.invite !== 'string' ||
      e.invite === '' ||
      typeof e.suite !== 'string' ||
      !entier(e.graine, 0) ||
      !entier(e.n_jetons, 1) ||
      typeof e.s_arrete !== 'boolean'
    ) {
      throw faute(`echantillons[${i}] n’a pas le format attendu (invite, suite, graine, n_jetons, s_arrete)`);
    }
  });
  return valeur as unknown as Evaluation;
}

/** Vérifie qu'une valeur lue a le format d'un relevé de QCM notés (qcm-<nom>.json), et la rend telle quelle. */
export function verifierQcm(valeur: unknown, fichier: string): QcmExemples {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (typeof valeur.nom !== 'string' || valeur.nom.trim() === '') throw faute('nom est vide');
  if (!datee(valeur.releve_le)) throw faute('releve_le doit être une date AAAA-MM-JJ');
  if (typeof valeur.appareil !== 'string' || valeur.appareil === '') throw faute('appareil est vide');
  const jeu = valeur.jeu;
  if (!objet(jeu)) throw faute('jeu manque');
  for (const cle of ['nom', 'configuration', 'partie', 'adresse', 'licence'] as const) {
    if (typeof jeu[cle] !== 'string' || jeu[cle] === '') throw faute(`jeu.${cle} est vide`);
  }
  if (!/^https:\/\//.test(jeu.adresse as string)) throw faute('jeu.adresse doit être une adresse https');
  if (!datee(jeu.licence_verifiee_le) || !datee(jeu.lu_le)) {
    throw faute('jeu.licence_verifiee_le et jeu.lu_le doivent être des dates AAAA-MM-JJ');
  }
  if (!entier(valeur.n, 1)) throw faute('n doit être un entier de 1 ou plus');
  const questions = valeur.questions;
  if (!Array.isArray(questions) || questions.length !== valeur.n) throw faute('questions doit avoir n éléments');
  let justes = 0;
  questions.forEach((q: unknown, i: number) => {
    const bon =
      objet(q) &&
      typeof q.contexte === 'string' &&
      Array.isArray(q.choix) &&
      q.choix.length >= 2 &&
      q.choix.every((c: unknown) => typeof c === 'string') &&
      Array.isArray(q.scores) &&
      q.scores.length === q.choix.length &&
      q.scores.every(fini) &&
      Array.isArray(q.scores_normalises) &&
      q.scores_normalises.length === q.choix.length &&
      q.scores_normalises.every(fini) &&
      entier(q.prefere, 0) &&
      q.prefere < q.choix.length &&
      entier(q.bonne, 0) &&
      q.bonne < q.choix.length &&
      typeof q.juste === 'boolean' &&
      q.juste === (q.prefere === q.bonne);
    if (!bon) {
      throw faute(`questions[${i}] n’a pas le format attendu (contexte, choix, scores, scores_normalises, prefere, bonne, juste)`);
    }
    if ((q as unknown as QuestionQcm).juste) justes += 1;
  });
  if (valeur.justes !== justes) throw faute(`justes vaut ${String(valeur.justes)}, mais ${justes} questions sont justes`);
  if (!proportion(valeur.hasard)) throw faute('hasard doit être une proportion entre 0 et 1');
  return valeur as unknown as QcmExemples;
}

const REFAIRE_CARTES =
  'Relance « python -m evaluation_pas_a_pas cartes --modele <dossier de ton-ia-1.5> --phrase … --choisir --appareil cpu ' +
  '--json sorties/cartes-ton-ia.json » (voir le README de projets/1.6-evaluation), ou corrige le fichier.';
const REFAIRE_SUIVANTS =
  'Relance « python -m evaluation_pas_a_pas suivants --modele <dossier de ton-ia-1.5> --phrase … --appareil cpu ' +
  '--json sorties/ton-ia-suivants.json » (voir le README de projets/1.6-evaluation), ou corrige le fichier.';
const ROLES: readonly RoleDeTete[] = ['jeton-d-avant', 'loin'];
/** Une ligne de poids, arrondis à 6 décimales par le projet, fait 1 à 10⁻⁴ près (README du projet 1.6). */
const TOLERANCE_LIGNE = 1e-4;

/** Le regard d'une tête est-il bien formé : trois nombres, deux parts entre 0 et 1, une distance positive ? */
function regardForme(r: Record<string, unknown>): boolean {
  return proportion(r.jeton_d_avant) && fini(r.distance) && r.distance >= 0 && proportion(r.debut);
}

/**
 * Vérifie qu'une valeur lue a le format du fichier des cartes d'attention (sorties/cartes-ton-ia.json),
 * et la rend telle quelle. Rien n'est recalculé : les nombres viennent du projet 1.6. Mais ce que le
 * chapitre 1.4 en dit doit tenir : des cartes du processeur, des poids qui ne regardent jamais la suite
 * et font 1 à chaque ligne, le regard de chaque carte égal à celui des chiffres du choix, et le choix
 * fait par la règle du projet (la couche de la tête qui regarde le plus le jeton d'avant ; dans cette
 * couche, cette tête, puis celle qui regarde le plus loin parmi les autres).
 */
export function verifierCartes(valeur: unknown, fichier: string): FichierCartes {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE_CARTES}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (typeof valeur.nom !== 'string' || valeur.nom.trim() === '') throw faute('nom est vide');
  if (!datee(valeur.releve_le)) throw faute('releve_le doit être une date AAAA-MM-JJ');
  if (valeur.appareil !== 'cpu') {
    throw faute(`appareil vaut « ${String(valeur.appareil)} » : le site ne montre que des cartes calculées sur le processeur (cpu)`);
  }
  if (typeof valeur.phrase !== 'string' || valeur.phrase.trim() === '') throw faute('phrase est vide');
  const jetons = valeur.jetons;
  if (!Array.isArray(jetons) || jetons.length < 3 || !jetons.every((j: unknown) => typeof j === 'string')) {
    throw faute('jetons doit être une liste d’au moins trois textes : le jeton de début, puis au moins deux jetons de la phrase');
  }
  if (jetons[0] !== JETON_DE_DEBUT) throw faute(`le premier jeton doit être ${JETON_DE_DEBUT}, le début de document du modèle`);
  const n = jetons.length;
  if (!entier(valeur.couches, 1) || !entier(valeur.tetes, 1)) throw faute('couches et tetes doivent être des entiers de 1 ou plus');
  const couches = valeur.couches;
  const tetes = valeur.tetes;
  if (!entier(valeur.couche, 0) || valeur.couche >= couches) throw faute(`couche doit être un entier de 0 à ${couches - 1}`);

  const cartes = valeur.cartes;
  if (!Array.isArray(cartes) || cartes.length !== ROLES.length) throw faute(`cartes doit avoir ${ROLES.length} entrées, une par rôle`);
  cartes.forEach((c: unknown, k: number) => {
    const ou = `cartes[${k}]`;
    if (!objet(c)) throw faute(`${ou} n’est pas un objet`);
    if (!entier(c.tete, 0) || c.tete >= tetes) throw faute(`${ou}.tete doit être un entier de 0 à ${tetes - 1}`);
    if (typeof c.role !== 'string' || !(ROLES as readonly string[]).includes(c.role)) {
      throw faute(`${ou}.role doit valoir ${ROLES.map((r) => `« ${r} »`).join(' ou ')}`);
    }
    if (!regardForme(c)) throw faute(`${ou} doit avoir jeton_d_avant et debut entre 0 et 1, et une distance positive ou nulle`);
    const poids = c.poids;
    if (!Array.isArray(poids) || poids.length !== n) throw faute(`${ou}.poids doit avoir une ligne par jeton (${n})`);
    poids.forEach((ligne: unknown, i: number) => {
      const ici = `${ou}.poids[${i}]`;
      if (!Array.isArray(ligne) || ligne.length !== n || !ligne.every(proportion)) {
        throw faute(`${ici} doit avoir ${n} nombres entre 0 et 1`);
      }
      for (let j = i + 1; j < n; j++) {
        if (ligne[j] !== 0) throw faute(`${ici} regarde le jeton ${j}, qui vient après lui : le masque l’interdit`);
      }
      let total = 0;
      for (const p of ligne as number[]) total += p;
      if (Math.abs(total - 1) > TOLERANCE_LIGNE) throw faute(`${ici} fait ${String(total)} en tout, au lieu de 1`);
    });
  });
  const [a, b] = cartes as CarteDeTete[];
  if (a.tete === b.tete) throw faute(`les deux cartes montrent la même tête (${a.tete})`);
  if (a.role === b.role) throw faute(`les deux cartes ont le même rôle (« ${a.role} »)`);

  const choix = valeur.choix;
  if (!objet(choix)) throw faute('choix manque');
  const parCouche = choix.jeton_d_avant_par_couche;
  if (
    !Array.isArray(parCouche) ||
    parCouche.length !== couches ||
    !parCouche.every((x: unknown, c: number) => objet(x) && x.couche === c && entier(x.tete, 0) && x.tete < tetes && proportion(x.jeton_d_avant))
  ) {
    throw faute(`choix.jeton_d_avant_par_couche doit avoir une entrée par couche (${couches}), dans l’ordre`);
  }
  const regards = choix.regards_de_la_couche;
  if (
    !Array.isArray(regards) ||
    regards.length !== tetes ||
    !regards.every((r: unknown, t: number) => objet(r) && r.tete === t && regardForme(r))
  ) {
    throw faute(`choix.regards_de_la_couche doit avoir le regard de chaque tête de la couche (${tetes}), dans l’ordre`);
  }
  const R = regards as RegardDeTete[];
  (cartes as CarteDeTete[]).forEach((c, k) => {
    const r = R[c.tete];
    if (c.jeton_d_avant !== r.jeton_d_avant || c.distance !== r.distance || c.debut !== r.debut) {
      throw faute(`cartes[${k}] n’a pas le regard de sa tête (${c.tete}) dans choix.regards_de_la_couche`);
    }
  });

  // Le choix, refait sur les chiffres du fichier (sans les recalculer) : à égalité, n'importe laquelle des ex æquo.
  const avant = (cartes as CarteDeTete[]).find((c) => c.role === 'jeton-d-avant')!;
  const loin = (cartes as CarteDeTete[]).find((c) => c.role === 'loin')!;
  const meilleure = R.find((r) => r.jeton_d_avant > avant.jeton_d_avant);
  if (meilleure !== undefined) {
    throw faute(`la tête « jeton-d-avant » (${avant.tete}) n’est plus celle de sa couche qui regarde le plus le jeton d’avant : la tête ${meilleure.tete} le regarde plus`);
  }
  const plusLoin = R.find((r) => r.tete !== avant.tete && r.distance > loin.distance);
  if (plusLoin !== undefined) {
    throw faute(`la tête « loin » (${loin.tete}) n’est plus celle qui regarde le plus loin parmi les autres têtes de sa couche : la tête ${plusLoin.tete} regarde plus loin`);
  }
  const ici = (parCouche as FichierCartes['choix']['jeton_d_avant_par_couche'])[valeur.couche];
  if (ici.tete !== avant.tete || ici.jeton_d_avant !== avant.jeton_d_avant) {
    throw faute(`choix.jeton_d_avant_par_couche[${valeur.couche}] ne donne plus la tête « jeton-d-avant » de la couche choisie`);
  }
  const autre = (parCouche as FichierCartes['choix']['jeton_d_avant_par_couche']).find((x) => x.jeton_d_avant > ici.jeton_d_avant);
  if (autre !== undefined) {
    throw faute(`la couche ${valeur.couche} n’est plus celle de la tête qui regarde le plus le jeton d’avant : la couche ${autre.couche} le regarde plus`);
  }
  return valeur as unknown as FichierCartes;
}

/**
 * Vérifie qu'une valeur lue a le format du fichier des jetons suivants (sorties/ton-ia-suivants.json),
 * et la rend telle quelle : des jetons tous différents, du plus probable au moins probable, avec des
 * probabilités entre 0 (exclu) et 1 qui ne font pas plus que 1 à elles toutes.
 */
export function verifierSuivants(valeur: unknown, fichier: string): FichierSuivants {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE_SUIVANTS}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (typeof valeur.nom !== 'string' || valeur.nom.trim() === '') throw faute('nom est vide');
  if (!datee(valeur.releve_le)) throw faute('releve_le doit être une date AAAA-MM-JJ');
  if (typeof valeur.appareil !== 'string' || valeur.appareil === '') throw faute('appareil est vide');
  if (typeof valeur.phrase !== 'string' || valeur.phrase.trim() === '') throw faute('phrase est vide');
  const suivants = valeur.suivants;
  if (!Array.isArray(suivants) || suivants.length === 0) throw faute('suivants est vide');
  const vus = new Set<string>();
  let total = 0;
  suivants.forEach((s: unknown, i: number) => {
    if (!objet(s) || typeof s.jeton !== 'string' || s.jeton === '' || !proportion(s.probabilite) || s.probabilite === 0) {
      throw faute(`suivants[${i}] doit avoir un jeton non vide et une probabilité plus grande que 0, jusqu’à 1`);
    }
    if (vus.has(s.jeton)) throw faute(`le jeton « ${s.jeton} » apparaît deux fois dans suivants`);
    vus.add(s.jeton);
    if (i > 0 && s.probabilite > (suivants[i - 1] as SuivantDuModele).probabilite) {
      throw faute(`suivants n’est plus dans l’ordre, du plus probable au moins probable (suivants[${i}])`);
    }
    total += s.probabilite;
  });
  if (total > 1 + 1e-9) throw faute(`les probabilités de suivants font plus que 1 (${String(total)})`);
  return valeur as unknown as FichierSuivants;
}

// --- Lire les relevés --------------------------------------------------------------------------

function racineDuDepot(racineDepot: string | URL): string {
  const racine =
    typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
  if (!existsSync(join(racine, DOSSIER_DU_PROJET))) {
    throw new Error(
      `La racine du dépôt donnée à evaluation.ts (${racine}) n’a pas de dossier ${DOSSIER_DU_PROJET}. ` +
        'Donne la racine du dépôt, le dossier au-dessus de site/ : new URL(\'../\', root) dans un composant Astro, ' +
        'path.resolve(\'..\') depuis site/ dans Vitest et les parcours.',
    );
  }
  return racine;
}

function lireJson(racine: string, fichier: string, refaire = REFAIRE): unknown | undefined {
  const chemin = join(racine, fichier);
  if (!existsSync(chemin)) return undefined;
  try {
    return JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${refaire}`);
  }
}

/** Un fichier versionné du projet 1.6, qui doit exister : lu, ou une erreur qui dit comment le refaire. */
function lireSortie(racineDepot: string | URL, fichier: string, refaire: string): unknown {
  const valeur = lireJson(racineDuDepot(racineDepot), fichier, refaire);
  if (valeur === undefined) throw new Error(`${fichier}${FINE}: le fichier manque. ${refaire}`);
  return valeur;
}

/**
 * Le relevé d'évaluation `nom`, lu dans le dépôt dont on donne la racine : un chemin, une URL file:
 * (comme new URL('../', root) avec le root d'Astro), ou une chaîne qui commence par file:. Par
 * défaut, le dossier au-dessus de site/ (Vitest et les parcours sont lancés depuis site/). Null si le
 * fichier n'existe pas encore : l'évaluation reste « à mesurer ». Une racine qui n'a pas le dossier
 * projets/1.6-evaluation est une erreur : elle ne doit pas passer pour une mesure absente.
 */
export function lireEvaluation(nom: NomEvaluation, racineDepot: string | URL = '..'): Evaluation | null {
  const racine = racineDuDepot(racineDepot);
  const valeur = lireJson(racine, FICHIERS_EVALUATION[nom]);
  return valeur === undefined ? null : verifierEvaluation(valeur, FICHIERS_EVALUATION[nom]);
}

/** Le relevé des QCM de MMMLU notés par le modèle `nom` (voir lireEvaluation pour la racine), ou null s'il manque. */
export function lireQcm(nom: NomEvaluation, racineDepot: string | URL = '..'): QcmExemples | null {
  const racine = racineDuDepot(racineDepot);
  const valeur = lireJson(racine, FICHIERS_QCM[nom]);
  return valeur === undefined ? null : verifierQcm(valeur, FICHIERS_QCM[nom]);
}

/**
 * Ce que le modèle `nom` écrit à partir de `invite`, lu dans son rapport d'évaluation (l'un des dix
 * débuts fixes de forge), ou null si le relevé manque. Une invite que le relevé n'a pas est une
 * erreur : le chapitre ne doit pas afficher un texte qu'il n'a pas.
 */
export function lireEchantillon(
  nom: NomEvaluation,
  invite: string,
  racineDepot: string | URL = '..',
): EchantillonEvaluation | null {
  const evaluation = lireEvaluation(nom, racineDepot);
  if (evaluation === null) return null;
  const echantillon = evaluation.echantillons.find((e) => e.invite === invite);
  if (!echantillon) {
    throw new Error(
      `${FICHIERS_EVALUATION[nom]}${FINE}: aucun échantillon ne part de « ${invite} ». ` +
        `Les débuts du relevé sont ${evaluation.echantillons.map((e) => `« ${e.invite} »`).join(', ')}. ${REFAIRE}`,
    );
  }
  return echantillon;
}

/**
 * Les cartes d'attention de ton IA, la vraie (sorties/cartes-ton-ia.json), lues dans le dépôt dont on
 * donne la racine (voir lireEvaluation) et vérifiées par verifierCartes. Un fichier absent est une
 * erreur : le chapitre 1.4, paru, les montre.
 */
export function lireCartes(racineDepot: string | URL = '..'): FichierCartes {
  const fichier = FICHIERS_SORTIES_TON_IA.cartes;
  return verifierCartes(lireSortie(racineDepot, fichier, REFAIRE_CARTES), fichier);
}

/**
 * Les jetons que ton IA, la vraie, juge les plus probables après une phrase (sorties/ton-ia-suivants.json),
 * lus dans le dépôt dont on donne la racine et vérifiés par verifierSuivants. Un fichier absent est une
 * erreur : le chapitre 1.1, paru, les montre.
 */
export function lireSuivants(racineDepot: string | URL = '..'): FichierSuivants {
  const fichier = FICHIERS_SORTIES_TON_IA.suivants;
  return verifierSuivants(lireSortie(racineDepot, fichier, REFAIRE_SUIVANTS), fichier);
}
