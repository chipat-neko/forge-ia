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
  maths: 'projets/0.2-maths/tests/attendus.json',
});

/**
 * Les sections d'un fichier d'attendus que le site ne refait pas : il les lit
 * telles quelles. Pour 0.2 : la pente approchée (section pente) et la règle de
 * la chaîne (section chaine), qui ne servent qu'en Python, puis softmax (section
 * softmax) et −ln p, l'erreur d'une prédiction (section erreur : rien à voir
 * avec la fonction erreur(x) de maths.ts, qui est refaite dans la section
 * descente). Ces deux dernières passent par exp et log, dont le dernier chiffre
 * change d'un système à l'autre. La page de parité ne les écrit pas ; les
 * comparaisons les retirent du fichier (partieRefaite).
 */
export const SECTIONS_NON_REFAITES: Readonly<Record<string, readonly string[]>> = Object.freeze({
  maths: Object.freeze(['pente', 'chaine', 'softmax', 'erreur']),
});

/**
 * Ce que la page de parité doit retrouver d'un fichier d'attendus : tout le
 * fichier, sans ses sections non refaites. Une section non refaite absente du
 * fichier arrête la comparaison : la liste ne doit pas viser une section qui
 * n'existe plus, sans quoi elle ne retirerait rien sans le dire.
 */
export function partieRefaite(nom: string, attendus: Readonly<Record<string, unknown>>): Record<string, unknown> {
  const reste: Record<string, unknown> = { ...attendus };
  for (const section of SECTIONS_NON_REFAITES[nom] ?? []) {
    if (!Object.hasOwn(reste, section)) {
      throw new Error(
        `La section « ${section} » n’est pas dans le fichier d’attendus « ${nom} » : ` +
          'retire-la de SECTIONS_NON_REFAITES (src/lib/partie-0/fichiers.ts), ou régénère le fichier.',
      );
    }
    delete reste[section];
  }
  return reste;
}
