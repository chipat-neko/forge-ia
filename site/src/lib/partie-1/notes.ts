// La note d'une réponse, chapitre 1.8 : le jumeau TypeScript des contrôles de forge qui classent deux réponses
// sans juge (projets/forge/forge/evaluation/langue.py, projets/forge/forge/evaluation/consignes.py pour les huit
// consignes de CONTRAINTES, et projets/forge/forge/preferences/noter.py pour la note).
//
// Python d'abord, TypeScript ensuite : une fonction pour chaque fonction du Python, les mêmes opérations dans le
// même ordre. Les attendus (FICHIERS_PARTIE_1.notes, projets/1.8-alignement/tests/attendus.json) sont calculés par
// le Python, et la page de parité les retrouve dans Chrome, Firefox et WebKit.
//
// Ce que Python et JavaScript ne font pas pareil, et ce que le jumeau fait à la place :
// - ni \w, ni \b, ni \s : les tests de caractères sont explicites. Une lettre est de catégorie Unicode L
//   (/\p{L}/u), un caractère de mot une lettre, un chiffre décimal (Nd) ou « _ » ;
// - les blancs de str.strip(), str.rstrip() et str.isspace() de Python sont BLANCS_PYTHON, pas ceux de trim() :
//   JavaScript retire U+FEFF, que Python garde, et ne retire ni U+001C à U+001F ni U+0085, que Python retire ;
// - les textes sont lus en points de code (Array.from), comme len() de Python : « 𝒜 » (une majuscule hors du
//   premier plan d'Unicode) est une lettre, un seul caractère, alors que .length en compte deux ;
// - les listes de mots outils sont celles de langue.py, mot pour mot (notes.test.ts relit le texte de langue.py).
//
// Un seul écart avec noter.py : `noteSansJustesse` n'a pas le critère « juste », qui lit le dernier nombre d'un
// texte avec des fractions exactes (forge.raisonnement.verification) : l'atelier du chapitre ne note que les
// consignes, la langue et la longueur.
//
// Ce module n'importe rien : une page ou un parcours le charge sans rien embarquer d'autre.

/** Les réglages d'une consigne, tels que l'invite les porte (`{ n: 20 }`, `{ phrase: '…' }`, `{}`). */
export type ReglagesConsigne = Readonly<Record<string, unknown>>;

/** Une consigne d'une invite : son identifiant et ses réglages. */
export type ConsigneDInvite = readonly [string, ReglagesConsigne];

/** La note d'une réponse sans la justesse : les quatre autres critères de forge, dans le même ordre. */
export interface NoteSansJustesse {
  terminee: number;
  consignes: number;
  francais: number;
  longueur: number;
}

export const MOTS_MINIMUM = 3;
export const MOTS_MAXIMUM = 300;

// --- Les mots outils de forge.evaluation.langue ----------------------------------------------------------------

// Les deux listes n'ont aucun mot commun : les mots qui existent dans les deux langues en sont absents.
export const MOTS_FRANCAIS: ReadonlySet<string> = new Set(
  `
    le la les un une des du de et est en que qui dans pour pas sur au aux avec il elle ils elles nous vous
    je tu ce cette ces ses sa mais ou où se ne ni y à été sont ont était être avoir fait puis dont comme
    très aussi tout tous leur leurs lui cela ça mon ton notre votre mes tes cet quand sans sous entre
    chez vers donc car si
  `
    .split(/[ \n]+/)
    .filter((mot) => mot !== ''),
);

export const MOTS_ANGLAIS: ReadonlySet<string> = new Set(
  `
    the and of to is are was were be been in it that this with for his her they their have has had not at
    by from which you your we he she there would will can if then than when what who how do does did so
    its also just about into my our them these those been being
  `
    .split(/[ \n]+/)
    .filter((mot) => mot !== ''),
);

// --- Les petits tests de caractères ----------------------------------------------------------------------------

/**
 * Les points de code où str.isspace() de Python est vrai : ce que str.strip() et str.rstrip() retirent. Ce sont
 * ceux de BLANCS_PYTHON (nettoyeur.ts), que notes.test.ts compare.
 */
export const BLANCS_DE_PYTHON: readonly number[] = Object.freeze([
  0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003,
  0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000,
]);

const BLANCS: ReadonlySet<number> = new Set(BLANCS_DE_PYTHON);

const LETTRE = /^\p{L}$/u;
const CARACTERE_DE_MOT = /^[\p{L}\p{Nd}_]$/u;
const A_UNE_LETTRE_OU_UN_NOMBRE = /[\p{L}\p{N}]/u;

/** Un blanc de Python : c.isspace(), pour un caractère (un point de code lu par Array.from). */
function estUnBlanc(c: string): boolean {
  return BLANCS.has(c.codePointAt(0) as number);
}

function estUneLettre(c: string): boolean {
  return LETTRE.test(c);
}

function estUnCaractereDeMot(c: string): boolean {
  return CARACTERE_DE_MOT.test(c);
}

function estUnChiffreArabe(c: string): boolean {
  return c >= '0' && c <= '9';
}

/** str.strip() de Python, sans argument : les blancs de BLANCS_PYTHON, au début et à la fin (tous dans le premier plan). */
function strip(texte: string): string {
  let debut = 0;
  let fin = texte.length;
  while (debut < fin && BLANCS.has(texte.charCodeAt(debut))) debut++;
  while (fin > debut && BLANCS.has(texte.charCodeAt(fin - 1))) fin--;
  return texte.slice(debut, fin);
}

/** str.rstrip() de Python, sans argument. */
function rstrip(texte: string): string {
  let fin = texte.length;
  while (fin > 0 && BLANCS.has(texte.charCodeAt(fin - 1))) fin--;
  return texte.slice(0, fin);
}

/** str.rstrip(caracteres) de Python : `caracteres` ne contient que des caractères du premier plan. */
function rstripCaracteres(texte: string, caracteres: string): string {
  let fin = texte.length;
  while (fin > 0 && caracteres.includes(texte.charAt(fin - 1))) fin--;
  return texte.slice(0, fin);
}

/** str.lstrip(caracteres) de Python. */
function lstripCaracteres(texte: string, caracteres: string): string {
  let debut = 0;
  while (debut < texte.length && caracteres.includes(texte.charAt(debut))) debut++;
  return texte.slice(debut);
}

// --- forge.evaluation.langue ------------------------------------------------------------------------------------

/** Les suites de lettres du texte, en minuscules ; le reste coupe, apostrophes comprises. */
export function mots(texte: string): string[] {
  const resultat: string[] = [];
  let courant: string[] = [];
  for (const c of Array.from(texte)) {
    if (estUneLettre(c)) {
      courant.push(c);
    } else if (courant.length > 0) {
      resultat.push(courant.join('').toLowerCase());
      courant = [];
    }
  }
  if (courant.length > 0) resultat.push(courant.join('').toLowerCase());
  return resultat;
}

/** « fr » si le texte est français, « autre » sinon, « indetermine » s'il a moins de 3 mots outils. */
export function langue(texte: string): 'fr' | 'autre' | 'indetermine' {
  let f = 0;
  let a = 0;
  for (const mot of mots(texte)) {
    if (MOTS_FRANCAIS.has(mot)) f++;
    else if (MOTS_ANGLAIS.has(mot)) a++;
  }
  if (f + a < 3) return 'indetermine';
  if (f >= 2 * a) return 'fr';
  return 'autre';
}

// --- forge.evaluation.consignes : les petits outils de texte ----------------------------------------------------

/** « mot » est-il dans le texte, entier (sans lettre, chiffre ni « _ » collé), sans tenir compte de la casse ? */
function contientMotEntier(texte: string, mot: string): boolean {
  const t = Array.from(texte.toLowerCase());
  const m = Array.from(mot.toLowerCase());
  if (m.length === 0) return false;
  const trouver = (depuis: number): number => {
    for (let i = depuis; i + m.length <= t.length; i++) {
      let pareil = true;
      for (let k = 0; k < m.length; k++) {
        if (t[i + k] !== m[k]) {
          pareil = false;
          break;
        }
      }
      if (pareil) return i;
    }
    return -1;
  };
  let debut = trouver(0);
  while (debut >= 0) {
    const fin = debut + m.length;
    const avantLibre = debut === 0 || !estUnCaractereDeMot(t[debut - 1]);
    const apresLibre = fin === t.length || !estUnCaractereDeMot(t[fin]);
    if (avantLibre && apresLibre) return true;
    debut = trouver(debut + 1);
  }
  return false;
}

/** Au moins une lettre à casse, et aucune majuscule. */
function estMinuscule(texte: string): boolean {
  return texte === texte.toLowerCase() && texte !== texte.toUpperCase();
}

// Les phrases : un jeton (suite de caractères non blancs) clôt la phrase s'il finit, avant d'éventuels
// guillemets ou parenthèses fermants, par . ! ? ou … ; sauf une abréviation courante (« M. », « Dr. »...) et
// un numéro de liste (« 1. ») au début d'une phrase. Une phrase doit contenir une lettre ou un chiffre.
const TERMINAISONS = '.!?…';
const FERMANTS = '"\'»”’)]*_';
const OUVRANTS = '(«"\'“[*_';
const ABBREVIATIONS: ReadonlySet<string> = new Set(['m', 'mm', 'mme', 'mmes', 'mlle', 'mlles', 'dr', 'pr', 'st', 'ste', 'cf', 'vs']);

/** Les positions (début, fin exclue) des suites de caractères non blancs. */
function jetons(texte: string): [number, number][] {
  const resultat: [number, number][] = [];
  let debut = -1;
  for (let i = 0; i < texte.length; i++) {
    if (BLANCS.has(texte.charCodeAt(i))) {
      if (debut >= 0) {
        resultat.push([debut, i]);
        debut = -1;
      }
    } else if (debut < 0) {
      debut = i;
    }
  }
  if (debut >= 0) resultat.push([debut, texte.length]);
  return resultat;
}

function phrasesPositions(texte: string): [number, number][] {
  const phrases: [number, number][] = [];
  let debutPhrase = -1;
  let contenu = false;
  for (const [debut, fin] of jetons(texte)) {
    const jeton = texte.slice(debut, fin);
    const coeur = rstripCaracteres(jeton, FERMANTS);
    const sansLeDernier = coeur.slice(0, -1);
    if (!contenu && coeur.endsWith('.') && sansLeDernier !== '' && Array.from(sansLeDernier).every(estUnChiffreArabe)) {
      continue; // numéro de liste au début d'une phrase : ni contenu ni fin
    }
    if (debutPhrase < 0) debutPhrase = debut;
    if (A_UNE_LETTRE_OU_UN_NOMBRE.test(jeton)) contenu = true;
    const abreviation = coeur.endsWith('.') && ABBREVIATIONS.has(lstripCaracteres(sansLeDernier.toLowerCase(), OUVRANTS));
    if (contenu && coeur !== '' && TERMINAISONS.includes(coeur.charAt(coeur.length - 1)) && !abreviation) {
      phrases.push([debutPhrase, fin]);
      debutPhrase = -1;
      contenu = false;
    }
  }
  if (contenu) phrases.push([debutPhrase, texte.length]);
  return phrases;
}

/** Le nombre de phrases du texte, par la règle maison de forge. */
export function compterPhrases(texte: string): number {
  return phrasesPositions(texte).length;
}

/** Les lignes qui ne sont pas vides une fois les blancs retirés, sans leurs blancs de bord. */
function lignesNonVides(reponse: string): string[] {
  return reponse
    .split('\n')
    .map((ligne) => strip(ligne))
    .filter((ligne) => ligne !== '');
}

// --- forge.evaluation.consignes : les huit vérificateurs de CONTRAINTES ----------------------------------------

const CHEVRONS: readonly (readonly [string, string])[] = [
  ['«', '»'],
  ['<<', '>>'],
];

function nombreDe(reglages: ReglagesConsigne, cle: string): number {
  const valeur = reglages[cle];
  if (typeof valeur !== 'number') throw new Error(`Il manque le nombre « ${cle} » de la consigne (reçu : ${Object.keys(reglages).join(', ') || 'rien'}).`);
  return valeur;
}

function chaineDe(reglages: ReglagesConsigne, cle: string): string {
  const valeur = reglages[cle];
  if (typeof valeur !== 'string') throw new Error(`Il manque le texte « ${cle} » de la consigne (reçu : ${Object.keys(reglages).join(', ') || 'rien'}).`);
  return valeur;
}

/** Les huit consignes de forge (CONTRAINTES), chacune avec son vérificateur strict : la réponse la respecte-t-elle ? */
export const VERIFICATEURS_CONTRAINTES: Readonly<Record<string, (reponse: string, reglages: ReglagesConsigne) => boolean>> = Object.freeze({
  // mots_max : « Réponds en {n} mots au plus. »
  mots_max: (reponse, reglages) => {
    const n = mots(reponse).length;
    return n >= 1 && n <= nombreDe(reglages, 'n');
  },
  // phrases_max : « Réponds en {n} phrases au plus. »
  phrases_max: (reponse, reglages) => {
    const n = compterPhrases(reponse);
    return n >= 1 && n <= nombreDe(reglages, 'n');
  },
  // minuscules : « Écris toute ta réponse en minuscules. »
  minuscules: (reponse) => estMinuscule(reponse),
  // sans_virgule : « N'utilise aucune virgule. »
  sans_virgule: (reponse) => strip(reponse) !== '' && !reponse.includes(','),
  // mot_obligatoire : « Emploie le mot « {mot} » dans ta réponse. »
  mot_obligatoire: (reponse, reglages) => contientMotEntier(reponse, chaineDe(reglages, 'mot')),
  // puces : « Réponds par exactement {n} puces, chacune commençant par « - ». »
  puces: (reponse, reglages) => {
    const lignes = lignesNonVides(reponse);
    return lignes.length === nombreDe(reglages, 'n') && lignes.every((ligne) => ligne.startsWith('- ') && strip(ligne.slice(2)) !== '');
  },
  // fin_imposee : « Termine ta réponse par la phrase exacte : « {phrase} » »
  fin_imposee: (reponse, reglages) => {
    const phrase = chaineDe(reglages, 'phrase');
    return phrase !== '' && rstrip(reponse).endsWith(phrase);
  },
  // titre : « Donne d'abord un titre entre doubles chevrons, comme « titre ». »
  titre: (reponse) => {
    const lignes = lignesNonVides(reponse);
    if (lignes.length === 0) return false;
    const premiere = lignes[0];
    for (const [ouvrant, fermant] of CHEVRONS) {
      if (premiere.startsWith(ouvrant)) {
        const fin = premiere.indexOf(fermant, ouvrant.length);
        if (fin >= 0 && strip(premiere.slice(ouvrant.length, fin)) !== '') return true;
      }
    }
    return false;
  },
});

// --- forge.preferences.noter ------------------------------------------------------------------------------------

/**
 * La note d'une réponse, sans le critère « juste » : `terminee` (1 si la réponse a fini son tour), `consignes` (le
 * nombre de consignes de l'invite qu'elle respecte), `francais` (0 seulement si la langue est reconnue « autre »)
 * et `longueur` (1 si le texte a de 3 à 300 mots). Une consigne inconnue lève une erreur, comme noter().
 */
export function noteSansJustesse(texte: string, terminee: boolean, contraintes: readonly ConsigneDInvite[]): NoteSansJustesse {
  let respectees = 0;
  for (const [nom, reglages] of contraintes) {
    const verifier = Object.hasOwn(VERIFICATEURS_CONTRAINTES, nom) ? VERIFICATEURS_CONTRAINTES[nom] : undefined;
    if (verifier === undefined) {
      throw new Error(`La consigne « ${nom} » est inconnue : les consignes sont ${Object.keys(VERIFICATEURS_CONTRAINTES).join(', ')}.`);
    }
    if (verifier(texte, reglages)) respectees += 1;
  }
  const n = mots(texte).length;
  return {
    terminee: terminee ? 1 : 0,
    consignes: respectees,
    francais: langue(texte) === 'autre' ? 0 : 1,
    longueur: n >= MOTS_MINIMUM && n <= MOTS_MAXIMUM ? 1 : 0,
  };
}
