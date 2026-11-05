// Les chronos du projet 0.4, lus dans projets/0.4-tenseurs/mesures/*.json.
//
// Le processeur et la carte ont été mesurés à la porte de la Partie 0, carte au
// repos. Si mesures/rtx-5070-ti.json manque, lireMesures('rtx-5070-ti', …) vaut
// null : TableauChronos afficherait « à mesurer », mais le chapitre 0.4 arrête
// sa construction avant (le pari « petite » et les phrases de l'étape 6 ont
// besoin de la carte). Quand il existe, son format est vérifié.

import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';
import { FICHIERS_MESURES, lireMesures, verifierMesures, type MesuresChrono } from './mesures';

// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const RACINE = resolve('..');
const TAILLES = [64, 256, 1024, 2048, 4096];

/** Ce que les deux fichiers ont en commun. */
function verifierCommun(m: MesuresChrono): void {
  expect(m.version).toBe(1);
  expect(m.releve_le).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(m.nom.trim()).not.toBe('');
  expect(m.torch).not.toBe('');
  expect(Number.isInteger(m.fils_par_defaut) && Number.isInteger(m.fils_max)).toBe(true);
  expect(m.fils_par_defaut).toBeLessThanOrEqual(m.fils_max);
  expect(m.mesures.length).toBeGreaterThan(0);
  for (const x of m.mesures) {
    expect(Object.keys(x)).toStrictEqual(['taille', 'fils', 'millisecondes']);
    expect(Number.isFinite(x.millisecondes) && x.millisecondes > 0).toBe(true);
  }
}

describe('lireMesures : les fichiers du dépôt', () => {
  it('processeur : le format de mesures/processeur.json', () => {
    const m = lireMesures('processeur', RACINE);
    expect(m).not.toBeNull();
    if (m === null) return;
    verifierCommun(m);
    expect(Object.keys(m)).toStrictEqual([
      'version',
      'releve_le',
      'appareil',
      'nom',
      'torch',
      'fils_par_defaut',
      'fils_max',
      'mesures',
      'transfert_ms',
    ]);
    expect(m.appareil).toBe('cpu');
    expect(m.transfert_ms).toBeNull();
    expect([...new Set(m.mesures.map((x) => x.taille))]).toStrictEqual(TAILLES);
    // Pour chaque taille : 1 fil, le réglage par défaut de PyTorch et tous les fils du processeur.
    const fils = [...new Set([1, m.fils_par_defaut, m.fils_max])];
    for (const taille of TAILLES) {
      expect(m.mesures.filter((x) => x.taille === taille).map((x) => x.fils), `${taille}`).toStrictEqual(fils);
    }
  });

  it('rtx-5070-ti : null si et seulement si le fichier manque, sinon le format de la carte', () => {
    const present = existsSync(join(RACINE, FICHIERS_MESURES['rtx-5070-ti']));
    const m = lireMesures('rtx-5070-ti', RACINE);
    if (!present) {
      expect(m).toBeNull();
      return;
    }
    expect(m).not.toBeNull();
    if (m === null) return;
    verifierCommun(m);
    expect(m.appareil).toBe('cuda');
    expect(m.mesures.every((x) => x.fils === null)).toBe(true);
    expect(typeof m.transfert_ms === 'object' && m.transfert_ms !== null && !Array.isArray(m.transfert_ms)).toBe(true);
    for (const ms of Object.values(m.transfert_ms ?? {})) {
      expect(Number.isFinite(ms) && ms > 0).toBe(true);
    }
  });

  it('la racine du dépôt se donne en chemin ou en URL (comme root d’astro:config/server)', () => {
    const parUrl = lireMesures('processeur', pathToFileURL(`${RACINE}/`));
    expect(parUrl).toStrictEqual(lireMesures('processeur', RACINE));
    // Une chaîne file:///… est une URL, pas un chemin.
    const parTexte = lireMesures('processeur', pathToFileURL(`${RACINE}/`).href);
    expect(parTexte).toStrictEqual(lireMesures('processeur', RACINE));
  });

  it('une racine fausse est une erreur, pas « à mesurer »', () => {
    // Le root d'Astro est site/ : passé sans '../', il n'a pas de dossier projets/0.4-tenseurs.
    for (const fausse of [resolve('.'), pathToFileURL(`${resolve('.')}/`)]) {
      expect(() => lireMesures('rtx-5070-ti', fausse)).toThrow(/n’a pas de dossier projets\/0\.4-tenseurs/);
      expect(() => lireMesures('processeur', fausse)).toThrow(/new URL\('\.\.\/', root\)/);
    }
  });
});

describe('lireMesures : un dépôt factice', () => {
  const racine = mkdtempSync(join(tmpdir(), 'forge-ia-mesures-'));
  const dossier = join(racine, 'projets', '0.4-tenseurs', 'mesures');
  mkdirSync(dossier, { recursive: true });
  afterAll(() => rmSync(racine, { recursive: true, force: true }));

  const carte = {
    version: 1,
    releve_le: '2026-11-10',
    appareil: 'cuda',
    nom: 'NVIDIA GeForce RTX 5070 Ti',
    torch: '2.15.0+cu132',
    fils_par_defaut: 8,
    fils_max: 16,
    mesures: [{ taille: 64, fils: null, millisecondes: 0.01 }],
    transfert_ms: { '64': 0.02 },
  };

  it('un fichier absent vaut null', () => {
    expect(lireMesures('processeur', racine)).toBeNull();
    expect(lireMesures('rtx-5070-ti', racine)).toBeNull();
  });

  it('un fichier de carte bien formé se lit tel quel', () => {
    writeFileSync(join(dossier, 'rtx-5070-ti.json'), JSON.stringify(carte));
    expect(lireMesures('rtx-5070-ti', racine)).toStrictEqual(carte);
  });

  it('un fichier mal formé arrête la construction, avec ce qu’il faut faire', () => {
    writeFileSync(join(dossier, 'processeur.json'), '{"version": 1,');
    expect(() => lireMesures('processeur', racine)).toThrow(/processeur\.json.*JSON.*python -m tenseurs mesurer/s);
    writeFileSync(join(dossier, 'processeur.json'), JSON.stringify({ ...carte, version: 2 }));
    expect(() => lireMesures('processeur', racine)).toThrow(/version/);
  });

  it('verifierMesures refuse chaque écart au format', () => {
    const cas: [string, unknown][] = [
      ['un tableau', []],
      ['version', { ...carte, version: 2 }],
      ['releve_le', { ...carte, releve_le: '10/11/2026' }],
      ['appareil', { ...carte, appareil: 'mps' }],
      ['nom', { ...carte, nom: '' }],
      ['fils_max', { ...carte, fils_max: 0 }],
      ['mesures vides', { ...carte, mesures: [] }],
      ['millisecondes', { ...carte, mesures: [{ taille: 64, fils: null, millisecondes: 0 }] }],
      ['fils sur la carte', { ...carte, mesures: [{ taille: 64, fils: 8, millisecondes: 1 }] }],
      ['fils sur le processeur', { ...carte, appareil: 'cpu', transfert_ms: null }],
      ['transfert sur le processeur', { ...carte, appareil: 'cpu', mesures: [{ taille: 64, fils: 1, millisecondes: 1 }] }],
      ['transfert absent sur la carte', { ...carte, transfert_ms: null }],
      ['transfert en tableau', { ...carte, transfert_ms: [0.02] }],
      ['fils_par_defaut au-dessus de fils_max', { ...carte, fils_par_defaut: 32, fils_max: 16 }],
      [
        'tailles décroissantes',
        {
          ...carte,
          mesures: [
            { taille: 128, fils: null, millisecondes: 0.02 },
            { taille: 64, fils: null, millisecondes: 0.01 },
          ],
          transfert_ms: { '64': 0.02, '128': 0.03 },
        },
      ],
      [
        'taille en double',
        {
          ...carte,
          mesures: [
            { taille: 64, fils: null, millisecondes: 0.01 },
            { taille: 64, fils: null, millisecondes: 0.01 },
          ],
        },
      ],
      [
        'taille qui revient après une autre',
        {
          ...carte,
          appareil: 'cpu',
          transfert_ms: null,
          mesures: [
            { taille: 64, fils: 1, millisecondes: 0.01 },
            { taille: 128, fils: 1, millisecondes: 0.02 },
            { taille: 64, fils: 8, millisecondes: 0.01 },
          ],
        },
      ],
      ['transfert d’une autre taille', { ...carte, transfert_ms: { '128': 0.02 } }],
      ['transfert vide', { ...carte, transfert_ms: {} }],
      ['transfert en trop', { ...carte, transfert_ms: { '64': 0.02, '128': 0.03 } }],
    ];
    for (const [nom, valeur] of cas) {
      expect(() => verifierMesures(valeur, 'mesures/essai.json'), nom).toThrow(/^mesures\/essai\.json\u202F: /);
    }
    expect(verifierMesures(carte, 'mesures/essai.json')).toStrictEqual(carte);
  });

  it('verifierMesures accepte plusieurs fils par taille sur le processeur, rangés par taille', () => {
    const processeur = {
      ...carte,
      appareil: 'cpu',
      nom: 'AMD Ryzen 7 9800X3D 8-Core Processor',
      torch: '2.15.0+cpu',
      transfert_ms: null,
      mesures: [
        { taille: 64, fils: 1, millisecondes: 0.01 },
        { taille: 64, fils: 8, millisecondes: 0.01 },
        { taille: 128, fils: 1, millisecondes: 0.02 },
        { taille: 128, fils: 8, millisecondes: 0.01 },
      ],
    };
    expect(verifierMesures(processeur, 'mesures/essai.json')).toStrictEqual(processeur);
    const deuxTailles = {
      ...carte,
      mesures: [
        { taille: 64, fils: null, millisecondes: 0.01 },
        { taille: 128, fils: null, millisecondes: 0.02 },
      ],
      transfert_ms: { '128': 0.03, '64': 0.02 },
    };
    expect(verifierMesures(deuxTailles, 'mesures/essai.json')).toStrictEqual(deuxTailles);
  });
});
