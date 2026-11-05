// La parité de la Partie 0 : refait en TypeScript les attendus des projets 0.x
// dont le jumeau tourne dans le navigateur.
//
// Chacun de ces projets écrit un fichier projets/<projet>/tests/attendus.json :
// des entrées, et ce que le Python en tire. Chaque calcul ci-dessous relit les
// entrées de son fichier (les textes, les mots de départ et les longueurs pour
// le mot suivant ; les vecteurs, les matrices, les départs et les graines pour
// les maths utiles) et refait les sorties avec les fonctions du jumeau. La liste
// des fichiers, sous le nom de leur calcul, est FICHIERS_PARTIE_0 (fichiers.ts).
//
// Les sections que le site ne refait pas (SECTIONS_NON_REFAITES, fichiers.ts :
// softmax et −ln p de 0.2, qui passent par exp et log, et ce qui ne sert qu'en
// Python) ne sont pas écrites par ces calculs : les comparaisons les retirent du
// fichier avant de comparer (partieRefaite).
//
// - les tests Vitest du jumeau lisent le fichier de FICHIERS_PARTIE_0 et le
//   comparent à ces calculs dans Node : un import ci-dessous qui viserait un
//   autre fichier les ferait échouer ;
// - la page d'essai parite-partie-0 (ControleParite.svelte, jeu="partie-0")
//   les fait dans le navigateur, et e2e/parite.spec.ts compare ce qu'elle
//   écrit aux mêmes fichiers, dans Chrome, Firefox et WebKit. C'est la seule
//   façon de voir qu'un moteur JavaScript s'écarte du Python (les minuscules
//   d'Unicode, l'ordre des points de code).
//
// Ce module importe les fichiers d'attendus (.json, par Vite) : un parcours
// Playwright ne peut pas l'importer. Les parcours lisent ces fichiers par
// readFileSync, d'après FICHIERS_PARTIE_0.

import fichierMotSuivant from '../../../../projets/0.1-python/tests/attendus.json';
import fichierMaths from '../../../../projets/0.2-maths/tests/attendus.json';
import { Hasard } from '../mini-modele/calcul';
import type { Attendus } from '../mini-modele/parite';
import {
  cosinus,
  descendre,
  erreur,
  EXEMPLE_COMPTES,
  GRAINE_TIRAGE,
  matriceFoisVecteur,
  norme,
  pasPourAtteindre,
  pente,
  probabilites,
  produitScalaire,
  somme,
  TAUX_DESCENTE,
  tirages,
  tirer,
} from './maths';
import { compterSuivants, decouperMots, generer, predire, premiereReprise, suivantsTries } from './mot-suivant';

export { FICHIERS_PARTIE_0 } from './fichiers';

/** Les entrées d'un texte du fichier d'attendus du mot suivant. */
interface EntreesTexte {
  texte: string;
  suites: { depart: string; longueur: number }[];
}

/** Les attendus du mot suivant (FICHIERS_PARTIE_0['mot-suivant']), refaits ici. */
export function attendusMotSuivant(): Attendus {
  const { textes } = fichierMotSuivant as unknown as { textes: EntreesTexte[] };
  return {
    textes: textes.map(({ texte, suites }) => {
      const mots = decouperMots(texte);
      const suivants = compterSuivants(mots);
      return {
        texte,
        mots,
        suivants: [...suivants].map(([mot, compte]) => [mot, suivantsTries(compte)]),
        // Chaque mot une seule fois, dans l'ordre de sa première apparition (dict.fromkeys en Python).
        predictions: [...new Set(mots)].map((mot) => [mot, predire(suivants, mot)]),
        suites: suites.map(({ depart, longueur }) => {
          const suite = generer(suivants, depart, longueur);
          return { depart, longueur, suite, reprise: premiereReprise(suite) };
        }),
      };
    }),
  };
}

/** Les entrées du fichier d'attendus des maths utiles : tout ce que la page relit, et rien de ce qu'elle refait. */
export interface EntreesMaths {
  vecteurs: { a: number[]; b: number[] }[];
  matrices: { m: number[][]; v: number[] }[];
  descente: { nb_pas: number; seuil: number; cas: { x0: number; taux: number }[] };
  tirage: {
    // Seul leur nombre compte : la page tire elle-même autant de valeurs de new Hasard(graine).
    uniformes: { graine: number; valeurs: readonly unknown[] };
    tirer: { probas: number[]; u: number }[];
    tirages: { n: number; graine: number }[];
  };
}

/**
 * Les sections vecteurs, matrices, descente et tirage du fichier des maths
 * utiles, refaites à partir de ses seules entrées. Les constantes du jumeau
 * (TAUX_DESCENTE, GRAINE_TIRAGE, EXEMPLE_COMPTES) sont écrites telles que le
 * site les connaît : la comparaison vérifie qu'elles sont celles du Python.
 */
export function refaireMaths(entrees: EntreesMaths): Attendus {
  const { vecteurs, matrices, descente, tirage } = entrees;
  const probas = probabilites(EXEMPLE_COMPTES);
  const hasard = new Hasard(tirage.uniformes.graine);
  return {
    vecteurs: vecteurs.map(({ a, b }) => ({
      a,
      b,
      produit_scalaire: produitScalaire(a, b),
      norme_a: norme(a),
      norme_b: norme(b),
      cosinus: cosinus(a, b),
      somme: somme(a, b),
    })),
    // Comme le Python : le résultat, ou le message de l'erreur quand les tailles ne vont pas.
    matrices: matrices.map(({ m, v }) => {
      try {
        return { m, v, resultat: matriceFoisVecteur(m, v), erreur: null };
      } catch (e) {
        return { m, v, resultat: null, erreur: e instanceof Error ? e.message : String(e) };
      }
    }),
    descente: {
      taux: [...TAUX_DESCENTE],
      nb_pas: descente.nb_pas,
      seuil: descente.seuil,
      cas: descente.cas.map(({ x0, taux }) => {
        const positions = descendre(x0, taux, descente.nb_pas);
        return {
          x0,
          taux,
          positions,
          erreurs: positions.map(erreur),
          pentes: positions.map(pente),
          pas_pour_atteindre: pasPourAtteindre(x0, taux, descente.seuil),
        };
      }),
    },
    tirage: {
      graine_tirage: GRAINE_TIRAGE,
      exemple_comptes: EXEMPLE_COMPTES.map(([mot, n]) => [mot, n]),
      probabilites: probas,
      uniformes: { graine: tirage.uniformes.graine, valeurs: tirage.uniformes.valeurs.map(() => hasard.uniforme()) },
      tirer: tirage.tirer.map(({ probas: p, u }) => ({ probas: p, u, indice: tirer(p, u) })),
      tirages: tirage.tirages.map(({ n, graine }) => ({ n, graine, comptes: tirages(probas, n, graine) })),
    },
  };
}

/** Les attendus des maths utiles (FICHIERS_PARTIE_0.maths), sans les sections non refaites, refaits ici. */
export function attendusMaths(): Attendus {
  return refaireMaths(fichierMaths as unknown as EntreesMaths);
}

/** Chaque calcul de parité de la Partie 0, sous le nom de son fichier dans FICHIERS_PARTIE_0. */
export const CALCULS_PARTIE_0: Record<string, () => Attendus> = {
  'mot-suivant': attendusMotSuivant,
  maths: attendusMaths,
};
