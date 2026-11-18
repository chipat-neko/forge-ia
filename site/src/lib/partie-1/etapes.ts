// Les rapports d'étape de la vague 2 : ton IA, version par version, sur les mêmes mesures.
//
// `forge evaluer-etape` écrit un rapport complet (projets/forge/forge/evaluation/etape.py). Le projet de
// chaque chapitre (1.7 à 1.10) en garde un résumé, sans rien recalculer :
// projets/1.N-*/mesures/etape-<version>.json, avec `resumer_etape`. Le chapitre lit ce résumé à la
// construction, avec node:fs, à partir de la racine du dépôt qu'on lui donne (comme journal.ts). Ce module
// n'importe ni .json ni astro:* : un parcours Playwright peut l'importer.
//
// Un nom de FICHIERS_ETAPES est « version@étape » : « 1.7@1.7 » est ton IA 1.7 mesurée à l'étape 1.7,
// « 1.5@1.7 » est ton IA 1.5 (la version du chapitre 1.5) passant les mêmes mesures, « 1.7-court@1.7 » la
// version d'essai plus courte de 1.7. Les noms de versions des fichiers sont ceux des Releases (« ton-ia-1.7 »).
//
// Tant qu'un fichier manque, lireRapportEtape rend null, et la page pose data-a-mesurer. Un fichier qui a le
// mauvais format est une erreur qui dit quel relevé refaire : la construction s'arrête plutôt que d'afficher un
// tableau faux.
//
// Les séries de courbes de 1.8 (DPO) et de 1.9 (GRPO) se lisent avec lireSeries.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FINE = '\u202F';

/** Les rapports d'étape, en chemins depuis la racine du dépôt : « version@étape » vers le résumé du rapport. */
export const FICHIERS_ETAPES = Object.freeze({
  '1.5@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.5.json',
  '1.7@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.7.json',
  '1.7-court@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.7-court.json',
  '1.8@1.8': 'projets/1.8-alignement/mesures/etape-ton-ia-1.8.json',
  '1.8-court@1.8': 'projets/1.8-alignement/mesures/etape-ton-ia-1.8-court.json',
  '1.5@1.9': 'projets/1.9-raisonnement/mesures/etape-ton-ia-1.5.json',
  '1.9@1.9': 'projets/1.9-raisonnement/mesures/etape-ton-ia-1.9.json',
  '1.5@1.10': 'projets/1.10-code/mesures/etape-ton-ia-1.5.json',
  '1.10@1.10': 'projets/1.10-code/mesures/etape-ton-ia-1.10.json',
} as const);

export type NomRapportEtape = keyof typeof FICHIERS_ETAPES;

/** Les étapes qui ont des mesures. */
export type EtapeDeRapport = '1.7' | '1.8' | '1.9' | '1.10';

/**
 * Les mesures de chaque étape : les clés de MESURES_PAR_ETAPE (projets/forge/forge/evaluation/etape.py) sans
 * `echantillons`, que le rapport range à part. Celles de 1.8 et de 1.10 sont celles que le plan 7 y ajoute.
 */
export const MESURES_DE_L_ETAPE: Readonly<Record<EtapeDeRapport, readonly string[]>> = Object.freeze({
  '1.7': ['perte_conversation', 'ifeval_fr', 'tenue', 'oubli'],
  '1.8': ['perte_conversation', 'ifeval_fr', 'tenue', 'oubli', 'victoire'],
  '1.9': ['ifeval_fr', 'tenue', 'oubli', 'problemes', 'mgsm_fr', 'gsm8k_platinum_fr'],
  '1.10': ['ifeval_fr', 'tenue', 'oubli', 'problemes', 'humaneval', 'humaneval_fr', 'fim_ligne'],
});

/** Une mesure que les données n'ont pas permis de faire : sa raison, dite telle quelle. */
export interface MesureAbsente {
  absente: string;
}

/** Les nombres d'une mesure, éventuellement rangés par groupe (par_famille, par_difficulte). */
export interface NombresDeMesure {
  [cle: string]: number | NombresDeMesure;
}

export type Mesure = NombresDeMesure | MesureAbsente;

/** Une réponse de ton IA à une invite fixe, gardée telle quelle. */
export interface EchantillonDeReponse {
  invite: string;
  texte: string;
  pensee?: string | null;
  terminee?: boolean;
}

/** Le résumé d'un rapport d'étape. */
export interface RapportEtape {
  /** « ton-ia-1.7 » : la version mesurée. */
  version: string;
  /** « 1.7 », « 1.8 », « 1.9 » ou « 1.10 ». */
  etape: EtapeDeRapport;
  /** AAAA-MM-JJ. */
  releve_le: string;
  /** Une entrée par mesure de l'étape (MESURES_DE_L_ETAPE). */
  mesures: Record<string, Mesure>;
  echantillons: EchantillonDeReponse[];
}

/** Une mesure absente : `{ absente: raison }`, et rien d'autre. */
export function estAbsente(mesure: Mesure): mesure is MesureAbsente {
  return typeof (mesure as MesureAbsente).absente === 'string';
}

const REFAIRE =
  'Relance le relevé avec « python -m <paquet du projet> resumer --rapport <rapport.json> --json <ce fichier> » ' +
  '(voir le README du projet du chapitre), ou corrige le fichier.';

function objet(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

function fini(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

function texte(x: unknown): x is string {
  return typeof x === 'string';
}

/** Vrai si `x` est un objet dont toutes les feuilles sont des nombres finis ; sinon, le chemin de la première faute. */
function fauteDeNombres(x: unknown, chemin: string): string | null {
  if (!objet(x)) return `${chemin} doit être un objet de nombres`;
  for (const [cle, valeur] of Object.entries(x)) {
    if (objet(valeur)) {
      const faute = fauteDeNombres(valeur, `${chemin}.${cle}`);
      if (faute !== null) return faute;
    } else if (!fini(valeur)) {
      return `${chemin}.${cle} doit être un nombre fini`;
    }
  }
  return null;
}

/**
 * Vérifie qu'une valeur lue a le format du résumé d'un rapport d'étape, et la rend telle quelle. Un écart lève
 * une erreur qui nomme le fichier et le champ, et dit quel relevé refaire.
 */
export function verifierRapportEtape(valeur: unknown, fichier: string): RapportEtape {
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  if (!texte(valeur.version) || valeur.version.trim() === '') throw faute('version est vide');
  if (!texte(valeur.etape) || !Object.hasOwn(MESURES_DE_L_ETAPE, valeur.etape)) {
    throw faute(`etape doit être l’une de ${Object.keys(MESURES_DE_L_ETAPE).join(', ')}`);
  }
  if (!texte(valeur.releve_le) || !/^\d{4}-\d{2}-\d{2}$/.test(valeur.releve_le)) {
    throw faute('releve_le doit être une date AAAA-MM-JJ');
  }

  const mesures = valeur.mesures;
  if (!objet(mesures)) throw faute('mesures manque');
  const attendues = MESURES_DE_L_ETAPE[valeur.etape as EtapeDeRapport];
  for (const nom of Object.keys(mesures)) {
    if (!attendues.includes(nom)) throw faute(`mesures.${nom} n’est pas une mesure de l’étape ${valeur.etape}`);
  }
  for (const nom of attendues) {
    const m = mesures[nom];
    if (m === undefined) throw faute(`mesures.${nom} manque (l’étape ${valeur.etape} la mesure)`);
    if (objet(m) && Object.hasOwn(m, 'absente')) {
      if (!texte(m.absente) || m.absente.trim() === '' || Object.keys(m).length !== 1) {
        throw faute(`mesures.${nom} : une mesure absente s’écrit { "absente": "<raison>" }, et rien d’autre`);
      }
      continue;
    }
    const mauvaise = fauteDeNombres(m, `mesures.${nom}`);
    if (mauvaise !== null) throw faute(mauvaise);
  }

  const echantillons = valeur.echantillons;
  if (!Array.isArray(echantillons)) throw faute('echantillons doit être une liste');
  echantillons.forEach((e: unknown, i: number) => {
    if (
      !objet(e) ||
      !texte(e.invite) ||
      !texte(e.texte) ||
      (e.pensee !== undefined && e.pensee !== null && !texte(e.pensee)) ||
      (e.terminee !== undefined && typeof e.terminee !== 'boolean')
    ) {
      throw faute(`echantillons[${i}] doit avoir une invite et un texte (pensee et terminee sont facultatifs)`);
    }
  });
  return valeur as unknown as RapportEtape;
}

/** La racine du dépôt, en chemin : une chaîne, ou une URL file: (comme new URL('../', root) avec le root d'Astro). */
function racineEnChemin(racineDepot: string | URL): string {
  return typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
}

/** Refuse une racine qui n'est pas celle du dépôt : elle ne doit pas passer pour une mesure absente. */
function verifierRacine(racine: string, lecteur: string): void {
  if (!existsSync(join(racine, 'projets/1.5-pre-entrainement'))) {
    throw new Error(
      `La racine du dépôt donnée à ${lecteur} (${racine}) n’a pas de dossier projets/1.5-pre-entrainement. ` +
        'Donne la racine du dépôt, le dossier au-dessus de site/ : new URL(\'../\', root) dans un composant Astro, ' +
        'path.resolve(\'..\') depuis site/ dans Vitest et les parcours.',
    );
  }
}

function lireJson(chemin: string, fichier: string): unknown {
  try {
    return JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${REFAIRE}`);
  }
}

/**
 * Le rapport d'étape `nom` (« version@étape »), lu dans le dépôt dont on donne la racine. Par défaut, le
 * dossier au-dessus de site/ (Vitest et les parcours sont lancés depuis site/). Null si le fichier n'existe pas
 * encore : la mesure reste « à mesurer ». Un rapport dont l'étape n'est pas celle de son nom est une erreur.
 */
export function lireRapportEtape(nom: NomRapportEtape, racineDepot: string | URL = '..'): RapportEtape | null {
  const racine = racineEnChemin(racineDepot);
  verifierRacine(racine, 'lireRapportEtape');
  const fichier = FICHIERS_ETAPES[nom];
  const chemin = join(racine, fichier);
  if (!existsSync(chemin)) return null;
  const rapport = verifierRapportEtape(lireJson(chemin, fichier), fichier);
  const etapeDuNom = nom.slice(nom.indexOf('@') + 1);
  if (rapport.etape !== etapeDuNom) {
    throw new Error(
      `${fichier}${FINE}: le rapport est celui de l’étape ${rapport.etape}, mais « ${nom} » attend l’étape ${etapeDuNom}. ${REFAIRE}`,
    );
  }
  return rapport;
}

/**
 * Les séries d'un fichier de courbes de 1.8 (mesures/entrainement-dpo-1.8.json) ou de 1.9
 * (mesures/entrainement-grpo-1.9.json) : une clé par série, chacune une liste de [pas, valeur] qui vient de
 * `pre_entrainement.journal.serie`. `fichier` est un chemin depuis la racine du dépôt. Null si le fichier
 * manque. Les clés qui ne sont pas des séries (`lance: false` d'un RL non lancé) sont laissées de côté : un
 * fichier sans série rend `{}`.
 */
export function lireSeries(fichier: string, racineDepot: string | URL = '..'): Record<string, [number, number][]> | null {
  const racine = racineEnChemin(racineDepot);
  verifierRacine(racine, 'lireSeries');
  const chemin = join(racine, fichier);
  if (!existsSync(chemin)) return null;
  const valeur = lireJson(chemin, fichier);
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${REFAIRE}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  const series: Record<string, [number, number][]> = {};
  for (const [cle, points] of Object.entries(valeur)) {
    if (!Array.isArray(points)) continue;
    let avant = 0;
    points.forEach((p: unknown, i: number) => {
      const bon = Array.isArray(p) && p.length === 2 && fini(p[0]) && p[0] > avant && fini(p[1]);
      if (!bon) throw faute(`${cle}[${i}] doit être [pas, valeur], avec des pas croissants et des nombres finis`);
      avant = (p as number[])[0];
    });
    series[cle] = points as [number, number][];
  }
  return series;
}
