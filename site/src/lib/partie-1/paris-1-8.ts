// Les paris du chapitre 1.8, « L'aligner : préférences et récompenses », et ce que le chapitre lit du projet 1.8, de
// forge et des rapports d'étape, à la construction.
//
// Leurs bonnes réponses sont calculées, jamais tapées :
// - « note » : la réponse que les contrôles de forge préfèrent, par le jumeau des notes (noteSansJustesse, et la fin
//   du tour, par expliquerNote d'atelier-1-8.ts), sur la paire de l'ouverture ;
// - « notes » : l'ordre des critères, sur la même paire, la réponse préférée imaginée coupée et l'autre finie ;
// - « paires » : le plancher de forge (noter.py), relu dans son code ;
// - « vraisemblance » : les courbes de la DPO (mesures/entrainement-dpo-1.8.json) ;
// - « longueur » et « victoire » : la mesure victoire du rapport de ton IA 1.8 (« 1.8@1.8 »).
// Les trois derniers rendent null tant que leur fichier manque : la page pose alors data-a-mesurer à leur place.
//
// La paire de l'ouverture et de l'atelier est la première vraie paire d'une question à consignes de
// mesures/paires-exemples.json. Tant que ce fichier n'existe pas (il vient avec les paires de ton IA 1.8, tâche 12
// du plan 8), c'est une paire écrite pour l'exemple, sur une invite à deux consignes de forge, dite comme telle par
// la page, qui pose aussi data-a-mesurer à la place de la vraie.
//
// Une phrase du chapitre qui deviendrait fausse arrête la construction (« Exemple devenu faux : … »). Chaque
// fonction lit le dépôt dont on lui donne la racine (par défaut le dossier au-dessus de site/, d'où Vitest et les
// parcours sont lancés). Ce module lit les fichiers avec node:fs, sans import .json ni astro:* : un parcours
// Playwright peut l'importer. Les îlots n'en importent rien : ce qu'ils calculent est dans atelier-1-8.ts.

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre, pourcent } from '../nombres';
import {
  avecConsignes,
  comparerNotes,
  critereQuiDepartage,
  CRITERES,
  expliquerNote,
  noteEnTexte,
  phraseDeConsigne,
  type Critere,
  type Note,
  type NoteExpliquee,
} from './atelier-1-8';
import { estAbsente, lireRapportEtape, lireSeries, refaire, type NombresDeMesure, type RapportEtape } from './etapes';
import { extraireRegion } from '../regions';
import { extraireSymbole } from '../symboles';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { MOTS_MAXIMUM, MOTS_MINIMUM, type ConsigneDInvite, type ReglagesConsigne } from './notes';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-8.ts et le texte des paris du chapitre 1.8');

/** Les relevés du projet 1.8 que lit le chapitre, en chemins depuis la racine du dépôt. Ils viennent avec ton IA 1.8. */
export const FICHIERS_1_8 = Object.freeze({
  /** Les premières paires du jeu de préférences de ton IA 1.8 (`paires` du projet). */
  pairesExemples: 'projets/1.8-alignement/mesures/paires-exemples.json',
  /** Les essais du balayage de la DPO (`balayage` du projet). */
  balayage: 'projets/1.8-alignement/mesures/balayage-1.8.json',
  /** Les courbes de la DPO de ton IA 1.8 (`courbes` du projet). */
  courbes: 'projets/1.8-alignement/mesures/entrainement-dpo-1.8.json',
} as const);

/** La configuration de l'entraînement de ton IA 1.8, dans forge (elle vient avec son entraînement, au plan 7). */
export const CONFIG_DPO_18 = 'projets/forge/configs/dpo-1.8.toml';

// ---------- Lire le dépôt ----------

function enChemin(racineDepot: string | URL): string {
  return typeof racineDepot === 'string' && !racineDepot.startsWith('file:') ? racineDepot : fileURLToPath(racineDepot);
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

/** Un fichier JSON du dépôt, ou null s'il n'existe pas. Un JSON illisible est une erreur qui dit quoi relancer. */
function lireJsonSiPresent(racineDepot: string | URL, fichier: string, quoiRelancer: string): unknown {
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) return null;
  try {
    return JSON.parse(readFileSync(chemin, 'utf8'));
  } catch (erreur) {
    const raison = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`${fichier}${FINE}: JSON illisible (${raison}). ${quoiRelancer}`);
  }
}

function lireTexte(racineDepot: string | URL, fichier: string): string {
  const chemin = join(enChemin(racineDepot), fichier);
  if (!existsSync(chemin)) throw new Error(`${fichier}${FINE}: le fichier manque. Récupère-le depuis git.`);
  return readFileSync(chemin, 'utf8').replace(/\r\n?/g, '\n');
}

/** Les blancs d'un texte ramenés à une espace : une phrase d'un docstring se cherche sans ses retours à la ligne. */
function enUneLigne(t: string): string {
  return t.replace(/\s+/g, ' ');
}

// ---------- Les consignes de référence du projet ----------

/** Une consigne des attendus du projet 1.8 : son identifiant, ses réglages de référence et sa phrase écrite par forge. */
export interface ConsigneDeReference {
  id: string;
  kwargs: ReglagesConsigne;
  consigne: string;
}

const REFAIRE_ATTENDUS = 'Régénère les attendus : uv run --extra cpu python -m alignement_pas_a_pas.attendus, dans projets/1.8-alignement.';

/** Les huit consignes de forge avec leurs réglages de référence (tests/attendus.json du projet 1.8, section « consignes »). */
export function lireConsignesDeReference(racineDepot: string | URL = '..'): ConsigneDeReference[] {
  const fichier = FICHIERS_PARTIE_1.notes;
  const a = lireJsonSiPresent(racineDepot, fichier, REFAIRE_ATTENDUS);
  if (a === null) throw new Error(`${fichier}${FINE}: le fichier manque. ${REFAIRE_ATTENDUS}`);
  const consignes = objet(a) ? a.consignes : undefined;
  const bonnes = Array.isArray(consignes) && consignes.every((c) => objet(c) && texte(c.id) && objet(c.kwargs) && texte(c.consigne));
  if (!bonnes) throw new Error(`${fichier}${FINE}: la section « consignes » manque ou n’a pas id, kwargs et consigne. ${REFAIRE_ATTENDUS}`);
  return consignes as ConsigneDeReference[];
}

// ---------- Les paires de préférences ----------

/** Une réponse d'une paire, telle que `paires` du projet l'écrit (resumer.py). */
export interface ReponseDePaire {
  texte: string;
  terminee: boolean;
  note: Note;
  jetons: number;
  logp_reference: number;
}

/** Une vraie paire de ton IA : l'invite, ses consignes, les deux réponses et ce qui les a départagées. */
export interface PaireExemple {
  id: string;
  source: { nom: string; licence: string; lien: string };
  invite: { role: string; texte: string }[];
  contraintes: ConsigneDInvite[];
  attendu: number | null;
  choisie: ReponseDePaire;
  rejetee: ReponseDePaire;
  raison: Critere;
}

function reponseValide(r: unknown): boolean {
  return (
    objet(r) &&
    texte(r.texte) &&
    typeof r.terminee === 'boolean' &&
    objet(r.note) &&
    CRITERES.every((c) => Number.isInteger((r.note as Record<string, unknown>)[c])) &&
    fini(r.jetons) &&
    fini(r.logp_reference)
  );
}

function paireValide(p: unknown): boolean {
  return (
    objet(p) &&
    texte(p.id) &&
    objet(p.source) &&
    texte(p.source.nom) &&
    texte(p.source.licence) &&
    texte(p.source.lien) &&
    Array.isArray(p.invite) &&
    p.invite.length > 0 &&
    p.invite.every((t) => objet(t) && texte(t.role) && texte(t.texte)) &&
    Array.isArray(p.contraintes) &&
    p.contraintes.every((c) => Array.isArray(c) && c.length === 2 && texte(c[0]) && objet(c[1])) &&
    (p.attendu === null || fini(p.attendu)) &&
    reponseValide(p.choisie) &&
    reponseValide(p.rejetee) &&
    texte(p.raison) &&
    (CRITERES as readonly string[]).includes(p.raison)
  );
}

/** Les premières paires du jeu de ton IA 1.8 (mesures/paires-exemples.json), ou null tant qu'elles ne sont pas relevées. */
export function lirePairesExemples(racineDepot: string | URL = '..'): PaireExemple[] | null {
  const fichier = FICHIERS_1_8.pairesExemples;
  const p = lireJsonSiPresent(racineDepot, fichier, refaire(fichier));
  if (p === null) return null;
  if (!Array.isArray(p) || p.length === 0 || !p.every(paireValide)) {
    throw new Error(
      `${fichier}${FINE}: il faut une liste de paires, chacune avec id, source, invite, contraintes, attendu, choisie, rejetee et raison. ${refaire(fichier)}`,
    );
  }
  return p as PaireExemple[];
}

// ---------- La paire de l'ouverture et de l'atelier ----------

/** La question de la paire d'exemple, tant que les vraies paires de ton IA n'existent pas. */
export const QUESTION_D_EXEMPLE = 'Quelle est la capitale de la France ?';
/** Ses deux consignes, avec les réglages de référence des attendus du projet : la page compare ses verdicts au Python. */
export const CONSIGNES_D_EXEMPLE: readonly ConsigneDInvite[] = Object.freeze([
  Object.freeze(['mots_max', Object.freeze({ n: 20 })] as const),
  Object.freeze(['sans_virgule', Object.freeze({})] as const),
]);
/** Ses deux réponses, écrites pour l'exemple : A, plus riche, a une virgule ; B, plus courte, respecte les deux consignes. */
export const REPONSES_D_EXEMPLE: readonly { texte: string; terminee: boolean }[] = Object.freeze([
  Object.freeze({ texte: 'La capitale de la France est Paris, une grande ville au bord de la Seine.', terminee: true }),
  Object.freeze({ texte: 'Paris est la capitale de la France.', terminee: true }),
]);

export type Lettre = 'A' | 'B';

/** Une réponse montrée par l'ouverture : sa lettre, son texte, si elle a fini son tour, et sa note par le jumeau. */
export interface ReponseMontree {
  lettre: Lettre;
  texte: string;
  terminee: boolean;
  note: Note;
}

/** La paire de l'ouverture et de l'atelier. */
export interface PaireDeLOuverture {
  /** Une vraie paire de ton IA (paires-exemples.json), ou celle de l'exemple. */
  reelle: boolean;
  /** Le message système de l'invite, s'il y en a un. */
  systeme: string | null;
  /** Le message de l'utilisateur, consignes comprises, tel que ton IA l'a lu. */
  invite: string;
  consignes: ConsigneDInvite[];
  reponses: [ReponseMontree, ReponseMontree];
  /** La lettre de la réponse que forge a choisie (une vraie paire), null pour l'exemple. */
  choisie: Lettre | null;
  /** La source de l'invite et sa licence (une vraie paire), null pour l'exemple. */
  source: PaireExemple['source'] | null;
}

function montree(lettre: Lettre, r: { texte: string; terminee: boolean }, consignes: readonly ConsigneDInvite[]): ReponseMontree {
  return { lettre, texte: r.texte, terminee: r.terminee, note: expliquerNote(r.texte, r.terminee, consignes).note };
}

/**
 * La paire de l'ouverture et de l'atelier : la première vraie paire d'une question à consignes (l'atelier ne refait
 * pas le critère « juste » d'un problème), ses deux réponses dans l'ordre de leur texte, pour que la lettre ne dise
 * pas laquelle est choisie ; ou, sans paires-exemples.json, la paire de l'exemple.
 */
export function paireDeLOuverture(racineDepot: string | URL = '..'): PaireDeLOuverture {
  const paires = lirePairesExemples(racineDepot);
  if (paires === null) {
    // Les phrases des consignes de l'exemple sont celles que forge écrit (attendus du projet, calculés par le Python).
    const reference = lireConsignesDeReference(racineDepot);
    for (const [id, kwargs] of CONSIGNES_D_EXEMPLE) {
      const r = reference.find((c) => c.id === id);
      exiger(r !== undefined && JSON.stringify(r.kwargs) === JSON.stringify(kwargs), `la consigne « ${id} » de l’exemple n’a plus les réglages de référence des attendus`);
      exiger(r!.consigne === phraseDeConsigne(id, kwargs), `la phrase de la consigne « ${id} » n’est plus celle de forge`);
    }
    const consignes = CONSIGNES_D_EXEMPLE.map(([id, k]) => [id, k] as ConsigneDInvite);
    return {
      reelle: false,
      systeme: null,
      invite: avecConsignes(QUESTION_D_EXEMPLE, consignes),
      consignes,
      reponses: [montree('A', REPONSES_D_EXEMPLE[0], consignes), montree('B', REPONSES_D_EXEMPLE[1], consignes)],
      choisie: null,
      source: null,
    };
  }
  const p = paires.find((x) => x.attendu === null && x.contraintes.length > 0);
  if (p === undefined) {
    throw new Error(
      `${FICHIERS_1_8.pairesExemples}${FINE}: aucune des ${paires.length} paires n’est une question avec consignes, et l’atelier n’en note pas d’autre. ` +
        `Relève plus de paires (--n). ${refaire(FICHIERS_1_8.pairesExemples)}`,
    );
  }
  const utilisateur = p.invite[p.invite.length - 1];
  exiger(utilisateur.role === 'utilisateur', `l’invite de la paire ${p.id} ne finit plus par le message de l’utilisateur`);
  const systeme = p.invite.length > 1 && p.invite[0].role === 'systeme' ? p.invite[0].texte : null;
  // Le jumeau retrouve les notes de forge (sauf « juste », acquis pour une question), et forge a choisi la meilleure.
  for (const [nom, r] of [['choisie', p.choisie], ['rejetee', p.rejetee]] as const) {
    const n = expliquerNote(r.texte, r.terminee, p.contraintes).note;
    exiger(CRITERES.every((c) => n[c] === r.note[c]), `la note de la ${nom} de la paire ${p.id} n’est plus celle du jumeau`);
  }
  exiger(comparerNotes(p.choisie.note, p.rejetee.note) > 0, `la choisie de la paire ${p.id} n’a plus la meilleure note`);
  const [premiere, seconde] = [p.choisie, p.rejetee].sort((a, b) => (a.texte < b.texte ? -1 : a.texte > b.texte ? 1 : 0));
  const reponses: [ReponseMontree, ReponseMontree] = [montree('A', premiere, p.contraintes), montree('B', seconde, p.contraintes)];
  return {
    reelle: true,
    systeme,
    invite: utilisateur.texte,
    consignes: p.contraintes,
    reponses,
    choisie: premiere === p.choisie ? 'A' : 'B',
    source: p.source,
  };
}

// ---------- Étape 1 : le pari « note » ----------

/** Les choix du pari « note ». */
export const TEXTES_NOTE = Object.freeze(['La réponse A', 'Aucune : elles ont la même note', 'La réponse B'] as const);

/** Le pari « note » : la réponse que les contrôles de forge préfèrent, par le jumeau, sur la paire de l'ouverture. */
export function choixNote(racineDepot: string | URL = '..'): Choix[] {
  const p = paireDeLOuverture(racineDepot);
  const c = comparerNotes(p.reponses[0].note, p.reponses[1].note);
  const juste = c > 0 ? 0 : c < 0 ? 2 : 1;
  if (p.choisie !== null) exiger(TEXTES_NOTE[juste] === `La réponse ${p.choisie}`, 'le jumeau ne préfère plus la réponse que forge a choisie');
  return TEXTES_NOTE.map((texte, i) => ({ texte, juste: i === juste }));
}

/** Ce que deux réponses à égalité font d'un critère, en mots : « finissent leur tour »… */
function aEgalite(e: NoteExpliquee, c: Critere): string {
  const x = e.criteres.find((k) => k.nom === c)!;
  if (c === 'terminee') return x.verdict ? 'finissent leur tour' : 'sont coupées par la limite de jetons';
  if (c === 'consignes') return `respectent ${nombre(x.valeur)} consigne${x.valeur >= 2 ? 's' : ''} sur ${nombre(x.maximum)}`;
  if (c === 'francais') return x.verdict ? 'passent le contrôle du français' : 'sont dans une autre langue';
  const bornes = `${nombre(MOTS_MINIMUM)} à ${nombre(MOTS_MAXIMUM)} mots`;
  if (c === 'longueur') return x.verdict ? `ont de ${bornes}` : `sortent des ${bornes}`;
  return x.verdict ? 'sont justes' : 'sont fausses';
}

/** Ce qui départage deux réponses sur un critère, en mots : « B respecte 2 consignes sur 2, A seulement 1 »… */
function departage(c: Critere, G: string, g: NoteExpliquee, L: string, l: NoteExpliquee): string {
  const valeur = (e: NoteExpliquee) => e.criteres.find((k) => k.nom === c)!.valeur;
  if (c === 'terminee') return `${G} finit son tour, alors que ${L} est coupée par la limite de jetons`;
  if (c === 'consignes') {
    const n = g.criteres.find((k) => k.nom === c)!.maximum;
    const vl = valeur(l);
    const oubliees = l.consignes.filter((k) => !k.respectee).map((k) => `« ${k.consigne} »`);
    return (
      `${G} respecte ${nombre(valeur(g))} consigne${valeur(g) >= 2 ? 's' : ''} sur ${nombre(n)}, ${L} ${vl === 0 ? 'aucune' : `seulement ${nombre(vl)}`}` +
      `${FINE}: elle oublie ${oubliees.join(' et ')}`
    );
  }
  if (c === 'francais') return `${G} passe le contrôle du français, alors que ${L} est dans une autre langue`;
  if (c === 'longueur') return `${G} a ${nombre(g.mots)} mots, ${L} ${nombre(l.mots)}, hors des ${nombre(MOTS_MINIMUM)} à ${nombre(MOTS_MAXIMUM)}`;
  return `${G} est juste, ${L} non`;
}

/**
 * L'explication du pari « note », calculée : la réponse préférée, les critères où les deux sont à égalité avant
 * celui qui décide, celui-là, et ce qu'il départage.
 */
export function phraseDeLaNote(racineDepot: string | URL = '..'): string {
  const p = paireDeLOuverture(racineDepot);
  const [ea, eb] = p.reponses.map((r) => expliquerNote(r.texte, r.terminee, p.consignes));
  const decide = critereQuiDepartage(ea.note, eb.note);
  if (decide === null) return 'Aucune : elles ont la même note, critère par critère. Forge n’en ferait pas de paire.';
  const aGagne = comparerNotes(ea.note, eb.note) > 0;
  const [g, l] = aGagne ? [ea, eb] : [eb, ea];
  const [G, L] = aGagne ? ['A', 'B'] : ['B', 'A'];
  const avant = CRITERES.slice(0, CRITERES.indexOf(decide)).filter((c) => c !== 'juste');
  const egalites = avant.length === 0 ? '' : `Les deux ${avant.map((c) => aEgalite(g, c)).join(', et ')}. `;
  return `La réponse ${G}. ${egalites}Mais ${departage(decide, G, g, L, l)}. C’est le premier critère qui les départage${FINE}: forge s’arrête là.`;
}

// ---------- Étape 3 : le pari « notes », l'ordre des critères ----------

/** Le pari « notes », tiré de la paire de l'ouverture : sa réponse préférée, imaginée coupée, et l'autre, finie. */
export interface FaitsDuPariNotes {
  /** La lettre de la réponse que forge préfère dans la paire, et celle de l'autre. */
  preferee: Lettre;
  autre: Lettre;
  /** Leurs notes telles quelles, puis la préférée coupée et l'autre finie. */
  notePreferee: Note;
  noteAutre: Note;
  coupee: NoteExpliquee;
  finie: NoteExpliquee;
}

/** Les faits du pari « notes », sur la paire de l'ouverture (la vraie, ou celle de l'exemple). */
export function faitsDuPariNotes(racineDepot: string | URL = '..'): FaitsDuPariNotes {
  const p = paireDeLOuverture(racineDepot);
  const [a, b] = p.reponses;
  const c = comparerNotes(a.note, b.note);
  exiger(c !== 0, 'les deux réponses de la paire de l’ouverture ont la même note : le pari « notes » n’a plus de réponse préférée');
  const [g, l] = c > 0 ? [a, b] : [b, a];
  return {
    preferee: g.lettre,
    autre: l.lettre,
    notePreferee: g.note,
    noteAutre: l.note,
    coupee: expliquerNote(g.texte, false, p.consignes),
    finie: expliquerNote(l.texte, true, p.consignes),
  };
}

/** Le pari « notes » : la réponse préférée, si forge l'avait coupée, contre l'autre, finie. */
export function choixOrdreDesCriteres(racineDepot: string | URL = '..'): Choix[] {
  const f = faitsDuPariNotes(racineDepot);
  const textes = [`La réponse ${f.autre}, finie`, `La réponse ${f.preferee}, coupée`, 'Aucune : elles se valent'];
  const c = comparerNotes(f.finie.note, f.coupee.note);
  const juste = c > 0 ? 0 : c < 0 ? 1 : 2;
  return textes.map((texte, i) => ({ texte, juste: i === juste }));
}

/** La question, la précision et l'explication du pari « notes », calculées sur la paire de l'ouverture. */
export function textesDuPariNotes(racineDepot: string | URL = '..'): { question: string; precision: string; explication: string } {
  const f = faitsDuPariNotes(racineDepot);
  const juste = choixOrdreDesCriteres(racineDepot).find((x) => x.juste)!.texte;
  exiger(juste === `La réponse ${f.autre}, finie` && CRITERES[0] === 'terminee', 'une réponse coupée ne perd plus toujours');
  return {
    question:
      `Reprends la paire de l’ouverture : forge y préfère la réponse ${f.preferee}. Imagine qu’il l’ait coupée à la ` +
      `limite de jetons, et que la ${f.autre} finisse son tour. Laquelle préfère-t-il alors${FINE}?`,
    precision: `Sans coupure, la ${f.preferee} a la note ${noteEnTexte(f.notePreferee)}, la ${f.autre} ${noteEnTexte(f.noteAutre)}.`,
    explication:
      `La réponse ${f.autre}, finie. La fin du tour est le premier critère${FINE}: une réponse coupée perd toujours, même ` +
      `avec ce qui la faisait gagner. Coupée, la ${f.preferee} a la note ${noteEnTexte(f.coupee.note)}${FINE}; la ` +
      `${f.autre}, finie, ${noteEnTexte(f.finie.note)}${FINE}: forge compare d’abord 0 et 1, et s’arrête là.`,
  };
}

// ---------- Ce que le chapitre dit de forge, relu dans son code ----------

/** Les faits de forge que le chapitre cite : les critères, la recette des paires, les réglages de la DPO. */
export interface FaitsDeForge18 {
  /** Les cinq critères de Note, dans leur ordre (forge/preferences/noter.py). */
  criteres: string[];
  /** Une paire n'est gardée que si la meilleure réponse est finie et, pour un problème, juste (peut_etre_choisie). */
  plancherFinieEtJuste: boolean;
  /** Deux notes égales ne donnent pas de paire (choisir_paire rend None, sans_paire « egalite »). */
  egaliteSansPaire: boolean;
  /** La raison du plancher : la DPO prend la réponse choisie pour modèle, et son terme SFT l'apprend mot à mot. */
  modeleMotAMot: boolean;
  motsMinimum: number;
  motsMaximum: number;
  /** La recette des paires (RecettePreferences) : ses valeurs par défaut. */
  recette: { reponsesParInvite: number; temperature: number; topK: number; nNouveaux: number; longueur: number; partValidation: number };
  /** Les invites de preferences-1.8 et de preferences-1.8-court. */
  invites: number;
  invitesCourt: number;
  /** Sous ce taux de paires utilisables, la construction s'arrête et le dit. */
  seuilDuTauxDePaires: number;
  /** La part des problèmes parmi les invites, et le nombre de consignes ajoutées à une question. */
  partDesProblemes: number;
  consignesMin: number;
  consignesMax: number;
  /** Les valeurs par défaut de la table [dpo] (ReglagesDPO, forge/entrainement/boucle.py). */
  dpo: { beta: number; normaliserLongueur: boolean; poidsSft: number };
  /** Le README de forge : la référence est calculée une fois, avant le premier pas, et rangée dans le jeu. */
  referenceCalculeeUneFois: boolean;
  /** Le README de forge : les essais d'un balayage se départagent par la victoire, sur les invites de validation des paires. */
  balayageDepartageParLaVictoire: boolean;
  /** Le README de forge : un taux de victoire élevé est attendu par construction, ce n'est pas un juge. */
  victoirePasUnJuge: boolean;
  /** Le README de forge : dans la victoire, une égalité compte une demie. */
  egaliteUneDemie: boolean;
  /** Pour une question (sans réponse attendue), le critère « juste » est acquis (noter de noter.py). */
  questionSansJustesse: boolean;
  /** Le README de forge : les questions des invites sont celles de Luth-2 que le SFT n'a pas apprises. */
  questionsNonApprises: boolean;
  /** Les invites se traitent par paquets (INVITES_PAR_PAQUET). */
  invitesParPaquet: number;
  /** Le README de forge : l'index du jeu donne la longueur moyenne des réponses choisies et rejetées. */
  longueursDesPaires: boolean;
  /** noter.py : deux réponses également bonnes, une courte et une longue, ont la même note. */
  memeNoteCourteOuLongue: boolean;
}

/** Les valeurs par défaut de la table [dpo] de forge : faitsDeForge18 vérifie qu'elles sont toujours celles de boucle.py. */
export const DEFAUTS_DPO = Object.freeze({ beta: 0.1, normaliser_longueur: false, poids_sft: 1 });

/** Les faits de forge que le chapitre cite, relus dans le code et le README de forge. */
export function faitsDeForge18(racineDepot: string | URL = '..'): FaitsDeForge18 {
  const noter = lireTexte(racineDepot, 'projets/forge/forge/preferences/noter.py');
  const construction = lireTexte(racineDepot, 'projets/forge/forge/preferences/construction.py');
  const invites = lireTexte(racineDepot, 'projets/forge/forge/preferences/invites.py');
  const boucle = lireTexte(racineDepot, 'projets/forge/forge/entrainement/boucle.py');
  const readme = enUneLigne(lireTexte(racineDepot, 'projets/forge/README.md'));
  const lire = (source: string, fichier: string, motif: RegExp): string => {
    const m = motif.exec(source);
    if (m === null) throw new Error(`${fichier}${FINE}: ${motif.source} ne se lit plus. Revois faitsDeForge18 (paris-1-8.ts).`);
    return m[1];
  };
  const nombreLu = (source: string, fichier: string, motif: RegExp) => Number(lire(source, fichier, motif).replaceAll('_', ''));
  const classeNote = lire(noter, 'noter.py', /class Note\(NamedTuple\):\n((?:.*\n){1,12}?)\n\n/);
  const reglagesDpo = lire(boucle, 'boucle.py', /class ReglagesDPO:\n([\s\S]*?)\n    def /);
  return {
    criteres: [...classeNote.matchAll(/^ {4}(\w+): int$/gm)].map((m) => m[1]),
    plancherFinieEtJuste: noter.includes('return note.terminee == 1 and note.juste == 1'),
    egaliteSansPaire: noter.includes('if notes[meilleure] == notes[pire]:\n        return None') && noter.includes('return EGALITE'),
    modeleMotAMot: enUneLigne(noter).includes('la DPO prend la réponse choisie pour modèle, et son terme SFT l\'apprend mot à mot'),
    motsMinimum: nombreLu(noter, 'noter.py', /^MOTS_MINIMUM = (\d+)$/m),
    motsMaximum: nombreLu(noter, 'noter.py', /^MOTS_MAXIMUM = (\d+)$/m),
    recette: {
      reponsesParInvite: nombreLu(construction, 'construction.py', /reponses_par_invite: int = (\d+)/),
      temperature: nombreLu(construction, 'construction.py', /temperature: float = ([\d.]+)/),
      topK: nombreLu(construction, 'construction.py', /top_k: int = (\d+)/),
      nNouveaux: nombreLu(construction, 'construction.py', /n_nouveaux: int = (\d+)/),
      longueur: nombreLu(construction, 'construction.py', /^ {4}longueur: int = (\d+)/m),
      partValidation: nombreLu(construction, 'construction.py', /part_validation: float = ([\d.]+)/),
    },
    invites: nombreLu(construction, 'construction.py', /RecettePreferences\("preferences-1\.8", ([\d_]+)\)/),
    invitesCourt: nombreLu(construction, 'construction.py', /RecettePreferences\("preferences-1\.8-court", ([\d_]+)\)/),
    seuilDuTauxDePaires: nombreLu(construction, 'construction.py', /^SEUIL_DU_TAUX_DE_PAIRES = ([\d.]+)/m),
    partDesProblemes: nombreLu(invites, 'invites.py', /^PART_DES_PROBLEMES = ([\d.]+)$/m),
    consignesMin: nombreLu(invites, 'invites.py', /voulues = hasard\.entier\((\d+), \d+\)/),
    consignesMax: nombreLu(invites, 'invites.py', /voulues = hasard\.entier\(\d+, (\d+)\)/),
    dpo: {
      beta: nombreLu(reglagesDpo, 'boucle.py', /^ {4}beta: float = ([\d.]+)$/m),
      normaliserLongueur: lire(reglagesDpo, 'boucle.py', /^ {4}normaliser_longueur: bool = (True|False)$/m) === 'True',
      poidsSft: nombreLu(reglagesDpo, 'boucle.py', /^ {4}poids_sft: float = ([\d.]+)$/m),
    },
    referenceCalculeeUneFois: readme.includes('est calculée une seule fois et rangée dans le jeu'),
    balayageDepartageParLaVictoire: readme.includes('celles qui départagent les essais d\'un balayage'),
    victoirePasUnJuge: readme.includes('un taux élevé est attendu après la DPO, ce n\'est pas un juge'),
    egaliteUneDemie: readme.includes('une égalité comptant une demie'),
    questionSansJustesse: noter.includes('juste=1 if invite.attendu is None else'),
    questionsNonApprises: readme.includes('Les invites sont des questions de Luth-2 que le SFT n\'a pas apprises'),
    invitesParPaquet: nombreLu(construction, 'construction.py', /^INVITES_PAR_PAQUET = (\d+)$/m),
    longueursDesPaires: readme.includes('la longueur moyenne (en jetons) des réponses choisies et rejetées'),
    memeNoteCourteOuLongue: enUneLigne(noter).includes('l\'une courte, l\'autre longue, ont la même note (aucune paire)'),
  };
}

/** Ce que le chapitre dit du projet 1.8, relu dans son README, son test de la perte et son relevé du balayage. */
export function faitsDuProjet18(racineDepot: string | URL = '..'): {
  noterEgaleForge: boolean;
  perteA1e12: boolean;
  pousserSansPaire: boolean;
  pointsDuTestDpo: number;
  reglagesDuBalayage: boolean;
} {
  const readme = enUneLigne(lireTexte(racineDepot, 'projets/1.8-alignement/README.md'));
  const test = lireTexte(racineDepot, 'projets/1.8-alignement/tests/test_perte_dpo.py');
  const resumer = lireTexte(racineDepot, 'projets/1.8-alignement/alignement_pas_a_pas/resumer.py');
  const points = /^ {4}assert ecarts == (\d+)$/m.exec(test);
  if (points === null) throw new Error('projets/1.8-alignement/tests/test_perte_dpo.py : « assert ecarts == … » ne se lit plus. Revois faitsDuProjet18.');
  return {
    pointsDuTestDpo: Number(points[1]),
    // « Le taux d'apprentissage, β, la normalisation par la longueur, le poids du terme SFT » : ce que relève `balayage`.
    reglagesDuBalayage: ['"taux_max": valeurs["taux_max"]', '"beta": dpo.beta', '"normaliser_longueur": dpo.normaliser_longueur', '"poids_sft": dpo.poids_sft'].every(
      (k) => resumer.includes(k),
    ),
    noterEgaleForge: readme.includes('la `note` rendue est celle de `forge.preferences.noter` (un test, sur cinquante réponses)'),
    perteA1e12: readme.includes('égale à `perte_dpo` de forge à 10⁻¹² près'),
    pousserSansPaire: readme.includes(
      'La paire est la première de `mesures/paires-exemples.json` quand ce fichier existe, sinon une paire fabriquée, et la commande le dit.',
    ),
  };
}

/**
 * Le nombre de lignes d'un extrait que montre CodeExplique : une région, ou un symbole sans sa docstring. Le chapitre
 * le garde par exiger, pour que ses explications par plages de lignes ne glissent pas sans bruit si le code change.
 */
export function lignesDuCode(fichier: string, sorte: 'region' | 'symbole', nom: string, racineDepot: string | URL = '..'): number {
  const source = readFileSync(join(enChemin(racineDepot), fichier), 'utf8');
  const code = sorte === 'region' ? extraireRegion(source, nom, fichier) : extraireSymbole(source, nom, fichier, { docstring: false });
  return code.split('\n').length;
}

// ---------- Étape 4 : le pari « paires » ----------

/** Les choix du pari « paires ». */
export const TEXTES_PAIRES = Object.freeze(['Choisit celle qui respecte la consigne', 'N’en fait pas de paire', 'Les garde toutes les deux'] as const);

/** Le pari « paires » : deux réponses coupées, l'une respecte la consigne. Le juste vient du plancher de forge. */
export function choixPaires(racineDepot: string | URL = '..'): Choix[] {
  const f = faitsDeForge18(racineDepot);
  // Sans plancher, la meilleure des deux (celle qui respecte la consigne) serait choisie.
  const juste = f.plancherFinieEtJuste ? 1 : 0;
  return TEXTES_PAIRES.map((texte, i) => ({ texte, juste: i === juste }));
}

// ---------- Étape 6 : le pari « vraisemblance » ----------

/** L'écart (en nats par jeton) en deçà duquel la log-probabilité de la choisie « ne bouge pas ». */
export const TOLERANCE_VRAISEMBLANCE = 0.01;

export type Sens = 'monte' | 'baisse' | 'stable';

/** Les choix du pari « vraisemblance », dans l'ordre des sens. */
export const TEXTES_VRAISEMBLANCE: Readonly<Record<Sens, string>> = Object.freeze({
  monte: 'Monte',
  baisse: 'Baisse',
  stable: `Ne bouge pas, à ${nombre(TOLERANCE_VRAISEMBLANCE, 2)} près`,
});

function sens(ecart: number): Sens {
  return Math.abs(ecart) <= TOLERANCE_VRAISEMBLANCE ? 'stable' : ecart > 0 ? 'monte' : 'baisse';
}

/** Les deux courbes de la DPO, au premier et au dernier point du relevé (des moyennes par paquets de pas). Null sans le relevé. */
export function faitsDeLaVraisemblance(
  racineDepot: string | URL = '..',
): { debut: number; fin: number; rejeteeDebut: number; rejeteeFin: number; pasFin: number } | null {
  const fichier = FICHIERS_1_8.courbes;
  const s = lireSeries(fichier, racineDepot);
  if (s === null) return null;
  const c = s.logps_choisie;
  const r = s.logps_rejetee;
  if (c === undefined || r === undefined || c.length === 0 || r.length === 0) {
    throw new Error(`${fichier}${FINE}: il faut les courbes logps_choisie et logps_rejetee, non vides. ${refaire(fichier)}`);
  }
  return { debut: c[0][1], fin: c[c.length - 1][1], rejeteeDebut: r[0][1], rejeteeFin: r[r.length - 1][1], pasFin: c[c.length - 1][0] };
}

/** Le sens de la log-probabilité de la choisie pendant la DPO. Null sans le relevé. */
export function sensDeLaChoisie(racineDepot: string | URL = '..'): Sens | null {
  const f = faitsDeLaVraisemblance(racineDepot);
  return f === null ? null : sens(f.fin - f.debut);
}

/** Le pari « vraisemblance » : « Pendant la DPO, la probabilité que ton IA donne à la réponse choisie… ». Null sans le relevé. */
export function choixVraisemblance(racineDepot: string | URL = '..'): Choix[] | null {
  const s = sensDeLaChoisie(racineDepot);
  if (s === null) return null;
  return (Object.keys(TEXTES_VRAISEMBLANCE) as Sens[]).map((k) => ({ texte: TEXTES_VRAISEMBLANCE[k], juste: k === s }));
}

/**
 * La phrase de l'étape 6, qui suit les courbes : la choisie monte, baisse ou ne bouge pas, et la rejetée ; puis ce
 * que cela veut dire. « Le piège » n'est dit que si la choisie baisse pendant que l'écart entre les deux grandit.
 */
export function phraseDeLaVraisemblance(racineDepot: string | URL = '..'): string | null {
  const f = faitsDeLaVraisemblance(racineDepot);
  if (f === null) return null;
  const sc = sens(f.fin - f.debut);
  const sr = sens(f.rejeteeFin - f.rejeteeDebut);
  const verbe = (s: Sens) => (s === 'stable' ? `ne bouge pas, à ${nombre(TOLERANCE_VRAISEMBLANCE, 2)} près` : s);
  const de = (a: number, b: number) => `de ${nombre(a, 2)} à ${nombre(b, 2)}`;
  const debut =
    `La choisie ${verbe(sc)}${FINE}: sa log-probabilité moyenne par jeton passe ${de(f.debut, f.fin)}. ` +
    `La rejetée ${verbe(sr)}, ${de(f.rejeteeDebut, f.rejeteeFin)}.`;
  const ecartGrandit = f.fin - f.rejeteeFin > f.debut - f.rejeteeDebut + TOLERANCE_VRAISEMBLANCE;
  if (sc === 'baisse') {
    return ecartGrandit
      ? `${debut} C’est le piège${FINE}: l’écart entre les deux grandit, mais la réponse choisie devient moins probable qu’au départ.`
      : `${debut} La choisie baisse, et l’écart entre les deux ne grandit pas${FINE}: la DPO n’a pas séparé les réponses.`;
  }
  if (sc === 'monte') {
    return `${debut} Ici, la DPO rend les réponses choisies plus probables${sr === 'baisse' ? ', et les rejetées moins' : ''}.`;
  }
  return `${debut} La DPO n’a pas bougé la choisie${sr === 'baisse' ? `${FINE}: ce qu’elle a changé, c’est la rejetée` : ''}.`;
}

/** La garde d'une phrase qui annonce le sens de la choisie : elle arrête la construction si les courbes disent autre chose. */
export function exigerSensDeLaChoisie(annonce: Sens, racineDepot: string | URL = '..'): void {
  const s = sensDeLaChoisie(racineDepot);
  exiger(s === annonce, `le texte dit que la choisie « ${annonce} », les courbes disent « ${s ?? 'à mesurer'} »`);
}

/** Les deux courbes, dessinées à la main : leurs chemins SVG, leur échelle, et un tableau des mêmes valeurs. */
export interface DessinDesCourbes {
  choisie: string;
  rejetee: string;
  xMax: number;
  yMin: number;
  yMax: number;
  lignes: { pas: number; choisie: number | null; rejetee: number | null }[];
}

/**
 * Le dessin des courbes logps_choisie et logps_rejetee, dans un cadre largeur × hauteur : les pas de 0 au dernier,
 * les log-probabilités entre la plus basse et la plus haute des deux, avec un dixième d'air de chaque côté.
 */
export function dessinDesCourbes(series: Record<string, [number, number][]>, largeur: number, hauteur: number): DessinDesCourbes {
  const c = series.logps_choisie ?? [];
  const r = series.logps_rejetee ?? [];
  if (c.length === 0 || r.length === 0) throw new Error('dessinDesCourbes : il faut les deux courbes, logps_choisie et logps_rejetee.');
  const toutes = [...c, ...r];
  const xMax = Math.max(...toutes.map(([pas]) => pas));
  const bas = Math.min(...toutes.map(([, v]) => v));
  const haut = Math.max(...toutes.map(([, v]) => v));
  const air = haut > bas ? (haut - bas) / 10 : 0.1;
  const yMin = bas - air;
  const yMax = haut + air;
  const chemin = (points: [number, number][]) =>
    points
      .map(([pas, v], i) => `${i === 0 ? 'M' : 'L'}${((pas / xMax) * largeur).toFixed(2)},${(((yMax - v) / (yMax - yMin)) * hauteur).toFixed(2)}`)
      .join('');
  const pas = [...new Set(toutes.map(([p]) => p))].sort((a, b) => a - b);
  const valeur = (points: [number, number][], p: number) => points.find(([x]) => x === p)?.[1] ?? null;
  return {
    choisie: chemin(c),
    rejetee: chemin(r),
    xMax,
    yMin,
    yMax,
    lignes: pas.map((p) => ({ pas: p, choisie: valeur(c, p), rejetee: valeur(r, p) })),
  };
}

// ---------- Étape 8 : les paris « longueur » et « victoire » ----------

/** Les nombres d'une mesure d'un rapport, ou null si le rapport manque ou si la mesure est absente. */
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

/** L'écart relatif de longueur en deçà duquel les réponses sont « de même longueur ». */
export const TOLERANCE_LONGUEUR = 0.05;

export type SensDeLaLongueur = 'plus longues' | 'plus courtes' | 'de même longueur';

/** Les choix du pari « longueur ». */
export const TEXTES_LONGUEUR: Readonly<Record<SensDeLaLongueur, string>> = Object.freeze({
  'plus longues': 'Plus longues',
  'plus courtes': 'Plus courtes',
  'de même longueur': `De même longueur, à ${pourcent(TOLERANCE_LONGUEUR)} près`,
});

/** Les mots moyens des réponses de ton IA 1.8 et de ton IA 1.7, sur les invites de la victoire. Null sans le rapport. */
export function faitsDeLaLongueur(racineDepot: string | URL = '..'): { modele: number; reference: number } | null {
  const v = mesure(lireRapportEtape('1.8@1.8', racineDepot), 'victoire');
  return v === null ? null : { modele: nombreDe(v, 'mots_modele'), reference: nombreDe(v, 'mots_reference') };
}

/** Après la DPO, les réponses sont plus longues, plus courtes, ou de même longueur (à 5 % près). Null sans le rapport. */
export function sensDeLaLongueur(racineDepot: string | URL = '..'): SensDeLaLongueur | null {
  const f = faitsDeLaLongueur(racineDepot);
  if (f === null) return null;
  exiger(f.reference > 0, 'les réponses de ton IA 1.7 n’ont plus aucun mot en moyenne');
  const relatif = f.modele / f.reference - 1;
  return Math.abs(relatif) <= TOLERANCE_LONGUEUR ? 'de même longueur' : relatif > 0 ? 'plus longues' : 'plus courtes';
}

/** Le pari « longueur » : « Après la DPO, ses réponses sont… ». Null sans le rapport. */
export function choixLongueur(racineDepot: string | URL = '..'): Choix[] | null {
  const s = sensDeLaLongueur(racineDepot);
  if (s === null) return null;
  return (Object.keys(TEXTES_LONGUEUR) as SensDeLaLongueur[]).map((k) => ({ texte: TEXTES_LONGUEUR[k], juste: k === s }));
}

/**
 * La phrase de la longueur, qui suit les rapports : plus longues, plus courtes ou de même longueur ; et, si elles
 * s'allongent, si elles respectent plus souvent toutes les consignes d'IFEval-FR. Les consignes d'IFEval-FR et celles
 * des paires sont vérifiées par le même module de forge (forge/evaluation/consignes.py) : seules les invites
 * diffèrent, et la phrase n'en dit pas plus. Sans la mesure d'IFEval-FR de ton IA 1.7 ou de ton IA 1.8, elle s'arrête
 * à la longueur. Null sans la mesure victoire de ton IA 1.8.
 */
export function phraseDeLaLongueur(racineDepot: string | URL = '..'): string | null {
  const s = sensDeLaLongueur(racineDepot);
  const f = faitsDeLaLongueur(racineDepot);
  if (s === null || f === null) return null;
  const debut = `Ses réponses sont ${s}${FINE}: ${nombre(f.modele, 1)} mots en moyenne, contre ${nombre(f.reference, 1)} pour ton IA 1.7, aux mêmes invites.`;
  const i17 = mesure(lireRapportEtape('1.7@1.8', racineDepot), 'ifeval_fr');
  const i18 = mesure(lireRapportEtape('1.8@1.8', racineDepot), 'ifeval_fr');
  if (s !== 'plus longues' || i17 === null || i18 === null) return debut;
  const avant = nombreDe(i17, 'invite_stricte');
  const apres = nombreDe(i18, 'invite_stricte');
  const ifeval = `${pourcent(apres, 1)} des invites d’IFEval-FR respectées en entier, contre ${pourcent(avant, 1)}`;
  return apres > avant + 0.01
    ? `${debut} Et elles respectent plus souvent toutes les consignes d’IFEval-FR${FINE}: ${ifeval}.`
    : `${debut} Elles s’allongent sans respecter plus souvent les consignes d’IFEval-FR${FINE}: ${ifeval}.`;
}

/** Une tranche d'un pari : son texte, et la valeur sous laquelle elle s'arrête (non comprise). */
export interface Tranche {
  texte: string;
  jusqua: number;
}

/** Les tranches du pari « victoire », en taux de victoire de ton IA 1.8 contre ton IA 1.7. */
export const TRANCHES_VICTOIRE: readonly Tranche[] = Object.freeze([
  Object.freeze({ texte: `Moins de 50${FINE}%`, jusqua: 0.5 }),
  Object.freeze({ texte: `De 50 à 75${FINE}%`, jusqua: 0.75 }),
  Object.freeze({ texte: `75${FINE}% ou plus`, jusqua: Infinity }),
]);

/** Le pari « victoire » : trois tranches du taux de victoire de ton IA 1.8 contre ton IA 1.7. Null sans le rapport. */
export function choixVictoire(racineDepot: string | URL = '..'): Choix[] | null {
  const v = mesure(lireRapportEtape('1.8@1.8', racineDepot), 'victoire');
  if (v === null) return null;
  const taux = nombreDe(v, 'taux');
  const rang = TRANCHES_VICTOIRE.findIndex((t) => taux < t.jusqua);
  exiger(rang >= 0, `${String(taux)} ne tombe dans aucune tranche`);
  return TRANCHES_VICTOIRE.map((t, i) => ({ texte: t.texte, juste: i === rang }));
}

// ---------- Étape 7 : le balayage ----------

/** Les réglages que le balayage fait varier, comme `balayage` du projet les relève. */
export interface ReglagesDuBalayage {
  taux_max: number;
  beta: number;
  normaliser_longueur: boolean;
  poids_sft: number;
}

/** Un essai du balayage (mesures/balayage-1.8.json). */
export interface EssaiDuBalayage {
  essai: string;
  reglages: ReglagesDuBalayage;
  victoire: { taux: number; victoires: number; egalites: number; defaites: number; n: number } | { absente: string };
  longueur: { mots_modele: number; mots_reference: number } | { absente: string };
  logps_choisie: { debut: number; fin: number };
}

function essaiValide(e: unknown): boolean {
  const absente = (x: unknown) => objet(x) && texte(x.absente);
  return (
    objet(e) &&
    texte(e.essai) &&
    objet(e.reglages) &&
    fini(e.reglages.taux_max) &&
    fini(e.reglages.beta) &&
    typeof e.reglages.normaliser_longueur === 'boolean' &&
    fini(e.reglages.poids_sft) &&
    (absente(e.victoire) || (objet(e.victoire) && ['taux', 'victoires', 'egalites', 'defaites', 'n'].every((k) => fini((e.victoire as Record<string, unknown>)[k])))) &&
    (absente(e.longueur) || (objet(e.longueur) && fini(e.longueur.mots_modele) && fini(e.longueur.mots_reference))) &&
    objet(e.logps_choisie) &&
    fini(e.logps_choisie.debut) &&
    fini(e.logps_choisie.fin)
  );
}

/** Les essais du balayage, ou null tant qu'ils ne sont pas relevés. */
export function lireBalayage(racineDepot: string | URL = '..'): EssaiDuBalayage[] | null {
  const fichier = FICHIERS_1_8.balayage;
  const b = lireJsonSiPresent(racineDepot, fichier, refaire(fichier));
  if (b === null) return null;
  if (!Array.isArray(b) || b.length === 0 || !b.every(essaiValide)) {
    throw new Error(`${fichier}${FINE}: il faut une liste d’essais, chacun avec essai, reglages, victoire, longueur et logps_choisie. ${refaire(fichier)}`);
  }
  return b as EssaiDuBalayage[];
}

/**
 * Les réglages de configs/dpo-1.8.toml (taux_max, et la table [dpo], avec les valeurs par défaut de forge pour ce
 * qu'elle ne dit pas), ou null tant que la configuration n'existe pas.
 */
export function lireReglagesDpo18(racineDepot: string | URL = '..'): ReglagesDuBalayage | null {
  const chemin = join(enChemin(racineDepot), CONFIG_DPO_18);
  if (!existsSync(chemin)) return null;
  const lignes = readFileSync(chemin, 'utf8').replace(/\r\n?/g, '\n').split('\n');
  let table = '';
  const valeurs: Record<string, string> = {};
  for (const brute of lignes) {
    const ligne = brute.replace(/\s+#.*$/, '').trim();
    const entete = /^\[([\w.]+)\]$/.exec(ligne);
    if (entete !== null) {
      table = entete[1];
      continue;
    }
    const cle = /^(\w+)\s*=\s*(\S+)$/.exec(ligne);
    if (cle !== null) valeurs[table === '' ? cle[1] : `${table}.${cle[1]}`] = cle[2];
  }
  const nombreDe_ = (cle: string, defaut?: number): number => {
    const v = valeurs[cle];
    if (v === undefined && defaut !== undefined) return defaut;
    const x = Number(v?.replaceAll('_', ''));
    if (!Number.isFinite(x)) throw new Error(`${CONFIG_DPO_18}${FINE}: le réglage ${cle} manque ou ne se lit pas. Corrige la configuration.`);
    return x;
  };
  const normaliser = valeurs['dpo.normaliser_longueur'];
  if (normaliser !== undefined && normaliser !== 'true' && normaliser !== 'false') {
    throw new Error(`${CONFIG_DPO_18}${FINE}: normaliser_longueur vaut ${normaliser}, il faut true ou false.`);
  }
  return {
    taux_max: nombreDe_('taux_max'),
    beta: nombreDe_('dpo.beta', DEFAUTS_DPO.beta),
    normaliser_longueur: normaliser === undefined ? DEFAUTS_DPO.normaliser_longueur : normaliser === 'true',
    poids_sft: nombreDe_('dpo.poids_sft', DEFAUTS_DPO.poids_sft),
  };
}

/**
 * Les essais du tableau du balayage, et le rang de l'essai retenu : celui qui a les réglages de configs/dpo-1.8.toml.
 * Sans la configuration, aucun n'est marqué ; une configuration qu'aucun essai n'a arrête la construction. Null sans
 * le relevé.
 */
export function essaisDuBalayage(racineDepot: string | URL = '..'): { essais: EssaiDuBalayage[]; retenu: number | null } | null {
  const essais = lireBalayage(racineDepot);
  if (essais === null) return null;
  const config = lireReglagesDpo18(racineDepot);
  if (config === null) return { essais, retenu: null };
  const memes = essais
    .map((e, i) => ({ e, i }))
    .filter(({ e }) => (Object.keys(config) as (keyof ReglagesDuBalayage)[]).every((k) => e.reglages[k] === config[k]));
  exiger(memes.length === 1, `${memes.length} essais du balayage ont les réglages de configs/dpo-1.8.toml, il en faut un seul`);
  return { essais, retenu: memes[0].i };
}
