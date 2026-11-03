// Rien de lourd dans la page : MiniModele.svelte et CourbePerte.svelte
// n'importent des valeurs que de modules légers (aucun n'importe le moteur ni
// la liste des prénoms), et seulement des types d'apercu.ts et de
// boucle-travailleur.ts. Le seul import dynamique est celui du Worker.
//
// Le parcours e2e/mini-modele.spec.ts (« la page ne charge pas les prénoms
// avant le lancement ») vérifie le paquet réellement construit ; ce test-ci
// le dit plus tôt, en relisant les sources.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

/** Les imports statiques d'un script : leur chemin, et s'ils ne portent que des types. */
function imports(source: string): { chemin: string; type: boolean }[] {
  const script = [...source.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]).join('\n');
  const liens = [...script.matchAll(/^\s*import\s+(type\s+)?(?:[^;]*?\s+from\s+)?'([^']+)';/gm)];
  // Toutes les lignes d'import sont bien lues par le motif.
  expect(liens).toHaveLength(script.match(/^\s*import\s[^(]/gm)?.length ?? 0);
  return liens.map(([, type, chemin]) => ({ chemin, type: type !== undefined }));
}

// Les modules dont on peut importer des valeurs : aucun n'importe le moteur.
const VALEURS = new Set([
  'svelte',
  '../../lib/canal',
  '../../lib/nombres',
  '../../lib/typo',
  '../../lib/courbe',
  '../../lib/mini-modele/reglages',
  '../../lib/mini-modele/pilote',
  '../interactif/NombreManipulable.svelte',
  './CourbePerte.svelte',
]);
// Les modules dont on ne peut importer que des types.
const TYPES = new Set(['../../lib/mini-modele/apercu', '../../lib/mini-modele/boucle-travailleur', '../../scripts/chapitre']);

describe('ce que les composants du mini-modèle importent', () => {
  for (const fichier of ['MiniModele.svelte', 'CourbePerte.svelte']) {
    it(`${fichier} : des valeurs seulement de modules légers`, () => {
      const source = readFileSync(new URL(`./${fichier}`, import.meta.url), 'utf8');
      const liens = imports(source);
      expect(liens.length).toBeGreaterThan(0);
      for (const { chemin, type } of liens) {
        if (type) expect(VALEURS.has(chemin) || TYPES.has(chemin), chemin).toBe(true);
        else expect(VALEURS.has(chemin), `${fichier} importe des valeurs de ${chemin}`).toBe(true);
      }
      // Le seul import dynamique est celui du Worker.
      const dynamiques = [...source.matchAll(/\bimport\(\s*'([^']+)'\s*\)/g)].map((m) => m[1]);
      expect(dynamiques).toEqual(fichier === 'MiniModele.svelte' ? ['../../lib/mini-modele/travailleur.ts?worker'] : []);
    });
  }

  it('les modules permis n’importent eux-mêmes aucune valeur du moteur', () => {
    for (const module of ['../../lib/nombres.ts', '../../lib/courbe.ts', '../../lib/typo.ts', '../../lib/mini-modele/reglages.ts']) {
      const source = readFileSync(new URL(module, import.meta.url), 'utf8');
      expect(source, module).not.toMatch(/^\s*import\s[^;]*from\s/m);
    }
    const canal = readFileSync(new URL('../../lib/canal.ts', import.meta.url), 'utf8');
    expect(canal).not.toMatch(/^\s*import\s/m);
    // pilote.ts est vérifié par son propre test (pilote.test.ts).
  });
});
