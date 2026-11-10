// Les chiffres et les faits de labo du chapitre 1.6 : chacun a son adresse et sa date de lecture, et
// ce qu'en disent aussi l'annuaire des données (FrenchBench, MMMLU), le relevé des QCM de l'atelier
// (la licence de MMMLU) et le projet (la marge de la mesure) est la même chose.

import { describe, expect, it } from 'vitest';
import { ANNUAIRE } from '../annexes/annuaire';
import { lireQcm } from './evaluation';
import { Z_95 } from './marge';
import { ARTICLE_LLAMA_3, CARTE_LLAMA_31 } from './sources-1-5';
import {
  ARTICLE_CROISSANT,
  FRENCHBENCH,
  LLAMA_3_BANCS,
  LLAMA_31_405B_BASE,
  MMMLU,
  PAGE_FRENCHBENCH_ARC,
  PAGE_FRENCHBENCH_HELLASWAG,
  PAGE_MMMLU,
  SOURCES_LABO_1_6,
  SOURCES_LIMITES_1_6,
  type Releve,
} from './sources-1-6';

const RELEVES: [string, Releve<unknown>][] = [LLAMA_3_BANCS, LLAMA_31_405B_BASE, FRENCHBENCH, MMMLU].flatMap((groupe) =>
  Object.entries(groupe),
);
const ADRESSES = [ARTICLE_LLAMA_3, CARTE_LLAMA_31, ARTICLE_CROISSANT, PAGE_FRENCHBENCH_HELLASWAG, PAGE_FRENCHBENCH_ARC, PAGE_MMMLU].map((s) => s.url);

describe('les faits de labo du chapitre 1.6', () => {
  it('chacun a son adresse, l’endroit de la source et sa date de lecture', () => {
    expect(RELEVES.length).toBeGreaterThan(10);
    for (const [cle, r] of RELEVES) {
      expect(ADRESSES, cle).toContain(r.url);
      expect(r.releveLe, cle).toBe('2026-11-10');
      expect(r.ou.length, cle).toBeGreaterThan(5);
    }
  });

  it('les bancs de Llama 3 : les sept catégories du tableau 8, le 1,96 des intervalles, les 8-grammes', () => {
    const categories = LLAMA_3_BANCS.categories.valeur;
    expect(categories.map((c) => c.anglais)).toStrictEqual([
      'Reading Comprehension',
      'Code',
      'Commonsense reasoning/understanding',
      'Math, reasoning, and problem solving',
      'Adversarial',
      'Long context',
      'Aggregate',
    ]);
    // ARC Challenge et MMLU, que le chapitre compare à ton IA, sont bien dans le tableau.
    expect(categories.find((c) => c.bancs.includes('ARC Challenge'))?.anglais).toBe('Math, reasoning, and problem solving');
    expect(categories.find((c) => c.bancs.includes('MMLU'))?.anglais).toBe('Aggregate');
    for (const c of categories) {
      expect(c.francais, c.anglais).toBe(c.francais.toLowerCase());
      expect(c.bancs.length, c.anglais).toBeGreaterThan(1);
    }
    // La formule de Meta est la marge de la mesure du projet 1.6 (marge95) : le même 1,96.
    expect(LLAMA_3_BANCS.z.valeur).toBe(Z_95);
    expect(LLAMA_3_BANCS.ngramme.valeur).toBe(8);
    expect(LLAMA_3_BANCS.hellaswagContamine.valeur).toBe(85);
    // Les nuances que le chapitre dit : intervalles des seules moyennes simples, seuil de contamination par test.
    expect(LLAMA_3_BANCS.intervallesDesMoyennesSimples.valeur).toBe(true);
    expect(LLAMA_3_BANCS.seuilParTest.valeur).toBe(true);
    expect(LLAMA_3_BANCS.gainHellaswag405B.valeur).toBe(14.3);
    for (const [, r] of Object.entries(LLAMA_3_BANCS)) expect(r.url).toBe(ARTICLE_LLAMA_3.url);
  });

  it('Llama 3.1 405B pré-entraîné : MMLU 85,2 en 5 exemples, ARC-Challenge 96,1 en 25, lus dans sa carte de modèle', () => {
    expect(Object.fromEntries(Object.entries(LLAMA_31_405B_BASE).map(([cle, r]) => [cle, r.valeur]))).toStrictEqual({
      mmlu: 85.2,
      mmluMoyenneParMatiere: true,
      mmluExemples: 5,
      arc: 96.1,
      arcExemples: 25,
    });
    for (const [, r] of Object.entries(LLAMA_31_405B_BASE)) expect(r.url).toBe(CARTE_LLAMA_31.url);
  });

  it('FrenchBench : traduit de l’anglais par GPT-3.5, sans licence indiquée', () => {
    expect(FRENCHBENCH.langueDOrigine.valeur).toBe('anglais');
    expect(FRENCHBENCH.traduction.valeur).toBe('automatique');
    expect(FRENCHBENCH.traducteur.valeur).toBe('GPT-3.5');
    // La phrase entière : loin d'être parfaites, mais suffisantes pour mesurer les modèles.
    expect(FRENCHBENCH.jugement.valeur).toBe('loin d’être parfaites, mais suffisantes pour que ces jeux donnent une mesure approchée correcte des modèles');
    expect(FRENCHBENCH.jugement.ou).toContain('far from perfect but sufficient for these datasets to act as a correct performance proxy');
    expect(FRENCHBENCH.licence.valeur).toBeNull();
    expect(FRENCHBENCH.traduction.url).toBe(ARTICLE_CROISSANT.url);
    expect(ARTICLE_CROISSANT.url).toBe('https://arxiv.org/abs/2402.00786');
  });

  it('MMMLU : traduit par des humains, sous licence MIT', () => {
    expect(MMMLU.traduction.valeur).toBe('humaine');
    expect(MMMLU.licence.valeur).toBe('MIT');
    expect(MMMLU.langues.valeur).toBe(14);
    expect(MMMLU.categories.valeur).toBe(57);
  });

  it('l’annuaire et le relevé de l’atelier disent la même chose', () => {
    const fiche = (id: string) => ANNUAIRE.find((f) => f.id === id)!;
    // FrenchBench : sans licence, traduit automatiquement, sur les pages relevées ici.
    for (const [id, page] of [
      ['french-bench-hellaswag', PAGE_FRENCHBENCH_HELLASWAG],
      ['french-bench-arc-challenge', PAGE_FRENCHBENCH_ARC],
    ] as const) {
      expect(fiche(id).licence, id).toBeNull();
      expect(fiche(id).description, id).toContain('traduit automatiquement');
      expect(fiche(id).url, id).toBe(page.url);
      expect(fiche(id).tonIA, id).toBe('1.6');
    }
    // MMMLU : la licence de l'annuaire, celle du relevé des QCM de l'atelier, et celle relevée ici.
    expect(fiche('mmmlu').licence?.nom).toBe(MMMLU.licence.valeur);
    expect(fiche('mmmlu').url).toBe(PAGE_MMMLU.url);
    expect(fiche('mmmlu').description).toContain('traducteurs professionnels');
    expect(fiche('mmmlu').tonIA).toBe('1.6');
    expect(fiche('mmmlu').tonIAUsage).toBe("pour l'atelier des QCM");
    const qcm = lireQcm('ton-ia-mini');
    expect(qcm?.jeu.licence).toBe(MMMLU.licence.valeur);
    expect(qcm?.jeu.adresse).toBe(PAGE_MMMLU.url);
  });

  it('les sources des encadrés, avec leur date', () => {
    expect(SOURCES_LABO_1_6).toStrictEqual([
      { titre: ARTICLE_LLAMA_3.titre, url: ARTICLE_LLAMA_3.url, verifieLe: '2026-11-10' },
      { titre: CARTE_LLAMA_31.titre, url: CARTE_LLAMA_31.url, verifieLe: '2026-11-10' },
    ]);
    expect(SOURCES_LIMITES_1_6.map((s) => s.url)).toStrictEqual([ARTICLE_CROISSANT.url, PAGE_MMMLU.url, ARTICLE_LLAMA_3.url]);
  });
});
