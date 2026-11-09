// Le texte du site, pour le chapitre 1.1 et son atelier.
//
// Il vit à part de ngrammes.ts : les imports ?raw passent par Vite, et un
// parcours Playwright, chargé par Node sans Vite, ne pourrait pas importer un
// module qui les contient. ngrammes.ts prend le texte en argument et reste pur ;
// les parcours lisent les fichiers par readFileSync. Les perplexités du Python
// sont dans perplexites-1-1.ts : l'atelier, qui importe ce module, ne charge
// ainsi pas le fichier d'attendus dans le navigateur.

import texte from '../../../../projets/1.1-modele-de-langage/donnees/texte-du-site.txt?raw';
import { alphabet } from './ngrammes';

/** Le texte du site : une copie exacte de projets/1.1-modele-de-langage/donnees/texte-du-site.txt. */
export const TEXTE_DU_SITE: string = texte;

/** L'alphabet du texte entier (entraînement et validation), comme en Python. */
export const ALPHABET: readonly string[] = Object.freeze(alphabet(TEXTE_DU_SITE));
