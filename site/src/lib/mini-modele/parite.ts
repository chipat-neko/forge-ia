// La parité : refait en TypeScript ce que fait projets/mini-modele/mini_modele/attendus.py.
//
// Le Python écrit quatre fichiers d'attendus (tests/attendus-<nom>.json) : des
// entrées, et ce qu'il en tire, chaque flottant en 16 chiffres hexadécimaux.
// Chaque fonction attendus*() ci-dessous rend un objet de la même forme que
// son fichier : mêmes clés (les noms du Python, en snake_case), mêmes entrées
// (celles tirées au hasard viennent du même Hasard), mêmes motifs.
//
// - parite.test.ts les compare aux fichiers dans Node (Vitest) ;
// - la page d'essai de parité (ControleParite.svelte) les calcule dans le
//   navigateur, et e2e/parite.spec.ts compare ce qu'elle écrit aux mêmes
//   fichiers, dans Chrome, Firefox et WebKit. C'est la seule façon de voir
//   qu'un moteur JavaScript s'écarte du Python.
//
// Ce fichier suit attendus.py ligne à ligne : si l'un change, l'autre suit.

import prenomsBrut from '../../../../projets/mini-modele/donnees/prenoms.txt?raw';
import {
  C_COS,
  C_EXP,
  C_LOG,
  cos,
  empreinte,
  empreinteTexte,
  exp,
  Hasard,
  INV_LN2,
  LN2_BAS,
  LN2_HAUT,
  log,
  PI,
  SQRT_DEMI,
  versHex,
} from './calcul';
import { decoder, donneesParDefaut, preparer, prenomsDuTexte, tailleVocabulaire } from './donnees';
import { Entraineur, PRESETS_MINI, reglagesMini, TAUX_PROPOSES, taux, type ReglagesMini } from './entrainement';
import { chargerExemple, detaillerExemple, detaillerTete, type DetailTete, type Matrice } from './exemple-attention';
import { avant, configMini, entropieCroisee, generer, initialiser, nombreParametres, perte, perteEtGradient } from './modele';

/** Un objet d'attendus, tel qu'il s'écrit en JSON. */
export type Attendus = Record<string, unknown>;

// Entrées fixes : les cas limites (sous-normaux, débordements, −0, très petits et très grands).
const ENTREES_EXP = [
  -745.2, -745.0, -744.4, -740.0, -720.0, -709.0, -708.5, -50.0, -10.0, -1.0, -0.5, -1e-10, -0.0, 0.0, 1e-300, 1e-10,
  0.25, 0.5, 1.0, 2.0, 10.0, 50.0, 700.0, 709.7, 709.78, 709.79, 710.0,
];
const ENTREES_LOG = [
  5e-324, 1e-310, 2.225073858507201e-308, 1e-300, 1e-10, 0.1, 0.5, SQRT_DEMI, 0.75, 1.0, 1.0000001, 1.5, 2.0, 10.0,
  1e10, 1e300, 1.7976931348623157e308,
];
const ENTREES_COS = [0.0, 1e-8, 0.5, 1.0, PI * 0.25, PI * 0.5, 2.0, 3.0, PI];
// Les valeurs de l'empreinte : des signes, des sous-normaux, des infinis.
const VALEURS_EMPREINTE = [0.0, -0.0, 1.0, -2.5, 0.1, PI, 5e-324, 1e300, Infinity, -Infinity];
// « Élodie, Zoé et Maël », écrit en échappements : aucun outil ne peut en changer les octets.
const TEXTE_EMPREINTE = '\u00c9lodie, Zo\u00e9 et Ma\u00ebl';
const GRAINE = 1234;
// L'écart-type de l'initialisation du mini-modèle : vérifie aussi la dernière multiplication de gaussienne.
const ECART_TYPE_ESSAI = 0.08;

/** n tirages d'un Hasard(graine) neuf. */
function tirer<T>(graine: number, n: number, tirage: (h: Hasard) => T): T[] {
  const h = new Hasard(graine);
  return Array.from({ length: n }, () => tirage(h));
}

/** [x, f(x)] pour chaque entrée, en motifs hexadécimaux. */
function paires(fonction: (x: number) => number, entrees: readonly number[]): [string, string][] {
  return entrees.map((x) => [versHex(x), versHex(fonction(x))]);
}

/** Les motifs d'une liste de flottants. */
function hex(valeurs: ArrayLike<number>): string[] {
  return Array.from(valeurs, (v) => versHex(v));
}

/** Les attendus du noyau de calcul (tests/attendus-calcul.json). */
export function attendusCalcul(): Attendus {
  const entreesExp = [...ENTREES_EXP, ...tirer(42, 200, (h) => (h.uniforme() - 0.5) * 60)];
  const entreesLog = [...ENTREES_LOG, ...tirer(43, 200, (h) => h.uniforme() * 100 + 0.001)];
  const entreesCos = [...ENTREES_COS, ...tirer(44, 100, (h) => h.uniforme() * PI)];
  const melange = Array.from({ length: 20 }, (_, i) => i);
  new Hasard(GRAINE).melanger(melange);
  return {
    constantes: {
      LN2_HAUT: versHex(LN2_HAUT),
      LN2_BAS: versHex(LN2_BAS),
      INV_LN2: versHex(INV_LN2),
      SQRT_DEMI: versHex(SQRT_DEMI),
      PI: versHex(PI),
    },
    coefficients: { C_EXP: hex(C_EXP), C_LOG: hex(C_LOG), C_COS: hex(C_COS) },
    exp: paires(exp, entreesExp),
    log: paires(log, entreesLog),
    cos: paires(cos, entreesCos),
    hasard: {
      graine: GRAINE,
      suivant32: tirer(GRAINE, 20, (h) => h.suivant32()),
      uniforme: hex(tirer(GRAINE, 20, (h) => h.uniforme())),
      gaussienne: hex(tirer(GRAINE, 20, (h) => h.gaussienne(1.0))),
      gaussienne_0_08: hex(tirer(GRAINE, 20, (h) => h.gaussienne(ECART_TYPE_ESSAI))),
      entier_10: tirer(GRAINE, 20, (h) => h.entier(10)),
      melange_20: melange,
    },
    empreinte: { valeurs: hex(VALEURS_EMPREINTE), empreinte: empreinte(VALEURS_EMPREINTE) },
    empreinte_texte: { texte: TEXTE_EMPREINTE, empreinte: empreinteTexte(TEXTE_EMPREINTE) },
  };
}

/** Les attendus des prénoms (tests/attendus-donnees.json) : le fichier, le vocabulaire et le partage. */
export function attendusDonnees(): Attendus {
  // Le texte du fichier tel quel (?raw), comme FICHIER_PRENOMS.read_bytes().decode("utf-8") en Python.
  const texte = prenomsBrut;
  const donnees = preparer(prenomsDuTexte(texte));
  const entrainement = donnees.entrainement.map((s) => decoder(s, donnees.vocabulaire));
  const validation = donnees.validation.map((s) => decoder(s, donnees.vocabulaire));
  return {
    nb_prenoms: entrainement.length + validation.length,
    empreinte_fichier: empreinteTexte(texte),
    vocabulaire: donnees.vocabulaire,
    nb_entrainement: entrainement.length,
    nb_validation: validation.length,
    entrainement_10: entrainement.slice(0, 10),
    validation_10: validation.slice(0, 10),
    empreinte_entrainement: empreinteTexte(entrainement.join('\n')),
    empreinte_validation: empreinteTexte(validation.join('\n')),
  };
}

// Le mini-modèle : la graine des poids, et celle des prénoms inventés au départ (graine + 2 + pas, au pas 0).
const GRAINE_MODELE = 1234;
const GRAINE_GENERES = 1236;

/** La clé « modele » : l'initialisation, la perte et le gradient d'un lot, la validation et la génération. */
function attendusDuModele(): Attendus {
  const donnees = donneesParDefaut();
  const c = configMini(tailleVocabulaire(donnees.vocabulaire));
  const params = initialiser(c, new Hasard(GRAINE_MODELE));
  const lot = donnees.entrainement.slice(0, 8);
  const gradient = new Float64Array(params.length);
  const perteLot = perteEtGradient(c, params, lot, gradient);
  const generes = generer(c, params, new Hasard(GRAINE_GENERES), 8);
  const pertesPositions: number[] = [];
  for (const seq of lot) {
    const passe = avant(c, params, seq.slice(0, -1));
    for (let t = 0; t < seq.length - 1; t++) {
      pertesPositions.push(entropieCroisee(passe[t].logits, seq[t + 1]));
    }
  }
  return {
    // Les noms des champs sont ceux du Python (dataclasses.asdict(ConfigMini)).
    config: {
      taille_vocabulaire: c.tailleVocabulaire,
      dim: c.dim,
      tetes: c.tetes,
      contexte: c.contexte,
      largeur_mlp: c.largeurMlp,
    },
    graine: GRAINE_MODELE,
    nb_parametres: nombreParametres(c),
    init_empreinte: empreinte(params),
    init_premiers: hex(params.slice(0, 8)),
    lot: lot.map((s) => [...s]),
    perte_lot: versHex(perteLot),
    pertes_positions_empreinte: empreinte(pertesPositions),
    gradient_empreinte: empreinte(gradient),
    gradient_premiers: hex(gradient.slice(0, 8)),
    perte_validation_256: versHex(perte(c, params, donnees.validation.slice(0, 256))),
    generes: generes.map((p) => decoder(p, donnees.vocabulaire)),
  };
}

// L'entraînement : le préréglage complet, sur PAS_ENTRAINEMENT pas.
const PRESET_ENTRAINEMENT = 'complet';
const PAS_ENTRAINEMENT = 20;
// Le taux du préréglage complet à ces pas : la montée, le sommet, le cosinus et la fin.
const PAS_DU_PLANNING = [0, 1, 50, 99, 100, 101, 550, 1000, 1550, 2000, 2999, 3000, 3001];
// Un taux maximal absurde : l'erreur explose en quelques pas.
const TAUX_QUI_DIVERGE = 1000.0;

// Les noms Python des champs des réglages (dataclasses.asdict(ReglagesMini)), et ceux qui sont des entiers.
const NOMS_PYTHON: Readonly<Record<keyof ReglagesMini, string>> = {
  pasTotal: 'pas_total',
  echauffement: 'echauffement',
  tauxMax: 'taux_max',
  lot: 'lot',
  ratioMin: 'ratio_min',
  beta1: 'beta1',
  beta2: 'beta2',
  epsilon: 'epsilon',
  poidsDecroissance: 'poids_decroissance',
  ecretage: 'ecretage',
  graine: 'graine',
  validationTous: 'validation_tous',
  nbValidation: 'nb_validation',
  nbEchantillons: 'nb_echantillons',
};
const ENTIERS = new Set<keyof ReglagesMini>([
  'pasTotal',
  'echauffement',
  'lot',
  'graine',
  'validationTous',
  'nbValidation',
  'nbEchantillons',
]);

/** Les champs des réglages, avec leurs noms Python : les entiers tels quels, les flottants en motifs. */
function reglagesEnAttendus(r: ReglagesMini): Record<string, number | string> {
  const sortie: Record<string, number | string> = {};
  for (const cle of Object.keys(NOMS_PYTHON) as (keyof ReglagesMini)[]) {
    sortie[NOMS_PYTHON[cle]] = ENTIERS.has(cle) ? r[cle] : versHex(r[cle]);
  }
  return sortie;
}

// Un entraînement court sur vingt prénoms de deux lettres (18 en entraînement, 2 en validation) :
// avec des lots de 4, l'ordre est remélangé aux pas 5 et 9 ; avec un écrêtage à 100, le gradient
// n'est jamais écrêté. Dix pas sur 10 : la montée, le cosinus et la fin.
const PRENOMS_COURT = [
  'an', 'bo', 'ci', 'du', 'el', 'fa', 'gu', 'hi', 'in', 'jo', 'ka', 'lu', 'ma', 'ne', 'ol', 'pa', 'qu', 'ro', 'su', 'ti',
];
const REGLAGES_COURT = reglagesMini(10, 2, { lot: 4, ecretage: 100.0 });

/** La clé « court » de « entrainement » : 10 pas sur PRENOMS_COURT, lots de 4, écrêtage à 100. */
function attendusCourt(): Attendus {
  const e = new Entraineur(REGLAGES_COURT, preparer([...PRENOMS_COURT]));
  const pertes: string[] = [];
  const tauxDesPas: string[] = [];
  for (let i = 0; i < REGLAGES_COURT.pasTotal; i++) {
    pertes.push(versHex(e.faireUnPas()));
    tauxDesPas.push(versHex(e.tauxCourant()));
  }
  return {
    prenoms: [...PRENOMS_COURT],
    reglages: reglagesEnAttendus(REGLAGES_COURT),
    nb_pas: e.pas,
    pertes,
    taux: tauxDesPas,
    validation: versHex(e.perteValidation()),
    params_empreinte: empreinte(e.params),
    params_premiers: hex(e.params.slice(0, 8)),
    echantillons: e.echantillons(),
  };
}

/** La clé « entrainement » : 20 pas du préréglage complet, le planning du taux, une divergence, et le cas court. */
function attendusEntrainement(): Attendus {
  const reglages = PRESETS_MINI[PRESET_ENTRAINEMENT];
  const e = new Entraineur(reglages);
  const validation0 = e.perteValidation();
  const echantillons0 = e.echantillons();
  const pertes: string[] = [];
  const tauxDesPas: string[] = [];
  for (let i = 0; i < PAS_ENTRAINEMENT; i++) {
    pertes.push(versHex(e.faireUnPas()));
    tauxDesPas.push(versHex(e.tauxCourant()));
  }
  const fou = new Entraineur({ ...reglages, tauxMax: TAUX_QUI_DIVERGE });
  let perteFolle = 0.0;
  while (!fou.diverge && fou.pas < 50) {
    perteFolle = fou.faireUnPas();
  }
  if (!fou.diverge) {
    throw new Error(`Un taux maximal de ${TAUX_QUI_DIVERGE} n'a pas fait diverger l'entraînement en 50 pas.`);
  }
  const r = reglages;
  const presets: Record<string, Record<string, number | string>> = {};
  for (const [nom, p] of Object.entries(PRESETS_MINI)) {
    presets[nom] = reglagesEnAttendus(p);
  }
  return {
    preset: PRESET_ENTRAINEMENT,
    nb_pas: PAS_ENTRAINEMENT,
    pertes,
    taux: tauxDesPas,
    validation_0: versHex(validation0),
    validation_20: versHex(e.perteValidation()),
    params_empreinte_20: empreinte(e.params),
    params_premiers_20: hex(e.params.slice(0, 8)),
    echantillons_0: echantillons0,
    echantillons_20: e.echantillons(),
    taux_planning: PAS_DU_PLANNING.map((p) => [p, versHex(taux(p, r.pasTotal, r.tauxMax, r.echauffement, r.ratioMin))]),
    divergence: { taux_max: versHex(TAUX_QUI_DIVERGE), pas: fou.pas, perte: versHex(perteFolle) },
    presets,
    taux_proposes: hex(TAUX_PROPOSES),
    court: attendusCourt(),
  };
}

/** Les attendus du mini-modèle (tests/attendus-modele.json) : les clés « modele » et « entrainement ». */
export function attendusModele(): Attendus {
  return { modele: attendusDuModele(), entrainement: attendusEntrainement() };
}

/** Chaque case en motif hexadécimal ; une case masquée (null) reste null. */
function motifs(matrice: readonly (readonly (number | null)[])[]): (string | null)[][] {
  return matrice.map((ligne) => ligne.map((v) => (v === null ? null : versHex(v))));
}

/** Tout le détail d'une tête, en motifs, avec les noms du Python. */
function detailEnAttendus(d: DetailTete): Attendus {
  return {
    requetes: motifs(d.requetes),
    cles: motifs(d.cles),
    valeurs: motifs(d.valeurs),
    scores: motifs(d.scores),
    scores_echelles: motifs(d.scoresEchelles),
    poids: motifs(d.poids),
    sorties: motifs(d.sorties),
  };
}

/**
 * L'exemple à virgule de attendus.py (EXEMPLE_FLOTTANT), pour l'ordre des sommes.
 *
 * Dans la phrase de l'animation, tout est entier : chaque somme y est exacte,
 * dans n'importe quel ordre. Ici, 0,1 ou 0,3 ne s'écrivent pas exactement en
 * binaire : additionner dans un autre ordre change des bits. 5 mots de 4
 * traits, une tête de 3 (l'échelle 1 / √3 arrondit), des valeurs de 4.
 */
export const EXEMPLE_FLOTTANT: Readonly<Record<'x' | 'wq' | 'wk' | 'wv', Matrice>> = Object.freeze({
  x: [
    [0.1, 0.2, 0.3, -0.4],
    [0.7, -0.4, 0.5, 0.1],
    [-0.3, 0.9, 0.2, 0.6],
    [0.6, 0.1, -0.8, 0.3],
    [0.2, -0.7, 0.4, 0.9],
  ],
  wq: [
    [0.1, 0.2, 0.3],
    [0.4, -0.5, 0.6],
    [-0.7, 0.8, 0.9],
    [0.3, 0.1, -0.6],
  ],
  wk: [
    [0.3, -0.1, 0.2],
    [0.5, 0.7, -0.3],
    [0.2, 0.6, 0.1],
    [-0.4, 0.3, 0.8],
  ],
  wv: [
    [0.2, 0.3, -0.1, 0.6],
    [-0.6, 0.4, 0.7, 0.1],
    [0.9, -0.2, 0.3, -0.5],
    [0.1, 0.8, -0.4, 0.3],
  ],
});

/** La clé « flottant » : les entrées de EXEMPLE_FLOTTANT en motifs, puis tout le détail de sa tête. */
function attendusFlottant(): Attendus {
  const e = EXEMPLE_FLOTTANT;
  const d = detaillerTete(e.x, e.wq, e.wk, e.wv);
  return { x: motifs(e.x), wq: motifs(e.wq), wk: motifs(e.wk), wv: motifs(e.wv), ...detailEnAttendus(d) };
}

/**
 * Les attendus de l'exemple d'attention (tests/attendus-attention.json) : tout le détail de chaque tête.
 *
 * Les scores masqués sont null ; les poids masqués valent +0,0 (motif 0000000000000000).
 */
export function attendusAttention(): Attendus {
  const exemple = chargerExemple();
  const details = detaillerExemple(exemple);
  return {
    phrase: exemple.phrase,
    jetons: [...exemple.jetons],
    tetes: exemple.tetes.map((tete, t) => ({ nom: tete.nom, ...detailEnAttendus(details[t]) })),
    flottant: attendusFlottant(),
  };
}

/** Chaque fichier tests/attendus-<nom>.json et la fonction qui le refait, dans l'ordre de CALCULS en Python. */
export const CALCULS_ATTENDUS = Object.freeze({
  calcul: attendusCalcul,
  donnees: attendusDonnees,
  modele: attendusModele,
  attention: attendusAttention,
});

/** Le nom d'un fichier d'attendus : calcul, donnees, modele ou attention. */
export type NomAttendus = keyof typeof CALCULS_ATTENDUS;

/**
 * L'objet en JSON, indenté d'une espace comme les fichiers du Python.
 *
 * Refuse ce que le JSON ne sait pas écrire et changerait sans bruit :
 * undefined (la clé disparaîtrait) et les nombres non finis (ils deviendraient null).
 */
export function versJson(valeur: unknown): string {
  return JSON.stringify(
    valeur,
    (cle, v: unknown) => {
      if (v === undefined) {
        throw new TypeError(`versJson : « ${cle} » vaut undefined. Chaque clé des attendus doit avoir une valeur.`);
      }
      if (typeof v === 'number' && !Number.isFinite(v)) {
        throw new TypeError(`versJson : « ${cle} » vaut ${v}. Un flottant des attendus s'écrit en motif (versHex).`);
      }
      return v;
    },
    1,
  );
}
