// Le jumeau du nettoyage : nettoyeur.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (FICHIERS_PARTIE_1.nettoyeur, projets/1.2-donnees/tests/attendus.json)
// est écrit par `uv run python -m donnees_pas_a_pas.attendus`. Le jumeau doit retrouver les
// mêmes textes nettoyés, les mêmes longueurs, les mêmes empreintes et les mêmes verdicts
// (toStrictEqual). Les pièges : les blancs de fin de Python (et pas ceux de trimEnd), les
// moitiés de paires de substitution, la longueur en points de code.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FICHIERS_PARTIE_1 } from './fichiers';
import {
  BLANCS_PYTHON,
  CHIFFRES_DE_LA_CLE,
  coderTexte,
  compterRaisons,
  decoderTexte,
  empreinte,
  empreinteDuTexteNettoye,
  estUnControleRetire,
  estValidation,
  garderPythonPermissif,
  LONGUEUR_MINIMALE,
  longueurPointsDeCode,
  nettoyer,
  normaliser,
  RAISONS,
  trier,
  type Verdict,
} from './nettoyeur';
import { CALCULS_PARTIE_1, refaireNettoyeur, type EntreesNettoyeur } from './parite';

interface Attendus extends EntreesNettoyeur {
  blancs_python: number[];
  textes: {
    nom: string;
    entree: unknown;
    nettoye: unknown;
    longueur: number;
    empreinte: string;
    validation: boolean;
  }[];
  licences: { ligne: Record<string, unknown>; garde: boolean }[];
  tris: { source: 'web_fr' | 'code_python'; lignes: Record<string, unknown>[]; verdicts: Verdict[] }[];
}

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const attendus = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.nettoyeur}`, 'utf8')) as Attendus;

const texte = (nom: string): string => {
  const trouve = attendus.textes.find((t) => t.nom === nom);
  if (!trouve) throw new Error(`texte de référence introuvable : ${nom}`);
  return decoderTexte(trouve.entree) as string;
};

describe('les blancs de Python', () => {
  it('sont ceux de str.isspace(), sur tous les points de code', () => {
    expect([...BLANCS_PYTHON]).toStrictEqual(attendus.blancs_python);
  });

  it('ne sont pas ceux de trimEnd() : U+FEFF reste, les autres partent', () => {
    const base = 'a'.repeat(210);
    expect(`${base}\uFEFF`.trimEnd()).toBe(base); // JavaScript le retire
    expect(normaliser(`${base}\uFEFF`)).toBe(`${base}\uFEFF`); // Python (et le jumeau) le gardent
    for (const point of [0x3000, 0x2028, 0xa0, 0x2009, 0x202f, 0x205f, 0x1680, 0x0a, 0x09, 0x20]) {
      expect(normaliser(base + String.fromCodePoint(point)), point.toString(16)).toBe(base);
    }
  });
});

describe('nettoyer', () => {
  it('rend, pour chaque texte de référence, le texte, la longueur, l’empreinte et la place du Python', async () => {
    expect(attendus.textes.length).toBeGreaterThan(30);
    for (const t of attendus.textes) {
      const entree = decoderTexte(t.entree) as string;
      const nettoye = nettoyer(entree);
      expect(nettoye, t.nom).toStrictEqual(t.nettoye === null ? null : (decoderTexte(t.nettoye) as string));
      expect(longueurPointsDeCode(normaliser(entree)), t.nom).toBe(t.longueur);
      const digest = await empreinte(entree);
      expect(digest, t.nom).toBe(t.empreinte);
      expect(estValidation(digest), t.nom).toBe(t.validation);
    }
  });

  it('garde 200 caractères et écarte 199, une fois nettoyé', () => {
    expect(LONGUEUR_MINIMALE).toBe(200);
    expect(nettoyer('a'.repeat(200))).toBe('a'.repeat(200));
    expect(nettoyer('a'.repeat(199))).toBeNull();
    expect(nettoyer(`${'a'.repeat(199)}\u00A0`)).toBeNull();
    expect(nettoyer(`${'a'.repeat(200)} `)).toBe('a'.repeat(200));
    // La frontière avec U+3000 (un blanc de Python) en fin de texte.
    expect(nettoyer(`${'a'.repeat(199)}\u3000`)).toBeNull();
    expect(nettoyer(`${'a'.repeat(200)}\u3000`)).toBe('a'.repeat(200));
  });

  it('compte en points de code : 200 emojis suffisent, alors que .length en voit 400', () => {
    const emojis = '\u{1F600}'.repeat(200);
    expect(emojis.length).toBe(400);
    expect(longueurPointsDeCode(emojis)).toBe(200);
    expect(nettoyer(emojis)).toBe(emojis);
    expect(nettoyer('\u{1F600}'.repeat(199))).toBeNull();
  });

  it('retire une moitié de paire de substitution, jamais une paire entière', () => {
    const moitie = `\uD83D${'a'.repeat(210)}\uDE00`;
    expect(nettoyer(moitie)).toBe('a'.repeat(210));
    const emoji = `${'a'.repeat(200)}\u{1F600}`;
    expect(nettoyer(emoji)).toBe(emoji);
    expect(longueurPointsDeCode('\uD800')).toBe(1);
  });

  it('retire les contrôles avant la forme NFC, et garde \\n et \\t', () => {
    expect(nettoyer('e\u0000\u0301'.repeat(210))).toBe('é'.repeat(210));
    expect(normaliser('a\r\nb\rc\td\u0085e\u007Ff')).toBe('a\nbc\tdef');
    expect(normaliser('e\u0301')).toBe('é');
    expect(normaliser('\u212B\uFB01')).toBe('Å\uFB01'); // NFC, pas NFKC : la ligature reste
  });

  it('nettoie un texte déjà nettoyé sans le changer', () => {
    for (const t of attendus.textes) {
      const nettoye = decoderTexte(t.nettoye);
      if (typeof nettoye === 'string') expect(nettoyer(nettoye), t.nom).toBe(nettoye);
    }
  });

  it('nettoie 100 000 caractères en moins de 200 ms (médiane de 5 essais)', () => {
    const grand = decoderTexte(attendus.textes.find((t) => t.nom === '100 000 x')?.entree) as string;
    expect(grand.length).toBe(100_000);
    nettoyer(grand); // échauffement
    const durees: number[] = [];
    for (let i = 0; i < 5; i++) {
      const debut = performance.now();
      const propre = nettoyer(grand);
      durees.push(performance.now() - debut);
      expect(propre).toBe(grand);
    }
    durees.sort((a, b) => a - b);
    expect(durees[2], `durées (ms) : ${durees.map((d) => d.toFixed(1)).join(', ')}`).toBeLessThan(200);
  });
});

describe('empreinte', () => {
  it('est le SHA-1 en hexadécimal, de l’UTF-8 du texte nettoyé', async () => {
    expect(await empreinteDuTexteNettoye('abc')).toBe('a9993e364706816aba3e25717850c26c9cd0d89d');
    expect(await empreinteDuTexteNettoye('')).toBe('da39a3ee5e6b4b0d3255bfef95601890afd80709');
    // « é » fait deux octets en UTF-8 : le SHA-1 du Python (hashlib) est le même.
    expect(await empreinteDuTexteNettoye('é')).toBe((await empreinte('e\u0301')));
  });

  it('est la même pour deux textes qui se nettoient pareil', async () => {
    const t = texte('web.jsonl, ligne 2');
    expect(await empreinte(t.replaceAll('\n', '\r\n'))).toBe(await empreinte(t));
    expect(await empreinte(`${t}  \u3000\n`)).toBe(await empreinte(t));
  });
});

describe('estValidation', () => {
  it('lit les 8 premiers chiffres hexadécimaux, contre part × 2³²', () => {
    // 0,005 × 2³² = 21 474 836,48 : 0x0147AE14 = 21 474 836 est dessous, 0x0147AE15 dessus.
    expect(estValidation('0147ae14' + '0'.repeat(32))).toBe(true);
    expect(estValidation('0147ae15' + '0'.repeat(32))).toBe(false);
    expect(estValidation('00000000' + 'f'.repeat(32))).toBe(true);
    expect(estValidation('ffffffff' + '0'.repeat(32))).toBe(false);
    expect(estValidation('80000000' + '0'.repeat(32), 0.5)).toBe(false);
    expect(estValidation('7fffffff' + '0'.repeat(32), 0.5)).toBe(true);
  });
});

describe('garderPythonPermissif', () => {
  it('suit le filtre de forge pour chaque ligne de référence', () => {
    expect(attendus.licences.length).toBeGreaterThan(10);
    for (const { ligne, garde } of attendus.licences) {
      expect(garderPythonPermissif(ligne), JSON.stringify(ligne)).toBe(garde);
    }
  });
});

describe('trier', () => {
  it('rend les verdicts du Python sur les exemples, un par ligne', async () => {
    for (const { source, lignes, verdicts } of attendus.tris) {
      const decodees = lignes.map((l) => Object.fromEntries(Object.entries(l).map(([k, v]) => [k, decoderTexte(v)])));
      expect(await trier(decodees, source), source).toStrictEqual(verdicts);
    }
  });

  it('suit l’ordre de la fiche : court, doublon, licence, langage', async () => {
    const web = attendus.tris.find((t) => t.source === 'web_fr')!.verdicts;
    expect(web[0].raison).toBe('trop court');
    expect(web[1].raison).toBe('gardé');
    expect(web[2].raison).toBe('doublon');
    expect(web[2].empreinte).toBe(web[1].empreinte);
    expect(web[3].raison).toBe('doublon');
    const code = attendus.tris.find((t) => t.source === 'code_python')!.verdicts;
    expect(code.map((v) => v.raison)).toStrictEqual(['gardé', 'licence', 'langage']);
  });

  it('compte les raisons dans l’ordre, zéros compris', async () => {
    const web = attendus.tris.find((t) => t.source === 'web_fr')!.verdicts;
    const comptes = compterRaisons(web);
    expect(Object.keys(comptes)).toStrictEqual([...RAISONS]);
    expect(Object.values(comptes).reduce((a, b) => a + b, 0)).toBe(web.length);
    expect(comptes.licence).toBe(0);
  });
});

describe('le texte dans le fichier d’attendus', () => {
  it('se code et se décode : chaîne, points de code, ou caractère répété', () => {
    expect(coderTexte('a\uD800b')).toStrictEqual([0x61, 0xd800, 0x62]);
    expect(decoderTexte([0x61, 0xd800, 0x62])).toBe('a\uD800b');
    expect(coderTexte('x'.repeat(100_000))).toStrictEqual({ repete: 'x', fois: 100_000 });
    expect(decoderTexte({ repete: 'x', fois: 3 })).toBe('xxx');
    expect(coderTexte('é')).toBe('é');
    expect(decoderTexte('abc')).toBe('abc');
    expect(decoderTexte(5)).toBe(5);
  });

  it('écrit les demi-paires en points de code, et les textes nettoyés en chaînes', () => {
    const avecMoitie = attendus.textes.filter((t) => Array.isArray(t.entree));
    expect(avecMoitie.length).toBeGreaterThanOrEqual(3);
    for (const t of attendus.textes) expect(Array.isArray(t.nettoye), t.nom).toBe(false);
  });
});

describe('parité', () => {
  it('refait tout le fichier à partir de ses seules entrées', async () => {
    expect(await refaireNettoyeur(attendus)).toStrictEqual(attendus);
  });

  it('le calcul « nettoyeur » de la page de parité est asynchrone et rend le même fichier', async () => {
    const calcul = CALCULS_PARTIE_1.nettoyeur();
    expect(calcul).toBeInstanceOf(Promise);
    expect(await calcul).toStrictEqual(attendus);
  });
});

describe('ce que l’atelier du chapitre 1.2 lit du nettoyeur', () => {
  it('estUnControleRetire dit vrai exactement pour les caractères que normaliser retire', () => {
    // Tout le premier plan d'Unicode, plus des points de code hors de lui (emoji, U+10FFFF).
    const points = [...Array.from({ length: 0x10000 }, (_, i) => i), 0x1f600, 0x1f44d, 0x10ffff];
    for (const point of points) {
      const c = String.fromCodePoint(point);
      expect(estUnControleRetire(c), point.toString(16)).toBe(normaliser(`a${c}b`) === 'ab');
    }
  });

  it('CHIFFRES_DE_LA_CLE est celui de trier.py', () => {
    const trier = readFileSync('../projets/1.2-donnees/donnees_pas_a_pas/trier.py', 'utf8');
    expect(Number(/^CHIFFRES_DE_LA_CLE = (\d+)$/m.exec(trier)?.[1])).toBe(CHIFFRES_DE_LA_CLE);
  });
});
