// Le test long : l'entraînement complet apprend vraiment.
//
// Les 3 000 pas du préréglage complet (quelques secondes ici, quelques
// minutes en Python pur). L'erreur de validation doit finir à 2,45 ou moins,
// et baisser d'au moins 1,0 depuis le départ. Les nombres sont aussi ceux du
// Python, au bit près : le test long de projets/mini-modele/tests/test_entrainement.py
// (« uv run pytest -q -m lent ») vérifie les mêmes motifs. Si le code change,
// relance-le, puis recopie ses nouvelles valeurs ici et là-bas.

import { describe, expect, it } from 'vitest';
import { empreinte, versHex } from './calcul';
import { Entraineur, PRESETS_MINI } from './entrainement';

const VALIDATION_DEPART = '400d39161fba8940';
const VALIDATION_FIN = '40014367b7b1cd81';
const PARAMS_EMPREINTE = '1637bfe4';

describe('l’entraînement complet', () => {
  it('apprend vraiment : 2,45 ou moins, et au moins 1,0 de moins qu’au départ', { timeout: 180_000 }, () => {
    const r = PRESETS_MINI.complet;
    const e = new Entraineur(r);
    const depart = e.perteValidation();
    while (e.pas < r.pasTotal) e.faireUnPas();
    const fin = e.perteValidation();
    console.log(`perte de validation : ${depart} au départ, ${fin} au pas ${e.pas}`);
    expect(e.diverge).toBe(false);
    expect(fin).toBeLessThanOrEqual(2.45);
    expect(depart - fin).toBeGreaterThanOrEqual(1.0);
    // Les mêmes bits qu'en Python.
    expect(versHex(depart)).toBe(VALIDATION_DEPART);
    expect(versHex(fin)).toBe(VALIDATION_FIN);
    expect(empreinte(e.params)).toBe(PARAMS_EMPREINTE);
  });
});
