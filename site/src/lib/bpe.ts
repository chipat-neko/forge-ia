// Le tokenizer BPE du chapitre 1.3, en TypeScript, pour la démo du navigateur.
//
// C'est le jumeau exact de projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py :
// mêmes pré-jetons, mêmes fusions, mêmes numéros. Le fichier
// projets/1.3-tokenizer/tests/attendus.json, calculé par le Python, le prouve
// dans bpe.test.ts. Si l'un des deux change, l'autre doit suivre.
//
// Deux précautions rendent le résultat identique d'un langage à l'autre :
//  - le motif nomme la propriété Unicode White_Space au lieu de \s ;
//  - les comparaisons se font par point de code (comme Python), et non par
//    unité UTF-16 (comme le « < » de JavaScript sur les chaînes).

import corpus from '../../../projets/1.3-tokenizer/donnees/corpus.txt?raw';

// Un « pré-jeton » est un mot qui garde l'espace qui le précède (comme dans GPT).
// De gauche à droite, le motif essaie dans cet ordre :
//   - des lettres (avec leurs accents), précédées d'une espace éventuelle ;
//   - des chiffres, précédés d'une espace éventuelle ;
//   - de la ponctuation ou des symboles, précédés d'une espace éventuelle ;
//   - des espaces et retours à la ligne qui restent.
// Le drapeau `u` est nécessaire pour comprendre \p{L}, et pour que « 🙂 » soit
// un seul caractère et non deux moitiés.
const MOTIF =
  /\p{White_Space}?[\p{L}\p{M}]+|\p{White_Space}?\p{N}+|\p{White_Space}?[^\p{White_Space}\p{L}\p{N}]+|\p{White_Space}+/gu;

/** Une fusion apprise : les symboles `a` et `b` collés, vus `compte` fois. */
export interface Fusion {
  a: string;
  b: string;
  compte: number;
}

/**
 * Un jeton du texte découpé :
 * - `texte` : les caractères du jeton ;
 * - `id` : son numéro, ou `null` si c'est un caractère absent du corpus ;
 * - `mot` : l'indice du pré-jeton (du mot) dont il vient.
 */
export interface Jeton {
  texte: string;
  id: number | null;
  mot: number;
}

// Un mot du corpus : ses symboles (au départ, un par caractère) et le nombre
// de fois qu'il apparaît.
interface Mot {
  symboles: string[];
  frequence: number;
}

// Un symbole d'un texte à découper : son texte, et son numéro qui voyage avec lui.
interface Symbole {
  texte: string;
  id: number | null;
}

/**
 * Compare deux textes par point de code, comme le fait Python.
 *
 * Le « < » de JavaScript compare les unités UTF-16 : il rangerait « 🙂 »
 * (D83D DE42) avant « U+FFFD », alors que son point de code (U+1F642) est plus
 * grand. Un texte qui est le début d'un autre passe avant lui.
 */
export function comparerPointsDeCode(a: string, b: string): number {
  let i = 0;
  while (i < a.length && i < b.length) {
    const pa = a.codePointAt(i) as number;
    const pb = b.codePointAt(i) as number;
    if (pa !== pb) return pa < pb ? -1 : 1;
    // Deux points de code égaux occupent autant d'unités : i vaut pour a et pour b.
    i += pa > 0xffff ? 2 : 1;
  }
  return Math.sign(a.length - b.length);
}

/** Découpe un texte en pré-jetons : « Le forgeron » donne ["Le", " forgeron"]. */
export function preDecouper(texte: string): string[] {
  return texte.match(MOTIF) ?? [];
}

// Compte combien de fois chaque mot apparaît dans le corpus.
function compterMots(texte: string): Mot[] {
  const frequences = new Map<string, number>();
  for (const mot of preDecouper(texte)) frequences.set(mot, (frequences.get(mot) ?? 0) + 1);
  // Array.from(mot) sépare par point de code : un emoji reste un seul symbole.
  return [...frequences].map(([mot, frequence]) => ({ symboles: Array.from(mot), frequence }));
}

// Compte les paires de symboles voisins, en tenant compte de la fréquence des mots.
function compterPaires(mots: Mot[]): Map<string, Fusion> {
  const paires = new Map<string, Fusion>();
  for (const { symboles, frequence } of mots) {
    // On regarde chaque symbole avec son voisin de droite.
    for (let i = 0; i + 1 < symboles.length; i++) {
      const a = symboles[i];
      const b = symboles[i + 1];
      // La longueur de `a` devant la clé évite qu'« a|bc » et « ab|c » se confondent.
      const cle = `${a.length}:${a}${b}`;
      const paire = paires.get(cle);
      if (paire) paire.compte += frequence;
      else paires.set(cle, { a, b, compte: frequence });
    }
  }
  return paires;
}

// Choisit la paire la plus fréquente. En cas d'égalité, on prend la plus petite
// paire (a, b) dans l'ordre des points de code : le résultat est toujours le même.
function paireLaPlusFrequente(paires: Map<string, Fusion>): Fusion {
  let meilleure: Fusion | undefined;
  for (const paire of paires.values()) {
    if (
      meilleure === undefined ||
      paire.compte > meilleure.compte ||
      (paire.compte === meilleure.compte && plusPetite(paire, meilleure))
    ) {
      meilleure = paire;
    }
  }
  return meilleure as Fusion;
}

function plusPetite(x: Fusion, y: Fusion): boolean {
  return (comparerPointsDeCode(x.a, y.a) || comparerPointsDeCode(x.b, y.b)) < 0;
}

// Remplace la paire par un seul symbole dans tous les mots. On avance de gauche
// à droite, sans chevauchement : dans « aaa » avec la paire (a, a), on obtient
// (aa, a) et non (aa, aa).
function fusionner(mots: Mot[], a: string, b: string): Mot[] {
  return mots.map(({ symboles, frequence }) => {
    const resultat: string[] = [];
    let i = 0;
    while (i < symboles.length) {
      if (i + 1 < symboles.length && symboles[i] === a && symboles[i + 1] === b) {
        resultat.push(a + b);
        i += 2; // on saute les deux symboles qui viennent d'être collés
      } else {
        resultat.push(symboles[i]);
        i += 1;
      }
    }
    return { symboles: resultat, frequence };
  });
}

/**
 * Apprend au plus `nbFusions` fusions sur le corpus.
 *
 * On s'arrête plus tôt si aucune paire n'apparaît au moins 2 fois : coller une
 * paire vue une seule fois n'apprendrait rien d'utile.
 */
export function apprendre(texteDuCorpus: string, nbFusions: number): Fusion[] {
  let mots = compterMots(texteDuCorpus);
  const fusions: Fusion[] = [];
  for (let n = 0; n < nbFusions; n++) {
    const paires = compterPaires(mots);
    if (paires.size === 0) break;
    const paire = paireLaPlusFrequente(paires);
    if (paire.compte < 2) break;
    fusions.push({ a: paire.a, b: paire.b, compte: paire.compte });
    mots = fusionner(mots, paire.a, paire.b);
  }
  return fusions;
}

// Applique une fusion à un mot, de gauche à droite, sans chevauchement.
function fusionnerSymboles(symboles: Symbole[], fusion: Fusion, numero: number): Symbole[] {
  const resultat: Symbole[] = [];
  let i = 0;
  while (i < symboles.length) {
    if (i + 1 < symboles.length && symboles[i].texte === fusion.a && symboles[i + 1].texte === fusion.b) {
      resultat.push({ texte: fusion.a + fusion.b, id: numero });
      i += 2;
    } else {
      resultat.push(symboles[i]);
      i += 1;
    }
  }
  return resultat;
}

/** Apprend les fusions sur un corpus, puis découpe des textes. */
export class TokenizerPedagogique {
  readonly fusions: Fusion[];
  /** Les caractères du corpus, sans doublon, triés par point de code. */
  readonly base: string[];
  private readonly numeroDeBase: Map<string, number>;

  constructor(texteDuCorpus: string, nbFusionsMax = 200) {
    this.fusions = apprendre(texteDuCorpus, nbFusionsMax);
    // [...new Set(texte)] parcourt le texte par point de code, comme Python.
    this.base = [...new Set(texteDuCorpus)].sort(comparerPointsDeCode);
    this.numeroDeBase = new Map(this.base.map((caractere, i) => [caractere, i]));
  }

  /**
   * Découpe `texte` en rejouant les `k` premières fusions.
   *
   * Numéros des jetons :
   * - un caractère de base a pour numéro sa place dans `base` (`null` s'il est
   *   inconnu) ;
   * - le symbole créé par la fusion d'indice j a pour numéro base.length + j.
   * Le numéro voyage avec le symbole : on ne le cherche pas à partir de son
   * texte, car deux fusions différentes peuvent donner le même texte.
   */
  decouper(texte: string, k: number): Jeton[] {
    k = Math.max(0, Math.min(k, this.fusions.length));
    const jetons: Jeton[] = [];
    preDecouper(texte).forEach((mot, indiceMot) => {
      let symboles: Symbole[] = Array.from(mot, (caractere) => ({
        texte: caractere,
        id: this.numeroDeBase.get(caractere) ?? null,
      }));
      for (let j = 0; j < k && symboles.length > 1; j++) {
        // Un mot réduit à un seul symbole ne peut plus fusionner : on s'arrête là,
        // le résultat est le même et le découpage de longs textes reste rapide.
        symboles = fusionnerSymboles(symboles, this.fusions[j], this.base.length + j);
      }
      for (const { texte: morceau, id } of symboles) jetons.push({ texte: morceau, id, mot: indiceMot });
    });
    return jetons;
  }
}

/** Le tokenizer du chapitre 1.3, appris une seule fois sur son corpus. */
export const tokenizer13 = new TokenizerPedagogique(corpus);

/** Affichage lisible d'un jeton : l'espace devient « ␣ », le retour à la ligne « ↵ ». */
export function visible(s: string): string {
  return s.replace(/ /g, '␣').replace(/\n/g, '↵');
}

/**
 * Les trois réponses du pari « combien de jetons ? », par ordre croissant :
 * le nombre de mots (pré-jetons qui contiennent une lettre), le nombre exact
 * de jetons avec `k` fusions (la bonne réponse, `juste`) et le nombre de
 * caractères (points de code). La bonne réponse vient du même code que la démo.
 *
 * Lève une erreur si deux nombres sont égaux : l'auteur doit alors choisir un
 * autre exemple, sinon les choix ne seraient pas distincts.
 */
export function choixNombreDeJetons(texte: string, k: number): { texte: string; juste: boolean }[] {
  const mots = preDecouper(texte).filter((mot) => /\p{L}/u.test(mot)).length;
  const jetons = tokenizer13.decouper(texte, k).length;
  const caracteres = Array.from(texte).length;
  const choix = [
    { n: mots, juste: false },
    { n: jetons, juste: true },
    { n: caracteres, juste: false },
  ].sort((x, y) => x.n - y.n);
  if (choix[0].n === choix[1].n || choix[1].n === choix[2].n) {
    throw new Error(
      `Deux nombres sont égaux (${mots} mots, ${jetons} jetons, ${caracteres} caractères) : ` +
        'choisir un autre exemple.',
    );
  }
  return choix.map(({ n, juste }) => ({ texte: `${n} ${n > 1 ? 'jetons' : 'jeton'}`, juste }));
}
