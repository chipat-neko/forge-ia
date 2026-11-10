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
// Tant qu'un fichier manque, lireEvaluation, lireQcm et lireEchantillon rendent null : c'est le cas de
// ton IA, la vraie (ton-ia-1.5), jusqu'à son relevé (tâche 15 du plan 5).

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
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

function lireJson(racine: string, fichier: string): unknown | undefined {
  const chemin = join(racine, fichier);
  if (!existsSync(chemin)) return undefined;
  try {
    return JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${REFAIRE}`);
  }
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
