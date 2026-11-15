// Ce qui annonce les chapitres hors du site : les README du dépôt ne disent pas « à venir » un
// chapitre paru. À la parution de 1.5 et 1.6, le README racine et ceux de leurs projets disaient
// encore qu'ils paraîtraient (revue finale du plan 5, I1) ; l'étape 3 de « Parution d'un
// chapitre », dans le README, demande de les relire, et ce test le vérifie.
//
// Les chapitres parus sont ceux qui ont un fichier dans src/content/chapitres/, comme pour
// chapitresParus() (qui passe par astro:content, que Vitest ne charge pas).

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const PARUS = readdirSync('src/content/chapitres')
  .filter((f) => /^\d+-\d+\.mdx$/.test(f))
  .map((f) => f.replace(/\.mdx$/, '').replace('-', '.'));
/** Ce que dit un texte d'un chapitre qui n'a pas encore paru. */
const A_VENIR = /pas encore en ligne|n['’]existen?t? pas encore|paraîtr(?:a|ont)\b/;

/** Les paragraphes d'un texte Markdown (séparés par une ligne vide), sur une seule ligne chacun. */
function paragraphes(texte: string): string[] {
  return texte
    .replace(/\r\n?/g, '\n')
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\s+/g, ' ').trim());
}

/** Un numéro de chapitre écrit tel quel dans un texte : « 1.5 », pas « 11.5 » ni « 1.50 ». */
function cite(texte: string, numero: string): boolean {
  return new RegExp(`(?<![\\d.])${numero.replace('.', '\\.')}(?![\\d])`).test(texte);
}

describe('les README et les chapitres parus', () => {
  it('les chapitres parus sont lus sur le disque', () => {
    expect(PARUS).toContain('1.5');
    expect(PARUS).toContain('1.6');
  });

  it('le README du projet d’un chapitre paru ne le dit pas à venir', () => {
    const projets = readdirSync(`${RACINE}/projets`);
    let lus = 0;
    for (const numero of PARUS) {
      for (const projet of projets.filter((p) => p.startsWith(`${numero}-`))) {
        const chemin = `${RACINE}/projets/${projet}/README.md`;
        if (!existsSync(chemin)) continue;
        lus += 1;
        const fautifs = paragraphes(readFileSync(chemin, 'utf8')).filter((p) => A_VENIR.test(p));
        expect(fautifs, `projets/${projet}/README.md : le chapitre ${numero} a paru, relis ces phrases`).toEqual([]);
      }
    }
    expect(lus).toBeGreaterThan(0);
  });

  it('le README racine ne dit à venir aucun chapitre paru', () => {
    const fautifs = paragraphes(readFileSync(`${RACINE}/README.md`, 'utf8')).filter(
      (p) => A_VENIR.test(p) && PARUS.some((numero) => cite(p, numero)),
    );
    expect(fautifs, 'README.md : ces phrases disent à venir un chapitre paru, relis-les').toEqual([]);
  });

  it('la règle reconnaît l’ancienne phrase du README racine, et pas la procédure de parution', () => {
    const ancienne =
      'Les chapitres 1.5 et 1.6 paraîtront après la fin de l’entraînement de « ton IA » : leurs projets sont prêts, leurs adresses n’existent pas encore.';
    expect(A_VENIR.test(ancienne) && cite(ancienne, '1.5')).toBe(true);
    expect(A_VENIR.test('Ce chapitre n’est pas encore en ligne : il paraîtra après.')).toBe(true);
    expect(A_VENIR.test('Pour faire paraître un chapitre :')).toBe(false);
    expect(cite('les chapitres 11.5 et 1.50', '1.5')).toBe(false);
  });
});
