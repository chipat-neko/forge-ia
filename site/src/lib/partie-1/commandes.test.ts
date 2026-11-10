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
import { FICHIERS_EVALUATION, FICHIERS_QCM } from './evaluation';
import { FICHIERS_ENTRAINEMENT } from './journal';
import { MESURES_PARTIE_1 } from './mesures';
import { GRAINE_INITIALE, LONGUEUR_SUITE, N_INITIAL, TEMPERATURE_INITIALE } from './paris-1-1';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
// Une constante est une commande, ou une suite de commandes (ENTRAINER_COURT) dont chaque élément en est une.
const TOUTES: [string, string][] = Object.entries(commandes).flatMap(([nom, valeur]) =>
  typeof valeur === 'string' ? [[nom, valeur]] : (valeur as readonly string[]).map((c, i): [string, string] => [`${nom}[${i}]`, c]),
);
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

// Le chapitre 1.5 : les commandes du projet « pré-entraînement » (vérifiées contre son __main__.py, son
// README et les fichiers qu'elles écrivent), puis celles de la version d'une heure de ton IA
// (vérifiées contre docs/mesures/ton-ia-mini.md, le README et configs/mini.toml de forge).
describe('commandes du chapitre 1.5, le projet', () => {
  const PROJET = `${RACINE}/projets/1.5-pre-entrainement`;
  const MAIN = readFileSync(`${PROJET}/pre_entrainement/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const PYPROJECT = readFileSync(`${PROJET}/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_5).toBe('cd forge-ia/projets/1.5-pre-entrainement');
    expect(commandes.PRE_ENTRAINEMENT_ESSAI).toBe(
      'uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json',
    );
    expect(commandes.PRE_ENTRAINEMENT_COURBE).toBe(
      'uv run --extra cpu python -m pre_entrainement courbe --journal D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\journal.jsonl --config ..\\forge\\configs\\mini.toml --json mesures/ton-ia-mini.json',
    );
    expect(commandes.PRE_ENTRAINEMENT_TESTS).toBe('uv run --extra cpu pytest -q');
  });

  it('essai et courbe sont des commandes du script, avec leurs options', () => {
    expect(MAIN).toContain('add_parser("essai"');
    expect(MAIN).toContain('add_parser("courbe"');
    for (const option of ['--appareil', '--enregistrer', '--json']) {
      expect(commandes.PRE_ENTRAINEMENT_ESSAI).toContain(`${option} `);
      expect(MAIN, option).toMatch(new RegExp(`essai\\.add_argument\\(\\s*"${option}"`));
    }
    for (const option of ['--journal', '--config', '--json']) {
      expect(commandes.PRE_ENTRAINEMENT_COURBE).toContain(`${option} `);
      expect(MAIN, option).toMatch(new RegExp(`courbe\\.add_argument\\(\\s*"${option}"`));
    }
    // Le projet utilise PyTorch : chaque commande prend la version pour le processeur, un extra du projet.
    expect(PYPROJECT).toContain('cpu = ["torch==');
    for (const c of [commandes.PRE_ENTRAINEMENT_ESSAI, commandes.PRE_ENTRAINEMENT_COURBE, commandes.PRE_ENTRAINEMENT_TESTS]) {
      expect(c.startsWith('uv run --extra cpu '), c).toBe(true);
    }
  });

  it('l’essai écrit les fichiers que lit le chapitre (MESURES_PARTIE_1)', () => {
    const projet = 'projets/1.5-pre-entrainement/';
    expect(`${projet}${/--enregistrer (\S+)/.exec(commandes.PRE_ENTRAINEMENT_ESSAI)![1]}`).toBe(MESURES_PARTIE_1.sortieEssaiProcesseur);
    expect(`${projet}${/--json (\S+)/.exec(commandes.PRE_ENTRAINEMENT_ESSAI)![1]}`).toBe(MESURES_PARTIE_1.essaiProcesseur);
  });

  it('la courbe écrit le relevé que lit le chapitre (FICHIERS_ENTRAINEMENT)', () => {
    expect(`projets/1.5-pre-entrainement/${/--json (\S+)/.exec(commandes.PRE_ENTRAINEMENT_COURBE)![1]}`).toBe(
      FICHIERS_ENTRAINEMENT['ton-ia-mini'],
    );
    // Le journal et la configuration sont ceux de la version d'une heure.
    expect(commandes.PRE_ENTRAINEMENT_COURBE).toContain('entrainements\\ton-ia-mini\\journal.jsonl');
    expect(existsSync(`${RACINE}/projets/forge/configs/mini.toml`)).toBe(true);
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_5}\n`);
    expect(README).toContain(`${commandes.PRE_ENTRAINEMENT_ESSAI}\n`);
    expect(README).toContain(`${commandes.PRE_ENTRAINEMENT_COURBE}\n`);
    expect(README).toContain(`${commandes.PRE_ENTRAINEMENT_TESTS}\n`);
  });
});

describe('commandes de la version d’une heure de ton IA', () => {
  const FORGE = `${RACINE}/projets/forge`;
  const MINI_MD = readFileSync(`${RACINE}/docs/mesures/ton-ia-mini.md`, 'utf8').replace(/\r\n?/g, '\n');
  const README_FORGE = readFileSync(`${FORGE}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const MINI_TOML = readFileSync(`${FORGE}/configs/mini.toml`, 'utf8').replace(/\r\n?/g, '\n');
  const PREFIXE = 'uv run --extra gpu ';
  /** La partie « python -m forge … » d'une commande de la version courte. */
  const partie = (c: string) => c.slice(PREFIXE.length);

  it('ENTRAINER_COURT : donnees, encoder, entrainer, evaluer, dans cet ordre, en --extra gpu', () => {
    expect(commandes.ENTRAINER_COURT).toStrictEqual([
      commandes.COURT_DONNEES,
      commandes.COURT_ENCODER,
      commandes.COURT_ENTRAINER,
      commandes.COURT_EVALUER,
    ]);
    expect(commandes.ENTRAINER_COURT.map((c) => /python -m forge (\S+)/.exec(c)![1])).toStrictEqual([
      'donnees',
      'encoder',
      'entrainer',
      'evaluer',
    ]);
    for (const c of commandes.ENTRAINER_COURT) expect(c.startsWith(`${PREFIXE}python -m forge `), c).toBe(true);
  });

  it('chaque commande se lit telle quelle dans docs/mesures/ton-ia-mini.md, dans le même ordre', () => {
    const lignes = MINI_MD.split('\n');
    let apres = -1;
    for (const c of commandes.ENTRAINER_COURT) {
      const rang = lignes.indexOf(partie(c));
      expect(rang, partie(c)).toBeGreaterThan(apres);
      apres = rang;
    }
  });

  it('chaque commande a, dans le README de forge, son préfixe uv run --extra gpu', () => {
    for (const c of commandes.ENTRAINER_COURT) {
      const sous = /python -m forge (\S+)/.exec(c)![1];
      expect(README_FORGE, sous).toContain(`${PREFIXE}python -m forge ${sous}`);
    }
  });

  it('chaque option des commandes existe dans forge', () => {
    const main = readFileSync(`${FORGE}/forge/__main__.py`, 'utf8');
    for (const c of commandes.ENTRAINER_COURT) {
      // Les options de forge, après « python -m forge <commande> » (--extra est celle de uv).
      for (const [, option] of c.slice(c.indexOf('python -m forge')).matchAll(/ (--[a-z-]+)/g)) {
        expect(main, `${option} (${c})`).toContain(`"${option}"`);
      }
    }
  });

  it('l’entraînement lance configs/mini.toml, qui existe', () => {
    expect(commandes.COURT_ENTRAINER).toContain('--config configs/mini.toml');
    expect(MINI_MD).toContain('--config configs/mini.toml');
  });

  it('PAUSE et REPRENDRE se lisent dans configs/mini.toml', () => {
    expect(commandes.PAUSE).toBe('Ctrl+C met en pause');
    expect(MINI_TOML).toContain(`# ${commandes.PAUSE} (`);
    expect(MINI_TOML.split('\n')).toContain(`#   ${commandes.REPRENDRE}`);
  });

  it('REPRENDRE est la commande d’entraînement avec --reprendre', () => {
    expect(commandes.REPRENDRE).toBe(`${commandes.COURT_ENTRAINER} --reprendre`);
    expect(README_FORGE).toContain('`--reprendre`');
  });
});

// Le chapitre 1.6 : les sous-commandes resumer et qcm-exemples de
// projets/1.6-evaluation/evaluation_pas_a_pas/__main__.py, vérifiées contre ce script, le README du
// projet, et les relevés que lit le chapitre (FICHIERS_EVALUATION, FICHIERS_QCM).
describe('commandes du chapitre 1.6', () => {
  const PROJET = `${RACINE}/projets/1.6-evaluation`;
  const MAIN = readFileSync(`${PROJET}/evaluation_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const PYPROJECT = readFileSync(`${PROJET}/pyproject.toml`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_6).toBe('cd forge-ia/projets/1.6-evaluation');
    expect(commandes.EVALUATION_RESUMER).toBe(
      'uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\evaluation\\etape-0006370\\rapport.json --json mesures/evaluation-mini.json',
    );
    expect(commandes.EVALUATION_QCM).toBe(
      'uv run --extra cpu python -m evaluation_pas_a_pas qcm-exemples --sauvegarde D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt --appareil cpu --json mesures/qcm-mini.json',
    );
    expect(commandes.EVALUATION_TESTS).toBe('uv run --extra cpu pytest -q');
  });

  it('resumer et qcm-exemples sont des commandes du script, avec leurs options', () => {
    expect(MAIN).toContain('add_parser("resumer"');
    expect(MAIN).toContain('add_parser("qcm-exemples"');
    for (const option of ['--rapport', '--json']) {
      expect(commandes.EVALUATION_RESUMER).toContain(`${option} `);
      expect(MAIN, option).toContain(`resume.add_argument("${option}"`);
    }
    // qcm-exemples prend les options des commandes qui chargent un modèle (ajouter_modele).
    expect(MAIN).toContain('ajouter_modele(exemples)');
    for (const option of ['--sauvegarde', '--appareil', '--json']) {
      expect(commandes.EVALUATION_QCM).toContain(`${option} `);
      expect(MAIN, option).toContain(`commande.add_argument("${option}"`);
    }
    // Le projet utilise PyTorch : chaque commande prend la version pour le processeur, un extra du projet.
    expect(PYPROJECT).toContain('cpu = ["torch==');
    for (const c of [commandes.EVALUATION_RESUMER, commandes.EVALUATION_QCM, commandes.EVALUATION_TESTS]) {
      expect(c.startsWith('uv run --extra cpu '), c).toBe(true);
    }
  });

  it('elles écrivent les relevés que lit le chapitre', () => {
    const projet = 'projets/1.6-evaluation/';
    expect(`${projet}${/--json (\S+)/.exec(commandes.EVALUATION_RESUMER)![1]}`).toBe(FICHIERS_EVALUATION['ton-ia-mini']);
    expect(`${projet}${/--json (\S+)/.exec(commandes.EVALUATION_QCM)![1]}`).toBe(FICHIERS_QCM['ton-ia-mini']);
    // Le rapport et la sauvegarde sont ceux du dernier pas de la version d'une heure.
    expect(commandes.EVALUATION_RESUMER).toContain('entrainements\\ton-ia-mini\\evaluation\\etape-0006370\\rapport.json');
    expect(commandes.EVALUATION_QCM).toContain('entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt');
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_6}\n`);
    expect(README).toContain(`${commandes.EVALUATION_RESUMER}\n`);
    expect(README).toContain(`${commandes.EVALUATION_QCM}\n`);
    expect(README).toContain(`${commandes.EVALUATION_TESTS}\n`);
  });
});
