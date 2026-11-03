// Le mini-transformer : disposition, passe avant, perte, passe arrière, génération.
//
// Jumeau de projets/mini-modele/tests/test_modele.py. Les attendus sont écrits
// par le Python (tests/attendus-modele.json, clé « modele ») : la perte d'un
// lot, tout son gradient (dans une empreinte), la perte de validation et les
// prénoms inventés doivent être les mêmes, au bit près. Un seul ulp d'écart
// change un motif ou une empreinte, et le test échoue.

import { describe, expect, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-modele.json';
import { empreinte, Hasard, log, somme, versHex } from './calcul';
import { decoder, donneesParDefaut, tailleVocabulaire } from './donnees';
import {
  avant,
  configMini,
  disposition,
  ECART_TYPE_INIT,
  entropieCroisee,
  EPSILON_NORME,
  generer,
  initialiser,
  logitsSuivants,
  LONGUEUR_GENEREE_MAX,
  nombreParametres,
  perte,
  perteEtGradient,
  tirerNumero,
  type ConfigMini,
} from './modele';

// La configuration minuscule de test_modele.py, pour vérifier la passe arrière sur chaque paramètre.
const PETITE = configMini(5, { dim: 4, tetes: 2, contexte: 4, largeurMlp: 8 });
const PETITES_SEQUENCES = [
  [0, 1, 2, 0],
  [0, 3, 0],
];

function petitsParams(graine = 3): Float64Array {
  const h = new Hasard(graine);
  return Float64Array.from({ length: nombreParametres(PETITE) }, () => h.gaussienne(0.5));
}

function hex(valeurs: ArrayLike<number>): string[] {
  return Array.from(valeurs, (v) => versHex(v));
}

/** Le plus grand écart entre le gradient calculé et la pente mesurée, avec la limite de chaque paramètre. */
function comparerAuxDifferencesFinies(
  c: ConfigMini,
  params: Float64Array,
  seqs: number[][],
  limite: (numerique: number) => number,
): number {
  const g = new Float64Array(params.length);
  perteEtGradient(c, params, seqs, g);
  let pire = 0;
  for (let i = 0; i < params.length; i++) {
    const plus = params.slice();
    plus[i] += 1e-6;
    const moins = params.slice();
    moins[i] -= 1e-6;
    const numerique = (perte(c, plus, seqs) - perte(c, moins, seqs)) / 2e-6;
    const ecart = Math.abs(g[i] - numerique);
    expect(ecart, `paramètre ${i} : ${g[i]} calculé, ${numerique} mesuré`).toBeLessThanOrEqual(limite(numerique));
    if (ecart > pire) pire = ecart;
  }
  return pire;
}

describe('jumeau du Python : attendus-modele.json, clé « modele », au bit près', () => {
  const a = attendus.modele;
  const d = donneesParDefaut();
  const c = configMini(tailleVocabulaire(d.vocabulaire));
  const params = initialiser(c, new Hasard(a.graine));
  const lot = d.entrainement.slice(0, 8);
  const gradient = new Float64Array(params.length);
  const perteLot = perteEtGradient(c, params, lot, gradient);

  it('la configuration, avec les noms du Python, et le nombre de paramètres', () => {
    expect({
      taille_vocabulaire: c.tailleVocabulaire,
      dim: c.dim,
      tetes: c.tetes,
      contexte: c.contexte,
      largeur_mlp: c.largeurMlp,
    }).toEqual(a.config);
    expect(a.graine).toBe(1234);
    expect(nombreParametres(c)).toBe(a.nb_parametres);
    expect(params.length).toBe(a.nb_parametres);
  });

  it('les paramètres de départ', () => {
    expect(empreinte(params)).toBe(a.init_empreinte);
    expect(hex(params.slice(0, 8))).toEqual(a.init_premiers);
  });

  it('le lot : les 8 premières séquences d’entraînement', () => {
    expect(lot.map((s) => [...s])).toEqual(a.lot);
  });

  it('la perte du lot et tout son gradient', () => {
    expect(versHex(perteLot)).toBe(a.perte_lot);
    // La perte de chaque position : un ulp d'écart sur l'une d'elles disparaîtrait souvent dans la moyenne.
    const pertesPositions: number[] = [];
    for (const seq of lot) {
      const passe = avant(c, params, seq.slice(0, -1));
      for (let t = 0; t < seq.length - 1; t++) pertesPositions.push(entropieCroisee(passe[t].logits, seq[t + 1]));
    }
    expect(empreinte(pertesPositions)).toBe(a.pertes_positions_empreinte);
    expect(empreinte(gradient)).toBe(a.gradient_empreinte);
    expect(hex(gradient.slice(0, 8))).toEqual(a.gradient_premiers);
  });

  it('la perte sur les 256 premiers prénoms de validation', () => {
    expect(versHex(perte(c, params, d.validation.slice(0, 256)))).toBe(a.perte_validation_256);
  });

  it('les 8 prénoms inventés avec Hasard(1236)', () => {
    expect(generer(c, params, new Hasard(1236), 8).map((p) => decoder(p, d.vocabulaire))).toEqual(a.generes);
  });

  it('toutes les clés des attendus sont comparées', () => {
    expect(Object.keys(attendus)).toContain('modele');
    expect(Object.keys(a).sort()).toEqual(
      [
        'config',
        'graine',
        'nb_parametres',
        'init_empreinte',
        'init_premiers',
        'lot',
        'perte_lot',
        'pertes_positions_empreinte',
        'gradient_empreinte',
        'gradient_premiers',
        'perte_validation_256',
        'generes',
      ].sort(),
    );
  });
});

describe('la forme du modèle', () => {
  it('4 192 paramètres pour V = 27, et 32·V + 3 328 pour les prénoms', () => {
    expect(nombreParametres(configMini(27))).toBe(4192);
    const v = tailleVocabulaire(donneesParDefaut().vocabulaire);
    expect(nombreParametres(configMini(v))).toBe(32 * v + 3328);
    expect(nombreParametres(PETITE)).toBe(184);
  });

  it('les constantes et les valeurs par défaut', () => {
    expect(ECART_TYPE_INIT).toBe(0.08);
    expect(EPSILON_NORME).toBe(1e-5);
    expect(LONGUEUR_GENEREE_MAX).toBe(15);
    expect(configMini(40)).toEqual({ tailleVocabulaire: 40, dim: 16, tetes: 4, contexte: 16, largeurMlp: 64 });
    expect(Object.isFrozen(configMini(40))).toBe(true);
  });

  it('refuse des têtes de tailles inégales, en disant quoi changer', () => {
    expect(() => configMini(40, { dim: 10, tetes: 4 })).toThrow(/multiple de tetes.*Change dim ou tetes/);
    for (const mauvais of [{ dim: 0 }, { tetes: 0 }, { contexte: -1 }, { largeurMlp: 2.5 }]) {
      expect(() => configMini(40, mauvais), JSON.stringify(mauvais)).toThrow(/entier positif/);
    }
    expect(() => configMini(0)).toThrow(/entier positif/);
  });

  it('la disposition : les matrices dans l’ordre, sans trou ni chevauchement', () => {
    const c = configMini(40);
    const places = disposition(c);
    expect(Object.keys(places)).toEqual([
      'plongement',
      'positions',
      'requetes',
      'cles',
      'valeurs',
      'sortie_attention',
      'mlp_haut',
      'mlp_bas',
      'tete_de_lecture',
    ]);
    expect(places.plongement).toEqual([0, 40, 16]);
    expect(places.positions).toEqual([640, 16, 16]);
    expect(places.requetes).toEqual([896, 16, 16]);
    expect(places.mlp_haut).toEqual([1920, 16, 64]);
    expect(places.mlp_bas).toEqual([2944, 64, 16]);
    expect(places.tete_de_lecture).toEqual([3968, 16, 40]);
    let fin = 0;
    for (const [debut, lignes, colonnes] of Object.values(places)) {
      expect(debut).toBe(fin);
      fin = debut + lignes * colonnes;
    }
    expect(fin).toBe(nombreParametres(c));
  });

  it('initialiser tire une gaussienne de 0,08 par paramètre, dans l’ordre', () => {
    const c = configMini(40);
    const p = initialiser(c, new Hasard(1234));
    expect(p).toBeInstanceOf(Float64Array);
    expect(p.length).toBe(nombreParametres(c));
    const h = new Hasard(1234);
    expect(hex(p.slice(0, 20))).toEqual(Array.from({ length: 20 }, () => versHex(h.gaussienne(0.08))));
    expect(initialiser(c, new Hasard(1234))).toEqual(p);
    expect(initialiser(c, new Hasard(1235))).not.toEqual(p);
  });
});

describe('la passe arrière', () => {
  it('suit la pente mesurée par différences finies (limite du plan : 1e-5)', () => {
    comparerAuxDifferencesFinies(PETITE, petitsParams(3), PETITES_SEQUENCES, () => 1e-5);
  });

  it('suit la pente mesurée de près : un terme oublié ou faux se verrait', () => {
    for (const [graine, seqs] of [
      [3, PETITES_SEQUENCES],
      [8, [[0, 4, 4, 1, 0], [0, 2, 0], [0, 1, 3, 0]]],
    ] as const) {
      const params = petitsParams(graine);
      const g = new Float64Array(params.length);
      perteEtGradient(PETITE, params, seqs.map((s) => [...s]), g);
      expect(somme(Array.from(g, Math.abs))).toBeGreaterThan(1.0);
      const pire = comparerAuxDifferencesFinies(PETITE, params, seqs.map((s) => [...s]), (n) => 1e-8 + 1e-6 * Math.abs(n));
      expect(pire).toBeLessThan(1e-8);
    }
  });

  it('remet le gradient à zéro, sans changer la perte ni les paramètres', () => {
    const params = petitsParams();
    const g = new Float64Array(params.length);
    perteEtGradient(PETITE, params, PETITES_SEQUENCES, g);
    const sale = new Float64Array(params.length).fill(123.0);
    const valeur = perteEtGradient(PETITE, params, PETITES_SEQUENCES, sale);
    expect(hex(sale)).toEqual(hex(g));
    expect(versHex(valeur)).toBe(versHex(perte(PETITE, params, PETITES_SEQUENCES)));
    expect(params).toEqual(petitsParams());
  });

  it('une entrée refusée laisse le gradient intact : les vérifications passent avant la remise à zéro', () => {
    const params = petitsParams();
    const plus = new Float64Array(params.length + 1);
    plus.set(params);
    const cas: [Float64Array, number[][], RegExp][] = [
      [params.slice(0, -1), PETITES_SEQUENCES, /paramètres/],
      [plus, PETITES_SEQUENCES, /paramètres/],
      [params, [[0, 1, 2, 3, 1, 0]], /contexte/],
      [params, [[0, 5, 0]], /Numéro hors du vocabulaire/],
      [params, [[0]], /au moins deux numéros/],
      [params, [], /aucune séquence/],
    ];
    for (const [mauvais, sequences, message] of cas) {
      const sale = new Float64Array(params.length).fill(123.0);
      expect(() => perteEtGradient(PETITE, mauvais, sequences, sale)).toThrow(message);
      expect(Array.from(sale).every((x) => x === 123.0), String(message)).toBe(true);
    }
  });

  it('le gradient du lot est la somme de ceux des séquences, pesée par leurs positions', () => {
    const params = petitsParams();
    const [a, b] = PETITES_SEQUENCES;
    const ga = new Float64Array(params.length);
    const gb = new Float64Array(params.length);
    const gab = new Float64Array(params.length);
    perteEtGradient(PETITE, params, [a], ga);
    perteEtGradient(PETITE, params, [b], gb);
    perteEtGradient(PETITE, params, [a, b], gab);
    for (let i = 0; i < params.length; i++) {
      const attendu = (3 * ga[i] + 2 * gb[i]) / 5;
      expect(Math.abs(gab[i] - attendu), String(i)).toBeLessThanOrEqual(1e-12 * Math.abs(attendu) + 1e-13);
    }
  });

  it('les lignes jamais lues ont un gradient nul', () => {
    const params = petitsParams();
    const g = new Float64Array(params.length);
    perteEtGradient(PETITE, params, PETITES_SEQUENCES, g);
    const places = disposition(PETITE);
    const [plongement, , dim] = places.plongement;
    const positions = places.positions[0];
    expect(Array.from(g.slice(plongement + 4 * dim, plongement + 5 * dim))).toEqual([0, 0, 0, 0]);
    expect(Array.from(g.slice(positions + 3 * dim, positions + 4 * dim))).toEqual([0, 0, 0, 0]);
    expect(Array.from(g.slice(plongement, plongement + dim)).every((x) => x !== 0)).toBe(true);
  });
});

describe('la perte et la passe avant', () => {
  it('au départ, la perte est au niveau du hasard (ln V)', () => {
    const d = donneesParDefaut();
    const v = tailleVocabulaire(d.vocabulaire);
    const c = configMini(v);
    const p = initialiser(c, new Hasard(1234));
    expect(Math.abs(perte(c, p, d.validation.slice(0, 256)) - log(v))).toBeLessThan(0.15);
  });

  it('est somme(entropies croisées, dans l’ordre) / nombre, au bit près', () => {
    const params = petitsParams();
    const pertes: number[] = [];
    for (const seq of PETITES_SEQUENCES) {
      const passe = avant(PETITE, params, seq.slice(0, -1));
      for (let t = 0; t < seq.length - 1; t++) pertes.push(entropieCroisee(passe[t].logits, seq[t + 1]));
    }
    expect(versHex(perte(PETITE, params, PETITES_SEQUENCES))).toBe(versHex(somme(pertes) / 5));
  });

  it('est la moyenne de toutes les positions prédites', () => {
    const params = petitsParams();
    const [a, b] = PETITES_SEQUENCES;
    const attendu = (3 * perte(PETITE, params, [a]) + 2 * perte(PETITE, params, [b])) / 5;
    expect(Math.abs(perte(PETITE, params, [a, b]) - attendu)).toBeLessThanOrEqual(1e-14 * attendu);
    expect(perte(PETITE, params, [a, b])).toBe(perteEtGradient(PETITE, params, [a, b], null));
  });

  it('vaut −ln softmax(logits)[cible] sur une seule position', () => {
    const params = petitsParams();
    const logits = avant(PETITE, params, [0])[0].logits;
    const total = logits.reduce((s, l) => s + Math.exp(l), 0);
    const temoin = -Math.log(Math.exp(logits[2]) / total);
    expect(Math.abs(perte(PETITE, params, [[0, 2]]) - temoin)).toBeLessThanOrEqual(1e-14 * temoin);
  });

  it('le masque causal : une position ne voit que le passé', () => {
    const params = petitsParams();
    const p1 = avant(PETITE, params, [0, 1, 2, 3]);
    const p2 = avant(PETITE, params, [0, 1, 4, 1]);
    for (const t of [0, 1]) expect(hex(p1[t].logits)).toEqual(hex(p2[t].logits));
    expect(p1[2].logits).not.toEqual(p2[2].logits);
    for (let t = 0; t < 4; t++) {
      for (let h = 0; h < PETITE.tetes; h++) {
        expect(p1[t].poids[h].length).toBe(t + 1);
        expect(Math.abs(somme(p1[t].poids[h]) - 1.0)).toBeLessThanOrEqual(1e-15);
      }
    }
  });

  it('logitsSuivants donne les scores de la dernière position', () => {
    const params = petitsParams();
    expect(logitsSuivants(PETITE, params, [0, 3, 1])).toEqual(avant(PETITE, params, [0, 3, 1])[2].logits);
    expect(logitsSuivants(PETITE, params, [0]).length).toBe(PETITE.tailleVocabulaire);
  });

  it('vérifie ses entrées, avec les messages du Python', () => {
    const params = petitsParams();
    expect(() => perte(PETITE, params, [[0, 1, 2, 3, 1, 0]])).toThrow(/contexte/);
    expect(() => logitsSuivants(PETITE, params, [0, 1, 2, 3, 1])).toThrow(/contexte/);
    expect(() => perte(PETITE, params, [[0, 5, 0]])).toThrow(/Numéro hors du vocabulaire/);
    expect(() => perte(PETITE, params, [[0, -1, 0]])).toThrow(/Numéro hors du vocabulaire/);
    expect(() => perte(PETITE, params, [[0, 1.5, 0]])).toThrow(/Numéro hors du vocabulaire/);
    expect(() => perte(PETITE, params, [[0]])).toThrow(/au moins deux numéros/);
    expect(() => perte(PETITE, params, [])).toThrow(/aucune séquence/);
    expect(() => perte(PETITE, params.slice(0, -1), PETITES_SEQUENCES)).toThrow(/paramètres/);
    expect(() => perteEtGradient(PETITE, params, PETITES_SEQUENCES, new Float64Array(3))).toThrow(/gradient/);
    expect(() => logitsSuivants(PETITE, params, [])).toThrow(/au moins un numéro/);
  });
});

describe('la génération', () => {
  it('tirerNumero prend le premier indice où le seuil passe sous le cumul', () => {
    expect(tirerNumero([0.0, 0.0, 0.0, 0.0], new Hasard(5))).toBe(Math.floor(new Hasard(5).uniforme() * 4));
    const h6 = new Hasard(6);
    for (let i = 0; i < 200; i++) expect(tirerNumero([0.0, -1000.0, 0.0], h6)).not.toBe(1);
    const h7 = new Hasard(7);
    for (let i = 0; i < 50; i++) expect(tirerNumero([-50.0, 50.0, -50.0], h7)).toBe(1);
    // Un seuil que le cumul n'atteint jamais : le dernier numéro.
    expect(tirerNumero([0.0, 0.0, 0.0], { uniforme: () => 1.0 })).toBe(2);
  });

  it('invente des prénoms sans bord, de 15 caractères au plus, toujours les mêmes pour une graine', () => {
    const d = donneesParDefaut();
    const v = tailleVocabulaire(d.vocabulaire);
    const c = configMini(v);
    const params = initialiser(c, new Hasard(1234));
    const prenoms = generer(c, params, new Hasard(1236), 8);
    expect(prenoms.length).toBe(8);
    expect(prenoms.every((p) => !p.includes(0) && p.length <= 15)).toBe(true);
    expect(prenoms.flat().every((n) => n >= 1 && n < v)).toBe(true);
    expect(generer(c, params, new Hasard(1236), 8)).toEqual(prenoms);
    expect(generer(c, params, new Hasard(1237), 8)).not.toEqual(prenoms);
    expect(generer(c, params, new Hasard(1236), 0)).toEqual([]);
  });

  it('s’arrête à 15 caractères, ou quand le contexte est plein', () => {
    const c = configMini(40);
    const longueurs = generer(c, new Float64Array(nombreParametres(c)), new Hasard(2), 20).map((p) => p.length);
    expect(longueurs).toContain(15);
    expect(longueurs.every((n) => n <= 15)).toBe(true);
    const courtes = generer(PETITE, new Float64Array(nombreParametres(PETITE)), new Hasard(2), 60).map((p) => p.length);
    expect(courtes).toContain(4);
    expect(courtes.every((n) => n <= 4)).toBe(true);
  });

  it('refait la passe avant et tire chaque caractère, comme à la main', () => {
    const params = petitsParams();
    const h = new Hasard(9);
    const attendu: number[][] = [];
    for (let k = 0; k < 5; k++) {
      const ids = [0];
      while (ids.length - 1 < 4) {
        const n = tirerNumero(logitsSuivants(PETITE, params, ids), h);
        if (n === 0) break;
        ids.push(n);
      }
      attendu.push(ids.slice(1));
    }
    expect(generer(PETITE, params, new Hasard(9), 5)).toEqual(attendu);
  });
});
