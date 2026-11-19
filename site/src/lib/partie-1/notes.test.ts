// Le jumeau des notes retrouve exactement les attendus du Python (FICHIERS_PARTIE_1.notes,
// projets/1.8-alignement/tests/attendus.json) : le nombre de mots, la langue, le verdict de chacune des huit
// consignes et de la longueur, et la note sans la justesse, sur quarante textes de référence, dont les pièges de
// l'atelier du chapitre 1.8 : accent combinant, apostrophe courbe, espace fine insécable, emoji, lettre hors du
// premier plan d'Unicode, blancs que Python et JavaScript ne comptent pas pareil, texte vide, chiffres seuls,
// dix mille caractères. La page de parité compare le fichier tout entier, dans Chrome, Firefox et WebKit.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FICHIERS_PARTIE_1, partieRefaite } from './fichiers';
import { BLANCS_PYTHON } from './nettoyeur';
import {
  BLANCS_DE_PYTHON,
  compterPhrases,
  langue,
  MOTS_ANGLAIS,
  MOTS_FRANCAIS,
  mots,
  noteSansJustesse,
  VERIFICATEURS_CONTRAINTES,
  type ConsigneDInvite,
  type ReglagesConsigne,
} from './notes';
import { CALCULS_PARTIE_1, refaireNotes, type EntreesNotes } from './parite';

interface TexteAttendu {
  nom: string;
  texte: string;
  terminee: boolean;
  invite: [string, ReglagesConsigne][];
  mots: number;
  langue: string;
  verdicts: Record<string, boolean>;
  longueur: boolean;
  note: { terminee: number; consignes: number; francais: number; longueur: number };
}

interface Attendus extends EntreesNotes {
  textes: (EntreesNotes['textes'][number] & TexteAttendu)[];
  grille_dpo: { beta: number; ecart_choisie: number; ecart_rejetee: number; perte: number; derivee: number }[];
}

const RACINE = '..';
const ATTENDUS = JSON.parse(readFileSync(`${RACINE}/${FICHIERS_PARTIE_1.notes}`, 'utf8')) as Attendus;
const TOUTES_LES_CONSIGNES: ConsigneDInvite[] = ATTENDUS.consignes.map(({ id, kwargs }) => [id, kwargs]);

const texte = (nom: string): TexteAttendu => {
  const cas = ATTENDUS.textes.find((t) => t.nom === nom);
  if (cas === undefined) throw new Error(`Pas de texte de référence « ${nom} ».`);
  return cas;
};

describe('les mots outils sont ceux de langue.py', () => {
  /** Les mots d'une liste de langue.py : le texte entre les triples guillemets de `NOM = frozenset(…)`. */
  function listeDePython(nom: string): string[] {
    const source = readFileSync(`${RACINE}/projets/forge/forge/evaluation/langue.py`, 'utf8');
    const trouve = new RegExp(`${nom} = frozenset\\(\\s*"""([\\s\\S]*?)"""`).exec(source);
    if (trouve === null) throw new Error(`La liste ${nom} n'est plus dans langue.py : revois ce test.`);
    return trouve[1].split(/\s+/).filter((mot) => mot !== '');
  }

  it('la liste française est la même, mot pour mot', () => {
    const python = listeDePython('MOTS_FRANCAIS');
    expect(python.length).toBeGreaterThan(60);
    expect([...MOTS_FRANCAIS].sort()).toStrictEqual([...new Set(python)].sort());
  });

  it('la liste anglaise est la même, mot pour mot', () => {
    const python = listeDePython('MOTS_ANGLAIS');
    expect(python.length).toBeGreaterThan(50);
    expect([...MOTS_ANGLAIS].sort()).toStrictEqual([...new Set(python)].sort());
  });

  it('les deux listes n’ont aucun mot commun', () => {
    expect([...MOTS_FRANCAIS].filter((mot) => MOTS_ANGLAIS.has(mot))).toStrictEqual([]);
  });

  it('les blancs de Python sont ceux du jumeau du nettoyage (1.2)', () => {
    expect([...BLANCS_DE_PYTHON]).toStrictEqual([...BLANCS_PYTHON]);
  });
});

describe('les huit consignes', () => {
  it('sont celles de forge, dans le même ordre, avec leur identifiant', () => {
    expect(Object.keys(VERIFICATEURS_CONTRAINTES)).toStrictEqual(ATTENDUS.consignes.map((c) => c.id));
    expect(ATTENDUS.consignes).toHaveLength(8);
  });

  it('donnent, sur chaque texte de référence, le verdict de Python', () => {
    expect(ATTENDUS.textes).toHaveLength(40);
    for (const cas of ATTENDUS.textes) {
      for (const { id, kwargs } of ATTENDUS.consignes) {
        expect(VERIFICATEURS_CONTRAINTES[id](cas.texte, kwargs), `${cas.nom} / ${id}`).toBe(cas.verdicts[id]);
      }
    }
  });
});

describe('les mots, la langue, la longueur et la note', () => {
  it('retrouvent, sur chaque texte de référence, les attendus de Python', () => {
    for (const cas of ATTENDUS.textes) {
      expect(mots(cas.texte).length, `${cas.nom} : mots`).toBe(cas.mots);
      expect(langue(cas.texte), `${cas.nom} : langue`).toBe(cas.langue);
      const n = mots(cas.texte).length;
      expect(n >= 3 && n <= 300, `${cas.nom} : longueur`).toBe(cas.longueur);
      expect(noteSansJustesse(cas.texte, cas.terminee, cas.invite), `${cas.nom} : note`).toStrictEqual(cas.note);
    }
  });

  it('la page de parité refait le fichier tout entier, sauf la perte DPO de la grille', () => {
    const refait = refaireNotes(ATTENDUS);
    expect(refait).toStrictEqual(partieRefaite('notes', ATTENDUS as unknown as Record<string, unknown>));
    expect(Object.keys(refait)).toStrictEqual(['consignes', 'textes', 'grille_dpo']);
    expect(Object.keys((refait.grille_dpo as object[])[0])).toStrictEqual(['beta', 'ecart_choisie', 'ecart_rejetee']);
  });

  it('est un calcul de la page de parité', () => {
    expect(Object.keys(CALCULS_PARTIE_1)).toContain('notes');
    expect(CALCULS_PARTIE_1.notes()).toStrictEqual(partieRefaite('notes', ATTENDUS as unknown as Record<string, unknown>));
  });

  it('compte une réponse coupée, une consigne manquée, une autre langue et un texte trop court', () => {
    const invite: ConsigneDInvite[] = [['minuscules', {}], ['mots_max', { n: 5 }]];
    expect(noteSansJustesse('paris est la capitale.', true, invite)).toStrictEqual({ terminee: 1, consignes: 2, francais: 1, longueur: 1 });
    expect(noteSansJustesse('paris est la capitale.', false, invite).terminee).toBe(0);
    expect(noteSansJustesse('Paris est la capitale de la France, belle.', true, invite).consignes).toBe(0);
    expect(noteSansJustesse('The capital of France is Paris and it is beautiful.', true, []).francais).toBe(0);
    expect(noteSansJustesse('Oui.', true, [])).toStrictEqual({ terminee: 1, consignes: 0, francais: 1, longueur: 0 });
  });

  it('refuse une consigne inconnue, comme forge', () => {
    expect(() => noteSansJustesse('Bonjour.', true, [['inconnue', {}]])).toThrow(/« inconnue » est inconnue.*mots_max, phrases_max/);
    expect(() => noteSansJustesse('Bonjour.', true, [['toString', {}]])).toThrow(/inconnue/);
  });
});

describe('les pièges de l’atelier', () => {
  // Ce que Python compte comme un blanc de fin, et pas JavaScript (et inversement).
  it('retire les blancs de Python : U+0085 et U+001C, pas U+FEFF ni U+180E', () => {
    expect(texte('fin-imposee-next-line').verdicts.fin_imposee).toBe(true);
    expect(texte('fin-imposee-separateur-de-fichier').verdicts.fin_imposee).toBe(true);
    expect(texte('fin-imposee-bom').verdicts.fin_imposee).toBe(false);
    expect(texte('fin-imposee-mongol').verdicts.fin_imposee).toBe(false);
    // trimEnd() ferait l'inverse : c'est ce que le jumeau évite.
    expect('x\u{85}'.trimEnd()).toBe('x\u{85}');
    expect('x\u{feff}'.trimEnd()).toBe('x');
  });

  it('lit en points de code : une lettre hors du premier plan colle au mot', () => {
    expect(VERIFICATEURS_CONTRAINTES.mot_obligatoire('\u{1D49C}paris', { mot: 'paris' })).toBe(false);
    expect(VERIFICATEURS_CONTRAINTES.mot_obligatoire('\u{1F600}paris\u{1F600}', { mot: 'paris' })).toBe(true);
    expect(mots('\u{1D49C}b c')).toStrictEqual(['\u{1D49C}b', 'c']);
  });

  it('coupe les phrases aux blancs de Python', () => {
    expect(compterPhrases('Paris est belle.\u{85}Lyon aussi.\u{1c}Nice enfin.')).toBe(3);
  });

  it('le texte vide, les blancs et les chiffres seuls n’ont ni mot ni langue, et aucune consigne de contenu', () => {
    for (const nom of ['vide', 'blancs', 'chiffres-seuls']) {
      const cas = texte(nom);
      expect(mots(cas.texte)).toStrictEqual([]);
      expect(langue(cas.texte)).toBe('indetermine');
      const note = noteSansJustesse(cas.texte, true, TOUTES_LES_CONSIGNES);
      expect(Object.values(note).every((x) => Number.isInteger(x)), nom).toBe(true);
      expect(note.longueur).toBe(0);
    }
    expect(VERIFICATEURS_CONTRAINTES.mots_max('', { n: 20 })).toBe(false);
    expect(VERIFICATEURS_CONTRAINTES.sans_virgule('', {})).toBe(false);
    expect(VERIFICATEURS_CONTRAINTES.minuscules('2026', {})).toBe(false); // aucune lettre à casse
  });

  it('apostrophe courbe, accent combinant, espaces fines : ces caractères coupent les mots comme en Python', () => {
    expect(mots('l’eau d’Évian')).toStrictEqual(['l', 'eau', 'd', 'évian']);
    expect(mots('Cafe\u0301 ok')).toStrictEqual(['cafe', 'ok']); // l'accent combinant (catégorie Mn) n'est pas une lettre
    expect(mots('un\u202fdeux\u00a0trois')).toStrictEqual(['un', 'deux', 'trois']);
  });

  it('10 000 caractères se notent en moins de 200 ms, avec les huit consignes', () => {
    const textes = [
      ('Le chat dort dans la maison, et il rêve de Paris. ').repeat(200).slice(0, 10_000),
      'x'.repeat(10_000),
      '1234567890'.repeat(1_000),
      '\u{1F600}'.repeat(5_000),
      ' '.repeat(10_000),
      'a. '.repeat(3_333),
    ];
    for (const grand of textes) {
      const debut = performance.now();
      const note = noteSansJustesse(grand, true, TOUTES_LES_CONSIGNES);
      const duree = performance.now() - debut;
      expect(duree, `${grand.slice(0, 12)}… : ${duree.toFixed(1)} ms`).toBeLessThan(200);
      expect(Object.values(note).every((x) => Number.isFinite(x))).toBe(true);
    }
  });
});
