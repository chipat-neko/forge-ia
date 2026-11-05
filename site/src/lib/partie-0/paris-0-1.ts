// Les paris du chapitre 0.1, « Python pour l'IA », et ce que leurs
// explications affirment.
//
// Leurs bonnes réponses sont calculées : par JavaScript lui-même pour les
// nombres à virgule (le même calcul IEEE 754 qu'en Python), et par le jumeau du
// mot suivant (mot-suivant.ts) pour les mots. Rien n'est recopié. Si le texte
// ou le jumeau change et qu'une phrase de la page devient fausse, la
// construction s'arrête (« Exemple devenu faux : … »).
//
// Les fonctions qui lisent le texte le reçoivent en argument : ce module
// n'importe ni ?raw, ni .json, ni astro:* (B1). Le chapitre leur passe
// TEXTE_DE_DEPART (texte-0-1.ts), et les parcours de test le texte lu sur le
// disque. L'atelier (AtelierMotSuivant.svelte) y prend ses réglages et son défi.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { comparerPointsDeCode } from '../points-de-code';
import { compterSuivants, decouperMots, generer, predire, premiereReprise, suivantsTries } from './mot-suivant';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-0/paris-0-1.ts et le texte des paris du chapitre 0.1');

/** Le mot de départ des paris « suivant » et « boucle », et de l'atelier à l'arrivée. */
export const MOT_DU_PARI = 'le';
/** La longueur de la suite du pari « boucle ». */
export const LONGUEUR_DU_PARI = 20;

/** Les réglages de la longueur de l'atelier : de 1 à 30 mots, 20 à l'arrivée. */
export const LONGUEUR_MIN = 1;
export const LONGUEUR_MAX = 30;
export const LONGUEUR_INITIALE = 20;

/** Le défi de l'atelier : une suite d'au moins SEUIL_DU_DEFI mots, sans reprise. */
export const SEUIL_DU_DEFI = 15;
/** Ce que l'atelier affiche quand le défi est réussi. */
export const DEFI_REUSSI = `Défi réussi${FINE}: ${SEUIL_DU_DEFI} mots ou plus, sans boucle.`;

/** La liste du pari « tranche ». */
export const LISTE_DU_PARI: readonly string[] = Object.freeze(['le', 'forgeron', 'frappe']);

/**
 * Le mot de l'ouverture du chapitre : « Après « des », ce texte met le plus
 * souvent … ». Pas « le » : l'ouverture donnerait la réponse du pari de l'étape 5.
 */
export const MOT_D_OUVERTURE = 'des';

/** Vrai si le mot contient au moins une lettre : « le », mais pas « . ». */
function avecLettre(mot: string): boolean {
  return /\p{L}/u.test(mot);
}

/** Une chaîne écrite comme Python l'affiche dans une liste : 'fer', ou "l'eau". */
function reprChaine(s: string): string {
  const sansBarre = s.replace(/\\/g, '\\\\');
  // Python prend les guillemets doubles quand la chaîne contient une apostrophe et aucun guillemet double.
  if (s.includes("'") && !s.includes('"')) return `"${sansBarre}"`;
  return `'${sansBarre.replace(/'/g, "\\'")}'`;
}

/** Une liste de chaînes écrite comme Python l'affiche : ['le', 'forgeron']. */
export function reprListePython(l: readonly string[]): string {
  return `[${l.map(reprChaine).join(', ')}]`;
}

// ---------- Étape 2 : les nombres à virgule ----------

/** La somme 0.1 + 0.2 telle que Python et JavaScript l'affichent : le plus court texte qui redonne ce nombre. */
export const SOMME_DES_FLOTTANTS = String(0.1 + 0.2);

/**
 * Le pari « Que répond Python à `0.1 + 0.2 == 0.3` ? ». Les nombres à virgule
 * de JavaScript et de Python suivent la même norme (IEEE 754, double
 * précision) : le calcul fait ici donne la réponse de Python.
 */
export function choixFlottants(): Choix[] {
  const egal = 0.1 + 0.2 === 0.3;
  exiger(!egal, '0.1 + 0.2 vaut exactement 0.3 : l’explication de l’arrondi ne tient plus');
  return [
    { texte: '`True`', juste: egal },
    { texte: '`False`', juste: !egal },
    // Comparer deux nombres ne lève jamais d'erreur, ni en Python ni en JavaScript.
    { texte: 'Une erreur', juste: false },
  ];
}

// ---------- Étape 3 : les tranches ----------

/**
 * Le pari « que donne `mots[1:]` ? » sur LISTE_DU_PARI. La bonne réponse est
 * la tranche calculée ; les deux autres sont les erreurs courantes : prendre
 * les deux premiers (mots[:2]), ou seulement l'élément d'indice 1 (mots[1:2]).
 */
export function choixTranche(): Choix[] {
  const juste = reprListePython(LISTE_DU_PARI.slice(1));
  const textes = [LISTE_DU_PARI.slice(0, 2), LISTE_DU_PARI.slice(1), LISTE_DU_PARI.slice(1, 2)].map(reprListePython);
  exiger(new Set(textes).size === 3, 'deux choix du pari sur les tranches ont le même texte');
  return textes.map((texte) => ({ texte: `\`${texte}\``, juste: texte === juste }));
}

// ---------- Étape 5 : le mot suivant ----------

/** Ce que le pari « suivant » montre d'un mot : ses suivants triés, et le troisième choix. */
interface FaitsDuMot {
  mot: string;
  /** Les suivants du mot et leurs comptes, triés comme suivantsTries. */
  suivants: [string, number][];
  /** Le mot le plus fréquent du texte (fait de lettres) qui ne suit jamais `mot`, et son compte. */
  troisieme: { mot: string; fois: number } | null;
}

/** Les faits du pari pour un mot, sans garde. */
function faitsDuMot(texte: string, mot: string): FaitsDuMot {
  const mots = decouperMots(texte);
  const compte = compterSuivants(mots).get(mot) ?? new Map<string, number>();
  // Le troisième choix : un mot fait de lettres (un point serait un choix déroutant), autre que le
  // mot lui-même, qui ne le suit jamais ; le plus fréquent, puis le premier par point de code.
  const frequences = new Map<string, number>();
  for (const m of mots) frequences.set(m, (frequences.get(m) ?? 0) + 1);
  const candidats = [...frequences]
    .filter(([m]) => avecLettre(m) && m !== mot && !compte.has(m))
    .sort(([a, na], [b, nb]) => nb - na || comparerPointsDeCode(a, b));
  return {
    mot,
    suivants: suivantsTries(compte),
    troisieme: candidats.length > 0 ? { mot: candidats[0][0], fois: candidats[0][1] } : null,
  };
}

/** Vrai si le mot fait un bon pari : deux suivants au moins, le premier seul en tête, et un troisième choix. */
function passeLesGardes(faits: FaitsDuMot): boolean {
  const [premier, deuxieme] = faits.suivants;
  return deuxieme !== undefined && premier[1] > deuxieme[1] && faits.troisieme !== null;
}

/**
 * Le mot des paris « suivant » et « boucle » : MOT_DU_PARI s'il passe les
 * gardes (deux suivants au moins, le premier seul en tête, et un troisième
 * choix possible). Sinon, si le texte change et que « le » ne convient plus,
 * le premier mot du texte, fait de lettres, qui les passe toutes : la page
 * reste juste, avec un autre mot.
 */
export function motDuPari(texte: string): string {
  if (passeLesGardes(faitsDuMot(texte, MOT_DU_PARI))) return MOT_DU_PARI;
  for (const mot of new Set(decouperMots(texte))) {
    if (avecLettre(mot) && passeLesGardes(faitsDuMot(texte, mot))) return mot;
  }
  exiger(false, 'aucun mot du texte n’a deux suivants dont le premier est seul en tête, avec un troisième choix');
  return MOT_DU_PARI; // jamais atteint : exiger a levé l'erreur
}

/** Les faits du pari « suivant », pour son explication : suivants triés et troisième choix. */
export function faitsDuPariSuivant(texte: string): {
  mot: string;
  suivants: [string, number][];
  troisieme: { mot: string; fois: number };
} {
  const faits = faitsDuMot(texte, motDuPari(texte));
  return { mot: faits.mot, suivants: faits.suivants, troisieme: faits.troisieme! };
}

/**
 * Le pari « Dans ce texte, quel mot suit le plus souvent « le » ? ». Les
 * choix : le premier suivant (le juste, celui que prédit le jumeau), le
 * deuxième, et le mot le plus fréquent du texte qui ne suit jamais « le ».
 * Ils sont rangés par point de code : la bonne réponse n'a pas de place fixe.
 */
export function choixMotSuivant(texte: string): Choix[] {
  const { mot, suivants, troisieme } = faitsDuPariSuivant(texte);
  const prediction = predire(compterSuivants(decouperMots(texte)), mot);
  exiger(prediction === suivants[0][0], `le mot prédit après « ${mot} » n’est pas le premier de ses suivants triés`);
  return [suivants[0][0], suivants[1][0], troisieme.mot]
    .sort(comparerPointsDeCode)
    .map((m) => ({ texte: `« ${m} »`, juste: m === prediction }));
}

// ---------- Étape 6 : la boucle ----------

/**
 * Les choix du pari « boucle », selon la suite obtenue. Exactement un est
 * juste par construction : la suite ne dépend que de son dernier mot, donc dès
 * qu'un mot revient, elle tourne en rond jusqu'au bout et ne peut pas
 * s'arrêter ; et une suite qui s'arrête n'a pas eu de reprise.
 */
export function choixSelonLaSuite(suite: readonly string[], longueur: number): Choix[] {
  const boucle = premiereReprise(suite) !== null;
  const courte = suite.length < longueur;
  const choix = [
    { texte: 'Une boucle : les mêmes mots reviennent', juste: boucle },
    { texte: 'Une suite de mots qui ne se répète jamais', juste: !boucle && !courte },
    { texte: `Elle s'arrête avant ${longueur} mots`, juste: courte },
  ];
  exiger(choix.filter((c) => c.juste).length === 1, 'le pari sur la boucle n’a pas exactement un choix juste');
  return choix;
}

/** La suite du pari « boucle », sa première reprise et les mots qui tournent en rond. */
export function boucleDuPari(texte: string): { mot: string; suite: string[]; reprise: number; cycle: string[] } {
  const mot = motDuPari(texte);
  const suite = generer(compterSuivants(decouperMots(texte)), mot, LONGUEUR_DU_PARI);
  const reprise = premiereReprise(suite);
  exiger(
    reprise !== null,
    `la suite de ${LONGUEUR_DU_PARI} mots qui part de « ${mot} » ne revient sur aucun mot : ` +
      'le pari et son explication disent qu’elle tourne en rond',
  );
  // Le mot repris est apparu une première fois plus tôt : de là à la reprise, les mêmes mots se répètent.
  const debut = suite.indexOf(suite[reprise!]);
  return { mot, suite, reprise: reprise!, cycle: suite.slice(debut, reprise!) };
}

/** Le pari « Que donne une suite de 20 mots qui part de « le » ? ». */
export function choixBoucle(texte: string): Choix[] {
  const mot = motDuPari(texte);
  return choixSelonLaSuite(generer(compterSuivants(decouperMots(texte)), mot, LONGUEUR_DU_PARI), LONGUEUR_DU_PARI);
}

// ---------- L'atelier ----------

/** Le défi de l'atelier : une suite d'au moins SEUIL_DU_DEFI mots, sans reprise. */
export function defiReussi(suite: readonly string[]): boolean {
  return suite.length >= SEUIL_DU_DEFI && premiereReprise(suite) === null;
}

// ---------- L'ouverture ----------

/**
 * L'ouverture du chapitre : la première phrase du texte, ses mots tels que le
 * programme les découpe, et le mot qui suit le plus souvent MOT_D_OUVERTURE
 * dans tout le texte (`fois` sur `total`).
 */
export function ouvertureDuChapitre(texte: string): {
  phrase: string;
  mots: string[];
  mot: string;
  suivant: string;
  fois: number;
  total: number;
} {
  const fin = /[.!?]/.exec(texte);
  exiger(fin !== null, 'le texte n’a pas de première phrase (aucun point)');
  const phrase = texte.slice(0, fin!.index + 1);
  const mot = MOT_D_OUVERTURE;
  exiger(mot !== motDuPari(texte), `l’ouverture parle de « ${mot} », le mot du pari de l’étape 5 : elle en donnerait la réponse`);
  const tries = suivantsTries(compterSuivants(decouperMots(texte)).get(mot) ?? new Map());
  exiger(
    tries.length >= 2 && tries[0][1] > tries[1][1],
    `après « ${mot} », le texte n’a pas un suivant seul en tête : l’ouverture dit « le plus souvent »`,
  );
  let total = 0;
  for (const [, n] of tries) total += n;
  return { phrase, mots: decouperMots(phrase), mot, suivant: tries[0][0], fois: tries[0][1], total };
}
