// Le relevé du calculateur : à partir d'un réglage (modèle, jetons par
// paramètre, cartes, carte, efficacité), tous les nombres et toutes les
// phrases que le composant Calculateur affiche, et le détail de chaque
// formule (« Voir le calcul »).
//
// Tout vient des formules (formules.ts), des données sourcées (donnees.ts) et
// de ton IA (ton-ia.ts) : rien n'est recopié. Le composant ne fait que mettre
// ces textes en page ; ils sont testés ici (releve.test.ts).
//
// Une quantité garde son nombre et son unité ensemble : l'espace entre les
// deux est insécable (U+00A0), une ligne ne se coupe jamais entre « 5,9 » et
// « jours ». Dans une formule, l'espace après ×, ÷, + et = est insécable
// aussi : un opérateur reste avec le nombre qui le suit, jamais seul en fin
// de ligne.
//
// Les octets se comptent comme la mémoire des cartes : 1 Go vaut 1 024³
// octets (1 Mo, 1 024² ; 1 To, 1 024 Go). Les explications de « Voir le
// calcul » le disent, et chaque étape affichée se refait à la main à partir
// des nombres affichés (releve.test.ts le vérifie).
//
// Ce module est en TypeScript pur, sans import propre à Vite : les parcours
// Playwright l'importent directement.

import { decimalesUtiles, nombre, pourcent } from '../nombres';
import {
  EFFICACITE_PAR_DEFAUT,
  ELECTRICITE,
  fourchettePrix,
  MATERIELS,
  materiel as materielDe,
  MODELES_PUBLICS,
  REPERES_EFFICACITE,
  SOURCES_FORMULES,
  TAUX_DE_CHANGE,
  type Categorie,
  type Materiel,
  type PrixLocation,
  type RepereEfficacite,
  type Source,
} from './donnees';
import {
  dixPuissance,
  formaterDollars,
  formaterDuree,
  formaterEnergie,
  formaterEuros,
  formaterGoPourLesCartes,
  formaterHeures,
  formaterOctets,
  formaterPrix,
  formaterPuissanceDeDix,
  formaterQuantite,
} from './formats';
import {
  cacheKvOctets,
  cartesMinimum,
  coutElectriciteEur,
  coutLocationUsd,
  dureeSecondes,
  energieKwh,
  memoireEntrainementOctets,
  memoirePoidsOctets,
  operationsEntrainement,
  plafondGenerationJetonsParSeconde,
  usdEnEur,
  type Forme,
} from './formules';
import {
  CLES_FORGE,
  dureeHeures,
  MATERIEL_DES_MESURES,
  MESURES_TON_IA,
  NOMS_TAILLES,
  PRESETS_FORGE,
  reperesTonIA,
  type CleForge,
  type RepereTonIA,
} from './ton-ia';

const FINE = '\u202F';
const INSECABLE = '\u00A0';
const FOIS = ` ×${INSECABLE}`;
const DIVISE = ` ÷${INSECABLE}`;
const PLUS = ` +${INSECABLE}`;
const EGAL = ` =${INSECABLE}`;
/** La phrase qui dit l'unité des octets, dans les explications de la mémoire. */
const OCTETS_BINAIRES =
  `Ici, 1${INSECABLE}Go vaut 1${FINE}024³ octets, comme la mémoire des cartes${FINE}; ` +
  `1${INSECABLE}Mo, 1${FINE}024² octets${FINE}; 1${INSECABLE}To, 1${FINE}024${INSECABLE}Go.`;

/** Le texte d'une quantité, ses espaces rendues insécables : « 5,9 jours » ne se coupe plus. */
const lie = (texte: string): string => texte.replace(/ /g, INSECABLE);

/** Un nombre de cartes : « 1 carte », « 16 384 cartes ». */
const cartesTexte = (n: number): string => lie(`${nombre(n)} ${n > 1 ? 'cartes' : 'carte'}`);

/** Un pourcentage entier réglé : « 50 % ». */
const pourcentRegle = (p: number): string => `${nombre(p)}${FINE}%`;

/** Une crête en 10¹² opérations par seconde : « 87,9 × 10¹² ». */
const crete = (tflops: number): string => `${nombre(tflops, decimalesUtiles(tflops, 1))}${FINE}×${FINE}${dixPuissance(12)}`;

/** Le nom d'une taille de ton IA : « ton IA « très grand » ». */
const nomTonIA = (cle: CleForge): string => `ton IA «${FINE}${NOMS_TAILLES[cle]}${FINE}»`;

// ---------- Les réglages proposés ----------

/** Les jetons lus par paramètre, au choix. */
export const JETONS_PAR_PARAMETRE_PROPOSES: readonly number[] = Object.freeze([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000]);
/** Le nombre de cartes, au choix : 1, 2, 4, …, 16 384. */
export const CARTES_PROPOSEES: readonly number[] = Object.freeze(Array.from({ length: 15 }, (_, i) => 2 ** i));
/** L'efficacité va de 10 à 70 %, de 1 en 1. */
export const EFFICACITE_MIN_POURCENT = 10;
export const EFFICACITE_MAX_POURCENT = 70;
/** La longueur du cache de la génération : 4 096 jetons, ou tout le contexte du modèle s'il est plus court. */
export const JETONS_DU_CACHE = 4096;

/** Un modèle que le calculateur sait estimer. */
export interface ModeleDuCalculateur {
  /** Une clé de forge (« tres_grand ») ou l'identifiant d'un modèle public (« llama-3-405b »). */
  id: string;
  nom: string;
  forme: Forme;
  /** La taille de ton IA, ou null pour un modèle public. */
  tonIA: CleForge | null;
  /** Les sources de la forme d'un modèle public (vide pour ton IA : forge les écrit). */
  sources: readonly Source[];
  note: string | null;
}

/** Les modèles du calculateur : les 5 tailles de ton IA (clés de forge), puis les modèles publics. */
export const MODELES_DU_CALCULATEUR: readonly ModeleDuCalculateur[] = Object.freeze([
  ...CLES_FORGE.map(
    (cle): ModeleDuCalculateur => ({ id: cle, nom: nomTonIA(cle), forme: PRESETS_FORGE[cle], tonIA: cle, sources: [], note: null }),
  ),
  ...MODELES_PUBLICS.map(
    (m): ModeleDuCalculateur => ({
      id: m.id,
      nom: m.nom,
      forme: m,
      tonIA: null,
      sources: [m.source, ...(m.autresSources ?? [])],
      note: m.note ?? null,
    }),
  ),
]);

/** Le modèle d'identifiant `id`. */
export function modeleDuCalculateur(id: string): ModeleDuCalculateur {
  const m = MODELES_DU_CALCULATEUR.find((x) => x.id === id);
  if (m === undefined) {
    throw new RangeError(
      `Calculateur : le modèle «${FINE}${id}${FINE}» n’existe pas. Les identifiants sont ${MODELES_DU_CALCULATEUR.map((x) => x.id).join(', ')}.`,
    );
  }
  return m;
}

/** Les groupes du sélecteur de modèle. */
export const GROUPES_MODELES = Object.freeze([
  { titre: 'Ton IA', modeles: MODELES_DU_CALCULATEUR.filter((m) => m.tonIA !== null) },
  { titre: 'Modèles publics', modeles: MODELES_DU_CALCULATEUR.filter((m) => m.tonIA === null) },
]);

const TITRES_CATEGORIES: Readonly<Record<Categorie, string>> = { 'grand-public': 'Chez toi', colab: 'Colab', 'centre-de-donnees': 'En location' };

/** Les groupes du sélecteur de carte, dans l'ordre de MATERIELS. */
export const GROUPES_MATERIELS = Object.freeze(
  (['grand-public', 'colab', 'centre-de-donnees'] as const).map((c) => ({
    titre: TITRES_CATEGORIES[c],
    materiels: MATERIELS.filter((m) => m.categorie === c),
  })),
);

/** Un réglage du calculateur. L'efficacité est en pourcentage entier, de 10 à 70. */
export interface Reglage {
  modele: string;
  materiel: string;
  cartes: number;
  jetonsParParametre: number;
  efficacitePourcent: number;
}

/** Un réglage de départ, tel que le plan 5 le passera au composant ; l'efficacité est une fraction (0,4), comme EFFICACITE_PAR_DEFAUT. */
export interface ReglageInitial {
  modele?: string;
  materiel?: string;
  cartes?: number;
  jetonsParParametre?: number;
  efficacite?: number;
}

/** L'efficacité par défaut de la catégorie d'une carte, en pourcentage entier (50 pour une carte grand public). */
export function efficaciteParDefautPourcent(materielId: string): number {
  return Math.round(EFFICACITE_PAR_DEFAUT[materielDe(materielId).categorie] * 100);
}

function refuser(quoi: string, recu: unknown, permis: string): never {
  throw new RangeError(`Calculateur : ${quoi} vaut ${String(recu)}${FINE}; il faut ${permis}.`);
}

/** Refuse un réglage que le calculateur ne propose pas, en disant les valeurs permises. */
export function verifierReglage(r: Reglage): void {
  modeleDuCalculateur(r.modele);
  materielDe(r.materiel);
  if (!CARTES_PROPOSEES.includes(r.cartes)) refuser('le nombre de cartes', r.cartes, `l’une de ces valeurs${FINE}: ${CARTES_PROPOSEES.join(', ')}`);
  if (!JETONS_PAR_PARAMETRE_PROPOSES.includes(r.jetonsParParametre)) {
    refuser('le nombre de jetons par paramètre', r.jetonsParParametre, `l’une de ces valeurs${FINE}: ${JETONS_PAR_PARAMETRE_PROPOSES.join(', ')}`);
  }
  const e = r.efficacitePourcent;
  if (!(Number.isInteger(e) && e >= EFFICACITE_MIN_POURCENT && e <= EFFICACITE_MAX_POURCENT)) {
    refuser('l’efficacité', `${e}${FINE}%`, `un entier de ${EFFICACITE_MIN_POURCENT} à ${EFFICACITE_MAX_POURCENT}${FINE}%`);
  }
}

/**
 * Le réglage de départ : ton IA « très grand », une RTX 5070 Ti, 20 jetons par
 * paramètre, et l'efficacité par défaut de la catégorie de la carte, sauf ce
 * que `initial` précise. Lève une RangeError sur un réglage impossible.
 */
export function reglageDeDepart(initial: ReglageInitial = {}): Reglage {
  const materiel = initial.materiel ?? MATERIEL_DES_MESURES;
  materielDe(materiel);
  let efficacitePourcent: number;
  if (initial.efficacite === undefined) {
    efficacitePourcent = efficaciteParDefautPourcent(materiel);
  } else {
    const e = initial.efficacite;
    if (!(Number.isFinite(e) && e > 0 && e <= 1)) refuser('l’efficacité de départ', e, 'une fraction, de 0,1 à 0,7 (0,5 pour 50 %)');
    efficacitePourcent = Math.round(e * 100);
    if (Math.abs(e * 100 - efficacitePourcent) > 1e-9) refuser('l’efficacité de départ', e, 'un pourcentage entier (elle se règle de 1 en 1)');
  }
  const r: Reglage = {
    modele: initial.modele ?? 'tres_grand',
    materiel,
    cartes: initial.cartes ?? 1,
    jetonsParParametre: initial.jetonsParParametre ?? 20,
    efficacitePourcent,
  };
  verifierReglage(r);
  return r;
}

// ---------- Le relevé ----------

export interface Releve {
  reglage: Reglage;
  modele: ModeleDuCalculateur;
  materiel: Materiel;
  /** L'efficacité, en fraction. */
  efficacite: number;
  jetons: number;
  operations: number;
  secondes: number;
  memoire: { etats: number; activations: number; total: number; cartesMinimum: number };
  service: { bf16: number; int8: number; int4: number; cache: number; jetonsDuCache: number };
  /** Le plafond de génération en bf16 sur une carte, et les cartes qu'il faut pour loger les poids ; null sans bande passante connue. */
  generation: { jetonsParSeconde: number; cartesPourLesPoids: number } | null;
  /** Seulement pour les cartes grand public dont la puissance est connue. */
  electricite: { kwh: number; euros: number } | null;
  /** Les prix relevés pour la carte, du plus bas au plus haut ; null s'il n'y en a pas. */
  location: { prix: readonly PrixLocation[]; heures: number; usdMin: number; usdMax: number; eurMin: number; eurMax: number } | null;
  /** Ton IA sur une seule RTX 5070 Ti : la mesure, pour la comparer au calcul ; null sinon. */
  repere: { cle: CleForge; jetonsParSeconde: number; heures: number; efficacite: number } | null;
}

/** Tout le relevé d'un réglage. */
export function calculerReleve(r: Reglage): Releve {
  verifierReglage(r);
  const modele = modeleDuCalculateur(r.modele);
  const carte = materielDe(r.materiel);
  const f = modele.forme;
  const N = f.parametres;
  const efficacite = r.efficacitePourcent / 100;
  const jetons = r.jetonsParParametre * N;
  const operations = operationsEntrainement(N, jetons);
  const secondes = dureeSecondes(operations, carte.creteTflops, efficacite, r.cartes);
  const memoire = memoireEntrainementOctets(f);
  const jetonsDuCache = f.contexte < JETONS_DU_CACHE ? f.contexte : JETONS_DU_CACHE;
  const bf16 = memoirePoidsOctets(N, 2);

  const generation =
    carte.bandePassanteGoS === null
      ? null
      : {
          jetonsParSeconde: plafondGenerationJetonsParSeconde(N, 2, carte.bandePassanteGoS),
          cartesPourLesPoids: cartesMinimum(bf16, carte.memoireGo),
        };

  const electricite =
    carte.categorie === 'grand-public' && carte.puissanceW !== null
      ? (() => {
          const kwh = energieKwh(carte.puissanceW, r.cartes, secondes);
          return { kwh, euros: coutElectriciteEur(kwh, ELECTRICITE.eurParKwh) };
        })()
      : null;

  const fourchette = fourchettePrix(carte.id);
  const location =
    fourchette === null
      ? null
      : (() => {
          const usdMin = coutLocationUsd(secondes, r.cartes, fourchette.min);
          const usdMax = coutLocationUsd(secondes, r.cartes, fourchette.max);
          return {
            prix: fourchette.prix,
            heures: secondes / 3600,
            usdMin,
            usdMax,
            eurMin: usdEnEur(usdMin, TAUX_DE_CHANGE.usdPourUnEur),
            eurMax: usdEnEur(usdMax, TAUX_DE_CHANGE.usdPourUnEur),
          };
        })();

  const repere =
    modele.tonIA !== null && carte.id === MATERIEL_DES_MESURES && r.cartes === 1
      ? (() => {
          const cle = modele.tonIA;
          const ligne = ligneRepere(cle);
          const debit = MESURES_TON_IA[cle].carte.jetonsParSeconde;
          return { cle, jetonsParSeconde: debit, heures: dureeHeures(jetons, debit), efficacite: ligne.carte.efficacite };
        })()
      : null;

  return {
    reglage: { ...r },
    modele,
    materiel: carte,
    efficacite,
    jetons,
    operations,
    secondes,
    memoire: { ...memoire, cartesMinimum: cartesMinimum(memoire.total, carte.memoireGo) },
    service: { bf16, int8: memoirePoidsOctets(N, 1), int4: memoirePoidsOctets(N, 0.5), cache: cacheKvOctets(f, jetonsDuCache), jetonsDuCache },
    generation,
    electricite,
    location,
    repere,
  };
}

function ligneRepere(cle: CleForge): RepereTonIA {
  const ligne = reperesTonIA().find((l) => l.cle === cle);
  if (ligne === undefined) throw new RangeError(`Calculateur : pas de mesure pour la taille ${cle}.`);
  return ligne;
}

// ---------- Les textes du relevé ----------

/** Les jetons lus : « 8,67 milliards ». */
export function texteJetons(rel: Releve): string {
  return lie(formaterQuantite(rel.jetons));
}

/** La ligne « Calcul » : « 2,26 × 10¹⁹ opérations ». */
export function texteCalcul(rel: Releve): string {
  return `${formaterPuissanceDeDix(rel.operations)}${INSECABLE}opérations`;
}

/** La ligne « Durée » : « 5,9 jours ». */
export function texteDuree(rel: Releve): string {
  return lie(formaterDuree(rel.secondes));
}

/** La mémoire d'une carte : « 16 Go ». */
const memoireCarte = (m: Materiel): string => lie(`${nombre(m.memoireGo)} Go`);

/** La ligne « Mémoire pour l'entraîner » : « 8,1 Go : ça tient sur une carte de 16 Go », ou « il faut au moins N cartes de 16 Go ». */
export function texteMemoire(rel: Releve): string {
  const total = lie(formaterOctets(rel.memoire.total));
  if (rel.memoire.cartesMinimum <= 1) return `${total}${FINE}: ça tient sur une carte de ${memoireCarte(rel.materiel)}`;
  return `${total}${FINE}: il faut au moins ${cartesTexte(rel.memoire.cartesMinimum)} de ${memoireCarte(rel.materiel)}`;
}

/** Les jetons du cache : « 4 096 jetons », ou « 2 048 jetons (tout son contexte) ». */
function jetonsDuCache(rel: Releve): string {
  const n = lie(`${nombre(rel.service.jetonsDuCache)} jetons`);
  return rel.service.jetonsDuCache < JETONS_DU_CACHE ? `${n} (tout son contexte)` : n;
}

/** La ligne « Mémoire pour s'en servir » : les poids en bf16, int8 et int4, plus le cache. */
export function texteService(rel: Releve): string {
  const o = (x: number) => lie(formaterOctets(x));
  const s = rel.service;
  return `${o(s.bf16)} en bf16, ${o(s.int8)} en int8 ou ${o(s.int4)} en int4, plus ${o(s.cache)} de cache pour ${jetonsDuCache(rel)}`;
}

/** Un débit de génération : « 1 033 jetons », « 1,1 jeton ». */
function debitJetons(j: number): string {
  const decimales = Number(j.toFixed(1)) < 10 ? 1 : 0;
  const affiche = Number(j.toFixed(decimales));
  return lie(`${nombre(j, decimales)} ${affiche < 2 ? 'jeton' : 'jetons'}`);
}

/**
 * La ligne « Génération, au plus » : le débit sur une carte, seulement si les
 * poids en bf16 y tiennent ; sinon, combien de cartes il faut pour les loger.
 * Null si la bande passante de la carte n'est pas connue.
 */
export function texteGeneration(rel: Releve): string | null {
  const g = rel.generation;
  if (g === null) return null;
  if (g.cartesPourLesPoids <= 1) return `${debitJetons(g.jetonsParSeconde)} par seconde en bf16, sur une carte`;
  return (
    `pas sur une seule carte${FINE}: les poids en bf16 n’y tiennent pas, ` +
    `il faut au moins ${cartesTexte(g.cartesPourLesPoids)} de ${memoireCarte(rel.materiel)} pour les loger`
  );
}

/** La ligne « Électricité » (cartes grand public) : « 42,8 kWh, environ 8,56 € » ; null sinon. */
export function texteElectricite(rel: Releve): string | null {
  const e = rel.electricite;
  if (e === null) return null;
  const energie = lie(formaterEnergie(e.kwh));
  return e.euros < 1 ? `${energie}, moins d’un euro` : `${energie}, environ ${lie(formaterEuros(e.euros))}`;
}

const MONTANT = /^([\d\u202F]+(?:,\d+)?) (.+)$/;

/**
 * Une fourchette de deux montants déjà écrits : « de 38 à 174 € » quand les
 * deux bouts ont la même unité (ou son pluriel : « de 1,2 à 5,4 millions
 * d’euros »), « jusqu’à 3,20 € » quand le bas vaut moins d'un euro, sinon
 * « de 8,56 € à 1,2 million d’euros ». Un seul montant si les deux sont égaux.
 */
export function fourchette(bas: string, haut: string): string {
  if (bas === haut) return lie(bas);
  if (bas.startsWith('moins d’un')) return `jusqu’à ${lie(haut)}`;
  const b = MONTANT.exec(bas);
  const h = MONTANT.exec(haut);
  if (b !== null && h !== null) {
    const uniteBas = b[2].replace(/^(million|milliard)\b/, '$1s');
    if (b[2] === h[2] || uniteBas === h[2]) return `de ${b[1]} à ${lie(haut)}`;
  }
  return `de ${lie(bas)} à ${lie(haut)}`;
}

/** La ligne « Location » : la fourchette en euros, puis en dollars, ou « pas de prix relevé pour cette carte ». */
export function texteLocation(rel: Releve): string {
  const l = rel.location;
  if (l === null) return 'pas de prix relevé pour cette carte';
  const euros = fourchette(formaterEuros(l.eurMin), formaterEuros(l.eurMax));
  const dollars = fourchette(formaterDollars(l.usdMin), formaterDollars(l.usdMax));
  return l.prix.length > 1 && l.usdMin !== l.usdMax ? `${euros} (${dollars}), selon le loueur` : `${euros} (${dollars})`;
}

/** Une durée mesurée en heures : « 135 h », « 0,6 h ». */
function heures(h: number): string {
  return lie(`${nombre(h, Number(h.toFixed(1)) < 10 ? 1 : 0)} h`);
}

/**
 * La phrase qui compare le calcul à la mesure, quand le réglage est une
 * taille de ton IA sur une seule RTX 5070 Ti : « Calcul : 5,9 jours. Mesuré :
 * 5,6 jours (135 h). L’écart vient de l’efficacité : 52,8 % mesurés contre
 * 50 % supposés. » ; null sinon.
 */
export function phraseRepere(rel: Releve): string | null {
  const m = rel.repere;
  if (m === null) return null;
  const mesure = lie(formaterDuree(m.heures * 3600));
  const enHeures = mesure.endsWith(`${INSECABLE}h`) ? mesure : `${mesure} (${heures(m.heures)})`;
  return (
    `Calcul${FINE}: ${texteDuree(rel)}. Mesuré${FINE}: ${enHeures}. ` +
    `L’écart vient de l’efficacité${FINE}: ${pourcent(m.efficacite, 1)} mesurés contre ${pourcentRegle(rel.reglage.efficacitePourcent)} supposés.`
  );
}

/** Une efficacité publiée : « 46,2 % », « 38 % ». */
const pourcentPublie = (x: number): string => pourcent(x, decimalesUtiles(Number((x * 100).toFixed(6)), 1));

/** Les efficacités d'un repère publié : « 46,2 % », « de 38 % à 43 % ». */
const pourcentsPublies = (r: RepereEfficacite): string =>
  r.min === r.max ? pourcentPublie(r.min) : `de ${pourcentPublie(r.min)} à ${pourcentPublie(r.max)}`;

/** Un repère publié, pour la liste de leurs sources : son texte, sa définition et sa source. */
export interface SourceRepere {
  modele: string;
  texte: string;
  definition: string;
  source: Source;
}

/** Les repères publiés (PaLM, Llama 3), chacun avec ses efficacités, sa définition et sa source datée. */
export function sourcesDesReperes(): SourceRepere[] {
  return REPERES_EFFICACITE.map((r) => ({
    modele: r.modele,
    texte: `${r.modele}, ${pourcentsPublies(r)} (${r.materiel})`,
    definition: r.definition,
    source: r.source,
  }));
}

/**
 * La phrase qui compare ton IA aux grands entraînements publiés, en comptant
 * les opérations comme eux. La taille choisie si c'est une taille de ton IA,
 * « très grand » sinon. Les deux efficacités de ton IA sont calculées.
 */
export function phraseCommeLesGrands(rel: Releve): string {
  const cle = rel.modele.tonIA ?? 'tres_grand';
  const ligne = ligneRepere(cle);
  const reperes = REPERES_EFFICACITE.map((r) => `${r.modele} (${pourcentsPublies(r)}${r.noteCourte === null ? '' : `, ${r.noteCourte}`})`);
  const avec = REPERES_EFFICACITE.every((r) => r.compteAttention);
  if (!avec) {
    throw new Error('Calculateur : un repère publié ne compte pas l’attention. Revoir la phrase de comparaison (releve.ts).');
  }
  const liste = reperes.length > 1 ? `${reperes.slice(0, -1).join(', ')} et ${reperes[reperes.length - 1]}` : reperes[0];
  return (
    'Pour comparer avec les grands entraînements, il faut compter les opérations comme eux. ' +
    `${liste} comptent aussi l’attention${FINE}: ${nomTonIA(cle)} fait alors ${pourcent(ligne.carte.efficaciteAvecAttention, 1)} sur ce PC. ` +
    `Avec 6N seulement, comme le calculateur, elle fait ${pourcent(ligne.carte.efficacite, 1)}.`
  );
}

const CARTE_DE_LA_CATEGORIE: Readonly<Record<Categorie, string>> = {
  'grand-public': 'd’une carte grand public',
  colab: 'd’une carte de Colab',
  'centre-de-donnees': 'd’une carte de centre de données',
};

/**
 * Ce que la ligne d'état annonce aux lecteurs d'écran après un réglage : la
 * durée et la location. Si l'efficacité vient de suivre la carte
 * (`efficaciteSuivie`), elle le dit d'abord : « Efficacité : 40 %, celle
 * d’une carte de centre de données. »
 */
export function annonce(rel: Releve, efficaciteSuivie = false): string {
  const efficacite = efficaciteSuivie
    ? `Efficacité${FINE}: ${pourcentRegle(rel.reglage.efficacitePourcent)}, celle ${CARTE_DE_LA_CATEGORIE[rel.materiel.categorie]}. `
    : '';
  return `${efficacite}Durée${FINE}: ${texteDuree(rel)}. Location${FINE}: ${texteLocation(rel)}.`;
}

// ---------- « Voir le calcul » ----------

/** Une formule dépliée : ses nombres, ce qu'elle veut dire, et ses sources. */
export interface Formule {
  cle: 'calcul' | 'duree' | 'memoire' | 'service' | 'generation' | 'electricite' | 'location' | 'efficacites';
  titre: string;
  formule: string;
  explication: string;
  sources: readonly Source[];
}

/**
 * D'où viennent les efficacités par défaut : celle des cartes grand public est
 * proche de ce que ton IA tient sur ce PC, les autres sont dans la fourchette
 * des grands entraînements publiés. Tout est calculé à partir des données.
 */
function explicationEfficaciteParDefaut(): string {
  const d = EFFICACITE_PAR_DEFAUT;
  let bas = REPERES_EFFICACITE[0].min;
  let haut = REPERES_EFFICACITE[0].max;
  for (const r of REPERES_EFFICACITE) {
    if (r.min < bas) bas = r.min;
    if (r.max > haut) haut = r.max;
  }
  const tonIA = ligneRepere('tres_grand').carte.efficacite;
  return (
    `Par défaut, le calculateur suppose ${pourcentPublie(d['grand-public'])} sur une carte grand public ` +
    `(ton IA en tient ${pourcent(tonIA, 1)} sur ce PC), ${pourcentPublie(d.colab)} sur Colab et ` +
    `${pourcentPublie(d['centre-de-donnees'])} en centre de données, dans la fourchette des grands entraînements publiés ` +
    `(de ${pourcentPublie(bas)} à ${pourcentPublie(haut)}). Quand tu changes de carte, l’efficacité prend celle de sa catégorie, ` +
    'tant que tu ne l’as pas réglée toi-même.'
  );
}

/** Une énergie en kWh, toujours dans cette unité : « 42,8 kWh », « 8 640 kWh », « 1,87 million de kWh ». */
function energieEnKwh(kwh: number): string {
  if (Number(kwh.toFixed(1)) < 0.1) return lie('moins de 0,1 kWh');
  if (Number(kwh.toFixed(1)) < 100) return lie(`${nombre(kwh, 1)} kWh`);
  if (Number(kwh.toFixed(0)) < 1e6) return lie(`${nombre(kwh)} kWh`);
  const enMillions = Number((kwh / 1e6).toPrecision(3)) < 1000;
  const valeur = enMillions ? kwh / 1e6 : kwh / 1e9;
  const trois = Number(valeur.toPrecision(3));
  const decimales = trois < 10 ? 2 : trois < 100 ? 1 : 0;
  const affiche = Number(valeur.toFixed(decimales));
  const mot = enMillions ? (affiche < 2 ? 'million' : 'millions') : affiche < 2 ? 'milliard' : 'milliards';
  return lie(`${nombre(valeur, decimales)} ${mot} de kWh`);
}

/** Chaque formule du relevé, avec ses nombres ; les deux efficacités mesurées quand le modèle est une taille de ton IA. */
export function formulesDuCalcul(rel: Releve): Formule[] {
  const f = rel.modele.forme;
  const q = (x: number) => lie(formaterQuantite(x));
  const o = (x: number) => lie(formaterOctets(x));
  const carte = rel.materiel;
  const formules: Formule[] = [];

  formules.push({
    cle: 'calcul',
    titre: 'Le calcul',
    formule: `6${FOIS}${q(f.parametres)}${FOIS}${q(rel.jetons)}${EGAL}${texteCalcul(rel)}`,
    explication: `Six opérations par paramètre et par jeton lu${FINE}: deux pour la passe avant, quatre pour la passe arrière.`,
    sources: SOURCES_FORMULES.operations,
  });

  formules.push({
    cle: 'duree',
    titre: 'La durée',
    formule:
      `${formaterPuissanceDeDix(rel.operations)}${DIVISE}(${cartesTexte(rel.reglage.cartes)}${FOIS}${crete(carte.creteTflops)}` +
      ` opérations par seconde${FOIS}${pourcentRegle(rel.reglage.efficacitePourcent)})${EGAL}${texteDuree(rel)}`,
    explication:
      `${crete(carte.creteTflops)} opérations par seconde, c’est la crête de calcul en bf16 d’une ${carte.nom}, sans sparsité. ` +
      `L’efficacité dit quelle part de cette crête sert vraiment${FINE}; ici, elle compte 6 opérations par paramètre et par jeton, sans l’attention. ` +
      explicationEfficaciteParDefaut(),
    sources: [carte.source, ...SOURCES_FORMULES.efficacite, ...REPERES_EFFICACITE.map((r) => r.source)],
  });

  const m = rel.memoire;
  const parCarte =
    m.cartesMinimum <= 1
      ? ''
      : `${FINE}; ${lie(formaterGoPourLesCartes(m.total, carte.memoireGo))}${DIVISE}${memoireCarte(carte)}${EGAL}au moins ${cartesTexte(m.cartesMinimum)}`;
  formules.push({
    cle: 'memoire',
    titre: 'La mémoire pour l’entraîner',
    formule:
      `16 octets${FOIS}${q(f.parametres)}${EGAL}${o(m.etats)}, plus 34${FOIS}${nombre(f.contexte)}${FOIS}${nombre(f.dim)}${FOIS}` +
      `${nombre(f.couches)} octets${EGAL}${o(m.activations)}${FINE}: ${o(m.total)} en tout${parCarte}`,
    explication:
      `Les 16 octets par paramètre${FINE}: les poids et les gradients en 16 bits, plus une copie des poids, la moyenne et la variance ` +
      `d’AdamW en 32 bits. Les 34 octets${FINE}: les activations d’une séquence de ${lie(`${nombre(f.contexte)} jetons`)}, ` +
      `par couche et par dimension, sans la matrice de l’attention. C’est un minimum${FINE}: ni les logits, ni les tampons, ni la fragmentation. ` +
      OCTETS_BINAIRES,
    sources: [...SOURCES_FORMULES.etats, ...SOURCES_FORMULES.activations],
  });

  const s = rel.service;
  const dTete = f.dim / f.tetes;
  const groupee = f.tetesKv < f.tetes;
  formules.push({
    cle: 'service',
    titre: 'La mémoire pour s’en servir',
    formule:
      `${q(f.parametres)}${FOIS}${lie('2 octets')}${EGAL}${o(s.bf16)} en bf16,${FOIS}${lie('1 octet')}${EGAL}${o(s.int8)} en int8,${FOIS}${lie('0,5 octet')}${EGAL}${o(s.int4)} en int4${FINE}; ` +
      `cache${FINE}: 2${FOIS}2${FOIS}${nombre(f.couches)} couches${FOIS}${nombre(f.tetesKv)} têtes${FOIS}${nombre(dTete)}` +
      `${FOIS}${lie(`${nombre(s.jetonsDuCache)} jetons`)}${EGAL}${o(s.cache)}`,
    explication:
      'Un poids prend 2 octets en bf16, 1 octet en int8 (8 bits) et un demi-octet en int4 (4 bits). ' +
      `Le cache garde les clés et les valeurs de chaque jeton déjà lu, en 16 bits${FINE}: le premier 2 pour les clés et les valeurs, ` +
      `le second pour les 2 octets. ${
        groupee
          ? `Avec l’attention groupée, seules ${nombre(f.tetesKv)} têtes sur ${nombre(f.tetes)} gardent leurs clés et leurs valeurs.`
          : `Chacune des ${nombre(f.tetes)} têtes garde ses clés et ses valeurs, de ${nombre(dTete)} nombres chacune.`
      } ${OCTETS_BINAIRES}`,
    sources: SOURCES_FORMULES.cacheKv,
  });

  const g = rel.generation;
  if (g !== null && carte.bandePassanteGoS !== null) {
    const tiennent = g.cartesPourLesPoids <= 1;
    const bande = `${nombre(carte.bandePassanteGoS)}${FINE}×${FINE}${dixPuissance(9)} octets par seconde`;
    formules.push({
      cle: 'generation',
      titre: 'La génération, au plus',
      formule: tiennent
        ? `${bande}${DIVISE}${o(s.bf16)}${EGAL}${debitJetons(g.jetonsParSeconde)} par seconde`
        : `${lie(formaterGoPourLesCartes(s.bf16, carte.memoireGo))}${DIVISE}${memoireCarte(carte)}${EGAL}au moins ${cartesTexte(g.cartesPourLesPoids)}`,
      explication:
        `À chaque jeton qu’elle écrit, une carte relit tous les poids qu’elle garde${FINE}: la bande passante de sa mémoire borne le débit, ` +
        'pour une seule conversation à la fois. ' +
        (tiennent
          ? `La bande passante vient de la fiche de la carte, en octets décimaux${FINE}: ${lie(`${nombre(carte.bandePassanteGoS)} Go/s`)}, ` +
            `soit ${bande}. Les poids en bf16 sont ceux de la mémoire pour s’en servir, où 1${INSECABLE}Mo vaut ` +
            `1${FINE}024² octets et 1${INSECABLE}Go, 1${FINE}024³.`
          : `Ici, les poids en bf16 ne tiennent pas sur une seule carte${FINE}: il faudrait les répartir sur plusieurs, et le débit ` +
            'dépendrait de la façon de les relier. Le calculateur ne le chiffre pas.'),
      sources: SOURCES_FORMULES.generation,
    });
  }

  if (rel.electricite !== null && carte.puissanceW !== null) {
    formules.push({
      cle: 'electricite',
      titre: 'L’électricité',
      formule:
        `${lie(`${nombre(carte.puissanceW)} W`)}${FOIS}${cartesTexte(rel.reglage.cartes)}${FOIS}${texteDuree(rel)}${EGAL}` +
        `${energieEnKwh(rel.electricite.kwh)}${FINE};${FOIS}${lie(`${nombre(ELECTRICITE.eurParKwh, decimalesUtiles(ELECTRICITE.eurParKwh))} €`)} le kWh` +
        `${EGAL}${lie(formaterEuros(rel.electricite.euros))}`,
      explication:
        `La puissance maximale de la carte, sans le reste du PC (1${INSECABLE}kWh, c’est 1${FINE}000${INSECABLE}W pendant une heure), ` +
        `au prix du kWh ${ELECTRICITE.libelle.replace(/^EDF, /, 'd’EDF, ')}.`,
      sources: [ELECTRICITE.source],
    });
  }

  const l = rel.location;
  if (l !== null) {
    const premier = l.prix[0].usdParHeure;
    const dernier = l.prix[l.prix.length - 1].usdParHeure;
    formules.push({
      cle: 'location',
      titre: 'La location',
      formule:
        `${lie(formaterHeures(l.heures))}${FOIS}${cartesTexte(rel.reglage.cartes)}${FOIS}${fourchette(formaterPrix(premier), formaterPrix(dernier))}` +
        `${EGAL}${fourchette(formaterDollars(l.usdMin), formaterDollars(l.usdMax))}${FINE};` +
        `${DIVISE}${nombre(TAUX_DE_CHANGE.usdPourUnEur, decimalesUtiles(TAUX_DE_CHANGE.usdPourUnEur))}${EGAL}` +
        `${fourchette(formaterEuros(l.eurMin), formaterEuros(l.eurMax))}`,
      explication:
        'Le prix par carte et par heure, hors taxes, du loueur le moins cher au plus cher, puis en euros au taux de la BCE. ' +
        `Deux fois plus de cartes, c’est deux fois moins longtemps${FINE}: le prix ne change pas, à efficacité égale.`,
      sources: [TAUX_DE_CHANGE.source],
    });
  }

  if (rel.modele.tonIA !== null) {
    const cle = rel.modele.tonIA;
    const ligne = ligneRepere(cle);
    const debit = nombre(ligne.carte.jetonsParSeconde);
    const c = crete(materielDe(MATERIEL_DES_MESURES).creteTflops);
    const attention = `12${FOIS}${nombre(f.couches)}${FOIS}${nombre(f.dim)}${FOIS}${nombre(f.contexte)}`;
    formules.push({
      cle: 'efficacites',
      titre: `Les deux efficacités de ${nomTonIA(cle)}, mesurées sur ce PC`,
      formule:
        `6${FOIS}${q(f.parametres)}${FOIS}${lie(`${debit} jetons`)} par seconde${DIVISE}${c}${EGAL}${pourcent(ligne.carte.efficacite, 1)}${FINE}; ` +
        `en comptant l’attention${FINE}: (6${FOIS}${q(f.parametres)}${PLUS}${attention})${FOIS}${debit}${DIVISE}${c}${EGAL}` +
        `${pourcent(ligne.carte.efficaciteAvecAttention, 1)}`,
      explication:
        `Le débit a été mesuré sur la ${materielDe(MATERIEL_DES_MESURES).nom} de ce PC. Le calculateur compte 6 opérations par paramètre et par jeton${FINE}: ` +
        `c’est la première. PaLM et Llama 3 comptent aussi l’attention${FINE}: c’est la seconde, celle qui se compare à leurs chiffres.`,
      sources: [MESURES_TON_IA[cle].source, ...SOURCES_FORMULES.attention],
    });
  }

  return formules;
}

// ---------- Le tableau des repères ----------

/** Une ligne du tableau « Repère mesuré : ton IA sur ce PC », mise en texte. */
export interface LigneRepere {
  cle: CleForge;
  nom: string;
  parametres: string;
  carteDebit: string;
  carteDuree: string;
  efficacite: string;
  processeurDebit: string;
  processeurDuree: string;
}

/** Les 5 lignes du repère mesuré : débits sur la carte et sur le processeur, durées pour 20 jetons par paramètre, efficacité implicite. */
export function lignesReperes(): LigneRepere[] {
  return reperesTonIA().map((r) => ({
    cle: r.cle,
    nom: lie(r.nom),
    parametres: lie(formaterQuantite(r.parametres)),
    carteDebit: lie(`${nombre(r.carte.jetonsParSeconde)} jetons`),
    carteDuree: lie(formaterDuree(r.carte.heures * 3600)),
    efficacite: pourcent(r.carte.efficacite, 1),
    processeurDebit: lie(`${nombre(r.processeur.jetonsParSeconde)} jetons`),
    processeurDuree: lie(formaterDuree(r.processeur.heures * 3600)),
  }));
}
