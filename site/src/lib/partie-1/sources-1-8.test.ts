// Les chiffres sourcés du chapitre 1.8 : chacun a son adresse, l'endroit de la source où il se lit, sa date de
// lecture et son étiquette (publié, dérivé, tiers) ; les chiffres dérivés sont bien le calcul dit ; les sources des
// encadrés et des notes sont dans l'ordre où le chapitre les cite.

import { describe, expect, it } from 'vitest';
import {
  ARTICLE_COMMUNITY_ALIGNMENT,
  ARTICLE_DPO,
  ARTICLE_DPOP,
  ARTICLE_QWEN_25,
  COMMUNITY_ALIGNMENT,
  DPO,
  DPOP,
  FICHE_COMMUNITY_ALIGNMENT,
  FICHE_COMMUNITY_ALIGNMENT_FR,
  INSTRUCTGPT_RM,
  LLAMA_2_RLHF,
  LU_LE_1_8,
  QWEN_25,
  SOURCES_DONNEES_1_8,
  SOURCES_DPO_1_8,
  SOURCES_LABO_1_8,
  TULU_3_DPO,
} from './sources-1-8';
import { ARTICLE_INSTRUCTGPT, ARTICLE_LLAMA_2, ARTICLE_TULU_3, ETIQUETTES, LICENCE_LLAMA_33, type ChiffreSource } from './sources-1-7';

const SOURCES = [
  ARTICLE_DPO,
  ARTICLE_DPOP,
  ARTICLE_INSTRUCTGPT,
  ARTICLE_LLAMA_2,
  ARTICLE_QWEN_25,
  ARTICLE_TULU_3,
  FICHE_COMMUNITY_ALIGNMENT,
  FICHE_COMMUNITY_ALIGNMENT_FR,
  ARTICLE_COMMUNITY_ALIGNMENT,
  LICENCE_LLAMA_33,
];
const GROUPES = { DPO, DPOP, INSTRUCTGPT_RM, LLAMA_2_RLHF, QWEN_25, TULU_3_DPO, COMMUNITY_ALIGNMENT };

describe('les sources du chapitre 1.8', () => {
  it('chaque chiffre a sa valeur, l’adresse d’une source lue, l’endroit, la date de lecture et une étiquette', () => {
    expect(LU_LE_1_8).toBe('2026-11-19');
    const adresses = SOURCES.map((s) => s.url);
    for (const [nom, groupe] of Object.entries(GROUPES)) {
      for (const [cle, c] of Object.entries(groupe as Record<string, ChiffreSource<unknown>>)) {
        expect(adresses, `${nom}.${cle}`).toContain(c.url);
        expect(c.endroit.length, `${nom}.${cle}`).toBeGreaterThan(8);
        expect(c.lu_le, `${nom}.${cle}`).toBe(LU_LE_1_8);
        expect(ETIQUETTES, `${nom}.${cle}`).toContain(c.etiquette);
      }
    }
  });

  it('les valeurs relues à la source le 19 novembre 2026', () => {
    expect(INSTRUCTGPT_RM.invitesRm.valeur).toBe(33_000);
    expect(INSTRUCTGPT_RM.invitesPpo.valeur).toBe(31_000);
    expect([INSTRUCTGPT_RM.reponsesAClasserMin.valeur, INSTRUCTGPT_RM.reponsesAClasserMax.valeur]).toStrictEqual([4, 9]);
    expect(INSTRUCTGPT_RM.parametresRm.valeur).toBe(6e9);
    expect(INSTRUCTGPT_RM.petaflopsPpo.valeur).toBe(60);
    expect(INSTRUCTGPT_RM.petaflopsGpt3.valeur).toBe(3_640);
    expect(LLAMA_2_RLHF.comparaisonsMeta.valeur).toBe(1_418_091);
    expect(LLAMA_2_RLHF.comparaisonsTotal.valeur).toBe(2_919_326);
    expect(LLAMA_2_RLHF.modelesDeRecompense.valeur).toBe(2);
    expect(LLAMA_2_RLHF.versionsRlhf.valeur).toBe(5);
    expect(QWEN_25.paires.valeur).toBe(150_000);
    expect(QWEN_25.epoques.valeur).toBe(1);
    expect(QWEN_25.taux.valeur).toBe(7e-7);
    expect(TULU_3_DPO.pairesTotal.valeur).toBe(354_192);
    expect(TULU_3_DPO.paires8B.valeur).toBe(271_409);
    expect(TULU_3_DPO.invitesTableau7.valeur).toBe(425_145);
    expect(TULU_3_DPO.reponsesParInvite.valeur).toBe(4);
    expect(TULU_3_DPO.beta.valeur).toBe(5);
    expect(TULU_3_DPO.taux8B.valeur).toBe(5e-7);
    expect(TULU_3_DPO.epoques.valeur).toBe(1);
    expect([TULU_3_DPO.cartes8B.valeur, TULU_3_DPO.heures8B.valeur]).toStrictEqual([8, 10]);
    expect(COMMUNITY_ALIGNMENT.licence.valeur).toBe('CC BY 4.0');
    expect(COMMUNITY_ALIGNMENT.pairesFr.valeur).toBe(71_525);
    expect(COMMUNITY_ALIGNMENT.annotateurs.valeur).toBe(3_500);
    expect(COMMUNITY_ALIGNMENT.modeleDesReponses.valeur).toBe('Llama-3.3-70B-Instruct');
  });

  it('les chiffres dérivés sont le calcul dit, et marqués « dérivé »', () => {
    expect(INSTRUCTGPT_RM.partDuPreEntrainement.valeur).toBe(60 / 3_640);
    expect(INSTRUCTGPT_RM.partDuPreEntrainement.etiquette).toBe('dérivé');
    expect(TULU_3_DPO.heuresDeCartes8B.valeur).toBe(TULU_3_DPO.cartes8B.valeur * TULU_3_DPO.heures8B.valeur);
    expect(TULU_3_DPO.heuresDeCartes8B.etiquette).toBe('dérivé');
    const derives = Object.values(GROUPES).flatMap((g) => Object.values(g as Record<string, ChiffreSource<unknown>>)).filter((c) => c.etiquette === 'dérivé');
    expect(derives).toHaveLength(2);
  });

  it('les trois comptes de paires de Tülu 3 ne s’accordent pas : le chapitre le dit', () => {
    expect(new Set([TULU_3_DPO.pairesTotal.valeur, TULU_3_DPO.paires8B.valeur, TULU_3_DPO.invitesTableau7.valeur]).size).toBe(3);
  });

  it('les sources de chaque encadré et de chaque note, dans l’ordre où le chapitre les cite, lues le même jour', () => {
    expect(SOURCES_LABO_1_8.map((s) => s.url)).toStrictEqual([ARTICLE_INSTRUCTGPT.url, ARTICLE_LLAMA_2.url, ARTICLE_QWEN_25.url, ARTICLE_TULU_3.url]);
    expect(SOURCES_DPO_1_8.map((s) => s.url)).toStrictEqual([ARTICLE_DPO.url, ARTICLE_DPOP.url]);
    expect(SOURCES_DONNEES_1_8.map((s) => s.url)).toStrictEqual([
      FICHE_COMMUNITY_ALIGNMENT_FR.url,
      FICHE_COMMUNITY_ALIGNMENT.url,
      ARTICLE_COMMUNITY_ALIGNMENT.url,
      LICENCE_LLAMA_33.url,
    ]);
    for (const s of [...SOURCES_LABO_1_8, ...SOURCES_DPO_1_8, ...SOURCES_DONNEES_1_8]) expect(s.verifieLe).toBe(LU_LE_1_8);
    for (const s of SOURCES) expect(s.url).toMatch(/^https:\/\//);
  });
});
