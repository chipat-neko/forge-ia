// Les chemins de toutes les clés d'une valeur JSON, pour comparer deux fichiers
// d'attendus clé par clé : une clé en trop ou en moins, même profonde, se lit
// tout de suite dans le message d'échec. Sert à parite.test.ts (Vitest) et à
// e2e/parite.spec.ts (Playwright) : ce module n'importe rien.

/**
 * Chaque chemin de la valeur, trié : « a », « a.c », « a.c[0] », « a.c[0].d »…
 * Les objets donnent leurs clés, les tableaux leurs indices ; un texte, un
 * nombre ou null n'en donne aucun.
 */
export function cheminsDesCles(valeur: unknown): string[] {
  const chemins: string[] = [];
  const parcourir = (v: unknown, chemin: string): void => {
    if (Array.isArray(v)) {
      v.forEach((element, i) => {
        const suite = `${chemin}[${i}]`;
        chemins.push(suite);
        parcourir(element, suite);
      });
    } else if (typeof v === 'object' && v !== null) {
      for (const [cle, element] of Object.entries(v)) {
        const suite = chemin === '' ? cle : `${chemin}.${cle}`;
        chemins.push(suite);
        parcourir(element, suite);
      }
    }
  };
  parcourir(valeur, '');
  return chemins.sort();
}
