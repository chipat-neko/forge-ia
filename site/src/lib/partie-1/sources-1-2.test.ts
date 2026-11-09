// Les chiffres de labo du chapitre 1.2 : chaque source a son adresse et sa date, et les
// tailles de docs/donnees.md sont celles de sources-1-2.ts.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { NOMS_DES_SOURCES } from './donnees';
import { enGio, OCTETS_PAR_GIO, PART_PYTHON_PERMISSIF, SOURCES_1_2, TAILLES_DES_SOURCES } from './sources-1-2';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
// La documentation écrit « 4,1 % » avec une espace fine insécable : on la compare à une espace ordinaire.
const docs = readFileSync('../docs/donnees.md', 'utf8').replace(/[\u202F\u00A0]/g, ' ');
/** Un nombre à la française, sans espace insécable ni espace fine : « 539 897 427 722 ». */
const milliers = (n: number): string => n.toLocaleString('fr-FR').replace(/[\u202F\u00A0]/g, ' ');
const virgule = (x: number, decimales: number): string => x.toFixed(decimales).replace('.', ',');

describe('les sources du chapitre 1.2', () => {
  const toutes = [
    ...SOURCES_1_2.tailles,
    ...SOURCES_1_2.licences,
    ...Object.values(TAILLES_DES_SOURCES).map((t) => t.page),
    PART_PYTHON_PERMISSIF.source,
  ];

  it('ont chacune un titre, une adresse https et une date AAAA-MM-JJ', () => {
    expect(toutes.length).toBeGreaterThan(8);
    for (const s of toutes) {
      expect(s.titre.length, s.url).toBeGreaterThan(5);
      expect(s.url, s.titre).toMatch(/^https:\/\/\S+$/);
      expect(s.verifieLe, s.titre).toMatch(/^2026-\d{2}-\d{2}$/);
    }
  });

  it('couvrent les trois sources du mélange, dans l’ordre', () => {
    expect(Object.keys(TAILLES_DES_SOURCES)).toStrictEqual([...NOMS_DES_SOURCES]);
  });
});

describe('les tailles de docs/donnees.md', () => {
  it('disent, pour chaque source, les fichiers et les octets de sources-1-2.ts', () => {
    for (const [nom, t] of Object.entries(TAILLES_DES_SOURCES)) {
      expect(docs, `${nom} : octets`).toContain(milliers(t.octets));
      expect(docs, `${nom} : fichiers`).toContain(`${t.fichiers} fichiers`);
    }
  });

  it('écrivent chaque taille en Gio, arrondie à une décimale (deux pour Wikipédia)', () => {
    expect(docs).toContain(`${virgule(enGio(TAILLES_DES_SOURCES.web_fr.octets), 1)} Gio`);
    expect(docs).toContain(`${virgule(enGio(TAILLES_DES_SOURCES.wikipedia_fr.octets), 2)} Gio`);
    expect(docs).toContain(`${virgule(enGio(TAILLES_DES_SOURCES.code_python.octets), 1)} Gio`);
  });

  it('ne gardent plus d’anciennes tailles mal écrites', () => {
    expect(docs).not.toContain('4,85 Go');
    expect(docs).not.toContain('environ 314 Go');
    expect(docs).not.toContain('environ 4,61 Go');
  });

  it('disent la part du Python permissif mesurée', () => {
    expect(docs).toContain(`${virgule(100 * PART_PYTHON_PERMISSIF.fichiers, 1)} % des fichiers`);
    expect(docs).toContain(`${virgule(100 * PART_PYTHON_PERMISSIF.octets, 1)} % des`);
  });
});

describe('le Gio', () => {
  it('vaut 2³⁰ octets', () => {
    expect(OCTETS_PAR_GIO).toBe(2 ** 30);
    expect(enGio(2 ** 31)).toBe(2);
  });
});
