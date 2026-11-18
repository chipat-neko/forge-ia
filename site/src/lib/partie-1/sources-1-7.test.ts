// Les chiffres de labo et les sources des données du chapitre 1.7 : chacun a son adresse, l'endroit de la
// source où il se lit, sa date de lecture et son étiquette (publié, dérivé, tiers) ; les chiffres dérivés
// sont bien le calcul dit ; les licences sont celles que forge écrit dans ses sources de conversations.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  ARTICLE_INSTRUCTGPT,
  ARTICLE_LLAMA_2,
  ARTICLE_TULU_3,
  BILLET_SMOLLM3,
  COPIE_CONDITIONS_OPENAI,
  DISCUSSION_NANOCHAT,
  DONNEES_1_7,
  ETIQUETTES,
  FICHE_AYA,
  FICHE_LUTH_2,
  FICHE_OASST2,
  INSTRUCTGPT,
  LICENCE_LLAMA_33,
  LLAMA_2,
  LU_LE_1_7,
  NANOCHAT_D20,
  SMOLLM3,
  SOURCES_DONNEES_1_7,
  SOURCES_LABO_1_7,
  TULU_3,
  type ChiffreSource,
} from './sources-1-7';

const SOURCES = [
  ARTICLE_INSTRUCTGPT,
  ARTICLE_LLAMA_2,
  ARTICLE_TULU_3,
  BILLET_SMOLLM3,
  DISCUSSION_NANOCHAT,
  FICHE_LUTH_2,
  FICHE_AYA,
  FICHE_OASST2,
  LICENCE_LLAMA_33,
  COPIE_CONDITIONS_OPENAI,
];
const GROUPES = { INSTRUCTGPT, LLAMA_2, TULU_3, SMOLLM3, NANOCHAT_D20, DONNEES_1_7 };
const valeurs = (g: Record<string, ChiffreSource<unknown>>) => Object.fromEntries(Object.entries(g).map(([k, c]) => [k, c.valeur]));

describe('les sources du chapitre 1.7', () => {
  it('chaque chiffre a sa valeur, l’adresse d’une source lue, l’endroit, la date de lecture et une étiquette', () => {
    expect(LU_LE_1_7).toBe('2026-11-18');
    const adresses = SOURCES.map((s) => s.url);
    for (const [nom, groupe] of Object.entries(GROUPES)) {
      for (const [cle, c] of Object.entries(groupe as Record<string, ChiffreSource<unknown>>)) {
        expect(adresses, `${nom}.${cle}`).toContain(c.url);
        expect(c.endroit.length, `${nom}.${cle}`).toBeGreaterThan(8);
        expect(c.lu_le, `${nom}.${cle}`).toBe(LU_LE_1_7);
        expect(ETIQUETTES, `${nom}.${cle}`).toContain(c.etiquette);
      }
    }
  });

  it('les valeurs relues à la source le 18 novembre 2026', () => {
    expect(valeurs(INSTRUCTGPT)).toStrictEqual({ parametres: 175e9, invitesSft: 13_000, petaflopsSft: 4.9, petaflopsGpt3: 3_640, epoques: 16 });
    expect(valeurs(LLAMA_2)).toStrictEqual({ annotationsSft: 27_540, longueur: 4096, epoques: 2, perteSurLesReponses: true });
    expect(valeurs(TULU_3)).toStrictEqual({ invitesSft: 939_344, parametres8B: 8e9, cartes8B: 32, heures8B: 6, heuresDeCartes8B: 192, longueur: 4096, epoques: 2 });
    expect(valeurs(SMOLLM3)).toStrictEqual({ parametres: 3e9, jetonsSft: 1.8e9, jetonsRaisonnement: 0.8e9, epoques: 4, bfd: true, perteMasquee: true });
    expect(valeurs(NANOCHAT_D20)).toStrictEqual({ parametres: 560_988_160, arcAvant: 0.2875, arcApres: 0.2807, minutesSft: 7 });
  });

  it('les chiffres dérivés sont le calcul qu’ils disent, et seulement eux', () => {
    expect(TULU_3.heuresDeCartes8B.valeur).toBe(TULU_3.cartes8B.valeur * TULU_3.heures8B.valeur);
    expect(TULU_3.heuresDeCartes8B.etiquette).toBe('dérivé');
    const derives = Object.values(GROUPES).flatMap((g) => Object.values(g as Record<string, ChiffreSource<unknown>>)).filter((c) => c.etiquette === 'dérivé');
    expect(derives).toHaveLength(1);
    // Les conditions d'OpenAI sont lues dans une copie : tiers.
    expect(DONNEES_1_7.openai.etiquette).toBe('tiers');
    expect(DONNEES_1_7.openai.url).toBe(COPIE_CONDITIONS_OPENAI.url);
  });

  it('les licences des sources de conversations sont celles que forge écrit dans sources.py', () => {
    const sources = readFileSync('../projets/forge/forge/conversation/sources.py', 'utf8');
    expect(DONNEES_1_7.licenceLuth2.valeur).toBe('CC BY 4.0');
    expect(sources).toMatch(/_LICENCE_LUTH = "CC BY 4\.0"/);
    expect(DONNEES_1_7.licenceAya.valeur).toBe('Apache-2.0');
    expect(sources).toMatch(/_source\("aya_fr", "CohereLabs\/aya_dataset", "entrainement", "conversation", _convertir_aya,\s*"Apache-2\.0"/);
    expect(DONNEES_1_7.licenceOasst2.valeur).toBe('Apache-2.0');
    expect(sources).toMatch(/_source\("oasst2_fr", "OpenAssistant\/oasst2", "entrainement", "conversation", _convertir_oasst2,\s*"Apache-2\.0"/);
    // Forge ne garde de Luth-2 que les réponses écrites par Qwen : Gemma, Llama et GPT sont écartés.
    expect(sources).toContain('GENERATEURS_GARDES = ("Qwen/",)');
    // Les questions de Luth-2 venues de jeux écrits par GPT-4o ou Llama sont écartées aussi (Dolci, Tulu 3 Personas).
    expect(sources).toMatch(/SOURCES_AMONT_ECARTEES = \([^)]*"dolci"[^)]*"tulu"[^)]*\)/);
    // Les lignes de Luth-2 tirées de StackOverflow ne se reconnaissent pas : forge les garde, et le dit.
    expect(sources).toContain('Les lignes de Nemotron tirées de StackOverflow (CC BY-SA) ne se reconnaissent pas à leur source.');
    expect(DONNEES_1_7.stackoverflowLuth2.valeur).toBe('CC BY-SA 4.0');
  });

  it('les sources de l’encadré et celles de l’étape des données, dans l’ordre où le chapitre les cite', () => {
    const verifiee = (s: { titre: string; url: string }) => ({ titre: s.titre, url: s.url, verifieLe: LU_LE_1_7 });
    expect(SOURCES_LABO_1_7).toStrictEqual([ARTICLE_INSTRUCTGPT, ARTICLE_LLAMA_2, ARTICLE_TULU_3, BILLET_SMOLLM3].map(verifiee));
    expect(SOURCES_DONNEES_1_7).toStrictEqual([FICHE_LUTH_2, FICHE_AYA, FICHE_OASST2, LICENCE_LLAMA_33, COPIE_CONDITIONS_OPENAI].map(verifiee));
    for (const s of SOURCES) expect(s.url, s.titre).toMatch(/^https:\/\//);
  });
});
