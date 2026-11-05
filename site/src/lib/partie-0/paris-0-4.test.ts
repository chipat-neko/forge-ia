// Les paris du chapitre 0.4 : leurs bonnes réponses viennent du jumeau des
// formes (formes.ts) et des mesures (mesures/*.json), jamais écrites à la main.
// Les mesures du processeur et de la carte ont été relevées à la porte, carte au
// repos, et pourront l'être encore : les fonctions qui en tirent un verdict ou
// une phrase sont essayées ici sur de fausses mesures, qui couvrent chaque
// verdict et font tomber chaque garde, puis sur les vrais fichiers.

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
  explicationPetite,
  filsDesColonnes,
  lignesChronos,
  meilleurChrono,
  OCTETS_FLOAT32,
  OCTETS_PAR_MO,
  phraseCarteEtProcesseur,
  phraseFils,
  phraseTransfert,
  gainDuReglageParDefaut,
  SEUIL_A_PEU_PRES,
  SEUIL_OPERATIONS,
  SEUIL_BIEN_PLUS_VITE,
  SEUIL_CENTAINES,
  SEUIL_PARALLELE,
  SEUIL_PRIX_FIXE,
  questionFils,
  questionPetite,
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

/** De fausses mesures de la carte : `ms[taille]` en millisecondes, et la copie vers la carte (1 ms par défaut). */
function carte(ms: Record<number, number>, transfert: Record<number, number> = {}): MesuresChrono {
  return {
    version: 1,
    releve_le: '2026-11-10',
    appareil: 'cuda',
    nom: 'NVIDIA GeForce RTX 5070 Ti',
    torch: '2.15.0+cu132',
    fils_par_defaut: 8,
    fils_max: 16,
    mesures: Object.entries(ms).map(([taille, millisecondes]) => ({ taille: Number(taille), fils: null, millisecondes })),
    transfert_ms: Object.fromEntries(Object.keys(ms).map((t) => [t, transfert[Number(t)] ?? 1])),
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
    // Le verdict suit le rapport arrondi à deux décimales, celui que la page écrit.
    expect([verdictFils(1.796), verdictFils(1.794), verdictFils(1.096), verdictFils(1.094)]).toEqual([
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
    const avant = (tous: string, defaut: string) =>
      `Avec 16 fils, le produit prend ${tous}${INSECABLE}ms, contre ${defaut}${INSECABLE}ms avec 8${FINE}: `;
    // Deux fois plus vite : pas de phrase sur les cœurs, qui la contredirait.
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 200, 16: 100 } }))).toBe(
      `${avant('100', '200')}2,00 fois plus vite. Ici, les fils en plus calculent presque autant que les premiers.`,
    );
    // Un peu plus vite (les chronos de ce PC relevés avant la porte, carte au travail : 192 et 160 ms).
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
    // 179,6 contre 100 : 1,796 s'écrit « 1,80 », le seuil des deux fois. Le verdict suit le nombre écrit,
    // jamais « 1,80 fois plus vite » sous « un peu » (point mis de côté à la tâche 11).
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 179.6, 16: 100 } }))).toBe(
      `${avant('100', '180')}1,80 fois plus vite. Ici, les fils en plus calculent presque autant que les premiers.`,
    );
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 179.6, 16: 100 } })))).toBe('Deux fois plus vite');
    // 109,6 contre 100 : « 1,10 », au seuil d'« un peu ».
    expect(phraseFils(processeur({ [T]: { 1: 1000, 8: 109.96, 16: 100 } }))).toContain('1,10 fois plus vite. Les fils en plus aident');
    expect(juste(choixFils(processeur({ [T]: { 1: 1000, 8: 109.96, 16: 100 } })))).toBe('Un peu plus vite');
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
    const ecrit = Number(r.toFixed(2)); // le rapport tel que la page l'écrit
    const attendu = ecrit >= 1.8 ? 'Deux fois plus vite' : ecrit >= 1.1 ? 'Un peu plus vite' : 'Pas plus vite';
    expect(juste(choixFils(m))).toBe(attendu);
  });
});

describe('pari « petite matrice » : le processeur contre la carte', () => {
  const cpu = processeur({
    [TAILLE_PETITE]: { 1: 0.0077, 8: 0.0074, 16: 0.0301 },
    256: { 1: 0.25, 8: 0.07, 16: 0.09 },
    4096: { 1: 1000, 8: 190, 16: 150 },
  });
  /** Le prix fixe de la carte, dit de la même façon quel que soit le verdict. */
  const PRIX =
    `Sur la carte, chaque produit chronométré a un prix fixe${FINE}: PyTorch doit le lui envoyer, puis le chronomètre attend qu’elle ait fini. ` +
    'Pour un si petit produit, ce prix dépasse le calcul lui-même. ';
  /** La preuve, lue dans les chronos de la carte : la taille suivante, 64 fois plus de calcul. */
  const preuve = (fois: string) =>
    `Le tableau juste en dessous le montre${FINE}: le produit 256${INSECABLE}×${INSECABLE}256 demande 64 fois plus de calcul, ` +
    `et la carte n’y met que ${fois} fois plus de temps.`;

  it('le meilleur chrono du processeur, tous fils confondus', () => {
    expect(TAILLE_PETITE).toBe(64);
    expect(meilleurChrono(cpu, TAILLE_PETITE)).toBe(0.0074);
    expect(meilleurChrono(carte({ 64: 0.02 }), TAILLE_PETITE)).toBe(0.02);
  });

  it('la question nomme la plus petite taille, « 64 × 64 » d’un seul bloc', () => {
    expect(questionPetite()).toBe(`Pour deux matrices 64${INSECABLE}×${INSECABLE}64, qui calcule le plus vite${FINE}?`);
  });

  it('l’explication : les deux chronos, le prix fixe de la carte, et sa preuve à la taille suivante', () => {
    expect(explicationPetite(cpu, carte({ 64: 0.019, 256: 0.0216, 4096: 3.8 }))).toBe(
      `Le processeur${FINE}: 0,00740${INSECABLE}ms au mieux, contre 0,0190${INSECABLE}ms pour la carte. ${PRIX}${preuve('1,14')}`,
    );
    // Autant l'un que l'autre : l'écart (moins de 10 %) est dit, le prix fixe aussi.
    expect(explicationPetite(cpu, carte({ 64: 0.0078, 256: 0.0081, 4096: 3.8 }))).toBe(
      `Autant l’un que l’autre${FINE}: 0,00740${INSECABLE}ms au mieux pour le processeur, 0,00780${INSECABLE}ms pour la carte, ` +
        `moins de 10${FINE}% d’écart. ${PRIX}${preuve('1,04')}`,
    );
    // Une carte aussi rapide, voire plus, à la taille suivante : « pas plus de temps », jamais « 0,95 fois plus ».
    expect(explicationPetite(cpu, carte({ 64: 0.019, 256: 0.018 }))).toContain('et la carte n’y met pas plus de temps.');
  });

  it('l’explication tombe si la carte gagne, ou si la taille suivante ne montre plus le prix fixe', () => {
    // La carte plus rapide : l'acquis « la carte ne gagne pas toujours » ne serait plus montré.
    expect(() => explicationPetite(cpu, carte({ 64: 0.005, 256: 0.006 }))).toThrow(/acquis « petite »/);
    // 1,5 fois plus de temps pour 64 fois plus de calcul : le prix fixe ne dépasse plus forcément le calcul.
    expect(() => explicationPetite(cpu, carte({ 64: 0.02, 256: 0.031 }))).toThrow(/prix fixe/);
    expect(() => explicationPetite(cpu, carte({ 64: 0.02, 256: 0.0299 }))).not.toThrow();
    // Sans taille après 64 sur la carte, pas de preuve.
    expect(() => explicationPetite(cpu, carte({ 64: 0.02 }))).toThrow(/après 64/);
    // Une taille suivante trop proche (80 : 1,95 fois plus d'opérations) ne prouve rien : « au moins 2 fois » ne tiendrait pas.
    expect(() => explicationPetite(cpu, carte({ 64: 0.019, 80: 0.02 }))).toThrow(/8 fois/);
    // 128 en fait 8 fois plus : la garde passe.
    expect(explicationPetite(cpu, carte({ 64: 0.019, 128: 0.02 }))).toContain('le produit 128');
    expect(SEUIL_OPERATIONS).toBe(8);
    expect(SEUIL_PRIX_FIXE).toBe(1.5);
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
    expect(() => explicationPetite(carte({ 64: 0.02, 256: 0.021 }), cpu)).toThrow(/processeur.*carte/);
  });

  it('les vrais fichiers : un choix juste, et une explication qui tient', () => {
    const p = lireMesures('processeur', RACINE)!;
    const c = lireMesures('rtx-5070-ti', RACINE);
    expect(c, 'mesures/rtx-5070-ti.json manque : la carte se mesure à la porte').not.toBeNull();
    const meilleurP = Math.min(...p.mesures.filter((x) => x.taille === 64).map((x) => x.millisecondes));
    const surLaCarte = c!.mesures.find((x) => x.taille === 64)!.millisecondes;
    const autant = Math.max(meilleurP, surLaCarte) / Math.min(meilleurP, surLaCarte) < 1.1;
    expect(juste(choixPetiteMatrice(p, c!))).toBe(autant ? "Autant l'un que l'autre" : meilleurP < surLaCarte ? 'Le processeur' : 'La carte');
    expect(explicationPetite(p, c!)).toContain(`${ecrireMillisecondes(meilleurP)}${INSECABLE}ms`);
    expect(explicationPetite(p, c!)).toContain(`${ecrireMillisecondes(surLaCarte)}${INSECABLE}ms`);
  });
});

describe('ce que montrent les chronos : le processeur, puis la carte', () => {
  /** « 1 024 × 1 024 » : les milliers séparés par une espace fine, le × entre deux insécables. */
  const milliers = (t: number) => String(t).replace(/\B(?=(\d{3})+(?!\d))/g, FINE);
  const T = (t: number) => `${milliers(t)}${INSECABLE}×${INSECABLE}${milliers(t)}`;
  const MESURES_CPU = {
    64: { 1: 0.0078, 8: 0.0058, 16: 0.0194 },
    256: { 1: 0.26, 8: 0.11, 16: 0.071 },
    1024: { 1: 16, 8: 3.5, 16: 3 },
    4096: { 1: 1047, 8: 194, 16: 150 },
  };
  const cpu = processeur(MESURES_CPU);
  const fin = `, elle va des dizaines de fois plus vite que lui, même avec tous ses fils.`;

  it('le plus petit produit au processeur, la carte dès la taille où elle le dépasse, et des dizaines de fois au plus grand', () => {
    expect([SEUIL_BIEN_PLUS_VITE, SEUIL_CENTAINES]).toEqual([20, 100]);
    expect(phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.0216, 1024: 0.0997, 4096: 3.82 }))).toBe(
      `Le tableau le montre${FINE}: pour le plus petit produit, le processeur, au mieux de ses fils, va plus vite que la carte${FINE}; ` +
        `dès ${T(256)}, la carte le dépasse, et pour ${T(4096)}${fin}`,
    );
    // Autant l'un que l'autre au plus petit ; la carte ne dépasse le processeur qu'à 1 024.
    expect(phraseCarteEtProcesseur(cpu, carte({ 64: 0.006, 256: 0.075, 1024: 0.0997, 4096: 3.82 }))).toBe(
      `Le tableau le montre${FINE}: pour le plus petit produit, le processeur, au mieux de ses fils, et la carte vont à peu près aussi vite${FINE}; ` +
        `dès ${T(1024)}, la carte le dépasse, et pour ${T(4096)}${fin}`,
    );
  });

  it('chaque morceau de la phrase a sa garde', () => {
    // La carte gagne dès le plus petit produit.
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.004, 256: 0.02, 1024: 0.1, 4096: 3.8 }))).toThrow(/acquis « petite »/);
    // La carte dépasse le processeur, puis le laisse repasser devant.
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.02, 1024: 4, 4096: 3.8 }))).toThrow(/dès/);
    // La carte ne le dépasse qu'au plus grand produit : « dès » et « pour » nommeraient la même taille.
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.08, 1024: 3.1, 4096: 3.8 }))).toThrow(/plus grand/);
    // Moins de 20 fois, ou 100 fois et plus : « des dizaines de fois » serait faux.
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.02, 1024: 0.1, 4096: 7.6 }))).toThrow(/dizaines/);
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.02, 1024: 0.1, 4096: 7.4 }))).not.toThrow();
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.02, 1024: 0.1, 4096: 1.5 }))).toThrow(/dizaines/);
    // Une taille du processeur absente de la carte.
    expect(() => phraseCarteEtProcesseur(cpu, carte({ 64: 0.019, 256: 0.02, 4096: 3.8 }))).toThrow(/1024/);
    const ordinaire = carte({ 64: 0.019, 256: 0.0216, 1024: 0.0997, 4096: 3.8 });
    // (a) « même avec tous ses fils » : au mieux 39 fois (8 fils), mais 105 fois contre les 16 fils.
    const lents = processeur({ ...MESURES_CPU, 4096: { 1: 1047, 8: 150, 16: 400 } });
    expect(() => phraseCarteEtProcesseur(lents, ordinaire)).toThrow(/tous ses fils/);
    // (a) 39 fois contre les 16 fils, mais seulement 13 fois contre le meilleur réglage (8 fils).
    const rapides = processeur({ ...MESURES_CPU, 4096: { 1: 1047, 8: 50, 16: 150 } });
    expect(() => phraseCarteEtProcesseur(rapides, ordinaire)).toThrow(/au mieux de ses fils/);
    // (b) « le plus petit produit » est celui du pari : un tableau qui commence à 32 ne le dit plus.
    const des32 = processeur({ 32: { 1: 0.001, 8: 0.001, 16: 0.002 }, ...MESURES_CPU });
    expect(() => phraseCarteEtProcesseur(des32, carte({ 32: 0.018, 64: 0.019, 256: 0.0216, 1024: 0.0997, 4096: 3.8 }))).toThrow(
      /plus petit produit/,
    );
  });

  it('les vrais fichiers : la phrase tient, et la carte dépasse le processeur à la taille qu’elle nomme', () => {
    const p = lireMesures('processeur', RACINE)!;
    const c = lireMesures('rtx-5070-ti', RACINE)!;
    const phrase = phraseCarteEtProcesseur(p, c);
    const tailles = [...new Set(p.mesures.map((x) => x.taille))];
    const meilleurP = (t: number) => Math.min(...p.mesures.filter((x) => x.taille === t).map((x) => x.millisecondes));
    const surLaCarte = (t: number) => c.mesures.find((x) => x.taille === t)!.millisecondes;
    const depasse = tailles.find((t) => meilleurP(t) / surLaCarte(t) >= 1.1)!;
    expect(phrase).toContain(`dès ${T(depasse)}, la carte le dépasse`);
    const plusGrand = tailles.at(-1)!;
    expect(meilleurP(plusGrand) / surLaCarte(plusGrand)).toBeGreaterThanOrEqual(20);
  });
});

describe('le prix du transfert vers la carte', () => {
  const debut = `Copier une matrice 4${FINE}096${INSECABLE}×${INSECABLE}4${FINE}096 sur la carte de ce PC prend`;

  it('la copie d’une matrice face à son produit, au plus grand produit : à peu près autant, plus, ou moins', () => {
    expect(SEUIL_A_PEU_PRES).toBe(1.25);
    expect(phraseTransfert(carte({ 64: 0.019, 4096: 3.82 }, { 4096: 3.75 }))).toBe(
      `${debut} 3,75${INSECABLE}ms${FINE}: à peu près autant que de la multiplier par une autre, 3,82${INSECABLE}ms.`,
    );
    expect(phraseTransfert(carte({ 4096: 4 }, { 4096: 5 }))).toBe(`${debut} 5,00${INSECABLE}ms${FINE}: à peu près autant que de la multiplier par une autre, 4,00${INSECABLE}ms.`);
    expect(phraseTransfert(carte({ 4096: 4 }, { 4096: 3.2 }))).toBe(`${debut} 3,20${INSECABLE}ms${FINE}: à peu près autant que de la multiplier par une autre, 4,00${INSECABLE}ms.`);
    expect(phraseTransfert(carte({ 4096: 4 }, { 4096: 5.1 }))).toBe(`${debut} 5,10${INSECABLE}ms${FINE}: plus que de la multiplier par une autre, 4,00${INSECABLE}ms.`);
    expect(phraseTransfert(carte({ 4096: 4 }, { 4096: 3.1 }))).toBe(`${debut} 3,10${INSECABLE}ms${FINE}: moins que de la multiplier par une autre, 4,00${INSECABLE}ms.`);
  });

  it('il faut les mesures de la carte', () => {
    expect(() => phraseTransfert(processeur({ 4096: { 1: 1000, 8: 190, 16: 150 } }))).toThrow(/carte/);
  });

  it('le vrai fichier de la carte', () => {
    const c = lireMesures('rtx-5070-ti', RACINE)!;
    const plusGrand = c.mesures.at(-1)!;
    const phrase = phraseTransfert(c);
    expect(phrase).toContain(`prend ${ecrireMillisecondes(c.transfert_ms![String(plusGrand.taille)])}${INSECABLE}ms`);
    expect(phrase).toContain(`par une autre, ${ecrireMillisecondes(plusGrand.millisecondes)}${INSECABLE}ms.`);
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
