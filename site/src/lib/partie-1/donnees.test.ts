// Les valeurs de donnees.ts sont celles de forge.
//
// Le test lit le texte de projets/forge/forge/donnees/melange.py et sources.py, sans les
// importer (c'est du Python), et vérifie que le mélange, la part de validation et les
// licences permissives sont les mêmes. Si forge change, ce test échoue tant que donnees.ts
// ne suit pas.

import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { LICENCES_PERMISSIVES, MELANGE, NOMS_DES_SOURCES, PART_VALIDATION } from './donnees';
import { MESURES_PARTIE_1 } from './mesures';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const melange = readFileSync('../projets/forge/forge/donnees/melange.py', 'utf8');
const sources = readFileSync('../projets/forge/forge/donnees/sources.py', 'utf8');

describe('le mélange', () => {
  it('est MELANGE_PAR_DEFAUT de forge, dans le même ordre', () => {
    const corps = /MELANGE_PAR_DEFAUT: dict\[str, float\] = \{([^}]*)\}/.exec(melange)?.[1];
    expect(corps, 'MELANGE_PAR_DEFAUT introuvable dans melange.py').toBeDefined();
    const lu = [...(corps as string).matchAll(/"(\w+)":\s*([0-9.]+)/g)].map(([, nom, part]) => [nom, Number(part)]);
    expect(Object.entries(MELANGE)).toStrictEqual(lu);
    expect(NOMS_DES_SOURCES).toStrictEqual(lu.map(([nom]) => nom));
  });

  it('fait 1 en tout', () => {
    let total = 0;
    for (const part of Object.values(MELANGE)) total += part;
    expect(total).toBeCloseTo(1, 12);
  });

  it('a pour sources celles de SOURCES (sources.py)', () => {
    const noms = [...sources.matchAll(/^ {4}"(\w+)": Source\(/gm)].map(([, nom]) => nom);
    expect(noms).toStrictEqual([...NOMS_DES_SOURCES]);
  });
});

describe('la part de validation', () => {
  it('est le défaut de est_validation (melange.py)', () => {
    const defaut = /def est_validation\(empreinte: str, part: float = ([0-9.]+)\)/.exec(melange)?.[1];
    expect(defaut, 'est_validation introuvable dans melange.py').toBeDefined();
    expect(PART_VALIDATION).toBe(Number(defaut));
  });

  it('fait un document sur 200', () => {
    expect(1 / PART_VALIDATION).toBeCloseTo(200, 9);
  });
});

describe('les licences permissives', () => {
  it('sont LICENCES_PERMISSIVES de sources.py, dans le même ordre', () => {
    const corps = /LICENCES_PERMISSIVES = frozenset\(\s*\{([^}]*)\}/.exec(sources)?.[1];
    expect(corps, 'LICENCES_PERMISSIVES introuvable dans sources.py').toBeDefined();
    const lues = [...(corps as string).matchAll(/"([^"]+)"/g)].map(([, nom]) => nom);
    expect(lues.length).toBe(7);
    expect([...LICENCES_PERMISSIVES]).toStrictEqual(lues);
  });
});

describe('les fichiers de mesures', () => {
  it('sont sous un projet de la Partie 1, et existent', () => {
    for (const chemin of Object.values(MESURES_PARTIE_1)) {
      expect(chemin, chemin).toMatch(/^projets\/1\.\d-[a-z-]+\//);
      expect(existsSync(`../${chemin}`), chemin).toBe(true);
    }
  });
});
