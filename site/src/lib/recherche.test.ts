import { describe, expect, it } from 'vitest';
import { PARCOURS } from './parcours';
import {
  aplatir,
  chercher,
  chercherDansLesTitres,
  extraitPertinent,
  garderPertinents,
  morceauxExtrait,
  numeroDeChapitre,
  racines,
  versPassage,
  versResultat,
} from './recherche';

const TOUS = PARCOURS.flatMap((p) => p.chapitres);
const numeros = (requete: string) => chercherDansLesTitres(requete, TOUS).map((c) => c.numero);

describe('chercherDansLesTitres', () => {
  it('trouve les six titres qui parlent d’images, au singulier comme au pluriel', () => {
    expect(numeros('images')).toEqual(['1.11', '1.12', '1.13', '1.15', '2.3', '3.2']);
    expect(numeros('image')).toEqual(numeros('images'));
  });

  it('ignore les accents et les majuscules', () => {
    expect(numeros('evaluer')).toEqual(['1.6']);
    expect(numeros('bpe')).toEqual(['1.3']);
    expect(numeros('SÉCURITÉ')).toEqual(['1.21']);
  });

  it('demande tous les mots de la requête', () => {
    expect(numeros('modèle langage')).toEqual(['1.1']);
    expect(numeros('modèle xyz')).toEqual([]);
  });

  it('mène droit au chapitre qui porte un numéro', () => {
    expect(numeros('1.4')).toEqual(['1.4']);
    expect(numeros(' 1,13 ')).toEqual(['1.13']);
    expect(numeros('9.9')).toEqual([]);
  });

  it('ne trouve rien pour une requête vide ou faite d’une seule lettre', () => {
    expect(numeros('')).toEqual([]);
    expect(numeros('   ')).toEqual([]);
    expect(numeros('a')).toEqual([]);
    expect(numeros('🙂')).toEqual([]);
  });
});

describe('racines, aplatir et numeroDeChapitre', () => {
  it('retire le s ou le x final des mots de plus de quatre lettres', () => {
    expect(racines('Les fusions, des jeux')).toEqual(['les', 'fusion', 'des', 'jeux']);
  });

  it('aplatit les accents', () => {
    expect(aplatir('Éœé')).toBe('eœe');
  });

  it('reconnaît un numéro de chapitre', () => {
    expect(numeroDeChapitre('1.3')).toBe('1.3');
    expect(numeroDeChapitre('1,21')).toBe('1.21');
    expect(numeroDeChapitre('1.3.4')).toBeNull();
    expect(numeroDeChapitre('jetons')).toBeNull();
  });
});

describe('résultats de Pagefind', () => {
  const donnees = {
    url: '/forge-ia/partie-1/1-3/',
    excerpt: 'les <mark>fusions</mark> apprises',
    meta: { title: 'Le tokenizer', numero: '1.3' },
    sub_results: [
      { title: 'Le tokenizer', url: '/forge-ia/partie-1/1-3/', excerpt: 'début' },
      { title: 'À toi de découper', url: '/forge-ia/partie-1/1-3/#titre-etape-4', excerpt: 'quatre' },
      { title: 'Ce que tu sais maintenant', url: '/forge-ia/partie-1/1-3/#titre-recap', excerpt: 'recap' },
      { title: 'Lettres ou mots ?', url: '/forge-ia/partie-1/1-3/#titre-etape-2', excerpt: 'deux' },
    ],
  };

  it('vise la section de l’étape et garde son numéro', () => {
    expect(versPassage(donnees.sub_results[1])).toEqual({
      titre: 'À toi de découper',
      url: '/forge-ia/partie-1/1-3/#etape-4',
      extrait: 'quatre',
      etape: 4,
    });
  });

  it('garde les passages ancrés, dans l’ordre des étapes', () => {
    const resultat = versResultat(donnees);
    expect(resultat).toMatchObject({ titre: 'Le tokenizer', numero: '1.3', url: '/forge-ia/partie-1/1-3/' });
    expect(resultat.passages.map((p) => p.url.split('#')[1])).toEqual(['etape-2', 'etape-4', 'titre-recap']);
  });

  it('se passe de sous-résultats et de numéro', () => {
    expect(versResultat({ url: '/x/', excerpt: 'e', meta: {} })).toEqual({
      titre: '/x/',
      url: '/x/',
      extrait: 'e',
      numero: undefined,
      passages: [],
    });
  });
});

describe('morceauxExtrait', () => {
  it('sépare les mots marqués du reste', () => {
    expect(morceauxExtrait('on la <mark>fusionne</mark> en un <mark>nouveau</mark>')).toEqual([
      { texte: 'on la ', marque: false },
      { texte: 'fusionne', marque: true },
      { texte: ' en un ', marque: false },
      { texte: 'nouveau', marque: true },
    ]);
  });

  it('décode les entités sans jamais interpréter de HTML', () => {
    expect(morceauxExtrait('a &lt;b&gt; &amp; &#8217; &#x202F; <img src=x>')).toEqual([
      { texte: 'a <b> & ’   <img src=x>', marque: false },
    ]);
    expect(morceauxExtrait('&bidule; &#99999999;')).toEqual([{ texte: '&bidule; &#99999999;', marque: false }]);
  });
});

describe('extraitPertinent et garderPertinents', () => {
  it('garde un mot trouvé, au singulier, au pluriel ou conjugué', () => {
    expect(extraitPertinent('les <mark>fusions</mark> apprises', 'fusions')).toBe(true);
    expect(extraitPertinent('on la <mark>fusionne</mark>', 'fusions')).toBe(true);
    expect(extraitPertinent('chaque lettre est un <mark>jeton.</mark>', 'jetons')).toBe(true);
    expect(extraitPertinent('que donne <mark>list(zip(symboles,</mark>', 'zip')).toBe(true);
    expect(extraitPertinent('le <mark>BPE</mark>', 'bpe')).toBe(true);
  });

  it('écarte les morceaux de mots que Pagefind surligne faute de mieux', () => {
    expect(extraitPertinent('l. es. ␣f. o. r. <mark>g.</mark> er.', 'gabarit')).toBe(false);
    expect(extraitPertinent('on la fusionne <mark>en</mark> un nouveau', 'enclume')).toBe(false);
    expect(extraitPertinent('rien de surligné', 'jetons')).toBe(false);
    // « GPU » absent du chapitre : Pagefind surligne le « g » d'un exemple de code.
    expect(extraitPertinent("par exemple {('f', 'o', 'r', <mark>'g',</mark> 'e')", 'GPU')).toBe(false);
  });

  it('garde le mot que le racinisateur français trouve à juste titre', () => {
    // Pagefind ramène « mots » à « mot » et « jeux » à « jeu » : ces passages parlent bien du sujet.
    expect(extraitPertinent('découper <mark>mot</mark> par mot', 'mots')).toBe(true);
    expect(extraitPertinent('comme ceux d’un <mark>jeu</mark> de société', 'jeux')).toBe(true);
    expect(extraitPertinent('les <mark>mots</mark> rares', 'mot')).toBe(true);
    expect(extraitPertinent('les <mark>mots</mark> rares', 'Les mots rares')).toBe(true);
  });

  it('retire les passages hors sujet, puis les pages qui n’en ont plus', () => {
    const page = (passages: string[], extrait = 'x') => ({
      titre: 't',
      url: '/u/',
      extrait,
      passages: passages.map((e, i) => ({ titre: `p${i}`, url: `/u/#etape-${i + 1}`, extrait: e, etape: i + 1 })),
    });
    const resultats = [
      page(['un <mark>jeton</mark>', 'la lettre <mark>j</mark>']),
      page(['<mark>j.</mark>']),
      page([], 'en ouverture, des <mark>jetons</mark>'),
    ];
    const gardes = garderPertinents(resultats, 'jetons');
    expect(gardes.map((r) => r.passages.map((p) => p.titre))).toEqual([['p0'], []]);
    expect(gardes[1].extrait).toContain('jetons');
  });
});

describe('chercher', () => {
  it('ne charge rien pour une requête vide', async () => {
    await expect(chercher('  ')).resolves.toEqual([]);
  });
});
