// Typographie française : espace fine insécable (U+202F) devant « ; : ! ? »
// et à l'intérieur des guillemets « ».

const FINE = ' ';

// Une espace ordinaire (U+0020) ou insécable (U+00A0) juste avant ; : ! ?
const AVANT_PONCTUATION = /[  ]([;:!?])/g;

// « suivi d'une espace (remplacée) ou collé à un caractère (espace ajoutée).
// \s couvre aussi U+202F : une espace fine déjà en place n'est pas doublée.
const OUVRANT = /«(?:[  ]|(?=[^\s»]))/g;

// » précédé d'une espace (remplacée) ou collé à un caractère (espace ajoutée).
const FERMANT = /(?:[  ]|(?<=[^\s«]))»/g;

/**
 * Applique la typographie française à un texte.
 *
 * Rien n'est ajouté devant ; : ! ? quand il n'y avait pas d'espace : ça
 * protège « 16:9 » et « https:// ». Les guillemets, eux, reçoivent toujours
 * leur espace fine.
 */
export function typographier(texte: string): string {
  return texte
    .replace(AVANT_PONCTUATION, `${FINE}$1`)
    .replace(OUVRANT, `«${FINE}`)
    .replace(FERMANT, `${FINE}»`);
}
