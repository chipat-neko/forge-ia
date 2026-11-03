// Les paris de l'animation de l'attention : leurs bonnes réponses viennent du
// moteur (detaillerExemple), et un exemple devenu faux arrête tout.

import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { detaillerExemple, exempleAttention, type ExempleAttention } from './exemple-attention';
import {
  choixMasque,
  choixRegardDeIl,
  MOT_FORGERON,
  MOT_IL,
  MOT_PUIS,
  motLePlusRegarde,
  TETE_DE_QUI_ON_PARLE,
  TETE_QUI_AGIT,
} from './paris-attention';

/** Une copie de l'exemple, modifiée par la fonction donnée (l'original est figé). */
function exempleModifie(modifier: (e: { jetons: string[]; x: number[][] }) => void): ExempleAttention {
  const e = structuredClone(exempleAttention) as unknown as { jetons: string[]; x: number[][] };
  modifier(e);
  return e as unknown as ExempleAttention;
}

/** La règle de Pari.astro : exactement un choix juste. */
function unSeulJuste(choix: Choix[]): Choix {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes.length).toBe(1);
  return justes[0];
}

describe('les indices, comptés à partir de 0', () => {
  it('la tête 1 est « de qui on parle » (la « Tête 2 » de la page), la tête 0 « qui agit »', () => {
    expect(exempleAttention.tetes[TETE_QUI_AGIT].nom).toBe('qui agit');
    expect(exempleAttention.tetes[TETE_DE_QUI_ON_PARLE].nom).toBe('de qui on parle');
    expect([TETE_QUI_AGIT, TETE_DE_QUI_ON_PARLE]).toEqual([0, 1]);
  });

  it('les mots : 1 « forgeron », 5 « puis », 6 « il »', () => {
    expect(exempleAttention.jetons[MOT_FORGERON]).toBe('forgeron');
    expect(exempleAttention.jetons[MOT_PUIS]).toBe('puis');
    expect(exempleAttention.jetons[MOT_IL]).toBe('il');
  });
});

describe('motLePlusRegarde', () => {
  it('le mot visible de plus grand poids, calculé par le moteur', () => {
    expect(motLePlusRegarde(TETE_DE_QUI_ON_PARLE, MOT_IL)).toBe(MOT_FORGERON);
    expect(motLePlusRegarde(TETE_DE_QUI_ON_PARLE, 7)).toBe(4); // le second « le » → « fer »
    expect(motLePlusRegarde(TETE_QUI_AGIT, 2)).toBe(MOT_FORGERON); // « chauffe » → « forgeron »
    expect(motLePlusRegarde(TETE_QUI_AGIT, 0)).toBe(0); // le premier mot ne voit que lui-même
    // À égalité, le premier mot gagne : « Le » ne cherche rien, ses poids sont égaux.
    expect(motLePlusRegarde(TETE_DE_QUI_ON_PARLE, 3)).toBe(0);
    const poids = detaillerExemple(exempleAttention)[TETE_DE_QUI_ON_PARLE].poids[MOT_IL];
    for (let j = 0; j <= MOT_IL; j++) expect(poids[j]).toBeLessThanOrEqual(poids[MOT_FORGERON]);
  });

  it('refuse une tête ou un mot hors de l’exemple', () => {
    expect(() => motLePlusRegarde(2, 6)).toThrow(RangeError);
    expect(() => motLePlusRegarde(-1, 6)).toThrow(RangeError);
    expect(() => motLePlusRegarde(1, 9)).toThrow(RangeError);
    expect(() => motLePlusRegarde(1, 1.5)).toThrow(/de 0 à 8/);
  });
});

describe('choixRegardDeIl', () => {
  it('trois choix dans l’ordre de la phrase, dont un seul juste : « forgeron »', () => {
    const choix = choixRegardDeIl();
    expect(choix.length).toBe(3);
    expect(unSeulJuste(choix).texte).toBe('forgeron');
    expect(choix.map((c) => c.texte)).toEqual(['forgeron', 'fer', 'puis']);
  });

  it('les leurres : « puis », et le mot de deuxième plus grand poids, calculé', () => {
    const poids = detaillerExemple(exempleAttention)[TETE_DE_QUI_ON_PARLE].poids[MOT_IL];
    const rangs = Array.from({ length: MOT_IL + 1 }, (_, j) => j).sort((a, b) => poids[b] - poids[a]);
    expect(rangs[0]).toBe(MOT_FORGERON);
    const deuxieme = rangs[1] === MOT_PUIS ? rangs[2] : rangs[1];
    const textes = choixRegardDeIl().map((c) => c.texte);
    expect(textes).toContain('puis');
    expect(textes).toContain(exempleAttention.jetons[deuxieme]);
  });

  it('si « puis » est le deuxième mot le plus regardé, le leurre est le troisième', () => {
    // « puis » devient un nom : « il » le regarde alors plus que « fer », mais moins que « forgeron ».
    const puisNom = exempleModifie((e) => {
      e.x[MOT_PUIS] = [0, 1, 0, 0, 0, 0, 0, 0];
    });
    const poids = detaillerExemple(puisNom)[TETE_DE_QUI_ON_PARLE].poids[MOT_IL];
    expect(poids[MOT_FORGERON]).toBeGreaterThan(poids[MOT_PUIS]);
    expect(poids[MOT_PUIS]).toBeGreaterThan(poids[4]);
    for (const j of [0, 2, 3, 6]) expect(poids[4]).toBeGreaterThan(poids[j]);
    const choix = choixRegardDeIl(puisNom);
    expect(choix.map((c) => c.texte)).toEqual(['forgeron', 'fer', 'puis']);
    expect(unSeulJuste(choix).texte).toBe('forgeron');
  });

  it('Exemple devenu faux : « il » regarde surtout un autre mot', () => {
    // « forgeron » et « fer » échangent leurs traits : « il » (sujet, personne) regarde alors le mot 4.
    const echange = exempleModifie((e) => {
      [e.x[1], e.x[4]] = [e.x[4], e.x[1]];
    });
    expect(motLePlusRegarde(TETE_DE_QUI_ON_PARLE, MOT_IL, echange)).toBe(4);
    expect(() => choixRegardDeIl(echange)).toThrow(/^Exemple devenu faux : /);
  });

  it('Exemple devenu faux : un autre mot reçoit autant que « forgeron »', () => {
    // « fer » prend les traits de « forgeron » : leurs poids sont égaux, le pari n'a plus de réponse unique.
    const egalite = exempleModifie((e) => {
      e.x[4] = [...e.x[1]];
    });
    expect(motLePlusRegarde(TETE_DE_QUI_ON_PARLE, MOT_IL, egalite)).toBe(MOT_FORGERON);
    expect(() => choixRegardDeIl(egalite)).toThrow(/^Exemple devenu faux : /);
  });

  it('Exemple devenu faux : la phrase a changé', () => {
    const autre = exempleModifie((e) => {
      e.jetons[MOT_IL] = 'elle';
    });
    expect(() => choixRegardDeIl(autre)).toThrow(/^Exemple devenu faux : /);
    expect(() => choixMasque(autre)).toThrow(/^Exemple devenu faux : /);
  });
});

describe('choixMasque', () => {
  it('la bonne réponse est 0 : « forgeron » ne voit pas « il », qui vient après', () => {
    const choix = choixMasque();
    expect(choix.map((c) => c.texte)).toEqual(['0', 'environ la moitié', 'presque tout']);
    expect(unSeulJuste(choix).texte).toBe('0');
    for (const d of detaillerExemple(exempleAttention)) expect(d.poids[MOT_FORGERON][MOT_IL]).toBe(0);
  });
});
