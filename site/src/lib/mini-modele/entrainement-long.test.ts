// Le test long : l'entraînement complet apprend vraiment.
//
// Les 3 000 pas du préréglage complet (quelques secondes ici, quelques
// minutes en Python pur). L'erreur de validation doit finir à 2,45 ou moins,
// et baisser d'au moins 1,0 depuis le départ. Les nombres sont aussi ceux du
// Python, au bit près : le test long de projets/mini-modele/tests/test_entrainement.py
// (« uv run pytest -q -m lent ») vérifie les mêmes motifs. Si le code change,
// relance-le, puis recopie ses nouvelles valeurs ici et là-bas. L'intégration
// continue ne lance pas ce test Python (trop long) : un test rapide, plus bas,
// relit ses trois constantes LONG_* dans test_entrainement.py et vérifie
// qu'elles sont celles d'ici.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { empreinte, versHex } from './calcul';
import { Entraineur, PRESETS_MINI } from './entrainement';

/** Le test long du Python (Vitest tourne dans site/). */
const TEST_PYTHON = new URL('../../../../projets/mini-modele/tests/test_entrainement.py', import.meta.url);

const VALIDATION_DEPART = '400d39161fba8940';
const VALIDATION_FIN = '40014367b7b1cd81';
const PARAMS_EMPREINTE = '1637bfe4';

describe('les motifs du test long, les mêmes qu’en Python', () => {
  it('les trois constantes LONG_* de test_entrainement.py valent celles d’ici', () => {
    const source = readFileSync(TEST_PYTHON, 'utf8').replace(/\r\n/g, '\n');
    /** La valeur de « NOM = "…" », seule sur sa ligne, dans le test Python. */
    const constante = (nom: string): string => {
      const trouve = new RegExp(`^${nom} = "([0-9a-f]+)"$`, 'm').exec(source);
      if (trouve === null) {
        throw new Error(`${nom} = "…" introuvable dans test_entrainement.py : la constante a-t-elle changé de nom ou de forme ?`);
      }
      return trouve[1];
    };
    expect(constante('LONG_VALIDATION_DEPART')).toBe(VALIDATION_DEPART);
    expect(constante('LONG_VALIDATION_FIN')).toBe(VALIDATION_FIN);
    expect(constante('LONG_PARAMS_EMPREINTE')).toBe(PARAMS_EMPREINTE);
  });
});

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
