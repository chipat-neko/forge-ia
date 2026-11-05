// Les commandes affichées par les chapitres de la Partie 0 (commandes.ts) sont
// vérifiées contre le dépôt : le dépôt cloné est celui du site, chaque dossier
// visé par un cd existe, et chaque module lancé par python -m a son __main__.py
// dans un projet de la Partie 0.

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DEPOT } from '../depot';
import { A_DEPART, B_DEPART } from './atelier-formes';
import * as commandes from './commandes';
import { ecrireForme } from './formes';

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

  it('la mise à jour vise le dossier que crée le clonage', () => {
    expect(commandes.METTRE_A_JOUR_DEPOT).toBe('git -C forge-ia pull');
    const vise = /^git -C (\S+) pull$/.exec(commandes.METTRE_A_JOUR_DEPOT);
    expect(vise, 'METTRE_A_JOUR_DEPOT doit être « git -C <dossier> pull »').not.toBeNull();
    // git clone <adresse> crée un dossier du nom du dépôt : le dernier morceau de l'adresse.
    expect(vise![1]).toBe(commandes.CLONER_DEPOT.split('/').at(-1));
    expect(commandes.ALLER_AU_PROJET_0_3.startsWith(`cd ${vise![1]}/`)).toBe(true);
  });

  it('forcer le processeur : la variable que lit appareil.py, à la valeur cpu', () => {
    expect(commandes.FORCER_PROCESSEUR_POWERSHELL).toBe('$env:FORGE_APPAREIL = "cpu"');
    expect(commandes.FORCER_PROCESSEUR_BASH).toBe('export FORGE_APPAREIL=cpu');
    const appareil = readFileSync(`${RACINE}/projets/0.3-poste/poste/appareil.py`, 'utf8');
    expect(appareil).toContain('os.environ.get("FORGE_APPAREIL")');
    expect(appareil).toContain('if valeur == "cpu":');
  });
});

// Le chapitre 0.4 : le script `python -m tenseurs` et ses deux commandes,
// formes et mesurer, vérifiées contre le __main__.py et le pyproject.toml du
// projet, lus en texte (sans PyTorch).
describe('commandes du chapitre 0.4', () => {
  const PROJET = `${RACINE}/projets/0.4-tenseurs`;
  const MAIN = readFileSync(`${PROJET}/tenseurs/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const PYPROJECT = readFileSync(`${PROJET}/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');
  const DU_CHAPITRE = [commandes.TENSEURS_FORMES, commandes.TENSEURS_MESURER_CPU, commandes.TENSEURS_MESURER_GPU];

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_0_4).toBe('cd forge-ia/projets/0.4-tenseurs');
    expect(commandes.TENSEURS_FORMES).toBe('uv run --extra cpu python -m tenseurs formes "(3, 1)" "(4,)"');
    expect(commandes.TENSEURS_MESURER_CPU).toBe('uv run --extra cpu python -m tenseurs mesurer');
    expect(commandes.TENSEURS_MESURER_GPU).toBe('uv run --extra gpu python -m tenseurs mesurer');
  });

  it('les formes de la commande sont celles du départ de l’atelier, écrites comme Python', () => {
    expect(commandes.TENSEURS_FORMES.endsWith(` "${ecrireForme(A_DEPART)}" "${ecrireForme(B_DEPART)}"`)).toBe(true);
  });

  it('formes et mesurer sont des commandes du script, et mesurer suit FORGE_APPAREIL sans --appareil', () => {
    expect(MAIN).toContain('add_parser("formes"');
    expect(MAIN).toContain('add_parser("mesurer"');
    for (const commande of DU_CHAPITRE) {
      const sous = /python -m tenseurs (\S+)/.exec(commande)![1];
      expect(['formes', 'mesurer'], commande).toContain(sous);
    }
    // Sans --appareil, mesurer passe None à choisir_appareil, qui lit alors FORGE_APPAREIL.
    expect(MAIN).toMatch(/"--appareil",[^\n]*default=None/);
    expect(MAIN).toContain('choisir_appareil(options.appareil)');
    expect(commandes.TENSEURS_MESURER_CPU).not.toContain('--appareil');
    expect(commandes.TENSEURS_MESURER_GPU).not.toContain('--appareil');
  });

  it('chaque --extra est un extra du pyproject.toml du projet 0.4', () => {
    const section = /^\[project\.optional-dependencies\]\n([\s\S]*?)(?=^\[|(?![\s\S]))/m.exec(PYPROJECT);
    expect(section, 'section [project.optional-dependencies] introuvable dans le pyproject.toml de 0.4-tenseurs').not.toBeNull();
    const extras = [...section![1].matchAll(/^([A-Za-z0-9_-]+)\s*=/gm)].map(([, nom]) => nom);
    expect(extras.sort()).toEqual(['cpu', 'gpu']);
    for (const commande of DU_CHAPITRE) {
      for (const [, extra] of commande.matchAll(/--extra (\S+)/g)) expect(extras, commande).toContain(extra);
    }
  });

  it('la mise à jour du dépôt mène aussi au projet 0.4', () => {
    const vise = /^git -C (\S+) pull$/.exec(commandes.METTRE_A_JOUR_DEPOT)![1];
    expect(commandes.ALLER_AU_PROJET_0_4.startsWith(`cd ${vise}/`)).toBe(true);
  });
});

// Le chapitre 0.5 : le script `python -m premier_reseau entrainer`, vérifié
// contre le __main__.py, l'appareil.py, le pyproject.toml et le README du
// projet, lus en texte (sans PyTorch).
describe('commandes du chapitre 0.5', () => {
  const PROJET = `${RACINE}/projets/0.5-reseau`;
  const MAIN = readFileSync(`${PROJET}/premier_reseau/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const APPAREIL = readFileSync(`${PROJET}/premier_reseau/appareil.py`, 'utf8').replace(/\r\n?/g, '\n');
  const PYPROJECT = readFileSync(`${PROJET}/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const DU_CHAPITRE = [commandes.RESEAU_ENTRAINER_CPU, commandes.RESEAU_ENTRAINER_GPU];

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_0_5).toBe('cd forge-ia/projets/0.5-reseau');
    expect(commandes.RESEAU_ENTRAINER_CPU).toBe('uv run --extra cpu python -m premier_reseau entrainer --appareil cpu');
    expect(commandes.RESEAU_ENTRAINER_GPU).toBe('uv run --extra gpu python -m premier_reseau entrainer --appareil cuda');
  });

  it('entrainer est une commande du script, et --appareil reçoit un choix de choisir_appareil', () => {
    expect(MAIN).toContain('add_parser("entrainer"');
    expect(MAIN).toMatch(/"--appareil",[^\n]*default=None/);
    expect(MAIN).toContain('choisir_appareil(options.appareil)');
    for (const commande of DU_CHAPITRE) {
      expect(/python -m premier_reseau (\S+)/.exec(commande)![1], commande).toBe('entrainer');
      const appareil = /--appareil (\S+)$/.exec(commande)![1];
      expect(APPAREIL, commande).toContain(`if valeur == "${appareil}":`);
    }
  });

  it('chaque --extra est un extra du pyproject.toml du projet 0.5', () => {
    const section = /^\[project\.optional-dependencies\]\n([\s\S]*?)(?=^\[|(?![\s\S]))/m.exec(PYPROJECT);
    expect(section, 'section [project.optional-dependencies] introuvable dans le pyproject.toml de 0.5-reseau').not.toBeNull();
    const extras = [...section![1].matchAll(/^([A-Za-z0-9_-]+)\s*=/gm)].map(([, nom]) => nom);
    expect(extras.sort()).toEqual(['cpu', 'gpu']);
    for (const commande of DU_CHAPITRE) {
      for (const [, extra] of commande.matchAll(/--extra (\S+)/g)) expect(extras, commande).toContain(extra);
    }
  });

  it('ce sont les commandes du README, celles qui ont écrit les sorties du chapitre', () => {
    for (const commande of DU_CHAPITRE) {
      expect(README, commande).toContain(`${commande}\n`);
      expect(README, commande).toContain(`${commande} --enregistrer sorties/`);
    }
  });

  it('la mise à jour du dépôt mène aussi au projet 0.5', () => {
    const vise = /^git -C (\S+) pull$/.exec(commandes.METTRE_A_JOUR_DEPOT)![1];
    expect(commandes.ALLER_AU_PROJET_0_5.startsWith(`cd ${vise}/`)).toBe(true);
  });
});
