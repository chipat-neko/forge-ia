// Les chronos du projet 0.4, lus dans projets/0.4-tenseurs/mesures/*.json.
//
// Le processeur est mesuré pendant les tâches (mesures provisoires, refaites à
// la porte, machine au repos). La carte n'est mesurée qu'à la porte : tant que
// mesures/rtx-5070-ti.json manque, lireMesures('rtx-5070-ti', …) vaut null, et
// le chapitre affiche « à mesurer ». Quand il existe, son format est vérifié.

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
    ];
    for (const [nom, valeur] of cas) {
      expect(() => verifierMesures(valeur, 'mesures/essai.json'), nom).toThrow(/^mesures\/essai\.json\u202F: /);
    }
    expect(verifierMesures(carte, 'mesures/essai.json')).toStrictEqual(carte);
  });
});
