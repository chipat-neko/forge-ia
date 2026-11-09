// projet-1-4.ts lit la section residus des attendus du projet 1.4, à l'identique.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { RESIDUS } from './projet-1-4';

describe('les fichiers du projet 1.4 lus par le chapitre', () => {
  it('la section residus des attendus', () => {
    // Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
    const attendus = JSON.parse(readFileSync('../projets/1.4-transformer/tests/attendus.json', 'utf8')) as { residus: unknown };
    expect(RESIDUS).toStrictEqual(attendus.residus);
  });
});
