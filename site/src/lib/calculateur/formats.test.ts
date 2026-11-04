// Les formats du calculateur : des nombres lisibles en français, jamais NaN,
// Infinity ni « e+ », même pour les réglages extrêmes.

import { describe, expect, it } from 'vitest';
import { MATERIELS, MODELES_PUBLICS, PRIX_LOCATION, TAUX_DE_CHANGE } from './donnees';
import {
  dixPuissance,
  formaterDuree,
  formaterEuros,
  formaterOctets,
  formaterPrix,
  formaterPuissanceDeDix,
  formaterQuantite,
} from './formats';
import {
  cartesMinimum,
  coutLocationUsd,
  dureeSecondes,
  memoireEntrainementOctets,
  OCTETS_PAR_GO,
  operationsEntrainement,
  usdEnEur,
} from './formules';
import { PRESETS_FORGE } from './ton-ia';

const FINE = '\u202F';
const AN = 31_557_600;

describe('formaterDuree', () => {
  it('les exemples du plan', () => {
    expect(formaterDuree(57_022)).toBe('16 h');
    expect(formaterDuree(3_600)).toBe('1,0 h');
    expect(formaterDuree(513_265)).toBe('5,9 jours');
    expect(formaterDuree(36_846_000)).toBe('1,2 an');
    expect(formaterDuree(31_557_600 * 27_315)).toBe('27\u202F315 ans');
  });

  it('secondes, minutes, heures, jours, ans', () => {
    expect(formaterDuree(0)).toBe('moins d’une seconde');
    expect(formaterDuree(0.4)).toBe('moins d’une seconde');
    expect(formaterDuree(1)).toBe('1 s');
    expect(formaterDuree(59)).toBe('59 s');
    expect(formaterDuree(60)).toBe('1 min');
    expect(formaterDuree(3540)).toBe('59 min');
    expect(formaterDuree(9.94 * 3600)).toBe('9,9 h');
    expect(formaterDuree(10 * 3600)).toBe('10 h');
    expect(formaterDuree(47 * 3600)).toBe('47 h');
    expect(formaterDuree(48 * 3600)).toBe('2,0 jours');
    expect(formaterDuree(12 * 86_400)).toBe('12 jours');
    expect(formaterDuree(364 * 86_400)).toBe('364 jours');
    expect(formaterDuree(AN)).toBe('1,0 an');
    expect(formaterDuree(1.94 * AN)).toBe('1,9 an');
    expect(formaterDuree(2 * AN)).toBe('2,0 ans');
    expect(formaterDuree(12.4 * AN)).toBe('12 ans');
  });

  it('aux frontières, l’unité suit la valeur arrondie : jamais « 60 s », « 60 min » ni « 48 h »', () => {
    expect(formaterDuree(59.6)).toBe('1 min');
    expect(formaterDuree(3599)).toBe('1,0 h');
    expect(formaterDuree(9.96 * 3600)).toBe('10 h');
    expect(formaterDuree(47.6 * 3600)).toBe('2,0 jours');
    expect(formaterDuree(9.96 * 86_400)).toBe('10 jours');
    expect(formaterDuree(1.96 * AN)).toBe('2,0 ans');
    expect(formaterDuree(9.96 * AN)).toBe('10 ans');
  });

  it('refuse une valeur non finie ou négative', () => {
    expect(() => formaterDuree(NaN)).toThrow();
    for (const x of [NaN, Infinity, -Infinity, -1]) expect(() => formaterDuree(x), String(x)).toThrow(RangeError);
  });
});

describe('formaterQuantite', () => {
  it('les exemples du plan', () => {
    expect(formaterQuantite(433_573_120)).toBe('433,6 millions');
    expect(formaterQuantite(8_671_462_400)).toBe('8,67 milliards');
    expect(formaterQuantite(15.6e12)).toBe('15\u202F600 milliards');
  });

  it('un entier sous un million, « million » au singulier sous 2', () => {
    expect(formaterQuantite(999_999)).toBe(`999${FINE}999`);
    expect(formaterQuantite(23_204_736)).toBe('23,2 millions');
    expect(formaterQuantite(1_500_000)).toBe('1,5 million');
    expect(formaterQuantite(2_000_000)).toBe('2,0 millions');
    expect(formaterQuantite(999_999.6)).toBe('1,0 million');
    expect(formaterQuantite(999_960_000)).toBe('1,00 milliard');
    expect(formaterQuantite(86.71e9)).toBe('86,7 milliards');
    expect(formaterQuantite(810e12)).toBe(`810${FINE}000 milliards`);
  });

  it('refuse une valeur non finie ou négative', () => {
    for (const x of [NaN, Infinity, -1]) expect(() => formaterQuantite(x), String(x)).toThrow(RangeError);
  });
});

describe('formaterPuissanceDeDix', () => {
  it('trois chiffres et un exposant en chiffres supérieurs, des espaces fines autour de ×', () => {
    expect(formaterPuissanceDeDix(2.2558e19)).toBe('2,26\u202F×\u202F10¹⁹');
    expect(formaterPuissanceDeDix(3.15e23)).toBe(`3,15${FINE}×${FINE}10²³`);
    expect(formaterPuissanceDeDix(9.996e19)).toBe(`1,00${FINE}×${FINE}10²⁰`);
    expect(formaterPuissanceDeDix(1.968e27)).toBe(`1,97${FINE}×${FINE}10²⁷`);
    expect(formaterPuissanceDeDix(0.0012)).toBe(`1,20${FINE}×${FINE}10⁻³`);
    expect(() => formaterPuissanceDeDix(NaN)).toThrow(RangeError);
  });

  it('dixPuissance écrit 10 et son exposant', () => {
    expect(dixPuissance(19)).toBe('10¹⁹');
    expect(dixPuissance(13)).toBe('10¹³');
    expect(dixPuissance(0)).toBe('10⁰');
    expect(dixPuissance(-4)).toBe('10⁻⁴');
    expect(() => dixPuissance(1.5)).toThrow(RangeError);
  });
});

describe('formaterOctets', () => {
  it('en Go de 1 024³ octets, une décimale sous 100 Go, en To au-delà de 1 024 Go', () => {
    expect(formaterOctets(8.72e9)).toBe('8,1 Go');
    expect(formaterOctets(16 * OCTETS_PAR_GO)).toBe('16,0 Go');
    expect(formaterOctets(150 * OCTETS_PAR_GO)).toBe('150 Go');
    expect(formaterOctets(1023 * OCTETS_PAR_GO)).toBe(`1${FINE}023 Go`);
    expect(formaterOctets(1024 * OCTETS_PAR_GO)).toBe('1,0 To');
    expect(formaterOctets(6.5 * 1024 * OCTETS_PAR_GO)).toBe('6,5 To');
  });

  it('sous 1 Go, en Mo de 1 024² octets (jamais « 0,0 Go »)', () => {
    expect(formaterOctets(0)).toBe('0 Mo');
    expect(formaterOctets(46_409_472)).toBe('44 Mo');
    expect(formaterOctets(1023 * 1024 * 1024)).toBe(`1${FINE}023 Mo`);
    expect(formaterOctets(1023.6 * 1024 * 1024)).toBe('1,0 Go');
  });

  it('refuse une valeur non finie ou négative', () => {
    for (const x of [NaN, Infinity, -1]) expect(() => formaterOctets(x), String(x)).toThrow(RangeError);
  });
});

describe('formaterEuros et formaterPrix', () => {
  it('les exemples du plan', () => {
    expect(formaterEuros(8.5587)).toBe('8,56 €');
    expect(formaterEuros(0.4)).toBe('moins d’un euro');
    expect(formaterEuros(33.4e6)).toBe('33 millions d’euros');
  });

  it('deux décimales sous 10 €, un entier sous 1 000 €, trois chiffres significatifs sous un million', () => {
    expect(formaterEuros(1)).toBe('1,00 €');
    expect(formaterEuros(9.996)).toBe('10 €');
    expect(formaterEuros(38.115)).toBe('38 €');
    expect(formaterEuros(999.4)).toBe('999 €');
    expect(formaterEuros(1234)).toBe(`1${FINE}230 €`);
    expect(formaterEuros(174_139)).toBe(`174${FINE}000 €`);
    expect(formaterEuros(999_600)).toBe('1,0 million d’euros');
  });

  it('les millions puis les milliards d’euros', () => {
    expect(formaterEuros(1.2e6)).toBe('1,2 million d’euros');
    expect(formaterEuros(2.5e6)).toBe('2,5 millions d’euros');
    expect(formaterEuros(9.96e6)).toBe('10 millions d’euros');
    expect(formaterEuros(152e6)).toBe('152 millions d’euros');
    expect(formaterEuros(1.5e9)).toBe('1,5 milliard d’euros');
    expect(formaterEuros(33e9)).toBe('33 milliards d’euros');
    expect(formaterEuros(1.2e12)).toBe(`1${FINE}200 milliards d’euros`);
  });

  it('un prix horaire en dollars', () => {
    expect(formaterPrix(2.69)).toBe('2,69 $');
    expect(formaterPrix(12.29)).toBe('12,29 $');
    expect(formaterPrix(0.34)).toBe('0,34 $');
  });

  it('refuse une valeur non finie ou négative', () => {
    for (const x of [NaN, Infinity, -0.01]) {
      expect(() => formaterEuros(x), String(x)).toThrow(RangeError);
      expect(() => formaterPrix(x), String(x)).toThrow(RangeError);
    }
  });
});

// Point à surveiller 4 du plan : les réglages extrêmes du calculateur.
describe('valeurs extrêmes : jamais NaN, Infinity ni « e+ »', () => {
  const INTERDIT = /NaN|Infinity|e\+|e-\d/;
  const carte = (id: string) => {
    const m = MATERIELS.find((x) => x.id === id);
    if (!m) throw new Error(`matériel ${id} introuvable`);
    return m;
  };
  const llama405 = MODELES_PUBLICS.find((m) => m.id === 'llama-3-405b');
  if (!llama405) throw new Error('llama-3-405b introuvable');

  it('405 milliards de paramètres sur une seule RTX 5070 Ti : des années, et « au moins N cartes »', () => {
    const rtx = carte('rtx-5070-ti');
    const operations = operationsEntrainement(llama405.parametres, 20 * llama405.parametres);
    const duree = formaterDuree(dureeSecondes(operations, rtx.creteTflops, 0.5, 1));
    expect(duree).toMatch(/^\d[\d\u202F]* ans$/);
    expect(duree).toBe(`14${FINE}192 ans`);
    const cartes = cartesMinimum(memoireEntrainementOctets(llama405).total, rtx.memoireGo);
    expect(cartes).toBe(411);
    expect(formaterPuissanceDeDix(operations)).not.toMatch(INTERDIT);
    expect(formaterOctets(memoireEntrainementOctets(llama405).total)).toBe('6,4 To');
  });

  it('16 384 H100 : des millions d’euros de location', () => {
    const h100 = carte('h100-sxm');
    const operations = operationsEntrainement(llama405.parametres, 20 * llama405.parametres);
    const secondes = dureeSecondes(operations, h100.creteTflops, 0.4, 16_384);
    expect(formaterDuree(secondes)).toBe('35 jours');
    const prix = PRIX_LOCATION.filter((p) => p.materiel === 'h100-sxm').map((p) => p.usdParHeure);
    const eur = (usd: number) => usdEnEur(coutLocationUsd(secondes, 16_384, usd), TAUX_DE_CHANGE.usdPourUnEur);
    expect(formaterEuros(eur(Math.min(...prix)))).toBe('33 millions d’euros');
    expect(formaterEuros(eur(Math.max(...prix)))).toBe('152 millions d’euros');
  });

  it('1 jeton par paramètre, et les plus grands réglages possibles', () => {
    const f = PRESETS_FORGE.tres_grand;
    expect(formaterQuantite(f.parametres)).toBe('433,6 millions');
    const petit = operationsEntrainement(f.parametres, f.parametres);
    expect(formaterPuissanceDeDix(petit)).toBe(`1,13${FINE}×${FINE}10¹⁸`);
    // Le pire : 405 milliards, 2 000 jetons par paramètre, une T4 à 10 %.
    const t4 = carte('t4');
    const pire = operationsEntrainement(llama405.parametres, 2000 * llama405.parametres);
    const textes = [
      formaterQuantite(2000 * llama405.parametres),
      formaterPuissanceDeDix(pire),
      formaterDuree(dureeSecondes(pire, t4.creteTflops, 0.1, 1)),
      formaterEuros(usdEnEur(coutLocationUsd(dureeSecondes(pire, 989, 0.1, 1), 1, 12.29), 1.1179)),
    ];
    for (const t of textes) expect(t).not.toMatch(INTERDIT);
    expect(textes[2]).toMatch(/ ans$/);
    // Le plus petit : mini, 1 jeton par paramètre, 16 384 B200 à 70 %.
    const mini = PRESETS_FORGE.mini;
    const s = dureeSecondes(operationsEntrainement(mini.parametres, mini.parametres), carte('b200').creteTflops, 0.7, 16_384);
    expect(formaterDuree(s)).toBe('moins d’une seconde');
  });
});
