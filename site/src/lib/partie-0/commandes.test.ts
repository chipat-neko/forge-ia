// Les commandes affichées par les chapitres de la Partie 0 (commandes.ts) sont
// vérifiées contre le dépôt : le dépôt cloné est celui du site, chaque dossier
// visé par un cd existe, et chaque module lancé par python -m a son __main__.py
// dans un projet de la Partie 0.

import { existsSync, readdirSync, readFileSync } from 'node:fs';
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

// Le chapitre 0.3 : les commandes de PyTorch, vérifiées contre le pyproject.toml
// du projet, lu en texte (un extra par ligne « nom = [...] » de sa section
// [project.optional-dependencies]).
describe('commandes du chapitre 0.3', () => {
  const PYPROJECT = readFileSync(`${RACINE}/projets/0.3-poste/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');

  /** Les extras du pyproject.toml : les clés de sa section [project.optional-dependencies]. */
  function extras(texte: string): string[] {
    const section = /^\[project\.optional-dependencies\]\n([\s\S]*?)(?=^\[|(?![\s\S]))/m.exec(texte);
    expect(section, 'section [project.optional-dependencies] introuvable dans le pyproject.toml de 0.3-poste').not.toBeNull();
    return [...section![1].matchAll(/^([A-Za-z0-9_-]+)\s*=/gm)].map(([, nom]) => nom);
  }

  it('les commandes du brief, à l’identique', () => {
    expect(commandes.NVIDIA_SMI).toBe('nvidia-smi');
    expect(commandes.SYNC_GPU).toBe('uv sync --extra gpu');
    expect(commandes.SYNC_CPU).toBe('uv sync --extra cpu');
    expect(commandes.VERIFIER_POSTE_GPU).toBe('uv run --extra gpu python -m poste');
    expect(commandes.VERIFIER_POSTE_CPU).toBe('uv run --extra cpu python -m poste');
    expect(commandes.ALLER_AU_PROJET_0_3).toBe('cd forge-ia/projets/0.3-poste');
    // Ce que d'anciens tutoriels font taper : cité par le chapitre, jamais à taper.
    expect(commandes.PIP_INSTALL_TORCH).toBe('pip install torch');
    expect(commandes.CONDA_INSTALL_PYTORCH).toBe('conda install pytorch -c pytorch');
  });

  it('le pyproject.toml a les extras cpu et gpu, et les index de PyTorch pour CUDA 13.2 et pour le processeur', () => {
    expect(extras(PYPROJECT).sort()).toEqual(['cpu', 'gpu']);
    expect(PYPROJECT).toContain('url = "https://download.pytorch.org/whl/cu132"');
    expect(PYPROJECT).toContain('url = "https://download.pytorch.org/whl/cpu"');
  });

  it('chaque --extra des commandes est un extra du pyproject.toml', () => {
    const connus = extras(PYPROJECT);
    const vus = TOUTES.flatMap(([nom, commande]) => [...commande.matchAll(/--extra (\S+)/g)].map(([, extra]) => [nom, extra]));
    expect(vus.length).toBeGreaterThanOrEqual(4);
    for (const [nom, extra] of vus) expect(connus, `${nom} : --extra ${extra}`).toContain(extra);
  });

  it('python -m poste lance le __main__.py du projet 0.3-poste', () => {
    expect(existsSync(`${RACINE}/projets/0.3-poste/poste/__main__.py`)).toBe(true);
  });
});
