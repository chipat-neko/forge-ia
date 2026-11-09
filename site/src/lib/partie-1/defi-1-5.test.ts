// Le défi de l'atelier du chapitre 1.5 : ses pertes viennent du moteur du mini-modèle, au bit près
// celles que la démo affiche au dernier pas (le même Entraineur, les mêmes réglages, la même
// graine). Chaque entraînement complet prend quelques secondes : le résultat est calculé une fois.

import { describe, expect, it } from 'vitest';
import { Entraineur, PRESETS_MINI, TAUX_PROPOSES } from '../mini-modele/entrainement';
import { resultatDuDefi, TAUX_DU_DEFI } from './defi-1-5';
import { ECART_DU_DEFI } from './paris-1-5';

describe('le défi de l’atelier', () => {
  it('ses taux : celui du préréglage complet, puis les taux proposés plus grands que lui', () => {
    const defaut = PRESETS_MINI.complet.tauxMax;
    expect(TAUX_DU_DEFI.defaut).toBe(defaut);
    expect(TAUX_DU_DEFI.plusGrands).toStrictEqual(TAUX_PROPOSES.filter((t) => t > defaut));
    expect(TAUX_DU_DEFI.plusGrands.length).toBeGreaterThanOrEqual(2);
  });

  it(
    'sa réponse vient des pertes du moteur : au dernier pas, la même erreur que la démo',
    { timeout: 180_000 },
    () => {
      const r = resultatDuDefi();
      // Calculé une fois, puis gardé.
      expect(resultatDuDefi()).toBe(r);
      // L'erreur du taux par défaut, refaite ici comme la démo la calcule au dernier pas.
      const e = new Entraineur(PRESETS_MINI.complet);
      while (e.pas < PRESETS_MINI.complet.pasTotal) e.faireUnPas();
      expect(e.diverge).toBe(false);
      expect(r.defaut).toStrictEqual({ taux: PRESETS_MINI.complet.tauxMax, fin: e.perteValidation() });
      // La réponse réussit, le taux suivant échoue : c'est bien le plus grand qui réussit.
      expect(r.reponse.taux).toBeGreaterThan(r.defaut.taux);
      expect(r.reponse.fin).toBeLessThanOrEqual(r.defaut.fin + ECART_DU_DEFI);
      expect(r.suivant).not.toBeNull();
      expect(r.suivant!.taux).toBeGreaterThan(r.reponse.taux);
      expect(r.suivant!.fin > r.defaut.fin + ECART_DU_DEFI).toBe(true);
      // Mesuré le 9 novembre 2026 : 0,03 réussit, 0,1 échoue. Si le moteur change, la page suit
      // d'elle-même ; ce test dit alors de relire le texte du défi.
      expect([r.reponse.taux, r.suivant!.taux], 'le défi a changé de réponse : relis son texte dans 1-5.mdx').toStrictEqual([0.03, 0.1]);
    },
  );
});
