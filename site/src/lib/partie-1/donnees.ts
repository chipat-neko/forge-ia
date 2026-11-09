// Les données de « ton IA », côté site : le mélange des trois sources, les licences de
// code qu'on garde, et la part mise de côté pour la validation.
//
// Ces valeurs sont celles de forge, le moteur de « ton IA » : le mélange est
// MELANGE_PAR_DEFAUT (projets/forge/forge/donnees/melange.py), la part de validation le
// défaut de est_validation (même fichier), et les licences LICENCES_PERMISSIVES
// (projets/forge/forge/donnees/sources.py). donnees.test.ts lit le texte de ces deux
// fichiers, sans les importer, et vérifie que les valeurs sont les mêmes : si forge change,
// le test échoue tant que ce module ne suit pas.
//
// Ce module n'importe rien : le jumeau du nettoyage (nettoyeur.ts) et le chapitre 1.2 le
// chargent sans charger d'attendus.

/** Les sources, dans l'ordre de lecture et d'affichage. */
export type NomSource = 'web_fr' | 'wikipedia_fr' | 'code_python';

/** Part de chaque source : 75 % de web français, 10 % de Wikipédia française, 15 % de code Python permissif. */
export const MELANGE: Readonly<Record<NomSource, number>> = Object.freeze({
  web_fr: 0.75,
  wikipedia_fr: 0.1,
  code_python: 0.15,
});

/** Les sources dans l'ordre du mélange. */
export const NOMS_DES_SOURCES: readonly NomSource[] = Object.freeze(['web_fr', 'wikipedia_fr', 'code_python']);

/** Les licences de code gardées : celles qui autorisent de réutiliser le code en citant ses auteurs. */
export const LICENCES_PERMISSIVES: readonly string[] = Object.freeze([
  'mit',
  'apache-2.0',
  'bsd-2-clause',
  'bsd-3-clause',
  'isc',
  'unlicense',
  'cc0-1.0',
]);

/** La part des documents mise de côté pour la validation : 0,5 %, soit un document sur 200. */
export const PART_VALIDATION = 0.005;
