// Les formats français des nombres, partagés par les démos (mini-modèle,
// attention, calculateur).
//
// Les milliers sont séparés par une espace fine insécable (U+202F) et les
// décimales par une virgule : c'est ce que donne Intl.NumberFormat('fr-FR').
// Ce module n'importe rien : la page peut s'en servir sans rien embarquer
// d'autre (ni le moteur du mini-modèle, ni la liste des prénoms).

const FINE = '\u202F';
const DECIMALES_MAX = 20;

// Un format par nombre de décimales, créé à la première demande.
const formats = new Map<string, Intl.NumberFormat>();

function format(decimales: number, style: 'decimal' | 'percent'): Intl.NumberFormat {
  if (!Number.isInteger(decimales) || decimales < 0 || decimales > DECIMALES_MAX) {
    throw new RangeError(`Le nombre de décimales va de 0 à ${DECIMALES_MAX}, en entier (reçu ${decimales}).`);
  }
  const cle = `${style}:${decimales}`;
  let f = formats.get(cle);
  if (f === undefined) {
    f = new Intl.NumberFormat('fr-FR', { style, minimumFractionDigits: decimales, maximumFractionDigits: decimales });
    formats.set(cle, f);
  }
  return f;
}

function verifierFini(x: number, fonction: string): void {
  if (!Number.isFinite(x)) {
    throw new RangeError(
      `${fonction} : la valeur n'est pas un nombre fini (reçu ${String(x)}). ` +
        "Vérifie le calcul avant de l'afficher : la page ne doit jamais montrer NaN ni ∞.",
    );
  }
}

// Un résultat arrondi à zéro ne garde pas de signe : « 0 », jamais « -0 » ni « -0,000 ».
function sansMoinsZero(texte: string): string {
  return texte.replace(/^[-\u2212](?=[^1-9]*$)/, ''); // trait d'union ou signe moins (U+2212), selon le moteur
}

/** x en français, avec exactement `decimales` décimales : nombre(12345.678, 1) donne « 12 345,7 ». */
export function nombre(x: number, decimales = 0): string {
  verifierFini(x, 'nombre');
  return sansMoinsZero(format(decimales, 'decimal').format(x));
}

/**
 * Une fraction en pourcentage, avec une espace fine avant « % » :
 * pourcent(0.528, 1) donne « 52,8 % ».
 *
 * Intl fait la multiplication par 100 sur la valeur décimale exacte (0,0285
 * donne 2,9 %, quand 0,0285 × 100 donnerait 2,8499… en flottant). Il met
 * selon les moteurs une espace insécable ou une espace fine avant « % » : on
 * pose toujours la fine.
 */
export function pourcent(fraction: number, decimales = 0): string {
  verifierFini(fraction, 'pourcent');
  const texte = format(decimales, 'percent').format(fraction).replace(/\s*%$/, `${FINE}%`);
  return sansMoinsZero(texte);
}

/**
 * Le plus petit nombre de décimales qui écrit x sans rien perdre, au plus
 * max : 0,3 en demande 1, 0,003 en demande 3, 150 aucune. Pour écrire un
 * réglage tel qu'il est : nombre(x, decimalesUtiles(x)).
 */
export function decimalesUtiles(x: number, max = 6): number {
  verifierFini(x, 'decimalesUtiles');
  for (let d = 0; d < max; d++) {
    if (Number(x.toFixed(d)) === x) return d;
  }
  return max;
}

/**
 * Une erreur (une perte) avec trois décimales : « 3,742 ».
 *
 * Une erreur qui a explosé (infinie, ou non numérique) s'écrit « hors
 * échelle », comme le repère de la courbe : jamais NaN ni ∞.
 */
export function formaterPerte(x: number): string {
  return Number.isFinite(x) ? nombre(x, 3) : 'hors échelle';
}
