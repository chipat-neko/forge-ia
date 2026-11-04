// Le texte du projet 0.1 (projets/0.1-python/donnees/texte.txt), tel quel.
//
// Il vit à part de mot-suivant.ts : l'import ?raw passe par Vite, et un
// parcours Playwright, chargé par Node sans Vite, ne pourrait pas importer un
// module qui le contient. Les parcours lisent ce fichier par readFileSync.

import texte from '../../../../projets/0.1-python/donnees/texte.txt?raw';

/** Le texte de départ de l'atelier : une copie exacte du corpus du chapitre 1.3. */
export const TEXTE_DE_DEPART: string = texte;
