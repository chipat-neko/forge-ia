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
// version d'essai plus courte de 1.7. La version de référence d'un rapport (ton IA 1.5 en 1.7, ton IA 1.7 en 1.8)
// est résumée dans le projet de l'étape, avec `resumer --reference`. Les noms de versions des fichiers sont ceux des Releases (« ton-ia-1.7 »).
//
// Tant qu'un fichier manque, lireRapportEtape rend null, et la page pose data-a-mesurer. Un fichier qui a le
// mauvais format est une erreur qui dit quel relevé refaire : la construction s'arrête plutôt que d'afficher un
// tableau faux.
//
// Les séries de courbes de 1.8 (DPO) et de 1.9 (GRPO) se lisent avec lireSeries.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { nombre, pourcent } from '../nombres';

const FINE = '\u202F';

/** Les rapports d'étape, en chemins depuis la racine du dépôt : « version@étape » vers le résumé du rapport. */
export const FICHIERS_ETAPES = Object.freeze({
  '1.5@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.5.json',
  '1.7@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.7.json',
  '1.7-court@1.7': 'projets/1.7-conversation/mesures/etape-ton-ia-1.7-court.json',
  '1.7@1.8': 'projets/1.8-alignement/mesures/etape-ton-ia-1.7.json',
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
 * `echantillons`, que le rapport range à part. Celles de 1.10 sont celles que le plan 7 y ajoutera (tâche 21).
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

// Le paquet Python de chaque projet qui sait refaire ses relevés (`python -m <paquet> resumer`, etc.). Le projet
// 1.10 n'y est pas encore : son message reste général jusqu'à sa tâche.
const PAQUETS_DES_PROJETS: Readonly<Record<string, string>> = Object.freeze({
  '1.7-conversation': 'conversation_pas_a_pas',
  '1.8-alignement': 'alignement_pas_a_pas',
  '1.9-raisonnement': 'raisonnement_pas_a_pas',
});

// Le relevé de la version de référence de chaque projet : la référence du rapport de l'étape (`--reference` de
// `forge evaluer-etape`), que `resumer --reference` résume.
const REFERENCES_DES_PROJETS: Readonly<Record<string, string>> = Object.freeze({
  '1.7-conversation': 'etape-ton-ia-1.5.json',
  '1.8-alignement': 'etape-ton-ia-1.7.json',
  '1.9-raisonnement': 'etape-ton-ia-1.5.json',
});

/**
 * Ce qu'il faut relancer pour refaire le relevé `fichier` (un chemin depuis la racine du dépôt) : la commande du
 * projet qui l'écrit, pas celle d'un autre. Un fichier d'un projet inconnu reçoit le message général.
 */
export function refaire(fichier: string): string {
  const general =
    'Relance le relevé avec « python -m <paquet du projet> resumer --rapport <rapport.json> --json <ce fichier> » ' +
    '(voir le README du projet du chapitre), ou corrige le fichier.';
  const trouve = /^projets\/([^/]+)\/mesures\/([^/]+)$/.exec(fichier);
  if (trouve === null) return general;
  const [, dossier, nom] = trouve;
  const paquet = PAQUETS_DES_PROJETS[dossier];
  if (paquet === undefined) return general;
  const commande = (arguments_: string): string =>
    `Relance le relevé, depuis projets/${dossier}, avec « uv run --extra cpu python -m ${paquet} ${arguments_} --json mesures/${nom} », ou corrige le fichier.`;
  if (nom.startsWith('entrainement-dpo') || nom.startsWith('entrainement-grpo')) return commande('courbes --journal <journal.jsonl>');
  if (nom.startsWith('controle-')) return commande('controle --sortie <dossier de sortie du grpo>');
  if (nom === 'paires-exemples.json') return commande('paires --jeu <dossier du jeu de paires>');
  if (nom.startsWith('balayage')) return commande('balayage <dossier d’essai> <dossier d’essai>');
  if (nom === REFERENCES_DES_PROJETS[dossier]) return commande('resumer --rapport <rapport.json> --reference');
  if (nom.startsWith('etape-')) return commande('resumer --rapport <rapport.json>');
  return general;
}

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
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${refaire(fichier)}`);
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
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${refaire(fichier)}`);
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
      `${fichier}${FINE}: le rapport est celui de l’étape ${rapport.etape}, mais « ${nom} » attend l’étape ${etapeDuNom}. ${refaire(fichier)}`,
    );
  }
  return rapport;
}

/** Un point d'une série : [pas, valeur]. La valeur est null quand le paquet de pas n'avait aucune valeur finie. */
export type PointDeSerie = [number, number | null];

/** Les options de lireSeries : `absents` accepte les points sans valeur (`null`), que `serie()` rend quand un RL diverge. */
export interface OptionsDeSeries {
  absents?: boolean;
}

/**
 * Les séries d'un fichier de courbes de 1.8 (mesures/entrainement-dpo-1.8.json) ou de 1.9
 * (mesures/entrainement-grpo-1.9.json) : une clé par série, chacune une liste de [pas, valeur] qui vient de
 * `pre_entrainement.journal.serie`. `fichier` est un chemin depuis la racine du dépôt. Null si le fichier manque.
 *
 * Les clés d'un fichier sont des séries (des listes), ou `lance`, un booléen : `lance: false` dit qu'un RL n'a pas été
 * lancé (le contrôle de départ n'a trouvé aucune réponse juste), et le fichier n'a alors aucune série (`{}`). Toute
 * autre clé est une erreur qui nomme le fichier : elle ne doit pas disparaître sans rien dire.
 *
 * Une valeur `null` (un paquet de pas sans aucune valeur finie) est refusée, sauf avec `{ absents: true }` : le point
 * garde alors son pas et sa valeur est `null`, que la page montre comme absente. Les courbes de 1.9, qui peuvent
 * diverger, demandent les absents ; celles de 1.8, que le Python refuse d'écrire avec un trou, non.
 */
export function lireSeries(
  fichier: string,
  racineDepot?: string | URL,
  options?: { absents?: false },
): Record<string, [number, number][]> | null;
export function lireSeries(
  fichier: string,
  racineDepot: string | URL | undefined,
  options: { absents: true },
): Record<string, PointDeSerie[]> | null;
export function lireSeries(
  fichier: string,
  racineDepot: string | URL = '..',
  options: OptionsDeSeries = {},
): Record<string, PointDeSerie[]> | null {
  const racine = racineEnChemin(racineDepot);
  verifierRacine(racine, 'lireSeries');
  const chemin = join(racine, fichier);
  if (!existsSync(chemin)) return null;
  const valeur = lireJson(chemin, fichier);
  const faute = (quoi: string): Error => new Error(`${fichier}${FINE}: ${quoi}. ${refaire(fichier)}`);
  if (!objet(valeur)) throw faute('ce n’est pas un objet JSON');
  const series: Record<string, PointDeSerie[]> = {};
  for (const [cle, points] of Object.entries(valeur)) {
    if (cle === 'lance') {
      if (typeof points !== 'boolean') throw faute('« lance » doit être vrai ou faux');
      continue;
    }
    if (!Array.isArray(points)) {
      throw faute(`la clé « ${cle} » n’est ni une série de [pas, valeur] ni « lance »`);
    }
    let avant = 0;
    points.forEach((p: unknown, i: number) => {
      const vide = options.absents === true && Array.isArray(p) && p.length === 2 && p[1] === null;
      const bon = Array.isArray(p) && p.length === 2 && fini(p[0]) && p[0] > avant && (vide || fini(p[1]));
      if (!bon) {
        const precision = options.absents === true ? ' ou null' : '';
        throw faute(`${cle}[${i}] doit être [pas, valeur], avec des pas croissants et des nombres finis${precision}`);
      }
      avant = (p as number[])[0];
    });
    series[cle] = points as PointDeSerie[];
  }
  if (valeur.lance === false && Object.keys(series).length > 0) {
    throw faute('« lance » est faux, mais le fichier a des séries : un RL non lancé n’a aucune courbe');
  }
  return series;
}

// ---------- Ce que montre le tableau d'une étape (TableauEtape.astro) ----------
// Une ligne par mesure : son libellé, ce qu'elle compte, et le nombre qu'on en lit, mis en forme. Le tableau
// est commun aux chapitres 1.7 à 1.10 : une mesure qui n'a pas encore sa ligne arrête la construction, avec un
// message qui dit où l'ajouter. Une valeur absente (rapport qui manque, ou mesure `{ absente }`) devient « à
// mesurer » dans la page.

/** Une ligne du tableau : le libellé, sa précision, et la valeur et le détail lus dans les nombres de la mesure. */
export interface LigneDeMesure {
  libelle: string;
  precision: string;
  valeur: (m: NombresDeMesure) => string;
  detail: (m: NombresDeMesure) => string;
}

function lu(m: NombresDeMesure, cle: string): number {
  const x = m[cle];
  if (typeof x !== 'number') throw new Error(`La mesure n’a pas de nombre « ${cle} » : relève de nouveau le rapport d’étape.`);
  return x;
}

/** Les lignes des mesures que les chapitres montrent. */
export const LIGNES_DES_MESURES: Readonly<Record<string, LigneDeMesure>> = Object.freeze({
  perte_conversation: {
    libelle: 'Perte sur des conversations',
    precision: 'en nats par jeton appris, sur la validation de sft-1.7',
    valeur: (m) => nombre(lu(m, 'perte'), 3),
    detail: (m) => `sur ${nombre(lu(m, 'n'))} rangées`,
  },
  ifeval_fr: {
    libelle: 'Consignes d’IFEval-FR',
    precision: 'part des invites dont toutes les consignes sont respectées',
    valeur: (m) => pourcent(lu(m, 'invite_stricte'), 1),
    detail: (m) => `consignes${FINE}: ${pourcent(lu(m, 'consigne_stricte'), 1)}`,
  },
  tenue: {
    libelle: 'Réponses finies',
    precision: 'part des réponses qui finissent par <|fin_tour|>',
    valeur: (m) => pourcent(lu(m, 'terminee'), 1),
    detail: (m) => `sur ${nombre(lu(m, 'n'))} réponses`,
  },
  oubli: {
    libelle: 'Perte sur le texte du web',
    precision: 'en nats par jeton, sur la validation de son pré-entraînement',
    valeur: (m) => nombre(lu(m, 'perte'), 3),
    detail: (m) => `sur ${nombre(lu(m, 'n'))} morceaux`,
  },
  // Étape 1.8 : chaque version du rapport garde son taux contre l'autre (celui de la référence est le complément).
  victoire: {
    libelle: 'Victoires aux contrôles',
    precision: 'part des invites où sa réponse a la meilleure note, face à l’autre version du rapport (une égalité compte une demie)',
    valeur: (m) => pourcent(lu(m, 'taux'), 1),
    detail: (m) => `sur ${nombre(lu(m, 'n'))} invites`,
  },
});

/** La cellule d'une mesure dans un rapport : sa valeur et son détail ; null si le rapport manque ou si la mesure est absente. */
export function celluleDeMesure(rapport: RapportEtape | null, nom: string): { valeur: string; detail: string } | null {
  const ligne = LIGNES_DES_MESURES[nom];
  if (ligne === undefined) {
    throw new Error(
      `La mesure « ${nom} » n’a pas de ligne de tableau : ajoute-la à LIGNES_DES_MESURES (src/lib/partie-1/etapes.ts), ` +
        'avec son libellé, sa précision et le nombre à montrer.',
    );
  }
  if (rapport === null) return null;
  const m = rapport.mesures[nom];
  if (m === undefined || estAbsente(m)) return null;
  return { valeur: ligne.valeur(m), detail: ligne.detail(m) };
}

/** Le nom d'une version en tête de colonne : « Ton IA 1.5 », « Ton IA 1.7 », « Version courte ». */
export function nomDeVersion(nom: NomRapportEtape): string {
  const version = nom.slice(0, nom.indexOf('@'));
  return version.endsWith('-court') ? 'Version courte' : `Ton IA ${version}`;
}
