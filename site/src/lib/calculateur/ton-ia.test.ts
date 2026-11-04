// Le jumeau de forge : le calculateur refait trois choses de forge
// (largeur_cachee, nombre_parametres, estimer). Ce test lit le code source de
// forge sans l'importer (donc sans PyTorch), et vérifie les nombres que forge
// a écrits lui-même : ses tests, ses configurations, ses rapports de mesure.
// Si forge change une forme ou une formule, il échoue. On ne modifie jamais
// projets/forge.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { materiel } from './donnees';
import { efficaciteMesuree, operationsParJetonAvecAttention } from './formules';
import {
  CLES_FORGE,
  dureeHeures,
  JETONS_PAR_PARAMETRE,
  largeurCachee,
  MESURES_TON_IA,
  nombreParametres,
  NOMS_TAILLES,
  PAS_LARGEUR_CACHEE,
  PRESETS_FORGE,
  reperesTonIA,
  VOCABULAIRE_FORGE,
} from './ton-ia';

const FORGE = '../../../../projets/forge/';
// Fins de ligne ramenées à \n : la copie de travail peut avoir des CRLF (Windows), le dépôt a des LF.
const lire = (chemin: string): string => readFileSync(new URL(chemin, import.meta.url), 'utf8').replace(/\r\n/g, '\n');
const CONFIG_PY = `${FORGE}forge/modele/config.py`;
const MESURE_PY = `${FORGE}forge/mesure.py`;
const TEST_MODELE_PY = `${FORGE}tests/test_modele.py`;
const TEST_MESURE_PY = `${FORGE}tests/test_mesure.py`;
const PRINCIPAL_TOML = `${FORGE}configs/principal.toml`;
const MINI_TOML = `${FORGE}configs/mini.toml`;
const RAPPORT = '../../../../docs/mesures/entrainement-2026-11.md';
const RAPPORT_MINI = '../../../../docs/mesures/ton-ia-mini.md';

/** Les espaces insécables (U+00A0) et fines (U+202F) deviennent des espaces ordinaires. */
const sansInsecables = (texte: string): string => texte.replace(/[\u00A0\u202F]/g, ' ');

/**
 * Les lignes de code d'une fonction Python de premier niveau : de sa ligne
 * `def` à la prochaine ligne non indentée, sans la docstring, les commentaires
 * ni les lignes vides, chacune sans son indentation.
 */
function corpsDeFonction(source: string, nom: string): string[] {
  const lignes = source.split(/\r?\n/);
  const debut = lignes.findIndex((l) => l.startsWith(`def ${nom}(`));
  if (debut < 0) throw new Error(`def ${nom}( introuvable dans forge : la fonction a-t-elle changé de nom ?`);
  const corps: string[] = [];
  let dansDocstring = false;
  for (const ligne of lignes.slice(debut + 1)) {
    if (ligne.length > 0 && !/^\s/.test(ligne)) break;
    const t = ligne.trim();
    if (t.startsWith('"""')) {
      const fermeeSurLaLigne = t.length > 3 && t.endsWith('"""');
      if (!fermeeSurLaLigne) dansDocstring = !dansDocstring;
      continue;
    }
    if (dansDocstring || t === '' || t.startsWith('#')) continue;
    corps.push(t);
  }
  return corps;
}

describe('les formes et les constantes, lues dans le code de forge', () => {
  it('les cinq presets de forge/modele/config.py, dans le même ordre', () => {
    const config = lire(CONFIG_PY);
    const formes = [
      ...config.matchAll(/"(\w+)": ConfigModele\(dim=(\d+), couches=(\d+), tetes=(\d+), longueur_contexte=(\d+)\)/g),
    ];
    expect(formes).toHaveLength(5);
    expect(formes.map(([, n, d, c, t, l]) => [n, +d, +c, +t, +l])).toEqual(
      Object.entries(PRESETS_FORGE).map(([n, f]) => [n, f.dim, f.couches, f.tetes, f.contexte]),
    );
    expect(Object.keys(PRESETS_FORGE)).toEqual([...CLES_FORGE]);
  });

  it('les constantes : largeur cachée par pas de 64, 20 jetons par paramètre, vocabulaire de 32 768', () => {
    const config = lire(CONFIG_PY);
    expect(config).toContain('PAS_LARGEUR_CACHEE = 64');
    expect(PAS_LARGEUR_CACHEE).toBe(64);
    expect(readFileSync(new URL(MESURE_PY, import.meta.url), 'utf8')).toContain('JETONS_PAR_PARAMETRE = 20');
    expect(JETONS_PAR_PARAMETRE).toBe(20);
    expect(config).toContain('taille_vocabulaire: int = 32768');
    expect(VOCABULAIRE_FORGE).toBe(32_768);
    for (const f of Object.values(PRESETS_FORGE)) {
      expect(f.vocabulaire).toBe(VOCABULAIRE_FORGE);
      expect(f.tetesKv).toBe(f.tetes);
    }
  });

  it('les formules de forge n’ont pas changé (sinon, recopie-les ici et dans ton-ia.ts)', () => {
    const config = lire(CONFIG_PY);
    expect(corpsDeFonction(config, 'largeur_cachee')).toEqual([
      'multiples = (dim + 12) // 24',
      'return max(1, multiples) * PAS_LARGEUR_CACHEE',
    ]);
    expect(corpsDeFonction(config, 'nombre_parametres')).toEqual([
      'h = largeur_cachee(c.dim)',
      'plongement = c.taille_vocabulaire * c.dim',
      'attention = 4 * c.dim * c.dim',
      'mlp = 3 * c.dim * h',
      'normes = 2 * c.dim',
      'return plongement + c.couches * (attention + mlp + normes) + c.dim',
    ]);
    // estimer : la division et la garde sur le débit (le message d'erreur peut changer).
    expect(corpsDeFonction(lire(MESURE_PY), 'estimer').filter((l) => /^(if |jetons = |return )/.test(l))).toEqual([
      'if not jetons_par_seconde > 0:',
      'if jetons is None:',
      'jetons = JETONS_PAR_PARAMETRE * nombre_parametres(config)',
      'return jetons / jetons_par_seconde / 3600',
    ]);
  });
});

describe('largeurCachee et nombreParametres, sur les nombres écrits par forge', () => {
  it('les largeurs de forge/tests/test_modele.py', () => {
    for (const [d, h] of [
      [384, 1024],
      [512, 1344],
      [768, 2048],
      [1024, 2752],
      [1280, 3392],
      [36, 128],
      [12, 64],
    ]) {
      expect(largeurCachee(d)).toBe(h);
    }
    // Les mêmes, lues dans le fichier de test de forge.
    const assertions = [...lire(TEST_MODELE_PY).matchAll(/assert largeur_cachee\((\d+)\) == (\d+)/g)];
    expect(assertions.length).toBeGreaterThanOrEqual(7);
    for (const [, d, h] of assertions) expect(largeurCachee(+d), `largeur_cachee(${d})`).toBe(+h);
    // Jamais plus loin de 8/3 × dim que 32, comme le vérifie forge.
    for (let dim = 24; dim <= 2048; dim += 2) expect(Math.abs(largeurCachee(dim) - (8 * dim) / 3)).toBeLessThanOrEqual(32 + 1e-9);
  });

  it('les paramètres des cinq tailles : ceux du test de forge, du rapport « mini » et de principal.toml', () => {
    expect(PRESETS_FORGE.mini.parametres).toBe(23_204_736);
    expect(PRESETS_FORGE.tres_grand.parametres).toBe(433_573_120);
    // test_nombre_de_parametres_des_cinq_tailles : les valeurs exactes relevées par forge.
    const test = lire(TEST_MODELE_PY);
    const debut = test.indexOf('def test_nombre_de_parametres_des_cinq_tailles');
    expect(debut).toBeGreaterThan(0);
    const bloc = test.slice(debut, test.indexOf('\ndef ', debut + 1));
    const attendus = Object.fromEntries([...bloc.matchAll(/"(\w+)": ([\d_]+),/g)].map(([, n, v]) => [n, Number(v.replaceAll('_', ''))]));
    expect(Object.fromEntries(Object.entries(PRESETS_FORGE).map(([n, f]) => [n, f.parametres]))).toEqual(attendus);
    // docs/mesures/ton-ia-mini.md et configs/principal.toml.
    expect(sansInsecables(lire(RAPPORT_MINI))).toContain('« mini », 23 204 736 paramètres');
    const principal = /20 × ([\d ]+) = ([\d ]+)/.exec(sansInsecables(lire(PRINCIPAL_TOML)));
    expect(principal).not.toBeNull();
    const [, n, jetons] = principal ?? [];
    expect(Number(n.replaceAll(' ', ''))).toBe(PRESETS_FORGE.tres_grand.parametres);
    expect(Number(jetons.replaceAll(' ', ''))).toBe(JETONS_PAR_PARAMETRE * PRESETS_FORGE.tres_grand.parametres);
  });

  it('nombreParametres refuse une forme que forge refuserait', () => {
    const base = { tailleVocabulaire: 512, dim: 64, couches: 2, tetes: 4, longueurContexte: 32 };
    expect(nombreParametres(base)).toBe(512 * 64 + 2 * (4 * 64 * 64 + 3 * 64 * largeurCachee(64) + 2 * 64) + 64);
    expect(() => nombreParametres({ ...base, couches: 0 })).toThrow(/couches/);
    expect(() => nombreParametres({ ...base, dim: 60, tetes: 8 })).toThrow(/divisible/);
    expect(() => nombreParametres({ ...base, dim: 12, tetes: 4 })).toThrow(/pair/);
    expect(() => largeurCachee(0)).toThrow(/dim/);
    expect(() => largeurCachee(1.5)).toThrow(/dim/);
  });
});

describe('dureeHeures, comme forge.mesure.estimer', () => {
  it('jetons ÷ débit ÷ 3 600, et les attendus de forge/tests/test_mesure.py', () => {
    expect(dureeHeures(20 * 433_573_120, 17_855)).toBeCloseTo(134.9, 1);
    const cas = [...lire(TEST_MESURE_PY).matchAll(/estimer\(MODELE_MINUSCULE, ([\d.]+), ([\d_]+)\) == pytest\.approx\(([\d.]+)\)/g)];
    expect(cas.length).toBeGreaterThanOrEqual(2);
    for (const [, debit, jetons, heures] of cas) {
      expect(dureeHeures(Number(jetons.replaceAll('_', '')), Number(debit))).toBeCloseTo(Number(heures), 12);
    }
  });

  it('un débit qui n’est pas plus grand que 0 est une erreur, comme dans forge', () => {
    for (const debit of [0, -1, NaN]) expect(() => dureeHeures(1000, debit), String(debit)).toThrow(/débit/);
  });
});

describe('les mesures de ton IA sur ce PC', () => {
  it('l’efficacité implicite : 52,8 % avec 6N, 65,6 % en comptant l’attention', () => {
    expect(efficaciteMesuree(433_573_120, 17_855, 87.9)).toBeCloseTo(0.528, 3);
    expect((17_855 * operationsParJetonAvecAttention(PRESETS_FORGE.tres_grand)) / 87.9e12).toBeCloseTo(0.656, 3);
  });

  it('les débits recopiés sont ceux des rapports (docs/mesures et configs/mini.toml)', () => {
    const rapport = lire(RAPPORT).replace(/[\u00A0\u202F]/g, ' ');
    for (const v of ['138 433', '62 368', '32 704', '17 855', '1 749', '776', '404', '235', '10,9 Go']) expect(rapport).toContain(v);
    // Chaque ligne du tableau de la carte : taille, micro-lot le plus rapide, débit, pic de mémoire.
    for (const cle of ['petit', 'moyen', 'grand', 'tres_grand'] as const) {
      const m = MESURES_TON_IA[cle];
      const debit = m.carte.jetonsParSeconde.toLocaleString('fr-FR').replace(/\s/g, ' ');
      const memoire = m.carte.memoireGo.toLocaleString('fr-FR');
      expect(rapport, cle).toMatch(new RegExp(`\\| ${cle} \\|[^\\n]*\\| ${m.carte.microLot} \\| ${debit} \\| ${memoire} Go \\|\\n`));
      const cpu = m.processeur.jetonsParSeconde.toLocaleString('fr-FR').replace(/\s/g, ' ');
      expect(rapport, cle).toMatch(new RegExp(`\\| ${cle} \\| 16 \\| 2 \\| \\d+ \\| ${cpu} \\|`));
    }
    // Les commentaires de mini.toml passent à la ligne : on les remet bout à bout.
    const mini = sansInsecables(lire(MINI_TOML)).replace(/\n# /g, ' ');
    expect(mini).toContain('le micro-lot le plus rapide est 16 (231 934 jetons par seconde');
    expect(mini).toContain('2 707 jetons par seconde pour le processeur');
    expect(mini).toContain('16 (le plus rapide mesuré, 4,4 Go de mémoire)');
  });

  it('les valeurs du plan', () => {
    const resume = CLES_FORGE.map((cle) => {
      const m = MESURES_TON_IA[cle];
      return [cle, m.carte.jetonsParSeconde, m.carte.microLot, m.carte.memoireGo, m.processeur.jetonsParSeconde];
    });
    expect(resume).toEqual([
      ['mini', 231_934, 16, 4.4, 2707],
      ['petit', 138_433, 4, 5.5, 1749],
      ['moyen', 62_368, 2, 5.4, 776],
      ['grand', 32_704, 2, 9.1, 404],
      ['tres_grand', 17_855, 1, 10.9, 235],
    ]);
    for (const cle of CLES_FORGE) {
      expect(MESURES_TON_IA[cle].source.releveLe).toBe('2026-11-03');
      expect(MESURES_TON_IA[cle].source.url).toMatch(/^https:\/\/github\.com\/chipat-neko\/forge-ia\/blob\/main\//);
    }
    expect(MESURES_TON_IA.mini.source.url).toMatch(/configs\/mini\.toml$/);
    expect(MESURES_TON_IA.tres_grand.source.url).toMatch(/docs\/mesures\/entrainement-2026-11\.md$/);
  });

  it('le tableau des repères : débits, durées pour 20 jetons par paramètre, efficacités', () => {
    const reperes = reperesTonIA();
    expect(reperes.map((r) => r.cle)).toEqual([...CLES_FORGE]);
    const tg = reperes[4];
    expect(tg.nom).toBe(NOMS_TAILLES.tres_grand);
    expect(tg.parametres).toBe(433_573_120);
    expect(tg.jetons).toBe(20 * 433_573_120);
    expect(tg.carte.heures).toBe(dureeHeures(20 * 433_573_120, 17_855));
    expect(tg.carte.efficacite).toBe(efficaciteMesuree(433_573_120, 17_855, materiel('rtx-5070-ti').creteTflops));
    expect(tg.carte.efficaciteAvecAttention).toBeCloseTo(0.656, 3);
    expect(tg.processeur.heures).toBe(dureeHeures(20 * 433_573_120, 235));
    // Le rapport écrit 10 235 h : il part du débit avant arrondi (235,3 jetons par seconde).
    expect(Math.abs(tg.processeur.heures / 10_235 - 1)).toBeLessThan(0.002);
    // Les durées du rapport : 1,7 h, 9,8 h, 40,1 h et 135 h sur la carte.
    expect(reperes.slice(1).map((r) => Math.round(r.carte.heures * 10) / 10)).toEqual([1.7, 9.8, 40.1, 134.9]);
  });
});
