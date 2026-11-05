// Les chronos du chapitre 0.4 : les fichiers projets/0.4-tenseurs/mesures/*.json,
// écrits par `python -m tenseurs mesurer` (voir le README du projet).
//
// Le chapitre ne mesure rien : il lit ces fichiers à la construction, avec
// node:fs, à partir de la racine du dépôt qu'on lui donne. TableauChronos lui
// passe celle d'astro:config/server ; Vitest et les parcours, path.resolve('..')
// depuis site/. Ce module n'importe ni .json ni astro:* : un parcours
// Playwright peut l'importer (B1).
//
// Le processeur est mesuré pendant les tâches, la carte seulement à la porte :
// tant qu'un fichier manque, lireMesures rend null, et le chapitre affiche
// « à mesurer ».

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FINE = '\u202F';

/** Une durée : un produit de deux matrices taille × taille en float32. */
export interface MesureChrono {
  taille: number;
  /** Les fils du processeur qui calculaient ; null sur la carte. */
  fils: number | null;
  /** La durée médiane d'un produit, en millisecondes. */
  millisecondes: number;
}

/** Le contenu d'un fichier de mesures, version 1. */
export interface MesuresChrono {
  version: 1;
  /** AAAA-MM-JJ. */
  releve_le: string;
  appareil: 'cpu' | 'cuda';
  /** Le nom du processeur ou de la carte. */
  nom: string;
  /** La version de PyTorch, par exemple « 2.15.0+cpu ». */
  torch: string;
  /** Les fils que PyTorch prend sans réglage. */
  fils_par_defaut: number;
  /** Tous les fils du processeur. */
  fils_max: number;
  /** Rangées par taille ; sur le processeur, chaque taille avec chaque nombre de fils. */
  mesures: MesureChrono[];
  /** Sur la carte : la copie d'une matrice vers la carte, en millisecondes, par taille (« 4096 »). Null sur le processeur. */
  transfert_ms: Record<string, number> | null;
}

/** Les fichiers de mesures, en chemins depuis la racine du dépôt. */
export const FICHIERS_MESURES = Object.freeze({
  processeur: 'projets/0.4-tenseurs/mesures/processeur.json',
  'rtx-5070-ti': 'projets/0.4-tenseurs/mesures/rtx-5070-ti.json',
} as const);

export type NomMesures = keyof typeof FICHIERS_MESURES;

const REFAIRE =
  'Relance la mesure avec « python -m tenseurs mesurer » (voir le README de projets/0.4-tenseurs), ' +
  'ou corrige le fichier.';

function entierPositif(x: unknown): x is number {
  return typeof x === 'number' && Number.isInteger(x) && x > 0;
}

function dureePositive(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x) && x > 0;
}

function objet(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

/**
 * Vérifie qu'une valeur lue a le format des mesures (version 1), et la rend
 * telle quelle. Un écart lève une erreur qui nomme le fichier, le champ, et dit
 * quoi faire : la construction s'arrête plutôt que d'afficher un chrono faux.
 */
export function verifierMesures(valeur: unknown, fichier: string): MesuresChrono {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  const m = valeur;
  if (m.version !== 1) throw faute(`version ${String(m.version)} au lieu de 1`);
  if (typeof m.releve_le !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(m.releve_le)) {
    throw faute('releve_le doit être une date AAAA-MM-JJ');
  }
  if (m.appareil !== 'cpu' && m.appareil !== 'cuda') throw faute('appareil doit valoir cpu ou cuda');
  if (typeof m.nom !== 'string' || m.nom.trim() === '') throw faute('nom est vide');
  if (typeof m.torch !== 'string' || m.torch === '') throw faute('torch est vide');
  if (!entierPositif(m.fils_par_defaut) || !entierPositif(m.fils_max)) {
    throw faute('fils_par_defaut et fils_max doivent être des entiers de 1 ou plus');
  }
  if (m.fils_par_defaut > m.fils_max) {
    throw faute(`fils_par_defaut (${m.fils_par_defaut}) dépasse fils_max (${m.fils_max})`);
  }
  if (!Array.isArray(m.mesures) || m.mesures.length === 0) throw faute('mesures est vide');
  const surLaCarte = m.appareil === 'cuda';
  // Les tailles distinctes, dans l'ordre du fichier.
  const tailles: number[] = [];
  const couples = new Set<string>();
  for (const x of m.mesures as unknown[]) {
    if (!objet(x) || !entierPositif(x.taille) || !dureePositive(x.millisecondes)) {
      throw faute('chaque mesure a une taille (entier) et des millisecondes (plus de 0)');
    }
    if (surLaCarte ? x.fils !== null : !entierPositif(x.fils)) {
      throw faute(surLaCarte ? 'fils vaut null sur la carte' : 'fils est un entier de 1 ou plus sur le processeur');
    }
    // Les mesures d'une même taille se suivent (sur le processeur, une par nombre de fils), et les tailles vont
    // en croissant. Une même taille, avec les mêmes fils, n'est mesurée qu'une fois.
    const derniere = tailles[tailles.length - 1];
    const couple = `${x.taille}/${String(x.fils)}`;
    if (derniere !== undefined && x.taille < derniere) {
      throw faute(
        `la taille ${x.taille} vient après ${derniere}${FINE}: range les mesures par taille croissante, ` +
          (surLaCarte ? 'une par taille' : 'celles d’une même taille à la suite, une par nombre de fils'),
      );
    }
    if (couples.has(couple)) {
      throw faute(
        surLaCarte
          ? `la taille ${x.taille} est mesurée deux fois${FINE}: une seule mesure par taille sur la carte`
          : `la taille ${x.taille} avec ${String(x.fils)} fils est mesurée deux fois${FINE}: ` +
              'une seule mesure par taille et par nombre de fils sur le processeur',
      );
    }
    if (x.taille !== derniere) tailles.push(x.taille);
    couples.add(couple);
  }
  if (surLaCarte) {
    if (!objet(m.transfert_ms) || !Object.values(m.transfert_ms).every(dureePositive)) {
      throw faute('transfert_ms est un objet de durées sur la carte');
    }
    const cles = Object.keys(m.transfert_ms);
    const attendues = tailles.map(String);
    if (cles.length !== attendues.length || !attendues.every((t) => Object.hasOwn(m.transfert_ms as object, t))) {
      throw faute(
        `les clés de transfert_ms (${cles.join(', ') || 'aucune'}) doivent être les tailles mesurées (${attendues.join(', ')})`,
      );
    }
  } else if (m.transfert_ms !== null) {
    throw faute('transfert_ms vaut null sur le processeur');
  }
  return m as unknown as MesuresChrono;
}

/** Le dossier du projet 0.4, depuis la racine du dépôt. */
const PROJET_0_4 = 'projets/0.4-tenseurs';

/**
 * Les mesures `nom` (processeur, ou carte de La Forge IA), lues dans le dépôt
 * dont on donne la racine : un chemin, une URL file: (comme new URL('../', root)
 * avec le root d'Astro), ou une chaîne qui commence par file:. Null si le
 * fichier de mesures n'existe pas encore : la mesure reste « à mesurer ». Une
 * racine qui n'a pas le dossier projets/0.4-tenseurs est une erreur : elle ne
 * doit pas passer pour une mesure absente.
 */
export function lireMesures(nom: NomMesures, racineDepot: string | URL): MesuresChrono | null {
  const racine =
    typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
  if (!existsSync(join(racine, PROJET_0_4))) {
    throw new Error(
      `La racine du dépôt donnée à lireMesures (${racine}) n’a pas de dossier ${PROJET_0_4}. ` +
        'Donne la racine du dépôt, le dossier au-dessus de site/ : new URL(\'../\', root) dans un composant Astro, ' +
        'path.resolve(\'..\') depuis site/ dans Vitest et les parcours.',
    );
  }
  const chemin = join(racine, FICHIERS_MESURES[nom]);
  if (!existsSync(chemin)) return null;
  let valeur: unknown;
  try {
    valeur = JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${FICHIERS_MESURES[nom]}${FINE}: JSON illisible (${raison}). ${REFAIRE}`);
  }
  return verifierMesures(valeur, FICHIERS_MESURES[nom]);
}
