// Le nettoyage des textes de « ton IA », en TypeScript.
//
// C'est le jumeau exact de projets/forge/forge/donnees/nettoyage.py (nettoyer, empreinte),
// de melange.py (est_validation) et de sources.py (le filtre du code Python), et du tri
// de projets/1.2-donnees/donnees_pas_a_pas/trier.py. Le fichier d'attendus
// projets/1.2-donnees/tests/attendus.json, calculé par le Python, le prouve dans
// nettoyeur.test.ts, et la page d'essai de parité le vérifie dans Chrome, Firefox et WebKit.
//
// Trois pièges, que les attendus vérifient :
// - les blancs de fin sont ceux de str.isspace() de Python (BLANCS_PYTHON), et pas ceux de
//   trimEnd() : celui-ci retire U+FEFF, que Python garde, et ne retire pas U+001C à U+001F
//   ni U+0085 (que le nettoyage a retirés avant, comme contrôles) ;
// - une moitié de paire de substitution est retirée, mais pas une paire entière (un emoji) :
//   l'indicateur « u » de l'expression régulière lit le texte en points de code ;
// - la longueur se compte en points de code, comme len() de Python : « 😀 » compte pour un,
//   alors que .length en compte deux.
//
// Une limite, la seule : deux moitiés de paire de substitution collées, haute puis basse
// (deux points de code dans une chaîne Python), sont pour JavaScript une paire valide, donc
// un seul caractère (un emoji) que le jumeau garde, alors que Python les retire. JavaScript
// ne distingue pas les deux cas, et aucun fichier JSON ne peut les produire : le décodeur de
// json recolle \ud83d\ude00 en un seul point de code, en Python comme en JavaScript. Seule
// une chaîne fabriquée à la main dans un programme Python l'atteint. Les moitiés seules (une
// haute sans basse, ou l'inverse) sont, elles, retirées des deux côtés.
//
// L'empreinte passe par crypto.subtle (SHA-1), donc elle est asynchrone. Ce module n'importe
// que donnees.ts, qui n'importe rien : un parcours de test peut l'importer.

import { LICENCES_PERMISSIVES, PART_VALIDATION, type NomSource } from './donnees';

/** Sous cette longueur (en points de code, une fois nettoyé), un texte n'apprend rien : écarté. */
export const LONGUEUR_MINIMALE = 200;

/**
 * Les points de code où str.isspace() de Python est vrai : ce que str.rstrip() retire. Les
 * attendus (blancs_python) le vérifient contre Python lui-même, sur les 1 114 112 points de code.
 */
export const BLANCS_PYTHON: readonly number[] = Object.freeze([
  0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003,
  0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000,
]);

const BLANCS: ReadonlySet<number> = new Set(BLANCS_PYTHON);

// Les caractères de contrôle retirés : tout sauf \n (0x0A) et \t (0x09), donc aussi \r seul, les
// contrôles C0, 0x7F et les contrôles C1. S'y ajoutent les moitiés de paires de substitution.
// L'indicateur « u » : une paire complète est un seul point de code, hors de la classe.
const CONTROLES = /[\u{0}-\u{8}\u{b}-\u{1f}\u{7f}-\u{9f}\u{d800}-\u{dfff}]/gu;

/** Le nombre de points de code d'un texte, comme len() en Python (une moitié de paire compte pour un). */
export function longueurPointsDeCode(texte: string): number {
  let n = 0;
  for (let i = 0; i < texte.length; i++) {
    n++;
    const unite = texte.charCodeAt(i);
    // Une paire complète (une moitié haute, puis une basse) est un seul point de code.
    if (unite >= 0xd800 && unite <= 0xdbff && i + 1 < texte.length) {
      const suivante = texte.charCodeAt(i + 1);
      if (suivante >= 0xdc00 && suivante <= 0xdfff) i++;
    }
  }
  return n;
}

/** Retire les blancs de fin de Python (BLANCS_PYTHON), et seulement eux. */
function retirerBlancsDeFin(texte: string): string {
  let fin = texte.length;
  while (fin > 0 && BLANCS.has(texte.charCodeAt(fin - 1))) fin--;
  return texte.slice(0, fin);
}

/**
 * Les transformations du nettoyage, sans le seuil de longueur : fins de ligne \n, contrôles
 * retirés (avant la forme NFC, pour qu'un contrôle ne sépare pas une lettre de son accent),
 * forme NFC, blancs de fin retirés.
 */
export function normaliser(texte: string): string {
  const unifie = texte.replace(/\r\n/g, '\n');
  const sansControles = unifie.replace(CONTROLES, '');
  return retirerBlancsDeFin(sansControles.normalize('NFC'));
}

/** Nettoie un texte ; renvoie null s'il fait moins de 200 caractères (points de code) une fois nettoyé. */
export function nettoyer(texte: string): string | null {
  const propre = normaliser(texte);
  return longueurPointsDeCode(propre) < LONGUEUR_MINIMALE ? null : propre;
}

/** SHA-1 en hexadécimal d'un texte déjà nettoyé (pas de nettoyage de plus). */
export async function empreinteDuTexteNettoye(texteNettoye: string): Promise<string> {
  const octets = new TextEncoder().encode(texteNettoye);
  const condensat = new Uint8Array(await crypto.subtle.digest('SHA-1', octets));
  return Array.from(condensat, (octet) => octet.toString(16).padStart(2, '0')).join('');
}

/** SHA-1 en hexadécimal du texte nettoyé : deux textes qui se nettoient pareil ont la même. */
export async function empreinte(texte: string): Promise<string> {
  return empreinteDuTexteNettoye(normaliser(texte));
}

/**
 * Dit si un document, d'après son empreinte, va dans la validation (0,5 % par défaut) : les
 * 8 premiers chiffres hexadécimaux, lus comme un entier entre 0 et 2³² − 1, comparés à part × 2³².
 */
export function estValidation(empreinteHex: string, part: number = PART_VALIDATION): boolean {
  return parseInt(empreinteHex.slice(0, 8), 16) < part * 4294967296;
}

/** Une ligne d'une source : colonne → valeur (du JSON). */
export type Ligne = Readonly<Record<string, unknown>>;

/** Garde un fichier Python publié sous une licence permissive ; tout le reste est écarté. */
export function garderPythonPermissif(ligne: Ligne): boolean {
  const licence = ligne.license;
  return ligne.language === 'Python' && typeof licence === 'string' && LICENCES_PERMISSIVES.includes(licence.toLowerCase());
}

/** Ce que le tri sait d'une source : la colonne du texte, et le filtre de ses lignes. */
export interface SourceDeTri {
  colonne: string;
  garder: (ligne: Ligne) => boolean;
}

/** Les sources de forge.donnees.sources.SOURCES : le français du web et Wikipédia ne refusent aucune ligne. */
export const SOURCES_DE_TRI: Readonly<Record<NomSource, SourceDeTri>> = Object.freeze({
  web_fr: Object.freeze({ colonne: 'text', garder: () => true }),
  wikipedia_fr: Object.freeze({ colonne: 'text', garder: () => true }),
  code_python: Object.freeze({ colonne: 'code', garder: garderPythonPermissif }),
});

export type Raison = 'gardé' | 'trop court' | 'doublon' | 'licence' | 'langage';

/** Les raisons dans l'ordre où on les affiche : d'abord ce qui est gardé, puis les raisons d'écart. */
export const RAISONS: readonly Raison[] = Object.freeze(['gardé', 'trop court', 'doublon', 'licence', 'langage']);

/** Ce que le tri décide d'un document (les champs vides valent null, comme None en Python). */
export interface Verdict {
  garde: boolean;
  raison: Raison;
  texte: string | null;
  empreinte: string | null;
  validation: boolean | null;
}

// Le téléchargement de forge retient les 64 premiers bits de l'empreinte pour reconnaître un doublon.
const CHIFFRES_DE_LA_CLE = 16;

/** Un autre langage que Python : « langage » ; sinon, c'est la licence. */
export function raisonDuRefus(ligne: Ligne): Raison {
  return ligne.language !== 'Python' ? 'langage' : 'licence';
}

/**
 * Un verdict par ligne, dans l'ordre : licence et langage, longueur, doublon, puis gardé. Le
 * jumeau de trier() de trier.py.
 */
export async function trier(lignes: Iterable<Ligne>, nomSource: NomSource): Promise<Verdict[]> {
  const source = SOURCES_DE_TRI[nomSource];
  const vues = new Set<string>();
  const verdicts: Verdict[] = [];
  for (const ligne of lignes) {
    if (!source.garder(ligne)) {
      verdicts.push({ garde: false, raison: raisonDuRefus(ligne), texte: null, empreinte: null, validation: null });
      continue;
    }
    const brut = ligne[source.colonne];
    const texte = typeof brut === 'string' ? nettoyer(brut) : null;
    if (texte === null) {
      verdicts.push({ garde: false, raison: 'trop court', texte: null, empreinte: null, validation: null });
      continue;
    }
    const empreinteDuTexte = await empreinteDuTexteNettoye(texte);
    const cle = empreinteDuTexte.slice(0, CHIFFRES_DE_LA_CLE);
    if (vues.has(cle)) {
      verdicts.push({ garde: false, raison: 'doublon', texte: null, empreinte: empreinteDuTexte, validation: null });
      continue;
    }
    vues.add(cle);
    verdicts.push({
      garde: true,
      raison: 'gardé',
      texte,
      empreinte: empreinteDuTexte,
      validation: estValidation(empreinteDuTexte),
    });
  }
  return verdicts;
}

/** Combien de verdicts pour chaque raison, dans l'ordre de RAISONS (zéro compris). */
export function compterRaisons(verdicts: Iterable<Pick<Verdict, 'raison'>>): Record<Raison, number> {
  const comptes: Record<Raison, number> = { gardé: 0, 'trop court': 0, doublon: 0, licence: 0, langage: 0 };
  for (const { raison } of verdicts) comptes[raison]++;
  return comptes;
}

/**
 * Lit une valeur du fichier d'attendus qui code un texte : une chaîne, une liste de points de
 * code (texte à moitié de paire de substitution), ou { repete, fois } (un caractère répété).
 */
export function decoderTexte(valeur: unknown): unknown {
  if (Array.isArray(valeur)) return valeur.map((point: number) => String.fromCodePoint(point)).join('');
  if (typeof valeur === 'object' && valeur !== null && 'repete' in valeur && 'fois' in valeur) {
    const { repete, fois } = valeur as { repete: string; fois: number };
    return repete.repeat(fois);
  }
  return valeur;
}

/**
 * Écrit un texte comme le fichier d'attendus (l'inverse de decoderTexte) : en liste de points de
 * code s'il contient une moitié de paire de substitution, en { repete, fois } s'il est très long
 * et fait d'un seul caractère répété, en chaîne sinon.
 */
export function coderTexte(texte: string): string | number[] | { repete: string; fois: number } {
  const points = Array.from(texte, (c) => c.codePointAt(0) as number);
  if (points.some((point) => point >= 0xd800 && point <= 0xdfff)) return points;
  if (points.length > 1000 && points.every((point) => point === points[0])) {
    return { repete: String.fromCodePoint(points[0]), fois: points.length };
  }
  return texte;
}
