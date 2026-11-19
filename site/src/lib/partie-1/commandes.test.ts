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
import {
  FICHIERS_EVALUATION,
  FICHIERS_QCM,
  FICHIERS_SORTIES_TON_IA,
  lireCartes,
  lireEvaluation,
  lireSuivants,
  VERSION_PUBLIEE,
} from './evaluation';
import { FICHIERS_ENTRAINEMENT } from './journal';
import { MESURES_PARTIE_1 } from './mesures';
import { GRAINE_INITIALE, LONGUEUR_SUITE, N_INITIAL, TEMPERATURE_INITIALE } from './paris-1-1';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
// Une constante est une commande, ou une suite de commandes (ENTRAINER_COURT) dont chaque élément en est une.
// Une fonction (TELECHARGER_VERSION) fabrique une commande : elle est vérifiée à part, plus bas.
const TOUTES: [string, string][] = Object.entries(commandes).flatMap(([nom, valeur]) =>
  typeof valeur === 'function'
    ? []
    : typeof valeur === 'string'
      ? [[nom, valeur]]
      : (valeur as readonly string[]).map((c, i): [string, string] => [`${nom}[${i}]`, c]),
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
    // Sur la carte graphique de l'auteur : les mêmes options, l'extra gpu et l'appareil cuda.
    expect(`${projet}${/--enregistrer (\S+)/.exec(commandes.PRE_ENTRAINEMENT_ESSAI_CARTE)![1]}`).toBe(MESURES_PARTIE_1.sortieEssaiCarte);
    expect(`${projet}${/--json (\S+)/.exec(commandes.PRE_ENTRAINEMENT_ESSAI_CARTE)![1]}`).toBe(MESURES_PARTIE_1.essaiCarte);
  });

  it('l’essai sur la carte : la même commande, avec l’extra gpu et --appareil cuda', () => {
    expect(commandes.PRE_ENTRAINEMENT_ESSAI_CARTE).toBe(
      'uv run --extra gpu python -m pre_entrainement essai --appareil cuda --enregistrer sorties/essai-rtx-5070-ti.txt --json mesures/essai-rtx-5070-ti.json',
    );
    expect(PYPROJECT).toContain('gpu = ["torch==');
    for (const option of ['--appareil', '--enregistrer', '--json']) expect(commandes.PRE_ENTRAINEMENT_ESSAI_CARTE).toContain(`${option} `);
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
    expect(README).toContain(`${commandes.PRE_ENTRAINEMENT_ESSAI_CARTE}\n`);
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
      'uv run --extra cpu python -m evaluation_pas_a_pas resumer --rapport D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\evaluation\\meilleur-2026-11-17\\rapport.json --json mesures/evaluation-mini.json',
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
    // Le rapport est celui de la réévaluation du 17/11/2026 (bits par octet exacts) : malgré le nom de son
    // dossier, elle porte sur la sauvegarde du dernier pas, celle que note qcm-exemples.
    expect(commandes.EVALUATION_RESUMER).toContain('entrainements\\ton-ia-mini\\evaluation\\meilleur-2026-11-17\\rapport.json');
    expect(commandes.EVALUATION_QCM).toContain('entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt');
  });

  it('resumer relit le rapport du relevé, daté du même jour', () => {
    // resumer recopie la date du rapport dans releve_le : le chemin du rapport porte cette date.
    const rapport = /--rapport (\S+)/.exec(commandes.EVALUATION_RESUMER)![1];
    expect(rapport).toContain(lireEvaluation('ton-ia-mini', RACINE)!.releve_le);
  });

  it('ce sont les commandes du README du projet', () => {
    expect(README).toContain(`${commandes.ALLER_AU_PROJET_1_6}\n`);
    expect(README).toContain(`${commandes.EVALUATION_RESUMER}\n`);
    expect(README).toContain(`${commandes.EVALUATION_QCM}\n`);
    expect(README).toContain(`${commandes.EVALUATION_TESTS}\n`);
  });
});

// Ton IA, la vraie (la version publiée ton-ia-1.5) : le téléchargement et les quatre commandes du projet 1.6
// qui ont écrit ses relevés, vérifiés contre le __main__.py et le README du projet, et contre les fichiers que
// lisent les chapitres 1.6 (étape 8), 1.4 (étape 5) et 1.1 (étape 9). Le chapitre 1.6 les montre à son étape 10.
describe('commandes de ton IA, la vraie', () => {
  const PROJET = `${RACINE}/projets/1.6-evaluation`;
  const MAIN = readFileSync(`${PROJET}/evaluation_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const DOSSIER_TON_IA = 'D:\\forge-ia-donnees\\cache\\ton-ia-1.5';
  const DU_MODELE = [
    commandes.EVALUATION_QCM_TON_IA,
    commandes.EVALUATION_CARTES_TON_IA,
    commandes.EVALUATION_SUIVANTS_TON_IA,
  ];
  /** La valeur d'une option d'une commande : le mot qui la suit, ou la phrase entre guillemets. */
  const option = (commande: string, nom: string) => new RegExp(`--${nom} (?:"([^"]*)"|(\\S+))`).exec(commande)?.slice(1).find((x) => x !== undefined);

  it('le téléchargement prend la version publiée, dans le dossier que lisent les autres commandes', () => {
    expect(commandes.TELECHARGER_TON_IA).toBe(`gh release download ${VERSION_PUBLIEE.nom} --dir ${DOSSIER_TON_IA}`);
    expect(VERSION_PUBLIEE.adresse.endsWith(`/releases/tag/${VERSION_PUBLIEE.nom}`)).toBe(true);
    for (const c of DU_MODELE) expect(option(c, 'modele'), c).toBe(DOSSIER_TON_IA);
    // Le rapport corrigé du 17/11/2026, joint à la version publiée, et non son rapport.json d'origine.
    expect(option(commandes.EVALUATION_RESUMER_TON_IA, 'rapport')).toBe(`${DOSSIER_TON_IA}\\rapport-2026-11-17.json`);
  });

  it('resumer relit le rapport du relevé, daté du même jour', () => {
    // resumer recopie la date du rapport dans releve_le : le nom du rapport porte cette date.
    expect(option(commandes.EVALUATION_RESUMER_TON_IA, 'rapport')).toContain(lireEvaluation('ton-ia-1.5', RACINE)!.releve_le);
  });

  it('resumer, qcm-exemples, cartes et suivants sont des commandes du script, avec leurs options', () => {
    for (const sous of ['resumer', 'qcm-exemples', 'cartes', 'suivants']) expect(MAIN, sous).toContain(`add_parser("${sous}"`);
    // resumer prend --nom : sans lui, le relevé prendrait le nom du dossier de l'entraînement (« ton-ia »).
    expect(option(commandes.EVALUATION_RESUMER_TON_IA, 'nom')).toBe(VERSION_PUBLIEE.nom);
    expect(MAIN).toContain('resume.add_argument("--nom"');
    // Les commandes qui chargent un modèle prennent --modele (ajouter_modele), sur le processeur.
    expect(MAIN).toContain('"--modele",');
    for (const c of DU_MODELE) expect(option(c, 'appareil'), c).toBe('cpu');
    // cartes --choisir : le bloc et les deux têtes du chapitre 1.4, sans --couche ni --tete.
    expect(MAIN).toContain('"--choisir",');
    expect(commandes.EVALUATION_CARTES_TON_IA).toContain(' --choisir ');
    expect(commandes.EVALUATION_CARTES_TON_IA).not.toMatch(/--couche|--tete/);
    for (const c of [commandes.EVALUATION_RESUMER_TON_IA, ...DU_MODELE]) expect(c.startsWith('uv run --extra cpu '), c).toBe(true);
  });

  it('elles écrivent les fichiers que lisent les chapitres 1.6, 1.4 et 1.1', () => {
    const projet = 'projets/1.6-evaluation/';
    expect(`${projet}${option(commandes.EVALUATION_RESUMER_TON_IA, 'json')}`).toBe(FICHIERS_EVALUATION['ton-ia-1.5']);
    expect(`${projet}${option(commandes.EVALUATION_QCM_TON_IA, 'json')}`).toBe(FICHIERS_QCM['ton-ia-1.5']);
    expect(`${projet}${option(commandes.EVALUATION_CARTES_TON_IA, 'json')}`).toBe(FICHIERS_SORTIES_TON_IA.cartes);
    expect(`${projet}${option(commandes.EVALUATION_SUIVANTS_TON_IA, 'json')}`).toBe(FICHIERS_SORTIES_TON_IA.suivants);
  });

  it('leurs phrases sont celles des sorties que montrent les chapitres', () => {
    const cartes = lireCartes(RACINE);
    const suivants = lireSuivants(RACINE);
    expect(option(commandes.EVALUATION_CARTES_TON_IA, 'phrase')).toBe(cartes.phrase);
    expect(option(commandes.EVALUATION_SUIVANTS_TON_IA, 'phrase')).toBe(suivants.phrase);
    // Sans --k, suivants en garde 10 : ceux du tableau du chapitre 1.1.
    expect(commandes.EVALUATION_SUIVANTS_TON_IA).not.toContain('--k');
    expect(MAIN).toContain('suivant.add_argument("--k", type=int, default=10,');
    expect(suivants.suivants).toHaveLength(10);
  });

  it('ce sont les commandes du README du projet', () => {
    for (const c of [
      commandes.TELECHARGER_TON_IA,
      commandes.EVALUATION_RESUMER_TON_IA,
      commandes.EVALUATION_QCM_TON_IA,
      commandes.EVALUATION_CARTES_TON_IA,
      commandes.EVALUATION_SUIVANTS_TON_IA,
    ]) {
      expect(README, c).toContain(`${c}\n`);
    }
  });
});

// La vague 2 : les versions publiées de ton IA, et les commandes que leurs chapitres montrent.
describe('commandes de la vague 2', () => {
  const README_DE_FORGE = readFileSync(`${RACINE}/projets/forge/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  // Les commandes des chapitres 1.7 à 1.10 : chacune entre dans commandes.ts avec la parution de son chapitre.
  const COMMANDES_DES_CHAPITRES = [
    'AFFINER_1_7',
    'AFFINER_1_7_COURT',
    'REPRENDRE_1_7',
    'DISCUTER_1_7',
    'PREFERENCES_1_8',
    'DPO_1_8',
    'PROBLEMES_1_9',
    'SFT_1_9',
    'GRPO_1_9',
    'TRADUIRE_1_10',
    'CODE_1_10',
  ];

  it('TELECHARGER_VERSION est la commande de TELECHARGER_TON_IA, pour une autre étiquette', () => {
    expect(commandes.TELECHARGER_VERSION('ton-ia-1.5')).toBe(commandes.TELECHARGER_TON_IA);
    expect(commandes.TELECHARGER_VERSION('ton-ia-1.7')).toBe('gh release download ton-ia-1.7 --dir D:\\forge-ia-donnees\\cache\\ton-ia-1.7');
    expect(commandes.TELECHARGER_VERSION('ton-ia-1.10')).toBe('gh release download ton-ia-1.10 --dir D:\\forge-ia-donnees\\cache\\ton-ia-1.10');
    expect(commandes.TELECHARGER_VERSION('donnees-ton-ia-2')).toBe(
      'gh release download donnees-ton-ia-2 --dir D:\\forge-ia-donnees\\cache\\donnees-ton-ia-2',
    );
    const commande = commandes.TELECHARGER_VERSION('ton-ia-1.9');
    expect(commande).not.toMatch(/\n/);
    expect(commande).toBe(commande.trim());
  });

  it('refuse une étiquette qui n’est pas celle d’une Release de ton IA', () => {
    for (const mauvaise of ['', 'ton-ia', 'ton-ia-1.7 ; rm -r', 'v1.7', 'ton-ia-1.7\n']) {
      expect(() => commandes.TELECHARGER_VERSION(mauvaise), mauvaise).toThrow(/n’est pas l’étiquette d’une Release de ton IA/);
    }
  });

  it('chaque commande de chapitre qui existe se lit telle quelle dans le README de forge, sur une ligne', () => {
    for (const nom of COMMANDES_DES_CHAPITRES) {
      if (!(nom in commandes)) continue; // elle entre avec la parution de son chapitre (tâches 11 à 14)
      const commande = (commandes as Record<string, unknown>)[nom];
      expect(typeof commande, nom).toBe('string');
      expect(README_DE_FORGE, nom).toContain(commande as string);
    }
    // Seules ces commandes sont attendues : un autre nom en AFFINER_, DPO_… serait une faute de frappe.
    const attendues = new Set(COMMANDES_DES_CHAPITRES);
    // L'entrée dans le projet d'un chapitre (ALLER_AU_PROJET_1_7…) n'est pas une commande de forge.
    for (const nom of Object.keys(commandes)) {
      if (/_1_(7|8|9|10)(_COURT)?$/.test(nom) && !nom.startsWith('ALLER_AU_PROJET_')) expect(attendues.has(nom), nom).toBe(true);
    }
  });
});

// Le chapitre 1.7 : le projet de la conversation pas à pas (montrer, fuite, essai), vérifié contre le
// __main__.py et le README du projet, et contre les fichiers que lit le chapitre. Les commandes de forge
// (AFFINER_1_7…) entrent avec la parution du chapitre : elles sont vérifiées plus bas, avec la vague 2.
describe('commandes du chapitre 1.7', () => {
  const PROJET = `${RACINE}/projets/1.7-conversation`;
  const MAIN = readFileSync(`${PROJET}/conversation_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');

  it('les commandes, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_7).toBe('cd forge-ia/projets/1.7-conversation');
    expect(commandes.CONVERSATION_MONTRER).toBe(
      'uv run --extra cpu python -m conversation_pas_a_pas montrer "Quelle est la capitale de la France ?" --reponse "Paris."',
    );
    expect(commandes.CONVERSATION_FUITE).toBe(
      'uv run --extra cpu python -m conversation_pas_a_pas fuite --enregistrer sorties/fuite.txt --json mesures/fuite.json',
    );
    expect(commandes.CONVERSATION_ESSAI).toBe(
      'uv run --extra cpu python -m conversation_pas_a_pas essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json',
    );
    expect(commandes.CONVERSATION_TESTS).toBe('uv run --extra cpu pytest -q');
  });

  it('ce sont des commandes du script, avec leurs options, et celles du README du projet', () => {
    for (const [sous, commande, options] of [
      ['montrer', commandes.CONVERSATION_MONTRER, ['--reponse']],
      ['fuite', commandes.CONVERSATION_FUITE, ['--enregistrer', '--json']],
      ['essai', commandes.CONVERSATION_ESSAI, ['--appareil', '--enregistrer', '--json']],
    ] as const) {
      expect(MAIN).toContain(`add_parser("${sous}"`);
      for (const option of options) {
        expect(commande).toContain(`${option} `);
        expect(MAIN, `${sous} ${option}`).toMatch(new RegExp(`\\w+\\.add_argument\\("${option}"`));
      }
    }
    for (const c of [commandes.ALLER_AU_PROJET_1_7, commandes.CONVERSATION_MONTRER, commandes.CONVERSATION_FUITE, commandes.CONVERSATION_ESSAI, commandes.CONVERSATION_TESTS]) {
      expect(README, c).toContain(`${c}\n`);
    }
  });

  it('elles écrivent les sorties et les mesures que lit le chapitre', () => {
    const projet = 'projets/1.7-conversation/';
    const ecrit = (c: string, option: string) => `${projet}${new RegExp(`${option} (\\S+)`).exec(c)![1]}`;
    expect(ecrit(commandes.CONVERSATION_FUITE, '--enregistrer')).toBe(MESURES_PARTIE_1.sortieFuiteConversation);
    expect(ecrit(commandes.CONVERSATION_FUITE, '--json')).toBe(MESURES_PARTIE_1.fuiteConversation);
    expect(ecrit(commandes.CONVERSATION_ESSAI, '--enregistrer')).toBe(MESURES_PARTIE_1.sortieEssaiAffinage);
    expect(ecrit(commandes.CONVERSATION_ESSAI, '--json')).toBe(MESURES_PARTIE_1.essaiAffinage);
  });

  it('AFFINER_1_7, AFFINER_1_7_COURT et DISCUTER_1_7 : les commandes de forge du README de forge, chacune sur sa ligne', () => {
    const readme = readFileSync(`${RACINE}/projets/forge/README.md`, 'utf8').replace(/\r\n?/g, '\n');
    const mainDeForge = readFileSync(`${RACINE}/projets/forge/forge/__main__.py`, 'utf8');
    expect(commandes.AFFINER_1_7).toBe('uv run --extra gpu python -m forge entrainer --config configs/sft-1.7.toml');
    expect(commandes.AFFINER_1_7_COURT).toBe('uv run --extra gpu python -m forge entrainer --config configs/sft-1.7-court.toml');
    expect(commandes.DISCUTER_1_7).toBe(
      'uv run --extra gpu python -m forge discuter --modele "$env:FORGE_DONNEES\\publications\\ton-ia-1.7" --temperature 0.7',
    );
    for (const c of [commandes.AFFINER_1_7, commandes.AFFINER_1_7_COURT, commandes.DISCUTER_1_7]) {
      expect(readme.split('\n'), c).toContain(c);
      for (const [, option] of c.matchAll(/ (--[a-z-]+)/g)) {
        if (option !== '--extra') expect(mainDeForge, `${option} (${c})`).toContain(`"${option}"`);
      }
    }
    // Les configurations qu'elles lancent existent : la version publiée et sa version courte.
    for (const c of [commandes.AFFINER_1_7, commandes.AFFINER_1_7_COURT]) {
      expect(existsSync(`${RACINE}/projets/forge/${/--config (\S+)/.exec(c)![1]}`), c).toBe(true);
    }
  });
});

// Le chapitre 1.8 : le projet de l'alignement pas à pas (noter, dpo, pousser), vérifié contre le __main__.py et le
// README du projet ; et la commande de forge qui construit les paires de ton IA 1.8, dans le README de forge.
describe('commandes du chapitre 1.8', () => {
  const PROJET = `${RACINE}/projets/1.8-alignement`;
  const MAIN = readFileSync(`${PROJET}/alignement_pas_a_pas/__main__.py`, 'utf8').replace(/\r\n?/g, '\n');
  const README = readFileSync(`${PROJET}/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const README_DE_FORGE = readFileSync(`${RACINE}/projets/forge/README.md`, 'utf8').replace(/\r\n?/g, '\n');
  const MAIN_DE_FORGE = readFileSync(`${RACINE}/projets/forge/forge/__main__.py`, 'utf8');

  it('les commandes du projet, à l’identique', () => {
    expect(commandes.ALLER_AU_PROJET_1_8).toBe('cd forge-ia/projets/1.8-alignement');
    expect(commandes.ALIGNEMENT_NOTER).toBe(
      'uv run --extra cpu python -m alignement_pas_a_pas noter "paris est la capitale." --consigne minuscules --consigne mots_max:n=20',
    );
    expect(commandes.ALIGNEMENT_DPO).toBe('uv run --extra cpu python -m alignement_pas_a_pas dpo --pc -12 --pr -20 --qc -14 --qr -18 --beta 0.1');
    expect(commandes.ALIGNEMENT_POUSSER).toBe('uv run --extra cpu python -m alignement_pas_a_pas pousser --pas 40');
    expect(commandes.ALIGNEMENT_TESTS).toBe('uv run --extra cpu pytest -q');
  });

  it('ce sont des commandes du script, avec leurs options, et celles du README du projet', () => {
    for (const [sous, commande, options] of [
      ['noter', commandes.ALIGNEMENT_NOTER, ['--consigne']],
      ['dpo', commandes.ALIGNEMENT_DPO, ['--pc', '--pr', '--qc', '--qr', '--beta']],
      ['pousser', commandes.ALIGNEMENT_POUSSER, ['--pas']],
    ] as const) {
      expect(MAIN).toContain(`add_parser("${sous}"`);
      for (const option of options) {
        expect(commande).toContain(`${option} `);
        expect(MAIN, `${sous} ${option}`).toMatch(new RegExp(`\\w+\\.add_argument\\("${option}"`));
      }
    }
    for (const c of [commandes.ALLER_AU_PROJET_1_8, commandes.ALIGNEMENT_NOTER, commandes.ALIGNEMENT_DPO, commandes.ALIGNEMENT_POUSSER, commandes.ALIGNEMENT_TESTS]) {
      expect(README, c).toContain(`${c}\n`);
    }
  });

  it('PREFERENCES_1_8 : la commande de forge qui fait écrire les paires à ton IA 1.7, telle que le README de forge la donne', () => {
    expect(commandes.PREFERENCES_1_8).toBe(
      'uv run --extra gpu python -m forge preferences --modele "$env:FORGE_DONNEES\\publications\\ton-ia-1.7" --recette preferences-1.8',
    );
    expect(README_DE_FORGE).toContain(`${commandes.PREFERENCES_1_8}\n`);
    for (const [, option] of commandes.PREFERENCES_1_8.matchAll(/ (--[a-z-]+)/g)) {
      if (option === '--extra') continue; // l'option de uv
      expect(MAIN_DE_FORGE, option).toContain(`"${option}"`);
    }
  });

  it('DPO_1_8 attend que le README de forge donne la commande de l’entraînement de ton IA 1.8 (et sa configuration)', () => {
    // Tant que configs/dpo-1.8.toml n'existe pas, le README de forge ne la donne pas : le brouillon la dit en prose.
    if (!existsSync(`${RACINE}/projets/forge/configs/dpo-1.8.toml`)) expect('DPO_1_8' in commandes).toBe(false);
  });
});
