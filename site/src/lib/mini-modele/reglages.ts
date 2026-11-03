// Les réglages de l'entraînement du mini-modèle : les taux proposés, les
// réglages et les deux préréglages.
//
// Ce module n'importe rien : la page peut lire les taux et les préréglages
// sans embarquer le moteur ni les prénoms (seul le Worker les charge, par
// entrainement.ts, qui réexporte tout ce qui est ici).
//
// C'est le jumeau de la partie « réglages » de
// projets/mini-modele/mini_modele/entrainement.py (TAUX_PROPOSES,
// ReglagesMini, PRESETS_MINI), avec les noms en camelCase. Les attendus
// (tests/attendus-modele.json, clé « entrainement », « presets » et
// « taux_proposes ») le vérifient dans entrainement.test.ts.

/** Les taux d'apprentissage maximaux que le lecteur peut choisir. */
export const TAUX_PROPOSES: readonly number[] = Object.freeze([0.001, 0.003, 0.01, 0.03, 0.1, 0.3]);

/** Les réglages d'un entraînement. Une même valeur redonne exactement la même courbe. */
export interface ReglagesMini {
  readonly pasTotal: number;
  readonly echauffement: number;
  readonly tauxMax: number;
  readonly lot: number;
  readonly ratioMin: number;
  readonly beta1: number;
  readonly beta2: number;
  readonly epsilon: number;
  readonly poidsDecroissance: number;
  readonly ecretage: number;
  readonly graine: number;
  readonly validationTous: number;
  readonly nbValidation: number;
  readonly nbEchantillons: number;
}

/** Les noms des deux préréglages. */
export type NomPreset = 'complet' | 'avant-gout';

const GRAINE_MAX = 4294967295; // 2^32 − 1 : la plus grande graine de Hasard

// Les champs entiers des réglages, et leur plus petite valeur permise.
const ENTIERS: readonly [keyof ReglagesMini, number][] = [
  ['pasTotal', 1],
  ['echauffement', 0],
  ['lot', 1],
  ['validationTous', 1],
  ['nbValidation', 1],
  ['nbEchantillons', 0],
];

// Les champs flottants des réglages, et ce qu'ils doivent respecter.
const FLOTTANTS: readonly [keyof ReglagesMini, string, (x: number) => boolean][] = [
  ['tauxMax', 'plus grand que 0', (x) => x > 0.0],
  ['ratioMin', 'de 0 à 1', (x) => x >= 0.0 && x <= 1.0],
  ['beta1', 'de 0 à 1, 1 non compris', (x) => x >= 0.0 && x < 1.0],
  ['beta2', 'de 0 à 1, 1 non compris', (x) => x >= 0.0 && x < 1.0],
  ['epsilon', 'plus grand que 0', (x) => x > 0.0],
  ['poidsDecroissance', 'positif ou nul', (x) => x >= 0.0],
  ['ecretage', 'plus grand que 0', (x) => x > 0.0],
];

/**
 * Vérifie les réglages comme ReglagesMini en Python (mêmes règles, mêmes
 * messages), et en renvoie une copie figée.
 */
export function verifierReglages(r: ReglagesMini): ReglagesMini {
  for (const [nom, plusPetit] of ENTIERS) {
    const valeur: unknown = r[nom];
    if (typeof valeur !== 'number' || !Number.isInteger(valeur) || valeur < plusPetit) {
      throw new RangeError(`ReglagesMini : ${nom} doit être un entier d'au moins ${plusPetit} (reçu ${String(valeur)}).`);
    }
  }
  const graine: unknown = r.graine;
  if (typeof graine !== 'number' || !Number.isInteger(graine) || graine < 0 || graine > GRAINE_MAX) {
    throw new RangeError(`ReglagesMini : graine doit être un entier de 0 à 2^32 − 1 (reçu ${String(graine)}).`);
  }
  for (const [nom, condition, permis] of FLOTTANTS) {
    const valeur: unknown = r[nom];
    if (typeof valeur !== 'number' || !Number.isFinite(valeur) || !permis(valeur)) {
      throw new RangeError(`ReglagesMini : ${nom} doit être un nombre fini ${condition} (reçu ${String(valeur)}).`);
    }
  }
  return Object.freeze({
    pasTotal: r.pasTotal,
    echauffement: r.echauffement,
    tauxMax: r.tauxMax,
    lot: r.lot,
    ratioMin: r.ratioMin,
    beta1: r.beta1,
    beta2: r.beta2,
    epsilon: r.epsilon,
    poidsDecroissance: r.poidsDecroissance,
    ecretage: r.ecretage,
    graine: r.graine,
    validationTous: r.validationTous,
    nbValidation: r.nbValidation,
    nbEchantillons: r.nbEchantillons,
  });
}

/**
 * Des réglages de pasTotal pas, dont echauffement de montée du taux, avec les
 * valeurs par défaut du Python pour tout ce que autres ne change pas. Ils sont
 * vérifiés, et figés.
 */
export function reglagesMini(
  pasTotal: number,
  echauffement: number,
  autres: Partial<Omit<ReglagesMini, 'pasTotal' | 'echauffement'>> = {},
): ReglagesMini {
  return verifierReglages({
    pasTotal,
    echauffement,
    tauxMax: autres.tauxMax ?? 0.01,
    lot: autres.lot ?? 8,
    ratioMin: autres.ratioMin ?? 0.1,
    beta1: autres.beta1 ?? 0.9,
    beta2: autres.beta2 ?? 0.95,
    epsilon: autres.epsilon ?? 1e-8,
    poidsDecroissance: autres.poidsDecroissance ?? 0.1,
    ecretage: autres.ecretage ?? 1.0,
    graine: autres.graine ?? 1234,
    validationTous: autres.validationTous ?? 100,
    nbValidation: autres.nbValidation ?? 256,
    nbEchantillons: autres.nbEchantillons ?? 8,
  });
}

/** Les deux préréglages du site : l'entraînement complet (1.5), et l'avant-goût (0.5). */
export const PRESETS_MINI: Readonly<Record<NomPreset, ReglagesMini>> = Object.freeze({
  complet: reglagesMini(3000, 100),
  'avant-gout': reglagesMini(600, 50),
});
