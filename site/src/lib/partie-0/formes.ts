// Les règles de forme du chapitre 0.4, en TypeScript, pour l'atelier des formes.
//
// C'est le jumeau exact de projets/0.4-tenseurs/tenseurs/formes.py et
// memoire.py : mêmes fonctions, mêmes opérations, dans le même ordre. Une forme
// est une liste d'entiers : [2, 3] pour une matrice de 2 lignes et 3 colonnes,
// [4] pour un vecteur, [] pour un nombre seul. Le fichier
// projets/0.4-tenseurs/tests/attendus-formes.json, écrit avec PyTorch lui-même,
// le prouve dans formes.test.ts, sur les 1 521 paires de formes de 1 à 3
// dimensions de tailles 1 à 3. Si l'un des deux change, l'autre doit suivre.
//
// Tout est en entiers : aucun arrondi, le résultat est le même partout.
//
// Ce module n'importe rien : un parcours de test peut l'importer (aucun ?raw,
// aucun .json).

/**
 * La forme de a + b selon la règle de la diffusion, ou null si les formes ne
 * vont pas ensemble. On aligne les deux formes par la droite : une dimension
 * qui manque à gauche compte pour 1. Dimension par dimension, les tailles
 * doivent être égales, ou l'une doit valoir 1.
 */
export function formeDiffusee(a: readonly number[], b: readonly number[]): number[] | null {
  const n = Math.max(a.length, b.length);
  const ga = [...new Array<number>(n - a.length).fill(1), ...a];
  const gb = [...new Array<number>(n - b.length).fill(1), ...b];
  const resultat: number[] = [];
  for (let i = 0; i < n; i++) {
    const x = ga[i];
    const y = gb[i];
    if (x === y || y === 1) {
      resultat.push(x); // égales, ou b s'étire pour suivre a
    } else if (x === 1) {
      resultat.push(y); // a s'étire pour suivre b
    } else {
      return null; // deux tailles différentes, et aucune ne vaut 1
    }
  }
  return resultat;
}

/**
 * La forme de a @ b (torch.matmul), ou null si les formes ne vont pas
 * ensemble. Un vecteur à gauche devient une ligne (1, n), à droite une colonne
 * (n, 1) ; la dernière dimension de gauche doit être l'avant-dernière de
 * droite ; les autres dimensions, celles du lot, se diffusent comme pour a + b ;
 * enfin, on retire le 1 ajouté à un vecteur.
 */
export function formeProduit(a: readonly number[], b: readonly number[]): number[] | null {
  if (a.length === 0 || b.length === 0) return null; // un nombre seul n'a pas de produit matriciel
  const gauche = a.length === 1 ? [1, ...a] : [...a];
  const droite = b.length === 1 ? [...b, 1] : [...b];
  if (gauche[gauche.length - 1] !== droite[droite.length - 2]) return null;
  const lot = formeDiffusee(gauche.slice(0, -2), droite.slice(0, -2));
  if (lot === null) return null;
  let forme = [...lot, gauche[gauche.length - 2], droite[droite.length - 1]];
  if (a.length === 1) forme = [...forme.slice(0, -2), ...forme.slice(-1)];
  if (b.length === 1) forme = forme.slice(0, -1);
  return forme;
}

/**
 * Le nombre d'octets d'un tenseur de cette forme : le nombre de nombres (le
 * produit des tailles, 1 pour un nombre seul), fois la place d'un nombre (4
 * octets en float32, 2 en bfloat16). Le jumeau d'octets() de memoire.py, qui
 * lit cette place dans PyTorch.
 */
export function memoireOctets(forme: readonly number[], octetsParNombre: number): number {
  let nombres = 1;
  for (const taille of forme) {
    nombres *= taille;
  }
  return nombres * octetsParNombre;
}

/**
 * Une forme écrite comme Python l'écrit : « (2, 3) », « (4,) » pour un vecteur
 * (la virgule dit que c'est un tuple), « () » pour un nombre seul.
 */
export function ecrireForme(forme: readonly number[]): string {
  if (forme.length === 1) return `(${forme[0]},)`;
  return `(${forme.join(', ')})`;
}
