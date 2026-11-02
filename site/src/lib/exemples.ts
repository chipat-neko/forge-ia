// Les exemples découpés hors chapitre : la phrase du pari de l'accueil,
// « 404 » et le mot du pari de la page 404.
//
// Tout est calculé ici, au moment de la construction, par le moteur du
// chapitre 1.3 (tokenizer13, avec toutes ses fusions) : les nombres des paris
// et les morceaux montrés viennent du même code que la démo. Ce que les textes
// affirment sur ces exemples (« ons » reste collé, « 404 » donne des jetons
// inconnus…) est vérifié aussi : si le corpus ou le moteur change et qu'une
// phrase devient fausse, la construction s'arrête avec un message clair.
import corpus from '../../../projets/1.3-tokenizer/donnees/corpus.txt?raw';
import { choixNombreDeJetons, preDecouper, tokenizer13, type Jeton } from './bpe';

/** Toutes les fusions apprises : le découpeur « fini » du chapitre 1.3. */
export const NB_FUSIONS = tokenizer13.fusions.length;

const TAILLE_BASE = tokenizer13.base.length;

/** Vrai si le jeton vient d'une fusion apprise, et non d'un caractère seul. */
export function estAssemblage(jeton: Jeton): boolean {
  return jeton.id !== null && jeton.id >= TAILLE_BASE;
}

function exiger(condition: boolean, message: string): void {
  if (!condition) throw new Error(`Exemple devenu faux : ${message}. Revoir src/lib/exemples.ts.`);
}

const NOMBRES = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix'];

/** Un petit nombre écrit en lettres (« trois »), sinon en chiffres. */
export function enLettres(n: number): string {
  return NOMBRES[n] ?? String(n);
}

/** « a », « a et b », « a, b et c ». */
export function enumerer(elements: string[]): string {
  if (elements.length <= 1) return elements.join('');
  return `${elements.slice(0, -1).join(', ')} et ${elements[elements.length - 1]}`;
}

// Les jetons d'un mot (pré-jeton) de la phrase, retrouvé par son texte.
function jetonsDuMot(jetons: Jeton[], phrase: string, mot: string): Jeton[] {
  const indice = preDecouper(phrase).indexOf(mot);
  exiger(indice >= 0, `« ${mot} » n'est pas un mot de « ${phrase} »`);
  return jetons.filter((jeton) => jeton.mot === indice);
}

// ---------- Accueil : le pari d'ouverture ----------

/** La phrase du pari d'ouverture. */
export const PHRASE_ACCUEIL = 'Construis ton IA de zéro.';

/** Ses jetons, avec toutes les fusions. */
export const jetonsAccueil = tokenizer13.decouper(PHRASE_ACCUEIL, NB_FUSIONS);

/** Les trois réponses du pari : mots, jetons (la bonne) et caractères. */
export const choixAccueil = choixNombreDeJetons(PHRASE_ACCUEIL, NB_FUSIONS);

/** Nombre de caractères de la phrase, espaces et point compris. */
export const caracteresAccueil = Array.from(PHRASE_ACCUEIL).length;

/** Deux assemblages fréquents restés collés, cités par l'explication. */
export const COLLES_ACCUEIL = ['ons', ' de'];

/** Deux mots absents du corpus, qui partent en lettres. */
export const INCONNUS_ACCUEIL = ['IA', 'zéro'];

for (const colle of COLLES_ACCUEIL) {
  exiger(
    jetonsAccueil.some((j) => j.texte === colle && estAssemblage(j)),
    `« ${colle} » n'est plus un assemblage de « ${PHRASE_ACCUEIL} »`,
  );
}
for (const mot of INCONNUS_ACCUEIL) {
  exiger(!corpus.includes(mot), `« ${mot} » apparaît dans le corpus`);
  const jetons = jetonsDuMot(jetonsAccueil, PHRASE_ACCUEIL, ` ${mot}`);
  exiger(
    jetons.every((j) => Array.from(j.texte).length === 1),
    `« ${mot} » ne part plus en lettres`,
  );
}

// ---------- Page 404 ----------

/** « 404 », tel que le lit le découpeur : un jeton par chiffre, tous inconnus. */
export const jetons404 = tokenizer13.decouper('404', NB_FUSIONS);

exiger(
  jetons404.length === 3 && jetons404.every((j) => j.id === null),
  '« 404 » ne donne plus trois jetons inconnus',
);
exiger(!tokenizer13.base.some((c) => /\p{N}/u.test(c)), 'le corpus contient un chiffre');

/** Le mot du pari de la 404. */
export const MOT_404 = 'introuvable';

/** Ses jetons, avec toutes les fusions. */
export const jetonsIntrouvable = tokenizer13.decouper(MOT_404, NB_FUSIONS);

/** Les trois réponses du pari (1 mot, les jetons, les lettres). */
export const choixIntrouvable = choixNombreDeJetons(MOT_404, NB_FUSIONS);

/** Les assemblages appris ailleurs qui servent à l'écrire : « ou », « ab », « le ». */
export const assemblagesIntrouvable = jetonsIntrouvable.filter(estAssemblage).map((j) => j.texte);

exiger(/^\p{L}+$/u.test(MOT_404), `« ${MOT_404} » n'est pas fait que de lettres`);
exiger(!corpus.includes(MOT_404), `« ${MOT_404} » apparaît dans le corpus`);
exiger(
  jetonsIntrouvable.filter((j) => !estAssemblage(j)).every((j) => Array.from(j.texte).length === 1),
  `« ${MOT_404} » a d'autres morceaux que des lettres seules et des assemblages`,
);
exiger(assemblagesIntrouvable.length > 0, `« ${MOT_404} » n'utilise aucun assemblage`);
