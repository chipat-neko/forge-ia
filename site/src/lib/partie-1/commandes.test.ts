// Les commandes affichées par les chapitres de la Partie 1 (commandes.ts) sont
// vérifiées contre le dépôt, comme celles de la Partie 0 : chaque dossier visé
// par un cd existe, chaque module lancé par python -m a son __main__.py dans un
// projet de la Partie 1 (ou dans forge), et la mise à jour du dépôt mène au
// projet. Chaque chapitre vérifie ensuite ses propres commandes contre son
// projet (le README, le __main__.py).

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CLONER_DEPOT, METTRE_A_JOUR_DEPOT } from '../partie-0/commandes';
import * as commandes from './commandes';
import { MESURES_PARTIE_1 } from './mesures';
import { GRAINE_INITIALE, LONGUEUR_SUITE, N_INITIAL, TEMPERATURE_INITIALE } from './paris-1-1';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const TOUTES = Object.entries(commandes) as [string, string][];
/** Le dossier que crée le clonage, et que vise la mise à jour : le dernier morceau de l'adresse. */
const DOSSIER = CLONER_DEPOT.split('/').at(-1)!;

describe('commandes de la Partie 1', () => {
  it('chaque commande tient sur une ligne, sans espace en trop', () => {
    expect(TOUTES.length).toBeGreaterThan(0);
    for (const [nom, commande] of TOUTES) {
      expect(commande, nom).not.toMatch(/\n/);
      expect(commande, nom).toBe(commande.trim());
    }
  });

  it('chaque cd vise un dossier du dépôt cloné qui existe, et la mise à jour y mène', () => {
    expect(METTRE_A_JOUR_DEPOT).toBe(`git -C ${DOSSIER} pull`);
    const cd = TOUTES.filter(([, c]) => c.startsWith('cd '));
    expect(cd.length).toBeGreaterThan(0);
    for (const [nom, commande] of cd) {
      const chemin = commande.slice(3);
      expect(chemin.startsWith(`${DOSSIER}/projets/1.`) || chemin === `${DOSSIER}/projets/forge`, nom).toBe(true);
      expect(existsSync(`${RACINE}/${chemin.slice(DOSSIER.length + 1)}`), `${nom} : ${chemin}`).toBe(true);
    }
  });

  it('chaque python -m vise un module qui a son __main__.py dans un projet de la Partie 1, ou dans forge', () => {
    const projets = readdirSync(`${RACINE}/projets`).filter((d) => /^1\./.test(d) || d === 'forge');
    for (const [nom, commande] of TOUTES) {
      for (const [, module] of commande.matchAll(/python -m (\S+)/g)) {
        const trouves = projets.filter((p) => existsSync(`${RACINE}/projets/${p}/${module.replace(/\./g, '/')}/__main__.py`));
        expect(trouves, `${nom} : ${module}`).toHaveLength(1);
      }
    }
  });
});

// Le chapitre 1.1 : le script `python -m modele_de_langage suite`, vérifié
// contre le __main__.py et le README du projet, lus en texte.
describe('commandes du chapitre 1.1', () => {
  const PROJET = `${RACINE}/projets/1.1-modele-de-langage`;
  const MAIN = readFileSync(`${PROJET}/modele_de_langage/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_1).toBe('cd forge-ia/projets/1.1-modele-de-langage');
    expect(commandes.MODELE_SUITE).toBe('uv run python -m modele_de_langage suite --n 4 --temperature 1 --graine 0 "Le forgeron "');
  });

  it('suite est une commande du script, avec ses trois options', () => {
    expect(MAIN).toContain('add_parser("suite"');
    expect(/python -m modele_de_langage (\S+)/.exec(commandes.MODELE_SUITE)![1]).toBe('suite');
    for (const option of ['--n', '--temperature', '--graine']) {
      expect(commandes.MODELE_SUITE).toContain(`${option} `);
      expect(MAIN, option).toContain(`suite.add_argument("${option}"`);
    }
    // Aucun --extra : le projet n'utilise que la bibliothèque standard.
    expect(commandes.MODELE_SUITE).not.toContain('--extra');
  });

  it('ses réglages sont ceux de l’atelier à l’arrivée : le chapitre dit que l’atelier écrit le même texte', () => {
    const option = (nom: string) => Number(new RegExp(`--${nom} (\\S+)`).exec(commandes.MODELE_SUITE)![1]);
    expect(option('n')).toBe(N_INITIAL);
    expect(option('temperature')).toBe(TEMPERATURE_INITIALE);
    expect(option('graine')).toBe(GRAINE_INITIALE);
    // Sans --longueur, le script écrit 200 caractères, comme l'atelier.
    expect(commandes.MODELE_SUITE).not.toContain('--longueur');
    expect(MAIN).toContain(`suite.add_argument("--longueur", type=int, default=${LONGUEUR_SUITE},`);
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_1}\n`);
    expect(README).toContain(`${commandes.MODELE_SUITE}\n`);
  });
});

// Le chapitre 1.2 : le tri des exemples et l'aperçu des sources, vérifiés contre le
// __main__.py et le README du projet, et contre les fichiers que lit le chapitre.
describe('commandes du chapitre 1.2', () => {
  const PROJET = `${RACINE}/projets/1.2-donnees`;
  const MAIN = readFileSync(`${PROJET}/donnees_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_2).toBe('cd forge-ia/projets/1.2-donnees');
    expect(commandes.DONNEES_TRIER).toBe('uv run python -m donnees_pas_a_pas trier exemples/web.jsonl');
    expect(commandes.DONNEES_APERCU).toBe(
      'uv run python -m donnees_pas_a_pas apercu --octets 5M --enregistrer sorties/apercu.txt --json mesures/apercu.json',
    );
  });

  it('trier et apercu sont des commandes du script, avec leurs options', () => {
    expect(MAIN).toContain('add_parser("trier"');
    expect(MAIN).toContain('add_parser("apercu"');
    for (const option of ['--octets', '--enregistrer', '--json']) {
      expect(commandes.DONNEES_APERCU).toContain(`${option} `);
      expect(MAIN, option).toContain(`ape.add_argument("${option}"`);
    }
    expect(existsSync(`${PROJET}/${/trier (\S+)$/.exec(commandes.DONNEES_TRIER)![1]}`)).toBe(true);
    // Aucun --extra : le projet n'installe pas PyTorch.
    expect(commandes.DONNEES_TRIER).not.toContain('--extra');
    expect(commandes.DONNEES_APERCU).not.toContain('--extra');
  });

  it('l’aperçu écrit les fichiers que lit le chapitre (MESURES_PARTIE_1)', () => {
    const projet = 'projets/1.2-donnees/';
    expect(`${projet}${/--enregistrer (\S+)/.exec(commandes.DONNEES_APERCU)![1]}`).toBe(MESURES_PARTIE_1.sortieApercu);
    expect(`${projet}${/--json (\S+)/.exec(commandes.DONNEES_APERCU)![1]}`).toBe(MESURES_PARTIE_1.apercu);
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_2}\n`);
    expect(README).toContain(`${commandes.DONNEES_TRIER}\n`);
    expect(README).toContain(`${commandes.DONNEES_APERCU}\n`);
  });
});

// Le chapitre 1.4 : la comparaison à forge et le comptage des paramètres, vérifiés contre le
// __main__.py et le README du projet, et contre la sortie que montre le chapitre.
describe('commandes du chapitre 1.4', () => {
  const PROJET = `${RACINE}/projets/1.4-transformer`;
  const MAIN = readFileSync(`${PROJET}/transformer_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const PYPROJECT = readFileSync(`${PROJET}/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_4).toBe('cd forge-ia/projets/1.4-transformer');
    expect(commandes.TRANSFORMER_COMPARER).toBe(
      'uv run --extra cpu python -m transformer_pas_a_pas comparer --enregistrer sorties/comparaison.txt',
    );
    expect(commandes.TRANSFORMER_COMPTER).toBe('uv run --extra cpu python -m transformer_pas_a_pas compter --preset tres_grand');
    expect(commandes.TRANSFORMER_TESTS).toBe('uv run --extra cpu pytest -q');
  });

  it('comparer et compter sont des commandes du script, avec leurs options', () => {
    expect(MAIN).toContain('add_parser("comparer"');
    expect(MAIN).toContain('add_parser("compter"');
    expect(MAIN).toContain('comparer.add_argument("--enregistrer"');
    expect(MAIN).toContain('compter.add_argument("--preset"');
    // Le projet utilise PyTorch : chaque commande prend la version pour le processeur, un extra du projet.
    expect(PYPROJECT).toContain('cpu = ["torch==');
    for (const commande of [commandes.TRANSFORMER_COMPARER, commandes.TRANSFORMER_COMPTER, commandes.TRANSFORMER_TESTS]) {
      expect(commande.startsWith('uv run --extra cpu '), commande).toBe(true);
    }
  });

  it('comparer écrit la sortie que montre le chapitre (MESURES_PARTIE_1)', () => {
    expect(`projets/1.4-transformer/${/--enregistrer (\S+)/.exec(commandes.TRANSFORMER_COMPARER)![1]}`).toBe(
      MESURES_PARTIE_1.sortieComparaison,
    );
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_4}\n`);
    expect(README).toContain(`${commandes.TRANSFORMER_COMPARER}\n`);
    expect(README).toContain(`${commandes.TRANSFORMER_COMPTER}\n`);
    expect(README).toContain(`${commandes.TRANSFORMER_TESTS}\n`);
  });
});
