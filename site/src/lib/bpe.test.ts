import { describe, expect, it } from 'vitest';
import attendus from '../../../projets/1.3-tokenizer/tests/attendus.json';
import corpus from '../../../projets/1.3-tokenizer/donnees/corpus.txt?raw';
import {
  apprendre,
  choixNombreDeJetons,
  comparerPointsDeCode,
  preDecouper,
  TokenizerPedagogique,
  tokenizer13,
  visible,
} from './bpe';

describe('jumeau du Python : les attendus partagés', () => {
  it('le corpus est lu avec des fins de ligne LF', () => {
    expect(corpus).not.toContain('\r');
  });

  it('apprend exactement les mêmes 165 fusions que le Python', () => {
    const fusions = apprendre(corpus, 200);
    expect(fusions).toHaveLength(165);
    expect(fusions.map((f) => [f.a, f.b, f.compte])).toEqual(attendus.fusions);
  });

  it('découpe exactement comme le Python, jeton par jeton (texte, numéro, mot)', () => {
    expect(attendus.cas).toHaveLength(63);
    for (const c of attendus.cas) {
      const jetons = tokenizer13.decouper(c.texte, c.k).map((j) => [j.texte, j.id, j.mot]);
      expect(jetons, `texte ${JSON.stringify(c.texte)}, k = ${c.k}`).toEqual(c.jetons);
    }
  });

  it('tokenizer13 porte les mêmes fusions que le Python', () => {
    expect(tokenizer13.fusions.map((f) => [f.a, f.b, f.compte])).toEqual(attendus.fusions);
    expect(tokenizer13.base).toHaveLength(45);
  });
});

describe('preDecouper', () => {
  it('garde l’espace qui précède chaque mot', () => {
    expect(preDecouper('Le forgeron  frappe, 2026 !\nFin')).toEqual([
      'Le', ' forgeron', '  ', 'frappe', ',', ' 2026', ' !', '\nFin',
    ]);
  });

  it('renvoie une liste vide pour un texte vide', () => {
    expect(preDecouper('')).toEqual([]);
  });

  it('suit la propriété Unicode White_Space, comme le Python', () => {
    // U+0085 est une espace (White_Space) ; U+FEFF n’en est pas une.
    expect(preDecouper('a\u0085b')).toEqual(['a', '\u0085b']);
    expect(preDecouper('a﻿b')).toEqual(['a', '﻿', 'b']);
  });

  it('découpe un emoji en un seul pré-mot, sans couper la paire de substitution', () => {
    expect(preDecouper('a 🙂🙂 b')).toEqual(['a', ' 🙂🙂', ' b']);
  });
});

describe('comparerPointsDeCode', () => {
  it('trie par point de code, pas par unité UTF-16', () => {
    // 🙂 (U+1F642) s’écrit D83D DE42 en UTF-16, donc passerait avant U+FFFD.
    expect(['\u{1F642}', '\uFFFD'].sort(comparerPointsDeCode)).toEqual(['\uFFFD', '\u{1F642}']);
    expect(comparerPointsDeCode('\uFFFD', '\u{1F642}')).toBeLessThan(0);
    expect(comparerPointsDeCode('\u{1F642}', '\uFFFD')).toBeGreaterThan(0);
  });

  it('met un préfixe avant le mot plus long, et renvoie 0 pour deux textes égaux', () => {
    expect(comparerPointsDeCode('a', 'ab')).toBeLessThan(0);
    expect(comparerPointsDeCode('ab', 'a')).toBeGreaterThan(0);
    expect(comparerPointsDeCode('ab', 'ab')).toBe(0);
    expect(comparerPointsDeCode('', '')).toBe(0);
  });

  it('compare les lettres selon leur point de code', () => {
    expect(['é', 'e', 'z', 'E', ' '].sort(comparerPointsDeCode)).toEqual([' ', 'E', 'e', 'z', 'é']);
  });
});

describe('apprendre', () => {
  it('s’arrête quand aucune paire n’apparaît au moins 2 fois', () => {
    expect(apprendre('ab', 5)).toEqual([]);
    expect(apprendre('', 5)).toEqual([]);
    expect(apprendre('ab ab', 5)).toEqual([{ a: 'a', b: 'b', compte: 2 }]);
  });

  it('n’apprend pas plus de fusions que demandé', () => {
    expect(apprendre(corpus, 0)).toEqual([]);
    expect(apprendre(corpus, 3).map((f) => [f.a, f.b, f.compte])).toEqual([
      ['e', 's', 43], [' ', 'l', 27], ['e', 'n', 26],
    ]);
  });

  it('départage les égalités par la plus petite paire (a, b)', () => {
    // (a, b), (espace, b) et (b, a) sont vues 2 fois : (espace, b) est la plus petite.
    expect(apprendre('ab ab ba ba', 1)).toEqual([{ a: ' ', b: 'b', compte: 2 }]);
  });

  it('départage les égalités par point de code, pas par unité UTF-16', () => {
    // (🙂, 🙂) et (U+FFFD, U+FFFD) sont vues 2 fois chacune. Par point de code,
    // U+FFFD est plus petit ; par unité UTF-16, 🙂 le serait.
    const texte = '🙂🙂a🙂🙂a\uFFFD\uFFFDa\uFFFD\uFFFDa';
    expect(apprendre(texte, 1)).toEqual([{ a: '\uFFFD', b: '\uFFFD', compte: 2 }]);
  });

  it('fusionne de gauche à droite, sans chevauchement', () => {
    // « aaa » avec (a, a) donne « aa » + « a », pas « aa » + « aa ».
    const t = new TokenizerPedagogique('aaa aaa', 1);
    expect(t.fusions).toEqual([{ a: 'a', b: 'a', compte: 4 }]);
    expect(t.decouper('aaa', 1).map((j) => j.texte)).toEqual(['aa', 'a']);
    expect(t.decouper('aaaa', 1).map((j) => j.texte)).toEqual(['aa', 'aa']);
  });
});

describe('TokenizerPedagogique', () => {
  it('trie la base par point de code et numérote les fusions après elle', () => {
    expect(tokenizer13.base).toEqual([...tokenizer13.base].sort(comparerPointsDeCode));
    expect(new Set(tokenizer13.base).size).toBe(tokenizer13.base.length);
    const n = tokenizer13.base.length;
    // La première fusion (« e » + « s ») a pour numéro n + 0 ; « e » et « s » viennent de la base.
    const jetons = tokenizer13.decouper('es', 1);
    expect(jetons).toEqual([{ texte: 'es', id: n, mot: 0 }]);
    expect(tokenizer13.decouper('es', 0).map((j) => j.id)).toEqual(
      ['e', 's'].map((c) => tokenizer13.base.indexOf(c)),
    );
  });

  it('découpe un texte vide en aucun jeton', () => {
    expect(tokenizer13.decouper('', 30)).toEqual([]);
  });

  it('donne le numéro null à un caractère absent du corpus, sans planter', () => {
    const jetons = tokenizer13.decouper('🙂', 10);
    expect(jetons).toEqual([{ texte: '🙂', id: null, mot: 0 }]);
    // Un seul jeton pour l’emoji entier : pas deux moitiés de paire de substitution.
    expect(tokenizer13.decouper('a🙂b', 165).map((j) => j.texte)).toEqual(['a', '🙂', 'b']);
  });

  it('accepte les saisies inhabituelles : retours à la ligne, espaces multiples, texte seul d’espaces', () => {
    for (const texte of ['\n', '   ', 'a\r\nb', '\t\t', 'Le  forgeron\n\nfrappe', '\u0000', '\u{10FFFF}']) {
      const jetons = tokenizer13.decouper(texte, 100);
      expect(jetons.map((j) => j.texte).join('')).toBe(texte);
    }
  });

  it('ramène k dans l’intervalle [0, nombre de fusions]', () => {
    const phrase = 'Les forgerons découpent le texte en jetons.';
    expect(tokenizer13.decouper(phrase, -5)).toEqual(tokenizer13.decouper(phrase, 0));
    expect(tokenizer13.decouper(phrase, 1000)).toEqual(tokenizer13.decouper(phrase, 165));
    expect(tokenizer13.decouper(phrase, 0)).toHaveLength(43);
  });

  it('donne le numéro du pré-mot dont vient chaque jeton', () => {
    // À k = 0 : « a », « ␣b », « ␣c » donnent a | ␣ b | ␣ c, venus des mots 0, 1 et 2.
    expect(tokenizer13.decouper('a b c', 0).map((j) => [j.texte, j.mot])).toEqual([
      ['a', 0], [' ', 1], ['b', 1], [' ', 2], ['c', 2],
    ]);
  });

  it('découpe 10 000 caractères en moins de 500 ms', () => {
    const long = 'Le forgeron frappe le métal. '.repeat(345); // ~10 000 caractères
    expect(long.length).toBeGreaterThan(9900);
    const t0 = performance.now();
    const jetons = tokenizer13.decouper(long, 165);
    const duree = performance.now() - t0;
    expect(jetons.length).toBeGreaterThan(0);
    expect(jetons.map((j) => j.texte).join('')).toBe(long);
    expect(duree).toBeLessThan(500);
  });
});

describe('visible', () => {
  it('écrit l’espace « ␣ » et le retour à la ligne « ↵ »', () => {
    expect(visible(' le forgeron')).toBe('␣le␣forgeron');
    expect(visible('a\nb')).toBe('a↵b');
    expect(visible('  \n ')).toBe('␣␣↵␣');
    expect(visible('abc')).toBe('abc');
  });
});

describe('choixNombreDeJetons', () => {
  it('propose trois choix croissants, dont un seul juste', () => {
    expect(choixNombreDeJetons('les forgerons', 30)).toEqual([
      { texte: '2 jetons', juste: false },
      { texte: '9 jetons', juste: true },
      { texte: '13 jetons', juste: false },
    ]);
  });

  it('compte les pré-mots qui contiennent une lettre (pas la ponctuation ni les chiffres)', () => {
    // « Le » et « ␣forgeron » : 2 mots ; « , » et « ␣2026 » n'ont pas de lettre.
    // À k = 165 : L | e | ␣forger | on | , | ␣ | 2 | 0 | 2 | 6 = 10 jetons ; 17 caractères.
    expect(choixNombreDeJetons('Le forgeron, 2026', 165)).toEqual([
      { texte: '2 jetons', juste: false },
      { texte: '10 jetons', juste: true },
      { texte: '17 jetons', juste: false },
    ]);
  });

  it('compte les caractères en points de code (un emoji vaut 1)', () => {
    // 1 mot avec lettre ; à k = 165 : « le », « ␣ » et 4 emojis = 6 jetons ; 7 caractères.
    expect(choixNombreDeJetons('le 🙂🙂🙂🙂', 165)).toEqual([
      { texte: '1 jeton', juste: false },
      { texte: '6 jetons', juste: true },
      { texte: '7 jetons', juste: false },
    ]);
  });

  it('écrit « jeton » au singulier pour 0 ou 1', () => {
    expect(choixNombreDeJetons('reforgeronnes', 165).map((c) => c.texte)).toEqual([
      '1 jeton', '6 jetons', '13 jetons',
    ]);
  });

  it('lève une erreur quand deux valeurs sont égales', () => {
    // k = 0 : un jeton par caractère, donc jetons = caractères.
    expect(() => choixNombreDeJetons('les forgerons', 0)).toThrow(/autre exemple/);
    // Texte vide : tout vaut 0.
    expect(() => choixNombreDeJetons('', 30)).toThrow(/autre exemple/);
  });
});
