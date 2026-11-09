// Les fichiers d'attendus de la Partie 1 que la page d'essai de parité refait,
// chacun sous le nom de son calcul (CALCULS_PARTIE_1, dans parite.ts), en
// chemins depuis la racine du dépôt. Chaque tâche qui ajoute un calcul ajoute
// ici son fichier.
//
// Cette liste ne sert qu'aux attendus de parité. Les mesures et les sorties sont
// dans un module à part (MESURES_PARTIE_1, mesures.ts).
//
// Ce module n'importe rien (ni .json, ni ?raw) : une page le charge sans les
// attendus, et un parcours Playwright peut l'importer.

/** Le fichier d'attendus du Python que refait chaque calcul de la Partie 1. */
export const FICHIERS_PARTIE_1: Readonly<Record<string, string>> = Object.freeze({
  ngrammes: 'projets/1.1-modele-de-langage/tests/attendus.json',
  nettoyeur: 'projets/1.2-donnees/tests/attendus.json',
});

/**
 * Ce que le site ne refait pas dans un fichier d'attendus : il le lit tel quel.
 * Pour chaque fichier, les clés de chaque élément d'une section. Pour 1.1 : les
 * deux perplexités de chaque ordre (section ordres), qui passent par exp et
 * log, dont le dernier chiffre change d'un système à l'autre. Les comparaisons
 * les retirent du fichier (partieRefaite).
 */
export const CLES_NON_REFAITES: Readonly<Record<string, Readonly<Record<string, readonly string[]>>>> = Object.freeze({
  ngrammes: Object.freeze({ ordres: Object.freeze(['perplexite_entrainement', 'perplexite_validation']) }),
});

/**
 * Ce que la page de parité doit retrouver d'un fichier d'attendus : tout le
 * fichier, sans les clés non refaites. Une section ou une clé absente arrête la
 * comparaison : la liste ne doit pas viser ce qui n'existe plus, sans quoi elle
 * ne retirerait rien sans le dire.
 */
export function partieRefaite(nom: string, attendus: Readonly<Record<string, unknown>>): Record<string, unknown> {
  const reste: Record<string, unknown> = { ...attendus };
  for (const [section, cles] of Object.entries(CLES_NON_REFAITES[nom] ?? {})) {
    const elements = reste[section];
    if (!Array.isArray(elements)) {
      throw new Error(
        `La section « ${section} » n’est pas un tableau dans le fichier d’attendus « ${nom} » : ` +
          'retire-la de CLES_NON_REFAITES (src/lib/partie-1/fichiers.ts), ou régénère le fichier.',
      );
    }
    reste[section] = elements.map((element: Record<string, unknown>) => {
      const copie = { ...element };
      for (const cle of cles) {
        if (!Object.hasOwn(copie, cle)) {
          throw new Error(
            `La clé « ${cle} » n’est pas dans la section « ${section} » du fichier d’attendus « ${nom} » : ` +
              'retire-la de CLES_NON_REFAITES (src/lib/partie-1/fichiers.ts), ou régénère le fichier.',
          );
        }
        delete copie[cle];
      }
      return copie;
    });
  }
  return reste;
}
