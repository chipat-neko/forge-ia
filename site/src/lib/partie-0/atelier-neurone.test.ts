// L'atelier du neurone du chapitre 0.5 : ses comptes sont ceux du jumeau du
// Python (neurone.ts), et ses phrases, son dessin et son défi viennent
// d'atelier-neurone.ts. On les vérifie ici sur les 729 réglages de la grille,
// pour les trois portes, puis sur les phrases exactes des cas du chapitre.

import { describe, expect, it } from 'vitest';
import { bienClasses, GRILLE, POINTS, PORTES, sortieSeuil, type Porte } from './neurone';
import {
  B_DEPART,
  bilan,
  DEFI_NEURONE_REUSSI,
  defiReussi,
  DOMAINE_MAX,
  DOMAINE_MIN,
  droite,
  ecrireReglage,
  etatDesPoints,
  etatDuDefi,
  gagneNeurone,
  morceauxDuPoint,
  noterReussite,
  PORTE_DEPART,
  PORTES_ATELIER,
  REGLAGE_MAX,
  REGLAGE_MIN,
  REGLAGE_PAS,
  regionUn,
  remarque,
  SANS_POIDS,
  texteDuPoint,
  W1_DEPART,
  W2_DEPART,
  type Reussites,
} from './atelier-neurone';

const FINE = '\u202F';
const MOINS = '−';
const INSECABLE = '\u00A0';
const PORTES_TOUTES: Porte[] = ['et', 'ou', 'ou_exclusif'];

/** Les 729 réglages de la grille. */
function reglages(): [number, number, number][] {
  const tous: [number, number, number][] = [];
  for (const w1 of GRILLE) for (const w2 of GRILLE) for (const b of GRILLE) tous.push([w1, w2, b]);
  return tous;
}

/** Vrai si le point (x, y) est dans le polygone convexe (bords compris, à 1e-9 près). */
function dansLePolygone(poly: readonly (readonly [number, number])[], x: number, y: number): boolean {
  let signe = 0;
  for (let i = 0; i < poly.length; i++) {
    const [ax, ay] = poly[i];
    const [bx, by] = poly[(i + 1) % poly.length];
    const c = (bx - ax) * (y - ay) - (by - ay) * (x - ax);
    if (Math.abs(c) < 1e-9) continue;
    if (signe === 0) signe = Math.sign(c);
    else if (Math.sign(c) !== signe) return false;
  }
  return true;
}

describe('les réglages de l’atelier', () => {
  it('suivent la grille du Python : de −2 à 2 par pas de 0,5', () => {
    expect([REGLAGE_MIN, REGLAGE_MAX, REGLAGE_PAS]).toEqual([GRILLE[0], GRILLE[GRILLE.length - 1], GRILLE[1] - GRILLE[0]]);
    for (const v of [W1_DEPART, W2_DEPART, B_DEPART]) expect(GRILLE).toContain(v);
    expect(PORTE_DEPART).toBe('et');
    expect(PORTES_ATELIER).toEqual([
      { porte: 'et', nom: 'ET' },
      { porte: 'ou', nom: 'OU' },
      { porte: 'ou_exclusif', nom: 'OU exclusif' },
    ]);
  });

  it('au départ, sur ET : 2 points sur 4 ; b = −1,5 les classe tous', () => {
    expect(bienClasses([W1_DEPART, W2_DEPART], B_DEPART, 'et')).toBe(2);
    expect(bilan(bienClasses([W1_DEPART, W2_DEPART], B_DEPART, 'et'))).toBe('2 points sur 4 bien classés.');
    expect(bilan(bienClasses([W1_DEPART, W2_DEPART], -1.5, 'et'))).toBe('Les 4 points sont bien classés.');
  });

  it('écrit les réglages à la française, avec le signe moins', () => {
    expect(GRILLE.map(ecrireReglage)).toEqual([
      `${MOINS}2`,
      `${MOINS}1,5`,
      `${MOINS}1`,
      `${MOINS}0,5`,
      '0',
      '0,5',
      '1',
      '1,5',
      '2',
    ]);
    expect(ecrireReglage(-0)).toBe('0');
  });

  it('le bilan, pour chaque compte possible', () => {
    expect([0, 1, 2, 3, 4].map(bilan)).toEqual([
      'Aucun point n’est bien classé.',
      '1 point sur 4 bien classé.',
      '2 points sur 4 bien classés.',
      '3 points sur 4 bien classés.',
      'Les 4 points sont bien classés.',
    ]);
  });
});

describe('les points : la somme, la réponse, et si elle est juste', () => {
  it('suivent sortieSeuil et bienClasses sur toute la grille, pour les trois portes', () => {
    for (const porte of PORTES_TOUTES) {
      for (const [w1, w2, b] of reglages()) {
        const etats = etatDesPoints(w1, w2, b, porte);
        expect(etats.map((e) => e.point)).toEqual(POINTS);
        expect(etats.map((e) => e.attendu)).toEqual(PORTES[porte]);
        expect(etats.map((e) => e.reponse)).toEqual(POINTS.map((x) => sortieSeuil([w1, w2], b, x)));
        expect(etats.filter((e) => e.juste)).toHaveLength(bienClasses([w1, w2], b, porte));
        for (const e of etats) expect(e.somme).toBe(w1 * e.point[0] + w2 * e.point[1] + b);
      }
    }
  });

  it('le texte d’un point le dit en mots', () => {
    const [p00, p01, , p11] = etatDesPoints(W1_DEPART, W2_DEPART, B_DEPART, 'et');
    expect(texteDuPoint(p00)).toBe(`(0, 0)${FINE}: somme 0, réponse 0, il faut 0, bien classé.`);
    expect(texteDuPoint(p01)).toBe(`(0, 1)${FINE}: somme 1, réponse 1, il faut 0, mal classé.`);
    expect(texteDuPoint(p11)).toBe(`(1, 1)${FINE}: somme 2, réponse 1, il faut 1, bien classé.`);
    // Les morceaux qui ne se coupent pas, mis bout à bout, font la phrase.
    expect(morceauxDuPoint(p01)).toEqual([`(0, 1)${FINE}:`, 'somme 1,', 'réponse 1,', 'il faut 0,', 'mal classé.']);
    expect(morceauxDuPoint(p01).join(' ')).toBe(texteDuPoint(p01));
    expect(texteDuPoint(etatDesPoints(1, 1, -1.5, 'et')[0])).toBe(`(0, 0)${FINE}: somme ${MOINS}1,5, réponse 0, il faut 0, bien classé.`);
  });
});

describe('le dessin : la droite et le côté « 1 »', () => {
  it('sans poids, pas de droite, et le message du brief', () => {
    for (const b of GRILLE) {
      expect(droite(0, 0, b)).toBeNull();
      expect(remarque(0, 0, b)).toBe(SANS_POIDS);
      // Le côté « 1 » : tout le dessin si b > 0, rien sinon.
      expect(regionUn(0, 0, b).length).toBe(b > 0 ? 4 : 0);
    }
    expect(SANS_POIDS).toBe(`Sans poids, le neurone répond pareil partout${FINE}: 1 si b${INSECABLE}>${INSECABLE}0, sinon 0.`);
  });

  it('la droite passe par la somme nulle, et le côté « 1 » contient les points où le neurone répond 1', () => {
    for (const [w1, w2, b] of reglages()) {
      if (w1 === 0 && w2 === 0) continue;
      const poly = regionUn(w1, w2, b);
      const d = droite(w1, w2, b);
      if (d !== null) {
        for (const [x, y] of d) {
          expect(Math.abs(w1 * x + w2 * y + b), `${w1} ${w2} ${b}`).toBeLessThan(1e-9);
          expect(x).toBeGreaterThanOrEqual(DOMAINE_MIN - 1e-9);
          expect(x).toBeLessThanOrEqual(DOMAINE_MAX + 1e-9);
          expect(y).toBeGreaterThanOrEqual(DOMAINE_MIN - 1e-9);
          expect(y).toBeLessThanOrEqual(DOMAINE_MAX + 1e-9);
        }
        expect(remarque(w1, w2, b)).toBeNull();
      } else {
        // La droite ne coupe pas le dessin : le carré de 0 à 1 est tout entier d'un côté, et le texte le dit.
        const r = sortieSeuil([w1, w2], b, [0, 0]);
        expect(POINTS.every((x) => sortieSeuil([w1, w2], b, x) === r), `${w1} ${w2} ${b}`).toBe(true);
        expect(remarque(w1, w2, b)).toBe(`La droite passe hors du dessin${FINE}: dans tout le carré, le neurone répond ${r}.`);
      }
      // Chaque point du côté « 1 » est dans le polygone ; un point qui répond 0 n'y est pas, sauf sur son bord.
      for (const x of POINTS) {
        const s = w1 * x[0] + w2 * x[1] + b;
        if (s > 0) expect(dansLePolygone(poly, x[0], x[1]), `${w1} ${w2} ${b} ${x}`).toBe(true);
        if (s < 0 && poly.length > 0) expect(dansLePolygone(poly, x[0], x[1]), `${w1} ${w2} ${b} ${x}`).toBe(false);
      }
      for (const [x, y] of poly) {
        expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
        expect(w1 * x + w2 * y + b).toBeGreaterThanOrEqual(-1e-9);
      }
    }
  });

  it('au départ, la droite x1 + x2 = 0 coupe le coin du dessin', () => {
    const d = droite(W1_DEPART, W2_DEPART, B_DEPART);
    expect(d).not.toBeNull();
    expect(regionUn(W1_DEPART, W2_DEPART, B_DEPART).length).toBeGreaterThanOrEqual(3);
  });
});

describe('l’acquis et le défi', () => {
  it('l’acquis : 4 sur 4 sur ET ou sur OU, avec un autre réglage que celui du départ', () => {
    expect(gagneNeurone(W1_DEPART, W2_DEPART, B_DEPART, 'et')).toBe(false);
    // Le départ classe déjà OU : ce n'est pas un réglage du lecteur.
    expect(bienClasses([W1_DEPART, W2_DEPART], B_DEPART, 'ou')).toBe(4);
    expect(gagneNeurone(W1_DEPART, W2_DEPART, B_DEPART, 'ou')).toBe(false);
    expect(gagneNeurone(1, 1, -1.5, 'et')).toBe(true);
    expect(gagneNeurone(1, 1, -0.5, 'ou')).toBe(true);
    expect(gagneNeurone(1, 1, -0.5, 'ou_exclusif')).toBe(false);
    for (const [w1, w2, b] of reglages()) {
      for (const porte of PORTES_TOUTES) {
        const depart = w1 === W1_DEPART && w2 === W2_DEPART && b === B_DEPART;
        expect(gagneNeurone(w1, w2, b, porte)).toBe(porte !== 'ou_exclusif' && !depart && bienClasses([w1, w2], b, porte) === 4);
      }
    }
  });

  it('le défi : ET puis OU avec les mêmes poids, en ne changeant que b', () => {
    let r: Reussites = {};
    expect(etatDuDefi(r, 1, 1)).toBe(`Pas encore${FINE}: classe d’abord les 4 points de ET, ou ceux de OU.`);
    r = noterReussite(r, 1, 1, 0, 'et'); // 2 sur 4 : rien de noté
    expect(r).toEqual({});
    r = noterReussite(r, 1, 1, -1.5, 'et');
    expect(defiReussi(r)).toBe(false);
    expect(etatDuDefi(r, 1, 1)).toBe(`ET est classé avec w1 = 1 et w2 = 1${FINE}: garde-les, et trouve b pour OU.`);
    expect(etatDuDefi(r, 0.5, 1)).toBe(`Pas encore${FINE}: classe d’abord les 4 points de ET, ou ceux de OU.`);
    // Le OU exclusif ne compte pas, ni d'autres poids.
    r = noterReussite(r, 1, 1, -0.5, 'ou_exclusif');
    r = noterReussite(r, 0.5, 0.5, 0, 'ou');
    expect(defiReussi(r)).toBe(false);
    expect(etatDuDefi(r, 0.5, 0.5)).toBe(`OU est classé avec w1 = 0,5 et w2 = 0,5${FINE}: garde-les, et trouve b pour ET.`);
    r = noterReussite(r, 1, 1, -0.5, 'ou');
    expect(defiReussi(r)).toBe(true);
    expect(etatDuDefi(r, 2, -2)).toBe(DEFI_NEURONE_REUSSI);
    expect(DEFI_NEURONE_REUSSI).toBe(`Défi réussi${FINE}: les mêmes poids classent ET et OU, seul b change.`);
  });

  it('noterReussite ne modifie pas ce qu’elle reçoit', () => {
    const r: Reussites = Object.freeze({});
    const r2 = noterReussite(r, 1, 1, -1.5, 'et');
    expect(r).toEqual({});
    expect(noterReussite(r2, 1, 1, -1.5, 'et')).toEqual(r2);
  });
});
