// L'exemple de l'animation de l'attention : « Le forgeron chauffe le fer puis il le tord ».
//
// C'est le jumeau exact de projets/mini-modele/mini_modele/exemple_attention.py :
// mêmes fonctions, mêmes boucles, même ordre des opérations. Les attendus
// (tests/attendus-attention.json, écrits par le Python) le prouvent au bit
// près dans exemple-attention.test.ts.
//
// Seuls les vecteurs des mots et les matrices sont écrits à la main, dans
// projets/mini-modele/donnees/exemple-attention.json : chaque mot porte 8
// traits (des 0 et des 1), et chacune des 2 têtes a trois matrices de 8 lignes
// et 4 colonnes, d'entiers de −5 à 5. Tout le reste est calculé ici, par les
// fonctions du mini-modèle (attention.ts) : les requêtes, les clés et les
// valeurs, les scores, le masque, les poids et les sorties.
//
// Les conventions sont celles du mini-modèle :
//  - un vecteur est une ligne, et sa projection vaut x · W :
//    y[j] = x[0] × W[0][j] + x[1] × W[1][j] + …, par i croissant ;
//  - les lignes sont les requêtes : la requête i pose la question, et le score
//    de la clé j vaut requête · clé (scoresAttention), multiplié par l'échelle
//    1 / √(taille de la tête) dans scoresEchelles ;
//  - le masque causal : la requête i ne voit que les mots 0 à i. Les cases
//    masquées (j > i) n'ont pas de score (null), et leur poids vaut 0,0.
// Ce fichier est vérifié par sources.test.ts.

import brut from '../../../../projets/mini-modele/donnees/exemple-attention.json';
import { melangerValeurs, scoresAttention, softmax } from './attention';
import { produitScalaire, racine } from './calcul';

/** Une matrice, rangée ligne par ligne. */
export type Matrice = readonly (readonly number[])[];

/** Une tête de l'exemple : son nom, ce qu'elle cherche, et ses trois matrices (une ligne par trait). */
export interface TeteExemple {
  readonly nom: string;
  readonly description: string;
  readonly wq: Matrice;
  readonly wk: Matrice;
  readonly wv: Matrice;
}

/** Un exemple d'attention : la phrase, ses jetons, les traits, un vecteur x par jeton, et les têtes. */
export interface ExempleAttention {
  readonly phrase: string;
  readonly jetons: readonly string[];
  readonly traits: readonly string[];
  readonly x: Matrice;
  readonly tetes: readonly TeteExemple[];
}

/**
 * Tout ce qu'une tête calcule sur la phrase, pour l'animation (n mots).
 *
 * - requetes, cles, valeurs : une ligne par mot (n × 4) ;
 * - scores (requête · clé) et scoresEchelles (fois l'échelle) : n × n, null quand j > i ;
 * - poids : n × n, le softmax des scoresEchelles visibles, et 0,0 quand j > i ;
 * - sorties : une ligne par mot (n × 4), les valeurs mélangées selon les poids.
 */
export interface DetailTete {
  readonly requetes: number[][];
  readonly cles: number[][];
  readonly valeurs: number[][];
  readonly scores: (number | null)[][];
  readonly scoresEchelles: (number | null)[][];
  readonly poids: number[][];
  readonly sorties: number[][];
}

const CLES_EXEMPLE = ['phrase', 'jetons', 'traits', 'x', 'tetes'] as const;
const MATRICES_TETE = ['wq', 'wk', 'wv'] as const;

/** Un nombre (pas un booléen), ni infini ni NaN. */
function estNombreFini(v: unknown): boolean {
  return typeof v === 'number' && Number.isFinite(v);
}

/**
 * m est une liste de lignes non vide, de même longueur, de nombres finis. Renvoie sa largeur.
 *
 * Si lignes est donné, m doit avoir exactement ce nombre de lignes (une par trait).
 */
export function verifierMatrice(m: unknown, nom: string, lignes: number | null): number {
  if (!Array.isArray(m) || m.length === 0) {
    throw new RangeError(`${nom} doit être une liste de lignes non vide.`);
  }
  if (lignes !== null && m.length !== lignes) {
    throw new RangeError(`${nom} doit avoir ${lignes} lignes, une par trait (reçu ${m.length}).`);
  }
  let largeur = -1;
  for (let i = 0; i < m.length; i++) {
    const ligne: unknown = m[i];
    if (!Array.isArray(ligne) || ligne.length === 0) {
      throw new RangeError(`${nom}, ligne ${i} : il faut une liste de nombres non vide.`);
    }
    if (largeur < 0) {
      largeur = ligne.length;
    }
    if (ligne.length !== largeur) {
      throw new RangeError(
        `${nom} : la ligne ${i} n'a pas la longueur de la ligne 0 (${ligne.length} au lieu de ${largeur}). ` +
          'Donne des lignes de même longueur.',
      );
    }
    for (const v of ligne) {
      if (!estNombreFini(v)) {
        throw new RangeError(`${nom}, ligne ${i} : « ${String(v)} » n'est pas un nombre fini.`);
      }
    }
  }
  return largeur;
}

/** L'exemple a ses cinq clés, une ligne de x par jeton, une case par trait, et des têtes complètes. */
export function verifierExemple(exemple: unknown): void {
  if (typeof exemple !== 'object' || exemple === null || Array.isArray(exemple)) {
    throw new RangeError("L'exemple doit être un objet JSON avec phrase, jetons, traits, x et tetes.");
  }
  const e = exemple as Record<string, unknown>;
  for (const cle of CLES_EXEMPLE) {
    if (!(cle in e)) {
      throw new RangeError(`Exemple d'attention : il manque « ${cle} » (il faut phrase, jetons, traits, x et tetes).`);
    }
  }
  const { phrase, jetons, traits, x } = e;
  if (
    typeof phrase !== 'string' ||
    !Array.isArray(jetons) ||
    !Array.isArray(traits) ||
    jetons.length === 0 ||
    traits.length === 0 ||
    ![...jetons, ...traits].every((t) => typeof t === 'string')
  ) {
    throw new RangeError(
      "Exemple d'attention : la phrase, les jetons et les traits sont des textes (au moins un jeton et un trait).",
    );
  }
  const largeur = verifierMatrice(x, 'x', null);
  const nbJetons = jetons.length;
  const nbTraits = traits.length;
  const nbLignes = (x as unknown[]).length;
  if (nbLignes !== nbJetons) {
    throw new RangeError(`Exemple d'attention : il faut une ligne de x par jeton (${nbJetons} jetons, ${nbLignes} lignes).`);
  }
  if (largeur !== nbTraits) {
    throw new RangeError(`Exemple d'attention : chaque ligne de x a une case par trait (${nbTraits} traits, ${largeur} cases).`);
  }
  const tetes = e.tetes;
  if (!Array.isArray(tetes) || tetes.length === 0) {
    throw new RangeError("Exemple d'attention : il faut au moins une tête dans tetes.");
  }
  for (const tete of tetes as unknown[]) {
    const t = tete as Record<string, unknown> | null;
    if (typeof t !== 'object' || t === null || typeof t.nom !== 'string' || typeof t.description !== 'string') {
      throw new RangeError("Exemple d'attention : le nom et la description de chaque tête sont des textes.");
    }
    for (const m of MATRICES_TETE) {
      if (!(m in t)) {
        throw new RangeError(`Exemple d'attention : il manque « ${m} » dans la tête « ${t.nom} ».`);
      }
      verifierMatrice(t[m], `tête « ${t.nom} », ${m}`, largeur);
    }
  }
}

/** Fige l'objet et tout ce qu'il contient : l'exemple est partagé, personne ne doit le modifier. */
function figer<T>(valeur: T): T {
  if (typeof valeur === 'object' && valeur !== null) {
    for (const enfant of Object.values(valeur)) figer(enfant);
    Object.freeze(valeur);
  }
  return valeur;
}

/** L'exemple du fichier donnees/exemple-attention.json, vérifié et figé. */
export const exempleAttention: ExempleAttention = (() => {
  verifierExemple(brut);
  return figer(brut);
})();

/** L'exemple par défaut, comme charger_exemple() en Python (ici, il est déjà chargé). */
export function chargerExemple(): ExempleAttention {
  return exempleAttention;
}

/** Une copie de la matrice, en tableaux ordinaires (en TypeScript, les nombres sont déjà des flottants). */
function enFlottants(m: Matrice): number[][] {
  return m.map((ligne) => ligne.map((v) => v));
}

/** x · W : y[j] = x[0] × W[0][j] + x[1] × W[1][j] + …, par i croissant (comme produit dans modele.ts). */
export function projeter(x: readonly number[], w: Matrice): number[] {
  const y: number[] = [];
  for (let j = 0; j < w[0].length; j++) {
    const colonne: number[] = [];
    for (let i = 0; i < w.length; i++) colonne.push(w[i][j]);
    y.push(produitScalaire(x, colonne));
  }
  return y;
}

/** Le calcul d'une tête sur toute la phrase, mot par mot, avec les fonctions du mini-modèle. */
export function detaillerTete(x: Matrice, wq: Matrice, wk: Matrice, wv: Matrice): DetailTete {
  const traits = verifierMatrice(x, 'x', null);
  const taille = verifierMatrice(wq, 'wq', traits);
  if (verifierMatrice(wk, 'wk', traits) !== taille) {
    throw new RangeError(
      `wq et wk doivent avoir autant de colonnes (${taille} et ${wk[0].length}) : le score est requête · clé.`,
    );
  }
  verifierMatrice(wv, 'wv', traits);
  const xf = enFlottants(x);
  const wqf = enFlottants(wq);
  const wkf = enFlottants(wk);
  const wvf = enFlottants(wv);
  const requetes = xf.map((ligne) => projeter(ligne, wqf));
  const cles = xf.map((ligne) => projeter(ligne, wkf));
  const valeurs = xf.map((ligne) => projeter(ligne, wvf));
  const echelle = 1.0 / racine(taille); // 1 / √4 = 0,5 pour des têtes de 4
  const n = xf.length;
  const scores: (number | null)[][] = [];
  const scoresEchelles: (number | null)[][] = [];
  const poids: number[][] = [];
  const sorties: number[][] = [];
  for (let i = 0; i < n; i++) {
    const visibles = cles.slice(0, i + 1); // le masque causal : les mots 0 à i
    const masques = n - i - 1;
    const bruts = scoresAttention(requetes[i], visibles, 1.0);
    const echelles = scoresAttention(requetes[i], visibles, echelle);
    const p = softmax(echelles);
    scores.push([...bruts, ...new Array<null>(masques).fill(null)]);
    scoresEchelles.push([...echelles, ...new Array<null>(masques).fill(null)]);
    poids.push([...p, ...new Array<number>(masques).fill(0.0)]);
    sorties.push(melangerValeurs(p, valeurs.slice(0, i + 1)));
  }
  return { requetes, cles, valeurs, scores, scoresEchelles, poids, sorties };
}

/** Le détail de chaque tête de l'exemple, dans l'ordre des têtes. */
export function detaillerExemple(exemple: ExempleAttention): DetailTete[] {
  verifierExemple(exemple);
  return exemple.tetes.map((t) => detaillerTete(exemple.x, t.wq, t.wk, t.wv));
}
