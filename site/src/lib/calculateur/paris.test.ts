// Les paris du calculateur : leurs bonnes réponses sont calculées par les
// formules et les données, et un exemple devenu faux arrête la construction.

import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { MATERIELS, PRIX_LOCATION, type PrixLocation } from './donnees';
import { memoireEntrainementOctets, OCTETS_PAR_GO } from './formules';
import {
  choixCoutH100,
  choixMemoireTonIA,
  choixOperationsTonIA,
  EFFICACITE_PARI_H100,
  fourchetteCoutH100,
} from './paris';
import { PRESETS_FORGE } from './ton-ia';

/** La règle de Pari.astro : exactement un choix juste. */
function unSeulJuste(choix: Choix[]): Choix {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes).toHaveLength(1);
  return justes[0];
}

describe('le pari « opérations »', () => {
  it('10¹³, 10¹⁶ ou 10¹⁹ opérations : l’exposant juste est lu sur 6·N·20N', () => {
    expect(choixOperationsTonIA().find((c) => c.juste)?.texte).toBe('10¹⁹ opérations');
    expect(choixOperationsTonIA().map((c) => c.texte)).toEqual(['10¹³ opérations', '10¹⁶ opérations', '10¹⁹ opérations']);
    unSeulJuste(choixOperationsTonIA());
  });

  it('un autre modèle rendrait la question fausse (« 433,6 millions de paramètres ») : la construction s’arrête', () => {
    const petit = { ...PRESETS_FORGE.tres_grand, parametres: 433_573_120 / 1000 };
    // 6 × 433 573 × 8 671 462 ≈ 2,26e13 : la question ne parle plus de ton IA.
    expect(() => choixOperationsTonIA(petit)).toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « coût sur des H100 »', () => {
  it('des dizaines à des centaines d’euros, aux prix relevés', () => {
    expect(choixCoutH100().find((c) => c.juste)?.texte).toBe('Des dizaines à des centaines d’euros');
    expect(choixCoutH100().map((c) => c.texte)).toEqual([
      'Quelques euros',
      'Des dizaines à des centaines d’euros',
      'Des dizaines de milliers d’euros',
    ]);
    unSeulJuste(choixCoutH100());
  });

  it('la fourchette : ton IA sur une H100 SXM à 40 %, du prix primaire le plus bas au plus haut', () => {
    const f = fourchetteCoutH100();
    expect(EFFICACITE_PARI_H100).toBe(0.4);
    expect(f.secondes).toBeCloseTo(57_022.9, 0);
    expect(f.usdParHeureMin).toBe(2.69);
    expect(f.usdParHeureMax).toBe(12.29);
    expect(f.eurMin).toBeCloseTo(38.12, 2);
    expect(f.eurMax).toBeCloseTo(174.14, 2);
  });

  it('chaque bonne réponse selon les prix, et « Exemple devenu faux » entre deux choix', () => {
    const avec = (min: number, max: number): PrixLocation[] =>
      [min, max].map((usdParHeure) => ({ ...PRIX_LOCATION[0], materiel: 'h100-sxm', usdParHeure }));
    // 15,84 heures de H100 : il faut moins de 0,63 $ de l'heure pour « quelques euros ».
    expect(unSeulJuste(choixCoutH100(avec(0.1, 0.6))).texte).toBe('Quelques euros');
    expect(unSeulJuste(choixCoutH100(avec(800, 900))).texte).toBe('Des dizaines de milliers d’euros');
    expect(() => choixCoutH100(avec(0.01, 0.02))).toThrow(/Exemple devenu faux/);
    expect(() => choixCoutH100(avec(2, 100))).toThrow(/Exemple devenu faux/);
    expect(() => choixCoutH100(avec(100, 200))).toThrow(/Exemple devenu faux/);
    expect(() => choixCoutH100([])).toThrow(/Exemple devenu faux/);
  });
});

describe('le pari « mémoire » (gardé pour le plan 5)', () => {
  it('moins de 16 Go, d’après la formule, et le pic mesuré de 10,9 Go le confirme', () => {
    expect(choixMemoireTonIA().find((c) => c.juste)?.texte).toBe('Moins de 16 Go');
    expect(choixMemoireTonIA().map((c) => c.texte)).toEqual(['Moins de 16 Go', 'Plus de 16 Go']);
    unSeulJuste(choixMemoireTonIA());
    const carte = MATERIELS.find((m) => m.id === 'rtx-5070-ti');
    expect(memoireEntrainementOctets(PRESETS_FORGE.tres_grand).total).toBeLessThan((carte?.memoireGo ?? 0) * OCTETS_PAR_GO);
  });

  it('« Exemple devenu faux » si la formule et la mesure ne disent plus la même chose', () => {
    expect(() => choixMemoireTonIA(17.2)).toThrow(/Exemple devenu faux/);
    expect(() => choixMemoireTonIA(NaN)).toThrow(/Exemple devenu faux/);
  });
});
