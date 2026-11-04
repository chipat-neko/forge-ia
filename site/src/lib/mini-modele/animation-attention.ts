// Ce que montre l'animation de l'attention (AnimationAttention.svelte), étape
// par étape : les titres, l'explication, la ligne d'état, la barre de chaque
// mot et les couleurs de la carte. Des fonctions pures, testées dans
// animation-attention.test.ts : le composant ne fait que les afficher.
//
// Tous les nombres viennent du moteur : le détail d'une tête (detaillerTete,
// dans exemple-attention.ts) et, pour les scores des mots que le masque
// cachera à l'étape 5, la même fonction scoresAttention avec la même échelle.
// Rien n'est recopié de l'exemple : si ses vecteurs changent, les textes
// suivent.
//
// Têtes et mots sont comptés à partir de 0, comme dans paris-attention.ts :
// la tête 1 est « de qui on parle », la « Tête 2 » de la page, et le mot 6
// est « il ».
//
// Ce n'est pas un fichier vérifié (sources.test.ts) : il ne calcule rien que
// le Python doive refaire, il arrondit et met en forme pour l'écran. Toutes
// ses phrases passent par typographier() (espaces fines, apostrophes).

import { decimalesUtiles, nombre, pourcent } from '../nombres';
import { typographier } from '../typo';
import { scoresAttention } from './attention';
import { racine } from './calcul';
import type { DetailTete, ExempleAttention } from './exemple-attention';

/** Le nombre d'étapes de l'animation. */
export const NB_ETAPES = 7;

/** Une étape : son titre, et son nom court pour la ligne d'état (« Étape 6 sur 7 : softmax. »). */
export interface EtapeAttention {
  readonly titre: string;
  readonly court: string;
}

/** Ce qu'une ligne de la vue principale montre pour un mot, à une étape. */
export interface LigneMot {
  /** L'indice du mot dans la phrase. */
  readonly mot: number;
  /** Le nombre montré : le score (étape 3), le score divisé (4 et 5) ou le poids (6 et 7) ; null sinon. */
  readonly valeur: number | null;
  /** Ce qui s'écrit en bout de ligne : « 8 », « −0,5 », « 77 % » ou « masqué ». */
  readonly texte: string;
  readonly masque: boolean;
  readonly negatif: boolean;
  /** Le début de la barre, en pourcentage de la piste (arrondi à 2 décimales). */
  readonly debut: number;
  /** La largeur de la barre, en pourcentage de la piste (arrondie à 2 décimales) : data-cible. */
  readonly largeur: number;
}

/**
 * x arrondi à 2 décimales, sans −0 : 77,4795 donne 77,48.
 *
 * C'est la largeur d'une barre : String() de ce nombre est son data-cible, et
 * le style de la barre est fait de la même chaîne (« 77.48% »), que le
 * navigateur relit à l'identique.
 */
export function arrondi2(x: number): number {
  const r = Number(x.toFixed(2));
  return r === 0 ? 0 : r;
}

/** Un nombre sans décimale inutile, 2 au plus : « 8 », « 2,5 », « 0,77 ». */
export function valeur(x: number): string {
  return nombre(x, decimalesUtiles(x, 2));
}

/** Un vecteur entre parenthèses : « (5 ; 2 ; 0 ; 1) », avec l'espace fine devant « ; ». */
export function vecteur(v: ArrayLike<number>): string {
  return typographier(`(${Array.from(v, valeur).join(' ; ')})`);
}

/**
 * Un poids en pourcentage entier, à partir du même arrondi que sa barre :
 * le nombre affiché et la largeur de la barre disent toujours la même chose.
 */
export function pourcentPoids(p: number): string {
  return pourcent(arrondi2(p * 100) / 100);
}

/** Les sept étapes. La quatrième dit la vraie division : √4 = 2 pour des têtes de 4. */
export function etapesAttention(taille: number): EtapeAttention[] {
  const r = valeur(Math.sqrt(taille));
  const lignes: [string, string][] = [
    ['Les mots et leurs traits', 'les traits'],
    ['Requête, clé, valeur', 'requête, clé, valeur'],
    ['Les scores : requête · clé', 'les scores'],
    [`Divisés par √${nombre(taille)} = ${r}`, `divisés par ${r}`],
    ['Le masque : pas de regard vers la suite', 'le masque'],
    ['Softmax : des poids qui font 1', 'softmax'],
    ['Le mélange des valeurs', 'le mélange'],
  ];
  return lignes.map(([titre, court]) => ({ titre: typographier(titre), court: typographier(court) }));
}

function verifier(etape: number, d: DetailTete, requete: number): void {
  if (!Number.isInteger(etape) || etape < 1 || etape > NB_ETAPES) {
    throw new RangeError(`L'étape va de 1 à ${NB_ETAPES} (reçu ${etape}).`);
  }
  const n = d.cles.length;
  if (!Number.isInteger(requete) || requete < 0 || requete >= n) {
    throw new RangeError(`Le mot qui pose la question va de 0 à ${n - 1} (reçu ${requete}).`);
  }
}

/**
 * Les scores de la requête avec toutes les clés, y compris celles que le
 * masque cachera : bruts (étape 3) et divisés par √taille (étape 4). Même
 * fonction et même échelle que detaillerTete : pour les mots visibles, ce
 * sont exactement ses scores et ses scoresEchelles.
 */
function scoresComplets(d: DetailTete, requete: number): { bruts: number[]; divises: number[] } {
  const q = d.requetes[requete];
  return { bruts: scoresAttention(q, d.cles, 1.0), divises: scoresAttention(q, d.cles, 1.0 / racine(q.length)) };
}

/** La ligne de chaque mot, à cette étape, pour ce mot qui pose la question. */
export function lignesEtape(etape: number, d: DetailTete, requete: number): LigneMot[] {
  verifier(etape, d, requete);
  const n = d.cles.length;
  const lignes: LigneMot[] = [];
  const masquee = (mot: number, debut: number): LigneMot => ({
    mot,
    valeur: null,
    texte: 'masqué',
    masque: true,
    negatif: false,
    debut,
    largeur: 0,
  });
  if (etape <= 2) {
    for (let j = 0; j < n; j++) {
      lignes.push({ mot: j, valeur: null, texte: '', masque: false, negatif: false, debut: 50, largeur: 0 });
    }
    return lignes;
  }
  if (etape <= 5) {
    // Les barres partent d'un axe central : le plus grand |score brut| remplit
    // une demi-piste, et la division de l'étape 4 garde la même échelle (les
    // barres raccourcissent de moitié).
    const { bruts, divises } = scoresComplets(d, requete);
    let plusGrand = 0;
    for (const s of bruts) {
      const a = Math.abs(s);
      if (a > plusGrand) plusGrand = a;
    }
    const scores = etape === 3 ? bruts : divises;
    for (let j = 0; j < n; j++) {
      if (etape === 5 && j > requete) {
        lignes.push(masquee(j, 50));
        continue;
      }
      const s = scores[j];
      const largeur = plusGrand === 0 ? 0 : arrondi2((Math.abs(s) / plusGrand) * 50);
      lignes.push({
        mot: j,
        valeur: s,
        texte: valeur(s),
        masque: false,
        negatif: s < 0,
        debut: s < 0 ? arrondi2(50 - largeur) : 50,
        largeur,
      });
    }
    return lignes;
  }
  // Étapes 6 et 7 : les poids, depuis la gauche ; une piste entière vaut 100 %.
  for (let j = 0; j < n; j++) {
    if (j > requete) {
      lignes.push(masquee(j, 0));
      continue;
    }
    const p = d.poids[requete][j];
    const largeur = arrondi2(p * 100);
    lignes.push({ mot: j, valeur: p, texte: pourcent(largeur / 100), masque: false, negatif: false, debut: 0, largeur });
  }
  return lignes;
}

// ---------- Les phrases ----------

const g = (mot: string) => `« ${mot} »`;

/** « a », « a et b », « a, b et c ». */
function liste(elements: readonly string[]): string {
  if (elements.length <= 1) return elements.join('');
  return `${elements.slice(0, -1).join(', ')} et ${elements[elements.length - 1]}`;
}

/** Les indices des plus grandes valeurs de 0 à dernier compris (plusieurs à égalité exacte). */
function lesPlusGrands(valeurs: readonly number[], dernier: number): number[] {
  let m = valeurs[0];
  for (let j = 1; j <= dernier; j++) if (valeurs[j] > m) m = valeurs[j];
  const indices: number[] = [];
  for (let j = 0; j <= dernier; j++) if (valeurs[j] === m) indices.push(j);
  return indices;
}

function requeteNulle(d: DetailTete, requete: number): boolean {
  return d.requetes[requete].every((v) => v === 0);
}

/** Tous les traits de l'exemple valent 0 ou 1 : on peut les nommer (« pronom, sujet et personne »). */
function traitsBinaires(exemple: ExempleAttention): boolean {
  return exemple.x.every((ligne) => ligne.every((v) => v === 0 || v === 1));
}

/** D'où vient la nouvelle valeur du mot, après « Sa nouvelle valeur » ou « La nouvelle valeur de « il » ». */
function origine(exemple: ExempleAttention, d: DetailTete, requete: number): string {
  if (requete === 0) return "est sa propre valeur : il ne voit que lui-même.";
  const poids = d.poids[requete];
  const tops = lesPlusGrands(poids, requete);
  if (tops.length === requete + 1) return `est la moyenne des valeurs des ${requete + 1} mots qu'il voit.`;
  let total = 0.0;
  for (const j of tops) total += poids[j];
  const adverbe = total > 0.5 ? 'surtout' : "d'abord";
  const de = liste(tops.map((j) => `de ${g(exemple.jetons[j])}`));
  const part = tops.length > 1 ? `${pourcentPoids(poids[tops[0]])} chacun` : pourcentPoids(poids[tops[0]]);
  return `vient ${adverbe} ${de} (${part}).`;
}

/** La phrase calculée de l'étape 7 : « Sa nouvelle valeur vient surtout de « forgeron » (77 %). » */
export function phraseMelange(exemple: ExempleAttention, d: DetailTete, requete: number): string {
  return typographier(`Sa nouvelle valeur ${origine(exemple, d, requete)}`);
}

function phraseEtat(etape: number, exemple: ExempleAttention, d: DetailTete, requete: number): string {
  const n = d.cles.length;
  const mot = g(exemple.jetons[requete]);
  const nulle = requeteNulle(d, requete);
  switch (etape) {
    case 1: {
      const nb = exemple.traits.length;
      if (!traitsBinaires(exemple)) return `Les ${nb} nombres de ${mot} sont sur sa ligne du tableau.`;
      const actifs = exemple.traits.filter((_, k) => exemple.x[requete][k] === 1);
      if (actifs.length === 0) return `${mot} n'a aucun de ces traits : ses ${nb} nombres valent 0.`;
      return `${mot} a ${actifs.length} trait${actifs.length > 1 ? 's' : ''} sur ${nb} : ${liste(actifs)}.`;
    }
    case 2:
      return nulle
        ? `La requête de ${mot} est nulle : ${vecteur(d.requetes[requete])}.`
        : `La requête de ${mot} vaut ${vecteur(d.requetes[requete])}.`;
    case 3: {
      if (nulle) return `La requête de ${mot} est nulle : tous ses scores valent 0.`;
      const { bruts } = scoresComplets(d, requete);
      const tops = lesPlusGrands(bruts, n - 1);
      if (tops.length === n) return `Tous les scores de ${mot} valent ${valeur(bruts[0])}.`;
      return `Le plus grand score de ${mot} est ${valeur(bruts[tops[0]])}, avec ${liste(tops.map((j) => g(exemple.jetons[j])))}.`;
    }
    case 4: {
      if (nulle) return `Les scores de ${mot} valent toujours 0.`;
      const { bruts, divises } = scoresComplets(d, requete);
      const tops = lesPlusGrands(bruts, n - 1);
      if (tops.length === n) return `Tous les scores de ${mot} valent maintenant ${valeur(divises[0])}.`;
      const avec = liste(tops.map((j) => g(exemple.jetons[j])));
      const deA = `de ${valeur(bruts[tops[0]])} à ${valeur(divises[tops[0]])}`;
      return tops.length > 1
        ? `Les scores de ${mot} avec ${avec} passent ${deA}.`
        : `Le score de ${mot} avec ${avec} passe ${deA}.`;
    }
    case 5: {
      const suivants = n - requete - 1;
      const masques = suivants === 1 ? 'le suivant est masqué' : `les ${suivants} suivants sont masqués`;
      if (n === 1) return `${mot} est le seul mot : rien n'est masqué.`;
      if (requete === 0) return `${mot} est le premier mot : il ne voit que lui-même, ${masques}.`;
      if (suivants === 0) return `${mot} est le dernier mot : il voit toute la phrase, rien n'est masqué.`;
      return `${mot} voit les ${requete + 1} premiers mots, lui compris : ${masques}.`;
    }
    case 6: {
      const poids = d.poids[requete];
      if (requete === 0) return `${mot} ne voit que lui-même : il se donne ${pourcentPoids(poids[0])} de son attention.`;
      const tops = lesPlusGrands(poids, requete);
      if (tops.length === requete + 1) {
        return `${mot} partage son attention à parts égales : ${pourcentPoids(poids[0])} pour chacun des ${requete + 1} mots qu'il voit.`;
      }
      const debut = `${mot} donne ${pourcentPoids(poids[tops[0]])} de son attention à ${g(exemple.jetons[tops[0]])}`;
      if (tops.length === 1) return `${debut}.`;
      return `${debut}, et autant ${liste(tops.slice(1).map((j) => `à ${g(exemple.jetons[j])}`))}.`;
    }
    default:
      return `La nouvelle valeur de ${mot} ${origine(exemple, d, requete)}`;
  }
}

/**
 * Les deux parties de la ligne d'état : où l'on en est (« Étape 6 sur 7 :
 * softmax. »), puis ce que dit l'étape pour le mot choisi.
 */
export function partiesLigneEtat(
  etape: number,
  exemple: ExempleAttention,
  d: DetailTete,
  requete: number,
): { ou: string; phrase: string } {
  verifier(etape, d, requete);
  const { court } = etapesAttention(d.requetes[requete].length)[etape - 1];
  return {
    ou: typographier(`Étape ${etape} sur ${NB_ETAPES} : ${court}.`),
    phrase: typographier(phraseEtat(etape, exemple, d, requete)),
  };
}

/** La ligne d'état (role="status") : « Étape 6 sur 7 : softmax. « il » donne 77 % de son attention à « forgeron ». » */
export function ligneEtat(etape: number, exemple: ExempleAttention, d: DetailTete, requete: number): string {
  const { ou, phrase } = partiesLigneEtat(etape, exemple, d, requete);
  return `${ou} ${phrase}`;
}

/** Ce que fait l'étape, en deux phrases, avec le mot choisi ; et si sa requête est nulle, ce que ça donne. */
export function explication(etape: number, exemple: ExempleAttention, d: DetailTete, requete: number): string {
  verifier(etape, d, requete);
  const mot = g(exemple.jetons[requete]);
  const nb = exemple.traits.length;
  // La taille de la requête et de la clé (celle de la tête), et celle de la valeur : wv peut avoir
  // un autre nombre de colonnes que wq et wk, et la nouvelle valeur a la taille de la valeur.
  const taille = d.requetes[requete].length;
  const tailleValeur = d.valeurs[requete].length;
  const textes = [
    traitsBinaires(exemple)
      ? `Chaque mot entre dans la tête sous forme de ${nb} nombres, un par trait : 1 s'il a ce trait, 0 sinon.`
      : `Chaque mot entre dans la tête sous forme de ${nb} nombres, un par trait.`,
    `La tête multiplie les ${nb} nombres de chaque mot par trois matrices. ` +
      (tailleValeur === taille
        ? `Elle en tire trois vecteurs de ${taille} nombres : ` +
          "la requête q, ce que le mot cherche ; la clé k, ce qu'il offre aux autres ; la valeur v, ce qu'il transmettra."
        : "Elle en tire trois vecteurs : la requête q, ce que le mot cherche, et la clé k, ce qu'il offre aux autres, " +
          `de ${taille} nombres chacune ; la valeur v, ce qu'il transmettra, de ${tailleValeur} nombres.`),
    `Le score d'un mot, c'est la requête de ${mot} multipliée par la clé de ce mot, case par case, puis additionnée : ` +
      'requête · clé. Plus il est grand, mieux ce mot répond à la question.',
    `Chaque score est divisé par √${nombre(taille)} = ${valeur(Math.sqrt(taille))}, la racine de la taille de la tête. ` +
      'Sans cela, dans les grandes têtes des vrais modèles, les scores deviendraient si grands que le softmax donnerait presque tout à un seul mot.',
    "Quand le modèle écrit, la suite n'existe pas encore : chaque mot ne regarde que lui-même et ceux d'avant. " +
      'Les scores des mots suivants sont masqués.',
    `Le softmax change les scores visibles en poids, tous positifs, qui font ${pourcent(1)} à eux tous. ` +
      "Un score plus grand d'une unité donne un poids environ 2,7 fois plus grand.",
    `Chaque mot visible transmet sa valeur v, multipliée par son poids ; leur somme est la nouvelle valeur de ${mot}, ${tailleValeur} nombres.`,
  ];
  let texte = textes[etape - 1];
  if (etape >= 3 && requeteNulle(d, requete)) {
    texte +=
      requete === 0
        ? ` La requête de ${mot} ne vaut que des 0 : tous ses scores valent 0.`
        : ` La requête de ${mot} ne vaut que des 0 : tous ses scores valent 0, et il partage son attention à parts égales entre les mots qu'il voit.`;
  }
  return typographier(texte);
}

// ---------- La carte ----------

/** « Tête 2 : de qui on parle » (la tête d'indice 1). */
export function nomTete(exemple: ExempleAttention, tete: number): string {
  return typographier(`Tête ${tete + 1} : ${exemple.tetes[tete].nom}`);
}

/** La légende du tableau de la carte. */
export function legendeCarte(exemple: ExempleAttention, tete: number): string {
  return typographier(`${nomTete(exemple, tete)}. Les poids après le softmax, en pourcentage.`);
}

/** Ce que la page dit à la place des commandes, sans JavaScript. */
export function messageSansJs(exemple: ExempleAttention, tete: number): string {
  return typographier(
    `Sans JavaScript, l'animation reste à sa première étape ; la carte complète de la tête ${tete + 1}, ` +
      `${g(exemple.tetes[tete].nom)}, est juste en dessous.`,
  );
}

/**
 * La phrase sous la carte sur les requêtes nulles, avec le premier mot
 * concerné qui voit plusieurs mots (pas le premier de la phrase) ; null si
 * aucun mot de la tête n'a de requête nulle.
 */
export function phraseRequeteNulle(exemple: ExempleAttention, d: DetailTete): string | null {
  for (let i = 1; i < d.requetes.length; i++) {
    if (requeteNulle(d, i)) {
      return typographier(
        `Un mot dont la requête ne vaut que des 0, comme ${g(exemple.jetons[i])} ici, a tous ses scores à 0 : ` +
          "il partage son attention à parts égales entre les mots qu'il voit.",
      );
    }
  }
  return null;
}

// Le fond d'une case est un mélange d'indigo et de papier (color-mix), d'autant
// plus indigo que le poids est grand ; au-delà de 0,5, le texte passe en papier.
// Entre 50 % et 65 % d'indigo, ni l'un ni l'autre texte n'atteint le contraste
// AA (4,5) : au-delà de 0,5, le fond saute donc à 65 %, puis monte jusqu'à 100 %.
// Le fond n'est pas proportionnel au poids : il est linéaire par morceaux.
const SEUIL_CLAIR = 0.5;
const FOND_CLAIR_MIN = 65;

/**
 * La part d'indigo du fond d'une case, en pourcentage (0 à 100), linéaire par
 * morceaux : égale au poids jusqu'à 0,5 (0 à 50 %), puis de 65 % à 100 % de
 * 0,5 à 1. Le saut à 0,5 garde le contraste AA du texte, indigo puis papier.
 * Elle croît toujours avec le poids, mais elle n'est pas proportionnelle.
 */
export function fondCarte(p: number): number {
  if (p <= SEUIL_CLAIR) return arrondi2(p * 100);
  return arrondi2(FOND_CLAIR_MIN + ((100 - FOND_CLAIR_MIN) * (p - SEUIL_CLAIR)) / (1 - SEUIL_CLAIR));
}

/** Vrai quand le texte de la case passe en papier (poids au-delà de 0,5). */
export function caseClaire(p: number): boolean {
  return p > SEUIL_CLAIR;
}

// ---------- Les mots ----------

/** Vrai si ce mot apparaît plusieurs fois dans la phrase, sans compter la casse (« Le » et les deux « le »). */
export function repete(exemple: ExempleAttention, i: number): boolean {
  const mot = exemple.jetons[i].toLocaleLowerCase('fr');
  let fois = 0;
  for (const autre of exemple.jetons) if (autre.toLocaleLowerCase('fr') === mot) fois += 1;
  return fois > 1;
}

/** Les mots que la requête voit, du plus regardé au moins regardé ; à égalité, dans l'ordre de la phrase. */
export function classement(d: DetailTete, requete: number): number[] {
  const poids = d.poids[requete];
  return Array.from({ length: requete + 1 }, (_, j) => j).sort((a, b) => poids[b] - poids[a] || a - b);
}

/**
 * La première partie de la légende : ce que l'exemple dit de ses vecteurs, d'où ils viennent (sa
 * clé « legende »). Elle vaut à toutes les étapes. Elle appartient à l'exemple : la phrase du
 * forgeron dit qu'ils sont écrits à la main, un autre exemple dira d'où viennent les siens. Sans
 * légende, null : la figure ne parle alors que de la carte, et ne dit rien de faux sur les vecteurs.
 */
export function legendeVecteurs(exemple: ExempleAttention): string | null {
  const texte = exemple.legende?.trim() ?? '';
  return texte === '' ? null : typographier(texte);
}

/**
 * La source de la mise en garde de la carte : des poids d'attention ne disent pas pourquoi le
 * modèle répond. Le titre de l'article est en anglais (lang="en" sur son lien).
 */
export const SOURCE_POIDS_NON_EXPLICATION = Object.freeze({
  auteurs: 'Jain et Wallace',
  titre: 'Attention is not Explanation',
  reference: 'arXiv 1902.10186',
  annee: 2019,
  url: 'https://arxiv.org/abs/1902.10186',
});

/** La seconde partie de la légende, jusqu'au titre de l'article cité (le lien) : elle parle de la carte. */
export const LEGENDE_CARTE_AVANT = typographier(
  `La carte montre où le calcul lit, pas pourquoi le modèle répond (voir ${SOURCE_POIDS_NON_EXPLICATION.auteurs}, « `,
);

/** La fin de la seconde partie de la légende, après le titre de l'article cité. */
export const LEGENDE_CARTE_APRES = typographier(
  ` », ${SOURCE_POIDS_NON_EXPLICATION.reference}, ${SOURCE_POIDS_NON_EXPLICATION.annee}). ` +
    'Une ligne par mot qui demande, une colonne par mot regardé ; score = requête · clé.',
);

/** La seconde partie de la légende, en texte : elle parle de la carte, et ne s'affiche qu'avec elle. */
export const LEGENDE_CARTE = `${LEGENDE_CARTE_AVANT}${SOURCE_POIDS_NON_EXPLICATION.titre}${LEGENDE_CARTE_APRES}`;

/** La légende complète de la figure, celle des étapes 6 et 7 : les vecteurs de l'exemple (s'il en parle), puis la carte. */
export function legendeFigure(exemple: ExempleAttention): string {
  const vecteurs = legendeVecteurs(exemple);
  return vecteurs === null ? LEGENDE_CARTE : `${vecteurs} ${LEGENDE_CARTE}`;
}
