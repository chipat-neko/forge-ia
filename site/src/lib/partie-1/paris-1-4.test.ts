// Les paris du chapitre 1.4 et son atelier des paramètres : leurs bonnes réponses viennent des
// jumeaux (rope.ts, parametres.ts) et, pour le pari « residus », de la section residus des
// attendus du Python, lue sur le disque (le chapitre ne refait pas ce calcul).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { Choix } from '../choix';
import { formaterQuantite } from '../calculateur/formats';
import { CLES_FORGE, nombreParametres, PRESETS_FORGE } from '../calculateur/ton-ia';
import { pourcent } from '../nombres';
import { nombresDeTetes, repartitionParametres } from './parametres';
import {
  BASE_ROPE,
  choixOuSontLesParametres,
  choixResidus,
  choixRopeRapide,
  COUCHES_MAX,
  COUCHES_MIN,
  DIM_MAX,
  DIM_MIN,
  etatDeLAtelier,
  etatDuDefi,
  faitsDuPariParametres,
  faitsDuPariResidus,
  faitsDuPariRope,
  FIGURE_ROPE,
  PAS_DIM,
  phraseDeLAtelier,
  placeParmiLesTailles,
  POSITION_INITIALE,
  SEUIL_DU_DEFI,
  tetesVoisines,
  texteDegres,
  trancheDeLaRessemblance,
  TRANCHES_RESIDUS,
  type ResidusDuPari,
} from './paris-1-4';
import { anglesRope } from './rope';

const FINE = '\u202F';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/1.4-transformer/tests/attendus.json', 'utf8')) as {
  rope: { dim_tete: number; base: number; positions: number };
  residus: ResidusDuPari;
};
const RESIDUS = ATTENDUS.residus;
const CONFIG_PY = readFileSync('../projets/forge/forge/modele/config.py', 'utf8');

/** Le texte du seul choix juste ; échoue s'il n'y en a pas exactement un. */
function juste(choix: Choix[]): string {
  const justes = choix.filter((c) => c.juste === true);
  expect(justes, JSON.stringify(choix)).toHaveLength(1);
  return justes[0].texte;
}

/** Une copie modifiable de la section residus. */
const copie = (): ResidusDuPari => structuredClone(RESIDUS);

describe('la figure de RoPE', () => {
  it('a la tête et la base des attendus du Python, et la base de forge', () => {
    expect(FIGURE_ROPE.dimTete).toBe(ATTENDUS.rope.dim_tete);
    expect(FIGURE_ROPE.positionMax).toBe(ATTENDUS.rope.positions - 1);
    expect(BASE_ROPE).toBe(ATTENDUS.rope.base);
    expect(CONFIG_PY).toContain(`base_rope: float = ${BASE_ROPE.toFixed(1)}`);
    expect(POSITION_INITIALE).toBeGreaterThan(0);
    expect(POSITION_INITIALE).toBeLessThanOrEqual(FIGURE_ROPE.positionMax);
  });
});

describe('les angles de la figure, en degrés', () => {
  it('sans décimale à partir de 10°, une de 1 à 10°, deux en dessous', () => {
    expect(texteDegres(0)).toBe('0°');
    expect(texteDegres(1)).toBe('57°');
    expect(texteDegres(3)).toBe('172°');
    expect(texteDegres(0.3)).toBe('17°');
    expect(texteDegres(0.03)).toBe('1,7°');
    expect(texteDegres(0.003)).toBe('0,17°');
    expect(texteDegres(32)).toBe(`1${FINE}833°`);
  });
});

describe('le pari « rope »', () => {
  it('un seul juste, la paire 1, la plus rapide d’après anglesRope', () => {
    const choix = choixRopeRapide();
    expect(choix.map((c) => c.texte)).toStrictEqual(['La paire 1', 'La paire 4', 'Toutes au même pas']);
    expect(juste(choix)).toBe('La paire 1');
    const pas = anglesRope(1, FIGURE_ROPE.dimTete, BASE_ROPE);
    expect(pas[0]).toBeGreaterThan(pas[1]);
  });

  it('refuse une tête d’une seule paire : « la paire 1 » et « la dernière » seraient la même', () => {
    expect(() => choixRopeRapide(2)).toThrow(/Exemple devenu faux/);
  });

  it('les faits de l’explication : un radian par position pour la paire 1, mille fois moins pour la 4', () => {
    const f = faitsDuPariRope();
    const pas = anglesRope(1, FIGURE_ROPE.dimTete, BASE_ROPE);
    expect(f.radiansPaire1).toBe(pas[0]);
    expect(f.rapport).toBe(Math.round(pas[0] / pas[3]));
    expect(f.rapport).toBe(1000);
    // Une tête de ton IA : 64 valeurs (1 280 ÷ 20), 32 paires.
    const tete = PRESETS_FORGE.tres_grand.dim / PRESETS_FORGE.tres_grand.tetes;
    expect(f.dimTeteTonIA).toBe(tete);
    expect(f.pairesTonIA).toBe(tete / 2);
    const pasTonIA = anglesRope(1, tete, BASE_ROPE);
    expect(f.rapportTonIA).toBe(Math.round(pasTonIA[0] / pasTonIA[tete / 2 - 1]));
  });
});

describe('le pari « parametres »', () => {
  it('un seul juste, la plus grande part de repartitionParametres', () => {
    for (const cle of CLES_FORGE) {
      const r = repartitionParametres(PRESETS_FORGE[cle]);
      const plus = (['plongement', 'attention', 'mlp'] as const).reduce((a, b) => (r[b] > r[a] ? b : a));
      const textes = { plongement: 'Le plongement', attention: 'L’attention', mlp: 'Les MLP' };
      expect(juste(choixOuSontLesParametres(cle)), cle).toBe(textes[plus]);
    }
  });

  it('pour ton IA, ce sont les MLP ; pour mini, le plongement', () => {
    expect(juste(choixOuSontLesParametres())).toBe('Les MLP');
    expect(juste(choixOuSontLesParametres('tres_grand'))).toBe('Les MLP');
    expect(juste(choixOuSontLesParametres('mini'))).toBe('Le plongement');
  });

  it('les faits de l’explication viennent de repartitionParametres', () => {
    const f = faitsDuPariParametres('tres_grand');
    const r = repartitionParametres(PRESETS_FORGE.tres_grand);
    expect(f.total).toBe(PRESETS_FORGE.tres_grand.parametres);
    expect(f.repartition).toStrictEqual(r);
    expect(f.largeurCachee * 3 * PRESETS_FORGE.tres_grand.dim * PRESETS_FORGE.tres_grand.couches).toBe(r.mlp);
  });
});

describe('le pari « residus »', () => {
  it('lit la section residus des attendus : un seul juste, celui de la tranche du dernier bloc', () => {
    const choix = choixResidus(RESIDUS);
    expect(choix.map((c) => c.texte)).toStrictEqual([...TRANCHES_RESIDUS]);
    const dernier = RESIDUS.par_bloc.at(-1)!;
    expect(juste(choix)).toBe(TRANCHES_RESIDUS[trancheDeLaRessemblance(dernier.sans)]);
    expect(juste(choix)).toBe(`Elle se perd${FINE}: les deux textes sortent pareils`);
  });

  it('les tranches : moins de 0,5 ; de 0,5 à 0,999 ; au moins 0,999', () => {
    expect(trancheDeLaRessemblance(0.07)).toBe(0);
    expect(trancheDeLaRessemblance(-0.3)).toBe(0);
    expect(trancheDeLaRessemblance(0.5)).toBe(1);
    expect(trancheDeLaRessemblance(0.85)).toBe(1);
    expect(trancheDeLaRessemblance(0.999)).toBe(2);
    expect(trancheDeLaRessemblance(1)).toBe(2);
  });

  it('suit les attendus : une autre ressemblance, une autre bonne réponse', () => {
    const r = copie();
    r.par_bloc.at(-1)!.sans = 0.6;
    expect(juste(choixResidus(r))).toBe(TRANCHES_RESIDUS[1]);
  });

  it('les faits de l’explication, et leurs gardes', () => {
    const f = faitsDuPariResidus(RESIDUS);
    expect(f.couches).toBe(RESIDUS.par_bloc.length);
    expect(f.dernier).toStrictEqual(RESIDUS.par_bloc.at(-1));
    expect(f.premier).toStrictEqual(RESIDUS.par_bloc[0]);
    expect(f.milliardieme).toBe(1 - RESIDUS.par_bloc.at(-1)!.sans < 1e-9);
    expect(f.uniforme).toBe(1 / RESIDUS.jetons);
    // Avec le x +, les deux textes restent distincts ; sans, ils sortent pareils.
    const avecPareil = copie();
    avecPareil.par_bloc.at(-1)!.avec = 0.9999;
    expect(() => faitsDuPariResidus(avecPareil)).toThrow(/Exemple devenu faux/);
    const sansDistinct = copie();
    sansDistinct.par_bloc.at(-1)!.sans = 0.9;
    expect(() => faitsDuPariResidus(sansDistinct)).toThrow(/Exemple devenu faux/);
    const entreesPareilles = copie();
    entreesPareilles.entrees = 0.8;
    expect(() => faitsDuPariResidus(entreesPareilles)).toThrow(/Exemple devenu faux/);
    const attentionNette = copie();
    attentionNette.poids_attention_max = 0.5;
    expect(() => faitsDuPariResidus(attentionNette)).toThrow(/Exemple devenu faux/);
  });
});

describe('l’atelier des paramètres', () => {
  it('à l’arrivée, ton IA : le nombre de très grand, lu dans nombreParametres', () => {
    const f = PRESETS_FORGE.tres_grand;
    const e = etatDeLAtelier(f.dim, f.couches, f.tetes);
    expect(e.total).toBe(f.parametres);
    expect(e.total).toBe(
      nombreParametres({ tailleVocabulaire: f.vocabulaire, dim: f.dim, couches: f.couches, tetes: f.tetes, longueurContexte: f.contexte }),
    );
    expect(e.preset).toBe('tres_grand');
    expect(e.repartition).toStrictEqual(repartitionParametres(f));
  });

  it('chaque taille de forge se retrouve, avec son nombre', () => {
    for (const cle of CLES_FORGE) {
      const f = PRESETS_FORGE[cle];
      const e = etatDeLAtelier(f.dim, f.couches, f.tetes);
      expect(e.total, cle).toBe(f.parametres);
      expect(e.preset, cle).toBe(cle);
    }
    expect(etatDeLAtelier(512, 9, 8).preset).toBeNull();
  });

  it('les réglages couvrent les cinq tailles, et chaque largeur a des têtes possibles', () => {
    for (const cle of CLES_FORGE) {
      const f = PRESETS_FORGE[cle];
      expect(f.dim % PAS_DIM, cle).toBe(0);
      expect(f.dim >= DIM_MIN && f.dim <= DIM_MAX, cle).toBe(true);
      expect(f.couches >= COUCHES_MIN && f.couches <= COUCHES_MAX, cle).toBe(true);
    }
    for (let dim = DIM_MIN; dim <= DIM_MAX; dim += PAS_DIM) {
      const e = etatDeLAtelier(dim, COUCHES_MAX, nombresDeTetes(dim).at(-1)!);
      expect(e.tetesPossibles).toStrictEqual(nombresDeTetes(dim));
      expect(Number.isSafeInteger(e.total)).toBe(true);
    }
  });

  it('ne propose que des têtes qui partagent dim en parts paires', () => {
    for (let dim = DIM_MIN; dim <= DIM_MAX; dim += PAS_DIM) {
      for (const t of etatDeLAtelier(dim, 1, 1).tetesPossibles) {
        expect(dim % t, `${dim} / ${t}`).toBe(0);
        expect((dim / t) % 2, `${dim} / ${t}`).toBe(0);
      }
    }
    expect(() => etatDeLAtelier(1280, 20, 3)).toThrow(RangeError);
  });

  it('tetesVoisines garde le nombre s’il est possible, sinon prend le plus proche (le plus petit à égalité)', () => {
    expect(tetesVoisines(1280, 20)).toBe(20);
    expect(tetesVoisines(384, 20)).toBe(16);
    expect(nombresDeTetes(384)).toContain(16);
    expect(nombresDeTetes(384)).toContain(24);
    expect(tetesVoisines(64, 20)).toBe(16);
    expect(tetesVoisines(64, 1000)).toBe(32);
    for (let dim = DIM_MIN; dim <= DIM_MAX; dim += PAS_DIM) {
      for (const t of [1, 7, 20, 100]) expect(nombresDeTetes(dim)).toContain(tetesVoisines(dim, t));
    }
  });

  it('la phrase : le total, puis les trois grandes familles, de la plus lourde à la plus légère', () => {
    const f = PRESETS_FORGE.tres_grand;
    const e = etatDeLAtelier(f.dim, f.couches, f.tetes);
    const r = e.repartition;
    expect(phraseDeLAtelier(e)).toBe(
      `ton IA aurait ${e.totalTexte} paramètres${FINE}: ${pourcent(r.mlp / e.total)} dans les MLP, ` +
        `${pourcent(r.attention / e.total)} dans l’attention, ${pourcent(r.plongement / e.total)} dans le plongement.`,
    );
    const mini = PRESETS_FORGE.mini;
    expect(phraseDeLAtelier(etatDeLAtelier(mini.dim, mini.couches, mini.tetes))).toMatch(/: \d+\u202F% dans le plongement, /);
  });

  it('le défi : sous 100 millions, le MLP plus lourd que le plongement', () => {
    expect(SEUIL_DU_DEFI).toBe(100_000_000);
    const verifier = (dim: number, couches: number, tetes: number) => {
      const e = etatDeLAtelier(dim, couches, tetes);
      return e.total < SEUIL_DU_DEFI && e.repartition.mlp > e.repartition.plongement;
    };
    // Ton IA est trop grande ; petit a un MLP un peu plus léger que son plongement ; un bloc de plus suffit.
    for (const [dim, couches, tetes] of [
      [1280, 20, 20],
      [512, 8, 8],
      [512, 9, 8],
      [768, 12, 12],
      [64, 48, 2],
    ] as const) {
      const e = etatDeLAtelier(dim, couches, tetes);
      expect(etatDuDefi(e).reussi, `${dim}, ${couches}, ${tetes}`).toBe(verifier(dim, couches, tetes));
    }
    expect(etatDuDefi(etatDeLAtelier(512, 9, 8)).reussi).toBe(true);
    expect(etatDuDefi(etatDeLAtelier(512, 8, 8)).reussi).toBe(false);
    const reussi = etatDeLAtelier(512, 9, 8);
    expect(etatDuDefi(reussi).texte).toBe(
      `Défi réussi${FINE}: ${formaterQuantite(reussi.total)} de paramètres, et les MLP en portent plus que le plongement.`,
    );
    const tonIA = etatDeLAtelier(1280, 20, 20);
    expect(etatDuDefi(tonIA).texte).toBe(`Pas encore${FINE}: ${formaterQuantite(tonIA.total)} de paramètres, c’est plus de 100 millions.`);
    const petit = etatDeLAtelier(512, 8, 8);
    expect(etatDuDefi(petit).texte).toBe(
      `Pas encore${FINE}: les MLP portent ${formaterQuantite(petit.repartition.mlp)} de paramètres, ` +
        `le plongement ${formaterQuantite(petit.repartition.plongement)}.`,
    );
  });

  it('la place parmi les cinq tailles de forge', () => {
    const t = (dim: number, couches: number, tetes: number) => placeParmiLesTailles(etatDeLAtelier(dim, couches, tetes));
    expect(t(1280, 20, 20)).toBe(`C’est la taille «${FINE}très grand${FINE}» de forge.`);
    expect(t(512, 9, 8)).toBe(`Entre «${FINE}petit${FINE}» et «${FINE}moyen${FINE}».`);
    expect(t(64, 1, 1)).toBe(`Plus petite que «${FINE}mini${FINE}».`);
    expect(t(2048, 48, 16)).toBe(`Plus grande que «${FINE}très grand${FINE}».`);
    // Le même nombre de têtes ne change pas le total : 1 280, 20 blocs et 10 têtes ont le total de très grand.
    expect(t(1280, 20, 10)).toBe(`Autant de paramètres que «${FINE}très grand${FINE}», avec d’autres têtes.`);
  });
});
