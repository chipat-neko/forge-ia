// Les paris du chapitre 0.2, « Les maths utiles », les réglages de ses trois
// figures (FigureVecteurs, FigureDescente et FigureTirage) et les phrases
// qu'elles écrivent.
//
// Les bonnes réponses et tous les nombres affichés sont calculés par le jumeau
// exact du Python (maths.ts), jamais écrits à la main. Si le jumeau change et
// qu'une phrase de la page devient fausse, la construction s'arrête
// (« Exemple devenu faux : … »).
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* (B1) : les parcours de test
// l'importent pour calculer ce que les figures doivent afficher. Les fonctions
// qui lisent les attendus du Python (la règle de la chaîne, softmax, −ln p et
// le pari « erreur ») les reçoivent en argument : le MDX les importe, les
// parcours les lisent sur le disque. Ces valeurs passent par exp et log, dont
// le dernier chiffre peut changer d'un système à l'autre : elles sont
// seulement mises en forme, jamais recalculées ici.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { decimalesUtiles, nombre, pourcent } from '../nombres';
import {
  cosinus,
  descendre,
  erreur,
  EXEMPLE_COMPTES,
  GRAINE_TIRAGE,
  matriceFoisVecteur,
  norme,
  pasPourAtteindre,
  pente,
  probabilites,
  produitScalaire,
  TAUX_DESCENTE,
  tirages,
} from './maths';

const FINE = '\u202F';
/** Le signe moins de la typographie (U+2212), plus long que le trait d'union. */
const MOINS = '\u2212';
/** L'espace insécable ordinaire (U+00A0), entre les coordonnées d'un vecteur. */
const INSECABLE = '\u00A0';

const exiger = exigeur('src/lib/partie-0/paris-0-2.ts et le texte des paris et des figures du chapitre 0.2');

/** Un vecteur du plan : deux nombres. */
export type Vecteur = readonly [number, number];

// ---------- Les nombres écrits ----------

/**
 * x en français, avec `decimales` décimales et le signe moins U+2212 :
 * ecrireNombre(-3.072, 3) donne « −3,072 ». Jamais « −0 » : un résultat
 * arrondi à zéro perd son signe (nombre() s'en charge).
 */
export function ecrireNombre(x: number, decimales = 0): string {
  return nombre(x, decimales).replace(/^-/, MOINS);
}

/** Un réglage tel qu'il est, sans zéro inutile : « 0,1 », « 1,05 », « −1,5 », « 8 ». */
export function ecrireReglage(x: number): string {
  return ecrireNombre(x, decimalesUtiles(x));
}

/** Un vecteur entre parenthèses : « (2, −1) », qui ne se coupe pas en fin de ligne (espace insécable après la virgule). */
export function ecrireVecteur(v: readonly number[]): string {
  return `(${v.map((x) => ecrireNombre(x)).join(`,${INSECABLE}`)})`;
}

// ---------- La figure des vecteurs ----------

/** Les coordonnées réglables des deux vecteurs : des entiers de −4 à 4. */
export const COORDONNEE_MIN = -4;
export const COORDONNEE_MAX = 4;
/** Le quadrillage du dessin va de −DEMI_GRILLE à DEMI_GRILLE sur chaque axe. */
export const DEMI_GRILLE = 5;
/** Les vecteurs à l'arrivée : a = (3, 1) et b = (1, 2). */
export const A_DEPART: Vecteur = Object.freeze([3, 1] as const);
export const B_DEPART: Vecteur = Object.freeze([1, 2] as const);

/** Un facteur d'un produit : entre parenthèses s'il est négatif, « 2 × (−1) ». */
function facteur(x: number): string {
  return x < 0 ? `(${ecrireNombre(x)})` : ecrireNombre(x);
}

/** Une longueur ou un cosinus : sans décimale s'il tombe juste, avec deux sinon. */
function ecrireArrondi(x: number): string {
  return Number.isInteger(x) ? ecrireNombre(x) : ecrireNombre(x, 2);
}

/** Les termes d'un produit scalaire : « 3 × 1 + 1 × 2 ». */
function termesDuProduit(a: readonly number[], b: readonly number[]): string {
  return a.map((x, i) => `${facteur(x)} × ${facteur(b[i])}`).join(' + ');
}

/** Le produit scalaire, terme à terme : « a · b = 3 × 1 + 1 × 2 = 5 ». */
export function texteScalaire(a: readonly number[], b: readonly number[]): string {
  return `a · b = ${termesDuProduit(a, b)} = ${ecrireNombre(produitScalaire(a, b))}`;
}

/** L'ouverture du chapitre : « (3, 1) · (1, 2) = 5 », les vecteurs de la figure à l'arrivée. */
export function texteOuverture(): string {
  return `${ecrireVecteur(A_DEPART)} · ${ecrireVecteur(B_DEPART)} = ${ecrireNombre(produitScalaire(A_DEPART, B_DEPART))}`;
}

/**
 * Ce que le cosinus dit de la direction des deux vecteurs. Les seuils sont
 * ceux de la tâche : au-dessus de 0,9, de 0,3 à 0,9, de −0,3 à 0,3 (bornes
 * exclues), de −0,9 à −0,3, et sous −0,9.
 */
export function directionSelonCosinus(c: number): string {
  if (c > 0.9) return 'presque la même direction';
  if (c >= 0.3) return 'à peu près la même direction';
  if (c > -0.3) return 'presque perpendiculaires';
  if (c >= -0.9) return 'des directions plutôt opposées';
  return 'des directions opposées';
}

/** Vrai si le vecteur est nul : il n'a pas de direction. */
export function estNul(v: readonly number[]): boolean {
  return norme(v) === 0;
}

/** Le message d'un vecteur nul (a, b ou les deux), ou null si aucun ne l'est. */
export function messageVecteurNul(a: readonly number[], b: readonly number[]): string | null {
  const fin = `pas de direction, le cosinus n’existe pas.`;
  if (estNul(a) && estNul(b)) return `a et b sont nuls${FINE}: ils n’ont ${fin}`;
  if (estNul(a)) return `a est nul${FINE}: il n’a ${fin}`;
  if (estNul(b)) return `b est nul${FINE}: il n’a ${fin}`;
  return null;
}

/**
 * Le cosinus et ce qu'il dit : « cos = 5 ÷ (3,16 × 2,24) = 0,71 : à peu près
 * la même direction ». Un vecteur nul donne son message.
 *
 * Les cas exacts se décident sur les coordonnées entières, jamais sur le
 * cosinus calculé (√2 × √8 ne fait pas exactement 4 en flottants) : produit
 * scalaire nul, les vecteurs sont perpendiculaires (cos = 0) ; produit en croix
 * nul (a₁ × b₂ − a₂ × b₁), ils sont sur une même droite, dans la même
 * direction (cos = 1) ou dans des directions opposées (cos = −1). Sinon, les
 * longueurs et le cosinus sont arrondis à deux décimales, et la direction se
 * lit sur le cosinus affiché, selon les seuils : le texte et le nombre disent
 * toujours la même chose.
 */
export function texteCosinus(a: readonly number[], b: readonly number[]): string {
  const c = cosinus(a, b);
  if (c === null) return messageVecteurNul(a, b)!;
  const scalaire = produitScalaire(a, b);
  const entiers = [...a, ...b].every(Number.isInteger);
  const enCroix = a.length === 2 && b.length === 2 ? a[0] * b[1] - a[1] * b[0] : null;
  let affiche: string;
  let direction: string;
  if (entiers && scalaire === 0) {
    affiche = ecrireNombre(0);
    direction = 'perpendiculaires';
  } else if (entiers && enCroix === 0) {
    affiche = ecrireNombre(Math.sign(scalaire));
    direction = scalaire > 0 ? 'la même direction' : 'des directions opposées';
  } else {
    affiche = ecrireArrondi(c);
    direction = directionSelonCosinus(Number(affiche.replace(MOINS, '-').replace(',', '.')));
  }
  return (
    `cos = ${ecrireNombre(scalaire)} ÷ (${ecrireArrondi(norme(a))} × ${ecrireArrondi(norme(b))}) = ` +
    `${affiche}${FINE}: ${direction}`
  );
}

/** Le défi de la figure : a · b = 0, avec deux vecteurs non nuls. */
export function perpendiculaires(a: readonly number[], b: readonly number[]): boolean {
  return !estNul(a) && !estNul(b) && produitScalaire(a, b) === 0;
}

/** Ce que la figure affiche quand le défi est réussi. */
export const DEFI_VECTEURS_REUSSI = `Défi réussi${FINE}: a · b = 0, a et b sont perpendiculaires.`;

// ---------- La figure de la descente ----------

/** Le départ x0 : de −2 à 8, par demi-unité, 0 à l'arrivée. */
export const X0_MIN = -2;
export const X0_MAX = 8;
export const X0_PAS = 0.5;
export const X0_DEPART = 0;
/** Le taux à l'arrivée : 0,1, et son rang dans TAUX_DESCENTE (le réglage de la figure). */
export const TAUX_DEPART = 0.1;
export const INDICE_TAUX_DEPART = TAUX_DESCENTE.indexOf(TAUX_DEPART);
exiger(INDICE_TAUX_DEPART >= 0, `le taux de départ ${TAUX_DEPART} n’est pas dans TAUX_DESCENTE`);

/** Le fond de la courbe : là où la pente s'annule et où l'erreur est la plus petite. */
export const FOND = 3;
exiger(pente(FOND) === 0 && erreur(FOND) < erreur(FOND - X0_PAS) && erreur(FOND) < erreur(FOND + X0_PAS), 'le fond de l’erreur n’est plus en x = 3');

/** Une position à plus de ECART_EXPLOSION du fond arrête la descente : elle explose. */
export const ECART_EXPLOSION = 1000;
/** La figure s'arrête à PAS_MAX pas : assez pour voir où va la descente, à chaque taux. */
export const PAS_MAX = 50;

/** Ce que la figure dit quand la descente explose. */
export const MESSAGE_EXPLOSION = `x est parti à plus de ${nombre(ECART_EXPLOSION)} du fond${FINE}: ce taux fait exploser la descente.`;

/** Vrai si x est parti à plus de ECART_EXPLOSION du fond. */
export function explose(x: number): boolean {
  return Math.abs(x - FOND) > ECART_EXPLOSION;
}

/**
 * Les positions de la descente, comme descendre(x0, taux, nbPas), au plus
 * PAS_MAX pas, et arrêtées à la première qui explose : la figure ne calcule
 * jamais au-delà, et n'écrit donc jamais ni Infinity ni NaN.
 */
export function cheminDeDescente(x0: number, taux: number, nbPas: number): number[] {
  const positions = descendre(x0, taux, Math.min(nbPas, PAS_MAX));
  const fin = positions.findIndex(explose);
  return fin === -1 ? positions : positions.slice(0, fin + 1);
}

/** La ligne d'un pas : « Pas 3 : x = 1,464, erreur = 3,359, pente = −3,072. » */
export function lignePas(n: number, x: number): string {
  return `Pas ${n}${FINE}: x = ${ecrireNombre(x, 3)}, erreur = ${ecrireNombre(erreur(x), 3)}, pente = ${ecrireNombre(pente(x), 3)}.`;
}

/**
 * La phrase de la pente au pas 0 : « En x = 0, la pente vaut 2 × (0 − 3) = −6 :
 * la courbe descend vers la droite. » x est un réglage de la figure (un
 * demi-entier) : la pente tombe juste.
 */
export function phrasePente(x: number): string {
  const p = pente(x);
  const sens =
    p < 0 ? 'la courbe descend vers la droite.' : p > 0 ? 'la courbe monte vers la droite.' : 'la courbe est à plat, c’est le fond.';
  const ecrit = ecrireReglage(x);
  return `En x = ${ecrit}, la pente vaut 2 × (${ecrit} ${MOINS} ${ecrireNombre(FOND)}) = ${ecrireReglage(p)}${FINE}: ${sens}`;
}

/**
 * La ligne d'état de la figure, pour ses positions : la phrase de la pente au
 * pas 0, le message de l'explosion, ou la ligne du dernier pas (avec la fin de
 * la figure à PAS_MAX pas).
 */
export function etatDescente(positions: readonly number[]): string {
  const n = positions.length - 1;
  const x = positions[n];
  if (explose(x)) return MESSAGE_EXPLOSION;
  if (n === 0) return phrasePente(x);
  const ligne = lignePas(n, x);
  return n >= PAS_MAX ? `${ligne} La figure s’arrête à ${PAS_MAX} pas${FINE}: recommence, ou change un réglage.` : ligne;
}

// ---------- La figure des tirages ----------

/** Les nombres de tirages réglables, et le réglage à l'arrivée : 100 tirages. */
export const NOMBRES_DE_TIRAGES: readonly number[] = Object.freeze([10, 100, 1000, 10000, 100000]);
export const INDICE_TIRAGES_DEPART = 1;

/** Une ligne du tableau des tirages : « fer : 60 % attendu, 58 sur 100 tirés (58 %) ». */
export interface LigneTirage {
  nom: string;
  proba: number;
  compte: number;
  /** « 60 % attendu » */
  attendu: string;
  /** « 58 sur 100 tirés (58 %) » */
  tires: string;
}

/**
 * Les n tirages de la graine, issue par issue (EXEMPLE_COMPTES). La fréquence
 * tirée a juste assez de décimales pour être exacte : aucune sur 100 tirages,
 * trois sur 100 000 (60,072 %).
 */
export function resultatsDesTirages(n: number, graine: number): LigneTirage[] {
  const probas = probabilites(EXEMPLE_COMPTES);
  const comptes = tirages(probas, n, graine);
  const decimales = Math.max(0, String(n).length - 3);
  // Les probabilités de l'exemple tombent sur des pourcentages entiers (6 sur 10…) : « 60 % » les dit exactement.
  exiger(
    probas.every((p) => Math.abs(p * 100 - Math.round(p * 100)) < 1e-9),
    'une probabilité de l’exemple ne tombe plus sur un pourcentage entier',
  );
  return EXEMPLE_COMPTES.map(([nom], i) => ({
    nom,
    proba: probas[i],
    compte: comptes[i],
    attendu: `${pourcent(probas[i])} attendu`,
    tires: `${nombre(comptes[i])} sur ${nombre(n)} tirés (${pourcent(comptes[i] / n, decimales)})`,
  }));
}

// ---------- Les paris ----------

/** Les vecteurs du pari « scalaire ». */
export const VECTEURS_DU_PARI: readonly [Vecteur, Vecteur] = Object.freeze([
  Object.freeze([2, 1] as const),
  Object.freeze([-1, 2] as const),
]);

/**
 * Le pari « Que vaut (2, 1) · (−1, 2) ? » : 0, calculé par le jumeau. Les deux
 * autres choix sont des distracteurs fixes, qui ne doivent pas tomber sur le
 * bon résultat.
 */
export function choixProduitScalaire(): Choix[] {
  const [a, b] = VECTEURS_DU_PARI;
  const juste = produitScalaire(a, b);
  const valeurs = [juste, 3, 4];
  exiger(new Set(valeurs).size === 3, 'un distracteur du pari sur le produit scalaire tombe sur le bon résultat');
  return valeurs.map((v) => ({ texte: ecrireNombre(v), juste: v === juste }));
}

/** La matrice du pari « formes » : 3 lignes et 4 colonnes. */
export const MATRICE_DU_PARI: readonly (readonly number[])[] = Object.freeze([
  Object.freeze([1, 0, 2, 1]),
  Object.freeze([0, 1, 1, 0]),
  Object.freeze([2, 1, 0, 1]),
]);

/**
 * Le pari « Une matrice de 3 lignes et 4 colonnes multiplie un vecteur de
 * combien de nombres ? » : autant que de colonnes. Le jumeau le confirme : un
 * vecteur de 4 nombres passe, un vecteur de 3 est refusé. Les deux autres
 * choix sont les erreurs courantes : le nombre de lignes, et leur produit.
 */
export function choixFormeMatrice(): Choix[] {
  const lignes = MATRICE_DU_PARI.length;
  const colonnes = MATRICE_DU_PARI[0].length;
  exiger(
    MATRICE_DU_PARI.every((l) => l.length === colonnes),
    'les lignes de la matrice du pari n’ont pas toutes la même longueur',
  );
  exiger(
    matriceFoisVecteur(MATRICE_DU_PARI, new Array<number>(colonnes).fill(1)).length === lignes,
    `la matrice du pari ne multiplie pas un vecteur de ${colonnes} nombres`,
  );
  let refuse = false;
  try {
    matriceFoisVecteur(MATRICE_DU_PARI, new Array<number>(lignes).fill(1));
  } catch {
    refuse = true;
  }
  exiger(refuse, `la matrice du pari accepte un vecteur de ${lignes} nombres, autant que ses lignes`);
  const valeurs = [lignes, colonnes, lignes * colonnes];
  exiger(new Set(valeurs).size === 3, 'deux choix du pari sur les formes ont le même nombre');
  return valeurs.map((v) => ({ texte: nombre(v), juste: v === colonnes }));
}

/** Le point du pari « pente ». */
export const X_DU_PARI_PENTE = 0;

/** Le pari « En x = 0, la pente est-elle négative, nulle ou positive ? », par le signe de pente(0). */
export function choixPente(): Choix[] {
  const p = pente(X_DU_PARI_PENTE);
  return [
    { texte: 'Négative', juste: p < 0 },
    { texte: 'Nulle', juste: p === 0 },
    { texte: 'Positive', juste: p > 0 },
  ];
}

/** Le seuil des paris sur le taux : l'erreur passe sous 1,01, à un centième du fond. */
export const SEUIL_DU_PARI = 1.01;
/** Le taux du pari « taux-moitie ». */
export const TAUX_MOITIE = 0.5;
/** Le taux du pari « taux-grand », et la longueur de sa descente. */
export const TAUX_GRAND = 1.05;
export const NB_PAS_DU_PARI = 30;

/**
 * Le pari « Au taux 0,5, en combien de pas l'erreur passe-t-elle sous 1,01 ? »,
 * depuis x = 0 : le nombre de pas du jumeau (1), celui du taux de départ de la
 * figure (16), et « Jamais ».
 */
export function choixTauxMoitie(): Choix[] {
  const juste = pasPourAtteindre(X0_DEPART, TAUX_MOITIE, SEUIL_DU_PARI);
  const auDepart = pasPourAtteindre(X0_DEPART, TAUX_DEPART, SEUIL_DU_PARI);
  exiger(juste !== null, `au taux ${TAUX_MOITIE}, l’erreur ne passe jamais sous ${SEUIL_DU_PARI}`);
  exiger(auDepart !== null && auDepart !== juste, `au taux ${TAUX_DEPART}, le nombre de pas n’est plus un distracteur`);
  return [
    { texte: nombre(juste!), juste: true },
    { texte: nombre(auDepart!), juste: false },
    { texte: 'Jamais', juste: false },
  ];
}

/**
 * Ce que fait la descente au taux 1,05, depuis x = 0, pendant 30 pas : ses
 * positions, et la distance de chacune au fond.
 */
export function faitsTauxGrand(): { positions: number[]; distances: number[] } {
  const positions = descendre(X0_DEPART, TAUX_GRAND, NB_PAS_DU_PARI);
  return { positions, distances: positions.map((x) => Math.abs(x - FOND)) };
}

/**
 * Le pari « Au taux 1,05, que fait x pendant 30 pas ? ». Chaque choix a sa
 * condition exacte : x arrive (l'erreur passe sous le seuil), x oscille
 * toujours à la même distance du fond (ce que fait le taux 1,0), ou x
 * s'éloigne du fond à chaque pas. Au taux 1,05, x change bien de côté à chaque
 * pas, mais de plus en plus loin : « oscille », seul, aurait été vrai aussi,
 * d'où « toujours à la même distance ». Une garde exige exactement un choix
 * juste.
 */
export function choixTauxGrand(): Choix[] {
  const { distances } = faitsTauxGrand();
  const arrive = pasPourAtteindre(X0_DEPART, TAUX_GRAND, SEUIL_DU_PARI, NB_PAS_DU_PARI) !== null;
  const memeDistance = distances.every((d) => d === distances[0]);
  const eloigne = distances.every((d, n) => n === 0 || d > distances[n - 1]);
  const choix = [
    { texte: 'Il arrive plus vite', juste: arrive },
    { texte: 'Il oscille autour du fond, toujours à la même distance', juste: memeDistance },
    { texte: "Il s'éloigne du fond à chaque pas", juste: eloigne },
  ];
  exiger(
    choix.filter((c) => c.juste).length === 1,
    `au taux ${TAUX_GRAND}, la descente n’est pas exactement dans un des trois cas du pari`,
  );
  return choix;
}

/** Le nombre de tirages du pari « tirage ». */
export const N_DU_PARI_TIRAGE = 10;

/**
 * Les faits du pari « tirage » : la première issue (« fer »), sa probabilité,
 * le compte attendu en moyenne sur 10 tirages (6), et le compte tiré avec la
 * graine de la figure.
 */
export function faitsDuPariTirage(): { nom: string; proba: number; n: number; attendu: number; compte: number } {
  const probas = probabilites(EXEMPLE_COMPTES);
  const [nom] = EXEMPLE_COMPTES[0];
  const attendu = probas[0] * N_DU_PARI_TIRAGE;
  exiger(Number.isInteger(attendu), `« ${nom} » n’est pas attendu un nombre entier de fois sur ${N_DU_PARI_TIRAGE} tirages`);
  const compte = tirages(probas, N_DU_PARI_TIRAGE, GRAINE_TIRAGE)[0];
  return { nom, proba: probas[0], n: N_DU_PARI_TIRAGE, attendu, compte };
}

/**
 * Le pari « Sur 10 tirages, « fer » (60 %) sort-il exactement 6 fois ? ». Le
 * juste dit le compte tiré avec GRAINE_TIRAGE. S'il valait 6, le pari ne dirait
 * plus rien : il faudrait changer GRAINE_TIRAGE en Python (tirage.py) et en
 * TypeScript (maths.ts), puis régénérer les attendus.
 */
export function choixTirage(): Choix[] {
  const { nom, attendu, compte } = faitsDuPariTirage();
  exiger(
    compte !== attendu,
    `avec la graine ${GRAINE_TIRAGE}, « ${nom} » sort exactement ${attendu} fois sur ${N_DU_PARI_TIRAGE} : ` +
      'change GRAINE_TIRAGE dans projets/0.2-maths/maths_utiles/tirage.py et dans maths.ts, puis régénère les attendus',
  );
  return [
    { texte: 'Oui, forcément', juste: false },
    { texte: `Pas forcément : ici, ${nombre(compte)} fois`, juste: compte !== attendu },
    { texte: `Jamais ${nombre(attendu)} fois`, juste: false },
  ];
}

// ---------- La matrice de l'étape 2 ----------

/** L'exemple de l'étape 2 : la matrice [[1, 2, 3], [0, 1, 0]], fois le vecteur [1, 1, 1]. */
export const MATRICE_EXEMPLE: readonly (readonly number[])[] = Object.freeze([
  Object.freeze([1, 2, 3]),
  Object.freeze([0, 1, 0]),
]);
export const VECTEUR_EXEMPLE: readonly number[] = Object.freeze([1, 1, 1]);

/**
 * Le tableau de « matrice fois vecteur », une ligne par ligne de la matrice :
 * la ligne, son produit scalaire avec le vecteur terme à terme, et la case du
 * résultat (matriceFoisVecteur, le jumeau). Une ligne qui ne va pas avec le
 * vecteur arrête tout, avec le message du jumeau.
 */
export function tableauMatrice(m: readonly (readonly number[])[], v: readonly number[]): string[][] {
  const resultat = matriceFoisVecteur(m, v);
  return m.map((ligne, i) => [ecrireVecteur(ligne), termesDuProduit(ligne, v), ecrireNombre(resultat[i])]);
}

// ---------- Les valeurs du Python : la pente approchée, la chaîne, softmax et −ln p ----------

/**
 * Une pente approchée, avec juste assez de décimales pour qu'elle ne se
 * confonde pas avec la pente exacte : l'écart doit dépasser un demi-chiffre de
 * la dernière décimale. −6,000000000838… face à −6 s'écrit « −6,000000001 »,
 * 11,9999999999009… face à 12, « 11,9999999999 ».
 */
export function ecrireApprochee(approchee: number, exacte: number): string {
  const ecart = Math.abs(approchee - exacte);
  for (let d = 0; d <= 15; d++) {
    if (ecart > 0.5 * 10 ** -d) {
      const texte = ecrireNombre(approchee, d);
      exiger(texte !== ecrireNombre(exacte, d), `la pente approchée ${texte} s’écrit comme la pente exacte`);
      return texte;
    }
  }
  return ecrireNombre(approchee, decimalesUtiles(approchee));
}

/** La section « chaine » des attendus : h(x) = (2x + 1)² en x, sa pente exacte et sa pente approchée. */
export interface ChaineAttendue {
  x: number;
  h: number;
  exacte: number;
  approchee: number;
}

/** La pente de f(x) = 2x + 1, l'opération intérieure de la règle de la chaîne. */
const PENTE_INTERIEURE = 2;

/**
 * Ce que dit l'étape 5 de h(x) = g(f(x)), avec f(x) = 2x + 1 et g(u) = u² :
 * u = f(x), h = u², la pente de g en u (2u), celle de f (2), leur produit (la
 * pente exacte des attendus) et la pente approchée de Python. Des entiers ou
 * des demi-entiers : ces vérifications tombent juste.
 */
export function faitsChaine(c: ChaineAttendue): {
  x: string;
  u: string;
  h: string;
  penteExterieur: string;
  penteInterieur: string;
  exacte: string;
  approchee: string;
} {
  const u = PENTE_INTERIEURE * c.x + 1;
  const penteExterieur = 2 * u;
  exiger(c.h === u * u, `h(${c.x}) vaut ${c.h} dans les attendus, et non (2x + 1)² = ${u * u}`);
  exiger(
    c.exacte === penteExterieur * PENTE_INTERIEURE,
    `la pente exacte des attendus (${c.exacte}) n’est plus 2u × 2 = ${penteExterieur * PENTE_INTERIEURE}`,
  );
  exiger(Math.abs(c.approchee - c.exacte) < 1e-6, 'la pente approchée de la chaîne s’éloigne de la pente exacte');
  return {
    x: ecrireReglage(c.x),
    u: ecrireNombre(u),
    h: ecrireNombre(c.h),
    penteExterieur: ecrireNombre(penteExterieur),
    penteInterieur: ecrireNombre(PENTE_INTERIEURE),
    exacte: ecrireNombre(c.exacte),
    approchee: ecrireApprochee(c.approchee, c.exacte),
  };
}

/** Une ligne de la section « softmax » des attendus. */
export interface SoftmaxAttendu {
  scores: readonly number[];
  temperature: number;
  probabilites: readonly number[];
}

/** La somme d'une liste, de gauche à droite. */
function total(valeurs: readonly number[]): number {
  let s = 0;
  for (const v of valeurs) s += v;
  return s;
}

/**
 * Le tableau softmax de l'étape 7 : une colonne par mot de l'exemple de
 * l'étape 6 (« fer », « métal », « feu »), avec son score, et une ligne par
 * température, les probabilités en pourcentages à une décimale.
 *
 * Les gardes vérifient ce que dit le texte : les mêmes scores sur chaque
 * ligne, rangés du plus grand au plus petit ; des probabilités dans le même
 * ordre, de somme 1 ; des températures sous 1, à 1 et au-dessus, en ordre
 * croissant ; et, quand la température monte, le plus grand score perd du
 * terrain et le plus petit en gagne.
 */
export function tableauSoftmax(softmax: readonly SoftmaxAttendu[]): { colonnes: string[]; lignes: string[][] } {
  exiger(softmax.length >= 2, 'la section « softmax » des attendus a moins de deux températures');
  const scores = softmax[0].scores;
  exiger(scores.length === EXEMPLE_COMPTES.length, `il faut un score par mot de l’exemple (${EXEMPLE_COMPTES.length})`);
  exiger(
    scores.every((s, i) => i === 0 || s < scores[i - 1]),
    'les scores de softmax ne sont plus rangés du plus grand au plus petit',
  );
  for (const [n, ligne] of softmax.entries()) {
    const t = ecrireReglage(ligne.temperature);
    exiger(
      ligne.scores.length === scores.length && ligne.scores.every((s, i) => s === scores[i]),
      `à la température ${t}, les scores ne sont plus ceux des autres lignes`,
    );
    exiger(ligne.probabilites.length === scores.length, `à la température ${t}, il manque des probabilités`);
    exiger(Math.abs(total(ligne.probabilites) - 1) < 1e-9, `à la température ${t}, les probabilités ne font plus 1`);
    // « Chaque ligne fait 100 % » : aussi pour le lecteur qui additionne les pourcentages affichés, à une décimale.
    exiger(
      total(ligne.probabilites.map((p) => Math.round(p * 1000))) === 1000,
      `à la température ${t}, les pourcentages arrondis ne font plus 100,0 %`,
    );
    exiger(
      ligne.probabilites.every((p, i) => p > 0 && (i === 0 || p < ligne.probabilites[i - 1])),
      `à la température ${t}, les probabilités ne suivent plus l’ordre des scores`,
    );
    if (n > 0) {
      const avant = softmax[n - 1];
      exiger(ligne.temperature > avant.temperature, 'les températures de softmax ne sont plus en ordre croissant');
      exiger(
        ligne.probabilites[0] < avant.probabilites[0] && ligne.probabilites.at(-1)! > avant.probabilites.at(-1)!,
        `en passant à la température ${t}, les probabilités ne se rapprochent plus`,
      );
    }
  }
  exiger(
    softmax[0].temperature < 1 && softmax.some((l) => l.temperature === 1) && softmax.at(-1)!.temperature > 1,
    'les températures de softmax ne vont plus de moins de 1 à plus de 1, en passant par 1',
  );
  return {
    colonnes: EXEMPLE_COMPTES.map(([nom], i) => `«${FINE}${nom}${FINE}», score ${ecrireReglage(scores[i])}`),
    lignes: softmax.map((l) => [ecrireReglage(l.temperature), ...l.probabilites.map((p) => pourcent(p, 1))]),
  };
}

/** Une ligne de la section « erreur » des attendus : p, et l'erreur −ln p calculée par Python. */
export interface ErreurAttendue {
  p: number;
  erreur: number;
}

/**
 * Le tableau −ln p de l'étape 7 : p, « une chance sur » 1 ÷ p, et l'erreur à
 * trois décimales. −ln 1 vaut −0.0 en Python : nombre() l'écrit « 0,000 »,
 * jamais « −0 ».
 *
 * Les gardes vérifient ce que dit le texte : p = 1 donne une erreur nulle,
 * chaque p est une chance sur un nombre entier, et quand p baisse, l'erreur
 * monte. La valeur affichée reste celle de Python.
 */
export function tableauErreur(erreurs: readonly ErreurAttendue[]): string[][] {
  exiger(erreurs.length > 0 && erreurs[0].p === 1 && erreurs[0].erreur === 0, 'p = 1 ne donne plus une erreur nulle');
  for (const [n, e] of erreurs.entries()) {
    exiger(e.p > 0 && e.p <= 1 && Number.isInteger(1 / e.p), `p = ${e.p} n’est pas une chance sur un nombre entier`);
    exiger(Math.abs(e.erreur + Math.log(e.p)) < 1e-12, `l’erreur des attendus pour p = ${e.p} n’est pas −ln p`);
    if (n > 0) {
      exiger(e.p < erreurs[n - 1].p && e.erreur > erreurs[n - 1].erreur, 'l’erreur ne grandit plus quand la chance baisse');
    }
  }
  return erreurs.map((e) => [ecrireReglage(e.p), nombre(1 / e.p), ecrireNombre(e.erreur, 3)]);
}

/**
 * Le pari « Si le modèle ne donne qu'une chance sur 40 à la bonne lettre, son
 * erreur vaut… ». V est le vocabulaire du mini-modèle
 * (etatInitial('complet').tailleVocabulaire, 40) : un modèle qui devine au
 * hasard donne 1/V à chaque caractère. Le juste est l'erreur des attendus pour
 * p = 1/V, à trois décimales (ln 40, « 3,689 ») ; les deux autres choix sont la
 * chance elle-même et V. Si les attendus n'ont plus p = 1/V, la construction
 * s'arrête : le texte dirait un nombre que le Python n'a pas calculé.
 */
export function choixErreur(erreurs: readonly ErreurAttendue[], tailleVocabulaire: number): Choix[] {
  const v = tailleVocabulaire;
  exiger(Number.isInteger(v) && v >= 2, `le vocabulaire du mini-modèle a ${v} caractères${FINE}: il en faut au moins 2`);
  const p = 1 / v;
  const ligne = erreurs.find((e) => e.p === p);
  exiger(
    ligne !== undefined,
    `la section « erreur » des attendus n’a pas p = 1/${v}, la chance d’un modèle qui devine au hasard parmi les ` +
      `${v} caractères du mini-modèle${FINE}: mets 1 / ${v} dans PROBAS_ERREUR (projets/0.2-maths/maths_utiles/attendus.py) ` +
      'et dans le notebook 0.2, puis régénère les attendus',
  );
  const valeurs = [ecrireReglage(p), ecrireNombre(ligne!.erreur, 3), nombre(v)];
  exiger(new Set(valeurs).size === 3, 'deux choix du pari sur l’erreur ont le même texte');
  return [
    { texte: valeurs[0], juste: false },
    { texte: valeurs[1], juste: true },
    { texte: valeurs[2], juste: false },
  ];
}
