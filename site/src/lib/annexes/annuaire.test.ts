import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { NUMEROS_DU_PARCOURS } from '../parcours';
import { ANNUAIRE, GROUPES, NOTES, texteLicence, texteTaille } from './annuaire';

const FORGE = fileURLToPath(new URL('../../../../projets/forge/forge/', import.meta.url));

/** Les dépôts Hugging Face cités dans un fichier de forge, lu comme du texte (sans l'importer). */
function depotsCites(fichier: string, motif: RegExp): string[] {
  const texte = readFileSync(`${FORGE}${fichier}`, 'utf8');
  return [...texte.matchAll(motif)].map((m) => m[1]);
}

describe('ANNUAIRE', () => {
  it('donne à chaque fiche une adresse https, une date de relevé AAAA-MM-JJ et une source https', () => {
    for (const f of ANNUAIRE) {
      expect(f.url, f.id).toMatch(/^https:\/\//);
      expect(f.releveLe, f.id).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(new Date(`${f.releveLe}T00:00:00Z`).toISOString().slice(0, 10), f.id).toBe(f.releveLe);
      expect(f.source, f.id).toMatch(/^https:\/\//);
      if (f.licence) expect(f.licence.url, f.id).toMatch(/^https:\/\//);
      // Une taille donnée a toujours sa source, que la page met en lien.
      if (f.taille !== null) expect(f.sourceTaille, f.id).toMatch(/^https:\/\//);
      for (const l of f.autresLicences ?? []) expect(l.url, f.id).toMatch(/^https:\/\//);
    }
  });

  it('a une fiche, avec son usage par ton IA, pour chaque dépôt de forge.donnees.sources et de forge.evaluation.qcm', () => {
    const sources = depotsCites('donnees/sources.py', /depot="([^"]+)"/g);
    const qcm = depotsCites('evaluation/qcm.py', /\(\s*"([\w.-]+\/[\w.-]+)"\s*,\s*"\w+"\s*\)/g);
    expect(sources).toHaveLength(3);
    expect(qcm).toEqual(['manu/french_bench_hellaswag', 'manu/french_bench_arc_challenge']);
    for (const depot of [...sources, ...qcm]) {
      const fiche = ANNUAIRE.find((f) => f.depot === depot);
      expect(fiche, depot).toBeDefined();
      expect(fiche!.tonIA, depot).not.toBeNull();
    }
  });

  it('renvoie chaque usage par ton IA à un chapitre du parcours', () => {
    for (const f of ANNUAIRE) {
      if (f.tonIA !== null) {
        expect(NUMEROS_DU_PARCOURS, f.id).toContain(f.tonIA);
        expect(f.tonIAUsage, f.id).toMatch(/\S/);
      } else {
        expect(f.tonIAUsage, f.id).toBeUndefined();
        expect(f.tonIAPart, f.id).toBeUndefined();
      }
    }
  });

  it('ne liste que les jeux de la recherche du plan 5 : trois groupes, douze fiches, chacune unique', () => {
    expect(GROUPES.map((g) => g.id)).toEqual(['francais', 'code', 'evaluation']);
    expect(ANNUAIRE.map((f) => f.depot).sort()).toEqual(
      [
        'HuggingFaceFW/fineweb-2',
        'wikimedia/wikipedia',
        'PleIAs/common_corpus',
        'croissantllm/croissant_dataset',
        'uonlp/CulturaX',
        'OpenLLM-France/Lucie-Training-Dataset',
        'oscar-corpus/OSCAR-2301',
        'codeparrot/github-code-clean',
        'bigcode/the-stack-v2',
        'manu/french_bench_hellaswag',
        'manu/french_bench_arc_challenge',
        'openai/MMMLU',
      ].sort(),
    );
    expect(new Set(ANNUAIRE.map((f) => f.id)).size).toBe(ANNUAIRE.length);
    for (const f of ANNUAIRE) expect(f.url, f.id).toBe(`https://huggingface.co/datasets/${f.depot}`);
  });

  it('dit « non indiquée » pour une fiche sans licence, et « pas relevée » pour une taille absente', () => {
    const sansLicence = ANNUAIRE.filter((f) => f.licence === null);
    expect(sansLicence.length).toBeGreaterThan(0);
    for (const f of sansLicence) expect(texteLicence(f)).toBe('non indiquée');
    for (const f of ANNUAIRE.filter((f) => f.licence !== null)) expect(texteLicence(f)).toBe(f.licence!.nom);
    for (const f of ANNUAIRE) expect(texteTaille(f)).toBe(f.taille ?? 'pas relevée');
  });

  it('appelle des notes qui existent, et chaque note est appelée', () => {
    const appelees = new Set(ANNUAIRE.flatMap((f) => Object.values(f.appels ?? {})));
    expect([...appelees].sort()).toEqual(NOTES.map((n) => n.id).sort());
    // Une note par groupe : celle du groupe de la fiche qui l'appelle.
    for (const f of ANNUAIRE) {
      for (const id of Object.values(f.appels ?? {})) {
        expect(NOTES.find((n) => n.id === id)!.groupe, `${f.id} → ${id}`).toBe(f.groupe);
      }
    }
  });

  it('écrit les accès et les groupes avec les seules valeurs prévues', () => {
    for (const f of ANNUAIRE) {
      expect(['libre', 'conditions', 'accord'], f.id).toContain(f.acces);
      expect(GROUPES.map((g) => g.id), f.id).toContain(f.groupe);
    }
  });
});
