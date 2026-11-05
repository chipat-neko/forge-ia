// Les paris du chapitre 0.4, « Tenseurs et calcul sur GPU », et ce que le
// chapitre écrit des chronos.
//
// Les bonnes réponses sont calculées, jamais écrites à la main : par le jumeau
// des formes (formes.ts) pour la diffusion et la mémoire, par les mesures
// (projets/0.4-tenseurs/mesures/*.json, que lit mesures.ts) pour les fils et la
// petite matrice. Les chronos du processeur et de la carte ont été relevés à la
// porte de la Partie 0, carte au repos, et pourront l'être encore : tout ce qui
// en est tiré ici (verdicts, phrases) vaut pour n'importe quelles mesures
// valides, ou s'arrête sur une garde qui dit quelle phrase revoir.
// paris-0-4.test.ts l'essaie sur de fausses mesures, puis sur les vrais fichiers.
//
// Ce module n'importe ni ?raw, ni .json, ni astro:* : le parcours du chapitre
// l'importe (B1). De mesures.ts, il ne prend que des types.

import { OCTETS_PAR_GO } from '../calculateur/formules';
import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre, pourcent } from '../nombres';
import { A_DEPART, B_DEPART } from './atelier-formes';
import { ecrireForme, formeDiffusee, memoireOctets } from './formes';
import type { MesuresChrono } from './mesures';

const FINE = '\u202F';
/** L'espace insécable ordinaire, autour du × d'une taille (« 4 096 × 4 096 ») : la ligne ne s'y coupe pas. */
const INSECABLE = '\u00A0';
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

/** Un rapport tel que la page l'écrit, arrondi à deux décimales : 1,796 s'écrit « 1,80 ». */
function rapportEcrit(rapport: number): number {
  return Number(rapport.toFixed(2));
}

/**
 * Le verdict d'un rapport de chronos, lu sur le rapport écrit : « 1,80 fois
 * plus vite » compte pour deux fois, comme le nombre que lit le lecteur, même
 * si le rapport exact vaut 1,796 (point mis de côté à la tâche 11).
 */
export function verdictFils(rapport: number): VerdictFils {
  const ecrit = rapportEcrit(rapport);
  if (ecrit >= SEUIL_DEUX_FOIS) return 'deux-fois';
  if (ecrit >= SEUIL_UN_PEU) return 'un-peu';
  return 'pas';
}

/**
 * Le gain minimal du réglage par défaut sur un seul fil. L'étape 7 dit « Le
 * processeur aussi calcule en parallèle » en montrant ce gain : à 1,5, les
 * fils du réglage par défaut font gagner au moins un tiers du temps, bien
 * au-delà de ce qu'une mesure dérangée peut déplacer ; en dessous, la phrase
 * ne serait plus démontrée par le tableau, et la mesure est à refaire.
 */
export const SEUIL_PARALLELE = 1.5;

/** Combien de fois le réglage par défaut va plus vite qu'un seul fil, au produit du pari ; gardé par SEUIL_PARALLELE. */
export function gainDuReglageParDefaut(m: MesuresChrono): number {
  const gain = m.fils_par_defaut > 1 ? chrono(m, TAILLE_DU_PARI_FILS, 1) / chrono(m, TAILLE_DU_PARI_FILS, m.fils_par_defaut) : 1;
  exiger(
    gain >= SEUIL_PARALLELE,
    `le réglage par défaut (${m.fils_par_defaut} fils) ne va plus que ${nombre(gain, 1)} fois plus vite qu’un seul fil, ` +
      `sous ${nombre(SEUIL_PARALLELE, 1)} : l’étape 7 ne montre plus que le processeur calcule en parallèle (refais la mesure du processeur)`,
  );
  return gain;
}

/** La question du pari « fils », avec les fils du fichier de mesures ; « 4 096 × 4 096 » ne se coupe pas. */
export function questionFils(m: MesuresChrono): string {
  const t = nombre(TAILLE_DU_PARI_FILS);
  return `Avec ${nombre(m.fils_max)} fils au lieu de ${nombre(m.fils_par_defaut)}, le produit ${t}${INSECABLE}×${INSECABLE}${t} va-t-il deux fois plus vite${FINE}?`;
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

/**
 * L'explication du pari « fils », tirée des mesures et juste pour n'importe
 * quel fichier valide : les deux chronos, la comparaison (« 1,20 fois plus
 * vite », « 1,30 fois plus lent » si tous les fils vont moins vite, « pas plus
 * vite » à 1 % près), une phrase selon le verdict, et, quand les fils en plus
 * aident peu ou pas, la raison : deux fils d'un même cœur se partagent ses
 * unités de calcul (8 cœurs et 16 fils sur ce PC, docs/mesures/entrainement-2026-11.md).
 */
export function phraseFils(m: MesuresChrono): string {
  const r = rapportFils(m);
  const tous = ecrireMillisecondes(chrono(m, TAILLE_DU_PARI_FILS, m.fils_max));
  const defaut = ecrireMillisecondes(chrono(m, TAILLE_DU_PARI_FILS, m.fils_par_defaut));
  const plusVite = r >= 1;
  const facteur = plusVite ? r : 1 / r;
  // À 1 % près (deux décimales), ni plus vite ni plus lent. Le nombre écrit est celui du verdict.
  const egaux = rapportEcrit(facteur) === 1;
  const comparaison = egaux ? 'pas plus vite' : `${nombre(rapportEcrit(facteur), 2)} fois ${plusVite ? 'plus vite' : 'plus lent'}`;
  const debut =
    `Avec ${nombre(m.fils_max)} fils, le produit prend ${tous}${INSECABLE}ms, contre ${defaut}${INSECABLE}ms ` +
    `avec ${nombre(m.fils_par_defaut)}${FINE}: ${comparaison}.`;
  const coeurs =
    `Un fil n’est pas un cœur${FINE}: un cœur du processeur peut faire tourner deux fils à la fois, ` +
    'qui se partagent alors ses unités de calcul.';
  switch (verdictFils(r)) {
    case 'deux-fois':
      return `${debut} Ici, les fils en plus calculent presque autant que les premiers.`;
    case 'un-peu':
      return `${debut} Les fils en plus aident, mais bien moins que les premiers. ${coeurs}`;
    case 'pas':
      return plusVite || egaux
        ? `${debut} Ici, les fils en plus n’aident presque pas. ${coeurs}`
        : `${debut} Ici, les fils en plus ralentissent même le calcul. ${coeurs}`;
  }
}

// ---------- Le pari « petite matrice », et ce que montrent les chronos ----------

/** La taille du pari : la plus petite des chronos. */
export const TAILLE_PETITE = 64;
/** Sous ce rapport entre le plus lent et le plus rapide (un écart de moins de 10 %), « autant l'un que l'autre ». */
export const SEUIL_AUTANT = 1.1;

/**
 * Le prix fixe de la carte. Un chrono sur la carte, c'est un prix fixe P
 * (PyTorch lui envoie le produit, puis le chronomètre attend qu'elle ait
 * fini : torch.cuda.synchronize dans chrono.py) plus le calcul C. Le produit
 * de la taille suivante demande bien plus d'opérations (64 fois plus de 64 à
 * 256, au moins SEUIL_OPERATIONS fois) : on admet seulement, très prudemment,
 * que son calcul prend au moins 2 fois celui du petit. Si la carte n'y met que
 * r fois plus de temps, alors C(petit) ≤ (r − 1) × t et P ≥ (2 − r) × t, où t
 * est la durée du petit produit : P dépasse C dès que r < 1,5. Au-delà,
 * l'explication du pari ne serait plus démontrée par le tableau.
 */
export const SEUIL_PRIX_FIXE = 1.5;
/**
 * L'hypothèse « au moins 2 fois le calcul » n'est prudente que si la taille
 * suivante a bien plus d'opérations : au moins 8 fois, une taille doublée. Avec
 * 80 après 64, il n'y en aurait que 1,95 fois plus.
 */
export const SEUIL_OPERATIONS = 8;
/** Au plus grand produit, la carte va « des dizaines de fois plus vite » que le processeur : de 20 fois à 100 fois. */
export const SEUIL_BIEN_PLUS_VITE = 20;
export const SEUIL_CENTAINES = 100;
/** Copier une matrice prend « à peu près autant » que son produit à 25 % près, dans un sens ou dans l'autre. */
export const SEUIL_A_PEU_PRES = 1.25;

type VerdictPetite = 'processeur' | 'carte' | 'autant';

/** « 64 × 64 », « 4 096 × 4 096 » : le × entre deux espaces insécables, la taille ne se coupe pas. */
function ecrireTaille(t: number): string {
  return `${nombre(t)}${INSECABLE}×${INSECABLE}${nombre(t)}`;
}

/** Les tailles d'un fichier de mesures, dans l'ordre (croissant, vérifié par mesures.ts). */
function taillesDe(m: MesuresChrono): number[] {
  return [...new Set(m.mesures.map((x) => x.taille))];
}

/** Le verdict du pari « petite » : le meilleur chrono du processeur à 64, tous fils confondus, contre celui de la carte. */
function verdictPetite(cpu: MesuresChrono, carte: MesuresChrono): { verdict: VerdictPetite; p: number; c: number } {
  exiger(
    cpu.appareil === 'cpu' && carte.appareil === 'cuda',
    'le pari « petite » et ce qui en est tiré attendent les mesures du processeur, puis celles de la carte',
  );
  const p = meilleurChrono(cpu, TAILLE_PETITE);
  const c = meilleurChrono(carte, TAILLE_PETITE);
  const autant = (p > c ? p / c : c / p) < SEUIL_AUTANT;
  return { verdict: autant ? 'autant' : p < c ? 'processeur' : 'carte', p, c };
}

/** La garde commune : si la carte gagne au plus petit produit, l'acquis « petite » n'est plus montré. */
function exigerPasLaCarte(verdict: VerdictPetite, c: number, p: number): void {
  exiger(
    verdict !== 'carte',
    `la carte calcule le produit ${TAILLE_PETITE} × ${TAILLE_PETITE} en ${ecrireMillisecondes(c)} ms, plus vite que le processeur ` +
      `(${ecrireMillisecondes(p)} ms) : l’acquis « petite » (« la carte ne gagne pas toujours »), l’explication du pari ` +
      'et la phrase sous le tableau des chronos sont à revoir',
  );
}

/** La question du pari « petite » : « Pour deux matrices 64 × 64, qui calcule le plus vite ? » ; « 64 × 64 » ne se coupe pas. */
export function questionPetite(): string {
  return `Pour deux matrices ${ecrireTaille(TAILLE_PETITE)}, qui calcule le plus vite${FINE}?`;
}

/**
 * « Pour deux matrices 64 × 64, qui calcule le plus vite ? », d'après le
 * meilleur chrono de chacun à cette taille. Le pari de l'étape 6 du chapitre,
 * avant le tableau des chronos, avec l'acquis `petite`.
 */
export function choixPetiteMatrice(cpu: MesuresChrono, carte: MesuresChrono): Choix[] {
  const { verdict } = verdictPetite(cpu, carte);
  return [
    { texte: 'Le processeur', juste: verdict === 'processeur' },
    { texte: 'La carte', juste: verdict === 'carte' },
    { texte: "Autant l'un que l'autre", juste: verdict === 'autant' },
  ];
}

/** La preuve du prix fixe, lue dans les chronos de la carte : la taille suivante, bien plus de calcul, à peine plus de temps. */
function preuveDuPrixFixe(carte: MesuresChrono): string {
  const tailles = taillesDe(carte);
  const suivante = tailles[tailles.indexOf(TAILLE_PETITE) + 1];
  exiger(
    tailles.includes(TAILLE_PETITE) && suivante !== undefined,
    `la carte n’a pas de mesure après ${TAILLE_PETITE} : l’explication du pari « petite » n’a plus la preuve de son prix fixe`,
  );
  const calcul = (suivante / TAILLE_PETITE) ** 3;
  exiger(
    calcul >= SEUIL_OPERATIONS,
    `le produit ${suivante} × ${suivante} ne demande que ${nombre(calcul, 2)} fois les opérations du ` +
      `${TAILLE_PETITE} × ${TAILLE_PETITE}, moins de ${SEUIL_OPERATIONS} fois : il ne prouve plus le prix fixe ` +
      '(explication du pari « petite », SEUIL_PRIX_FIXE)',
  );
  const r = chrono(carte, suivante, null) / chrono(carte, TAILLE_PETITE, null);
  exiger(
    r < SEUIL_PRIX_FIXE,
    `sur la carte, le produit ${suivante} × ${suivante} prend ${nombre(r, 2)} fois le temps du ${TAILLE_PETITE} × ${TAILLE_PETITE}, ` +
      `pas moins de ${nombre(SEUIL_PRIX_FIXE, 1)} : le tableau ne montre plus que le prix fixe dépasse le calcul ` +
      '(explication du pari « petite »)',
  );
  // À deux décimales, 1,00 ou moins ne s'écrit pas « 1,00 fois plus de temps ».
  const temps = Number(r.toFixed(2)) > 1 ? `n’y met que ${nombre(r, 2)} fois plus de temps` : 'n’y met pas plus de temps';
  return (
    `Les chronos de l’étape suivante le montrent${FINE}: le produit ${ecrireTaille(suivante)} demande ` +
    `${nombre(calcul)} fois plus de calcul, et la carte ${temps}.`
  );
}

/**
 * L'explication du pari « petite », juste pour n'importe quel fichier valide :
 * les deux chronos ; le prix fixe de chaque produit chronométré sur la carte
 * (l'envoyer, puis l'attente du chronomètre : PyTorch, lui, n'attend pas la
 * carte, l'étape 6 le dit), qui dépasse le calcul d'un si petit produit ; et sa
 * preuve dans le tableau. Si la carte gagne, la garde tombe : l'acquis
 * « petite » ne serait plus montré.
 */
export function explicationPetite(cpu: MesuresChrono, carte: MesuresChrono): string {
  const { verdict, p, c } = verdictPetite(cpu, carte);
  exigerPasLaCarte(verdict, c, p);
  const [tp, tc] = [ecrireMillisecondes(p), ecrireMillisecondes(c)];
  const debut =
    verdict === 'processeur'
      ? `Le processeur${FINE}: ${tp}${INSECABLE}ms au mieux, contre ${tc}${INSECABLE}ms pour la carte.`
      : `Autant l’un que l’autre${FINE}: ${tp}${INSECABLE}ms au mieux pour le processeur, ${tc}${INSECABLE}ms pour la carte, ` +
        `moins de ${pourcent(SEUIL_AUTANT - 1)} d’écart.`;
  const prix =
    `Sur la carte, chaque produit chronométré a un prix fixe${FINE}: PyTorch doit le lui envoyer, puis le chronomètre attend qu’elle ait fini. ` +
    'Pour un si petit produit, ce prix dépasse le calcul lui-même.';
  return `${debut} ${prix} ${preuveDuPrixFixe(carte)}`;
}

/**
 * La phrase sous le tableau des chronos : au plus petit produit, le processeur
 * (ou autant l'un que l'autre) ; la taille dès laquelle la carte le dépasse, et
 * reste devant ; au plus grand, des dizaines de fois plus vite que le
 * processeur au mieux de ses fils. Chaque morceau a sa garde.
 */
export function phraseCarteEtProcesseur(cpu: MesuresChrono, carte: MesuresChrono): string {
  const { verdict, p, c } = verdictPetite(cpu, carte);
  exigerPasLaCarte(verdict, c, p);
  const tailles = taillesDe(cpu);
  exiger(
    tailles[0] === TAILLE_PETITE,
    `le tableau commence à ${tailles[0]} × ${tailles[0]}, et non au ${TAILLE_PETITE} × ${TAILLE_PETITE} du pari : ` +
      '« pour le plus petit produit » dans la phrase sous le tableau des chronos est à revoir',
  );
  // Combien de fois la carte va plus vite que le processeur au mieux de ses fils.
  const gain = (t: number) => meilleurChrono(cpu, t) / chrono(carte, t, null);
  const depasse = tailles.findIndex((t) => gain(t) >= SEUIL_AUTANT);
  const plusGrand = tailles[tailles.length - 1];
  exiger(
    depasse >= 0 && depasse < tailles.length - 1,
    'la carte ne dépasse le processeur qu’au plus grand produit, ou jamais : « dès … » et « pour … » de la phrase ' +
      'sous le tableau des chronos sont à revoir',
  );
  exiger(
    tailles.slice(depasse).every((t) => gain(t) >= SEUIL_AUTANT),
    `la carte dépasse le processeur dès ${tailles[depasse]} × ${tailles[depasse]}, puis plus à une taille au-dessus : ` +
      '« dès … » dans la phrase sous le tableau des chronos est à revoir',
  );
  // « Des dizaines de fois plus vite que lui, même avec tous ses fils » : contre tous les fils, et contre son meilleur réglage.
  const dizaines = (g: number) => g >= SEUIL_BIEN_PLUS_VITE && g < SEUIL_CENTAINES;
  const contreTous = chrono(cpu, plusGrand, cpu.fils_max) / chrono(carte, plusGrand, null);
  exiger(
    dizaines(contreTous),
    `au plus grand produit, la carte va ${nombre(contreTous, 1)} fois plus vite que le processeur avec tous ses fils : ` +
      '« des dizaines de fois » dans la phrase sous le tableau des chronos est à revoir',
  );
  const g = gain(plusGrand);
  exiger(
    dizaines(g),
    `au plus grand produit, la carte va ${nombre(g, 1)} fois plus vite que le processeur au mieux de ses fils : ` +
      '« des dizaines de fois » dans la phrase sous le tableau des chronos est à revoir',
  );
  // « au mieux de ses fils » : le verdict compare le meilleur chrono du processeur, comme explicationPetite (revue finale, m6).
  const auPlusPetit =
    verdict === 'processeur'
      ? 'le processeur, au mieux de ses fils, va plus vite que la carte'
      : 'le processeur, au mieux de ses fils, et la carte vont à peu près aussi vite';
  return (
    `Le tableau le montre${FINE}: pour le plus petit produit, ${auPlusPetit}${FINE}; ` +
    `dès ${ecrireTaille(tailles[depasse])}, la carte le dépasse, et pour ${ecrireTaille(plusGrand)}, ` +
    'elle va des dizaines de fois plus vite que lui, même avec tous ses fils.'
  );
}

/**
 * Le prix du transfert, au plus grand produit de la carte : la copie d'une
 * matrice vers la carte, face à son produit par une autre. « À peu près
 * autant » à 25 % près ; sinon « plus » ou « moins ».
 */
export function phraseTransfert(carte: MesuresChrono): string {
  exiger(
    carte.appareil === 'cuda' && carte.transfert_ms !== null,
    'la phrase du transfert attend les mesures de la carte, avec leurs copies vers la carte',
  );
  const plusGrand = taillesDe(carte).at(-1)!;
  const produit = chrono(carte, plusGrand, null);
  const copie = carte.transfert_ms![String(plusGrand)];
  exiger(copie !== undefined, `la copie d’une matrice ${plusGrand} × ${plusGrand} vers la carte n’a pas été mesurée`);
  const comparaison =
    copie > produit * SEUIL_A_PEU_PRES ? 'plus que' : produit > copie * SEUIL_A_PEU_PRES ? 'moins que' : 'à peu près autant que';
  return (
    `Copier une matrice ${ecrireTaille(plusGrand)} sur la carte de ce PC prend ${ecrireMillisecondes(copie)}${INSECABLE}ms${FINE}: ` +
    `${comparaison} de la multiplier par une autre, ${ecrireMillisecondes(produit)}${INSECABLE}ms.`
  );
}
