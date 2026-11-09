// Les chiffres de labo du chapitre 1.2 : chaque source a son adresse et sa date, et les
// tailles de docs/donnees.md sont celles de sources-1-2.ts.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { NOMS_DES_SOURCES } from './donnees';
import {
  enGio,
  FICHES_DES_SOURCES,
  FINEWEB_2,
  LICENCES,
  LICENCES_DE_GITHUB_CODE,
  LLAMA_3,
  OCTETS_PAR_GIO,
  PART_PYTHON_PERMISSIF,
  REGLEMENT_IA,
  SOURCES_1_2,
  TAILLES_DES_SOURCES,
  WIKIPEDIA_EN_4_0,
} from './sources-1-2';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
// La documentation écrit « 4,1 % » avec une espace fine insécable : on la compare à une espace ordinaire.
const docs = readFileSync('../docs/donnees.md', 'utf8').replace(/[\u202F\u00A0]/g, ' ');
/** Un nombre à la française, sans espace insécable ni espace fine : « 539 897 427 722 ». */
const milliers = (n: number): string => n.toLocaleString('fr-FR').replace(/[\u202F\u00A0]/g, ' ');
const virgule = (x: number, decimales: number): string => x.toFixed(decimales).replace('.', ',');
const sourcesPy = readFileSync('../projets/forge/forge/donnees/sources.py', 'utf8');

describe('les sources du chapitre 1.2', () => {
  const toutes = [
    ...SOURCES_1_2.tailles,
    ...SOURCES_1_2.licences,
    ...SOURCES_1_2.fiches,
    ...SOURCES_1_2.labo,
    ...Object.values(LICENCES).map((l) => l.source),
    WIKIPEDIA_EN_4_0.source,
    LICENCES_DE_GITHUB_CODE.source,
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

describe('les fiches des sources', () => {
  /** Le bloc Source(...) d'une source dans sources.py, lu en texte. */
  const bloc = (nom: string): string => {
    const debut = sourcesPy.indexOf(`"${nom}": Source(`);
    expect(debut, nom).toBeGreaterThan(-1);
    return sourcesPy.slice(debut, sourcesPy.indexOf('\n    ),', debut));
  };
  /** La valeur d'un champ du bloc : une chaîne, ou null pour None. */
  const champ = (texte: string, nom: string): string | null => {
    const m = new RegExp(`${nom}=("([^"]*)"|None)`).exec(texte);
    expect(m, nom).not.toBeNull();
    return m![2] ?? null;
  };

  it('ont le dépôt, le dossier ou la configuration, et la première licence de forge.donnees.sources', () => {
    expect(Object.keys(FICHES_DES_SOURCES)).toStrictEqual([...NOMS_DES_SOURCES]);
    for (const [nom, fiche] of Object.entries(FICHES_DES_SOURCES)) {
      const b = bloc(nom);
      expect(fiche.depot, nom).toBe(champ(b, 'depot'));
      expect(fiche.dossier, nom).toBe(champ(b, 'dossier_donnees'));
      expect(fiche.configuration, nom).toBe(champ(b, 'configuration'));
      expect(fiche.licences[0].source.url, nom).toBe(champ(b, 'url_licence'));
      expect(fiche.api.url, nom).toBe(`https://huggingface.co/api/datasets/${fiche.depot}`);
      expect(fiche.libre, nom).toBe(true);
    }
  });

  it('nomment les licences de docs/donnees.md, avec les mêmes liens', () => {
    for (const l of [LICENCES.odcBy, LICENCES.ccBySa3, LICENCES.apache]) {
      expect(docs, l.nom).toContain(`[${l.nom}](${l.source.url})`);
    }
  });
});

describe('les chiffres de labo', () => {
  it('Llama 3 : un mélange qui fait 100 %, 15 000 milliards de jetons, des connaissances jusqu’à fin 2023', () => {
    let total = 0;
    for (const part of Object.values(LLAMA_3.melange)) total += part;
    expect(total).toBeCloseTo(1, 12);
    expect(LLAMA_3.jetons).toBe(15e12);
    expect(LLAMA_3.connaissancesJusqua).toBe(2023);
    expect(LLAMA_3.source.url).toBe('https://arxiv.org/abs/2407.21783');
  });

  it('FineWeb-2 : le français est une partie du tout', () => {
    expect(FINEWEB_2.francais.mots).toBeLessThan(FINEWEB_2.total.mots);
    expect(FINEWEB_2.francais.documents).toBeLessThan(FINEWEB_2.total.documents);
  });

  it('le règlement européen : article 53, applicable depuis le 2 août 2025, 2027 pour les modèles déjà sur le marché', () => {
    expect(REGLEMENT_IA.article).toBe(53);
    expect(REGLEMENT_IA.appliqueDepuis).toBe('2025-08-02');
    expect(REGLEMENT_IA.modelesAnterieurs).toBe('2027-08-02');
    expect(REGLEMENT_IA.source.url.startsWith('https://eur-lex.europa.eu/')).toBe(true);
  });

  it('Wikipédia en CC BY-SA 4.0, et les licences de github-code', () => {
    expect(WIKIPEDIA_EN_4_0.annonceLe).toBe('2023-06-29');
    expect(LICENCES_DE_GITHUB_CODE.licences).toBe(15);
  });
});
