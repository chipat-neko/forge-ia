// Le jumeau TypeScript de la marge et du verdict retrouve exactement la grille du Python
// (projets/1.6-evaluation/tests/attendus.json) ; les relevés de « mini » se lisent, se vérifient, et
// disent ce que dit docs/mesures/ton-ia-mini.md.

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  CLES_DES_VERSIONS,
  FICHIERS_EVALUATION,
  FICHIERS_QCM,
  lireEchantillon,
  lireEvaluation,
  lireQcm,
  marge95,
  margeHasard,
  QUI_EST_EVALUE,
  verdictQcm,
  verifierEvaluation,
  verifierQcm,
} from './evaluation';
import type { Evaluation, QcmExemples } from './evaluation';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';

interface CasAttendu {
  exactitude: number;
  n: number;
  choix: number;
  marge_95: number;
  hasard: number;
  marge_hasard: number;
  verdict: string;
}

const ATTENDUS = JSON.parse(readFileSync('../projets/1.6-evaluation/tests/attendus.json', 'utf8')) as CasAttendu[];

describe('le jumeau de la marge et du verdict', () => {
  it('lit une grille non vide, avec les trois verdicts', () => {
    expect(ATTENDUS.length).toBeGreaterThan(50);
    expect(new Set(ATTENDUS.map((c) => c.verdict))).toStrictEqual(new Set(['au-dessus', 'pas-different', 'en-dessous']));
  });

  it('retrouve exactement la marge de la mesure du Python', () => {
    for (const c of ATTENDUS) expect(marge95(c.exactitude, c.n), `${c.exactitude} sur ${c.n}`).toStrictEqual(c.marge_95);
  });

  it('retrouve exactement le hasard et sa marge', () => {
    for (const c of ATTENDUS) {
      expect(1 / c.choix, `${c.choix} choix`).toStrictEqual(c.hasard);
      expect(margeHasard(c.n, c.choix), `${c.n} questions à ${c.choix} choix`).toStrictEqual(c.marge_hasard);
    }
  });

  it('retrouve exactement le verdict du Python', () => {
    for (const c of ATTENDUS) {
      expect(verdictQcm(c.exactitude, c.hasard, c.marge_hasard), `${c.exactitude} sur ${c.n}, ${c.choix} choix`).toBe(c.verdict);
    }
  });

  it('la marge de la mesure s’annule aux extrêmes, pas celle du hasard', () => {
    expect(marge95(0, 5)).toBe(0);
    expect(marge95(1, 5)).toBe(0);
    expect(margeHasard(5, 4)).toBeGreaterThan(0.3);
    // 0 bonne réponse sur 5 à 4 choix : un quart du temps, au hasard.
    expect(verdictQcm(0, 0.25, margeHasard(5, 4))).toBe('pas-different');
  });

  it('le hasard par défaut est celui de quatre choix', () => {
    expect(margeHasard(100)).toBe(margeHasard(100, 4));
  });
});

describe('les relevés de « mini »', () => {
  it('lisent l’évaluation, qui dit ce que dit le document', () => {
    const evaluation = lireEvaluation('ton-ia-mini', RACINE);
    expect(evaluation).not.toBeNull();
    const e = evaluation!;
    const document = readFileSync('../docs/mesures/ton-ia-mini.md', 'utf8').replace(/[\u202F\u00a0]/g, ' ');
    const virgule = (x: number, decimales: number): string => x.toFixed(decimales).replace('.', ',');
    expect(e.nom).toBe('ton-ia-mini');
    expect(e.pas).toBe(6370);
    expect(document).toContain(`perplexité **${virgule(e.perplexite, 1)}**`);
    expect(document).toContain(`**${virgule(e.bits_par_octet, 3)} bit par octet**`);
    expect(document).toContain(`HellaSwag ${virgule(100 * e.qcm.hellaswag.exactitude_normalisee, 1)} %`);
    expect(document).toContain(`ARC-Challenge ${virgule(100 * e.qcm.arc.exactitude_normalisee, 1)} %`);
    expect(e.qcm.hellaswag.verdict).toBe('au-dessus');
    expect(e.qcm.arc.verdict).toBe('pas-different');
    expect(e.echantillons).toHaveLength(10);
  });

  it('lisent les QCM de MMMLU, avec leur licence et leur adresse', () => {
    const qcm = lireQcm('ton-ia-mini', RACINE);
    expect(qcm).not.toBeNull();
    expect(qcm!.jeu.licence).toBe('MIT');
    expect(qcm!.jeu.adresse).toBe('https://huggingface.co/datasets/openai/MMMLU');
    expect(qcm!.jeu.configuration).toBe('FR_FR');
    expect(qcm!.n).toBe(6);
    expect(qcm!.appareil).toBe('cpu');
  });

  it('rendent l’échantillon d’une invite', () => {
    const e = lireEchantillon('ton-ia-mini', 'La capitale de la France est', RACINE);
    expect(e).not.toBeNull();
    expect(e!.suite.length).toBeGreaterThan(50);
    expect(e!.n_jetons).toBe(60);
    expect(() => lireEchantillon('ton-ia-mini', 'Une invite qui n’existe pas', RACINE)).toThrow(/aucun échantillon ne part de/);
  });

  it('gardent leurs chemins', () => {
    expect(FICHIERS_EVALUATION['ton-ia-mini']).toBe('projets/1.6-evaluation/mesures/evaluation-mini.json');
    expect(FICHIERS_QCM['ton-ia-mini']).toBe('projets/1.6-evaluation/mesures/qcm-mini.json');
    // Ton IA, la vraie : les relevés que la tâche 15 du plan 5 écrira, lus par le chapitre 1.6 (« à mesurer » d'ici là).
    expect(FICHIERS_EVALUATION['ton-ia-1.5']).toBe('projets/1.6-evaluation/mesures/evaluation-1.5.json');
    expect(FICHIERS_QCM['ton-ia-1.5']).toBe('projets/1.6-evaluation/mesures/qcm-1.5.json');
  });

  it('les deux versions évaluées par le chapitre : leur relevé et leur nom', () => {
    expect(CLES_DES_VERSIONS).toStrictEqual({ mini: 'ton-ia-mini', '1.5': 'ton-ia-1.5' });
    for (const cle of Object.values(CLES_DES_VERSIONS)) expect(FICHIERS_EVALUATION[cle]).toBeDefined();
    expect(QUI_EST_EVALUE).toStrictEqual({ mini: 'la version d’une heure de ton IA', '1.5': 'ton IA' });
  });

  it('marge.ts, sans import, est le jumeau que réexporte evaluation.ts', async () => {
    const marge = await import('./marge');
    expect(marge95).toBe(marge.marge95);
    expect(margeHasard).toBe(marge.margeHasard);
    expect(verdictQcm).toBe(marge.verdictQcm);
    expect(readFileSync('src/lib/partie-1/marge.ts', 'utf8')).not.toMatch(/^import /m);
  });
});

describe('lireEvaluation, lireQcm et lireEchantillon dans un dépôt de passage', () => {
  const dossiers: string[] = [];
  afterAll(() => {
    for (const d of dossiers) rmSync(d, { recursive: true, force: true });
  });

  /** Un faux dépôt avec le dossier du projet (et, si on le donne, le fichier du relevé). */
  function fauxDepot(fichiers: Record<string, unknown> = {}): string {
    const racine = mkdtempSync(join(tmpdir(), 'evaluation-'));
    dossiers.push(racine);
    mkdirSync(join(racine, 'projets/1.6-evaluation/mesures'), { recursive: true });
    for (const [chemin, contenu] of Object.entries(fichiers)) {
      writeFileSync(join(racine, chemin), typeof contenu === 'string' ? contenu : JSON.stringify(contenu), 'utf8');
    }
    return racine;
  }

  it('rendent null quand le fichier manque', () => {
    const racine = fauxDepot();
    expect(lireEvaluation('ton-ia-mini', racine)).toBeNull();
    expect(lireQcm('ton-ia-mini', racine)).toBeNull();
    expect(lireEchantillon('ton-ia-mini', 'Il était une fois', racine)).toBeNull();
  });

  it('refusent une racine qui n’est pas celle du dépôt', () => {
    const racine = mkdtempSync(join(tmpdir(), 'pas-un-depot-'));
    dossiers.push(racine);
    expect(() => lireEvaluation('ton-ia-mini', racine)).toThrow(/n’a pas de dossier projets\/1\.6-evaluation/);
    expect(() => lireQcm('ton-ia-mini', racine)).toThrow(/n’a pas de dossier projets\/1\.6-evaluation/);
  });

  it('refusent un JSON illisible, en nommant le fichier', () => {
    const racine = fauxDepot({ [FICHIERS_EVALUATION['ton-ia-mini']]: '{ pas du json' });
    expect(() => lireEvaluation('ton-ia-mini', racine)).toThrow(/evaluation-mini\.json.*JSON illisible/);
  });

  it('acceptent une racine donnée en URL file:', () => {
    const racine = fauxDepot();
    expect(lireEvaluation('ton-ia-mini', new URL(`file:///${racine.replace(/\\/g, '/')}/`))).toBeNull();
  });
});

describe('verifierEvaluation', () => {
  const lu = (): Evaluation => JSON.parse(readFileSync('../' + FICHIERS_EVALUATION['ton-ia-mini'], 'utf8')) as Evaluation;
  const verifie = (modifie: (e: Evaluation) => void): (() => unknown) => {
    const e = lu();
    modifie(e);
    return () => verifierEvaluation(e, 'evaluation-essai.json');
  };

  it('accepte le relevé de mini', () => {
    expect(() => verifierEvaluation(lu(), 'evaluation-mini.json')).not.toThrow();
  });

  it('refuse ce qui n’est pas un relevé, en disant quoi faire', () => {
    expect(() => verifierEvaluation([], 'evaluation-essai.json')).toThrow(/evaluation-essai\.json.*pas un objet JSON.*python -m evaluation_pas_a_pas/);
    expect(verifie((e) => { e.nom = ''; })).toThrow(/nom est vide/);
    expect(verifie((e) => { e.releve_le = '3/11/2026'; })).toThrow(/releve_le doit être une date/);
    expect(verifie((e) => { e.pas = 0; })).toThrow(/pas doit être un entier/);
    expect(verifie((e) => { e.perte_val = -1; })).toThrow(/perte_val doit être un nombre positif/);
  });

  it('refuse une perplexité qui n’est pas exp(perte)', () => {
    expect(verifie((e) => { e.perplexite = 12; })).toThrow(/n’est pas exp\(perte_val\)/);
  });

  it('refuse un test absent ou des nombres hors des bornes', () => {
    expect(verifie((e) => { delete (e.qcm as Partial<Evaluation['qcm']>).arc; })).toThrow(/qcm\.arc manque/);
    expect(verifie((e) => { e.qcm.arc.hasard = 1.5; })).toThrow(/qcm\.arc\.hasard doit être une proportion/);
    expect(verifie((e) => { e.qcm.arc.marge_hasard = -1; })).toThrow(/qcm\.arc\.marge_hasard doit être un nombre positif ou nul/);
    expect(verifie((e) => { e.qcm.arc.n = e.qcm.arc.total_du_test + 1; })).toThrow(/total_du_test/);
  });

  it('refuse une marge qui n’est pas celle de l’exactitude', () => {
    expect(verifie((e) => { e.qcm.hellaswag.marge_95 = 0.5; })).toThrow(/qcm\.hellaswag\.marge_95 n’est pas la marge/);
    expect(verifie((e) => { e.qcm.hellaswag.marge_95_normalisee = 0.5; })).toThrow(/marge_95_normalisee n’est pas la marge/);
  });

  it('refuse un verdict qui n’est pas celui de la règle de forge', () => {
    expect(verifie((e) => { e.qcm.arc.verdict = 'au-dessus'; })).toThrow(/la règle de forge donne « pas-different »/);
    expect(verifie((e) => { (e.qcm.arc as { verdict: string }).verdict = 'peut-être'; })).toThrow(/doit être « au-dessus »/);
  });

  it('refuse des échantillons absents ou mal formés', () => {
    expect(verifie((e) => { e.echantillons = []; })).toThrow(/echantillons est vide/);
    expect(verifie((e) => { (e.echantillons[2] as { suite: unknown }).suite = 3; })).toThrow(/echantillons\[2\]/);
  });
});

describe('verifierQcm', () => {
  const lu = (): QcmExemples => JSON.parse(readFileSync('../' + FICHIERS_QCM['ton-ia-mini'], 'utf8')) as QcmExemples;
  const verifie = (modifie: (q: QcmExemples) => void): (() => unknown) => {
    const q = lu();
    modifie(q);
    return () => verifierQcm(q, 'qcm-essai.json');
  };

  it('accepte le relevé de mini', () => {
    expect(() => verifierQcm(lu(), 'qcm-mini.json')).not.toThrow();
  });

  it('refuse un jeu sans adresse ni licence', () => {
    expect(verifie((q) => { q.jeu.licence = ''; })).toThrow(/jeu\.licence est vide/);
    expect(verifie((q) => { q.jeu.adresse = 'huggingface.co/datasets/openai/MMMLU'; })).toThrow(/adresse https/);
    expect(verifie((q) => { q.jeu.lu_le = 'hier'; })).toThrow(/dates AAAA-MM-JJ/);
  });

  it('refuse des questions mal formées ou un compte de justes faux', () => {
    expect(verifie((q) => { q.questions.pop(); })).toThrow(/questions doit avoir n éléments/);
    expect(verifie((q) => { q.questions[1].prefere = 9; })).toThrow(/questions\[1\]/);
    expect(verifie((q) => { q.questions[0].juste = !q.questions[0].juste; })).toThrow(/questions\[0\]/);
    expect(verifie((q) => { q.justes += 1; })).toThrow(/justes vaut/);
  });
});
