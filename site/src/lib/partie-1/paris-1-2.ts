// Les paris du chapitre 1.2, « Les données », et les textes de son atelier du nettoyeur.
//
// Leurs bonnes réponses sont calculées par le jumeau du nettoyage de forge (nettoyeur.ts),
// sur les exemples du projet 1.2 et sur son aperçu des sources : rien n'est recopié. Si un
// exemple, l'aperçu ou le jumeau change et qu'une phrase de la page devient fausse, la
// construction s'arrête (« Exemple devenu faux : … »).
//
// Les fonctions reçoivent leurs données en argument (le texte, la ligne de code, les lignes,
// l'aperçu) : ce module n'importe ni ?raw, ni .json, ni astro:* (P8). Le chapitre leur passe
// les fichiers du projet (projet-1-2.ts), les parcours de test les mêmes fichiers lus sur le
// disque. L'atelier (AtelierNettoyeur.svelte) y prend ses phrases.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import type { NomSource } from './donnees';
import { PART_VALIDATION } from './donnees';
import {
  BLANCS_PYTHON,
  empreinte,
  estValidation,
  garderPythonPermissif,
  LONGUEUR_MINIMALE,
  longueurPointsDeCode,
  nettoyer,
  normaliser,
  trier,
  type Ligne,
  type Raison,
} from './nettoyeur';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-2.ts et le texte des paris du chapitre 1.2');

/** « 1 caractère », « 0 caractère », « 199 caractères » : le singulier pour 0 et 1, comme en français. */
function caracteres(n: number): string {
  return `${n} ${n > 1 ? 'caractères' : 'caractère'}`;
}

// ---------- Les fichiers du projet ----------

/** Les lignes d'un fichier .jsonl : un document par ligne non vide, comme lire_jsonl de trier.py. */
export function lireJsonl(texte: string): Ligne[] {
  return texte
    .split('\n')
    .filter((ligne) => ligne.trim() !== '')
    .map((ligne) => JSON.parse(ligne) as Ligne);
}

/** Le même texte, écrit sous Windows : chaque fin de ligne \n devient \r\n. */
export function versWindows(texte: string): string {
  return texte.replace(/\n/g, '\r\n');
}

/** Ce que l'aperçu (mesures/apercu.json) relève pour une source. */
export interface ApercuDeSource {
  lus: number;
  gardes: number;
  raisons: Record<Raison, number>;
  octets_gardes: number;
  en_validation: number;
  secondes: number;
}

/** L'aperçu des trois sources, tel que `python -m donnees_pas_a_pas apercu` l'écrit. */
export interface Apercu {
  releve_le: string;
  octets_par_source: number;
  sources: Record<NomSource, ApercuDeSource>;
}

// ---------- Étape 3 : le pari « licence » ----------

/**
 * Le pari « Un fichier Python sous GPL-3.0 entre-t-il dans les données de ton IA ? ». La
 * bonne réponse est celle du filtre de forge (garderPythonPermissif). Garde : la ligne est
 * bien du Python, sans quoi la question serait fausse.
 */
export function choixLicence(ligne: Ligne): Choix[] {
  exiger(ligne.language === 'Python', 'le fichier du pari « licence » n’est plus du Python');
  const garde = garderPythonPermissif(ligne);
  return [
    { texte: `Oui${FINE}: c’est du Python`, juste: garde },
    { texte: `Non${FINE}: sa licence n’est pas dans la liste`, juste: !garde },
    { texte: 'Oui, si on cite son auteur', juste: false },
  ];
}

// ---------- Étape 4 : le pari « court » ----------

/**
 * Les faits du pari « court » : la longueur du texte une fois nettoyé (en points de code,
 * comme len() en Python), et s'il est gardé. Garde : le nettoyage ne change rien au texte,
 * puisque le pari le dit « sans faute ».
 */
export function faitsDuPariCourt(texte: string): { longueur: number; garde: boolean } {
  exiger(normaliser(texte) === texte, 'le nettoyage change le texte du pari « court » : « sans faute » est à revoir');
  return { longueur: longueurPointsDeCode(texte), garde: nettoyer(texte) !== null };
}

/** Le pari « Ce texte de 150 caractères, sans faute, est-il gardé ? ». */
export function choixCourt(texte: string): Choix[] {
  const { garde } = faitsDuPariCourt(texte);
  return [
    { texte: `Oui${FINE}: il est propre`, juste: garde },
    { texte: `Non${FINE}: il est trop court`, juste: !garde },
    { texte: 'Oui, une fois sa typographie corrigée', juste: false },
  ];
}

// ---------- Étape 6 : le pari « doublon » ----------

/**
 * Les faits du pari « doublon » : les empreintes d'un texte et du même texte écrit sous
 * Windows. Gardes : le second est bien le premier avec des fins de ligne \r\n (et il en a
 * au moins une), et les deux passent le seuil de longueur (sinon ils seraient écartés avant
 * qu'on cherche les doublons).
 */
export async function faitsDuPariDoublon(
  unix: string,
  windows: string,
): Promise<{ meme: boolean; empreinte: string; empreinteWindows: string }> {
  exiger(unix.includes('\n') && windows === versWindows(unix), 'le texte « Windows » du pari « doublon » n’est plus le même texte, fini par \\r\\n');
  exiger(nettoyer(unix) !== null && nettoyer(windows) !== null, 'un texte du pari « doublon » est trop court');
  const [a, b] = await Promise.all([empreinte(unix), empreinte(windows)]);
  return { meme: a === b, empreinte: a, empreinteWindows: b };
}

/** Le pari « Le même texte, écrit sous Windows, compte-t-il comme un doublon ? ». */
export async function choixDoublon(unix: string, windows: string): Promise<Choix[]> {
  const { meme } = await faitsDuPariDoublon(unix, windows);
  return [
    { texte: `Oui${FINE}: une fois nettoyés, ils sont identiques`, juste: meme },
    { texte: `Non${FINE}: leurs octets diffèrent`, juste: !meme },
    { texte: `Non${FINE}: un texte de Windows est écarté`, juste: false },
  ];
}

// ---------- Étape 7 : le pari « validation » ----------

/** Le carnet de l'essai k : un texte de plus de 200 caractères, qui ne diffère que par son numéro. */
export function carnetDeLEssai(k: number): string {
  return (
    `Carnet du forgeron, essai numéro ${k}. La lame a été chauffée, frappée, trempée puis affûtée. ` +
    'Elle a tenu le choc sans se fendre, et le forgeron l’a rangée avec les autres, au fond de ' +
    'l’atelier, près de la fenêtre.'
  );
}

/** Le premier carnet que est_validation met de côté (environ un essai sur 200). */
export async function texteDeValidation(): Promise<{ texte: string; essai: number }> {
  for (let essai = 0; essai < 10_000; essai++) {
    const texte = carnetDeLEssai(essai);
    if (estValidation(await empreinte(texte))) return { texte, essai };
  }
  throw new Error('Aucun carnet de 0 à 9 999 ne va dans la validation : carnetDeLEssai est à revoir (paris-1-2.ts).');
}

/**
 * Les faits du pari « validation » : on trie les lignes et le carnet mis de côté, dans un
 * sens, puis dans l'autre, et on regarde où va le carnet chaque fois. Garde : il va bien
 * dans la validation au premier tri.
 */
export async function faitsDuPariValidation(
  lignes: readonly Ligne[],
): Promise<{ texte: string; essai: number; aller: boolean; retour: boolean; uneSur: number }> {
  const { texte, essai } = await texteDeValidation();
  const toutes = [...lignes, { text: texte }];
  const aller = (await trier(toutes, 'web_fr')).at(-1)!;
  const retour = (await trier([...toutes].reverse(), 'web_fr'))[0];
  exiger(aller.garde && aller.validation === true, 'le carnet du pari « validation » ne va plus dans la validation');
  exiger(retour.garde, 'le carnet du pari « validation » n’est plus gardé au second tri');
  return { texte, essai, aller: true, retour: retour.validation === true, uneSur: Math.round(1 / PART_VALIDATION) };
}

/** Le pari « Le même tri, dans l'autre sens : où va le texte mis de côté pour la validation ? ». */
export async function choixValidation(lignes: readonly Ligne[]): Promise<Choix[]> {
  const { retour, uneSur } = await faitsDuPariValidation(lignes);
  return [
    { texte: 'Encore dans la validation', juste: retour },
    { texte: `Au hasard${FINE}: une fois sur ${uneSur}`, juste: !retour },
    { texte: 'Dans l’entraînement, cette fois', juste: false },
  ];
}

// ---------- Étape 8 : le pari « part » ----------

/** Les trois tranches du pari « part ». */
export const TRANCHES_PART: readonly string[] = Object.freeze(['Moins de la moitié', 'La moitié ou plus, mais pas tous', 'Tous']);

/** La tranche d'une part : 0 sous la moitié, 1 de la moitié (comprise) à presque tous, 2 pour tous. */
export function trancheDeLaPartGardee(part: number): number {
  if (part >= 1) return 2;
  if (part >= 0.5) return 1;
  return 0;
}

/** Le pari « Quelle part des documents du web l'aperçu garde-t-il ? ». Garde : l'aperçu a lu des documents. */
export function choixPartGardee(apercu: Apercu): Choix[] {
  const { lus, gardes } = apercu.sources.web_fr;
  exiger(lus > 0, 'l’aperçu n’a lu aucun document du web : le pari « part » est à revoir');
  const juste = trancheDeLaPartGardee(gardes / lus);
  return TRANCHES_PART.map((texte, i) => ({ texte, juste: i === juste }));
}

// ---------- L'atelier ----------

/** Le signe d'un retour chariot retiré (\r), et celui d'un autre caractère invisible retiré. */
export const RETOUR_CHARIOT = '␍';
export const CONTROLE_RETIRE = '·';

/** Un morceau du texte nettoyé, tel que l'atelier le montre : du texte gardé, ou des retraits. */
export type Morceau = { texte: string; retire: false } | { texte: string; retire: true; nombre: number };

// Les caractères que le nettoyage retire : ceux de nettoyeur.ts (contrôles, \r seul, moitiés
// de paire). Lus point de code par point de code, une paire complète (un emoji) n'en est pas.
const CONTROLE = /^[\u{0}-\u{8}\u{b}-\u{1f}\u{7f}-\u{9f}\u{d800}-\u{dfff}]$/u;
const BLANCS: ReadonlySet<number> = new Set(BLANCS_PYTHON);

type Element = { garde: string } | { signe: string };

/** Ajoute un retrait, collé au précédent s'il est de la même sorte. */
function ajouterRetrait(morceaux: Morceau[], signe: string, nombre = 1): void {
  const dernier = morceaux.at(-1);
  if (dernier !== undefined && dernier.retire && dernier.texte.startsWith(signe)) {
    dernier.nombre += nombre;
    dernier.texte = signe.repeat(dernier.nombre);
  } else {
    morceaux.push({ texte: signe.repeat(nombre), retire: true, nombre });
  }
}

/** Ajoute du texte gardé, collé au précédent s'il en est. */
function ajouterGarde(morceaux: Morceau[], texte: string): void {
  if (texte === '') return;
  const dernier = morceaux.at(-1);
  if (dernier !== undefined && !dernier.retire) dernier.texte += texte;
  else morceaux.push({ texte, retire: false });
}

/**
 * Le texte nettoyé, en morceaux : le texte gardé, et chaque retrait à sa place (␍ pour un
 * retour chariot, · pour un autre contrôle, une moitié de paire ou un blanc de fin). Mis bout
 * à bout, les morceaux gardés font exactement normaliser(brut).
 *
 * Mêmes étapes que normaliser : \r\n, contrôles, forme NFC, blancs de fin. La forme NFC peut
 * réunir une lettre et son accent qu'un contrôle séparait : le texte des deux côtés du
 * retrait ne fait alors plus qu'un, et le retrait passe juste après lui.
 */
export function morceauxDuNettoyage(brut: string): Morceau[] {
  // 1. Les retraits des contrôles, à leur place.
  const elements: Element[] = [];
  let garde = '';
  const points = Array.from(brut);
  for (let i = 0; i < points.length; i++) {
    const c = points[i];
    if (c === '\r' || CONTROLE.test(c)) {
      if (garde !== '') elements.push({ garde });
      garde = '';
      elements.push({ signe: c === '\r' ? RETOUR_CHARIOT : CONTROLE_RETIRE });
    } else {
      garde += c;
    }
  }
  if (garde !== '') elements.push({ garde });

  // 2. La forme NFC, morceau par morceau, sauf quand elle réunit deux morceaux voisins.
  const morceaux: Morceau[] = [];
  let enCours = '';
  let entre: string[] = [];
  for (const e of elements) {
    if ('signe' in e) {
      if (enCours === '') ajouterRetrait(morceaux, e.signe);
      else entre.push(e.signe);
      continue;
    }
    if (enCours !== '' && (enCours + e.garde).normalize('NFC') !== enCours.normalize('NFC') + e.garde.normalize('NFC')) {
      enCours += e.garde;
      continue;
    }
    if (enCours !== '') {
      ajouterGarde(morceaux, enCours.normalize('NFC'));
      for (const s of entre) ajouterRetrait(morceaux, s);
    }
    enCours = e.garde;
    entre = [];
  }
  ajouterGarde(morceaux, enCours.normalize('NFC'));
  for (const s of entre) ajouterRetrait(morceaux, s);

  // 3. Les blancs de fin : retirés du texte gardé, en partant de la fin, à travers les retraits.
  const fin: Morceau[] = [];
  while (morceaux.length > 0) {
    const dernier = morceaux.at(-1)!;
    if (dernier.retire) {
      fin.unshift(morceaux.pop()!);
      continue;
    }
    let k = dernier.texte.length;
    while (k > 0 && BLANCS.has(dernier.texte.charCodeAt(k - 1))) k--;
    const blancs = longueurPointsDeCode(dernier.texte.slice(k));
    if (blancs > 0) fin.unshift({ texte: CONTROLE_RETIRE.repeat(blancs), retire: true, nombre: blancs });
    if (k > 0) {
      dernier.texte = dernier.texte.slice(0, k);
      break;
    }
    morceaux.pop();
  }
  for (const m of fin) {
    if (m.retire) ajouterRetrait(morceaux, m.texte[0], m.nombre);
  }

  // Un garde-fou : le texte gardé doit être celui du nettoyage, sinon on le montre d'un bloc.
  const gardes = morceaux
    .filter((m) => !m.retire)
    .map((m) => m.texte)
    .join('');
  const attendu = normaliser(brut);
  if (gardes !== attendu) {
    const retraits = morceaux.filter((m) => m.retire);
    return [...(attendu === '' ? [] : [{ texte: attendu, retire: false as const }]), ...retraits];
  }
  return morceaux;
}

/** Ce que l'atelier sait d'un texte avant son empreinte : sa longueur nettoyée, et s'il est gardé. */
export interface EtatNettoyage {
  /** La longueur du texte normalisé, en points de code. */
  longueur: number;
  /** Vrai s'il a au moins LONGUEUR_MINIMALE caractères : gardé. */
  garde: boolean;
  /** Le texte nettoyé, retraits compris (morceauxDuNettoyage). */
  morceaux: Morceau[];
}

/** L'état d'un texte, tout de suite, sans attendre l'empreinte (qui est asynchrone). */
export function etatDuNettoyage(brut: string): EtatNettoyage {
  const longueur = longueurPointsDeCode(normaliser(brut));
  return { longueur, garde: longueur >= LONGUEUR_MINIMALE, morceaux: morceauxDuNettoyage(brut) };
}

/** « 199 caractères sur les 200 qu'il faut ». */
export function phraseLongueur(n: number): string {
  return `${caracteres(n)} sur les ${LONGUEUR_MINIMALE} qu’il faut`;
}

/** Le verdict du nettoyage : gardé, ou écarté parce que trop court. */
export function verdictDuTexte(etat: EtatNettoyage): string {
  if (etat.garde) return `Gardé${FINE}: il a au moins ${LONGUEUR_MINIMALE} caractères.`;
  return `Écarté${FINE}: trop court, il manque ${caracteres(LONGUEUR_MINIMALE - etat.longueur)}.`;
}

/** Où ira le texte : à l'entraînement ou à la validation, d'après son empreinte (estValidation). */
export function coteDuTexte(etat: EtatNettoyage, empreinteDuTexte: string): string {
  if (!etat.garde) return 'Écarté, ce texte ne servira ni à l’entraînement, ni à la validation.';
  return estValidation(empreinteDuTexte) ? 'Ce texte servira à la validation.' : 'Ce texte servira à l’entraînement.';
}

/**
 * Ce que dit le second champ : même empreinte ou non. `etat` est celui du premier texte (deux
 * textes de même empreinte se nettoient pareil : ils ont la même longueur). Sans second texte,
 * ou sans son empreinte, l'invitation à en écrire un.
 */
export function messageDoublon(etat: EtatNettoyage, autre: string, empreinteA: string | null, empreinteB: string | null): string {
  if (autre === '' || empreinteA === null || empreinteB === null) return 'Écris un autre texte pour comparer les empreintes.';
  if (empreinteA !== empreinteB) return `Empreinte différente${FINE}: ce n’est pas un doublon.`;
  if (!etat.garde) return `Même empreinte${FINE}: ce serait un doublon, mais ce texte est déjà écarté, trop court.`;
  return `Même empreinte${FINE}: c’est un doublon.`;
}

/**
 * Le défi : deux textes différents à l'écran (les deux champs ne disent pas la même chose),
 * mais une seule empreinte. Seuls des textes qui se nettoient pareil y arrivent.
 */
export function etatDuDefi(
  premier: string,
  autre: string,
  empreinteA: string | null,
  empreinteB: string | null,
): { reussi: boolean; texte: string } {
  if (autre === '' || empreinteB === null) return { reussi: false, texte: `Pas encore${FINE}: écris un autre texte.` };
  if (autre === premier) return { reussi: false, texte: `Pas encore${FINE}: les deux textes sont les mêmes.` };
  if (empreinteA !== empreinteB) return { reussi: false, texte: `Pas encore${FINE}: les empreintes diffèrent.` };
  return {
    reussi: true,
    texte: `Défi réussi${FINE}: deux textes différents, une seule empreinte. Une fois nettoyés, ils sont identiques.`,
  };
}
