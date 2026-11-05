// Les paris du chapitre 0.4, « Tenseurs et calcul sur GPU », et ce que le
// chapitre écrit des chronos.
//
// Les bonnes réponses sont calculées, jamais écrites à la main : par le jumeau
// des formes (formes.ts) pour la diffusion et la mémoire, par les mesures
// (projets/0.4-tenseurs/mesures/*.json, que lit mesures.ts) pour les fils et la
// petite matrice. Les chronos du processeur seront refaits à la porte, machine
// au repos, et ceux de la carte n'y existent qu'à partir de là : tout ce qui en
// est tiré ici (verdicts, phrases) vaut pour n'importe quelles mesures valides,
// et paris-0-4.test.ts l'essaie sur de fausses mesures.
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* : le parcours du chapitre
// l'importe (B1). De mesures.ts, il ne prend que des types.

import { OCTETS_PAR_GO } from '../calculateur/formules';
import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre } from '../nombres';
import { A_DEPART, B_DEPART } from './atelier-formes';
import { ecrireForme, formeDiffusee, memoireOctets } from './formes';
import type { MesuresChrono } from './mesures';

const FINE = '\u202F';
const exiger = exigeur('src/lib/partie-0/paris-0-4.ts et le texte des paris du chapitre 0.4');

/** Deux formes égales (null compris). */
function memesFormes(a: readonly number[] | null, b: readonly number[] | null): boolean {
  if (a === null || b === null) return a === b;
  return a.length === b.length && a.every((x, i) => x === b[i]);
}

// ---------- Le pari « diffusion » ----------

/**
 * « A a la forme (3, 1), B la forme (4,). Quelle forme a A + B ? », sur les
 * formes de départ de l'atelier. Les choix : les lignes de A et la taille de B,
 * dans un ordre puis dans l'autre, ou « Impossible ». Le juste est celui du
 * jumeau des formes.
 */
export function choixDiffusion(): Choix[] {
  exiger(A_DEPART[0] !== B_DEPART[0], 'les deux premiers choix du pari « diffusion » sont devenus identiques');
  const r = formeDiffusee(A_DEPART, B_DEPART);
  const candidats = [[A_DEPART[0], B_DEPART[0]], [B_DEPART[0], A_DEPART[0]], null];
  return candidats.map((c) => ({ texte: c === null ? 'Impossible' : ecrireForme(c), juste: memesFormes(c, r) }));
}

// ---------- Le pari « memoire » ----------

/** La matrice du pari : 4 096 × 4 096 nombres, la plus grande des chronos. */
export const TAILLE_DU_PARI_MEMOIRE = 4096;
/** Un float32 prend 4 octets (element_size() de PyTorch, dans les attendus du projet). */
export const OCTETS_FLOAT32 = 4;
/** Comme le calculateur (Go de 1 024³ octets) : 1 Mo vaut 1 024² octets. */
export const OCTETS_PAR_MO = 1024 * 1024;

/** Des octets en Mo ou en Go entiers, comme les choix du pari : « 64 Mo », « 4 Go ». */
function ecrireOctetsRonds(octets: number): string {
  const [valeur, unite] = octets >= OCTETS_PAR_GO ? [octets / OCTETS_PAR_GO, 'Go'] : [octets / OCTETS_PAR_MO, 'Mo'];
  exiger(Number.isInteger(valeur), `${octets} octets ne font pas un nombre entier de ${unite}`);
  return `${nombre(valeur)} ${unite}`;
}

/**
 * « Une matrice de 4 096 × 4 096 nombres en float32 : combien de mémoire ? »
 * Le juste : le nombre de cases fois 4 octets (memoireOctets). Les leurres : le
 * nombre de cases seul, comme si un nombre prenait un octet ; et les 4 octets
 * d'un nombre lus comme 4 Go.
 */
export function choixMemoire(): Choix[] {
  const forme = [TAILLE_DU_PARI_MEMOIRE, TAILLE_DU_PARI_MEMOIRE];
  const octets = memoireOctets(forme, OCTETS_FLOAT32);
  const candidats = [memoireOctets(forme, 1), octets, OCTETS_FLOAT32 * OCTETS_PAR_GO];
  return candidats.map((o) => ({ texte: ecrireOctetsRonds(o), juste: o === octets }));
}

// ---------- Les chronos ----------

/** La durée d'un produit taille × taille avec ce nombre de fils (null sur la carte), en millisecondes. */
export function chrono(m: MesuresChrono, taille: number, fils: number | null): number {
  const x = m.mesures.find((y) => y.taille === taille && y.fils === fils);
  if (x === undefined) {
    throw new Error(
      `Aucune mesure à la taille ${taille} avec ${fils === null ? 'la carte' : `${fils} fils`} pour ${m.nom}. ` +
        'Relance « python -m tenseurs mesurer » dans projets/0.4-tenseurs (voir son README).',
    );
  }
  return x.millisecondes;
}

/** Le meilleur chrono à cette taille : sur le processeur, le plus court de tous les nombres de fils. */
export function meilleurChrono(m: MesuresChrono, taille: number): number {
  let meilleur = Number.POSITIVE_INFINITY;
  for (const x of m.mesures) {
    if (x.taille === taille && x.millisecondes < meilleur) meilleur = x.millisecondes;
  }
  if (meilleur === Number.POSITIVE_INFINITY) chrono(m, taille, m.appareil === 'cuda' ? null : 1); // lève l'erreur qui dit quoi faire
  return meilleur;
}

/** Une durée à trois chiffres significatifs, à la française : « 0,00770 », « 17,5 », « 1 070 ». */
export function ecrireMillisecondes(ms: number): string {
  if (!(Number.isFinite(ms) && ms > 0)) {
    throw new RangeError(`ecrireMillisecondes : ${String(ms)} n’est pas une durée. Vérifie le fichier de mesures.`);
  }
  // 3 chiffres significatifs : « 1.07e+3 » donne l'exposant, donc le nombre de décimales.
  const [mantisse, exposant] = ms.toExponential(2).split('e');
  const arrondi = Number(`${mantisse}e${exposant}`);
  return nombre(arrondi, Math.max(0, 2 - Number(exposant)));
}

/** Les colonnes du processeur : 1 fil, le réglage par défaut et tous les fils, sans doublon. */
export function filsDesColonnes(m: MesuresChrono): number[] {
  return [...new Set([1, m.fils_par_defaut, m.fils_max])];
}

/** Une ligne du tableau des chronos : la taille, les durées du processeur par fils, celle de la carte. */
export interface LigneChronos {
  taille: number;
  processeur: string[];
  /** Null tant que la carte n'est pas mesurée ; « — » si elle ne l'est pas à cette taille. */
  carte: string | null;
}

/** Les lignes du tableau des chronos, une par taille mesurée sur le processeur. */
export function lignesChronos(cpu: MesuresChrono, carte: MesuresChrono | null): LigneChronos[] {
  const tailles = [...new Set(cpu.mesures.map((x) => x.taille))];
  return tailles.map((taille) => {
    const surLaCarte = carte?.mesures.find((x) => x.taille === taille);
    return {
      taille,
      processeur: filsDesColonnes(cpu).map((f) => ecrireMillisecondes(chrono(cpu, taille, f))),
      carte: carte === null ? null : surLaCarte === undefined ? '—' : ecrireMillisecondes(surLaCarte.millisecondes),
    };
  });
}

// ---------- Le pari « fils » ----------

/** La taille du pari : le plus gros produit, où les fils ont le plus à faire. */
export const TAILLE_DU_PARI_FILS = 4096;
/** Au-dessus de ce rapport, « deux fois plus vite » ; au-dessus du second, « un peu ». */
export const SEUIL_DEUX_FOIS = 1.8;
export const SEUIL_UN_PEU = 1.1;

export type VerdictFils = 'deux-fois' | 'un-peu' | 'pas';

/** Combien de fois tous les fils vont plus vite que le réglage par défaut, au produit du pari. */
export function rapportFils(m: MesuresChrono): number {
  exiger(
    m.fils_par_defaut < m.fils_max,
    `fils_par_defaut (${m.fils_par_defaut}) n’est plus sous fils_max (${m.fils_max}) : le pari « fils » n’a plus de sens`,
  );
  return chrono(m, TAILLE_DU_PARI_FILS, m.fils_par_defaut) / chrono(m, TAILLE_DU_PARI_FILS, m.fils_max);
}

/** Le verdict d'un rapport de chronos. */
export function verdictFils(rapport: number): VerdictFils {
  if (rapport >= SEUIL_DEUX_FOIS) return 'deux-fois';
  if (rapport >= SEUIL_UN_PEU) return 'un-peu';
  return 'pas';
}

/** La question du pari « fils », avec les fils du fichier de mesures. */
export function questionFils(m: MesuresChrono): string {
  const t = nombre(TAILLE_DU_PARI_FILS);
  return `Avec ${nombre(m.fils_max)} fils au lieu de ${nombre(m.fils_par_defaut)}, le produit ${t} × ${t} va-t-il deux fois plus vite${FINE}?`;
}

/** Les choix du pari « fils » : le juste suit le rapport des chronos. */
export function choixFils(m: MesuresChrono): Choix[] {
  const v = verdictFils(rapportFils(m));
  const choix: [VerdictFils, string][] = [
    ['deux-fois', 'Deux fois plus vite'],
    ['un-peu', 'Un peu plus vite'],
    ['pas', 'Pas plus vite'],
  ];
  return choix.map(([cle, texte]) => ({ texte, juste: cle === v }));
}

/** La phrase de l'explication du pari « fils », selon le verdict des mesures. */
export function phraseFils(m: MesuresChrono): string {
  switch (verdictFils(rapportFils(m))) {
    case 'deux-fois':
      return 'Ici, les fils en plus calculent presque autant que les premiers.';
    case 'un-peu':
      return 'Les fils en plus aident, mais bien moins que les premiers.';
    case 'pas':
      return 'Ici, les fils en plus n’aident pas.';
  }
}

// ---------- Le pari « petite matrice » (à la porte, avec la carte) ----------

/** La taille du pari : la plus petite des chronos. */
export const TAILLE_PETITE = 64;
/** Sous ce rapport entre le plus lent et le plus rapide (un écart de moins de 10 %), « autant l'un que l'autre ». */
export const SEUIL_AUTANT = 1.1;

/**
 * « Pour deux matrices 64 × 64, qui calcule le plus vite ? », d'après le
 * meilleur chrono de chacun à cette taille. N'entre dans le chapitre qu'à la
 * porte (tâche 16), avec les mesures de la carte et l'acquis `petite`.
 */
export function choixPetiteMatrice(cpu: MesuresChrono, carte: MesuresChrono): Choix[] {
  exiger(cpu.appareil === 'cpu' && carte.appareil === 'cuda', 'choixPetiteMatrice attend le processeur, puis la carte');
  const p = meilleurChrono(cpu, TAILLE_PETITE);
  const c = meilleurChrono(carte, TAILLE_PETITE);
  const autant = (p > c ? p / c : c / p) < SEUIL_AUTANT;
  return [
    { texte: 'Le processeur', juste: !autant && p < c },
    { texte: 'La carte', juste: !autant && c < p },
    { texte: "Autant l'un que l'autre", juste: autant },
  ];
}
