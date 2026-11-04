// Ce que montre l'animation de l'attention, étape par étape : titres, ligne
// d'état, barres, couleurs de la carte. Les attendus viennent du moteur
// (detaillerExemple, scoresAttention) : aucun poids n'est recopié.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { nombre, pourcent } from '../nombres';
import { scoresAttention } from './attention';
import { detaillerExemple, exempleAttention, type DetailTete } from './exemple-attention';
import {
  arrondi2,
  caseClaire,
  classement,
  etapesAttention,
  explication,
  fondCarte,
  legendeCarte,
  LEGENDE,
  LEGENDE_CARTE,
  LEGENDE_VECTEURS,
  ligneEtat,
  lignesEtape,
  messageSansJs,
  NB_ETAPES,
  partiesLigneEtat,
  nomTete,
  phraseMelange,
  phraseRequeteNulle,
  pourcentPoids,
  repete,
  valeur,
  vecteur,
} from './animation-attention';

const F = '\u202F';
/** Un mot entre guillemets, avec les espaces fines. */
const g = (mot: string) => `«${F}${mot}${F}»`;
const D = detaillerExemple(exempleAttention);
const QUI_AGIT = 0;
const DE_QUI = 1;
const LE = 0;
const FORGERON = 1;
const CHAUFFE = 2;
const FER = 4;
const PUIS = 5;
const IL = 6;
const TORD = 8;
const etat = (etape: number, tete: number, requete: number) => ligneEtat(etape, exempleAttention, D[tete], requete);

describe('les indices de ce fichier', () => {
  it('désignent les bons mots et les bonnes têtes', () => {
    expect(exempleAttention.jetons).toEqual(['Le', 'forgeron', 'chauffe', 'le', 'fer', 'puis', 'il', 'le', 'tord']);
    expect(exempleAttention.tetes.map((t) => t.nom)).toEqual(['qui agit', 'de qui on parle']);
  });
});

describe('les sept étapes', () => {
  it('leurs titres, dans l’ordre', () => {
    expect(NB_ETAPES).toBe(7);
    expect(etapesAttention(4).map((e) => e.titre)).toEqual([
      'Les mots et leurs traits',
      'Requête, clé, valeur',
      `Les scores${F}: requête · clé`,
      'Divisés par √4 = 2',
      `Le masque${F}: pas de regard vers la suite`,
      `Softmax${F}: des poids qui font 1`,
      'Le mélange des valeurs',
    ]);
  });

  it('la division suit la taille de la tête', () => {
    expect(etapesAttention(9)[3].titre).toBe('Divisés par √9 = 3');
    expect(etapesAttention(8)[3]).toEqual({ titre: 'Divisés par √8 = 2,83', court: 'divisés par 2,83' });
  });
});

describe('les nombres', () => {
  it('arrondi2 : 2 décimales, jamais −0, et un texte qui fait l’aller-retour', () => {
    expect(arrondi2(77.4795)).toBe(77.48);
    expect(Object.is(arrondi2(-0.001), 0)).toBe(true);
    expect(String(arrondi2(50))).toBe('50');
    for (const x of [0, 6.25, 16.666666, 33.333333, 77.48, 99.999, 100]) {
      const r = arrondi2(x);
      expect(arrondi2(Number(String(r)))).toBe(r);
      expect(String(r)).not.toMatch(/e|\.\d{3}/);
    }
  });

  it('valeur : sans décimale inutile, 2 au plus', () => {
    expect(valeur(8)).toBe('8');
    expect(valeur(2.5)).toBe('2,5');
    expect(valeur(-1)).toBe(nombre(-1));
    expect(valeur(-0)).toBe('0');
    expect(valeur(0.7748)).toBe('0,77');
  });

  it('vecteur : entre parenthèses, « ; » précédé d’une espace fine', () => {
    expect(vecteur([5, 2, 0, 1])).toBe(`(5${F}; 2${F}; 0${F}; 1)`);
    expect(vecteur([2.5149, 0.5, 0])).toBe(`(2,51${F}; 0,5${F}; 0)`);
  });

  it('pourcentPoids : le pourcentage arrondi de la barre, écrit en entier', () => {
    const p = D[DE_QUI].poids[IL][FORGERON];
    expect(pourcentPoids(p)).toBe(pourcent(arrondi2(p * 100) / 100));
    expect(pourcentPoids(p)).toMatch(new RegExp(`^\\d+${F}%$`));
    expect(pourcentPoids(1)).toBe(`100${F}%`);
    expect(pourcentPoids(0)).toBe(`0${F}%`);
  });
});

describe('lignesEtape : une ligne par mot, sa barre et son nombre', () => {
  const d = D[DE_QUI];
  const bruts = scoresAttention(d.requetes[IL], d.cles, 1.0);
  let plusGrand = 0;
  for (const s of bruts) if (Math.abs(s) > plusGrand) plusGrand = Math.abs(s);

  it('étapes 1 et 2 : pas encore de barre, toutes posées sur l’axe', () => {
    for (const etape of [1, 2]) {
      const l = lignesEtape(etape, d, IL);
      expect(l).toHaveLength(9);
      for (const ligne of l) expect(ligne).toMatchObject({ debut: 50, largeur: 0, masque: false, valeur: null });
    }
  });

  it('étape 3 : les scores de tous les mots, depuis un axe central ; le plus grand |score| remplit une demi-piste', () => {
    const l = lignesEtape(3, d, IL);
    expect(plusGrand).toBeGreaterThan(0);
    l.forEach((ligne, j) => {
      const largeur = arrondi2((Math.abs(bruts[j]) / plusGrand) * 50);
      expect(ligne.mot).toBe(j);
      expect(ligne.valeur).toBe(bruts[j]);
      expect(ligne.texte).toBe(valeur(bruts[j]));
      expect(ligne.largeur).toBe(largeur);
      expect(ligne.debut).toBe(bruts[j] < 0 ? arrondi2(50 - largeur) : 50);
      expect(ligne.negatif).toBe(bruts[j] < 0);
      expect(ligne.masque).toBe(false);
    });
    // « forgeron » a le plus grand score, et un mot a un score négatif (à gauche de l'axe).
    expect(l[FORGERON].largeur).toBe(50);
    expect(l.some((ligne) => ligne.negatif && ligne.largeur > 0)).toBe(true);
    // Les scores des mots visibles sont ceux du moteur, au bit près.
    for (let j = 0; j <= IL; j++) expect(l[j].valeur).toBe(d.scores[IL][j]);
  });

  it('étape 4 : divisés par 2, à la même échelle : chaque barre deux fois plus courte', () => {
    const l3 = lignesEtape(3, d, IL);
    const l4 = lignesEtape(4, d, IL);
    l4.forEach((ligne, j) => {
      expect(ligne.valeur).toBe(bruts[j] / 2);
      expect(ligne.largeur).toBeCloseTo(l3[j].largeur / 2, 1);
    });
    for (let j = 0; j <= IL; j++) expect(l4[j].valeur).toBe(d.scoresEchelles[IL][j]);
    expect(l4[FORGERON].largeur).toBe(25);
  });

  it('étape 5 : les mots après le mot choisi sont masqués, sans barre', () => {
    const l = lignesEtape(5, d, IL);
    for (let j = 0; j < 9; j++) {
      if (j > IL) expect(l[j]).toMatchObject({ masque: true, texte: 'masqué', largeur: 0, debut: 50, valeur: null });
      else expect(l[j]).toMatchObject({ masque: false, valeur: d.scoresEchelles[IL][j] });
    }
    const forgeron = lignesEtape(5, d, FORGERON);
    expect(forgeron.filter((ligne) => ligne.masque).map((ligne) => ligne.mot)).toEqual([2, 3, 4, 5, 6, 7, 8]);
  });

  it('étapes 6 et 7 : les poids, depuis la gauche ; une piste entière vaut 100 %', () => {
    for (const etape of [6, 7]) {
      const l = lignesEtape(etape, d, IL);
      l.forEach((ligne, j) => {
        if (j > IL) {
          expect(ligne).toMatchObject({ masque: true, texte: 'masqué', largeur: 0, debut: 0, valeur: null });
          return;
        }
        expect(ligne.valeur).toBe(d.poids[IL][j]);
        expect(ligne.debut).toBe(0);
        expect(ligne.largeur).toBe(arrondi2(d.poids[IL][j] * 100));
        expect(ligne.texte).toBe(pourcent(ligne.largeur / 100));
      });
      expect(l[FORGERON].largeur).toBeGreaterThanOrEqual(60);
    }
  });

  it('une requête nulle : toutes les barres à zéro aux étapes 3 et 4, puis des parts égales', () => {
    expect(D[DE_QUI].requetes[PUIS].every((v) => v === 0)).toBe(true);
    for (const etape of [3, 4]) {
      for (const ligne of lignesEtape(etape, d, PUIS)) expect(ligne).toMatchObject({ largeur: 0, debut: 50, texte: '0' });
    }
    const l6 = lignesEtape(6, d, PUIS);
    const parts = l6.slice(0, PUIS + 1).map((ligne) => ligne.largeur);
    expect(new Set(parts).size).toBe(1);
    expect(parts[0]).toBe(arrondi2(100 / (PUIS + 1)));
  });

  it('refuse une étape ou un mot hors de l’exemple', () => {
    expect(() => lignesEtape(0, d, IL)).toThrow(RangeError);
    expect(() => lignesEtape(8, d, IL)).toThrow(/de 1 à 7/);
    expect(() => lignesEtape(3, d, 9)).toThrow(/de 0 à 8/);
  });
});

describe('ligneEtat : la ligne annoncée aux lecteurs d’écran', () => {
  it('l’exemple du brief, calculé : étape 6, « il » donne l’essentiel de son attention à « forgeron »', () => {
    const p = D[DE_QUI].poids[IL][FORGERON];
    expect(etat(6, DE_QUI, IL)).toBe(`Étape 6 sur 7${F}: softmax. ${g('il')} donne ${pourcentPoids(p)} de son attention à ${g('forgeron')}.`);
    // 0,7748 : le « 74 % » de l'ancien brief était le total des deux sujets de « tord ».
    expect(pourcentPoids(p)).toBe(pourcent(0.7748));
  });

  it('les sept étapes pour « il », dans la tête « de qui on parle »', () => {
    const d = D[DE_QUI];
    const traits = exempleAttention.traits.filter((_, k) => exempleAttention.x[IL][k] === 1);
    expect(traits).toEqual(['pronom', 'sujet', 'personne']);
    expect(etat(1, DE_QUI, IL)).toBe(`Étape 1 sur 7${F}: les traits. ${g('il')} a 3 traits sur 8${F}: pronom, sujet et personne.`);
    expect(etat(2, DE_QUI, IL)).toBe(`Étape 2 sur 7${F}: requête, clé, valeur. La requête de ${g('il')} vaut ${vecteur(d.requetes[IL])}.`);
    const brut = d.scores[IL][FORGERON]!;
    const divise = d.scoresEchelles[IL][FORGERON]!;
    expect(etat(3, DE_QUI, IL)).toBe(
      `Étape 3 sur 7${F}: les scores. Le plus grand score de ${g('il')} est ${valeur(brut)}, avec ${g('forgeron')}.`,
    );
    expect(etat(4, DE_QUI, IL)).toBe(
      `Étape 4 sur 7${F}: divisés par 2. Le score de ${g('il')} avec ${g('forgeron')} passe de ${valeur(brut)} à ${valeur(divise)}.`,
    );
    expect(etat(5, DE_QUI, IL)).toBe(
      `Étape 5 sur 7${F}: le masque. ${g('il')} voit les 7 premiers mots, lui compris${F}: les 2 suivants sont masqués.`,
    );
    expect(etat(7, DE_QUI, IL)).toBe(
      `Étape 7 sur 7${F}: le mélange. La nouvelle valeur de ${g('il')} vient surtout de ${g('forgeron')} (${pourcentPoids(d.poids[IL][FORGERON])}).`,
    );
  });

  it('une égalité : « tord » regarde autant « forgeron » que « il », dans la tête « qui agit »', () => {
    const d = D[QUI_AGIT];
    expect(d.poids[TORD][FORGERON]).toBe(d.poids[TORD][IL]);
    const p = pourcentPoids(d.poids[TORD][FORGERON]);
    const brut = valeur(d.scores[TORD][FORGERON]!);
    expect(etat(3, QUI_AGIT, TORD)).toBe(
      `Étape 3 sur 7${F}: les scores. Le plus grand score de ${g('tord')} est ${brut}, avec ${g('forgeron')} et ${g('il')}.`,
    );
    expect(etat(4, QUI_AGIT, TORD)).toBe(
      `Étape 4 sur 7${F}: divisés par 2. Les scores de ${g('tord')} avec ${g('forgeron')} et ${g('il')} passent de ${brut} à ${valeur(d.scoresEchelles[TORD][FORGERON]!)}.`,
    );
    expect(etat(5, QUI_AGIT, TORD)).toBe(
      `Étape 5 sur 7${F}: le masque. ${g('tord')} est le dernier mot${F}: il voit toute la phrase, rien n’est masqué.`,
    );
    expect(etat(6, QUI_AGIT, TORD)).toBe(
      `Étape 6 sur 7${F}: softmax. ${g('tord')} donne ${p} de son attention à ${g('forgeron')}, et autant à ${g('il')}.`,
    );
    expect(etat(7, QUI_AGIT, TORD)).toBe(
      `Étape 7 sur 7${F}: le mélange. La nouvelle valeur de ${g('tord')} vient surtout de ${g('forgeron')} et de ${g('il')} (${p} chacun).`,
    );
  });

  it('une requête nulle : « puis » partage son attention à parts égales', () => {
    const d = D[DE_QUI];
    expect(etat(2, DE_QUI, PUIS)).toBe(
      `Étape 2 sur 7${F}: requête, clé, valeur. La requête de ${g('puis')} est nulle${F}: ${vecteur([0, 0, 0, 0])}.`,
    );
    expect(etat(3, DE_QUI, PUIS)).toBe(`Étape 3 sur 7${F}: les scores. La requête de ${g('puis')} est nulle${F}: tous ses scores valent 0.`);
    expect(etat(4, DE_QUI, PUIS)).toBe(`Étape 4 sur 7${F}: divisés par 2. Les scores de ${g('puis')} valent toujours 0.`);
    expect(etat(6, DE_QUI, PUIS)).toBe(
      `Étape 6 sur 7${F}: softmax. ${g('puis')} partage son attention à parts égales${F}: ${pourcentPoids(d.poids[PUIS][0])} pour chacun des 6 mots qu’il voit.`,
    );
    expect(etat(7, DE_QUI, PUIS)).toBe(
      `Étape 7 sur 7${F}: le mélange. La nouvelle valeur de ${g('puis')} est la moyenne des valeurs des 6 mots qu’il voit.`,
    );
  });

  it('le premier mot ne voit que lui-même ; un mot sans trait', () => {
    expect(etat(1, DE_QUI, LE)).toBe(`Étape 1 sur 7${F}: les traits. ${g('Le')} a 1 trait sur 8${F}: déterminant.`);
    expect(etat(5, DE_QUI, LE)).toBe(
      `Étape 5 sur 7${F}: le masque. ${g('Le')} est le premier mot${F}: il ne voit que lui-même, les 8 suivants sont masqués.`,
    );
    expect(etat(6, DE_QUI, LE)).toBe(`Étape 6 sur 7${F}: softmax. ${g('Le')} ne voit que lui-même${F}: il se donne 100${F}% de son attention.`);
    expect(etat(7, DE_QUI, LE)).toBe(
      `Étape 7 sur 7${F}: le mélange. La nouvelle valeur de ${g('Le')} est sa propre valeur${F}: il ne voit que lui-même.`,
    );
    expect(etat(1, DE_QUI, PUIS)).toBe(`Étape 1 sur 7${F}: les traits. ${g('puis')} n’a aucun de ces traits${F}: ses 8 nombres valent 0.`);
    expect(etat(5, DE_QUI, FORGERON)).toBe(
      `Étape 5 sur 7${F}: le masque. ${g('forgeron')} voit les 2 premiers mots, lui compris${F}: les 7 suivants sont masqués.`,
    );
  });

  it('ses deux parties : où l’on en est, puis la phrase de l’étape', () => {
    for (let etape = 1; etape <= NB_ETAPES; etape++) {
      const { ou, phrase } = partiesLigneEtat(etape, exempleAttention, D[DE_QUI], IL);
      expect(ou).toMatch(new RegExp(`^Étape ${etape} sur 7${F}: [^.]+[.]$`));
      expect(`${ou} ${phrase}`).toBe(etat(etape, DE_QUI, IL));
    }
  });

  it('« chauffe », dans la tête « qui agit » : son sujet, et un score égal avec un mot masqué ensuite', () => {
    const d = D[QUI_AGIT];
    expect(etat(3, QUI_AGIT, CHAUFFE)).toBe(
      `Étape 3 sur 7${F}: les scores. Le plus grand score de ${g('chauffe')} est ${valeur(d.scores[CHAUFFE][FORGERON]!)}, avec ${g('forgeron')} et ${g('il')}.`,
    );
    expect(etat(6, QUI_AGIT, CHAUFFE)).toBe(
      `Étape 6 sur 7${F}: softmax. ${g('chauffe')} donne ${pourcentPoids(d.poids[CHAUFFE][FORGERON])} de son attention à ${g('forgeron')}.`,
    );
  });
});

describe('phraseMelange : d’où vient la nouvelle valeur', () => {
  it('surtout d’un mot, de deux à égalité, de tous à parts égales, ou de lui seul', () => {
    expect(phraseMelange(exempleAttention, D[DE_QUI], IL)).toBe(
      `Sa nouvelle valeur vient surtout de ${g('forgeron')} (${pourcentPoids(D[DE_QUI].poids[IL][FORGERON])}).`,
    );
    expect(phraseMelange(exempleAttention, D[QUI_AGIT], TORD)).toMatch(
      new RegExp(`^Sa nouvelle valeur vient surtout de ${g('forgeron')} et de ${g('il')} \\(\\d+${F}% chacun\\)\\.$`),
    );
    expect(phraseMelange(exempleAttention, D[DE_QUI], PUIS)).toBe('Sa nouvelle valeur est la moyenne des valeurs des 6 mots qu’il voit.');
    expect(phraseMelange(exempleAttention, D[DE_QUI], LE)).toBe(`Sa nouvelle valeur est sa propre valeur${F}: il ne voit que lui-même.`);
  });

  it('« d’abord » quand le mot le plus regardé reçoit la moitié ou moins', () => {
    const d = structuredClone(D[DE_QUI]) as DetailTete;
    d.poids[2] = [0.25, 0.45, 0.3, 0, 0, 0, 0, 0, 0];
    expect(phraseMelange(exempleAttention, d, 2)).toBe(`Sa nouvelle valeur vient d’abord de ${g('forgeron')} (45${F}%).`);
  });
});

describe('l’explication de chaque étape', () => {
  it('nomme le mot choisi, et dit quand sa requête est nulle', () => {
    expect(explication(3, exempleAttention, D[DE_QUI], IL)).toContain(`la requête de ${g('il')}`);
    expect(explication(4, exempleAttention, D[DE_QUI], IL)).toContain('√4 = 2');
    for (let etape = 3; etape <= 7; etape++) {
      expect(explication(etape, exempleAttention, D[DE_QUI], IL)).not.toContain('ne vaut que des 0');
      expect(explication(etape, exempleAttention, D[DE_QUI], PUIS)).toContain(
        `La requête de ${g('puis')} ne vaut que des 0${F}: tous ses scores valent 0, et il partage son attention à parts égales entre les mots qu’il voit.`,
      );
    }
    expect(explication(1, exempleAttention, D[DE_QUI], IL)).toContain('1 s’il a ce trait, 0 sinon');
    expect(explication(6, exempleAttention, D[DE_QUI], LE)).toContain(`La requête de ${g('Le')} ne vaut que des 0${F}: tous ses scores valent 0.`);
  });
});

describe('la carte', () => {
  it('nom de la tête, légende du tableau, message sans JavaScript', () => {
    expect(nomTete(exempleAttention, 0)).toBe(`Tête 1${F}: qui agit`);
    expect(nomTete(exempleAttention, 1)).toBe(`Tête 2${F}: de qui on parle`);
    expect(legendeCarte(exempleAttention, 1)).toBe(`Tête 2${F}: de qui on parle. Les poids après le softmax, en pourcentage.`);
    expect(messageSansJs(exempleAttention, 1)).toBe(
      `Sans JavaScript, l’animation reste à sa première étape${F}; la carte complète de la tête 2, ${g('de qui on parle')}, est juste en dessous.`,
    );
  });

  it('une phrase sur les requêtes nulles, avec le premier mot concerné qui voit plusieurs mots', () => {
    expect(phraseRequeteNulle(exempleAttention, D[DE_QUI])).toBe(
      `Un mot dont la requête ne vaut que des 0, comme ${g('chauffe')} ici, a tous ses scores à 0${F}: il partage son attention à parts égales entre les mots qu’il voit.`,
    );
    expect(phraseRequeteNulle(exempleAttention, D[QUI_AGIT])).toContain(`comme ${g('forgeron')} ici`);
    const sansNulle = structuredClone(D[DE_QUI]) as DetailTete;
    sansNulle.requetes.forEach((q) => q.fill(1));
    expect(phraseRequeteNulle(exempleAttention, sansNulle)).toBeNull();
  });

  /** Une couleur #RRGGBB de jetons.css, en [r, g, b] de 0 à 255. */
  function couleur(css: string, nom: string): number[] {
    const m = new RegExp(`--${nom}:\\s*#([0-9A-Fa-f]{6})`).exec(css);
    if (m === null) throw new Error(`--${nom} introuvable dans jetons.css`);
    return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  }

  /** Le rapport de contraste WCAG de deux couleurs [r, g, b]. */
  function contraste(a: number[], b: number[]): number {
    const lum = (c: number[]) => {
      const [r, v, bl] = c.map((x) => {
        const s = x / 255;
        return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * v + 0.0722 * bl;
    };
    const [claire, foncee] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (claire + 0.05) / (foncee + 0.05);
  }

  it('fond indigo selon le poids, texte papier au-delà de 0,5, contraste AA pour tout poids', () => {
    const css = readFileSync(new URL('../../styles/jetons.css', import.meta.url), 'utf8');
    const indigo = couleur(css, 'indigo');
    const papier = couleur(css, 'papier');
    let avant = -1;
    for (let i = 0; i <= 1000; i++) {
      const p = i / 1000;
      const f = fondCarte(p);
      expect(f).toBeGreaterThanOrEqual(avant); // jamais plus clair pour un poids plus grand
      avant = f;
      // color-mix(in srgb, var(--indigo) f%, var(--papier)), arrondi à l'octet comme le navigateur.
      const fond = indigo.map((c, k) => Math.round((f / 100) * c + (1 - f / 100) * papier[k]));
      const texte = caseClaire(p) ? papier : indigo;
      expect(contraste(fond, texte), `poids ${p}`).toBeGreaterThanOrEqual(4.5);
    }
    expect([fondCarte(0), fondCarte(0.25), fondCarte(0.5), fondCarte(1)]).toEqual([0, 25, 50, 100]);
    expect(caseClaire(0.5)).toBe(false);
    expect(caseClaire(0.5001)).toBe(true);
  });
});

describe('les mots qui reviennent, et le classement', () => {
  it('repete : « Le » et les deux « le » (la casse ne compte pas)', () => {
    expect(exempleAttention.jetons.map((_, i) => repete(exempleAttention, i))).toEqual([
      true,
      false,
      false,
      true,
      false,
      false,
      false,
      true,
      false,
    ]);
  });

  it('classement : les mots visibles, du plus regardé au moins regardé, dans l’ordre de la phrase à égalité', () => {
    const rangs = classement(D[DE_QUI], IL);
    expect(rangs).toHaveLength(IL + 1);
    expect(rangs[0]).toBe(FORGERON);
    expect(rangs[1]).toBe(FER);
    for (let k = 1; k < rangs.length; k++) {
      expect(D[DE_QUI].poids[IL][rangs[k]]).toBeLessThanOrEqual(D[DE_QUI].poids[IL][rangs[k - 1]]);
    }
    expect(classement(D[QUI_AGIT], TORD).slice(0, 2)).toEqual([FORGERON, IL]);
  });

  it('la légende en deux parties : les vecteurs (toujours), puis la carte (quand elle est là)', () => {
    expect(LEGENDE).toBe(`${LEGENDE_VECTEURS} ${LEGENDE_CARTE}`);
    expect(LEGENDE_VECTEURS).not.toMatch(/carte/i);
    expect(LEGENDE_CARTE).toMatch(/^La carte montre où le calcul lit/);
  });

  it('la légende de la figure', () => {
    expect(LEGENDE).toBe(
      'Ces vecteurs sont écrits à la main, comme si les couches précédentes avaient déjà reconnu le rôle de chaque mot. ' +
        'Dans un vrai modèle, ils sont appris, et les têtes sont rarement aussi nettes. ' +
        'La carte montre où le calcul lit, pas pourquoi le modèle répond. ' +
        `Une ligne par mot qui demande, une colonne par mot regardé${F}; score = requête · clé.`,
    );
  });
});
