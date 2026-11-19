// Ce que l'atelier des notes et la phrase de la DPO du chapitre 1.8 calculent dans le navigateur : la note d'une
// réponse, critère par critère, avec la raison de chacun (comme expliquer_note du projet 1.8,
// projets/1.8-alignement/alignement_pas_a_pas/noter.py), l'ordre de deux notes, le défi, et la phrase de la perte DPO.
//
// Tout passe par les jumeaux : notes.ts (les contrôles de forge, vérifiés contre les attendus du Python) et dpo.ts (la
// perte et sa dérivée). Ici, rien n'est recalculé autrement : on range leurs résultats dans des phrases.
//
// L'atelier note une réponse à une question (une invite sans réponse attendue) : le critère « juste », qui lit le
// dernier nombre d'un problème avec des fractions exactes, est alors acquis, comme dans forge. Le chapitre ne lui
// donne jamais un problème.
//
// Ce module n'importe ni node:fs, ni .json, ni astro:* : les îlots (AtelierNote.svelte, PhraseDpo.svelte) et les
// parcours Playwright l'importent.

import { nombre, pourcent } from '../nombres';
import { deriveeDpo, perteDpo, sigmoide } from './dpo';
import {
  langue,
  MOTS_MAXIMUM,
  MOTS_MINIMUM,
  mots,
  noteSansJustesse,
  VERIFICATEURS_CONTRAINTES,
  type ConsigneDInvite,
  type ReglagesConsigne,
} from './notes';

const FINE = '\u202F';

// ---------- Les consignes, telles que forge les écrit ----------

/**
 * La phrase de chacune des huit consignes de forge (`Contrainte.consigne` de forge/evaluation/consignes.py), pour
 * ses réglages. atelier-1-8.test.ts les compare aux phrases que le Python a écrites dans les attendus du projet 1.8.
 */
const PHRASES_DES_CONSIGNES: Readonly<Record<string, (k: ReglagesConsigne) => string>> = Object.freeze({
  mots_max: (k) => `Réponds en ${String(k.n)} mots au plus.`,
  phrases_max: (k) => `Réponds en ${String(k.n)} phrases au plus.`,
  minuscules: () => 'Écris toute ta réponse en minuscules.',
  sans_virgule: () => "N'utilise aucune virgule.",
  mot_obligatoire: (k) => `Emploie le mot « ${String(k.mot)} » dans ta réponse.`,
  puces: (k) => `Réponds par exactement ${String(k.n)} puces, chacune commençant par « - ».`,
  fin_imposee: (k) => `Termine ta réponse par la phrase exacte : « ${String(k.phrase)} »`,
  titre: () => "Donne d'abord un titre entre doubles chevrons, comme « titre ».",
});

/** La phrase d'une consigne, telle que forge l'ajoute à une invite. Une consigne inconnue est une erreur. */
export function phraseDeConsigne(id: string, reglages: ReglagesConsigne): string {
  const phrase = Object.hasOwn(PHRASES_DES_CONSIGNES, id) ? PHRASES_DES_CONSIGNES[id] : undefined;
  if (phrase === undefined) {
    throw new Error(`La consigne « ${id} » est inconnue : les consignes sont ${Object.keys(PHRASES_DES_CONSIGNES).join(', ')}.`);
  }
  return phrase(reglages);
}

/** Entre la question et ses consignes : une ligne vide (SEPARATEUR_DES_CONSIGNES de forge/preferences/invites.py). */
export const SEPARATEUR_DES_CONSIGNES = '\n\n';

/** Une invite comme forge l'écrit (avec_consignes) : la question, une ligne vide, puis les consignes, séparées d'une espace. */
export function avecConsignes(question: string, consignes: readonly ConsigneDInvite[]): string {
  if (consignes.length === 0) return question;
  return `${question}${SEPARATEUR_DES_CONSIGNES}${consignes.map(([id, k]) => phraseDeConsigne(id, k)).join(' ')}`;
}

// ---------- La note d'une réponse ----------

/** Les cinq critères de forge (Note de forge/preferences/noter.py), du plus important au moins important. */
export const CRITERES = Object.freeze(['terminee', 'juste', 'consignes', 'francais', 'longueur'] as const);
export type Critere = (typeof CRITERES)[number];
export type Note = Record<Critere, number>;

/** Le nom de chaque critère, pour la page. */
export const LIBELLES_DES_CRITERES: Readonly<Record<Critere, string>> = Object.freeze({
  terminee: 'Finie',
  juste: 'Juste',
  consignes: 'Consignes',
  francais: 'En français',
  longueur: 'Longueur',
});

/** Un critère, avec sa valeur, son maximum, son verdict (la valeur est-elle le maximum ?) et sa raison. */
export interface CritereExplique {
  nom: Critere;
  valeur: number;
  maximum: number;
  verdict: boolean;
  raison: string;
}

/** Une consigne de l'invite, sa phrase, et si la réponse la respecte. */
export interface ConsigneJugee {
  id: string;
  consigne: string;
  respectee: boolean;
}

/** La note d'une réponse, et pourquoi : ce que rend expliquer_note du projet 1.8, pour une question. */
export interface NoteExpliquee {
  note: Note;
  criteres: CritereExplique[];
  consignes: ConsigneJugee[];
  mots: number;
  langue: 'fr' | 'autre' | 'indetermine';
}

/** « 0 consigne », « 1 consigne », « 2 consignes » : le pluriel dès 2, comme _pluriel du projet. */
function pluriel(n: number, mot: string): string {
  return `${nombre(n)} ${mot}${n >= 2 ? 's' : ''}`;
}

function critere(nom: Critere, valeur: number, maximum: number, raison: string): CritereExplique {
  return { nom, valeur, maximum, verdict: valeur === maximum, raison };
}

/**
 * La note d'une réponse à une question, critère par critère, avec la raison de chacun : terminée (la bascule de
 * l'atelier), juste (acquis pour une question), le nombre de consignes respectées, le français, la longueur en mots.
 * Les valeurs sont celles du jumeau, noteSansJustesse (notes.ts) ; le détail des consignes, la langue et le nombre de
 * mots viennent des mêmes contrôles, pour les raisons, qui reprennent celles d'expliquer_note.
 */
export function expliquerNote(texte: string, terminee: boolean, consignes: readonly ConsigneDInvite[]): NoteExpliquee {
  const valeurs = noteSansJustesse(texte, terminee, consignes);
  const fin = critere('terminee', valeurs.terminee, 1, terminee ? 'elle a fini son tour' : 'elle est coupée par la limite de jetons');
  const juste = critere('juste', 1, 1, `une question n’a pas de réponse à vérifier${FINE}: le critère est acquis`);

  const jugees: ConsigneJugee[] = consignes.map(([id, reglages]) => {
    const verifier = Object.hasOwn(VERIFICATEURS_CONTRAINTES, id) ? VERIFICATEURS_CONTRAINTES[id] : undefined;
    if (verifier === undefined) throw new Error(`La consigne « ${id} » est inconnue : les consignes sont ${Object.keys(VERIFICATEURS_CONTRAINTES).join(', ')}.`);
    return { id, consigne: phraseDeConsigne(id, reglages), respectee: verifier(texte, reglages) };
  });
  const respectees = valeurs.consignes;
  if (jugees.filter((c) => c.respectee).length !== respectees) throw new Error('expliquerNote : le détail des consignes ne redonne plus la note du jumeau.');
  const consigne = critere('consignes', respectees, jugees.length, `${pluriel(respectees, 'consigne')} sur ${nombre(jugees.length)}`);

  const laLangue = langue(texte);
  const francais = critere(
    'francais',
    valeurs.francais,
    1,
    {
      fr: 'en français',
      autre: 'dans une autre langue que le français',
      indetermine: `moins de 3 mots outils${FINE}: la langue ne se juge pas, et le critère passe`,
    }[laLangue],
  );

  const n = mots(texte).length;
  const raisonLongueur =
    n < MOTS_MINIMUM
      ? `${pluriel(n, 'mot')}, moins de ${nombre(MOTS_MINIMUM)}`
      : n > MOTS_MAXIMUM
        ? `${pluriel(n, 'mot')}, plus de ${nombre(MOTS_MAXIMUM)}`
        : pluriel(n, 'mot');
  const longueur = critere('longueur', valeurs.longueur, 1, raisonLongueur);

  const criteres = [fin, juste, consigne, francais, longueur];
  const note = Object.fromEntries(criteres.map((c) => [c.nom, c.valeur])) as Note;
  return { note, criteres, consignes: jugees, mots: n, langue: laLangue };
}

/** Comparer deux notes comme forge (l'ordre d'un NamedTuple) : le premier critère qui diffère décide. > 0 si `a` gagne. */
export function comparerNotes(a: Note, b: Note): number {
  for (const c of CRITERES) if (a[c] !== b[c]) return a[c] - b[c];
  return 0;
}

/** Le premier critère qui départage deux notes (raison_de_la_paire de forge), ou null si elles sont égales. */
export function critereQuiDepartage(a: Note, b: Note): Critere | null {
  return CRITERES.find((c) => a[c] !== b[c]) ?? null;
}

/** La note la plus haute à une question qui a `consignes` consignes : tout au maximum. */
export function noteMaximale(consignes: number): Note {
  return { terminee: 1, juste: 1, consignes, francais: 1, longueur: 1 };
}

/** Une note écrite comme forge la range : « (1, 1, 2, 1, 1) », ses cinq critères dans l'ordre. */
export function noteEnTexte(note: Note): string {
  return `(${CRITERES.map((c) => nombre(note[c])).join(', ')})`;
}

/** Vrai si chaque critère est à son maximum. */
export function estLaPlusHaute(e: NoteExpliquee): boolean {
  return e.criteres.every((c) => c.verdict);
}

// ---------- Le défi : écrire sa propre réponse qui obtient la note la plus haute ----------

/** Un texte sans ses blancs de bord ni ses blancs répétés : une copie reste une copie, à une espace près. */
function sansBlancs(texte: string): string {
  return texte.replace(/\s+/g, ' ').trim();
}

/** La réponse de la paire que le texte recopie, ou null : le défi demande une réponse à soi. */
export function copieDe(texte: string, reponses: readonly { lettre: string; texte: string }[]): string | null {
  return reponses.find((r) => sansBlancs(r.texte) === sansBlancs(texte))?.lettre ?? null;
}

/** Le défi est réussi quand la note est la plus haute possible, et que la réponse n'est pas une de celles de la paire. */
export function defiReussi(e: NoteExpliquee, texte: string, reponses: readonly { lettre: string; texte: string }[]): boolean {
  return estLaPlusHaute(e) && copieDe(texte, reponses) === null;
}

/** Ce que dit le défi : réussi, recopié, ou ce qui manque, par les raisons des critères qui ne sont pas au maximum. */
export function texteDuDefi(e: NoteExpliquee, texte: string, reponses: readonly { lettre: string; texte: string }[]): string {
  const copie = copieDe(texte, reponses);
  if (copie !== null) return `Pas encore${FINE}: c’est la réponse ${copie} de la paire. Écris la tienne.`;
  if (defiReussi(e, texte, reponses)) return `Défi réussi${FINE}: ta réponse a la note la plus haute, ${noteEnTexte(e.note)}.`;
  const manque = e.criteres.filter((c) => !c.verdict).map((c) => c.raison);
  return `Pas encore${FINE}: ${manque.join(`${FINE}; `)}.`;
}

// ---------- La phrase de la perte DPO ----------

/** β se règle par un indice, de 1 à 10 : β = indice ÷ 20, de 0,05 à 0,5 (sans la poussière de 3 × 0,05). */
export const INDICE_BETA_MIN = 1;
export const INDICE_BETA_MAX = 10;
/** L'indice de départ : β = 0,1, la valeur par défaut de forge (ReglagesDPO). */
export const INDICE_BETA_DEPART = 2;
/** Les écarts de la choisie et de la rejetée face à la référence, en nats : de −3 à +3, par pas de 0,5. */
export const ECART_MIN = -3;
export const ECART_MAX = 3;
export const PAS_D_ECART = 0.5;
/** Les écarts de départ : la choisie gagne 1 nat sur la référence, la rejetée en perd 1. */
export const ECART_CHOISIE_DEPART = 1;
export const ECART_REJETEE_DEPART = -1;

export function betaDeLIndice(indice: number): number {
  return indice / 20;
}

/** Un écart écrit avec son signe : « +1,0 », « −1,5 », « 0,0 ». */
export function ecartEnTexte(x: number): string {
  if (x === 0) return nombre(0, 1);
  return x > 0 ? `+${nombre(x, 1)}` : `−${nombre(-x, 1)}`;
}

/**
 * La perte d'une paire et le sens de son gradient, en mots : `perte` (en nats, trois décimales), `force` (ce que la
 * perte perd quand la choisie gagne un peu, ou que la rejetée perd un peu, par nat : −dérivée), et `suite`, la
 * phrase qui le dit. La dérivée selon la choisie est −β σ(−z), toujours négative : monter la choisie fait baisser la
 * perte ; selon la rejetée, c'est l'opposée. La force est σ(−z) fois β : plus de la moitié de β quand la paire est à
 * l'envers (z < 0), moins quand elle est déjà dans le bon ordre.
 */
export function phraseDeLaPerteDpo(beta: number, ecartChoisie: number, ecartRejetee: number): { perte: string; force: string; suite: string } {
  const perte = perteDpo(beta, ecartChoisie, ecartRejetee);
  const derivee = deriveeDpo(beta, ecartChoisie, ecartRejetee);
  const z = beta * (ecartChoisie - ecartRejetee);
  const part = sigmoide(-z);
  const force = nombre(-derivee, 3);
  const sens = derivee < 0 ? 'pousse la choisie vers le haut et la rejetée vers le bas' : 'pousse la choisie vers le bas et la rejetée vers le haut';
  const ordre =
    z < 0
      ? `la paire est à l’envers, la rejetée devant${FINE}: la poussée dépasse la moitié de β`
      : z > 0
        ? `la paire est déjà dans le bon ordre${FINE}: la poussée faiblit à mesure que l’écart grandit`
        : 'les deux sont à égalité face à la référence';
  const suite = `Pour la faire baisser, la descente de gradient ${sens}, avec la même force${FINE}: ${force} par nat, soit ${pourcent(part)} de β. Ici, ${ordre}.`;
  return { perte: nombre(perte, 3), force, suite };
}
