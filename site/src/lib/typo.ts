// Typographie française : espace fine insécable (U+202F) devant « ; : ! ? »,
// à l'intérieur des guillemets « », et apostrophe courbe (U+2019) entre deux
// lettres. C'est le seul chemin typographique du site : le plugin remark
// l'applique à la prose Markdown et MDX, les composants à leurs props.
// (smartypants ne convertit plus les guillemets ni les apostrophes, voir
// astro.config.mjs.)

const FINE = '\u202F';
const APOSTROPHE = '\u2019';

// Une espace ordinaire (U+0020) ou insécable (U+00A0) juste avant ; : ! ?
const AVANT_PONCTUATION = /[ \u00A0]([;:!?])/g;

// « suivi d'une espace (remplacée) ou collé à un caractère (espace ajoutée).
// \s couvre aussi U+202F : une espace fine déjà en place n'est pas doublée.
const OUVRANT = /«(?:[ \u00A0]|(?=[^\s»]))/g;

// » précédé d'une espace (remplacée) ou collé à un caractère (espace ajoutée).
const FERMANT = /(?:[ \u00A0]|(?<=[^\s«]))»/g;

// Apostrophe droite entre deux lettres : « l'atelier », « aujourd'hui ». Une
// lettre accentuée peut s'écrire lettre + accent combinant (\p{M}). Les autres
// apostrophes droites (« 'a' », « 4'33 ») restent telles quelles.
const APOSTROPHE_DROITE = /(?<=[\p{L}\p{M}])'(?=\p{L})/gu;

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
    .replace(FERMANT, `${FINE}»`)
    .replace(APOSTROPHE_DROITE, APOSTROPHE);
}
