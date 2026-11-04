// Les attendus en JSON, des deux côtés de la comparaison.
//
// - cheminsDesCles : les chemins de toutes les clés d'une valeur JSON, pour
//   comparer deux fichiers d'attendus clé par clé (une clé en trop ou en moins,
//   même profonde, se lit tout de suite dans le message d'échec). Sert aux tests
//   de parité (Vitest) et à e2e/parite.spec.ts (Playwright).
// - versJson : l'écriture en JSON des attendus refaits par le site
//   (ControleParite.svelte et les tests Vitest).
//
// Ce module n'importe rien : une page ou un parcours le charge sans rien embarquer d'autre.

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

/**
 * L'objet en JSON, indenté d'une espace comme les fichiers du Python.
 *
 * Refuse ce que le JSON ne sait pas écrire et changerait sans bruit :
 * undefined (la clé disparaîtrait) et les nombres non finis (ils deviendraient null).
 */
export function versJson(valeur: unknown): string {
  return JSON.stringify(
    valeur,
    (cle, v: unknown) => {
      if (v === undefined) {
        throw new TypeError(`versJson : « ${cle} » vaut undefined. Chaque clé des attendus doit avoir une valeur.`);
      }
      if (typeof v === 'number' && !Number.isFinite(v)) {
        throw new TypeError(`versJson : « ${cle} » vaut ${v}. Un flottant des attendus s'écrit en motif (versHex).`);
      }
      return v;
    },
    1,
  );
}
