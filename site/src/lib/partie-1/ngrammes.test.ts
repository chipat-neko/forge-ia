// Le jumeau du modèle à n-grammes : ngrammes.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (FICHIERS_PARTIE_1.ngrammes,
// projets/1.1-modele-de-langage/tests/attendus.json) est écrit par
// `uv run python -m modele_de_langage.attendus`. Le jumeau doit retrouver les
// mêmes caractères, les mêmes comptes et les mêmes probabilités, au bit près
// (toStrictEqual). Seules les perplexités ne sont pas refaites : le site les lit
// telles quelles (PERPLEXITES, texte-1-1.ts).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FICHIERS_PARTIE_1, partieRefaite } from './fichiers';
import {
  alphabet,
  compter,
  couper,
  distribution,
  generer,
  MESSAGE_CONTEXTE_COURT,
  MESSAGE_TEMPERATURE,
  MESSAGE_TEXTE_VIDE,
  ORDRE_MAX,
  partJamaisVue,
  poids,
  TEMPERATURES,
  tirer,
  tourneEnRond,
} from './ngrammes';
import { CALCULS_PARTIE_1, refaireNgrammes, type EntreesNgrammes } from './parite';
import { ALPHABET, PERPLEXITES, TEXTE_DU_SITE } from './texte-1-1';

interface AttendusNgrammes extends EntreesNgrammes {
  alphabet: string[];
  ordres: {
    n: number;
    perplexite_entrainement: number;
    perplexite_validation: number;
    jamais_vus: [number, number];
    distributions: { contexte: string; rangs: [string, number][] }[];
  }[];
  suites: { n: number; temperature: number; graine: number; depart: string; longueur: number; suite: string }[];
  cas_limites: {
    nom: string;
    texte: string;
    n: number;
    contexte: string;
    alphabet: string[];
    coupe: [string, string];
    comptes: [string, [string, number][]][];
    distribution: [string, number][] | null;
    erreur: string | null;
    suite: string | null;
    erreur_suite: string | null;
  }[];
}

/** Les fichiers, lus depuis site/, d'où Vitest est lancé. */
const CHEMIN_TEXTE = '../projets/1.1-modele-de-langage/donnees/texte-du-site.txt';
const TEXTE: string = readFileSync(CHEMIN_TEXTE, 'utf8');
const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.ngrammes}`, 'utf8')) as AttendusNgrammes;

/** Le message d'erreur levé par la fonction, ou null si elle n'en lève pas. */
function messageDErreur(f: () => unknown): string | null {
  try {
    f();
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : String(e);
  }
}

describe('jumeau du Python : les attendus partagés de 1.1', () => {
  const [entrainement, validation] = couper(TEXTE);
  const lettres = alphabet(TEXTE);

  it('le texte du module est celui du fichier du projet, et son alphabet celui des attendus', () => {
    expect(TEXTE_DU_SITE).toBe(TEXTE);
    expect(TEXTE.length).toBeGreaterThanOrEqual(60_000);
    expect(lettres).toStrictEqual(ATTENDUS.alphabet);
    expect(ALPHABET).toStrictEqual(ATTENDUS.alphabet);
  });

  it('couper : 90 % pour apprendre, le reste pour vérifier, en points de code', () => {
    expect(couper('0123456789')).toStrictEqual(['012345678', '9']);
    expect(couper('')).toStrictEqual(['', '']);
    expect(Array.from(entrainement)).toHaveLength(Math.floor((Array.from(TEXTE).length * 9) / 10));
    expect(entrainement + validation).toBe(TEXTE);
  });

  it('ordres : les contextes jamais vus et les dix caractères les plus probables de chaque contexte', () => {
    expect(ATTENDUS.ordres.map((o) => o.n)).toStrictEqual([0, 1, 2, 3, 4, 5, 6]);
    for (const o of ATTENDUS.ordres) {
      const comptes = compter(entrainement, o.n);
      expect(partJamaisVue(comptes, validation, o.n), `jamais vus, n = ${o.n}`).toStrictEqual(o.jamais_vus);
      expect(o.distributions).toHaveLength(6);
      for (const d of o.distributions) {
        const rangs = distribution(comptes, lettres, d.contexte, o.n).slice(0, 10);
        expect(rangs, `n = ${o.n}, contexte ${JSON.stringify(d.contexte)}`).toStrictEqual(d.rangs);
      }
    }
  });

  it('suites : le texte écrit, pour chaque ordre, chaque température et chaque graine', () => {
    expect(ATTENDUS.suites).toHaveLength(ORDRE_MAX * TEMPERATURES.length * 2);
    for (const s of ATTENDUS.suites) {
      const comptes = compter(entrainement, s.n);
      expect(s.depart).toBe(Array.from(validation).slice(0, s.n).join(''));
      expect(generer(comptes, lettres, s.n, s.depart, s.longueur, s.temperature, s.graine)).toBe(s.suite);
    }
  });

  it('cas limites : texte vide, un caractère, un emoji, « İ », contextes jamais vus ou trop courts', () => {
    expect(ATTENDUS.cas_limites.map((c) => c.nom)).toHaveLength(8);
    for (const c of ATTENDUS.cas_limites) {
      const comptes = compter(c.texte, c.n);
      const lettresDuCas = alphabet(c.texte);
      expect(lettresDuCas, c.nom).toStrictEqual(c.alphabet);
      expect(couper(c.texte), c.nom).toStrictEqual(c.coupe);
      expect([...comptes].map(([k, v]) => [k, [...v]]), c.nom).toStrictEqual(c.comptes);
      let rangs: [string, number][] | null = null;
      const erreur = messageDErreur(() => {
        rangs = distribution(comptes, lettresDuCas, c.contexte, c.n);
      });
      expect(rangs, c.nom).toStrictEqual(c.distribution);
      expect(erreur, c.nom).toBe(c.erreur);
      let suite: string | null = null;
      const erreurSuite = messageDErreur(() => {
        suite = generer(comptes, lettresDuCas, c.n, c.contexte, 8, 1, 0);
      });
      expect(suite, c.nom).toBe(c.suite);
      expect(erreurSuite, c.nom).toBe(c.erreur_suite);
    }
  });

  it("refaireNgrammes refait tout le fichier, sauf les perplexités, à l'identique", () => {
    expect(refaireNgrammes(TEXTE, ATTENDUS)).toStrictEqual(partieRefaite('ngrammes', ATTENDUS as never));
  });

  it('PERPLEXITES lit celles du Python, dans l’ordre des n', () => {
    expect(PERPLEXITES.map((p) => p.n)).toStrictEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(PERPLEXITES.map((p) => p.validation)).toStrictEqual(ATTENDUS.ordres.map((o) => o.perplexite_validation));
    expect(PERPLEXITES.map((p) => p.entrainement)).toStrictEqual(ATTENDUS.ordres.map((o) => o.perplexite_entrainement));
  });

  it('la page de parité refait le fichier de FICHIERS_PARTIE_1, sous le même nom', () => {
    expect(Object.keys(CALCULS_PARTIE_1)).toStrictEqual(Object.keys(FICHIERS_PARTIE_1));
  });

  it('compter à l’ordre 6 sur le texte entier prend moins de 200 ms (médiane de 5 essais)', () => {
    const durees: number[] = [];
    for (let essai = 0; essai < 5; essai++) {
      const debut = performance.now();
      const comptes = compter(TEXTE, ORDRE_MAX);
      durees.push(performance.now() - debut);
      expect(comptes.size).toBeGreaterThan(1000);
    }
    durees.sort((a, b) => a - b);
    expect(durees[2], `durées en ms : ${durees.map((d) => d.toFixed(1)).join(', ')}`).toBeLessThan(200);
  });
});

describe('les mêmes exemples que les tests du Python', () => {
  it('compter et lissage de Laplace', () => {
    const c = compter('abab', 1);
    expect(c.get('a')).toStrictEqual(new Map([['b', 2]]));
    expect(c.get('b')).toStrictEqual(new Map([['a', 1]]));
    expect(new Map(distribution(c, ['a', 'b'], 'xa', 1))).toStrictEqual(
      new Map([
        ['b', 3 / 4],
        ['a', 1 / 4],
      ]),
    );
  });

  it('un contexte jamais vu donne la loi uniforme', () => {
    const c = compter('abab', 2);
    expect(distribution(c, ['a', 'b'], 'bb', 2)).toStrictEqual([
      ['a', 0.5],
      ['b', 0.5],
    ]);
  });

  it('les températures', () => {
    const cc = new Map([['b', 3]]);
    expect(poids(cc, ['a', 'b'], 1)).toStrictEqual([1, 4]);
    expect(poids(cc, ['a', 'b'], 0.5)).toStrictEqual([1, 16]);
    expect(poids(cc, ['a', 'b'], 2)).toStrictEqual([1, 2]);
    expect(poids(cc, ['a', 'b'], 0)).toStrictEqual([0, 1]);
    // Aucun compte, ou égalité : le plus petit point de code.
    expect(poids(new Map(), ['a', 'b'], 0)).toStrictEqual([1, 0]);
    expect(poids(new Map([['a', 2], ['b', 2]]), ['a', 'b'], 0)).toStrictEqual([1, 0]);
    expect(() => poids(new Map(), ['a'], 3)).toThrow(MESSAGE_TEMPERATURE);
  });

  it('tirer au bord, et sans poids positif', () => {
    expect(tirer([1, 1], 0.0)).toBe(0);
    expect(tirer([1, 1], 0.5)).toBe(1);
    expect(tirer([0, 1], 0.0)).toBe(1);
    expect(tirer([1, 4], 0.19999)).toBe(0);
    expect(tirer([1, 4], 0.2)).toBe(1);
    expect(() => tirer([0, 0], 0.5)).toThrow('Aucun poids positif');
    expect(() => tirer([], 0.5)).toThrow('Aucun poids positif');
  });

  it('texte vide, contexte trop court : les messages du Python, mot pour mot', () => {
    expect(MESSAGE_TEXTE_VIDE).toBe('Le texte est vide : il faut au moins un caractère.');
    expect(MESSAGE_CONTEXTE_COURT).toBe('Il faut au moins n caractères de contexte.');
    expect(() => distribution(new Map(), alphabet(''), '', 0)).toThrow(new RangeError(MESSAGE_TEXTE_VIDE));
    expect(() => generer(new Map(), [], 0, '', 5, 1, 0)).toThrow(MESSAGE_TEXTE_VIDE);
    expect(() => distribution(compter('abab', 2), ['a', 'b'], 'a', 2)).toThrow(MESSAGE_CONTEXTE_COURT);
  });

  it('generer : longueur nulle ou négative, température 0, départ trop court', () => {
    const c = compter('abab', 1);
    expect(generer(c, ['a', 'b'], 1, 'a', 0, 1, 0)).toBe('a');
    expect(generer(c, ['a', 'b'], 1, 'a', -3, 1, 0)).toBe('a');
    expect(generer(c, ['a', 'b'], 1, 'a', 4, 0, 0)).toBe('ababa');
    expect(() => generer(c, ['a', 'b'], 2, 'a', 4, 1, 0)).toThrow(MESSAGE_CONTEXTE_COURT);
  });

  it('les points de code, pas les unités UTF-16', () => {
    // « ～ » (U+FF5E) passe avant « 😀 » (U+1F600), alors que « < » les rangerait à l'envers.
    expect(alphabet('b😀a～a')).toStrictEqual(['a', 'b', '～', '😀']);
    expect(couper('😀😀😀😀😀😀😀😀😀😀')).toStrictEqual(['😀'.repeat(9), '😀']);
    expect(compter('😀a😀a', 1).get('😀')).toStrictEqual(new Map([['a', 2]]));
  });

  it('partJamaisVue et tourneEnRond', () => {
    const c = compter('abab', 2);
    expect(partJamaisVue(c, 'abbab', 2)).toStrictEqual([1, 3]);
    expect(partJamaisVue(c, 'ab', 2)).toStrictEqual([0, 0]);
    expect(tourneEnRond('xyz' + 'ab'.repeat(20))).toBe(true);
    expect(tourneEnRond('abcdefghijklmnopqrstuvwxyz0123456789')).toBe(false);
    expect(tourneEnRond('abab')).toBe(false);
    // Avec des caractères hors du premier plan : les positions restent cohérentes.
    expect(tourneEnRond('😀'.repeat(30))).toBe(true);
  });
});

describe('partieRefaite retire les perplexités, et refuse ce qui n’existe plus', () => {
  it('retire les deux clés de chaque ordre, et rien d’autre', () => {
    const refait = partieRefaite('ngrammes', ATTENDUS as never) as unknown as AttendusNgrammes;
    expect(Object.keys(refait.ordres[0])).toStrictEqual(['n', 'jamais_vus', 'distributions']);
    expect(Object.keys(refait)).toStrictEqual(Object.keys(ATTENDUS));
  });

  it('une clé ou une section absente arrête la comparaison', () => {
    expect(() => partieRefaite('ngrammes', { ordres: [{ n: 0 }] })).toThrow(/perplexite_entrainement/);
    expect(() => partieRefaite('ngrammes', {})).toThrow(/ordres/);
  });
});
