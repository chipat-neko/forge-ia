// Le chapitre 0.3 lit le diagnostic de son projet dans les attendus du Python
// (projets/0.3-poste/tests/attendus.json) : il ne refait pas le diagnostic. Ces
// tests vérifient qu'il les lit tels quels, que le tableau des situations et
// l'ouverture en viennent, que les commandes conseillées par le script sont
// celles de commandes.ts, et que les faits sourcés de la recherche (Colab,
// capacités des cartes, Llama 3) disent la même chose que les attendus et que
// les données du calculateur.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { REPERES_EFFICACITE } from '../calculateur/donnees';
import { formaterDate } from '../calculateur/formats';
import { nombre } from '../nombres';
import { lireSortie } from '../sorties';
import * as commandes from './commandes';
import { ATTENDUS_POSTE, constat, situation } from './poste';
import {
  architectureQuiSert,
  capaciteArchitecture,
  CONSTATS_HORS_TABLEAU,
  decrireSituation,
  ligneDuRapport,
  lignesDuRapport,
  lignesDesSituations,
  morceaux,
  NOMS_DES_SITUATIONS,
  nomArchitecture,
  RIEN_A_FAIRE,
  texteDesMorceaux,
  trouverSituation,
  type AttendusPoste,
} from './situations-0-3';
import {
  CAPACITES,
  CARTES_LLAMA_3_405B,
  COLAB,
  enGo,
  enMo,
  MACOS_MINIMUM,
  OCTETS_ROUE_CU132_WINDOWS,
  OCTETS_ROUE_PYPI_WINDOWS,
  PILOTE_MINIMUM_CUDA_13,
  SOURCES_0_3,
} from './sources-0-3';

const FINE = '\u202F';
// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const FICHIER = JSON.parse(readFileSync(`${RACINE}/projets/0.3-poste/tests/attendus.json`, 'utf8')) as AttendusPoste;
const SORTIE_PROCESSEUR = readFileSync(`${RACINE}/projets/0.3-poste/sorties/processeur.txt`, 'utf8');

describe('situation(nom) : les attendus du Python, tels quels', () => {
  it('rend les faits et les constats écrits par le Python', () => {
    for (const [nom, attendue] of FICHIER.situations) {
      expect(situation(nom), nom).toStrictEqual(attendue);
    }
    expect(ATTENDUS_POSTE).toStrictEqual(FICHIER);
  });

  it('les sept situations, dans l’ordre de SITUATIONS (diagnostic.py)', () => {
    expect(FICHIER.situations.map(([nom]) => nom)).toEqual([...NOMS_DES_SITUATIONS]);
    expect(NOMS_DES_SITUATIONS).toHaveLength(7);
  });

  it('un nom absent lève une erreur qui dit quoi faire', () => {
    expect(() => situation('windows_rtx9090')).toThrow(
      /«\u202Fwindows_rtx9090\u202F» n’est pas dans projets\/0\.3-poste\/tests\/attendus\.json.*windows_cu132_rtx5070ti.*régénère/,
    );
    expect(() => trouverSituation({ situations: [] }, 'sans_carte')).toThrow('sans_carte');
    expect(() => constat('sans_carte', 'carte_prete')).toThrow(/carte_prete.*sans_carte/);
  });

  it('les paires du chapitre : la roue de PyPI, la carte trop récente, la carte prête', () => {
    const cles = (nom: string) => situation(nom).constats.map((c) => c.cle);
    expect(cles('windows_pypi_rtx5070ti')).toEqual(['roue_processeur']);
    expect(cles('windows_cu126_rtx5070ti')).toEqual(['carte_trop_recente']);
    expect(cles('windows_cu132_rtx5070ti')).toEqual(['carte_prete']);
    expect(cles('fils_par_defaut')).toEqual(['carte_prete', 'fils']);
  });
});

describe('le rapport du script', () => {
  it('ligneDuRapport écrit un constat comme le script : la ligne est dans sorties/processeur.txt', () => {
    // Ce PC, avec la version de PyTorch pour le processeur : le constat de la situation PyPI, mot pour mot.
    const roue = constat('windows_pypi_rtx5070ti', 'roue_processeur');
    expect(SORTIE_PROCESSEUR.split('\n')).toContain(ligneDuRapport(roue));
    expect(ligneDuRapport(roue)).toBe(`  attention${FINE}: ${roue.message}`);
    expect(ligneDuRapport(constat('pilote_ancien', 'pilote_trop_ancien'))).toMatch(/^ {2}problème\u202F: /);
  });

  it('lignesDuRapport : le constat et son « À faire », lignes consécutives de la sortie de ce PC', () => {
    const sortie = SORTIE_PROCESSEUR.split('\n');
    for (const c of [constat('windows_pypi_rtx5070ti', 'roue_processeur'), constat('fils_par_defaut', 'fils')]) {
      const lignes = lignesDuRapport(c);
      expect(lignes).toHaveLength(2);
      const i = sortie.indexOf(lignes[0]);
      expect(i, c.cle).toBeGreaterThanOrEqual(0);
      expect(sortie.slice(i, i + 2), c.cle).toEqual(lignes);
    }
    // Un constat sans rien à faire n'a qu'une ligne.
    expect(lignesDuRapport(constat('windows_cu132_rtx5070ti', 'carte_prete'))).toHaveLength(1);
  });

  it('l’ouverture : le constat « carte_prete » de la RTX 5070 Ti, avec la version du projet', () => {
    const prete = constat('windows_cu132_rtx5070ti', 'carte_prete');
    expect(prete.message).toBe(
      'PyTorch 2.15.0+cu132 voit ta carte, NVIDIA GeForce RTX 5070 Ti (capacité 12.0), et sait calculer dessus.',
    );
    expect(ligneDuRapport(prete)).toBe(`  bon${FINE}: ${prete.message}`);
  });

  it('les fils : 16 dans le processeur, 8 pour PyTorch par défaut, comme dans la sortie de ce PC', () => {
    const { fils_processeur, fils_torch } = situation('fils_par_defaut').faits;
    expect([fils_processeur, fils_torch]).toEqual([16, 8]);
    expect(SORTIE_PROCESSEUR).toContain(`Fils du processeur${FINE}: ${fils_processeur}, dont ${fils_torch} utilisés par PyTorch`);
  });
});

describe('le tableau des situations', () => {
  const lignes = lignesDesSituations(FICHIER);

  it('une ligne par situation, dans l’ordre, avec ses constats tels quels', () => {
    expect(lignes.map((l) => l.nom)).toEqual([...NOMS_DES_SITUATIONS]);
    for (const [i, [nom, s]] of FICHIER.situations.entries()) {
      const ligne = lignes[i];
      expect(ligne.constats, nom).toHaveLength(s.constats.length);
      for (const [j, c] of s.constats.entries()) {
        // Les messages du Python sont déjà typographiés : seuls les accents graves deviennent du code.
        expect(texteDesMorceaux(ligne.constats[j].message), nom).toBe(c.message.replaceAll('`', ''));
        expect(texteDesMorceaux(ligne.constats[j].aFaire), nom).toBe(c.a_faire === null ? RIEN_A_FAIRE : c.a_faire.replaceAll('`', ''));
        expect(ligne.constats[j].cle).toBe(c.cle);
      }
    }
    expect(lignes[0].constats[0].niveau).toBe('bon');
    expect(lignes[3].constats[0].niveau).toBe('problème');
  });

  it('chaque situation est décrite d’après ses faits', () => {
    const texte = (nom: string) => texteDesMorceaux(lignes[NOMS_DES_SITUATIONS.indexOf(nom as never)].situation);
    expect(texte('windows_cu132_rtx5070ti')).toBe('Windows 11, RTX 5070 Ti, PyTorch 2.15.0+cu132 (la version du projet)');
    expect(texte('windows_pypi_rtx5070ti')).toBe('La même carte, avec pip install torch, qui donne PyTorch 2.15.0+cpu');
    expect(texte('windows_cu126_rtx5070ti')).toBe('La même carte, avec PyTorch 2.7.1+cu126, d’un ancien tutoriel');
    expect(texte('pilote_ancien')).toBe('Un pilote 551.86, qui va jusqu’à CUDA 12.4');
    expect(texte('sans_carte')).toBe('Un PC sans carte NVIDIA, avec PyTorch 2.15.0+cpu');
    // La T4 est celle que rapportent les utilisateurs de Colab : Google ne la nomme pas (point mis de côté à la tâche 9, N1).
    expect(texte('colab_t4')).toBe('Colab, avec la Tesla T4 que rapportent ses utilisateurs, et son PyTorch 2.14.1+cu130');
    expect(texte('fils_par_defaut')).toBe('La RTX 5070 Ti prête, mais PyTorch réglé par défaut');
    expect(() => decrireSituation('inconnue', situation('sans_carte').faits)).toThrow(/DESCRIPTIONS/);
  });

  it('la ligne de Colab ne montre ni le pilote ni les fils, qui sont des exemples non sourcés', () => {
    const { faits } = situation('colab_t4');
    const ligne = lignes[NOMS_DES_SITUATIONS.indexOf('colab_t4')];
    const tout = [ligne.situation, ...ligne.constats.flatMap((c) => [c.message, c.aFaire])].map(texteDesMorceaux).join(' ');
    expect(tout).not.toContain(faits.pilote!);
    expect(tout).not.toContain('fils');
    expect(tout).not.toContain(`CUDA ${faits.cuda_max_pilote}`);
  });

  it('morceaux : le code entre accents graves, le reste typographié', () => {
    expect(morceaux("Lance `uv sync --extra gpu` : c'est tout")).toEqual([
      { texte: 'Lance ', code: false },
      { texte: 'uv sync --extra gpu', code: true },
      { texte: `${FINE}: c’est tout`, code: false },
    ]);
  });
});

describe('les constats du diagnostic', () => {
  it('ceux du tableau et ceux hors du tableau font exactement ceux de diagnostic.py', () => {
    const source = readFileSync(`${RACINE}/projets/0.3-poste/poste/diagnostic.py`, 'utf8');
    // Les clés de constat_pour, une par « if cle == "…" », dans l'ordre du fichier.
    const duDiagnostic = [...source.matchAll(/^ {4}if cle == "(\w+)":$/gm)].map(([, cle]) => cle);
    expect(duDiagnostic).toContain('carte_prete');
    expect(new Set(duDiagnostic).size, 'une clé écrite deux fois dans diagnostic.py').toBe(duDiagnostic.length);
    const duTableau = new Set(FICHIER.situations.flatMap(([, s]) => s.constats.map((c) => c.cle)));
    const horsTableau = CONSTATS_HORS_TABLEAU.map((c) => c.cle);
    for (const cle of horsTableau) expect(duTableau.has(cle), `${cle} est aussi au tableau`).toBe(false);
    expect([...duTableau, ...horsTableau].sort()).toEqual([...duDiagnostic].sort());
    // Dans l'ordre où diagnostiquer les rencontre.
    expect(horsTableau).toEqual(duDiagnostic.filter((cle) => !duTableau.has(cle)));
  });
});

describe('les commandes que conseille le script', () => {
  it('chaque commande uv entre accents graves des attendus est une commande de commandes.ts', () => {
    const connues = new Set(Object.values(commandes));
    const vues = new Set(
      FICHIER.situations.flatMap(([, s]) =>
        s.constats.flatMap((c) => [...`${c.message} ${c.a_faire ?? ''}`.matchAll(/`(uv [^`]*)`/g)].map(([, cmd]) => cmd)),
      ),
    );
    expect(vues.size).toBeGreaterThan(0);
    for (const commande of vues) expect(connues, commande).toContain(commande);
  });
});

describe('la règle des générations', () => {
  it('nomArchitecture : (12, 0) donne sm_120, (7, 5) donne sm_75', () => {
    expect(nomArchitecture([12, 0])).toBe('sm_120');
    expect(nomArchitecture([7, 5])).toBe('sm_75');
  });

  it('même génération, mineure plus petite ou égale : sm_86 sert une carte de capacité 8.9', () => {
    const projet = situation('windows_cu132_rtx5070ti').faits.architectures;
    expect(projet).not.toContain('sm_89');
    expect(architectureQuiSert(CAPACITES['RTX 4070'], projet)).toBe('sm_86');
    expect(architectureQuiSert([12, 0], projet)).toBe('sm_120');
    expect(architectureQuiSert([6, 1], projet)).toBeNull();
    // La H100 de Llama 3, capacité 9.0 : servie par sm_90.
    expect(architectureQuiSert(CAPACITES.H100, projet)).toBe('sm_90');
    expect(architectureQuiSert([12, 0], ['compute_90'])).toBe('compute_90');
    expect(architectureQuiSert([8, 6], ['compute_90'])).toBeNull();
  });

  it('capaciteArchitecture lit la capacité d’un nom d’architecture', () => {
    expect(capaciteArchitecture('sm_90')).toEqual([9, 0]);
    expect(capaciteArchitecture('sm_120')).toEqual([12, 0]);
    expect(capaciteArchitecture('sm_90a')).toEqual([9, 0]);
    expect(capaciteArchitecture('compute_75')).toEqual([7, 5]);
    expect(capaciteArchitecture('gfx90a')).toBeNull();
  });

  it('elle dit la même chose que le diagnostic sur chaque carte vue par PyTorch', () => {
    for (const [nom, { faits, constats }] of FICHIER.situations) {
      if (!faits.cuda_disponible || faits.capacite === null) continue;
      const refusee = constats.some((c) => c.cle === 'carte_trop_recente' || c.cle === 'carte_trop_ancienne');
      expect(architectureQuiSert(faits.capacite, faits.architectures) === null, nom).toBe(refusee);
    }
  });
});

describe('les faits sourcés de la recherche', () => {
  it('chaque source a son titre, une adresse https et une date de vérification du calendrier', () => {
    const toutes = Object.values(SOURCES_0_3).flat();
    expect(toutes.length).toBeGreaterThan(10);
    for (const s of toutes) {
      expect(s.titre.length, s.url).toBeGreaterThan(0);
      expect(s.url).toMatch(/^https:\/\//);
      expect(() => formaterDate(s.verifieLe), s.url).not.toThrow();
    }
  });

  it('Colab : les versions de son image avec carte sont celles de la situation colab_t4', () => {
    const { faits } = situation('colab_t4');
    expect(faits.python).toBe(COLAB.avecCarte.python);
    expect(faits.torch).toBe(COLAB.avecCarte.torch);
    expect(COLAB.avecCarte).toEqual({ python: '3.13.16', torch: '2.14.1+cu130' });
    expect(COLAB.sansCarte).toEqual({ python: '3.13.18', torch: '2.14.1+cpu' });
    expect(COLAB.heuresMax).toBe(12);
  });

  it('les capacités de NVIDIA sont celles des attendus', () => {
    expect(situation('windows_cu132_rtx5070ti').faits.capacite).toEqual([...CAPACITES['RTX 5070 Ti']]);
    expect(situation('colab_t4').faits.capacite).toEqual([...CAPACITES.T4]);
    expect(CAPACITES['RTX 4070']).toEqual([8, 9]);
    expect(CAPACITES.H100).toEqual([9, 0]);
  });

  it('le pilote 580 de NVIDIA est la série que le diagnostic donne en exemple', () => {
    expect(PILOTE_MINIMUM_CUDA_13).toBe(580);
    // Le pilote trop ancien des attendus est d'une série plus ancienne que 580.
    expect(Number(situation('pilote_ancien').faits.pilote!.split('.')[0])).toBeLessThan(PILOTE_MINIMUM_CUDA_13);
  });

  it('Llama 3 405B : jusqu’à 16 384 H100, comme dans les repères d’efficacité du calculateur', () => {
    expect(CARTES_LLAMA_3_405B).toBe(16_384);
    const llama = REPERES_EFFICACITE.find((r) => r.modele === 'Llama 3 405B');
    expect(llama?.materiel).toContain(`${nombre(CARTES_LLAMA_3_405B)} H100`);
  });

  it('les roues de PyTorch 2.15.0 sous Windows : 126,7 Mo sur PyPI, 2,1 Go pour CUDA 13.2', () => {
    expect(enMo(OCTETS_ROUE_PYPI_WINDOWS)).toBe('126,7\u00A0Mo');
    expect(enGo(OCTETS_ROUE_CU132_WINDOWS)).toBe('2,1\u00A0Go');
    expect(MACOS_MINIMUM).toBe('14');
  });

  it('la sortie du processeur est lue telle quelle, sans sa ligne de date', () => {
    expect(lireSortie(SORTIE_PROCESSEUR, 'processeur.txt')?.releveLe).toBe('2026-11-05');
  });
});
