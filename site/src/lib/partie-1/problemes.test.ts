// Le jumeau du générateur de problèmes et de la lecture d'une réponse (chapitre 1.9) retrouve le Python.
//
// - les listes de prénoms et d'objets, les voyelles, les billets, les lieux, les familles et leurs difficultés sont
//   relues dans forge.raisonnement.problemes (le texte même du Python) et comparées à celles du jumeau ;
// - les 70 problèmes des graines 0 à 4, les 28 des plages d'évaluation et de validation du RL, et les textes de
//   la lecture d'un nombre se comparent à projets/1.9-raisonnement/tests/attendus.json, sans tolérance ;
// - la trace de chaque problème est un calcul juste, étape par étape, qui finit sur la réponse.
//
// Le fichier d'attendus est celui de FICHIERS_PARTIE_1.raisonnement : la page de parité le refait aussi dans Chrome,
// Firefox et WebKit.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { CALCULS_PARTIE_1, refaireRaisonnement, type EntreesRaisonnement } from './parite';
import {
  ans,
  BILLETS,
  de,
  DIFFICULTES,
  ecrireFraction,
  estJuste,
  euros,
  extraireNombre,
  FAMILLES,
  FORMES,
  GENRES_DES_PRENOMS,
  genererProbleme,
  GRAINES_EVALUATION,
  GRAINES_VALIDATION_RL,
  LIEUX,
  OBJETS,
  PRENOMS_ENTRAINEMENT,
  PRENOMS_EVALUATION,
  PRENOMS_VALIDATION_RL,
  quantite,
  que,
  un,
  usageDeLaGraine,
  VOYELLES,
} from './problemes';

const PYTHON = readFileSync('../projets/forge/forge/raisonnement/problemes.py', 'utf8').replace(/\r\n/g, '\n');
const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.raisonnement}`, 'utf8')) as EntreesRaisonnement & {
  problemes: { famille: string; difficulte: number; graine: number; enonce: string; etapes: string[]; reponse: number }[];
  problemes_reserves: { famille: string; difficulte: number; graine: number; enonce: string; etapes: string[]; reponse: number }[];
  nombres: { texte: string; lu: string | null; verdicts: { attendu: number; terminee: boolean; juste: boolean }[] }[];
};

/** Le corps entre les parenthèses ou les crochets qui suivent `nom` dans le texte du Python. */
function corpsDe(nom: string, ouvrant: string, fermant: string): string {
  const debut = PYTHON.indexOf(nom);
  expect(debut, `${nom} dans problemes.py`).toBeGreaterThanOrEqual(0);
  const depart = PYTHON.indexOf(ouvrant, debut) + 1;
  const fin = PYTHON.indexOf(fermant, depart);
  return PYTHON.slice(depart, fin);
}

describe('les listes sont celles de forge, lues dans problemes.py', () => {
  it('les 30 prénoms et leur genre, dans le même ordre', () => {
    const corps = corpsDe('GENRES_DES_PRENOMS: tuple[tuple[str, str], ...] = (', '(', '\n)\n');
    const paires = [...corps.matchAll(/\("([^"]+)", "([fm])"\)/g)].map((m) => [m[1], m[2]]);
    expect(paires).toHaveLength(30);
    expect(GENRES_DES_PRENOMS.map(([n, g]) => [n, g])).toStrictEqual(paires);
    expect(PRENOMS_ENTRAINEMENT).toHaveLength(20);
    expect(PRENOMS_VALIDATION_RL).toStrictEqual(paires.slice(20, 24).map(([n]) => n));
    expect(PRENOMS_EVALUATION).toStrictEqual(paires.slice(24).map(([n]) => n));
    expect(PYTHON).toContain('PRENOMS_ENTRAINEMENT = PRENOMS[:20]');
    expect(PYTHON).toContain('PRENOMS_VALIDATION_RL = PRENOMS[20:24]');
    expect(PYTHON).toContain('PRENOMS_EVALUATION = PRENOMS[24:]');
  });

  it('les 20 objets : singulier, pluriel, genre et fourchette de prix, dans le même ordre', () => {
    const corps = corpsDe('OBJETS: tuple[Objet, ...] = (', '(', '\n)\n');
    const objets = [...corps.matchAll(/Objet\("([^"]+)", "([^"]+)", "([fm])", (\d+), (\d+)\)/g)].map((m) => ({
      singulier: m[1],
      pluriel: m[2],
      genre: m[3],
      prixMin: Number(m[4]),
      prixMax: Number(m[5]),
    }));
    expect(objets).toHaveLength(20);
    expect(OBJETS.map((o) => ({ ...o }))).toStrictEqual(objets);
  });

  it('les voyelles, les billets, les lieux, les familles et leurs difficultés', () => {
    expect(PYTHON).toContain(`_VOYELLES = "${VOYELLES}"`);
    expect(PYTHON).toContain(`_BILLETS = (${BILLETS.join(', ')})`);
    const lieux = [...PYTHON.slice(PYTHON.indexOf('_LIEUX = (')).split('\n')[0].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
    expect(LIEUX).toStrictEqual(lieux);
    expect(PYTHON).toContain(`FAMILLES = (${FAMILLES.map((f) => `"${f}"`).join(', ')})`);
    expect(PYTHON).toContain(`DIFFICULTES = (${DIFFICULTES.join(', ')})`);
    const formes = [...corpsDe('FORMES: dict[str, tuple[int, ...]] = {', '{', '\n}\n').matchAll(/"(\w+)": \(([\d, ]+?),?\)/g)].map((m) => [
      m[1],
      m[2].split(',').map((x) => Number(x.trim())),
    ]);
    expect(Object.entries(FORMES).map(([f, d]) => [f, [...d]])).toStrictEqual(formes);
    expect(formes).toHaveLength(6);
  });

  it('les plages de graines : un million chacune, trois usages', () => {
    for (const [nom, valeur] of [
      ['GRAINES_EVALUATION', GRAINES_EVALUATION],
      ['GRAINES_VALIDATION_RL', GRAINES_VALIDATION_RL],
    ] as const) {
      expect(PYTHON).toMatch(new RegExp(`${nom} = ${String(valeur).replace(/(\d)(?=(\d{3})+$)/g, '$1_')}`));
    }
    expect([0, 999_999, 1_000_000, 1_999_999, 2_000_000, 4_999_999, 5_000_000, 5_999_999, 6_000_000].map(usageDeLaGraine)).toStrictEqual([
      'entrainement', 'entrainement', 'evaluation', 'evaluation', 'entrainement', 'entrainement', 'validation_rl', 'validation_rl', 'entrainement',
    ]);
  });

  it('les gabarits du français : accord, élision, article', () => {
    expect(quantite(0, OBJETS[0])).toBe('0 pomme');
    expect(quantite(1, OBJETS[0])).toBe('1 pomme');
    expect(quantite(2, OBJETS[3])).toBe('2 gâteaux');
    expect(euros(1)).toBe('1 euro');
    expect(euros(2)).toBe('2 euros');
    expect(ans(0)).toBe('0 an');
    expect(ans(1)).toBe('1 an');
    expect(ans(30)).toBe('30 ans');
    expect(de('pommes')).toBe('de pommes');
    expect(de('oranges')).toBe("d'oranges");
    expect(de('œufs')).toBe("d'œufs");
    expect(de('Hugo')).toBe("d'Hugo");
    expect(de('Émile')).toBe("d'Émile");
    expect(que('Léa')).toBe('que Léa');
    expect(que('Alice')).toBe("qu'Alice");
    expect(que('Éva')).toBe("qu'Éva");
    expect(un(OBJETS[7])).toBe('un livre');
    expect(un(OBJETS[0])).toBe('une pomme');
  });
});

describe('les problèmes sont ceux du Python, mot pour mot', () => {
  it('les 70 problèmes des graines 0 à 4', () => {
    expect(ATTENDUS.problemes).toHaveLength(70);
    for (const p of ATTENDUS.problemes) {
      const g = genererProbleme(p.famille, p.difficulte, p.graine);
      expect(g, `${p.famille} ${p.difficulte} graine ${p.graine}`).toStrictEqual({
        id: `${p.famille}-${p.difficulte}-${p.graine}`,
        famille: p.famille,
        difficulte: p.difficulte,
        enonce: p.enonce,
        etapes: p.etapes,
        reponse: p.reponse,
      });
    }
  });

  it('les 28 problèmes des plages d’évaluation et de validation du RL, avec leurs prénoms', () => {
    expect(ATTENDUS.problemes_reserves).toHaveLength(28);
    for (const p of ATTENDUS.problemes_reserves) {
      const g = genererProbleme(p.famille, p.difficulte, p.graine);
      expect([g.enonce, g.etapes, g.reponse], `${p.famille} ${p.difficulte} graine ${p.graine}`).toStrictEqual([p.enonce, p.etapes, p.reponse]);
      const prenoms = p.graine === GRAINES_EVALUATION ? PRENOMS_EVALUATION : PRENOMS_VALIDATION_RL;
      expect(prenoms.some((n) => g.enonce.includes(n))).toBe(true);
    }
  });

  it('refaireRaisonnement et la page de parité rendent le fichier entier, section par section', () => {
    expect(Object.keys(CALCULS_PARTIE_1)).toContain('raisonnement');
    const refait = refaireRaisonnement(ATTENDUS);
    expect(refait).toStrictEqual(ATTENDUS);
    expect(CALCULS_PARTIE_1.raisonnement()).toStrictEqual(ATTENDUS);
  });

  it('le même problème d’une graine à l’autre appel, des problèmes différents d’une graine à l’autre', () => {
    expect(genererProbleme('achats', 3, 123)).toStrictEqual(genererProbleme('achats', 3, 123));
    const enonces = new Set(Array.from({ length: 50 }, (_, g) => genererProbleme('addition', 2, g).enonce));
    expect(enonces.size).toBeGreaterThan(45);
  });

  it('la trace est un calcul juste, étape par étape, et sa dernière étape est la réponse', () => {
    const operations: Record<string, (a: number, b: number) => number> = {
      '+': (a, b) => a + b,
      '−': (a, b) => a - b,
      '×': (a, b) => a * b,
      '÷': (a, b) => a / b,
    };
    let compte = 0;
    for (const famille of FAMILLES) {
      for (const difficulte of FORMES[famille]) {
        for (let graine = 0; graine < 60; graine++) {
          const p = genererProbleme(famille, difficulte, graine);
          for (const etape of p.etapes) {
            const m = /^(\d+) (\S) (\d+) = (\d+)$/.exec(etape);
            expect(m, etape).not.toBeNull();
            expect(operations[m![2]](Number(m![1]), Number(m![3])), etape).toBe(Number(m![4]));
          }
          expect(p.etapes[p.etapes.length - 1].endsWith(`= ${p.reponse}`)).toBe(true);
          expect(p.reponse).toBeGreaterThanOrEqual(0);
          // L'énoncé nomme au moins une personne, de la liste de son usage : c'est ce qui garde les usages disjoints.
          const prenoms = { entrainement: PRENOMS_ENTRAINEMENT, evaluation: PRENOMS_EVALUATION, validation_rl: PRENOMS_VALIDATION_RL }[usageDeLaGraine(graine)];
          expect(prenoms.some((n) => p.enonce.includes(n))).toBe(true);
          compte++;
        }
      }
    }
    expect(compte).toBe(14 * 60);
  });

  it('refuse un couple, une graine ou une difficulté qui n’existent pas, comme le Python', () => {
    expect(() => genererProbleme('division', 1, 0)).toThrow(/Famille inconnue : « division »/);
    expect(() => genererProbleme('toString', 1, 0)).toThrow(/Famille inconnue/);
    expect(() => genererProbleme('partage', 3, 0)).toThrow(/La difficulté 3 n’existe pas pour la famille « partage » : ses difficultés sont 1, 2/);
    expect(() => genererProbleme('addition', 1, -1)).toThrow(/La graine -1 doit être un entier/);
    expect(() => genererProbleme('addition', 1, 2 ** 32)).toThrow(/La graine/);
    expect(() => genererProbleme('addition', 1, 1.5)).toThrow(/La graine/);
    expect(genererProbleme('addition', 1, 2 ** 32 - 1).id).toBe(`addition-1-${2 ** 32 - 1}`);
  });
});

describe('extraireNombre lit comme extraire_nombre', () => {
  it('les textes du fichier : le nombre lu et le verdict de chaque réponse', () => {
    expect(ATTENDUS.nombres.length).toBeGreaterThanOrEqual(60);
    for (const { texte, lu, verdicts } of ATTENDUS.nombres) {
      const f = extraireNombre(texte);
      expect(f === null ? null : ecrireFraction(f), JSON.stringify(texte)).toBe(lu);
      for (const v of verdicts) expect(estJuste(texte, v.terminee, v.attendu), `${JSON.stringify(texte)} ${JSON.stringify(v)}`).toBe(v.juste);
    }
  });

  it('les écritures françaises d’un nombre', () => {
    const lire = (t: string): string | null => {
      const f = extraireNombre(t);
      return f === null ? null : ecrireFraction(f);
    };
    expect(lire('La réponse est 84.')).toBe('84');
    expect(lire('3 puis 7')).toBe('7');
    expect(lire('1 234 567')).toBe('1234567');
    expect(lire('1\u202f234\u202f567')).toBe('1234567');
    expect(lire('1\u00a0234')).toBe('1234');
    expect(lire('12 3456')).toBe('3456'); // « 12 » puis « 3456 »
    expect(lire('1 2 3')).toBe('3');
    expect(lire('12,5')).toBe('25/2');
    expect(lire('3.5')).toBe('7/2');
    expect(lire('3, puis 4')).toBe('4');
    expect(lire('-3')).toBe('-3');
    expect(lire('−3')).toBe('-3');
    expect(lire('x = -4')).toBe('-4');
    expect(lire('5-3')).toBe('3'); // la soustraction n’est pas un signe
    expect(lire('a-3')).toBe('3');
    expect(lire('trois')).toBeNull();
    expect(lire('')).toBeNull();
    expect(lire('٣')).toBeNull(); // un chiffre arabe n’est pas un chiffre : seuls 0 à 9 comptent
  });

  it('lit un très grand nombre exactement, sans flottant', () => {
    const f = extraireNombre('a' + '9'.repeat(40));
    expect(f).toStrictEqual({ numerateur: BigInt('9'.repeat(40)), denominateur: 1n });
    expect(extraireNombre('0,125')).toStrictEqual({ numerateur: 1n, denominateur: 8n });
    expect(extraireNombre('-0,5')).toStrictEqual({ numerateur: -1n, denominateur: 2n });
    expect(extraireNombre('-0')).toStrictEqual({ numerateur: 0n, denominateur: 1n });
  });

  it('une réponse coupée, sans nombre ou à l’attendu qui n’est pas un nombre n’est jamais juste', () => {
    expect(estJuste('84', true, 84)).toBe(true);
    expect(estJuste('84', false, 84)).toBe(false);
    expect(estJuste('rien', true, 4)).toBe(false);
    expect(estJuste('7', true, '7')).toBe(true);
    expect(estJuste('7', true, 'sept')).toBe(false);
    expect(estJuste('12,5', true, '25/2')).toBe(false); // l’attendu texte se lit comme un nombre : « 25/2 » est « 25 » puis « 2 »
    expect(estJuste('12,5', true, '12,5')).toBe(true);
    expect(() => estJuste('7', true, 7.5)).toThrow(TypeError);
    expect(() => estJuste('7', true, true as unknown as number)).toThrow(TypeError);
  });
});
