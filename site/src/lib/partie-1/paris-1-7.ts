// Les paris du chapitre 1.7, « Apprendre à converser », et ce que le chapitre lit du projet 1.7 et des rapports
// d'étape, à la construction.
//
// Leurs bonnes réponses sont calculées, jamais tapées :
// - « fin » : la part des réponses de ton IA 1.5 qui finissent par <|fin_tour|> (tenue.terminee du rapport
//   « 1.5@1.7 ») ;
// - « gabarit » : les ids que le tokenizer de ton IA donne à un texte qui imite <|fin_tour|> (la conversation
//   « faux-special » des attendus du projet) ;
// - « masque » : le masque de perte que le jumeau d'encoder_conversation (assemblerConversation) donne à la
//   conversation de référence « avec-systeme » ;
// - « fuite » : l'écart des logits relevé par le projet sans le masque par document (mesures/fuite.json) ;
// - « consignes » et « oubli » : les rapports de ton IA 1.7 et de ton IA 1.5 (« 1.7@1.7 », « 1.5@1.7 »).
// Le balayage du taux d'apprentissage (étape 7) se lit dans mesures/balayage-sft-1.7.json, relevé par le projet dans
// les journaux des quatre essais.
// Les paris dont le rapport manque rendent null : la page pose alors data-a-mesurer à leur place. Une phrase
// du chapitre qui deviendrait fausse arrête la construction (« Exemple devenu faux : … »).
//
// Chaque fonction lit le dépôt dont on lui donne la racine (par défaut le dossier au-dessus de site/, d'où
// Vitest et les parcours sont lancés) : les tests lui donnent un dépôt fabriqué. Ce module lit les fichiers
// avec node:fs, sans import .json ni astro:* : un parcours Playwright peut l'importer. Les îlots (l'atelier,
// la figure) n'en importent rien : ce qu'ils calculent est dans atelier-1-7.ts.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre } from '../nombres';
import {
  CONVERSATION_DU_SYSTEME,
  enToursEncodes,
  LONGUEURS_DE_RANGEE,
  type ConversationDeReference,
  type EmpaquetageDeLaFigure,
} from './atelier-1-7';
import { empaqueterLongueurs } from './bfd';
import { assemblerConversation, NOMS_SPECIAUX, PREMIER_SPECIAL, SPECIAUX_TON_IA } from './conversation';
import { estAbsente, lireRapportEtape, type EchantillonDeReponse, type NombresDeMesure, type RapportEtape } from './etapes';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { MESURES_PARTIE_1 } from './mesures';
import { analyserReglages, type ReglagesEntrainement } from './paris-1-5';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-7.ts et le texte des paris du chapitre 1.7');

/** Une tranche d'un pari : son texte, et la valeur sous laquelle elle s'arrête (non comprise). */
export interface Tranche {
  texte: string;
  jusqua: number;
}

function rangDeTranche(tranches: readonly Tranche[], x: number): number {
  const rang = tranches.findIndex((t) => x < t.jusqua);
  exiger(rang >= 0, `${String(x)} ne tombe dans aucune tranche`);
  return rang;
}

function choixDesTranches(tranches: readonly Tranche[], x: number): Choix[] {
  const juste = rangDeTranche(tranches, x);
  return tranches.map((t, i) => ({ texte: t.texte, juste: i === juste }));
}

// ---------- Lire le dépôt ----------

function enChemin(racineDepot: string | URL): string {
  return typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
}

function lireJson(racineDepot: string | URL, fichier: string, refaire: string): unknown {
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) throw new Error(`${fichier}${FINE}: le fichier manque. ${refaire}`);
  try {
    return JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${refaire}`);
  }
}

function objet(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

function fini(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

const REFAIRE_ATTENDUS =
  'Régénère les attendus : uv run --extra cpu python -m conversation_pas_a_pas.attendus, dans projets/1.7-conversation.';

/** Les six conversations de référence du projet 1.7 (tests/attendus.json, section « conversations »). */
export function lireConversationsDeReference(racineDepot: string | URL = '..'): ConversationDeReference[] {
  const attendus = lireJson(racineDepot, FICHIERS_PARTIE_1.conversation, REFAIRE_ATTENDUS);
  if (!objet(attendus) || !Array.isArray(attendus.conversations)) {
    throw new Error(`${FICHIERS_PARTIE_1.conversation}${FINE}: la section « conversations » manque. ${REFAIRE_ATTENDUS}`);
  }
  return attendus.conversations as ConversationDeReference[];
}

/** Les longueurs de la liste de remplacement des attendus : celle que range la figure tant que le jeu de ton IA n'est pas relevé. */
function longueursDeReference(racineDepot: string | URL): number[] | null {
  const attendus = lireJson(racineDepot, FICHIERS_PARTIE_1.conversation, REFAIRE_ATTENDUS);
  const cas = objet(attendus) && Array.isArray(attendus.empaquetages) ? attendus.empaquetages : [];
  const reference = cas.find((c: unknown) => objet(c) && c.liste === 'longueurs-de-remplacement') as { longueurs: number[] } | undefined;
  return reference === undefined ? null : reference.longueurs;
}

/** L'écart des logits de la conversation B, avec et sans le masque par document (mesures/fuite.json). */
export interface Fuite {
  releve_le: string;
  graine: number;
  jetons_a: number;
  jetons_b: number;
  avec_masque: number;
  sans_masque: number;
}

/** La fuite relevée par le projet 1.7, sur le processeur. */
export function lireFuite(racineDepot: string | URL = '..'): Fuite {
  const fichier = MESURES_PARTIE_1.fuiteConversation;
  const refaire = 'Relance-la : uv run --extra cpu python -m conversation_pas_a_pas fuite --enregistrer sorties/fuite.txt --json mesures/fuite.json.';
  const f = lireJson(racineDepot, fichier, refaire);
  const nombres = ['graine', 'jetons_a', 'jetons_b', 'avec_masque', 'sans_masque'];
  if (!objet(f) || typeof f.releve_le !== 'string' || nombres.some((cle) => !fini(f[cle]))) {
    throw new Error(`${fichier}${FINE}: il faut releve_le et les nombres ${nombres.join(', ')}. ${refaire}`);
  }
  return f as unknown as Fuite;
}

/** Une réponse du petit modèle de l'essai, telle quelle. */
export interface ReponseDeLEssai {
  invite: string;
  texte: string;
  terminee: boolean;
}

/** Le tout petit affinage du projet 1.7 (mesures/essai-processeur.json). */
export interface EssaiAffinage {
  releve_le: string;
  appareil: string;
  pas: number;
  pertes: number[];
  fin_de_tour_avant: number;
  fin_de_tour_apres: number;
  reponses_avant: ReponseDeLEssai[];
  reponses_apres: ReponseDeLEssai[];
  exemples: number;
  rangees: number;
  jetons: number;
  jetons_appris: number;
  parametres: number;
  secondes: number;
}

/** Le petit affinage relevé par le projet 1.7, sur le processeur. */
export function lireEssaiAffinage(racineDepot: string | URL = '..'): EssaiAffinage {
  const fichier = MESURES_PARTIE_1.essaiAffinage;
  const refaire =
    'Relance-le : uv run --extra cpu python -m conversation_pas_a_pas essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json.';
  const e = lireJson(racineDepot, fichier, refaire);
  const nombres = ['pas', 'fin_de_tour_avant', 'fin_de_tour_apres', 'exemples', 'rangees', 'jetons', 'jetons_appris', 'parametres', 'secondes'];
  const reponses = (r: unknown) => Array.isArray(r) && r.every((x) => objet(x) && typeof x.invite === 'string' && typeof x.texte === 'string' && typeof x.terminee === 'boolean');
  if (
    !objet(e) ||
    typeof e.releve_le !== 'string' ||
    typeof e.appareil !== 'string' ||
    nombres.some((cle) => !fini(e[cle])) ||
    !Array.isArray(e.pertes) ||
    !e.pertes.every(fini) ||
    !reponses(e.reponses_avant) ||
    !reponses(e.reponses_apres)
  ) {
    throw new Error(`${fichier}${FINE}: il faut releve_le, appareil, les pertes, les réponses et les nombres ${nombres.join(', ')}. ${refaire}`);
  }
  return e as unknown as EssaiAffinage;
}

/** Les longueurs des exemples du jeu d'affinage de ton IA, développées depuis l'histogramme du relevé. */
export interface LongueursDuJeu {
  jeu: string;
  releve_le: string;
  longueur_des_rangees: number;
  /** Une longueur par exemple, croissantes (l'histogramme développé, comme `developper` du projet). */
  longueurs: number[];
}

/**
 * Le relevé des longueurs des exemples de sft-1.7, en histogramme. Il vient avec la Release de ton IA 1.7 (tâche 11
 * du plan 8) : il n'est pas dans MESURES_PARTIE_1, dont chaque fichier doit déjà exister (donnees.test.ts).
 */
export const FICHIER_LONGUEURS_SFT_17 = 'projets/1.7-conversation/mesures/longueurs-sft-1.7.json';

/** Le relevé des longueurs de sft-1.7, ou null tant qu'il n'est pas fait (il vient avec la Release de ton IA 1.7). */
export function lireLongueurs(racineDepot: string | URL = '..'): LongueursDuJeu | null {
  const fichier = FICHIER_LONGUEURS_SFT_17;
  if (!existsSync(join(enChemin(racineDepot), fichier))) return null;
  const refaire = 'Relance-le : uv run --extra cpu python -m conversation_pas_a_pas longueurs --jeu <FORGE_DONNEES>/affinage/sft-1.7 --json mesures/longueurs-sft-1.7.json.';
  const l = lireJson(racineDepot, fichier, refaire);
  const histogramme = objet(l) ? l.histogramme : undefined;
  const bon =
    objet(l) &&
    typeof l.jeu === 'string' &&
    typeof l.releve_le === 'string' &&
    fini(l.longueur_des_rangees) &&
    Array.isArray(histogramme) &&
    histogramme.every((p: unknown) => Array.isArray(p) && p.length === 2 && Number.isInteger(p[0]) && p[0] > 0 && Number.isInteger(p[1]) && p[1] > 0);
  if (!bon) throw new Error(`${fichier}${FINE}: il faut jeu, releve_le, longueur_des_rangees et un histogramme de [longueur, nombre]. ${refaire}`);
  const longueurs: number[] = [];
  for (const [longueur, n] of histogramme as [number, number][]) for (let i = 0; i < n; i++) longueurs.push(longueur);
  return { jeu: l.jeu as string, releve_le: l.releve_le as string, longueur_des_rangees: l.longueur_des_rangees as number, longueurs };
}

// ---------- Le texte des jetons, lu dans le tokenizer de ton IA ----------

const TOKENIZER = 'projets/forge/forge/ressources/tokenizer-ton-ia-v1.json';
const SAUT_DE_LIGNE = '␊';

/** Les octets de chaque jeton ordinaire : les 256 octets, puis une fusion par jeton (comme TokenizerOctets). */
function octetsDesJetons(racineDepot: string | URL): Uint8Array[] {
  const t = lireJson(racineDepot, TOKENIZER, 'Récupère le tokenizer figé de ton IA depuis git.');
  if (!objet(t) || !Array.isArray(t.fusions) || t.taille_vocabulaire !== PREMIER_SPECIAL + NOMS_SPECIAUX.length) {
    throw new Error(`${TOKENIZER}${FINE}: ce n’est pas le tokenizer de ton IA (32 768 jetons, des fusions). Récupère-le depuis git.`);
  }
  const octets: Uint8Array[] = Array.from({ length: 256 }, (_, i) => Uint8Array.of(i));
  for (const [a, b] of t.fusions as [number, number][]) {
    const ab = new Uint8Array(octets[a].length + octets[b].length);
    ab.set(octets[a]);
    ab.set(octets[b], octets[a].length);
    octets.push(ab);
  }
  return octets;
}

/**
 * Le texte de chaque jeton, comme `montrer` du projet 1.7 : ses octets lus en UTF-8 (un caractère coupé entre
 * deux jetons devient « � »), « ␊ » pour un saut de ligne, et son nom pour un jeton spécial.
 */
export function textesDesJetons(ids: Iterable<number>, racineDepot: string | URL = '..'): Record<number, string> {
  const octets = octetsDesJetons(racineDepot);
  const decodeur = new TextDecoder('utf-8');
  const textes: Record<number, string> = {};
  for (const id of ids) {
    if (!Number.isInteger(id) || id < 0 || id >= PREMIER_SPECIAL + NOMS_SPECIAUX.length) {
      throw new Error(`L’identifiant ${id} n’est pas un jeton de ton IA (de 0 à ${PREMIER_SPECIAL + NOMS_SPECIAUX.length - 1}).`);
    }
    if (id >= PREMIER_SPECIAL) textes[id] = NOMS_SPECIAUX[id - PREMIER_SPECIAL];
    else if (id < octets.length) textes[id] = decodeur.decode(octets[id]).replaceAll('\n', SAUT_DE_LIGNE);
    else throw new Error(`L’identifiant ${id} est libre dans le tokenizer de ton IA : il ne désigne aucun jeton.`);
  }
  return textes;
}

/** Les octets d'une suite de jetons ordinaires, mis bout à bout puis lus en UTF-8 : le texte encodé, comme `tok.decoder`. */
export function decoderLesIds(ids: readonly number[], racineDepot: string | URL = '..'): string {
  const octets = octetsDesJetons(racineDepot);
  const morceaux = ids.map((id) => {
    exiger(id < octets.length, `l’id ${id} n’est pas un jeton ordinaire`);
    return octets[id];
  });
  const tout = new Uint8Array(morceaux.reduce((n, m) => n + m.length, 0));
  let i = 0;
  for (const m of morceaux) {
    tout.set(m, i);
    i += m.length;
  }
  return new TextDecoder('utf-8').decode(tout);
}

// ---------- Le balayage du taux d'apprentissage ----------

/** Le relevé du balayage du taux de ton IA 1.7, écrit par `balayage` dans le projet 1.7, à partir des journaux des essais. */
export const FICHIER_BALAYAGE_SFT_17 = 'projets/1.7-conversation/mesures/balayage-sft-1.7.json';

/** Un essai du balayage : son dossier, son taux maximal, son dernier pas, et ses pertes de validation [pas, perte]. */
export interface EssaiDuBalayage {
  essai: string;
  taux_max: number;
  pas: number;
  validations: [number, number][];
}

/** Les essais du balayage, rangés par taux croissant. */
export interface BalayageDuTaux {
  releve_le: string;
  essais: EssaiDuBalayage[];
}

/** Le relevé du balayage, ou null tant qu'il n'est pas fait. Un relevé au mauvais format arrête la construction. */
export function lireBalayage(racineDepot: string | URL = '..'): BalayageDuTaux | null {
  const fichier = FICHIER_BALAYAGE_SFT_17;
  if (!existsSync(join(enChemin(racineDepot), fichier))) return null;
  const refaire =
    'Relance-le, depuis projets/1.7-conversation : uv run --extra cpu python -m conversation_pas_a_pas balayage <dossier d’essai> <dossier d’essai> … --json mesures/balayage-sft-1.7.json.';
  const b = lireJson(racineDepot, fichier, refaire);
  const essais = objet(b) ? b.essais : undefined;
  const bonEssai = (e: unknown) =>
    objet(e) &&
    typeof e.essai === 'string' &&
    fini(e.taux_max) &&
    e.taux_max > 0 &&
    Number.isInteger(e.pas) &&
    Array.isArray(e.validations) &&
    e.validations.length > 0 &&
    e.validations.every((v: unknown) => Array.isArray(v) && v.length === 2 && Number.isInteger(v[0]) && fini(v[1]));
  const valides = Array.isArray(essais) && essais.length > 0 && essais.every(bonEssai);
  const croissants = valides && (essais as EssaiDuBalayage[]).every((e, i, tous) => i === 0 || tous[i - 1].taux_max < e.taux_max);
  if (!objet(b) || typeof b.releve_le !== 'string' || !valides || !croissants) {
    throw new Error(`${fichier}${FINE}: il faut releve_le et des essais (essai, taux_max, pas, validations), par taux croissant. ${refaire}`);
  }
  return b as unknown as BalayageDuTaux;
}

/** L'écart sous lequel deux dernières pertes de validation sont égales : la règle du balayage (docs/mesures/ton-ia-1.7.md). */
export const EGALITE_DU_BALAYAGE = 0.005;

/**
 * L'essai que retient la règle du balayage, fixée avant les essais : celui dont la dernière perte de validation est la
 * plus basse ; en cas d'égalité à 0,005 près, celui du plus petit taux. Rend son rang dans `essais` (par taux croissant).
 */
export function retenuDuBalayage(essais: readonly EssaiDuBalayage[]): number {
  exiger(essais.length > 0, 'le balayage n’a aucun essai');
  const derniere = (e: EssaiDuBalayage) => e.validations[e.validations.length - 1][1];
  const meilleure = Math.min(...essais.map(derniere));
  // Les essais sont par taux croissant : le premier qui égale la meilleure, à 0,005 près, a le plus petit taux.
  return essais.findIndex((e) => derniere(e) - meilleure <= EGALITE_DU_BALAYAGE);
}

// ---------- Les réglages des affinages ----------

/**
 * Les configurations de l'affinage de ton IA 1.7, dans forge : la version publiée et sa version courte, au taux 1e-4,
 * puis les deux premières, au taux 3e-4, gardées pour comparer.
 */
export const FICHIERS_REGLAGES_SFT = Object.freeze({
  'sft-1.7': 'projets/forge/configs/sft-1.7.toml',
  'sft-1.7-court': 'projets/forge/configs/sft-1.7-court.toml',
  'sft-1.7-3e-4': 'projets/forge/configs/sft-1.7-3e-4.toml',
  'sft-1.7-court-3e-4': 'projets/forge/configs/sft-1.7-court-3e-4.toml',
} as const);

/** Les réglages d'un affinage : ceux d'un entraînement, plus sa méthode, sa version de départ et la longueur des rangées. */
export interface ReglagesSft extends ReglagesEntrainement {
  methode: string;
  depart: string;
  longueur: number;
}

/** Les réglages de configs/sft-1.7.toml ou de sa version courte, lus comme ceux du chapitre 1.5. */
export function lireReglagesSft(nom: keyof typeof FICHIERS_REGLAGES_SFT, racineDepot: string | URL = '..'): ReglagesSft {
  const fichier = FICHIERS_REGLAGES_SFT[nom];
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) throw new Error(`${fichier}${FINE}: la configuration manque. Récupère-la depuis git.`);
  const texte = readFileSync(chemin, 'utf8');
  const lire = (cle: string, motif: RegExp): string => {
    const m = new RegExp(`^${cle}\\s*=\\s*${motif.source}\\s*(#.*)?$`, 'm').exec(texte.replace(/\r\n?/g, '\n'));
    if (m === null) throw new Error(`${fichier}${FINE}: le réglage ${cle} manque ou ne se lit pas. Corrige la configuration.`);
    return m[1];
  };
  // La fin de la descente du taux : la valeur par défaut de ratio_min dans taux() (planning.py), comme au chapitre 1.5.
  const planning = lireTexte(racineDepot, 'projets/forge/forge/entrainement/planning.py');
  const ratio = /def taux\([^)]*ratio_min: float = ([\d.]+)\)/.exec(planning);
  if (ratio === null) throw new Error('projets/forge/forge/entrainement/planning.py : ratio_min ne se lit plus dans taux(). Revois lireReglagesSft.');
  return {
    ...analyserReglages(texte, fichier, Number(ratio[1])),
    methode: lire('methode', /"([a-z]+)"/),
    depart: lire('depart', /"([\w.-]+)"/),
    longueur: Number(lire('longueur', /(\d+)/)),
  };
}

function lireTexte(racineDepot: string | URL, fichier: string): string {
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) throw new Error(`${fichier}${FINE}: le fichier manque. Récupère-le depuis git.`);
  return readFileSync(chemin, 'utf8').replace(/\r\n?/g, '\n');
}

/** Les réglages du petit affinage du projet (petit_affinage.py), que le chapitre cite : ses taux et son pré-entraînement express. */
export interface ReglagesDeLEssai {
  tauxAffinage: number;
  tauxPreEntrainement: number;
  pasPreEntrainement: number;
}

/** Les constantes de petit_affinage.py que le chapitre cite, lues dans le fichier. */
export function lireReglagesDeLEssai(racineDepot: string | URL = '..'): ReglagesDeLEssai {
  const fichier = 'projets/1.7-conversation/conversation_pas_a_pas/petit_affinage.py';
  const texte = lireTexte(racineDepot, fichier);
  const lire = (nom: string): number => {
    const m = new RegExp(`^${nom} = ([\\d.e-]+)`, 'm').exec(texte);
    const x = m === null ? Number.NaN : Number(m[1]);
    if (!Number.isFinite(x)) throw new Error(`${fichier}${FINE}: la constante ${nom} ne se lit plus. Revois lireReglagesDeLEssai.`);
    return x;
  };
  return { tauxAffinage: lire('TAUX_D_AFFINAGE'), tauxPreEntrainement: lire('TAUX_DU_PRE_ENTRAINEMENT'), pasPreEntrainement: lire('PAS_DU_PRE_ENTRAINEMENT') };
}

/** Ce que le chapitre dit du code et des réglages de forge, relu dans les fichiers. */
export interface FaitsDeForge {
  /** Le pré-entraînement sépare ses textes par <|fin_texte|> (forge/donnees/jetons.py). */
  finDeTexteEntreLesTextes: boolean;
  /** Le plongement d'entrée et la projection de sortie sont la même matrice, les « poids liés » (forge/modele/transformer.py). */
  poidsLies: boolean;
  /** Sans masque, l'attention dit seulement « causal » à PyTorch ; avec le masque par document, elle lui passe un masque complet. */
  attentionCausaleOuMasquee: boolean;
  /** La configuration de l'affinage dit qu'aucune source ne donne son taux, et qu'il a été choisi par un balayage (configs/sft-1.7.toml). */
  tauxSansSourceParBalayage: boolean;
}

/** Les faits de forge que le chapitre cite, relus dans le code et les réglages de forge. */
export function faitsDeForge(racineDepot: string | URL = '..'): FaitsDeForge {
  const jetons = lireTexte(racineDepot, 'projets/forge/forge/donnees/jetons.py');
  const transformer = lireTexte(racineDepot, 'projets/forge/forge/modele/transformer.py');
  const reglages = lireTexte(racineDepot, FICHIERS_REGLAGES_SFT['sft-1.7']);
  return {
    finDeTexteEntreLesTextes: jetons.includes('JETON_FIN_DE_TEXTE = "<|fin_texte|>"'),
    poidsLies: transformer.includes('sont la MÊME matrice (« poids liés »)'),
    attentionCausaleOuMasquee:
      transformer.includes('F.scaled_dot_product_attention(q, k, v, is_causal=True)') &&
      transformer.includes('F.scaled_dot_product_attention(q, k, v, attn_mask=masque)'),
    tauxSansSourceParBalayage:
      reglages.includes('Aucune source pour un modèle de cette taille') && reglages.includes('entraîné de zéro : choisi par un balayage'),
  };
}

/** Vrai si un morceau d'au moins `longueur` caractères revient au moins `fois` fois dans le texte : une réponse qui tourne en boucle. */
export function tourneEnBoucle(texte: string, longueur = 40, fois = 3): boolean {
  for (let i = 0; i + longueur <= texte.length; i++) {
    const morceau = texte.slice(i, i + longueur);
    if (texte.split(morceau).length - 1 >= fois) return true;
  }
  return false;
}

// ---------- Étape 1 : le pari « fin » ----------

export const QUESTION_FIN = 'Ton IA 1.5, qui n’a jamais vu de conversation, finit-elle d’elle-même ses réponses ?';

/** Les tranches du pari « fin », en part des réponses qui finissent par <|fin_tour|>. */
export const TRANCHES_FIN: readonly Tranche[] = Object.freeze([
  Object.freeze({ texte: 'Presque jamais', jusqua: 0.1 }),
  Object.freeze({ texte: 'Parfois', jusqua: 0.9 }),
  Object.freeze({ texte: 'Presque toujours', jusqua: Infinity }),
]);

/** Les nombres d'une mesure, ou null si le rapport manque ou si la mesure est absente. */
function mesure(rapport: RapportEtape | null, nom: string): NombresDeMesure | null {
  if (rapport === null) return null;
  const m = rapport.mesures[nom];
  return m === undefined || estAbsente(m) ? null : m;
}

function nombreDe(m: NombresDeMesure, cle: string): number {
  const x = m[cle];
  exiger(typeof x === 'number', `la mesure n’a plus de nombre « ${cle} »`);
  return x as number;
}

/** Les faits du pari « fin » : la part terminée de ton IA 1.5, et sur combien de réponses. Null sans son rapport. */
export function faitsDuPariFin(racineDepot: string | URL = '..'): { terminee: number; n: number } | null {
  const tenue = mesure(lireRapportEtape('1.5@1.7', racineDepot), 'tenue');
  return tenue === null ? null : { terminee: nombreDe(tenue, 'terminee'), n: nombreDe(tenue, 'n') };
}

/** Le pari « fin » : trois tranches de la part des réponses de ton IA 1.5 qui finissent leur tour. Null sans son rapport. */
export function choixFinDeTour(racineDepot: string | URL = '..'): Choix[] | null {
  const f = faitsDuPariFin(racineDepot);
  return f === null ? null : choixDesTranches(TRANCHES_FIN, f.terminee);
}

/** L'invite fixe que montre l'ouverture, parmi les dix des rapports d'étape. */
export const INVITE_DE_L_OUVERTURE = 'Qui es-tu ?';

/** La réponse d'une version de ton IA à une des invites fixes de son rapport, telle quelle. */
export function reponseALInvite(rapport: RapportEtape, invite: string): EchantillonDeReponse {
  const e = rapport.echantillons.find((x) => x.invite === invite);
  if (e === undefined) {
    throw new Error(
      `Le rapport de ${rapport.version} n’a pas de réponse à « ${invite} » : les invites fixes de forge ` +
        '(INVITES_DE_CONVERSATION, forge/evaluation/etape.py) ont changé, revois l’ouverture du chapitre 1.7.',
    );
  }
  return e;
}

// ---------- Étape 2 : le pari « gabarit » ----------

/** Les choix du pari « gabarit ». */
export const TEXTES_GABARIT = Object.freeze(['le jeton spécial qui ferme le tour', 'des jetons ordinaires, comme le reste du texte'] as const);

/** Les faits du pari « gabarit », tirés de la conversation « faux-special » des attendus. */
export function faitsDuPariGabarit(racineDepot: string | URL = '..'): {
  question: string;
  ids: number[];
  jetons: number;
  speciauxDansLeTexte: number;
  finsDeTour: number;
  jetonsDeLaConversation: number;
} {
  const c = lireConversationsDeReference(racineDepot).find((x) => x.nom === 'faux-special');
  exiger(c !== undefined && c.ids !== null, 'la conversation « faux-special » des attendus manque, ou forge la refuse');
  const question = c!.tours[0];
  exiger(question.role === 'utilisateur' && question.texte.includes('<|fin_tour|>'), 'la question de « faux-special » n’imite plus <|fin_tour|>');
  const finTour = SPECIAUX_TON_IA['<|fin_tour|>'];
  return {
    question: question.texte,
    ids: question.ids,
    jetons: question.ids.length,
    speciauxDansLeTexte: question.ids.filter((id) => id >= PREMIER_SPECIAL).length,
    finsDeTour: c!.ids!.filter((id) => id === finTour).length,
    jetonsDeLaConversation: c!.ids!.length,
  };
}

/** Le pari « gabarit » : quelqu'un écrit « <|fin_tour|> » dans sa question ; ton IA lit… */
export function choixGabarit(racineDepot: string | URL = '..'): Choix[] {
  const f = faitsDuPariGabarit(racineDepot);
  const ordinaires = f.speciauxDansLeTexte === 0;
  return TEXTES_GABARIT.map((texte, i) => ({ texte, juste: ordinaires ? i === 1 : i === 0 }));
}

// ---------- Étape 3 : le pari « masque » ----------

/** Les choix du pari « masque ». */
export const TEXTES_MASQUE = Object.freeze(['Tous', 'Ceux des réponses de l’assistant, fin de tour comprise', 'Seulement le dernier jeton'] as const);

/** La conversation de référence du pari « masque » : « Quelle est la capitale de la France ? », avec son message système. */
export const CONVERSATION_DU_MASQUE = CONVERSATION_DU_SYSTEME;

/** Les faits du pari « masque » : les jetons de la conversation, ceux de la réponse de l'assistant, et ceux qui sont appris. */
export function faitsDuPariMasque(racineDepot: string | URL = '..'): {
  jetons: number;
  reponse: number;
  appris: number;
  question: string;
  reponseTexte: string;
  masque: boolean[];
  masqueAssistant: boolean[];
} {
  const c = lireConversationsDeReference(racineDepot).find((x) => x.nom === CONVERSATION_DU_MASQUE);
  exiger(c !== undefined, `la conversation « ${CONVERSATION_DU_MASQUE} » des attendus manque`);
  const { ids, appris } = assemblerConversation(enToursEncodes(c!.tours));
  const assistant = c!.tours.find((t) => t.role === 'assistant')!;
  const question = c!.tours.find((t) => t.role === 'utilisateur')!;
  // Le masque « réponse de l'assistant, fin de tour comprise » : tout ce qui suit <|assistant|>, jusqu'au bout.
  const debut = ids.indexOf(SPECIAUX_TON_IA['<|assistant|>']);
  exiger(debut > 0 && c!.tours[c!.tours.length - 1].role === 'assistant', 'la conversation du pari « masque » ne finit plus par une seule réponse de l’assistant');
  return {
    jetons: ids.length,
    reponse: assistant.ids.length,
    appris: appris.filter(Boolean).length,
    question: question.texte,
    reponseTexte: assistant.texte,
    masque: appris,
    masqueAssistant: ids.map((_, i) => i > debut),
  };
}

/** Le pari « masque » : le juste est le masque que le jumeau d'encoder_conversation calcule. */
export function choixMasque(racineDepot: string | URL = '..'): Choix[] {
  const f = faitsDuPariMasque(racineDepot);
  const candidats = [f.masque.map(() => true), f.masqueAssistant, f.masque.map((_, i) => i === f.masque.length - 1)];
  const choix = TEXTES_MASQUE.map((texte, i) => ({ texte, juste: JSON.stringify(candidats[i]) === JSON.stringify(f.masque) }));
  exiger(choix.filter((c) => c.juste).length === 1, 'le masque de forge n’est plus aucun des trois choix du pari « masque »');
  return choix;
}

// ---------- Étape 4 : le pari « fuite » ----------

/** L'écart des logits au-delà duquel B a « vu » A : celui du test du projet (test_fuite.py). */
export const SEUIL_DE_FUITE = 1e-3;
/** L'écart qu'on tient pour l'arrondi des nombres : celui du même test, avec le masque. */
export const ECART_D_ARRONDI = 1e-5;

/** Les choix du pari « fuite ». */
export const TEXTES_FUITE = Object.freeze(['est calculée comme si elle était seule', 'voit la première'] as const);

/** Le pari « fuite » : le juste se lit dans mesures/fuite.json. */
export function choixFuite(racineDepot: string | URL = '..'): Choix[] {
  const f = lireFuite(racineDepot);
  exiger(f.avec_masque <= ECART_D_ARRONDI, 'avec le masque par document, la conversation B n’est plus calculée comme si elle était seule');
  const voit = f.sans_masque > SEUIL_DE_FUITE;
  return TEXTES_FUITE.map((texte, i) => ({ texte, juste: voit ? i === 1 : i === 0 }));
}

// ---------- Les paris « consignes » (étape 8) et « oubli » (étape 7) ----------

/**
 * L'écart, en invites d'IFEval-FR, sous lequel deux versions respectent « à peu près autant » de consignes : le même que
 * SEUIL_IFEVAL_EN_INVITES du chapitre 1.8. Le même modèle, mesuré deux fois, peut changer d'une ou deux invites.
 */
export const SEUIL_CONSIGNES_EN_INVITES = 3;

export type SensDesConsignes = 'plus' | 'autant' | 'moins';

/** Les choix du pari « consignes », dans l'ordre. */
export const TEXTES_CONSIGNES: Readonly<Record<SensDesConsignes, string>> = Object.freeze({
  plus: 'Plus d’invites que ton IA 1.5',
  autant: `À peu près autant, à ${SEUIL_CONSIGNES_EN_INVITES - 1} invites près`,
  moins: 'Moins d’invites que ton IA 1.5',
});

/** Le nombre d'invites d'IFEval-FR dont toutes les consignes sont respectées : la part du rapport, fois n, arrondie. */
export function invitesRespectees(ifeval: NombresDeMesure): number {
  return Math.round(nombreDe(ifeval, 'invite_stricte') * nombreDe(ifeval, 'n'));
}

/** Les faits du pari « consignes » : IFEval-FR de ton IA 1.5 et de ton IA 1.7, en parts et en invites. Null sans les deux rapports. */
export function faitsDesConsignes(racineDepot: string | URL = '..'): {
  avant: number;
  apres: number;
  consignesAvant: number;
  consignesApres: number;
  invitesAvant: number;
  invitesApres: number;
  n: number;
  sens: SensDesConsignes;
} | null {
  const avant = mesure(lireRapportEtape('1.5@1.7', racineDepot), 'ifeval_fr');
  const apres = mesure(lireRapportEtape('1.7@1.7', racineDepot), 'ifeval_fr');
  if (avant === null || apres === null) return null;
  const n = nombreDe(apres, 'n');
  exiger(nombreDe(avant, 'n') === n, 'ton IA 1.5 et ton IA 1.7 n’ont pas passé IFEval-FR sur le même nombre d’invites');
  const invitesAvant = invitesRespectees(avant);
  const invitesApres = invitesRespectees(apres);
  const ecart = invitesApres - invitesAvant;
  return {
    avant: nombreDe(avant, 'invite_stricte'),
    apres: nombreDe(apres, 'invite_stricte'),
    consignesAvant: nombreDe(avant, 'consigne_stricte'),
    consignesApres: nombreDe(apres, 'consigne_stricte'),
    invitesAvant,
    invitesApres,
    n,
    sens: ecart >= SEUIL_CONSIGNES_EN_INVITES ? 'plus' : ecart <= -SEUIL_CONSIGNES_EN_INVITES ? 'moins' : 'autant',
  };
}

/** Le pari « consignes » : ton IA 1.7 respecte-t-elle toutes les consignes de plus d'invites que ton IA 1.5 ? Null sans les deux rapports. */
export function choixConsignes(racineDepot: string | URL = '..'): Choix[] | null {
  const f = faitsDesConsignes(racineDepot);
  if (f === null) return null;
  return (Object.keys(TEXTES_CONSIGNES) as SensDesConsignes[]).map((s) => ({ texte: TEXTES_CONSIGNES[s], juste: s === f.sens }));
}

/** L'écart des pertes sur le texte du web en deçà duquel elle « ne bouge pas ». */
export const TOLERANCE_OUBLI = 0.01;

/** L'écart (en nats par jeton) sous lequel la phrase de l'oubli dit qu'elle a perdu « un peu » ; au-delà, « une part ». */
export const SEUIL_UN_PEU_OUBLI = 0.1;

export type SensDeLOubli = 'monte' | 'baisse' | 'stable';

/** Les choix du pari « oubli », dans l'ordre des sens. */
export const TEXTES_OUBLI: Readonly<Record<SensDeLOubli, string>> = Object.freeze({
  monte: 'Elle monte',
  baisse: 'Elle baisse',
  stable: `Elle ne bouge pas, à ${nombre(TOLERANCE_OUBLI, 2)} près`,
});

/** Les pertes sur le texte du web de ton IA 1.5 et de ton IA 1.7, ou null si l'un des deux rapports manque. */
export function faitsDeLOubli(racineDepot: string | URL = '..'): { avant: number; apres: number; ecart: number } | null {
  const avant = mesure(lireRapportEtape('1.5@1.7', racineDepot), 'oubli');
  const apres = mesure(lireRapportEtape('1.7@1.7', racineDepot), 'oubli');
  if (avant === null || apres === null) return null;
  const a = nombreDe(avant, 'perte');
  const b = nombreDe(apres, 'perte');
  return { avant: a, apres: b, ecart: b - a };
}

/** Le sens de l'oubli : la perte sur le texte du web monte, baisse, ou ne bouge pas (à 0,01 près). Null sans les deux rapports. */
export function sensDeLOubli(racineDepot: string | URL = '..'): SensDeLOubli | null {
  const f = faitsDeLOubli(racineDepot);
  if (f === null) return null;
  return Math.abs(f.ecart) <= TOLERANCE_OUBLI ? 'stable' : f.ecart > 0 ? 'monte' : 'baisse';
}

/** Le pari « oubli » : « Après l'affinage, sa perte sur le texte du web… ». Null sans les deux rapports. */
export function choixOubli(racineDepot: string | URL = '..'): Choix[] | null {
  const sens = sensDeLOubli(racineDepot);
  if (sens === null) return null;
  return (Object.keys(TEXTES_OUBLI) as SensDeLOubli[]).map((s) => ({ texte: TEXTES_OUBLI[s], juste: s === sens }));
}

/**
 * La phrase de l'étape 8 sur l'oubli, qui suit les rapports : elle dit si la perte de ton IA sur le texte du web
 * monte, baisse ou ne bouge pas, et de combien. Null sans les deux rapports (la page pose data-a-mesurer).
 */
export function phraseDeLOubli(racineDepot: string | URL = '..'): string | null {
  const f = faitsDeLOubli(racineDepot);
  const sens = sensDeLOubli(racineDepot);
  if (f === null || sens === null) return null;
  const de = (x: number) => `${nombre(f.avant, 3)} à ${nombre(x, 3)}`;
  if (sens === 'monte') {
    // « Un peu » seulement sous le seuil : au-delà, la phrase ne minimise pas.
    const combien = f.ecart < SEUIL_UN_PEU_OUBLI ? 'un peu de ce' : 'une part de ce';
    return `Sa perte sur le texte du web monte, de ${de(f.apres)}${FINE}: l’affinage lui a fait perdre ${combien} qu’elle savait prédire du français brut.`;
  }
  if (sens === 'baisse') {
    return `Sa perte sur le texte du web baisse, de ${de(f.apres)}${FINE}: l’affinage ne lui a rien fait perdre de mesurable sur ces textes, au contraire.`;
  }
  return `Sa perte sur le texte du web ne bouge pas, à ${nombre(TOLERANCE_OUBLI, 2)} près (de ${de(f.apres)})${FINE}: l’affinage ne lui a rien fait perdre de mesurable sur ces textes.`;
}

/**
 * La garde d'une phrase qui annonce le sens de l'oubli : elle arrête la construction si les rapports disent
 * autre chose. Un texte qui dit « monte » ne doit pas survivre à des rapports où la perte baisse.
 */
export function exigerSensDeLOubli(annonce: SensDeLOubli, racineDepot: string | URL = '..'): void {
  const sens = sensDeLOubli(racineDepot);
  exiger(sens === annonce, `le texte dit que la perte sur le texte du web « ${annonce} », les rapports disent « ${sens ?? 'à mesurer'} »`);
}

// ---------- Étape 4 : la figure de l'empaquetage ----------

/** Le nombre de rangées que la figure dessine. */
export const RANGEES_DESSINEES = 8;

/** Ce que range la figure : les longueurs du jeu de ton IA si elles sont relevées, sinon la liste de référence des attendus. */
export interface FigureEmpaquetage {
  source: 'jeu' | 'reference';
  longueurs: number[];
  resultats: EmpaquetageDeLaFigure[];
}

/**
 * Les quatre empaquetages de la figure, calculés à la construction par le jumeau de BFD (empaqueterLongueurs) :
 * avec les 135 471 exemples de sft-1.7, chacun peut prendre plus d'une dizaine de millisecondes sur un PC
 * (jusqu'à environ 140 ms avec des rangées de 4 096, relevé du 18/11/2026 sur des longueurs tirées au sort), trop
 * pour un téléphone à chaque geste. La figure choisit parmi les quatre.
 */
export function empaquetagesDeLaFigure(racineDepot: string | URL = '..'): FigureEmpaquetage {
  const jeu = lireLongueurs(racineDepot);
  const reference = jeu === null ? longueursDeReference(racineDepot) : null;
  exiger(jeu !== null || reference !== null, 'ni les longueurs de sft-1.7 ni la liste de remplacement des attendus ne sont là');
  const longueurs = jeu === null ? (reference as number[]) : jeu.longueurs;
  const resultats = LONGUEURS_DE_RANGEE.map((longueur): EmpaquetageDeLaFigure => {
    const { rangees, ecartes } = empaqueterLongueurs(longueurs, longueur + 1);
    let occupees = 0;
    for (const rangee of rangees) for (const i of rangee) occupees += longueurs[i];
    return {
      longueur,
      places: longueur + 1,
      rangees: rangees.length,
      occupees,
      ecartes,
      premieres: rangees.slice(0, RANGEES_DESSINEES).map((rangee) => rangee.map((i) => longueurs[i])),
    };
  });
  for (const r of resultats) exiger(r.rangees > 0 && Number.isFinite(r.occupees / (r.rangees * r.places)), `les rangées de ${r.longueur} n’ont rien rangé`);
  return { source: jeu === null ? 'reference' : 'jeu', longueurs, resultats };
}

/** Le plus long exemple d'une liste, et leur nombre : ce que dit la note de la figure. */
export function resumeDesLongueurs(longueurs: readonly number[]): { exemples: number; plusLong: number } {
  return { exemples: longueurs.length, plusLong: longueurs.reduce((m, x) => (x > m ? x : m), 0) };
}
