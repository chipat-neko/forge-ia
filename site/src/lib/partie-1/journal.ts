// Les journaux d'entraînement du chapitre 1.5, « Le pré-entraînement » : les fichiers
// projets/1.5-pre-entrainement/mesures/ton-ia-mini.json (la version courte, d'une heure)
// et ton-ia-1.5.json (l'entraînement principal, relevé à la tâche 15), écrits par
// `python -m pre_entrainement courbe` (voir le README du projet).
//
// Le chapitre ne lit pas le journal de forge : il lit ce relevé (le résumé, les sessions et la
// courbe déjà réduite en paquets) à la construction, avec node:fs, à partir de la racine du dépôt
// qu'on lui donne. Les composants Astro lui passent celle d'astro:config/server ; Vitest et les
// parcours, path.resolve('..') depuis site/. Ce module n'importe ni .json ni astro:* : un parcours
// Playwright peut l'importer.
//
// Tant qu'un fichier manque, lireEntrainement rend null, et la page pose data-a-mesurer.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FINE = '\u202F';

/** Comment une session finit : en pause (Ctrl+C), au bout de l'entraînement, sur une perte infinie, ou coupée sans ligne de fin. */
export type FinDeSession = 'pause' | 'fin' | 'perte_non_finie' | 'coupée';

/**
 * Une session : de `debut` ou `reprise` à sa fin. Les secondes sont du temps de calcul, sans les
 * pauses. Une session qui a planté avant son premier pas n'a ni premier ni dernier pas (null).
 */
export interface SessionEntrainement {
  depart: 'debut' | 'reprise';
  premier_pas: number | null;
  dernier_pas: number | null;
  secondes: number;
  fin: FinDeSession;
}

/** Ce que le journal dit de l'entraînement, en nombres. */
export interface ResumeEntrainement {
  parametres: number;
  pas_total: number;
  pas_faits: number;
  jetons_vus: number;
  /** La somme des sessions, en secondes. */
  secondes_de_calcul: number;
  pauses: number;
  /** Jetons par seconde de calcul, sur toute la durée. */
  debit_moyen: number;
  /** La moyenne des 20 derniers pas. */
  perte_finale: number;
  validation_finale: number;
  perte_premier_pas: number;
  perte_dernier_pas: number;
}

/** [pas, perte] : la perte d'un paquet de pas (posée au milieu du paquet), ou d'une validation. */
export type PointDeCourbe = [number, number | null];

/** La courbe de perte, réduite pour la page. */
export interface CourbeEntrainement {
  /** Combien de pas par point : celui de taillePaquet(pas_total, 600), dans courbe.ts. */
  taille_paquet: number;
  pertes: PointDeCourbe[];
  validations: PointDeCourbe[];
  /** ln 32 768 : la perte d'un modèle qui devine au hasard. */
  hasard: number;
}

/** Le contenu d'un fichier de relevé d'entraînement. */
export interface Entrainement {
  /** « ton-ia-mini » ou « ton-ia-1.5 ». */
  nom: string;
  /** AAAA-MM-JJ. */
  releve_le: string;
  resume: ResumeEntrainement;
  sessions: SessionEntrainement[];
  courbe: CourbeEntrainement;
}

/** Les fichiers de relevé, en chemins depuis la racine du dépôt. */
export const FICHIERS_ENTRAINEMENT = Object.freeze({
  'ton-ia-mini': 'projets/1.5-pre-entrainement/mesures/ton-ia-mini.json',
  'ton-ia-1.5': 'projets/1.5-pre-entrainement/mesures/ton-ia-1.5.json',
} as const);

export type NomEntrainement = keyof typeof FICHIERS_ENTRAINEMENT;

const REFAIRE =
  'Relance le relevé avec « python -m pre_entrainement courbe » (voir le README de projets/1.5-pre-entrainement), ' +
  'ou corrige le fichier.';

const FINS: readonly string[] = ['pause', 'fin', 'perte_non_finie', 'coupée'];
const NOMBRES_DU_RESUME = [
  'parametres',
  'pas_total',
  'pas_faits',
  'jetons_vus',
  'secondes_de_calcul',
  'pauses',
  'debit_moyen',
  'perte_finale',
  'validation_finale',
  'perte_premier_pas',
  'perte_dernier_pas',
] as const;

function objet(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

function fini(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

function entier(x: unknown, minimum: number): x is number {
  return typeof x === 'number' && Number.isInteger(x) && x >= minimum;
}

/**
 * Vérifie qu'une valeur lue a le format d'un relevé d'entraînement, et la rend telle quelle.
 * Un écart lève une erreur qui nomme le fichier, le champ, et dit quoi faire : la construction
 * s'arrête plutôt que d'afficher une courbe fausse.
 */
export function verifierEntrainement(valeur: unknown, fichier: string): Entrainement {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (typeof valeur.nom !== 'string' || valeur.nom.trim() === '') throw faute('nom est vide');
  if (typeof valeur.releve_le !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(valeur.releve_le)) {
    throw faute('releve_le doit être une date AAAA-MM-JJ');
  }

  const resume = valeur.resume;
  if (!objet(resume)) throw faute('resume manque');
  for (const cle of NOMBRES_DU_RESUME) {
    if (!fini(resume[cle]) || (resume[cle] as number) < 0) throw faute(`resume.${cle} doit être un nombre positif ou nul`);
  }
  for (const cle of ['parametres', 'pas_total', 'pas_faits', 'jetons_vus', 'pauses'] as const) {
    if (!entier(resume[cle], 0)) throw faute(`resume.${cle} doit être un entier`);
  }
  if ((resume.pas_faits as number) < 1) throw faute('resume.pas_faits vaut 0 : le journal est vide');
  if ((resume.pas_faits as number) > (resume.pas_total as number)) {
    throw faute(`resume.pas_faits (${String(resume.pas_faits)}) dépasse resume.pas_total (${String(resume.pas_total)})`);
  }

  const sessions = valeur.sessions;
  if (!Array.isArray(sessions) || sessions.length === 0) throw faute('sessions est vide');
  let derniere = 0;
  // La session d'avant : sa fin, et son dernier pas. Une reprise après un plantage repart de la dernière
  // sauvegarde, donc d'un pas qui peut être avant la fin de la session coupée (ses pas d'après sont refaits).
  let precedente: { fin: string; dernier: number } | null = null;
  let secondes = 0;
  let pauses = 0;
  sessions.forEach((s: unknown, i: number) => {
    const sansPas = objet(s) && s.premier_pas === null && s.dernier_pas === null;
    if (
      !objet(s) ||
      (s.depart !== 'debut' && s.depart !== 'reprise') ||
      !(sansPas || (entier(s.premier_pas, 1) && entier(s.dernier_pas, 1))) ||
      !fini(s.secondes) ||
      s.secondes < 0 ||
      typeof s.fin !== 'string' ||
      !FINS.includes(s.fin)
    ) {
      throw faute(`la session ${i + 1} n’a pas le format attendu (depart, premier_pas, dernier_pas, secondes, fin)`);
    }
    if ((s.depart === 'debut') !== (i === 0)) {
      throw faute(`seule la première session part de « debut » (la session ${i + 1} part de « ${String(s.depart)} »)`);
    }
    if (!sansPas) {
      const premier = s.premier_pas as number;
      const dernier = s.dernier_pas as number;
      if (premier > dernier) throw faute(`la session ${i + 1} finit avant de commencer`);
      const refait = precedente !== null && precedente.fin === 'coupée' && premier <= precedente.dernier;
      if (premier <= derniere && !refait) {
        throw faute(`la session ${i + 1} commence au pas ${premier}, avant la fin de la précédente (pas ${derniere})`);
      }
      derniere = Math.max(derniere, dernier);
      precedente = { fin: s.fin as string, dernier };
    } else {
      precedente = { fin: s.fin as string, dernier: precedente?.dernier ?? 0 };
    }
    secondes += s.secondes;
    if (s.fin === 'pause') pauses += 1;
  });
  if (derniere !== resume.pas_faits) {
    throw faute(`la dernière session finit au pas ${derniere}, mais resume.pas_faits vaut ${String(resume.pas_faits)}`);
  }
  if (pauses !== resume.pauses) throw faute(`${pauses} session(s) finissent en pause, mais resume.pauses vaut ${String(resume.pauses)}`);
  if (Math.abs(secondes - (resume.secondes_de_calcul as number)) > 0.01) {
    throw faute(`les sessions font ${secondes.toFixed(3)} s, mais resume.secondes_de_calcul vaut ${String(resume.secondes_de_calcul)}`);
  }

  const courbe = valeur.courbe;
  if (!objet(courbe)) throw faute('courbe manque');
  if (!entier(courbe.taille_paquet, 1)) throw faute('courbe.taille_paquet doit être un entier de 1 ou plus');
  if (!fini(courbe.hasard) || courbe.hasard <= 0) throw faute('courbe.hasard doit être un nombre positif');
  for (const cle of ['pertes', 'validations'] as const) {
    const points = courbe[cle];
    if (!Array.isArray(points) || points.length === 0) throw faute(`courbe.${cle} est vide`);
    let avant = 0;
    points.forEach((p: unknown, i: number) => {
      const bon =
        Array.isArray(p) && p.length === 2 && fini(p[0]) && p[0] > avant && (p[1] === null || (fini(p[1]) && p[1] >= 0));
      if (!bon) throw faute(`courbe.${cle}[${i}] doit être [pas, perte], avec des pas croissants`);
      avant = (p as number[])[0];
    });
  }
  return valeur as unknown as Entrainement;
}

/**
 * Le relevé `nom`, lu dans le dépôt dont on donne la racine : un chemin, une URL file: (comme
 * new URL('../', root) avec le root d'Astro), ou une chaîne qui commence par file:. Par défaut,
 * le dossier au-dessus de site/ (Vitest et les parcours sont lancés depuis site/). Null si le
 * fichier n'existe pas encore : l'entraînement reste « à mesurer ». Une racine qui n'a pas le
 * dossier projets/1.5-pre-entrainement est une erreur : elle ne doit pas passer pour une mesure
 * absente.
 */
export function lireEntrainement(nom: NomEntrainement, racineDepot: string | URL = '..'): Entrainement | null {
  const racine =
    typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
  if (!existsSync(join(racine, 'projets/1.5-pre-entrainement'))) {
    throw new Error(
      `La racine du dépôt donnée à lireEntrainement (${racine}) n’a pas de dossier projets/1.5-pre-entrainement. ` +
        'Donne la racine du dépôt, le dossier au-dessus de site/ : new URL(\'../\', root) dans un composant Astro, ' +
        'path.resolve(\'..\') depuis site/ dans Vitest et les parcours.',
    );
  }
  const chemin = join(racine, FICHIERS_ENTRAINEMENT[nom]);
  if (!existsSync(chemin)) return null;
  let valeur: unknown;
  try {
    valeur = JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${FICHIERS_ENTRAINEMENT[nom]}${FINE}: JSON illisible (${raison}). ${REFAIRE}`);
  }
  return verifierEntrainement(valeur, FICHIERS_ENTRAINEMENT[nom]);
}
