// L'entraînement du mini-modèle : le taux, l'écrêtage, AdamW, et l'Entraineur.
//
// C'est le jumeau exact de projets/mini-modele/mini_modele/entrainement.py :
// mêmes fonctions, mêmes boucles, même ordre des opérations (les noms passent
// en camelCase). Les attendus (tests/attendus-modele.json, clé
// « entrainement ») le prouvent au bit près dans entrainement.test.ts : la
// perte et le taux de 20 pas, tous les paramètres après ces 20 pas, le
// planning du taux et une divergence.
//
// La recette est celle de ton IA (projets/forge) : AdamW avec beta1 = 0,9 et
// beta2 = 0,95, une décroissance des poids de 0,1, un écrêtage du gradient à 1,
// et un taux d'apprentissage qui monte en ligne droite, puis redescend en
// cosinus. Le taux est le même code que forge/entrainement/planning.py, avec
// le cos et le PI de calcul.ts.
//
// Un pas d'entraînement se fait dans cet ordre, le même en Python :
//  1. le numéro du pas augmente (le premier pas porte le numéro 1) ;
//  2. la perte et le gradient d'un lot de prénoms ;
//  3. si la perte n'est pas finie, ou dépasse 3 × ln V, l'entraînement a
//     divergé : on le note, et on s'arrête sans toucher aux paramètres ;
//  4. le taux du pas ;
//  5. l'écrêtage du gradient, puis le pas d'AdamW.
//
// Trois hasards séparés : les poids de départ (graine), l'ordre des prénoms
// (graine + 1), et les prénoms inventés au pas p (un Hasard neuf de graine
// graine + 2 + p). Inventer des prénoms ou mesurer la validation ne change
// donc rien à l'entraînement. Ce fichier est vérifié par sources.test.ts.

import { cos, Hasard, log, PI, racine } from './calcul';
import { decoder, donneesParDefaut, tailleVocabulaire, type Donnees } from './donnees';
import { configMini, generer, initialiser, perte, perteEtGradient, type ConfigMini } from './modele';
import { verifierReglages, type ReglagesMini } from './reglages';

export { PRESETS_MINI, reglagesMini, TAUX_PROPOSES, verifierReglages } from './reglages';
export type { NomPreset, ReglagesMini } from './reglages';

/**
 * Taux d'apprentissage du pas numéro pas (le premier pas porte le numéro 1) : le code de forge.
 *
 * - de 0 à echauffement : montée linéaire, de 0 à tauxMax ;
 * - de echauffement à pasTotal : descente en cosinus, de tauxMax à ratioMin × tauxMax ;
 * - après pasTotal : ratioMin × tauxMax, sans bouger.
 */
export function taux(pas: number, pasTotal: number, tauxMax: number, echauffement: number, ratioMin = 0.1): number {
  const tauxMin = ratioMin * tauxMax;
  if (pas < echauffement) {
    return (tauxMax * pas) / echauffement;
  }
  if (pas >= pasTotal) {
    return tauxMin;
  }
  // forge prend le plus grand de 1 et de pasTotal − echauffement : la même chose, en entiers.
  let etendue = pasTotal - echauffement;
  if (etendue < 1) {
    etendue = 1;
  }
  const avancement = (pas - echauffement) / etendue; // de 0 à 1 (jamais 1 : pas < pasTotal)
  return tauxMin + (tauxMax - tauxMin) * 0.5 * (1 + cos(PI * avancement));
}

/**
 * Entraîne le mini-modèle sur les prénoms, un pas à la fois.
 *
 * reglages, config (la forme du modèle), donnees, params (les paramètres,
 * modifiés sur place), pas (0 au départ ; le premier pas porte le numéro 1),
 * diverge (vrai dès que l'erreur a explosé) et limiteDivergence.
 */
export class Entraineur {
  readonly reglages: ReglagesMini;
  readonly donnees: Donnees;
  readonly config: ConfigMini;
  readonly params: Float64Array;
  /** Au-delà de 3 × ln V (trois fois l'erreur du pur hasard), l'erreur a explosé. */
  readonly limiteDivergence: number;
  private pasFaits = 0;
  private aDiverge = false;
  private readonly gradient: Float64Array;
  private readonly m: Float64Array;
  private readonly v: Float64Array;
  // beta1^pas et beta2^pas, tenus par des produits successifs (pas de puissance).
  private b1t = 1.0;
  private b2t = 1.0;
  private dernierePerte = NaN;
  private readonly hasardOrdre: Hasard;
  private ordre: number[] = [];
  private position = 0;

  constructor(reglages: ReglagesMini, donnees: Donnees | null = null) {
    this.reglages = verifierReglages(reglages);
    this.donnees = donnees === null ? donneesParDefaut() : donnees;
    const n = this.donnees.entrainement.length;
    if (this.reglages.lot > n) {
      throw new RangeError(
        `Entraineur : un lot de ${this.reglages.lot} prénoms, mais il n'y a que ${n} prénoms d'entraînement. ` +
          'Prends un lot plus petit.',
      );
    }
    this.config = configMini(tailleVocabulaire(this.donnees.vocabulaire));
    this.params = initialiser(this.config, new Hasard(this.reglages.graine));
    this.limiteDivergence = 3.0 * log(this.config.tailleVocabulaire);
    const nombre = this.params.length;
    this.gradient = new Float64Array(nombre);
    this.m = new Float64Array(nombre);
    this.v = new Float64Array(nombre);
    this.hasardOrdre = new Hasard(this.reglages.graine + 1);
    this.melanger();
  }

  /** Le numéro du dernier pas fait (0 au départ). */
  get pas(): number {
    return this.pasFaits;
  }

  /** Vrai dès que l'erreur a explosé : faireUnPas ne fait alors plus rien. */
  get diverge(): boolean {
    return this.aDiverge;
  }

  /** Un nouvel ordre des prénoms d'entraînement : [0, …, n − 1] mélangé, et on repart de 0. */
  private melanger(): void {
    this.ordre = Array.from({ length: this.donnees.entrainement.length }, (_, i) => i);
    this.hasardOrdre.melanger(this.ordre);
    this.position = 0;
  }

  /**
   * Les prénoms du prochain lot, dans l'ordre mélangé (région `lot` d'entrainement.py).
   *
   * Quand il n'en reste plus assez pour un lot entier, on mélange un nouvel
   * ordre et on repart du début : les derniers prénoms de l'ancien ordre
   * attendront le tour suivant.
   */
  private prochainLot(): (readonly number[])[] {
    const r = this.reglages;
    if (this.position + r.lot > this.donnees.entrainement.length) {
      this.melanger();
    }
    const lot: (readonly number[])[] = [];
    for (let i = 0; i < r.lot; i++) {
      lot.push(this.donnees.entrainement[this.ordre[this.position + i]]);
    }
    this.position += r.lot;
    return lot;
  }

  /**
   * Un pas d'entraînement. Renvoie l'erreur du lot, mesurée avant de corriger les paramètres.
   *
   * Si l'entraînement a divergé, ne fait plus rien et renvoie la dernière erreur.
   */
  faireUnPas(): number {
    if (this.aDiverge) {
      return this.dernierePerte;
    }
    const r = this.reglages;
    this.pasFaits += 1;
    const lot = this.prochainLot();
    const gradient = this.gradient;
    const params = this.params;
    const n = params.length;
    const perteLot = perteEtGradient(this.config, params, lot, gradient);
    this.dernierePerte = perteLot;
    if (!Number.isFinite(perteLot) || perteLot > this.limiteDivergence) {
      this.aDiverge = true;
      return perteLot;
    }
    const t = taux(this.pasFaits, r.pasTotal, r.tauxMax, r.echauffement, r.ratioMin);
    // L'écrêtage (région ecretage d'entrainement.py).
    let carres = 0.0;
    for (let i = 0; i < n; i++) {
      const g = gradient[i];
      carres += g * g;
    }
    const norme = racine(carres);
    if (norme > r.ecretage) {
      const facteur = r.ecretage / norme;
      for (let i = 0; i < n; i++) {
        gradient[i] = gradient[i] * facteur;
      }
    }
    // AdamW (région adamw d'entrainement.py).
    const m = this.m;
    const v = this.v;
    this.b1t = this.b1t * r.beta1;
    this.b2t = this.b2t * r.beta2;
    for (let i = 0; i < n; i++) {
      const g = gradient[i];
      m[i] = r.beta1 * m[i] + (1.0 - r.beta1) * g;
      v[i] = r.beta2 * v[i] + (1.0 - r.beta2) * (g * g);
      const mChapeau = m[i] / (1.0 - this.b1t);
      const vChapeau = v[i] / (1.0 - this.b2t);
      const p = params[i] * (1.0 - t * r.poidsDecroissance);
      params[i] = p - (t * mChapeau) / (racine(vChapeau) + r.epsilon);
    }
    return perteLot;
  }

  /** L'erreur moyenne sur les nbValidation premiers prénoms de validation, que le modèle ne voit jamais. */
  perteValidation(): number {
    return perte(this.config, this.params, this.donnees.validation.slice(0, this.reglages.nbValidation));
  }

  /** nbEchantillons prénoms inventés, tirés par un Hasard(graine + 2 + pas) neuf. */
  echantillons(): string[] {
    const r = this.reglages;
    const inventes = generer(this.config, this.params, new Hasard(r.graine + 2 + this.pasFaits), r.nbEchantillons);
    return inventes.map((p) => decoder(p, this.donnees.vocabulaire));
  }

  /** Le taux du pas numéro pas (0 avant le premier pas). */
  tauxCourant(): number {
    const r = this.reglages;
    return taux(this.pasFaits, r.pasTotal, r.tauxMax, r.echauffement, r.ratioMin);
  }
}
