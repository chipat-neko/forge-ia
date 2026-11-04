// La parité de la Partie 0 : refait en TypeScript les attendus des projets 0.x
// dont le jumeau tourne dans le navigateur.
//
// Chacun de ces projets écrit un fichier projets/<projet>/tests/attendus.json :
// des entrées, et ce que le Python en tire. Chaque calcul ci-dessous relit les
// entrées de son fichier (les textes, les mots de départ et les longueurs pour
// le mot suivant) et refait toutes les sorties avec les fonctions du jumeau.
// La liste des fichiers, sous le nom de leur calcul, est FICHIERS_PARTIE_0
// (fichiers.ts).
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
import type { Attendus } from '../mini-modele/parite';
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

/** Chaque calcul de parité de la Partie 0, sous le nom de son fichier dans FICHIERS_PARTIE_0. */
export const CALCULS_PARTIE_0: Record<string, () => Attendus> = {
  'mot-suivant': attendusMotSuivant,
};
