// Les paris du chapitre 0.4 : leurs bonnes réponses viennent du jumeau des
// formes (formes.ts) et des mesures (mesures/*.json), jamais écrites à la main.
// Les mesures du processeur seront refaites à la porte, et celles de la carte
// n'existent pas encore : les fonctions qui en tirent un verdict sont essayées
// ici sur de fausses mesures, qui couvrent chaque verdict.

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { A_DEPART, B_DEPART } from './atelier-formes';
import { formeDiffusee, memoireOctets } from './formes';
import { lireMesures, type MesuresChrono } from './mesures';
import {
  choixDiffusion,
  choixFils,
  choixMemoire,
  choixPetiteMatrice,
  chrono,
  ecrireMillisecondes,
  filsDesColonnes,
  lignesChronos,
  meilleurChrono,
  OCTETS_FLOAT32,
  OCTETS_PAR_MO,
  phraseFils,
  gainDuReglageParDefaut,
  SEUIL_PARALLELE,
  questionFils,
  rapportFils,
  TAILLE_DU_PARI_FILS,
  TAILLE_DU_PARI_MEMOIRE,
  TAILLE_PETITE,
  verdictFils,
} from './paris-0-4';

const FINE = '\u202F';
const INSECABLE = '\u00A0';
// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const RACINE = resolve('..');

/** Le texte du choix juste (et vérifie qu'il est seul). */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste);
  expect(justes).toHaveLength(1);
  return justes[0].texte;
}

/** De fausses mesures du processeur : `ms[taille][fils]` en millisecondes. */
function processeur(ms: Record<number, Record<number, number>>, defaut = 8, max = 16): MesuresChrono {
  return {
    version: 1,
    releve_le: '2026-11-10',
    appareil: 'cpu',
    nom: 'Processeur d’essai',
    torch: '2.15.0+cpu',
    fils_par_defaut: defaut,
    fils_max: max,
    mesures: Object.entries(ms).flatMap(([taille, parFils]) =>
      Object.entries(parFils).map(([fils, millisecondes]) => ({ taille: Number(taille), fils: Number(fils), millisecondes })),
    ),
    transfert_ms: null,
  };
}

/** De fausses mesures de la carte : `ms[taille]` en millisecondes. */
function carte(ms: Record<number, number>): MesuresChrono {
  return {
    version: 1,
    releve_le: '2026-11-10',
    appareil: 'cuda',
    nom: 'NVIDIA GeForce RTX 5070 Ti',
    torch: '2.15.0+cu132',
    fils_par_defaut: 8,
    fils_max: 16,
    mesures: Object.entries(ms).map(([taille, millisecondes]) => ({ taille: Number(taille), fils: null, millisecondes })),
    transfert_ms: Object.fromEntries(Object.keys(ms).map((t) => [t, 1])),
  };
}

describe('pari « diffusion » : (3, 1) + (4,)', () => {
  it('trois choix, le juste est celui du jumeau des formes', () => {
    expect(formeDiffusee(A_DEPART, B_DEPART)).toStrictEqual([3, 4]);
    expect(choixDiffusion().map((c) => c.texte)).toEqual(['(3, 4)', '(4, 3)', 'Impossible']);
    expect(juste(choixDiffusion())).toBe('(3, 4)');
  });
});

describe('pari « memoire » : 4 096 × 4 096 en float32', () => {
  it('64 Mo, avec 1 Mo = 2²⁰ octets, comme le calculateur', () => {
    expect(TAILLE_DU_PARI_MEMOIRE).toBe(4096);
    expect(OCTETS_FLOAT32).toBe(4);
    expect(OCTETS_PAR_MO).toBe(2 ** 20);
    const octets = memoireOctets([TAILLE_DU_PARI_MEMOIRE, TAILLE_DU_PARI_MEMOIRE], OCTETS_FLOAT32);
    expect(octets / OCTETS_PAR_MO).toBe(64);
    expect(choixMemoire().map((c) => c.texte)).toEqual(['16 Mo', '64 Mo', '4 Go']);
    expect(juste(choixMemoire())).toBe('64 Mo');
  });

  it('la taille d’un float32 et les octets sont ceux que PyTorch a donnés (attendus du projet)', () => {
    const attendus = JSON.parse(readFileSync('../projets/0.4-tenseurs/tests/attendus-formes.json', 'utf8')) as {
      memoire: { forme: number[]; dtype: string; octets_par_nombre: number; octets: number }[];
    };
    const cas = attendus.memoire.find(
      (c) => c.dtype === 'float32' && c.forme.length === 2 && c.forme.every((t) => t === TAILLE_DU_PARI_MEMOIRE),
    );
    expect(cas, 'le cas 4 096 × 4 096 en float32 manque aux attendus').toBeDefined();
    expect(cas!.octets_par_nombre).toBe(OCTETS_FLOAT32);
    expect(cas!.octets).toBe(memoireOctets(cas!.forme, OCTETS_FLOAT32));
  });
});

describe('pari « fils » : tous les fils contre le réglage par défaut', () => {
  const T = TAILLE_DU_PARI_FILS;

  it('les trois verdicts, selon le rapport des chronos', () => {
    expect(T).toBe(4096);
    // Deux fois plus vite : rapport 2,0 ; juste au seuil de 1,8.
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 200, 16: 100 } })))).toBe('Deux fois plus vite');
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 180, 16: 100 } })))).toBe('Deux fois plus vite');
    // Un peu plus vite : de 1,1 à 1,8.
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 192, 16: 160 } })))).toBe('Un peu plus vite');
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 110, 16: 100 } })))).toBe('Un peu plus vite');
    // Pas plus vite : sous 1,1, plus lent compris.
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 105, 16: 100 } })))).toBe('Pas plus vite');
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 100, 16: 130 } })))).toBe('Pas plus vite');
    expect(choixFils(processeur({ [T]: { 1: 1000, 8: 200, 16: 100 } })).map((c) => c.texte)).toEqual([
      'Deux fois plus vite',
      'Un peu plus vite',
      'Pas plus vite',
    ]);
    expect([verdictFils(2), verdictFils(1.8), verdictFils(1.79), verdictFils(1.1), verdictFils(1.09)]).toEqual([
      'deux-fois',
      'deux-fois',
      'un-peu',
      'un-peu',
      'pas',
    ]);
  });

  it('la question nomme les fils du fichier, et la garde refuse un processeur sans fils en plus', () => {
    const m = processeur({ [T]: { 1: 1000, 8: 192, 16: 160 } });
    // Des espaces insécables autour du × : « 4 096 × 4 096 » ne se coupe pas.
    expect(questionFils(m)).toBe(
      `Avec 16 fils au lieu de 8, le produit 4${FINE}096${INSECABLE}×${INSECABLE}4${FINE}096 va-t-il deux fois plus vite${FINE}?`,
    );
    expect(rapportFils(m)).toBe(192 / 160);
    expect(() => choixFils(processeur({ [T]: { 1: 1000, 8: 200 } }, 8, 8))).toThrow(/fils_par_defaut/);
    // Une mesure absente est une erreur qui dit quoi faire.
    expect(() => choixFils(processeur({ 1024: { 1: 10, 8: 2, 16: 2 } }))).toThrow(/4096.*python -m tenseurs mesurer/);
  });

  it('l’explication suit le verdict : la comparaison entière, et les cœurs seulement quand les fils en plus aident peu', () => {
    const coeurs = `Un fil n’est pas un cœur${FINE}: un cœur du processeur peut faire tourner deux fils à la fois, qui se partagent alors ses unités de calcul.`;
    const avant = (tous: string, defaut: string) => `Avec 16 fils, le produit prend ${tous} ms, contre ${defaut} ms avec 8${FINE}: `;
    // Deux fois plus vite : pas de phrase sur les cœurs, qui la contredirait.
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 200, 16: 100 } }))).toBe(
      `${avant('100', '200')}2,00 fois plus vite. Ici, les fils en plus calculent presque autant que les premiers.`,
    );
    // Un peu plus vite (les chronos provisoires de ce PC : 192 et 160 ms).
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 192.3, 16: 160 } }))).toBe(
      `${avant('160', '192')}1,20 fois plus vite. Les fils en plus aident, mais bien moins que les premiers. ${coeurs}`,
    );
    // Pas plus vite, mais un peu quand même.
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 105, 16: 100 } }))).toBe(
      `${avant('100', '105')}1,05 fois plus vite. Ici, les fils en plus n’aident presque pas. ${coeurs}`,
    );
    // Plus lent : la comparaison se retourne (1 / rapport), jamais « 0,77 fois plus vite ».
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 100, 16: 130 } }))).toBe(
      `${avant('130', '100')}1,30 fois plus lent. Ici, les fils en plus ralentissent même le calcul. ${coeurs}`,
    );
    // Égaux à 1 % près : ni plus vite, ni plus lent.
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 100, 16: 100.4 } }))).toBe(
      `${avant('100', '100')}pas plus vite. Ici, les fils en plus n’aident presque pas. ${coeurs}`,
    );
  });

  it('le gain du réglage par défaut sur un seul fil est gardé : sous 1,5, la page ne dirait plus vrai', () => {
    expect(SEUIL_PARALLELE).toBe(1.5);
    expect(gainDuReglageParDefaut(processeur({ [T]: { 1: 1066, 8: 192.3, 16: 160 } }))).toBe(1066 / 192.3);
    expect(gainDuReglageParDefaut(processeur({ [T]: { 1: 150, 8: 100, 16: 90 } }))).toBe(1.5);
    expect(() => gainDuReglageParDefaut(processeur({ [T]: { 1: 140, 8: 100, 16: 90 } }))).toThrow(/réglage par défaut.*1,4/);
    // Un réglage par défaut d'un seul fil n'a rien à montrer : la garde le refuse aussi.
    expect(() => gainDuReglageParDefaut(processeur({ [T]: { 1: 100, 16: 50 } }, 1, 16))).toThrow(/réglage par défaut/);
  });

  it('le fichier du processeur donne un verdict, et un seul choix juste', () => {
    const m = lireMesures('processeur', RACINE)!;
    expect(m).not.toBeNull();
    const r = chrono(m, T, m.fils_par_defaut) / chrono(m, T, m.fils_max);
    expect(rapportFils(m)).toBe(r);
    const attendu = r >= 1.8 ? 'Deux fois plus vite' : r >= 1.1 ? 'Un peu plus vite' : 'Pas plus vite';
    expect(juste(choixFils(m))).toBe(attendu);
  });
});

describe('pari « petite matrice » (à la porte, avec la carte)', () => {
  const cpu = processeur({ [TAILLE_PETITE]: { 1: 0.0077, 8: 0.0074, 16: 0.0301 } });

  it('le meilleur chrono du processeur, tous fils confondus', () => {
    expect(TAILLE_PETITE).toBe(64);
    expect(meilleurChrono(cpu, TAILLE_PETITE)).toBe(0.0074);
    expect(meilleurChrono(carte({ 64: 0.02 }), TAILLE_PETITE)).toBe(0.02);
  });

  it('le processeur, la carte, ou autant l’un que l’autre (écart sous 10 %)', () => {
    expect(choixPetiteMatrice(cpu, carte({ 64: 0.02 })).map((c) => c.texte)).toEqual([
      'Le processeur',
      'La carte',
      "Autant l'un que l'autre",
    ]);
    expect(juste(choixPetiteMatrice(cpu, carte({ 64: 0.02 })))).toBe('Le processeur');
    expect(juste(choixPetiteMatrice(cpu, carte({ 64: 0.005 })))).toBe('La carte');
    expect(juste(choixPetiteMatrice(cpu, carte({ 64: 0.007 })))).toBe("Autant l'un que l'autre");
    expect(juste(choixPetiteMatrice(cpu, carte({ 64: 0.0081 })))).toBe("Autant l'un que l'autre");
    expect(juste(choixPetiteMatrice(cpu, carte({ 64: 0.0082 })))).toBe('Le processeur');
  });

  it('les appareils doivent être dans le bon ordre', () => {
    expect(() => choixPetiteMatrice(carte({ 64: 0.02 }), cpu)).toThrow(/processeur.*carte/);
  });
});

describe('les chronos écrits par la page', () => {
  it('trois chiffres significatifs, à la française, jamais en « e »', () => {
    expect(ecrireMillisecondes(0.0077)).toBe('0,00770');
    expect(ecrireMillisecondes(0.0301)).toBe('0,0301');
    expect(ecrireMillisecondes(3.517)).toBe('3,52');
    expect(ecrireMillisecondes(17.48)).toBe('17,5');
    expect(ecrireMillisecondes(135.1)).toBe('135');
    expect(ecrireMillisecondes(1066)).toBe(`1${FINE}070`);
    expect(ecrireMillisecondes(9.996)).toBe('10,0');
    expect(ecrireMillisecondes(0.00000123)).toBe('0,00000123');
    for (const x of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) expect(() => ecrireMillisecondes(x)).toThrow();
  });

  it('les colonnes de fils : 1, le réglage par défaut et tous les fils, sans doublon', () => {
    expect(filsDesColonnes(processeur({ 64: { 1: 1 } }, 8, 16))).toEqual([1, 8, 16]);
    expect(filsDesColonnes(processeur({ 64: { 1: 1 } }, 1, 4))).toEqual([1, 4]);
    expect(filsDesColonnes(processeur({ 64: { 1: 1 } }, 4, 4))).toEqual([1, 4]);
  });

  it('les lignes du tableau : une par taille, le processeur par fils, puis la carte ou rien', () => {
    const m = lireMesures('processeur', RACINE)!;
    const lignes = lignesChronos(m, null);
    const taillesDuFichier = [...new Set(m.mesures.map((x) => x.taille))];
    expect(lignes.map((l) => l.taille)).toEqual(taillesDuFichier);
    for (const l of lignes) {
      expect(l.processeur).toEqual(filsDesColonnes(m).map((f) => ecrireMillisecondes(chrono(m, l.taille, f))));
      expect(l.carte).toBeNull();
    }
    const avecCarte = lignesChronos(m, carte({ 64: 0.02, 4096: 2 }));
    expect(avecCarte.map((l) => l.carte)).toEqual(taillesDuFichier.map((t) => (t === 64 ? '0,0200' : t === 4096 ? '2,00' : '—')));
  });
});
