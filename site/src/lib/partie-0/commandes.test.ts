// Les commandes affichées par les chapitres de la Partie 0 (commandes.ts) sont
// vérifiées contre le dépôt : le dépôt cloné est celui du site, chaque dossier
// visé par un cd existe, et chaque module lancé par python -m a son __main__.py
// dans un projet de la Partie 0.

import { existsSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DEPOT } from '../depot';
import * as commandes from './commandes';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const TOUTES = Object.entries(commandes) as [string, string][];

describe('commandes de la Partie 0', () => {
  it('les commandes du brief, à l’identique', () => {
    expect(commandes.INSTALLER_UV_LINUX_MAC).toBe('curl -LsSf https://astral.sh/uv/install.sh | sh');
    expect(commandes.VERIFIER_UV).toBe('uv --version');
    expect(commandes.CLONER_DEPOT).toBe('git clone https://github.com/chipat-neko/forge-ia');
  });

  it('chaque commande tient sur une ligne, sans espace en trop', () => {
    for (const [nom, commande] of TOUTES) {
      expect(commande, nom).not.toMatch(/\n/);
      expect(commande, nom).toBe(commande.trim());
    }
  });

  it('le dépôt cloné est celui du site, et son dossier est celui des cd', () => {
    expect(commandes.CLONER_DEPOT.endsWith(DEPOT)).toBe(true);
    const dossier = DEPOT.split('/').at(-1);
    for (const [nom, commande] of TOUTES.filter(([, c]) => c.startsWith('cd '))) {
      const chemin = commande.slice(3);
      expect(chemin.startsWith(`${dossier}/`), nom).toBe(true);
      expect(existsSync(`${RACINE}/${chemin.slice(dossier!.length + 1)}`), `${nom} : ${chemin}`).toBe(true);
    }
  });

  it('chaque python -m vise un module qui a son __main__.py dans un projet de la Partie 0', () => {
    const projets = readdirSync(`${RACINE}/projets`).filter((d) => /^0\./.test(d));
    for (const [nom, commande] of TOUTES) {
      for (const [, module] of commande.matchAll(/python -m (\S+)/g)) {
        const trouves = projets.filter((p) => existsSync(`${RACINE}/projets/${p}/${module.replace(/\./g, '/')}/__main__.py`));
        expect(trouves, `${nom} : ${module}`).toHaveLength(1);
      }
    }
  });
});
