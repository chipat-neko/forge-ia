// Ce que le chapitre 1.4 lit du projet 1.4, à la construction : la section residus de ses
// attendus (tests/attendus.json), que le pari « residus » montre sans refaire le calcul.
//
// Il vit à part de paris-1-4.ts : un import .json passe par Vite, et un parcours Playwright,
// chargé par Node sans Vite, ne pourrait pas importer un module qui en contient un (P8). Les
// parcours lisent le même fichier par readFileSync, et projet-1-4.test.ts vérifie que ce module
// en donne bien la section residus. L'atelier n'importe pas ce module.

import attendus from '../../../../projets/1.4-transformer/tests/attendus.json';
import type { ResidusDuPari } from './paris-1-4';

/** Ce que deviennent deux textes qui ne diffèrent que par leur dernier jeton, avec et sans le `x +`. */
export const RESIDUS: ResidusDuPari = attendus.residus as ResidusDuPari;
