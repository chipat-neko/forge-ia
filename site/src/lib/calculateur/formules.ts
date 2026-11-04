// Les formules du calculateur de coût, chacune avec sa source.
//
// On note N les paramètres, D les jetons, s le contexte, b le micro-lot,
// h la dimension, L les couches et a les têtes. Les adresses, titres et dates
// de relevé de chaque source sont dans donnees.ts (SOURCES_FORMULES), sous le
// nom donné entre crochets.
//
// Chaque fonction refuse une entrée impossible (non finie, négative, ou nulle
// là où elle diviserait) par une RangeError qui dit quoi corriger : le
// calculateur ne doit jamais afficher NaN ni Infinity.
//
// Ce module est en TypeScript pur, sans import propre à Vite : les parcours
// Playwright l'importent directement.

/** La forme d'un transformer, ce dont les formules ont besoin. */
export interface Forme {
  /** N, le nombre de paramètres. */
  parametres: number;
  /** L, le nombre de couches. */
  couches: number;
  /** h, la dimension des vecteurs (d_model). */
  dim: number;
  /** a, le nombre de têtes d'attention. */
  tetes: number;
  /** Le nombre de têtes de clés et de valeurs (moins que `tetes` avec l'attention groupée). */
  tetesKv: number;
  /** s, la longueur de contexte de l'entraînement. */
  contexte: number;
  vocabulaire: number;
}

/** Un Go vaut 1 024³ octets, comme dans forge et l'Explorateur de Windows. */
export const OCTETS_PAR_GO = 1024 * 1024 * 1024;

/** [operations] Kaplan et al., section 2.1 : C ≈ 6N opérations par jeton d'entraînement. */
export const OPERATIONS_PAR_PARAMETRE_ET_JETON = 6;
/** [etats] ZeRO, section 3.1 : 2Ψ + 2Ψ + 12Ψ = 16Ψ octets (AdamW en précision mixte). */
export const OCTETS_ETATS_PAR_PARAMETRE = 16;
/** [activations] Korthikanti et al., tableau 2 : 34·s·b·h octets par couche, sans la matrice s×s. */
export const OCTETS_ACTIVATIONS = 34;

const JOULES_PAR_KWH = 3_600_000;
const SECONDES_PAR_HEURE = 3600;

function erreur(fonction: string, quoi: string, x: unknown, attendu: string): RangeError {
  return new RangeError(
    `${fonction} : ${quoi} vaut ${String(x)}, il faut ${attendu}. ` +
      'Corrige le réglage ou la donnée avant de calculer : le calculateur ne doit jamais afficher NaN ni Infinity.',
  );
}

/** Un nombre fini, plus grand que 0. */
function positif(x: number, quoi: string, fonction: string): void {
  if (!(Number.isFinite(x) && x > 0)) throw erreur(fonction, quoi, x, 'un nombre fini plus grand que 0');
}

/** Un nombre fini, 0 compris. */
function positifOuNul(x: number, quoi: string, fonction: string): void {
  if (!(Number.isFinite(x) && x >= 0)) throw erreur(fonction, quoi, x, 'un nombre fini, positif ou nul');
}

/** Un entier, au moins 1. */
function entierPositif(x: number, quoi: string, fonction: string): void {
  if (!(Number.isSafeInteger(x) && x >= 1)) throw erreur(fonction, quoi, x, 'un entier d’au moins 1');
}

/** Une forme possible : des entiers positifs, des têtes de même taille, des têtes KV qui divisent les têtes. */
function verifierForme(f: Forme, fonction: string): void {
  positif(f.parametres, 'le nombre de paramètres', fonction);
  entierPositif(f.couches, 'le nombre de couches', fonction);
  entierPositif(f.dim, 'la dimension', fonction);
  entierPositif(f.tetes, 'le nombre de têtes', fonction);
  entierPositif(f.tetesKv, 'le nombre de têtes KV', fonction);
  entierPositif(f.contexte, 'le contexte', fonction);
  entierPositif(f.vocabulaire, 'le vocabulaire', fonction);
  if (f.dim % f.tetes !== 0) {
    throw new RangeError(`${fonction} : la dimension (${f.dim}) doit être divisible par le nombre de têtes (${f.tetes}).`);
  }
  if (f.tetes % f.tetesKv !== 0) {
    throw new RangeError(`${fonction} : les têtes KV (${f.tetesKv}) doivent diviser le nombre de têtes (${f.tetes}).`);
  }
}

/**
 * Les opérations d'un entraînement : 6·N·D.
 *
 * [operations] Kaplan et al. 2020 (arXiv 2001.08361), section 2.1 : C ≈ 6N
 * opérations par jeton (2N pour la passe avant, le double pour la passe
 * arrière), en négligeant l'attention. La colonne des opérations du tableau 3
 * de Chinchilla (arXiv 2203.15556) vaut exactement 6·N·D : 400 millions de
 * paramètres et 8 milliards de jetons font 1,92e19.
 */
export function operationsEntrainement(parametres: number, jetons: number): number {
  positif(parametres, 'le nombre de paramètres', 'operationsEntrainement');
  positifOuNul(jetons, 'le nombre de jetons', 'operationsEntrainement');
  return OPERATIONS_PAR_PARAMETRE_ET_JETON * parametres * jetons;
}

/**
 * Les opérations par jeton en comptant l'attention : 6N + 12·L·h·s.
 *
 * [attention] PaLM (arXiv 2204.02311), annexe B : 6N + 12·L·H·Q·T, où H·Q = h
 * (têtes × dimension d'une tête) et T = s ; c'est aussi `estimate_mfu` de
 * nanoGPT. Sans la remise de moitié due au masque causal.
 */
export function operationsParJetonAvecAttention(f: Forme): number {
  verifierForme(f, 'operationsParJetonAvecAttention');
  return OPERATIONS_PAR_PARAMETRE_ET_JETON * f.parametres + 12 * f.couches * f.dim * f.contexte;
}

/**
 * La durée d'un calcul, en secondes : opérations ÷ (crête × 10¹² × efficacité × cartes).
 *
 * [efficacite] L'efficacité est le débit d'opérations obtenu rapporté à la
 * crête des cartes, comme le MFU de PaLM (section 4.1 et annexe B). Mais le
 * calculateur compte 6N opérations par jeton, sans l'attention, quand PaLM
 * compte 6N + 12·L·h·s : son efficacité n'est qu'une approximation du MFU de
 * PaLM, un peu plus basse pour un même débit (ton IA : 52,8 % avec 6N,
 * 65,6 % en comptant l'attention). Voir REPERES_EFFICACITE.compteAttention.
 */
export function dureeSecondes(operations: number, creteTflops: number, efficacite: number, cartes: number): number {
  const f = 'dureeSecondes';
  positifOuNul(operations, 'le nombre d’opérations', f);
  positif(creteTflops, 'la crête (TFLOPS)', f);
  if (!(Number.isFinite(efficacite) && efficacite > 0 && efficacite <= 1)) {
    throw erreur(f, 'l’efficacité', efficacite, 'une fraction plus grande que 0 et au plus 1');
  }
  entierPositif(cartes, 'le nombre de cartes', f);
  return operations / (creteTflops * 1e12 * efficacite * cartes);
}

/**
 * L'efficacité d'un débit mesuré, avec 6N opérations par jeton : 6·N·débit ÷ (crête × 10¹²).
 *
 * [efficacite] Le MFU de PaLM (section 4.1 et annexe B), mais sans
 * l'attention : une approximation, celle que le calculateur utilise. Ton IA :
 * 6 × 433,6 millions × 17 855 jetons par seconde sur 87,9 TFLOPS, soit
 * 52,8 % (65,6 % en comptant l'attention, voir efficaciteMesureeAvecAttention).
 */
export function efficaciteMesuree(parametres: number, jetonsParSeconde: number, creteTflops: number): number {
  const f = 'efficaciteMesuree';
  positif(parametres, 'le nombre de paramètres', f);
  positifOuNul(jetonsParSeconde, 'le débit (jetons par seconde)', f);
  positif(creteTflops, 'la crête (TFLOPS)', f);
  return (OPERATIONS_PAR_PARAMETRE_ET_JETON * parametres * jetonsParSeconde) / (creteTflops * 1e12);
}

/**
 * La même efficacité en comptant l'attention : débit × (6N + 12·L·h·s) ÷ (crête × 10¹²).
 *
 * [attention] [efficacite] PaLM, annexe B : c'est le MFU de PaLM, celui qui se
 * compare aux efficacités publiées de PaLM et de Llama 3. Ton IA : 65,6 %.
 */
export function efficaciteMesureeAvecAttention(f: Forme, jetonsParSeconde: number, creteTflops: number): number {
  const nom = 'efficaciteMesureeAvecAttention';
  positifOuNul(jetonsParSeconde, 'le débit (jetons par seconde)', nom);
  positif(creteTflops, 'la crête (TFLOPS)', nom);
  return (jetonsParSeconde * operationsParJetonAvecAttention(f)) / (creteTflops * 1e12);
}

/**
 * La mémoire d'un entraînement, en octets : 16·N pour les états, 34·s·b·h·L
 * pour les activations.
 *
 * - [etats] ZeRO (arXiv 1910.02054), section 3.1 : avec AdamW en précision
 *   mixte, 2Ψ (poids fp16) + 2Ψ (gradients fp16) + 12Ψ (copie fp32 des poids,
 *   moyenne et variance), soit 16 octets par paramètre ; « au moins 24 Go »
 *   pour GPT-2 1,5 milliard.
 * - [activations] Korthikanti et al. (arXiv 2205.05198), tableau 2 :
 *   34·s·b·h octets par couche quand la matrice s×s de l'attention n'est pas
 *   gardée (recalcul sélectif ; FlashAttention a le même effet).
 *
 * Ce total ne compte ni les logits, ni les tampons temporaires, ni la
 * fragmentation : c'est un minimum (ton IA : 8,1 Go calculés, 10,9 Go mesurés).
 */
export function memoireEntrainementOctets(f: Forme, microLot = 1): { etats: number; activations: number; total: number } {
  verifierForme(f, 'memoireEntrainementOctets');
  entierPositif(microLot, 'le micro-lot', 'memoireEntrainementOctets');
  const etats = OCTETS_ETATS_PAR_PARAMETRE * f.parametres;
  const activations = OCTETS_ACTIVATIONS * f.contexte * microLot * f.dim * f.couches;
  return { etats, activations, total: etats + activations };
}

/**
 * Les activations sans FlashAttention, en octets : s·b·h·L·(34 + 5·a·s/h).
 *
 * [activations] Korthikanti et al. (arXiv 2205.05198), équation 1 (par
 * couche) et équation 5 (pour L couches, sans parallélisme de tenseurs) :
 * activations en 16 bits, masques de dropout compris. Le terme 5·a·s/h est la
 * matrice s×s de l'attention.
 */
export function activationsSansFlashOctets(f: Forme, microLot = 1): number {
  verifierForme(f, 'activationsSansFlashOctets');
  entierPositif(microLot, 'le micro-lot', 'activationsSansFlashOctets');
  return f.contexte * microLot * f.dim * f.couches * (OCTETS_ACTIVATIONS + (5 * f.tetes * f.contexte) / f.dim);
}

/** La mémoire des poids seuls, en octets : N × octets par poids (2 en bf16, 1 en int8, 0,5 en int4). */
export function memoirePoidsOctets(parametres: number, octetsParPoids: number): number {
  positif(parametres, 'le nombre de paramètres', 'memoirePoidsOctets');
  positif(octetsParPoids, 'le nombre d’octets par poids', 'memoirePoidsOctets');
  return parametres * octetsParPoids;
}

/**
 * Le cache KV de la génération, en octets : 2·2·L·têtes_kv·(h/a) par jeton.
 *
 * [cacheKv] kipply, « Transformer Inference Arithmetic » (2022), section
 * « kv cache » : 2·2·n_layers·n_heads·d_head octets par jeton en 16 bits (le
 * premier 2 pour K et V, le second pour les octets). Avec l'attention groupée,
 * n_heads devient le nombre de têtes KV.
 */
export function cacheKvOctets(f: Forme, jetons: number, lot = 1): number {
  verifierForme(f, 'cacheKvOctets');
  positifOuNul(jetons, 'le nombre de jetons', 'cacheKvOctets');
  entierPositif(lot, 'le lot', 'cacheKvOctets');
  return 2 * 2 * f.couches * f.tetesKv * (f.dim / f.tetes) * jetons * lot;
}

/**
 * Le plafond de génération, en jetons par seconde : bande passante ÷ octets des poids.
 *
 * [generation] kipply, section « latency calculations » : à petit lot, chaque
 * jeton relit tous les poids, et la bande passante de la mémoire borne le
 * débit. La bande passante est en Go/s décimaux (10⁹ octets), comme sur les
 * fiches des fabricants.
 */
export function plafondGenerationJetonsParSeconde(parametres: number, octetsParPoids: number, bandePassanteGoS: number): number {
  const f = 'plafondGenerationJetonsParSeconde';
  positif(parametres, 'le nombre de paramètres', f);
  positif(octetsParPoids, 'le nombre d’octets par poids', f);
  positif(bandePassanteGoS, 'la bande passante (Go/s)', f);
  return (bandePassanteGoS * 1e9) / (parametres * octetsParPoids);
}

/** Le nombre de cartes qu'il faut au moins pour loger `octets` : octets ÷ (mémoire × 1 024³), arrondi au-dessus. */
export function cartesMinimum(octets: number, memoireGo: number): number {
  positifOuNul(octets, 'le nombre d’octets', 'cartesMinimum');
  positif(memoireGo, 'la mémoire d’une carte (Go)', 'cartesMinimum');
  return Math.ceil(octets / (memoireGo * OCTETS_PAR_GO));
}

/** L'énergie consommée, en kWh : puissance × cartes × secondes ÷ 3 600 000. */
export function energieKwh(puissanceW: number, cartes: number, secondes: number): number {
  positifOuNul(puissanceW, 'la puissance (W)', 'energieKwh');
  entierPositif(cartes, 'le nombre de cartes', 'energieKwh');
  positifOuNul(secondes, 'la durée (s)', 'energieKwh');
  return (puissanceW * cartes * secondes) / JOULES_PAR_KWH;
}

/** Le prix de l'électricité, en euros : kWh × prix du kWh. */
export function coutElectriciteEur(kwh: number, eurParKwh: number): number {
  positifOuNul(kwh, 'l’énergie (kWh)', 'coutElectriciteEur');
  positifOuNul(eurParKwh, 'le prix du kWh', 'coutElectriciteEur');
  return kwh * eurParKwh;
}

/** Le prix d'une location, en dollars : heures × cartes × prix par carte et par heure. */
export function coutLocationUsd(secondes: number, cartes: number, usdParHeure: number): number {
  positifOuNul(secondes, 'la durée (s)', 'coutLocationUsd');
  entierPositif(cartes, 'le nombre de cartes', 'coutLocationUsd');
  positifOuNul(usdParHeure, 'le prix horaire', 'coutLocationUsd');
  return (secondes / SECONDES_PAR_HEURE) * cartes * usdParHeure;
}

/** Des dollars en euros, au taux de la BCE (dollars pour un euro). */
export function usdEnEur(usd: number, usdPourUnEur: number): number {
  positifOuNul(usd, 'le montant en dollars', 'usdEnEur');
  positif(usdPourUnEur, 'le taux de change (dollars pour un euro)', 'usdEnEur');
  return usd / usdPourUnEur;
}
