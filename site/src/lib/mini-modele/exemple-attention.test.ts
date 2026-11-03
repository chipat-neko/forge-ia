// L'exemple d'attention : « Le forgeron chauffe le fer puis il le tord ».
//
// Jumeau de projets/mini-modele/tests/test_exemple_attention.py. Les attendus
// sont écrits par le Python (tests/attendus-attention.json) : les requêtes,
// les clés, les valeurs, les scores, les poids et les sorties de chaque tête
// doivent être les mêmes, au bit près, cases masquées comprises (null pour
// les scores, +0,0 pour les poids). Les critères de l'exemple portent sur les
// poids calculés, jamais sur des nombres recopiés.

import { describe, expect, it } from 'vitest';
import attendus from '../../../../projets/mini-modele/tests/attendus-attention.json';
import { melangerValeurs, poidsAttention, scoresAttention, softmax } from './attention';
import { racine, somme, versHex } from './calcul';
import {
  chargerExemple,
  detaillerExemple,
  detaillerTete,
  exempleAttention,
  verifierExemple,
  type DetailTete,
  type ExempleAttention,
} from './exemple-attention';

const PHRASE = 'Le forgeron chauffe le fer puis il le tord';
const TRAITS = ['déterminant', 'nom', 'verbe', 'pronom', 'sujet', 'objet', 'personne', 'chose'];
// Les traits de chaque mot, dans l'ordre de la phrase (la définition de l'exemple).
const TRAITS_DES_MOTS = [
  ['déterminant'],
  ['nom', 'sujet', 'personne'],
  ['verbe'],
  ['déterminant'],
  ['nom', 'objet', 'chose'],
  [],
  ['pronom', 'sujet', 'personne'],
  ['pronom', 'objet', 'chose'],
  ['verbe'],
];
const MOTIF_ZERO = '0000000000000000'; // +0,0 : un poids masqué vaut exactement 0, sans signe moins

/** Chaque case en motif ; une case masquée (null) reste null, comme dans les attendus. */
function motifs(matrice: readonly (readonly (number | null)[])[]): (string | null)[][] {
  return matrice.map((ligne) => ligne.map((v) => (v === null ? null : versHex(v))));
}

/** Le détail comme le Python l'écrit : noms Python, motifs, null pour les cases masquées. */
function detailEnAttendus(nom: string, d: DetailTete): Record<string, unknown> {
  return {
    nom,
    requetes: motifs(d.requetes),
    cles: motifs(d.cles),
    valeurs: motifs(d.valeurs),
    scores: motifs(d.scores),
    scores_echelles: motifs(d.scoresEchelles),
    poids: motifs(d.poids),
    sorties: motifs(d.sorties),
  };
}

/** Le mot visible de plus grand poids (le premier, à égalité). */
function plusRegarde(poids: readonly number[], requete: number): number {
  let meilleur = 0;
  for (let j = 1; j <= requete; j++) if (poids[j] > poids[meilleur]) meilleur = j;
  return meilleur;
}

/** Un exemple qu'on peut abîmer, pour vérifier les messages d'erreur. */
interface ExempleModifiable {
  phrase: string;
  jetons: string[];
  traits: string[];
  x: number[][];
  tetes?: { nom: unknown; description: string; wq: number[][]; wk: number[][]; wv: number[][] }[];
}

/** Une copie modifiable de l'exemple (l'original est figé). */
function copie(): ExempleModifiable {
  return structuredClone(exempleAttention) as unknown as ExempleModifiable;
}

describe('jumeau du Python : attendus-attention.json, au bit près', () => {
  const details = detaillerExemple(exempleAttention);

  it('la phrase, les jetons et les noms des têtes', () => {
    expect(attendus.phrase).toBe(exempleAttention.phrase);
    expect(attendus.jetons).toEqual(exempleAttention.jetons);
    expect(attendus.tetes.map((t) => t.nom)).toEqual(exempleAttention.tetes.map((t) => t.nom));
  });

  it('tout le détail de chaque tête, cases masquées comprises', () => {
    expect(details.length).toBe(attendus.tetes.length);
    details.forEach((d, t) => {
      expect(detailEnAttendus(exempleAttention.tetes[t].nom, d), exempleAttention.tetes[t].nom).toEqual(
        attendus.tetes[t],
      );
    });
  });

  it('toutes les clés des attendus sont comparées', () => {
    expect(Object.keys(attendus).sort()).toEqual(['jetons', 'phrase', 'tetes']);
    for (const t of attendus.tetes) {
      expect(Object.keys(t).sort()).toEqual(
        ['nom', 'requetes', 'cles', 'valeurs', 'scores', 'scores_echelles', 'poids', 'sorties'].sort(),
      );
    }
  });
});

describe('l’exemple écrit à la main', () => {
  it('les critères de l’exemple, sur les poids calculés', () => {
    const ex = chargerExemple();
    const [agit, reprise] = detaillerExemple(ex);
    expect(agit.poids[2][1]).toBeGreaterThanOrEqual(0.7); // « chauffe » regarde « forgeron »
    expect(agit.poids[8][1] + agit.poids[8][6]).toBeGreaterThanOrEqual(0.7); // « tord » regarde ses sujets
    expect(reprise.poids[6][1]).toBeGreaterThanOrEqual(0.6); // « il » regarde « forgeron »
    expect(reprise.poids[7][4]).toBeGreaterThanOrEqual(0.6); // le second « le » regarde « fer »
    for (const d of [agit, reprise]) {
      for (let i = 0; i < 9; i++) {
        for (let j = i + 1; j < 9; j++) expect(d.poids[i][j]).toBe(0);
        expect(Math.abs(somme(d.poids[i].slice(0, i + 1)) - 1.0)).toBeLessThanOrEqual(1e-15);
      }
    }
    expect(ex.x.flat().every((v) => v === 0 || v === 1)).toBe(true);
    for (const t of ex.tetes) {
      for (const m of [t.wq, t.wk, t.wv]) {
        expect(m.flat().every((v) => Number.isInteger(v) && v >= -5 && v <= 5), t.nom).toBe(true);
      }
    }
  });

  it('la phrase, les traits de chaque mot et les deux têtes', () => {
    const ex = chargerExemple();
    expect(ex).toBe(exempleAttention);
    expect(Object.keys(ex).sort()).toEqual(['jetons', 'phrase', 'tetes', 'traits', 'x']);
    expect(ex.phrase).toBe(PHRASE);
    expect(ex.jetons).toEqual(PHRASE.split(' '));
    expect(ex.traits).toEqual(TRAITS);
    expect(ex.x.map((ligne) => TRAITS.filter((_, t) => ligne[t] === 1))).toEqual(TRAITS_DES_MOTS);
    expect(ex.tetes.map((t) => t.nom)).toEqual(['qui agit', 'de qui on parle']);
    for (const t of ex.tetes) {
      expect(Object.keys(t).sort()).toEqual(['description', 'nom', 'wk', 'wq', 'wv']);
      // Une seule phrase, avec l'apostrophe courbe.
      expect(t.description.endsWith('.')).toBe(true);
      expect(t.description.split('.').length).toBe(2);
      expect(t.description).not.toContain("'");
      for (const m of [t.wq, t.wk, t.wv]) {
        expect(m.length).toBe(8);
        expect(m.every((ligne) => ligne.length === 4)).toBe(true);
      }
    }
  });

  it('est figé : un composant ne peut pas le modifier par mégarde', () => {
    expect(Object.isFrozen(exempleAttention)).toBe(true);
    expect(Object.isFrozen(exempleAttention.x)).toBe(true);
    expect(Object.isFrozen(exempleAttention.x[0])).toBe(true);
    expect(Object.isFrozen(exempleAttention.tetes[1].wq[3])).toBe(true);
  });

  it('les têtes font ce que dit leur nom, sur les poids calculés', () => {
    const [agit, reprise] = detaillerExemple(exempleAttention);
    expect(plusRegarde(agit.poids[2], 2)).toBe(1); // « chauffe » → « forgeron »
    // « tord » : ses deux sujets, « forgeron » et « il », sont les deux mots les plus regardés.
    const rangs = Array.from({ length: 9 }, (_, j) => j).sort((a, b) => agit.poids[8][b] - agit.poids[8][a]);
    expect(rangs.slice(0, 2).sort()).toEqual([1, 6]);
    expect(plusRegarde(reprise.poids[6], 6)).toBe(1); // « il » → « forgeron »
    expect(plusRegarde(reprise.poids[7], 7)).toBe(4); // le second « le » → « fer »
    // « il » regarde « forgeron » plus que « fer », le nom le plus proche : la tête lit les traits, pas la distance.
    expect(reprise.poids[6][1]).toBeGreaterThan(reprise.poids[6][4]);
    expect(reprise.poids[6][4]).toBeGreaterThan(reprise.poids[6][5]);
  });

  it('le masque cache la suite', () => {
    for (const d of detaillerExemple(exempleAttention)) {
      for (let i = 0; i < 9; i++) {
        for (let j = 0; j < 9; j++) {
          const masque = j > i;
          expect(d.scores[i][j] === null, `${i}, ${j}`).toBe(masque);
          expect(d.scoresEchelles[i][j] === null, `${i}, ${j}`).toBe(masque);
          if (masque) expect(versHex(d.poids[i][j]), `${i}, ${j}`).toBe(MOTIF_ZERO);
          else expect(d.poids[i][j], `${i}, ${j}`).toBeGreaterThan(0);
        }
      }
      expect(d.poids[0][0]).toBe(1);
    }
  });
});

describe('detaillerTete', () => {
  it('calcule avec les fonctions du mini-modèle', () => {
    const ex = exempleAttention;
    detaillerExemple(ex).forEach((d, t) => {
      const tete = ex.tetes[t];
      const echelle = 1.0 / racine(4);
      expect(echelle).toBe(0.5);
      for (const [w, calcule] of [
        [tete.wq, d.requetes],
        [tete.wk, d.cles],
        [tete.wv, d.valeurs],
      ] as const) {
        const attendu = ex.x.map((x) =>
          Array.from({ length: 4 }, (_, j) => x.reduce((s, xi, i) => s + xi * w[i][j], 0)),
        );
        expect(calcule).toEqual(attendu);
      }
      for (let i = 0; i < 9; i++) {
        const q = d.requetes[i];
        const visibles = d.cles.slice(0, i + 1);
        const hex = (v: readonly (number | null)[]): string[] => v.map((x) => versHex(x as number));
        expect(hex(d.scores[i].slice(0, i + 1))).toEqual(hex(scoresAttention(q, visibles, 1.0)));
        expect(hex(d.scoresEchelles[i].slice(0, i + 1))).toEqual(hex(scoresAttention(q, visibles, echelle)));
        expect(hex(d.poids[i].slice(0, i + 1))).toEqual(hex(softmax(scoresAttention(q, visibles, echelle))));
        expect(hex(d.poids[i].slice(0, i + 1))).toEqual(hex(poidsAttention(q, visibles, echelle)));
        expect(hex(d.sorties[i])).toEqual(hex(melangerValeurs(d.poids[i].slice(0, i + 1), d.valeurs.slice(0, i + 1))));
      }
    });
  });

  it('sur un petit cas, où tout tombe juste', () => {
    const d = detaillerTete(
      [
        [1, 0],
        [0, 1],
      ],
      [
        [2, 0, 0, 0],
        [0, 2, 0, 0],
      ],
      [
        [1, 0, 0, 0],
        [1, 0, 0, 0],
      ],
      [
        [1, 2],
        [3, 4],
      ],
    );
    expect(d.requetes).toEqual([
      [2, 0, 0, 0],
      [0, 2, 0, 0],
    ]);
    expect(d.cles).toEqual([
      [1, 0, 0, 0],
      [1, 0, 0, 0],
    ]);
    expect(d.valeurs).toEqual([
      [1, 2],
      [3, 4],
    ]);
    expect(d.scores).toEqual([
      [2, null],
      [0, 0],
    ]);
    expect(d.scoresEchelles).toEqual([
      [1, null],
      [0, 0],
    ]);
    expect(d.poids).toEqual([
      [1, 0],
      [0.5, 0.5],
    ]);
    expect(d.sorties).toEqual([
      [1, 2],
      [2, 3],
    ]);
    // L'échelle suit la taille de la tête : 1 / √(colonnes de wq).
    const d1 = detaillerTete([[1]], [[3]], [[2]], [[5]]);
    expect([d1.scores, d1.scoresEchelles, d1.sorties]).toEqual([[[6]], [[6]], [[5]]]);
  });

  it('refuse des dimensions incohérentes, avec les messages du Python', () => {
    const x = [
      [1, 0],
      [0, 1],
    ];
    const bon = [
      [1, 0],
      [0, 1],
    ];
    expect(() => detaillerTete(x, [[1, 0], [0, 1], [1, 1]], bon, bon)).toThrow(
      'wq doit avoir 2 lignes, une par trait (reçu 3).',
    );
    expect(() => detaillerTete(x, bon, [[1, 0], [1]], bon)).toThrow(
      "wk : la ligne 1 n'a pas la longueur de la ligne 0 (1 au lieu de 2).",
    );
    expect(() => detaillerTete(x, bon, [[1, 0, 0], [0, 1, 0]], bon)).toThrow(
      /wq et wk doivent avoir autant de colonnes/,
    );
    expect(() => detaillerTete([], bon, bon, bon)).toThrow('x doit être une liste de lignes non vide.');
    expect(() => detaillerTete([[true as unknown as number, 0], [0, 1]], bon, bon, bon)).toThrow(
      /x, ligne 0 : « true » n'est pas un nombre fini/,
    );
    expect(() => detaillerTete(x, bon, bon, [[1, 0], [0, NaN]])).toThrow(/wv, ligne 1 : « NaN » n'est pas un nombre fini/);
  });
});

describe('verifierExemple', () => {
  it('refuse un exemple mal formé, avec les messages du Python', () => {
    verifierExemple(exempleAttention);
    const sansTetes = copie();
    delete sansTetes.tetes;
    expect(() => verifierExemple(sansTetes)).toThrow(/il manque « tetes »/);
    expect(() => detaillerExemple(sansTetes as unknown as ExempleAttention)).toThrow(/il manque « tetes »/);
    const motEnTrop = copie();
    motEnTrop.jetons.push('encore');
    expect(() => verifierExemple(motEnTrop)).toThrow(/une ligne de x par jeton \(10 jetons, 9 lignes\)/);
    const traitEnTrop = copie();
    traitEnTrop.traits.push('couleur');
    expect(() => verifierExemple(traitEnTrop)).toThrow(/une case par trait \(9 traits, 8 cases\)/);
    const teteCourte = copie();
    teteCourte.tetes?.[1].wv.pop();
    expect(() => verifierExemple(teteCourte)).toThrow(
      /tête « de qui on parle », wv doit avoir 8 lignes, une par trait \(reçu 7\)/,
    );
    const sansNom = copie();
    if (sansNom.tetes) sansNom.tetes[0].nom = 3;
    expect(() => verifierExemple(sansNom)).toThrow(/le nom et la description de chaque tête sont des textes/);
  });

  it('un autre exemple se détaille aussi (le composant en accepte un autre)', () => {
    const autre = copie() as unknown as ExempleAttention;
    expect(detaillerExemple(autre).map((d) => motifs(d.poids))).toEqual(
      detaillerExemple(exempleAttention).map((d) => motifs(d.poids)),
    );
  });
});
