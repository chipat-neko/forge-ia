// Les fonctions non reproductibles n'entrent pas dans le chemin vérifié.
//
// Jumeau de projets/mini-modele/tests/test_sources.py. Les fichiers vérifiés
// du mini-modèle doivent donner les mêmes bits que le Python dans tous les
// navigateurs : seuls + − × ÷, Math.sqrt, Math.floor, Math.imul et les
// opérations entières y sont permis. Le motif est cherché partout,
// commentaires compris.
//
// Règle des divisions entières, qu'aucun scan ne peut vérifier (le signe d'une
// variable ne se lit pas dans le texte) : les indices sont toujours positifs,
// et `%` et `//` ne servent que sur des entiers positifs (ou nuls pour le
// dividende). Là, les deux langages donnent le même résultat : `a % b` des deux
// côtés, `a // b` en Python face à `Math.floor(a / b)` ici. Ailleurs, le `%` de
// Python prend le signe du diviseur et celui de JavaScript le signe du
// dividende, et le `//` d'un flottant n'est pas toujours floor(a / b) : on
// écrit alors Math.floor(a / b), et a - b * Math.floor(a / b), des deux côtés.

import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { extraireRegion } from '../regions';

// L'ouverture « /** » d'un commentaire de documentation reste permise.
const INTERDITS =
  /Math\.(exp|log|log1p|log2|log10|expm1|cos|sin|tan|tanh|pow|hypot|random)\b|(?<!\/)\*\*|crypto\.getRandomValues/;
const VERIFIES = ['calcul', 'donnees', 'attention', 'modele', 'entrainement', 'exemple-attention'];
// Les fichiers vérifiés qui doivent déjà exister : sans cette liste, un fichier
// mal nommé ne serait jamais lu. Elle grandit à chaque tâche du plan 3.
const OBLIGATOIRES = ['calcul'];
// Les seules fonctions de Math permises. Les autres (max, min, fround, cbrt…)
// arrondissent autrement que le Python, ou traitent −0 autrement.
const MATH_PERMIS = new Set(['sqrt', 'floor', 'imul']);

const CALCUL_PY = new URL('../../../../projets/mini-modele/mini_modele/calcul.py', import.meta.url);

function chemin(nom: string): URL {
  return new URL(`./${nom}.ts`, import.meta.url);
}

/** Le nom et le texte de chaque fichier vérifié présent. */
function sourcesVerifiees(): [string, string][] {
  return VERIFIES.filter((nom) => OBLIGATOIRES.includes(nom) || existsSync(chemin(nom))).map((nom) => [
    nom,
    readFileSync(chemin(nom), 'utf8'),
  ]);
}

function numeroDeLigne(texte: string, position: number): number {
  return texte.slice(0, position).split('\n').length;
}

describe('fichiers vérifiés du mini-modèle', () => {
  it('les fichiers obligatoires existent', () => {
    for (const nom of OBLIGATOIRES) {
      expect(VERIFIES, `${nom} est obligatoire mais absent de VERIFIES : ajoute-le aux deux listes.`).toContain(nom);
      expect(
        existsSync(chemin(nom)),
        `src/lib/mini-modele/${nom}.ts est introuvable. Un fichier vérifié a-t-il changé de nom ? ` +
          'Renomme-le, ou corrige OBLIGATOIRES et VERIFIES dans sources.test.ts.',
      ).toBe(true);
    }
  });

  it('n’utilisent aucune fonction non reproductible, même en commentaire', () => {
    for (const [nom, texte] of sourcesVerifiees()) {
      const trouve = INTERDITS.exec(texte);
      expect(
        trouve,
        trouve
          ? `${nom}.ts, ligne ${numeroDeLigne(texte, trouve.index)} : « ${trouve[0]} » n'est pas reproductible ` +
              "d'un navigateur à l'autre. Utilise exp, log, cos, somme ou Hasard de calcul.ts."
          : '',
      ).toBeNull();
    }
  });

  it('n’utilisent que les fonctions exactes de Math', () => {
    for (const [nom, texte] of sourcesVerifiees()) {
      for (const trouve of texte.matchAll(/\bMath\.(\w+)/g)) {
        expect(
          MATH_PERMIS.has(trouve[1]),
          `${nom}.ts, ligne ${numeroDeLigne(texte, trouve.index)} : Math.${trouve[1]} n'est pas dans MATH_PERMIS. ` +
            'Remplace-la par des + − × ÷, ou ajoute-la à MATH_PERMIS seulement si elle est exacte (aucun arrondi).',
        ).toBe(true);
      }
      expect(
        /\bMath\s*\[|=\s*Math\s*(;|$)/m.test(texte),
        `${nom}.ts lit Math de façon indirecte : écris Math.sqrt(…), pour que ce test puisse vérifier chaque appel.`,
      ).toBe(false);
    }
  });

  it('le motif attrape les interdits, et laisse passer le reste', () => {
    for (const interdit of [
      'Math.exp(x)',
      'Math.log(x)',
      'Math.random()',
      'Math.hypot(a, b)',
      'x ** 2',
      'x **= 2',
      'crypto.getRandomValues(t)',
    ]) {
      expect(INTERDITS.test(interdit), interdit).toBe(true);
    }
    for (const permis of ['/** Documentation. */', 'Math.sqrt(x)', 'Math.imul(a, b)', 'a * b', 'somme(v)']) {
      expect(INTERDITS.test(permis), permis).toBe(false);
    }
  });
});

describe('régions de calcul.py, pour le chapitre 1.5', () => {
  it('extrait la région exp', () => {
    const region = extraireRegion(readFileSync(CALCUL_PY, 'utf8'), 'exp', 'calcul.py');
    expect(region.startsWith('def exp(')).toBe(true);
    expect(region).toContain('k = math.floor(x * INV_LN2 + 0.5)');
    expect(region.trimEnd().endsWith('return p * deux_puissance(k)')).toBe(true);
    expect(region).not.toMatch(/region:|fin:/);
  });

  it('extrait la région log', () => {
    const region = extraireRegion(readFileSync(CALCUL_PY, 'utf8'), 'log', 'calcul.py');
    expect(region.startsWith('def log(')).toBe(true);
    expect(region).toContain('m, e = math.frexp(x)');
    expect(region.trimEnd().endsWith('return e * LN2_HAUT + (2.0 * s * q + e * LN2_BAS)')).toBe(true);
    expect(region).not.toMatch(/region:|fin:/);
  });
});
