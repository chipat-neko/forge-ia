// Le comparateur par point de code, partagé par le tokenizer du chapitre 1.3 (bpe.ts)
// et par les prénoms du mini-modèle (mini-modele/donnees.ts).
//
// Ce module n'importe rien : l'utiliser ne charge ni le corpus ni le tokenizer.
// bpe.ts le ré-exporte, donc son interface ne change pas.

/**
 * Compare deux textes par point de code, comme le fait Python.
 *
 * Le « < » de JavaScript compare les unités UTF-16 : il rangerait « 🙂 »
 * (D83D DE42) avant « U+FFFD », alors que son point de code (U+1F642) est plus
 * grand. Un texte qui est le début d'un autre passe avant lui.
 */
export function comparerPointsDeCode(a: string, b: string): number {
  let i = 0;
  while (i < a.length && i < b.length) {
    const pa = a.codePointAt(i) as number;
    const pb = b.codePointAt(i) as number;
    if (pa !== pb) return pa < pb ? -1 : 1;
    // Deux points de code égaux occupent autant d'unités : i vaut pour a et pour b.
    i += pa > 0xffff ? 2 : 1;
  }
  return Math.sign(a.length - b.length);
}
