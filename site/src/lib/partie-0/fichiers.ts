// Les fichiers d'attendus de la Partie 0 que la page d'essai de parité refait,
// chacun sous le nom de son calcul (CALCULS_PARTIE_0, dans parite.ts), en
// chemins depuis la racine du dépôt.
//
// C'est la seule liste de ces fichiers : parite.ts, ControleParite.svelte, les
// tests Vitest et e2e/parite.spec.ts la lisent. Ce module n'importe rien (ni
// .json, ni ?raw) : une page le charge sans les attendus, et un parcours
// Playwright peut l'importer.

/** Le fichier d'attendus du Python que refait chaque calcul de la Partie 0. */
export const FICHIERS_PARTIE_0: Readonly<Record<string, string>> = Object.freeze({
  'mot-suivant': 'projets/0.1-python/tests/attendus.json',
});
