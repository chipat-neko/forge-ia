// Les formules du calculateur, vérifiées sur les exemples chiffrés de leurs
// sources : chaque attendu est un nombre imprimé dans l'article cité.

import { describe, expect, it } from 'vitest';
import {
  activationsSansFlashOctets,
  cacheKvOctets,
  cartesMinimum,
  coutElectriciteEur,
  coutLocationUsd,
  dureeSecondes,
  efficaciteMesuree,
  efficaciteMesureeAvecAttention,
  energieKwh,
  memoireEntrainementOctets,
  memoirePoidsOctets,
  OCTETS_PAR_GO,
  operationsEntrainement,
  operationsParJetonAvecAttention,
  plafondGenerationJetonsParSeconde,
  usdEnEur,
  type Forme,
} from './formules';

/** Complète une Forme avec des valeurs sans effet sur la formule testée. */
function formeAvec(partiel: Partial<Forme>): Forme {
  return { parametres: 1e6, couches: 1, dim: 64, tetes: 1, tetesKv: 1, contexte: 1, vocabulaire: 1, ...partiel };
}

// La forme de ton IA (preset « tres_grand » de forge) : 20 couches, dim 1 280,
// 20 têtes, contexte de 2 048, vocabulaire de 32 768.
const TRES_GRAND: Forme = {
  parametres: 433_573_120,
  couches: 20,
  dim: 1280,
  tetes: 20,
  tetesKv: 20,
  contexte: 2048,
  vocabulaire: 32_768,
};

describe('le calcul d’un entraînement : 6·N·D', () => {
  it('Chinchilla, tableau 3 : 400 millions de paramètres et 8 milliards de jetons font 1,92e19', () => {
    expect(operationsEntrainement(400e6, 8.0e9)).toBeCloseTo(1.92e19, -16);
    // La ligne suivante du tableau : 1 milliard de paramètres, 20,2 milliards de jetons, 1,21e20.
    expect(Math.abs(operationsEntrainement(1e9, 20.2e9) / 1.21e20 - 1)).toBeLessThan(0.01);
  });

  it('GPT-3 (tableau D.1) et Llama 3 405B (section 3.2) à 1 % près', () => {
    expect(Math.abs(operationsEntrainement(175e9, 300e9) / 3.14e23 - 1)).toBeLessThan(0.01);
    expect(Math.abs(operationsEntrainement(405e9, 15.6e12) / 3.8e25 - 1)).toBeLessThan(0.01);
  });

  it('avec l’attention (PaLM, annexe B) : 6N + 12·L·h·s par jeton', () => {
    // 6 × 433 573 120 + 12 × 20 × 1 280 × 2 048
    expect(operationsParJetonAvecAttention(TRES_GRAND)).toBe(2_601_438_720 + 629_145_600);
  });
});

describe('la durée et l’efficacité', () => {
  it('durée = opérations ÷ (crête × efficacité × cartes)', () => {
    expect(dureeSecondes(87.9e12 * 3600, 87.9, 1, 1)).toBeCloseTo(3600, 9);
    expect(dureeSecondes(87.9e12 * 3600, 87.9, 0.5, 1)).toBeCloseTo(7200, 9);
    expect(dureeSecondes(87.9e12 * 3600, 87.9, 0.5, 4)).toBeCloseTo(1800, 9);
    // Ton IA sur la RTX 5070 Ti à 50 % : 513 271 s, un peu moins de 6 jours.
    const s = dureeSecondes(operationsEntrainement(433_573_120, 20 * 433_573_120), 87.9, 0.5, 1);
    expect(s).toBeCloseTo(513_271.4, 0);
  });

  it('l’efficacité mesurée (MFU) : 6·N·débit ÷ crête, et la même en comptant l’attention', () => {
    expect(efficaciteMesuree(433_573_120, 17_855, 87.9)).toBeCloseTo(0.528, 3);
    expect(efficaciteMesureeAvecAttention(TRES_GRAND, 17_855, 87.9)).toBeCloseTo(0.656, 3);
    expect(efficaciteMesureeAvecAttention(TRES_GRAND, 17_855, 87.9)).toBe(
      (17_855 * operationsParJetonAvecAttention(TRES_GRAND)) / 87.9e12,
    );
  });
});

describe('la mémoire', () => {
  it('ZeRO, section 3.1 : 16 octets par paramètre, « au moins 24 Go » pour GPT-2 1,5 milliard, 3 Go de poids fp16', () => {
    expect(memoireEntrainementOctets(formeAvec({ parametres: 1.5e9 })).etats).toBe(24e9);
    expect(memoirePoidsOctets(1.5e9, 2)).toBe(3e9);
  });

  it('Korthikanti, équation 1 : s·b·h·L·(34 + 5·a·s/h) sans FlashAttention', () => {
    expect(activationsSansFlashOctets(formeAvec({ contexte: 2048, dim: 1024, couches: 24, tetes: 16 }))).toBe(9_764_339_712);
    expect(activationsSansFlashOctets(formeAvec({ contexte: 2048, dim: 1024, couches: 24, tetes: 16 }), 2)).toBe(
      2 * 9_764_339_712,
    );
  });

  it('Korthikanti, tableau 2 (recalcul sélectif) : 34·s·b·h·L sans la matrice s×s', () => {
    const f = formeAvec({ contexte: 2048, dim: 1024, couches: 24, tetes: 16, parametres: 1e9 });
    const m = memoireEntrainementOctets(f);
    expect(m.activations).toBe(34 * 2048 * 1024 * 24);
    expect(m.total).toBe(m.etats + m.activations);
    expect(memoireEntrainementOctets(f, 4).activations).toBe(4 * 34 * 2048 * 1024 * 24);
    // Ton IA : 6,94 Go d'états et 1,78 Go d'activations, 8,1 Go en tout (le pic mesuré est de 10,9 Go).
    expect(memoireEntrainementOctets(TRES_GRAND).total).toBe(8_719_749_120);
  });

  it('cache KV (kipply) : 2·2·L·têtes_kv·d_tête octets par jeton, 2,15 Go pour 4 096 jetons d’un 7B', () => {
    expect(cacheKvOctets(formeAvec({ couches: 32, tetesKv: 32, dim: 4096, tetes: 32 }), 4096)).toBe(2_147_483_648);
    // Avec 8 têtes KV (attention groupée, comme Llama 3 8B) : 4 fois moins.
    expect(cacheKvOctets(formeAvec({ couches: 32, tetesKv: 8, dim: 4096, tetes: 32 }), 4096)).toBe(536_870_912);
    expect(cacheKvOctets(formeAvec({ couches: 32, tetesKv: 8, dim: 4096, tetes: 32 }), 4096, 3)).toBe(3 * 536_870_912);
  });

  it('le plafond de génération : la bande passante lit tous les poids à chaque jeton', () => {
    // 433,6 millions de paramètres en bf16 sur 896 Go/s : environ 1 033 jetons par seconde.
    expect(plafondGenerationJetonsParSeconde(433_573_120, 2, 896)).toBeCloseTo(896e9 / (2 * 433_573_120), 9);
    expect(plafondGenerationJetonsParSeconde(433_573_120, 2, 896)).toBeCloseTo(1033.27, 2);
  });

  it('le nombre de cartes : arrondi au-dessus, en Go de 1 024³ octets', () => {
    expect(OCTETS_PAR_GO).toBe(1024 * 1024 * 1024);
    expect(cartesMinimum(16 * OCTETS_PAR_GO, 16)).toBe(1);
    expect(cartesMinimum(16 * OCTETS_PAR_GO + 1, 16)).toBe(2);
    expect(cartesMinimum(8_719_749_120, 16)).toBe(1);
  });
});

describe('l’énergie et l’argent', () => {
  it('kWh = W × cartes × secondes ÷ 3,6 millions ; euros = kWh × prix', () => {
    expect(energieKwh(1000, 1, 3600)).toBe(1);
    expect(energieKwh(300, 2, 3600)).toBeCloseTo(0.6, 12);
    // Le réglage de départ du calculateur : 42,8 kWh, environ 8,56 €.
    const kwh = energieKwh(300, 1, 513_271.4);
    expect(kwh).toBeCloseTo(42.77, 2);
    expect(coutElectriciteEur(kwh, 0.2001)).toBeCloseTo(8.5588, 3);
  });

  it('location = heures × cartes × prix horaire ; dollars en euros au taux de la BCE', () => {
    expect(coutLocationUsd(3600, 8, 2.69)).toBeCloseTo(21.52, 10);
    expect(coutLocationUsd(1800, 1, 4)).toBe(2);
    expect(usdEnEur(1.1179, 1.1179)).toBe(1);
    expect(usdEnEur(100, 1.25)).toBe(80);
  });
});

describe('les entrées impossibles lèvent une erreur, jamais NaN ni Infinity', () => {
  it('valeurs non finies ou négatives', () => {
    for (const x of [NaN, Infinity, -Infinity, -1]) {
      expect(() => operationsEntrainement(x, 1e9), String(x)).toThrow(RangeError);
      expect(() => operationsEntrainement(1e9, x), String(x)).toThrow(RangeError);
      expect(() => coutLocationUsd(x, 1, 2), String(x)).toThrow(RangeError);
      expect(() => energieKwh(300, 1, x), String(x)).toThrow(RangeError);
    }
  });

  it('divisions par zéro : crête, efficacité, cartes, bande passante, mémoire, taux', () => {
    expect(() => dureeSecondes(1e20, 0, 0.5, 1)).toThrow(/crête/);
    expect(() => dureeSecondes(1e20, 87.9, 0, 1)).toThrow(/efficacité/);
    expect(() => dureeSecondes(1e20, 87.9, 1.2, 1)).toThrow(/efficacité/);
    expect(() => dureeSecondes(1e20, 87.9, 0.5, 0)).toThrow(/cartes/);
    expect(() => dureeSecondes(1e20, 87.9, 0.5, 1.5)).toThrow(/cartes/);
    expect(() => plafondGenerationJetonsParSeconde(1e9, 2, 0)).toThrow(/bande passante/);
    expect(() => cartesMinimum(1e9, 0)).toThrow(/mémoire/);
    expect(() => usdEnEur(10, 0)).toThrow(/taux/);
    expect(() => efficaciteMesuree(1e9, 1000, 0)).toThrow(/crête/);
  });

  it('une forme impossible', () => {
    expect(() => cacheKvOctets(formeAvec({ dim: 100, tetes: 3 }), 10)).toThrow(/divisible/);
    expect(() => cacheKvOctets(formeAvec({ tetes: 4, tetesKv: 3, dim: 64 }), 10)).toThrow(/têtes KV/);
    expect(() => memoireEntrainementOctets(formeAvec({ couches: 0 }))).toThrow(/couches/);
    expect(() => memoireEntrainementOctets(formeAvec({ parametres: NaN }))).toThrow(/paramètres/);
    expect(() => memoireEntrainementOctets(formeAvec({}), 0)).toThrow(/micro-lot/);
  });
});
