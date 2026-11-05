// Les paris du chapitre 0.3 : leurs bonnes réponses viennent des mesures de ton
// IA (MESURES_TON_IA) et des attendus du diagnostic (poste.ts), jamais écrites
// à la main.

import { describe, expect, it } from 'vitest';
import { MESURES_TON_IA } from '../calculateur/ton-ia';
import type { Choix } from '../choix';
import { situation } from './poste';
import { choixCarteTropRecente, choixRouePypi, choixVitesse, rapportDesDebits, TAILLE_DU_PARI } from './paris-0-3';

/** Le texte du choix juste (et vérifie qu'il est seul). */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste);
  expect(justes).toHaveLength(1);
  return justes[0].texte;
}

describe('les paris du chapitre 0.3', () => {
  it('chaque pari a exactement un choix juste, et trois choix différents', () => {
    for (const f of [choixVitesse, choixRouePypi, choixCarteTropRecente]) {
      expect(f().filter((c) => c.juste)).toHaveLength(1);
      expect(new Set(f().map((c) => c.texte)).size).toBe(3);
    }
  });

  it('vitesse : le rapport arrondi des débits mesurés de la plus grande taille, carte contre processeur', () => {
    expect(TAILLE_DU_PARI).toBe('tres_grand');
    const { carte, processeur } = MESURES_TON_IA.tres_grand;
    expect(rapportDesDebits()).toBe(carte.jetonsParSeconde / processeur.jetonsParSeconde);
    const r = Math.round(carte.jetonsParSeconde / processeur.jetonsParSeconde);
    // 17 855 jetons par seconde sur la carte, 235 sur le processeur : 76 fois plus vite.
    expect(r).toBe(76);
    expect(choixVitesse().map((c) => c.texte)).toEqual(['2 fois', '10 fois', `${r} fois`]);
    expect(juste(choixVitesse())).toBe(`${r} fois`);
  });

  it('pypi : la situation de PyPI sous Windows donne la version pour processeur', () => {
    expect(situation('windows_pypi_rtx5070ti').constats.map((c) => c.cle)).toContain('roue_processeur');
    expect(choixRouePypi().map((c) => c.texte)).toEqual([
      'Oui, la carte calcule',
      "Non : c'est la version pour processeur",
      "PyTorch refuse de s'importer",
    ]);
    expect(juste(choixRouePypi())).toBe("Non : c'est la version pour processeur");
  });

  it('trop-recente : la RTX 5070 Ti avec l’ancienne version pour CUDA 12.6', () => {
    expect(situation('windows_cu126_rtx5070ti').constats.map((c) => c.cle)).toContain('carte_trop_recente');
    expect(choixCarteTropRecente().map((c) => c.texte)).toEqual([
      'Tout marche',
      'La carte est trop récente pour cette version',
      'Le pilote est trop ancien',
    ]);
    expect(juste(choixCarteTropRecente())).toBe('La carte est trop récente pour cette version');
  });
});
