// Les caractères invisibles : aucun U+00A0, U+202F, U+2009, U+200B, U+200C,
// U+200D, U+2060 ni U+FEFF littéral dans les fichiers de code du plan 4 (la
// Partie 0). À l'écran, on ne les distingue pas d'une espace ordinaire, ou on
// ne les voit pas du tout : on écrit donc leur échappement (\u202F dans
// TypeScript, Svelte et Python). Les outils d'écriture des agents ont tendance
// à changer un échappement en caractère littéral : ce test le rattrape.
//
// Les cellules Markdown des notebooks peuvent contenir U+202F (la typographie
// du texte affiché) : seules leurs cellules de code sont lues.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const RACINE = fileURLToPath(new URL('../../../', import.meta.url));

const NOMS: Record<string, string> = {
  '\u00A0': 'espace insécable',
  '\u202F': 'espace fine insécable',
  '\u2009': 'espace fine',
  '\u200B': 'espace sans chasse',
  '\u200C': 'antiliant sans chasse',
  '\u200D': 'liant sans chasse',
  '\u2060': 'gluon de mots',
  '\uFEFF': 'indicateur d’ordre des octets',
};
const INTERDITS = /[\u00A0\u202F\u2009\u200B\u200C\u200D\u2060\uFEFF]/g;

/** Ce qu'il faut écrire à la place du caractère, selon le langage du fichier. */
function echappement(caractere: string, fichier: string): string {
  const point = caractere.codePointAt(0) ?? 0;
  const hex = point.toString(16).toUpperCase().padStart(4, '0');
  if (fichier.endsWith('.mdx')) return `&#${point}; (ou \\u${hex} dans une expression JavaScript)`;
  if (fichier.endsWith('.css')) return `\\${hex}`;
  return `\\u${hex}`;
}

/**
 * Les caractères interdits d'un texte, un message par caractère : où il est
 * (`lieu`, puis la ligne, comptée à partir de 1), lequel, et quoi écrire à la place.
 */
function chercherInvisibles(texte: string, lieu: string, fichier: string): string[] {
  const fautes: string[] = [];
  texte.split('\n').forEach((ligne, i) => {
    for (const [caractere] of ligne.matchAll(INTERDITS)) {
      const hex = (caractere.codePointAt(0) ?? 0).toString(16).toUpperCase().padStart(4, '0');
      fautes.push(
        `${lieu}, ligne ${i + 1} : caractère U+${hex} (${NOMS[caractere]}) ; ` +
          `écris ${echappement(caractere, fichier)} à la place.`,
      );
    }
  });
  return fautes;
}

/** Les fautes d'un fichier du dépôt ; d'un notebook, seulement celles de ses cellules de code. */
function fautesDuFichier(fichier: string): string[] {
  const texte = readFileSync(join(RACINE, fichier), 'utf8');
  if (!fichier.endsWith('.ipynb')) return chercherInvisibles(texte, fichier, fichier);
  const cellules = (JSON.parse(texte) as { cells: { cell_type: string; source: string | string[] }[] }).cells;
  // Une cellule est désignée par son rang dans le notebook, à partir de 1, cellules Markdown comprises.
  return cellules.flatMap((cellule, i) => {
    if (cellule.cell_type !== 'code') return [];
    const source = Array.isArray(cellule.source) ? cellule.source.join('') : cellule.source;
    return chercherInvisibles(source, `${fichier}, cellule ${i + 1}`, fichier);
  });
}

// Le parcours des dossiers ne descend ni dans les dossiers cachés (.venv,
// .pytest_cache, .ipynb_checkpoints…), ni dans node_modules et __pycache__.
const SAUTES = new Set(['node_modules', '__pycache__']);

/** Les fichiers d'un dossier du dépôt, récursivement, en chemins depuis la racine du dépôt. */
function fichiersSous(dossier: string): string[] {
  if (!existsSync(join(RACINE, dossier))) return [];
  return readdirSync(join(RACINE, dossier), { withFileTypes: true }).flatMap((entree) => {
    if (entree.name.startsWith('.') || SAUTES.has(entree.name)) return [];
    const chemin = `${dossier}/${entree.name}`;
    if (entree.isDirectory()) return fichiersSous(chemin);
    return entree.isFile() ? [chemin] : [];
  });
}

/** Les fichiers d'un dossier dont le chemin, relatif à ce dossier, suit le motif. */
function sous(dossier: string, motif = /./): string[] {
  return fichiersSous(dossier).filter((f) => motif.test(f.slice(dossier.length + 1)));
}

/** Les sous-dossiers directs d'un dossier dont le nom suit le motif. */
function dossiers(parent: string, motif: RegExp): string[] {
  if (!existsSync(join(RACINE, parent))) return [];
  return readdirSync(join(RACINE, parent), { withFileTypes: true })
    .filter((e) => e.isDirectory() && motif.test(e.name))
    .map((e) => `${parent}/${e.name}`);
}

// Les fichiers du plan 4 qui existent. Après sa parution, un chapitre passe de
// src/brouillons/chapitres/ à src/content/chapitres/ : il reste lu.
const FICHIERS_SEULS = [
  'site/src/lib/exiger.ts',
  'site/src/lib/brouillons.ts',
  'site/src/lib/brouillons.test.ts',
  'site/src/lib/invisibles.test.ts',
  'site/src/lib/sorties.ts',
  'site/src/lib/sorties.test.ts',
  'site/src/components/gabarit/SortieCommande.astro',
  'site/src/components/gabarit/BlocCommande.astro',
  'site/src/components/interactif/ZoneDefilable.svelte',
  'site/src/styles/commandes.css',
  'site/src/essais/parite-partie-0.mdx',
  'site/src/pages/[partie]/[chapitre].astro',
];

const A_LIRE = [
  ...sous('site/src/brouillons', /\.mdx$/),
  ...sous('site/src/content/chapitres', /^0-[^/]*\.mdx$/),
  ...sous('site/src/lib/partie-0'),
  ...dossiers('site/src/components/chapitres', /^0-/).flatMap((d) => sous(d)),
  ...sous('site/e2e', /^(chapitre-0-[^/]*|brouillons|parution|figures-0-2)\.spec\.ts$/),
  ...dossiers('projets', /^0\./).flatMap((d) => sous(d, /\.py$|^pyproject\.toml$/)),
  ...sous('outils', /^[^/]*\.py$/),
  ...sous('notebooks', /^0\.[^/]*\.ipynb$/),
  ...FICHIERS_SEULS.filter((f) => existsSync(join(RACINE, f))),
];

describe('caractères invisibles', () => {
  it('le contrôle nomme le fichier, la ligne et le caractère, et dit quoi écrire à la place', () => {
    expect(chercherInvisibles('a\nb\u202Fc', 'site/x.ts', 'site/x.ts')).toEqual([
      'site/x.ts, ligne 2 : caractère U+202F (espace fine insécable) ; écris \\u202F à la place.',
    ]);
    expect(chercherInvisibles('x\u00A0= 1', 'n.ipynb, cellule 3', 'n.ipynb')).toEqual([
      'n.ipynb, cellule 3, ligne 1 : caractère U+00A0 (espace insécable) ; écris \\u00A0 à la place.',
    ]);
    expect(chercherInvisibles('a\u2009b\u200Bc', 'f.mdx', 'f.mdx')).toHaveLength(2);
    expect(chercherInvisibles('a\u2060b', 'f.mdx', 'f.mdx')[0]).toContain('écris &#8288;');
    expect(chercherInvisibles('Tout est visible : « oui ».', 'f.ts', 'f.ts')).toEqual([]);
  });

  it('la liste des fichiers à lire contient bien les fichiers de la tâche 2', () => {
    expect(A_LIRE).toContain('site/src/lib/brouillons.ts');
    expect(A_LIRE).toContain('site/src/components/gabarit/SortieCommande.astro');
    expect(A_LIRE.filter((f) => f.includes('/.') || f.includes('node_modules'))).toEqual([]);
  });

  it('aucun caractère invisible littéral dans les fichiers du plan 4', () => {
    const fautes = A_LIRE.flatMap(fautesDuFichier);
    expect(fautes, fautes.join('\n')).toEqual([]);
  });
});
