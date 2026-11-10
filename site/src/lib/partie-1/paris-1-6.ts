// Les paris du chapitre 1.6, « Évaluer son modèle », l'atelier des QCM et son défi, et ce que le
// chapitre lit autour d'eux.
//
// Leurs bonnes réponses sont calculées, jamais tapées :
// - la perplexité du hasard, par sa définition : l'exponentielle de la perte ln V ;
// - la tranche des bits par octet, et le verdict de HellaSwag (par la règle de forge, verdictQcm),
//   sur le rapport d'évaluation de la version d'une heure de ton IA (mesures/evaluation-mini.json
//   du projet 1.6, que le chapitre lit avec evaluation.ts) ;
// - la réponse que ton IA préfère, question par question, sur les QCM de MMMLU qu'elle a notés
//   (mesures/qcm-mini.json) ;
// - la langue d'origine de FrenchBench, et sa traduction, d'après sa source (sources-1-6.ts).
// Si une mesure change et qu'une phrase du chapitre devient fausse, la construction s'arrête
// (« Exemple devenu faux : … »).
//
// Ce module n'importe que des modules sans node:fs, ni ?raw, ni .json, ni astro:* (les types de
// evaluation.ts s'effacent à la compilation) : l'atelier des QCM, dans le navigateur, et les
// parcours Playwright peuvent l'importer. Le chapitre lui passe les relevés.

import type { Choix } from '../choix';
import { VOCABULAIRE_FORGE } from '../calculateur/ton-ia';
import { exigeur } from '../exiger';
import { decimalesUtiles, nombre } from '../nombres';
import type { EchantillonEvaluation, Evaluation, QcmExemples } from './evaluation';
import { margeHasard, verdictQcm, type Verdict } from './marge';
import { FRENCHBENCH, type Traduction } from './sources-1-6';

const FINE = '\u202F';

const exiger = exigeur('src/lib/partie-1/paris-1-6.ts et le texte des paris du chapitre 1.6');

/** Une tranche d'un pari : son texte, et la valeur sous laquelle elle s'arrête (non comprise). */
export interface Tranche {
  texte: string;
  jusqua: number;
}

/** Le rang de la tranche qui contient `x` : la première dont la borne est au-dessus. */
function rangDeTranche(tranches: readonly Tranche[], x: number): number {
  const rang = tranches.findIndex((t) => x < t.jusqua);
  exiger(rang >= 0, `${String(x)} ne tombe dans aucune tranche`);
  return rang;
}

// ---------- Étape 2 : le pari « hasard » ----------

/** Les perplexités proposées par le pari, de la plus petite à la plus grande. */
export const PERPLEXITES_PROPOSEES: readonly number[] = Object.freeze([2, 100, VOCABULAIRE_FORGE]);

/**
 * La perplexité d'un modèle qui tire chaque jeton au hasard parmi `vocabulaire` : chaque jeton a la
 * chance 1/V, sa perte est −ln(1/V) = ln V, et la perplexité l'exponentielle de cette perte.
 */
export function perplexiteDuHasard(vocabulaire: number): number {
  if (!Number.isInteger(vocabulaire) || vocabulaire < 1) {
    throw new RangeError(`perplexiteDuHasard : ${String(vocabulaire)} n’est pas une taille de vocabulaire (un entier, au moins 1).`);
  }
  const perte = -Math.log(1 / vocabulaire);
  return Math.exp(perte);
}

/**
 * Le pari « Un modèle qui tire chaque jeton au hasard parmi les 32 768 a une perplexité de… ». Le
 * juste est le choix égal (aux arrondis près) à perplexiteDuHasard(VOCABULAIRE_FORGE).
 */
export function choixPerplexiteHasard(): Choix[] {
  const hasard = perplexiteDuHasard(VOCABULAIRE_FORGE);
  const choix = PERPLEXITES_PROPOSEES.map((p) => ({ texte: nombre(p), juste: Math.abs(p - hasard) < 1e-9 * hasard }));
  exiger(choix.filter((c) => c.juste).length === 1, 'aucun choix du pari « hasard » n’est la perplexité du hasard');
  return choix;
}

/**
 * Les faits de l'explication du pari « hasard » : le vocabulaire, la perte du hasard (ln V), la
 * perplexité de ton IA (sa version d'une heure), et combien de fois elle est plus petite que celle
 * du hasard.
 */
export function faitsDuPariHasard(e: Evaluation): {
  vocabulaire: number;
  perteHasard: number;
  perplexite: number;
  hesitation: number;
  fois: number;
} {
  exiger(e.perplexite > 1 && e.perplexite < VOCABULAIRE_FORGE, 'la perplexité de ton IA n’est plus entre 1 et celle du hasard');
  return {
    vocabulaire: VOCABULAIRE_FORGE,
    perteHasard: Math.log(VOCABULAIRE_FORGE),
    perplexite: e.perplexite,
    // « Comme si elle hésitait entre N jetons » : la perplexité, arrondie.
    hesitation: Math.round(e.perplexite),
    fois: perplexiteDuHasard(VOCABULAIRE_FORGE) / e.perplexite,
  };
}

// ---------- Étape 3 : le pari « bits » ----------

/** Un fichier de texte range chaque octet sur 8 bits. */
export const BITS_PAR_OCTET_D_UN_FICHIER = 8;

/** Les trois tranches du pari « bits », en bits par octet. */
export const TRANCHES_BITS: readonly Tranche[] = Object.freeze([
  Object.freeze({ texte: 'Moins de 2', jusqua: 2 }),
  Object.freeze({ texte: `De 2 à ${BITS_PAR_OCTET_D_UN_FICHIER}`, jusqua: BITS_PAR_OCTET_D_UN_FICHIER }),
  Object.freeze({ texte: `Au moins ${BITS_PAR_OCTET_D_UN_FICHIER}`, jusqua: Infinity }),
]);

/** La tranche d'un nombre de bits par octet : 0 sous 2, 1 de 2 (compris) à 8, 2 à partir de 8 (« Au moins 8 », sans chiffre en tête : le pari ne l'affiche pas en grand). */
export function trancheDesBits(bits: number): number {
  return rangDeTranche(TRANCHES_BITS, bits);
}

/** Les faits de l'explication du pari « bits », tirés du rapport d'évaluation. */
export interface FaitsDesBits {
  /** Les bits par octet du rapport. */
  bits: number;
  /** La perte, comptée en bits par jeton : perte / ln 2. */
  bitsParJeton: number;
  /** Les octets de texte d'un jeton, en moyenne : ce que forge a divisé (perte / ln 2 / bits par octet). */
  octetsParJeton: number;
  /** La perte d'un modèle qui lirait octet par octet et prédirait aussi bien : bits × ln 2, en nats. */
  perteParOctet: number;
  /** Sa perplexité : exp(perteParOctet), soit 2 puissance les bits par octet. */
  perplexiteParOctet: number;
  /** Combien de fois moins de place qu'un fichier, en théorie : 8 / bits. */
  foisPlusPetit: number;
}

/**
 * Les faits du pari « bits ». Les octets par jeton ne sont pas dans le rapport : forge a calculé les
 * bits par octet comme perte / ln 2 / octets par jeton, on les retrouve donc en divisant. Garde : un
 * jeton couvre plusieurs octets, et ton IA prédit mieux qu'un fichier ne range.
 */
export function faitsDesBits(e: Evaluation): FaitsDesBits {
  const bitsParJeton = e.perte_val / Math.LN2;
  const octetsParJeton = bitsParJeton / e.bits_par_octet;
  exiger(octetsParJeton > 1, 'un jeton de ton IA ne couvre plus plusieurs octets de texte en moyenne');
  exiger(e.bits_par_octet < BITS_PAR_OCTET_D_UN_FICHIER, 'ton IA ne fait plus mieux que les 8 bits par octet d’un fichier');
  const perteParOctet = e.bits_par_octet * Math.LN2;
  return {
    bits: e.bits_par_octet,
    bitsParJeton,
    octetsParJeton,
    perteParOctet,
    perplexiteParOctet: Math.exp(perteParOctet),
    foisPlusPetit: BITS_PAR_OCTET_D_UN_FICHIER / e.bits_par_octet,
  };
}

/** Le pari « combien de bits par octet ? » : la bonne tranche est celle des bits par octet du rapport. */
export function choixBits(e: Evaluation): Choix[] {
  const juste = trancheDesBits(faitsDesBits(e).bits);
  return TRANCHES_BITS.map((t, i) => ({ texte: t.texte, juste: i === juste }));
}

// ---------- Étape 4 : l'atelier des QCM ----------

/** L'indice du plus grand score ; à égalité parfaite, le premier (comme choix_prefere du projet et forge). */
export function premierMax(scores: readonly number[]): number {
  if (scores.length === 0) throw new RangeError('premierMax : il faut au moins un score.');
  let meilleur = 0;
  scores.forEach((s, i) => {
    if (s > scores[meilleur]) meilleur = i;
  });
  return meilleur;
}

/** La question `i` du relevé, ou une erreur claire. */
function question(qcm: QcmExemples, i: number) {
  const q = qcm.questions[i];
  if (q === undefined) {
    throw new RangeError(`La question ${String(i)} n’existe pas : le relevé en a ${qcm.questions.length} (de 0 à ${qcm.questions.length - 1}).`);
  }
  return q;
}

/**
 * Le pari de l'atelier, sur la question `i` du relevé : les réponses possibles (sans l'espace qui les
 * colle à la question), et juste celle que ton IA préfère, celle de plus grand score normalisé. Garde :
 * c'est bien la préférence notée dans le relevé.
 */
export function choixPrefere(qcm: QcmExemples, i: number): Choix[] {
  const q = question(qcm, i);
  exiger(premierMax(q.scores_normalises) === q.prefere, `la préférence notée à la question ${i + 1} n’est plus le plus grand score normalisé`);
  return q.choix.map((c, j) => ({ texte: c.trim(), juste: j === q.prefere }));
}

/**
 * La longueur de chaque barre, de 0 à 1 : exp(score − meilleur score). La réponse préférée a 1 ; une
 * autre, la vraisemblance par octet qu'elle a, rapportée à celle de la préférée.
 */
export function largeursDesBarres(scores: readonly number[]): number[] {
  const meilleur = scores[premierMax(scores)];
  return scores.map((s) => Math.exp(s - meilleur));
}

/** Le compte final de l'atelier : les réponses justes de ton IA, les questions, et ce que donne le hasard en moyenne. */
export interface CompteDuQcm {
  justes: number;
  n: number;
  /** Le nombre moyen de réponses justes d'un tirage au sort : la somme des 1 / nombre de choix. */
  hasard: number;
}

/** Le compte de l'atelier. Garde : le hasard moyen est bien n fois le hasard du relevé. */
export function compteDuQcm(qcm: QcmExemples): CompteDuQcm {
  let hasard = 0;
  for (const q of qcm.questions) hasard += 1 / q.choix.length;
  exiger(Math.abs(hasard - qcm.n * qcm.hasard) < 1e-9, 'le hasard du relevé des QCM n’est plus la moyenne des 1 / nombre de choix');
  return { justes: qcm.questions.filter((q) => q.juste).length, n: qcm.questions.length, hasard };
}

/** « Ton IA : 2 sur 6, le hasard : 1,5 en moyenne. » */
export function texteDuCompte(c: CompteDuQcm): string {
  return `Ton IA${FINE}: ${nombre(c.justes)} sur ${nombre(c.n)}, le hasard${FINE}: ${nombre(c.hasard, decimalesUtiles(c.hasard, 2))} en moyenne.`;
}

/** Les indices des questions où ton IA préfère la bonne réponse. */
export function questionsJustes(qcm: QcmExemples): number[] {
  return qcm.questions.flatMap((q, i) => (q.juste ? [i] : []));
}

/**
 * L'état du défi : les questions où ton IA a juste que le lecteur a déjà vues (dans `vues`, les
 * indices des questions dont il a vu les barres). Réussi dès la première.
 */
export function etatDuDefi(vues: readonly number[], qcm: QcmExemples): { reussi: boolean; trouvees: number; texte: string } {
  const justes = questionsJustes(qcm);
  const trouvees = justes.filter((i) => vues.includes(i)).length;
  const total = justes.length;
  if (trouvees === 0) return { reussi: false, trouvees, texte: `Pas encore${FINE}: aucune question trouvée où ton IA a juste.` };
  const s = trouvees > 1 ? 's' : '';
  return { reussi: true, trouvees, texte: `Défi réussi${FINE}: ${nombre(trouvees)} question${s} trouvée${s} sur ${nombre(total)} où ton IA a juste.` };
}

/** Ce que les scores disent d'une question où ton IA a juste. */
export interface AnalyseDeQuestion {
  /** La question, à partir de 0. */
  indice: number;
  /** La réponse que ton IA préfère, ici la bonne. */
  prefere: number;
  /** L'avance de la réponse préférée sur la suivante, en nats par octet. */
  avance: number;
  /** Le rang de cette avance parmi celles de toutes les questions : 1, la plus nette. */
  rang: number;
  /** La réponse qu'elle aurait préférée sans diviser par les octets : le plus grand score brut. */
  sansNormaliser: number;
  /** La réponse la plus courte, en octets. */
  plusCourte: number;
}

/** L'avance de la réponse préférée sur la meilleure des autres, en scores normalisés. */
function avance(scores: readonly number[], prefere: number): number {
  let suivante = -Infinity;
  scores.forEach((s, j) => {
    if (j !== prefere && s > suivante) suivante = s;
  });
  return scores[prefere] - suivante;
}

/** Les octets UTF-8 d'une réponse, espace initiale comprise, comme octets_du_choix du projet. */
function octets(texte: string): number {
  return new TextEncoder().encode(texte).length;
}

/**
 * La réponse du défi : pour chaque question où ton IA a juste, ce que disent ses scores, et, sur
 * toutes les questions, le verdict de son compte face au hasard (la règle de forge, avec la marge du
 * hasard de n questions). Garde : il y a au moins une question où elle a juste, et toutes les
 * questions ont le même nombre de choix (la marge du projet le suppose).
 */
export function analyseDuDefi(qcm: QcmExemples): { questions: AnalyseDeQuestion[]; n: number; verdict: Verdict } {
  const avances = qcm.questions.map((q) => avance(q.scores_normalises, q.prefere));
  const justes = questionsJustes(qcm);
  exiger(justes.length > 0, 'ton IA n’a plus aucune question juste : le défi n’a plus de réponse');
  const choix = qcm.questions[0].choix.length;
  exiger(
    qcm.questions.every((q) => q.choix.length === choix),
    'les questions de l’atelier n’ont plus toutes le même nombre de choix',
  );
  const questions = justes.map((i) => {
    const q = qcm.questions[i];
    const longueurs = q.choix.map(octets);
    return {
      indice: i,
      prefere: q.prefere,
      avance: avances[i],
      rang: 1 + avances.filter((a) => a > avances[i]).length,
      sansNormaliser: premierMax(q.scores),
      plusCourte: premierMax(longueurs.map((l) => -l)),
    };
  });
  const c = compteDuQcm(qcm);
  return { questions, n: c.n, verdict: verdictQcm(c.justes / c.n, c.hasard / c.n, margeHasard(c.n, choix)) };
}

/** « nat » ou « nats » : le pluriel à partir de 2. */
function nats(x: number, decimales: number): string {
  return `${nombre(x, decimales)} ${Math.abs(Number(x.toFixed(decimales))) >= 2 ? 'nats' : 'nat'}`;
}

/** La place d'une avance parmi toutes les questions, en mots. */
function placeDeLAvance(rang: number, n: number): string {
  if (rang === 1) return 'l’avance la plus nette';
  if (rang === n) return 'l’avance la plus mince';
  if (rang === 2) return 'la deuxième avance la plus nette';
  if (rang === n - 1) return 'la deuxième avance la plus mince';
  return 'une avance moyenne';
}

/**
 * Une phrase par question où ton IA a juste : son avance, sa place parmi toutes les questions, et, si
 * la division par les octets a changé son choix, celui qu'elle aurait fait sans elle.
 */
export function phrasesDuDefi(analyse: { questions: AnalyseDeQuestion[]; n: number }): string[] {
  return analyse.questions.map((a) => {
    const phrase =
      `À la question ${nombre(a.indice + 1)}, la bonne réponse devance la suivante de ${nats(a.avance, 2)} par octet${FINE}: ` +
      `c’est ${placeDeLAvance(a.rang, analyse.n)} des ${nombre(analyse.n)} questions.`;
    if (a.sansNormaliser === a.prefere) return phrase;
    // Le plus grand score brut n'est pas la bonne réponse : sans diviser par les octets, elle se trompait.
    const laquelle = a.sansNormaliser === a.plusCourte ? 'la réponse la plus courte' : 'une autre réponse';
    return `${phrase} Sans diviser par les octets, elle aurait choisi ${laquelle}, et se serait trompée.`;
  });
}

// ---------- Étape 5 : le pari « marge » ----------

/** Les verdicts, dans l'ordre du pari. */
export const ORDRE_DES_VERDICTS: readonly Verdict[] = Object.freeze(['au-dessus', 'pas-different', 'en-dessous']);

/** Les choix du pari « marge », en tête de phrase. */
export const TEXTES_VERDICT: Readonly<Record<Verdict, string>> = Object.freeze({
  'au-dessus': 'Au-dessus du hasard',
  'pas-different': 'Pas différent du hasard',
  'en-dessous': 'En dessous du hasard',
});

/** Un verdict de forge en français, au fil d'une phrase : « au-dessus du hasard », « pas différent du hasard »… */
export function verdictEnPhrase(v: Verdict): string {
  return TEXTES_VERDICT[v].replace(/^./, (c) => c.toLowerCase());
}

/**
 * Le pari « Le score de ton IA sur HellaSwag est… » : la bonne réponse vient de la règle de forge
 * (verdictQcm), sur l'exactitude normalisée, le hasard et la marge du hasard du rapport. Garde : c'est
 * le verdict noté dans le relevé.
 */
export function choixAuDessusDuHasard(e: Evaluation): Choix[] {
  const m = e.qcm.hellaswag;
  const v = verdictQcm(m.exactitude_normalisee, m.hasard, m.marge_hasard);
  exiger(v === m.verdict, `le verdict de HellaSwag du relevé (${m.verdict}) n’est plus celui de la règle de forge (${v})`);
  return ORDRE_DES_VERDICTS.map((x) => ({ texte: TEXTES_VERDICT[x], juste: x === v }));
}

// ---------- Étape 6 : les échantillons ----------

/** Les faits que le chapitre dit des échantillons d'un rapport d'évaluation. */
export interface FaitsDesEchantillons {
  nombre: number;
  /** Le nombre de jetons de chaque texte, le même pour tous. */
  jetons: number;
  /** Aucun texte ne s'est arrêté de lui-même avant ses jetons. */
  aucunNeSArrete: boolean;
  /** Les débuts de fonction Python, parmi les débuts. */
  debutsDeCode: number;
  /** Après « def factorielle(n): », la suite commence par une ligne indentée de quatre espaces. */
  codeIndente: boolean;
  /** La suite du code finit par une licence, puis une autre fonction. */
  codeSansSuite: boolean;
  /** La suite de la docstring passe à l'anglais. */
  docstringEnAnglais: boolean;
  /** Chaque suite en français a des points et des virgules. */
  prosePonctuee: boolean;
  /** Après « La capitale de la France est », la suite ne dit pas « Paris ». */
  capitaleSansParis: boolean;
  /** Après « La photosynthèse est le processus par lequel », la suite ne parle ni de lumière ni de plantes. */
  photosyntheseHorsSujet: boolean;
  /** Après « Le soleil se couchait sur la mer et », combien de fois revient « le soleil se couchait ». */
  soleilRepete: number;
  /** Après « Dans un petit village de Bretagne, », la suite donne un nombre (une date). */
  villageDate: boolean;
}

/** L'échantillon d'une invite, ou une erreur qui nomme l'invite. */
function echantillon(e: Evaluation, invite: string): EchantillonEvaluation {
  const x = e.echantillons.find((y) => y.invite === invite);
  exiger(x !== undefined, `le rapport n’a plus d’échantillon qui part de « ${invite} »`);
  return x!;
}

/** Les faits des échantillons d'un rapport, que les phrases du chapitre affirment. */
export function faitsDesEchantillons(e: Evaluation): FaitsDesEchantillons {
  const jetons = e.echantillons[0].n_jetons;
  exiger(
    e.echantillons.every((x) => x.n_jetons === jetons),
    'les échantillons n’ont plus tous le même nombre de jetons',
  );
  const soleil = echantillon(e, 'Le soleil se couchait sur la mer et').suite.toLowerCase();
  const code = echantillon(e, 'def factorielle(n):\n').suite;
  return {
    nombre: e.echantillons.length,
    jetons,
    aucunNeSArrete: e.echantillons.every((x) => !x.s_arrete),
    debutsDeCode: e.echantillons.filter((x) => x.invite.startsWith('def ')).length,
    codeIndente: /^ {4}\S/.test(code),
    codeSansSuite: /License/.test(code) && /\ndef /.test(code),
    docstringEnAnglais: /\bReturns\b/.test(echantillon(e, 'def moyenne(valeurs):\n    """Renvoie la moyenne').suite),
    prosePonctuee: e.echantillons.filter((x) => !x.invite.startsWith('def ')).every((x) => x.suite.includes('.') && x.suite.includes(',')),
    capitaleSansParis: !echantillon(e, 'La capitale de la France est').suite.includes('Paris'),
    photosyntheseHorsSujet: !/lumi|plante|soleil|chlorophylle/i.test(echantillon(e, 'La photosynthèse est le processus par lequel').suite),
    soleilRepete: soleil.split('le soleil se couchait').length - 1,
    villageDate: /\d/.test(echantillon(e, 'Dans un petit village de Bretagne,').suite),
  };
}

// ---------- Étape 7 : le pari « limites » ----------

/** Une origine possible des questions de FrenchBench : leur langue, et leur traduction s'il y en a une. */
interface Origine {
  texte: string;
  langue: string;
  traduction: Traduction | null;
}

/** Les trois choix du pari « limites », qui complètent « Les questions de FrenchBench… ». */
export const ORIGINES_FRENCHBENCH: readonly Origine[] = Object.freeze([
  Object.freeze({ texte: 'ont été écrites en français', langue: 'français', traduction: null }),
  Object.freeze({ texte: 'ont été traduites de l’anglais par des traducteurs', langue: 'anglais', traduction: 'humaine' as const }),
  Object.freeze({ texte: 'ont été traduites de l’anglais par une machine', langue: 'anglais', traduction: 'automatique' as const }),
]);

/**
 * Le pari « Les questions de FrenchBench, qui notent ton IA… » : le juste est l'origine que donne sa
 * source (l'article de CroissantLLM, relevé dans sources-1-6.ts).
 */
export function choixLangueFrenchBench(): Choix[] {
  const choix = ORIGINES_FRENCHBENCH.map((o) => ({
    texte: o.texte,
    juste: o.langue === FRENCHBENCH.langueDOrigine.valeur && o.traduction === FRENCHBENCH.traduction.valeur,
  }));
  exiger(choix.filter((c) => c.juste).length === 1, 'aucun choix du pari « limites » n’est l’origine relevée de FrenchBench');
  return choix;
}
