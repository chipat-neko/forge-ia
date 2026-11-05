// L'état de départ de la démo, calculé une fois par préréglage, au pas 0.

import { describe, expect, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-modele.json';
import { etatInitial } from './apercu';
import { log, versHex } from './calcul';
import { donneesParDefaut, tailleVocabulaire } from './donnees';
import { configMini, nombreParametres } from './modele';
import { etatDeDepart, prenomAffiche, tableauAvantApres, tauxIndexParDefaut } from './pilote';
import { PRESETS_MINI } from './reglages';

describe('etatInitial', { timeout: 60_000 }, () => {
  it('le préréglage complet, au pas 0 : les mêmes nombres que le Python', () => {
    const e = etatInitial('complet');
    const d = donneesParDefaut();
    const v = tailleVocabulaire(d.vocabulaire);
    expect(e.preset).toBe('complet');
    expect(e.pasTotal).toBe(PRESETS_MINI.complet.pasTotal);
    expect(e.tailleVocabulaire).toBe(v);
    expect(e.tailleVocabulaire).toBe(attendus.modele.config.taille_vocabulaire);
    expect(e.nbParametres).toBe(nombreParametres(configMini(v)));
    expect(e.nbParametres).toBe(32 * v + 3328);
    expect(e.nbEntrainement).toBe(d.entrainement.length);
    expect(e.perteHasard).toBe(log(v));
    // Le pas 0 de l'entraînement complet, au bit près (attendus écrits par le Python).
    expect(versHex(e.perteValidation)).toBe(attendus.entrainement.validation_0);
    expect(e.echantillons.map((p) => p.texte)).toEqual(attendus.entrainement.echantillons_0);
    for (const p of e.echantillons) expect(p.existe, p.texte).toBe(d.connus.has(p.texte));
    // Un prénom vide (le modèle tire la fin tout de suite) reste un prénom vide, qui n'existe pas.
    expect(e.echantillons.some((p) => p.texte === '' && !p.existe)).toBe(true);
  });

  it('l’avant-goût : 600 pas, le même départ (le taux ne change rien au pas 0)', () => {
    const complet = etatInitial('complet');
    const avant = etatInitial('avant-gout');
    expect(avant.preset).toBe('avant-gout');
    expect(avant.pasTotal).toBe(PRESETS_MINI['avant-gout'].pasTotal);
    expect({ ...avant, preset: 'complet', pasTotal: complet.pasTotal }).toEqual(complet);
  });

  it('l’avant-goût : la colonne de gauche du tableau, ce sont les prénoms du pas 0', () => {
    // Le tableau que montre la page avant le lancement (MiniModele.svelte, préréglage avant-gout).
    const avant = etatInitial('avant-gout');
    const t = tableauAvantApres(etatDeDepart(avant, tauxIndexParDefaut('avant-gout')));
    const affichee = (c: { texte: string; existe: boolean }) => c.texte + (c.existe ? ' (existe déjà)' : '');
    const attendu = avant.echantillons.map((p) => prenomAffiche(p.texte) + (p.existe ? ' (existe déjà)' : ''));
    expect(t.lignes).toHaveLength(PRESETS_MINI['avant-gout'].nbEchantillons);
    expect(t.lignes.map((l) => affichee(l.depart))).toEqual(attendu);
    // Le pas 0 a un prénom vide : la case dit « (aucune lettre) ».
    expect(attendu).toContain('(aucune lettre)');
    expect(t.lignes.find((l) => l.depart.texte === '(aucune lettre)')?.depart.vide).toBe(true);
    // À droite, rien encore.
    expect(t.lignes.every((l) => l.fin === null)).toBe(true);
    expect(t.enTetes).toEqual(['Au départ, pas 0', 'Après l’entraînement']);
  });

  it('sérialisable : passe tel quel d’Astro à l’îlot', () => {
    for (const preset of ['complet', 'avant-gout'] as const) {
      const e = etatInitial(preset);
      expect(JSON.parse(JSON.stringify(e))).toEqual(e);
      expect(structuredClone(e)).toEqual(e);
      for (const valeur of Object.values(e)) {
        expect(['string', 'number', 'object']).toContain(typeof valeur);
      }
    }
  });

  it('calculé une fois par préréglage, et figé', () => {
    expect(etatInitial('complet')).toBe(etatInitial('complet'));
    const e = etatInitial('complet');
    expect(Object.isFrozen(e)).toBe(true);
    expect(Object.isFrozen(e.echantillons)).toBe(true);
    expect(Object.isFrozen(e.echantillons[0])).toBe(true);
  });

  it('refuse un préréglage inconnu', () => {
    expect(() => etatInitial('geant' as 'complet')).toThrow(/« complet » ou « avant-gout »/);
  });
});
