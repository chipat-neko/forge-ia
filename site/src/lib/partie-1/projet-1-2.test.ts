// projet-1-2.ts lit les fichiers du projet 1.2 que le chapitre montre : les exemples, et les
// mesures de MESURES_PARTIE_1, à l'identique.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { MESURES_PARTIE_1 } from './mesures';
import { lireJsonl } from './paris-1-2';
import { APERCU, CORPUS_PRINCIPAL, EXEMPLES_CODE, EXEMPLES_WEB } from './projet-1-2';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const lire = (chemin: string): string => readFileSync(`../${chemin}`, 'utf8');

describe('les fichiers du projet 1.2 lus par le chapitre', () => {
  it('les exemples', () => {
    expect(EXEMPLES_WEB).toStrictEqual(lireJsonl(lire('projets/1.2-donnees/exemples/web.jsonl')));
    expect(EXEMPLES_CODE).toStrictEqual(lireJsonl(lire('projets/1.2-donnees/exemples/code.jsonl')));
  });

  it('l’aperçu et le corpus principal sont les fichiers de MESURES_PARTIE_1', () => {
    expect(APERCU).toStrictEqual(JSON.parse(lire(MESURES_PARTIE_1.apercu)));
    expect(CORPUS_PRINCIPAL).toStrictEqual(JSON.parse(lire(MESURES_PARTIE_1.corpusPrincipal)));
  });
});
