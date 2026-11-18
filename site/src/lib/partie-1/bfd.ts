// L'empaquetage BFD (« best-fit decreasing ») du chapitre 1.7 : le jumeau TypeScript du placement d'`empaqueter`
// (projets/forge/forge/affinage/empaquetage.py).
//
// Plusieurs conversations courtes partagent une rangée de `capacite` jetons (la longueur d'une rangée, plus un) ;
// un exemple n'est jamais coupé. Seules les longueurs comptent pour le placement : le jumeau reçoit les
// longueurs des exemples et rend, pour chaque rangée, le rang d'origine des exemples qu'elle contient, dans
// l'ordre où ils y sont placés. Les mêmes égalités, le même ordre qu'en Python :
//
//   1. les exemples sont pris par longueur décroissante, et, à égalité, dans leur ordre d'origine ;
//   2. chacun va dans la rangée où il laisse le moins de place libre : la plus petite place qui convient,
//      et, parmi les rangées qui ont cette place, la première ouverte (le plus petit numéro) ;
//   3. s'il ne tient dans aucune, il ouvre une nouvelle rangée.
//
// Un exemple plus long qu'une rangée est écarté, et compté ; un exemple de longueur 0, qui n'a aucun jeton appris,
// l'est aussi (en Python, `any(appris)` est faux : il ne donnerait aucune perte). Ici, tous les jetons d'un exemple
// non vide comptent comme appris : le jumeau ne voit que les longueurs.
//
// Ce module n'importe rien : une page ou un parcours le charge sans rien embarquer d'autre.

/** Le résultat : `rangees[k]` liste les rangs (dans `longueurs`) des exemples de la rangée k, et `ecartes` compte les écartés. */
export interface Empaquetage {
  rangees: number[][];
  ecartes: number;
}

/** Ajoute `valeur` au tas-minimum `tas` (comme `heapq.heappush`). */
function pousser(tas: number[], valeur: number): void {
  tas.push(valeur);
  let i = tas.length - 1;
  while (i > 0) {
    const parent = (i - 1) >> 1;
    if (tas[parent] <= tas[i]) break;
    [tas[parent], tas[i]] = [tas[i], tas[parent]];
    i = parent;
  }
}

/** Retire et rend la plus petite valeur du tas-minimum `tas` (comme `heapq.heappop`). */
function retirer(tas: number[]): number {
  const plusPetit = tas[0];
  const dernier = tas.pop() as number;
  if (tas.length > 0) {
    tas[0] = dernier;
    let i = 0;
    for (;;) {
      const gauche = 2 * i + 1;
      const droite = gauche + 1;
      let petit = i;
      if (gauche < tas.length && tas[gauche] < tas[petit]) petit = gauche;
      if (droite < tas.length && tas[droite] < tas[petit]) petit = droite;
      if (petit === i) break;
      [tas[petit], tas[i]] = [tas[i], tas[petit]];
      i = petit;
    }
  }
  return plusPetit;
}

/**
 * Range des exemples de ces longueurs en rangées de `capacite` jetons (la longueur d'une rangée, plus un).
 * `capacite` doit valoir au moins 2, comme en Python une rangée d'au moins 1 jeton de contexte.
 */
export function empaqueterLongueurs(longueurs: readonly number[], capacite: number): Empaquetage {
  if (capacite - 1 < 1) {
    throw new Error(`La longueur d'une rangée doit valoir au moins 1, pas ${capacite - 1}.`);
  }
  const gardes: [number, number][] = []; // [rang, longueur]
  let ecartes = 0;
  longueurs.forEach((longueur, rang) => {
    if (longueur > capacite || longueur === 0) ecartes += 1;
    else gardes.push([rang, longueur]);
  });
  // Par longueur décroissante ; à égalité, dans l'ordre d'origine (le tri est stable, et les rangs croissent).
  gardes.sort((a, b) => b[1] - a[1] || a[0] - b[0]);

  const contenus: number[][] = [];
  const libre: number[] = [];
  // Un tas de numéros de rangée par place libre : la plus petite place qui convient, puis la première rangée ouverte.
  const parPlace: number[][] = Array.from({ length: capacite + 1 }, () => []);
  for (const [rang, taille] of gardes) {
    let place = -1;
    for (let p = taille; p <= capacite; p += 1) {
      if (parPlace[p].length > 0) {
        place = p;
        break;
      }
    }
    let numero: number;
    if (place === -1) {
      numero = contenus.length;
      contenus.push([]);
      libre.push(capacite);
    } else {
      numero = retirer(parPlace[place]);
    }
    contenus[numero].push(rang);
    libre[numero] -= taille;
    pousser(parPlace[libre[numero]], numero);
  }
  return { rangees: contenus, ecartes };
}
