// La géométrie de la courbe de perte (CourbePerte.svelte) : l'échelle, la
// réduction des points et le chemin SVG.
//
// Le chemin ne contient jamais NaN ni Infinity : un point non fini coupe le
// tracé (le suivant recommence par « M »), et une perte au-dessus du haut de
// l'échelle est ramenée au bord, avec horsEchelle = vrai pour que la courbe
// le dise.
//
// Ce module n'importe rien : la page peut s'en servir sans rien embarquer
// d'autre (ni le moteur du mini-modèle, ni la liste des prénoms).

/** Le cadre de la courbe : sa taille (en unités du viewBox) et les valeurs de ses bords. */
export interface Echelle {
  largeur: number;
  hauteur: number;
  /** Le dernier pas, au bord droit (le pas 0 est au bord gauche). */
  xMax: number;
  /** L'erreur au bas du cadre. */
  yMin: number;
  /** L'erreur au haut du cadre. */
  yMax: number;
}

/** Un point de la courbe : un pas, et l'erreur à ce pas. */
export interface Point {
  pas: number;
  perte: number;
}

function exigerPositif(x: number, nom: string): void {
  if (!Number.isFinite(x) || x <= 0) {
    throw new RangeError(`echelleCourbe : ${nom} doit être un nombre fini plus grand que 0 (reçu ${String(x)}).`);
  }
}

/**
 * L'échelle de la courbe : les pas de 0 à pasTotal, l'erreur de 0 à 1,25 fois
 * celle du hasard (ln V). L'erreur de départ, proche du hasard, tient donc
 * dans le cadre avec un peu d'air au-dessus.
 */
export function echelleCourbe(pasTotal: number, perteHasard: number, largeur = 640, hauteur = 280): Echelle {
  exigerPositif(pasTotal, 'pasTotal');
  exigerPositif(perteHasard, 'perteHasard');
  exigerPositif(largeur, 'largeur');
  exigerPositif(hauteur, 'hauteur');
  return { largeur, hauteur, xMax: pasTotal, yMin: 0, yMax: 1.25 * perteHasard };
}

/**
 * La taille des paquets qui ramène nbPas pas à maxPoints points au plus.
 * Calculée sur le nombre total de pas, elle ne change pas pendant
 * l'entraînement : la courbe garde le même lissage du début à la fin.
 */
export function taillePaquet(nbPas: number, maxPoints = 600): number {
  if (!Number.isInteger(maxPoints) || maxPoints < 1) {
    throw new RangeError(`maxPoints doit être un entier d'au moins 1 (reçu ${String(maxPoints)}).`);
  }
  return Math.max(1, Math.ceil(nbPas / maxPoints));
}

/**
 * Les moyennes des pertes par paquets de `taille` pas, chacune posée au
 * milieu de son paquet. La perte du pas p est à l'indice p − 1. Le dernier
 * paquet peut être incomplet. Les valeurs non finies sont ignorées ; un
 * paquet entièrement non fini donne NaN (cheminCourbe y coupe le tracé).
 */
export function moyennesParPaquets(pertes: readonly number[], taille: number): Point[] {
  if (!Number.isInteger(taille) || taille < 1) {
    throw new RangeError(`La taille des paquets doit être un entier d'au moins 1 (reçu ${String(taille)}).`);
  }
  const points: Point[] = [];
  for (let debut = 0; debut < pertes.length; debut += taille) {
    const fin = Math.min(pertes.length, debut + taille);
    let somme = 0;
    let n = 0;
    for (let i = debut; i < fin; i++) {
      const perte = pertes[i];
      if (Number.isFinite(perte)) {
        somme += perte;
        n += 1;
      }
    }
    // Les pas du paquet vont de debut + 1 à fin : son milieu est leur moyenne.
    points.push({ pas: (debut + 1 + fin) / 2, perte: n > 0 ? somme / n : NaN });
  }
  return points;
}

/** Les pertes de chaque pas ramenées à maxPoints points au plus, par moyennes sur des paquets égaux. */
export function reduirePoints(pertes: readonly number[], maxPoints = 600): Point[] {
  return moyennesParPaquets(pertes, taillePaquet(pertes.length, maxPoints));
}

/**
 * Les graduations d'un axe : 0, puis des multiples d'un pas rond (1, 2 ou 5
 * fois une puissance de 10) jusqu'au maximum compris, avec au plus nbMax
 * intervalles. graduations(3000, 3) donne 0, 1 000, 2 000 et 3 000.
 */
export function graduations(max: number, nbMax: number): number[] {
  if (!Number.isFinite(max) || max <= 0) {
    throw new RangeError(`graduations : le maximum doit être un nombre fini plus grand que 0 (reçu ${String(max)}).`);
  }
  if (!Number.isInteger(nbMax) || nbMax < 1) {
    throw new RangeError(`graduations : nbMax doit être un entier d'au moins 1 (reçu ${String(nbMax)}).`);
  }
  const brut = max / nbMax;
  // La puissance de 10 juste sous le pas brut : puissance ≤ brut < 10 × puissance.
  let puissance = 1;
  while (puissance > brut) puissance /= 10;
  while (puissance * 10 <= brut) puissance *= 10;
  // Le plus petit pas rond qui ne fait pas plus de nbMax intervalles jusqu'au maximum.
  const pas = [1, 2, 5, 10].map((m) => m * puissance).find((p) => Math.floor(max / p + 1e-9) <= nbMax) ?? 10 * puissance;
  const valeurs: number[] = [];
  // Number(…toPrecision(12)) efface les restes d'arrondi (0,2 × 3 = 0,6000000000000001).
  for (let k = 0; k * pas <= max * (1 + 1e-12); k++) valeurs.push(Number((k * pas).toPrecision(12)));
  return valeurs;
}

/** Vrai si une perte sort du cadre : non finie (NaN, ±∞), ou au-dessus de yMax. */
const dehors = (perte: number, e: Echelle) => !Number.isFinite(perte) || perte > e.yMax;

/**
 * Le premier pas où l'erreur sort de l'échelle, ou null : une perte non finie
 * (NaN, ±∞) ou au-dessus de yMax, parmi les pertes brutes de chaque pas (le
 * pas p est à l'indice p − 1) et les points de validation.
 *
 * Il se lit sur les pertes brutes, avant toute moyenne : une moyenne par
 * paquets noie un pas qui explose parmi ses voisins, et ignore NaN. Le repère
 * « hors échelle » de la courbe en dépend.
 */
export function sortieDeLEchelle(pertes: readonly number[], validations: readonly Point[], e: Echelle): number | null {
  let premier: number | null = null;
  for (let i = 0; i < pertes.length; i++) {
    if (dehors(pertes[i], e)) {
      premier = i + 1;
      break;
    }
  }
  for (const { pas, perte } of validations) {
    if (Number.isFinite(pas) && dehors(perte, e) && (premier === null || pas < premier)) premier = pas;
  }
  return premier;
}

const borne = (x: number, min: number, max: number) => (x < min ? min : x > max ? max : x);
const coordonnee = (x: number) => x.toFixed(1);

/**
 * Le chemin SVG (attribut d) des points, dans l'échelle e, avec des
 * coordonnées à une décimale.
 *
 * - Un point non fini (pas ou perte) coupe le tracé : le point fini suivant
 *   recommence par « M ».
 * - Une perte au-dessus de yMax est ramenée à yMax, et horsEchelle vaut vrai.
 *   Une perte infinie (+∞) est aussi hors échelle, mais n'entre pas dans le tracé.
 * - Une perte sous yMin est ramenée à yMin, et un pas hors de 0..xMax au bord.
 */
export function cheminCourbe(points: readonly Point[], e: Echelle): { d: string; horsEchelle: boolean } {
  const morceaux: string[] = [];
  let horsEchelle = false;
  let enCours = false;
  for (const { pas, perte } of points) {
    if (perte === Infinity) horsEchelle = true;
    if (!Number.isFinite(pas) || !Number.isFinite(perte)) {
      enCours = false;
      continue;
    }
    if (perte > e.yMax) horsEchelle = true;
    const x = (borne(pas, 0, e.xMax) / e.xMax) * e.largeur;
    const y = e.hauteur - ((borne(perte, e.yMin, e.yMax) - e.yMin) / (e.yMax - e.yMin)) * e.hauteur;
    morceaux.push(`${enCours ? 'L' : 'M'}${coordonnee(x)},${coordonnee(y)}`);
    enCours = true;
  }
  return { d: morceaux.join(''), horsEchelle };
}
