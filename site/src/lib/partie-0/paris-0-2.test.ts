// Les paris du chapitre 0.2 et les textes de ses trois figures : les bonnes
// réponses viennent du jumeau des maths utiles (maths.ts), jamais écrites à la
// main, et les phrases des figures disent exactement ce que la tâche demande.

import { describe, expect, it } from 'vitest';
import {
  cosinus,
  descendre,
  EXEMPLE_COMPTES,
  GRAINE_TIRAGE,
  matriceFoisVecteur,
  pasPourAtteindre,
  pente,
  probabilites,
  produitScalaire,
  TAUX_DESCENTE,
  tirages,
} from './maths';
import {
  A_DEPART,
  B_DEPART,
  cheminDeDescente,
  choixFormeMatrice,
  choixPente,
  choixProduitScalaire,
  choixTauxGrand,
  choixTauxMoitie,
  choixTirage,
  directionSelonCosinus,
  ecrireNombre,
  ecrireVecteur,
  ECART_EXPLOSION,
  etatDescente,
  faitsDuPariTirage,
  faitsTauxGrand,
  FOND,
  INDICE_TAUX_DEPART,
  INDICE_TIRAGES_DEPART,
  lignePas,
  MATRICE_DU_PARI,
  MESSAGE_EXPLOSION,
  messageVecteurNul,
  NOMBRES_DE_TIRAGES,
  PAS_MAX,
  perpendiculaires,
  phrasePente,
  resultatsDesTirages,
  SEUIL_DU_PARI,
  TAUX_DEPART,
  TAUX_GRAND,
  TAUX_MOITIE,
  texteCosinus,
  texteScalaire,
  VECTEURS_DU_PARI,
  X0_DEPART,
} from './paris-0-2';

const FINE = '\u202F';
const MOINS = '\u2212';

describe('les bonnes réponses viennent du jumeau', () => {
  it('produit scalaire : (2, 1) · (−1, 2), calculé', () => {
    const [a, b] = VECTEURS_DU_PARI;
    expect(a).toEqual([2, 1]);
    expect(b).toEqual([-1, 2]);
    expect(choixProduitScalaire().map((c) => c.texte)).toEqual(['0', '3', '4']);
    expect(choixProduitScalaire().find((c) => c.juste)?.texte).toBe(String(produitScalaire(a, b)));
  });

  it('forme de la matrice : le nombre de colonnes, que matriceFoisVecteur exige', () => {
    const lignes = MATRICE_DU_PARI.length;
    const colonnes = MATRICE_DU_PARI[0].length;
    expect([lignes, colonnes]).toEqual([3, 4]);
    expect(choixFormeMatrice().map((c) => c.texte)).toEqual(['3', '4', '12']);
    expect(choixFormeMatrice().find((c) => c.juste)?.texte).toBe(String(colonnes));
    // Un vecteur d'autant de nombres que de colonnes passe ; d'autant que de lignes, non.
    expect(matriceFoisVecteur(MATRICE_DU_PARI, new Array<number>(colonnes).fill(1))).toHaveLength(lignes);
    expect(() => matriceFoisVecteur(MATRICE_DU_PARI, new Array<number>(lignes).fill(1))).toThrow(/autant/);
  });

  it('pente en x = 0 : négative, par le signe de pente(0)', () => {
    expect(pente(0)).toBeLessThan(0);
    expect(choixPente().map((c) => c.texte)).toEqual(['Négative', 'Nulle', 'Positive']);
    expect(choixPente().find((c) => c.juste)?.texte).toBe('Négative');
  });

  it('taux 0,5 : un seul pas, face aux 16 du taux de départ', () => {
    expect(TAUX_MOITIE).toBe(0.5);
    expect(SEUIL_DU_PARI).toBe(1.01);
    expect(choixTauxMoitie().map((c) => c.texte)).toEqual([
      String(pasPourAtteindre(0, TAUX_MOITIE, SEUIL_DU_PARI)),
      String(pasPourAtteindre(0, TAUX_DEPART, SEUIL_DU_PARI)),
      'Jamais',
    ]);
    expect(choixTauxMoitie().map((c) => c.texte)).toEqual(['1', '16', 'Jamais']);
    expect(choixTauxMoitie().find((c) => c.juste)?.texte).toBe('1');
  });

  it('taux 1,05 : x s’éloigne du fond, |x₃₀ − 3| > |x₀ − 3|', () => {
    expect(TAUX_GRAND).toBe(1.05);
    const positions = descendre(0, TAUX_GRAND, 30);
    expect(Math.abs(positions[30] - FOND)).toBeGreaterThan(Math.abs(positions[0] - FOND));
    expect(choixTauxGrand().map((c) => c.texte)).toEqual([
      'Il arrive plus vite',
      'Il oscille autour du fond, toujours à la même distance',
      "Il s'éloigne du fond à chaque pas",
    ]);
    expect(choixTauxGrand().find((c) => c.juste)?.texte).toBe("Il s'éloigne du fond à chaque pas");
    // Le distracteur « toujours à la même distance » est ce que fait le taux 1,0 : x va de 0 à 6, puis revient.
    expect(descendre(0, 1.0, 4)).toEqual([0, 6, 0, 6, 0]);
    expect(pasPourAtteindre(0, 1.0, SEUIL_DU_PARI, 30)).toBeNull();
    const faits = faitsTauxGrand();
    expect(faits.distances).toEqual(positions.map((x) => Math.abs(x - FOND)));
    // « À chaque pas » : la distance au fond grandit d'un pas à l'autre, et x change de côté.
    for (let n = 1; n <= 30; n++) {
      expect(faits.distances[n]).toBeGreaterThan(faits.distances[n - 1]);
      expect(Math.sign(positions[n] - FOND)).toBe(-Math.sign(positions[n - 1] - FOND));
    }
  });

  it('tirage : « fer » ne sort pas forcément 6 fois sur 10, le compte vient du jumeau', () => {
    const compte = tirages(probabilites(EXEMPLE_COMPTES), 10, GRAINE_TIRAGE)[0];
    expect(compte).not.toBe(6);
    expect(choixTirage().map((c) => c.texte)).toEqual([
      'Oui, forcément',
      `Pas forcément : ici, ${compte} fois`,
      'Jamais 6 fois',
    ]);
    expect(choixTirage().find((c) => c.juste)?.texte).toBe(`Pas forcément : ici, ${compte} fois`);
    expect(faitsDuPariTirage()).toEqual({ nom: 'fer', proba: 0.6, n: 10, attendu: 6, compte });
  });

  it('chaque pari a exactement un choix juste', () => {
    for (const f of [choixProduitScalaire, choixFormeMatrice, choixPente, choixTauxMoitie, choixTauxGrand, choixTirage]) {
      expect(f().filter((c) => c.juste), f.name).toHaveLength(1);
    }
  });
});

describe('les nombres écrits', () => {
  it('le signe moins est U+2212, jamais « −0 »', () => {
    expect(ecrireNombre(-3.072, 3)).toBe(`${MOINS}3,072`);
    expect(ecrireNombre(-0.0001, 3)).toBe('0,000');
    expect(ecrireNombre(1638400.5, 1)).toBe(`1${FINE}638${FINE}400,5`);
    expect(ecrireVecteur([2, -1])).toBe(`(2,\u00A0${MOINS}1)`);
  });
});

describe('la figure des vecteurs', () => {
  it('part de (3, 1) et (1, 2)', () => {
    expect(A_DEPART).toEqual([3, 1]);
    expect(B_DEPART).toEqual([1, 2]);
  });

  it('le produit scalaire, terme à terme, les négatifs entre parenthèses', () => {
    expect(texteScalaire([3, 1], [1, 2])).toBe('a · b = 3 × 1 + 1 × 2 = 5');
    expect(texteScalaire([2, 1], [-1, 2])).toBe(`a · b = 2 × (${MOINS}1) + 1 × 2 = 0`);
    expect(texteScalaire([-4, -4], [4, 4])).toBe(`a · b = (${MOINS}4) × 4 + (${MOINS}4) × 4 = ${MOINS}32`);
  });

  it('le cosinus, ses longueurs, et ce qu’il dit de la direction', () => {
    expect(texteCosinus([3, 1], [1, 2])).toBe(`cos = 5 ÷ (3,16 × 2,24) = 0,71${FINE}: à peu près la même direction`);
    // Presque perpendiculaires, mais pas tout à fait : les seuils.
    expect(texteCosinus([4, 1], [-1, 3])).toBe(`cos = ${MOINS}1 ÷ (4,12 × 3,16) = ${MOINS}0,08${FINE}: presque perpendiculaires`);
  });

  it('les cas exacts se décident sur les entiers, pas sur le cosinus calculé', () => {
    // Produit scalaire nul : perpendiculaires, cos = 0.
    expect(texteCosinus([2, 1], [-1, 2])).toBe(`cos = 0 ÷ (2,24 × 2,24) = 0${FINE}: perpendiculaires`);
    // Sur une même droite : √2 × √8 ne fait pas exactement 4 en flottants, le cosinus calculé n'est pas 1.
    expect(cosinus([1, 1], [2, 2])).not.toBe(1);
    expect(texteCosinus([1, 1], [2, 2])).toBe(`cos = 4 ÷ (1,41 × 2,83) = 1${FINE}: la même direction`);
    expect(texteCosinus([3, 1], [3, 1])).toBe(`cos = 10 ÷ (3,16 × 3,16) = 1${FINE}: la même direction`);
    expect(texteCosinus([1, 0], [-3, 0])).toBe(`cos = ${MOINS}3 ÷ (1 × 3) = ${MOINS}1${FINE}: des directions opposées`);
    expect(texteCosinus([-4, -4], [4, 4])).toBe(`cos = ${MOINS}32 ÷ (5,66 × 5,66) = ${MOINS}1${FINE}: des directions opposées`);
    // Presque sur la même droite, sans y être : les seuils.
    expect(texteCosinus([4, 1], [4, 0])).toBe(`cos = 16 ÷ (4,12 × 4) = 0,97${FINE}: presque la même direction`);
  });

  it('les seuils du cosinus', () => {
    expect(directionSelonCosinus(0.95)).toBe('presque la même direction');
    expect(directionSelonCosinus(0.9)).toBe('à peu près la même direction');
    expect(directionSelonCosinus(0.3)).toBe('à peu près la même direction');
    expect(directionSelonCosinus(0.29)).toBe('presque perpendiculaires');
    expect(directionSelonCosinus(-0.29)).toBe('presque perpendiculaires');
    expect(directionSelonCosinus(-0.3)).toBe('des directions plutôt opposées');
    expect(directionSelonCosinus(-0.9)).toBe('des directions plutôt opposées');
    expect(directionSelonCosinus(-0.95)).toBe('des directions opposées');
  });

  it('un vecteur nul : pas de direction, pas de cosinus', () => {
    expect(messageVecteurNul([0, 0], [1, 2])).toBe(`a est nul${FINE}: il n’a pas de direction, le cosinus n’existe pas.`);
    expect(messageVecteurNul([1, 2], [0, 0])).toBe(`b est nul${FINE}: il n’a pas de direction, le cosinus n’existe pas.`);
    expect(messageVecteurNul([0, 0], [0, 0])).toBe(
      `a et b sont nuls${FINE}: ils n’ont pas de direction, le cosinus n’existe pas.`,
    );
    expect(messageVecteurNul([3, 1], [1, 2])).toBeNull();
    expect(texteCosinus([0, 0], [1, 2])).toBe(messageVecteurNul([0, 0], [1, 2]));
  });

  it('le défi : a · b = 0 avec deux vecteurs non nuls', () => {
    expect(perpendiculaires([2, 1], [-1, 2])).toBe(true);
    expect(perpendiculaires([3, 1], [1, 2])).toBe(false);
    expect(perpendiculaires([0, 0], [1, 2])).toBe(false);
    expect(perpendiculaires(A_DEPART, B_DEPART)).toBe(false);
  });
});

describe('la figure de la descente', () => {
  it('ses réglages de départ : x = 0, taux 0,1', () => {
    expect(X0_DEPART).toBe(0);
    expect(TAUX_DESCENTE[INDICE_TAUX_DEPART]).toBe(0.1);
    expect(TAUX_DEPART).toBe(0.1);
    expect(FOND).toBe(3);
    expect(pente(FOND)).toBe(0);
  });

  it('la ligne d’un pas, avec trois décimales', () => {
    const x3 = descendre(0, 0.1, 3)[3];
    expect(lignePas(3, x3)).toBe(`Pas 3${FINE}: x = 1,464, erreur = 3,359, pente = ${MOINS}3,072.`);
    expect(lignePas(1, descendre(0, 0.5, 1)[1])).toBe(`Pas 1${FINE}: x = 3,000, erreur = 1,000, pente = 0,000.`);
  });

  it('la phrase de la pente, au pas 0', () => {
    expect(phrasePente(0)).toBe(
      `En x = 0, la pente vaut 2 × (0 ${MOINS} 3) = ${MOINS}6${FINE}: la courbe descend vers la droite.`,
    );
    expect(phrasePente(-1.5)).toBe(
      `En x = ${MOINS}1,5, la pente vaut 2 × (${MOINS}1,5 ${MOINS} 3) = ${MOINS}9${FINE}: la courbe descend vers la droite.`,
    );
    expect(phrasePente(5)).toBe(`En x = 5, la pente vaut 2 × (5 ${MOINS} 3) = 4${FINE}: la courbe monte vers la droite.`);
    expect(phrasePente(3)).toBe(`En x = 3, la pente vaut 2 × (3 ${MOINS} 3) = 0${FINE}: la courbe est à plat, c’est le fond.`);
  });

  it('au taux 1,2, la descente explose au pas 18 et s’arrête là', () => {
    const chemin = cheminDeDescente(0, 1.2, 30);
    expect(chemin).toHaveLength(19);
    expect(chemin).toEqual(descendre(0, 1.2, 18));
    expect(Math.abs(chemin[18] - FOND)).toBeGreaterThan(ECART_EXPLOSION);
    expect(Math.abs(chemin[17] - FOND)).toBeLessThanOrEqual(ECART_EXPLOSION);
    expect(MESSAGE_EXPLOSION).toBe(`x est parti à plus de 1${FINE}000 du fond${FINE}: ce taux fait exploser la descente.`);
    expect(etatDescente(chemin)).toBe(MESSAGE_EXPLOSION);
    expect(lignePas(18, chemin[18])).not.toMatch(/NaN|Infinity|e\+/);
  });

  it('la ligne d’état : la phrase de la pente au pas 0, puis le pas courant', () => {
    expect(etatDescente([0])).toBe(phrasePente(0));
    expect(etatDescente(descendre(0, 0.1, 3))).toBe(lignePas(3, descendre(0, 0.1, 3)[3]));
  });

  it('la figure s’arrête à PAS_MAX pas', () => {
    expect(cheminDeDescente(0, 0.1, PAS_MAX + 10)).toHaveLength(PAS_MAX + 1);
    expect(etatDescente(cheminDeDescente(0, 0.1, PAS_MAX))).toContain(`La figure s’arrête à ${PAS_MAX} pas`);
  });
});

describe('la figure des tirages', () => {
  it('de 10 à 100 000 tirages, 100 au départ', () => {
    expect(NOMBRES_DE_TIRAGES).toEqual([10, 100, 1000, 10000, 100000]);
    expect(NOMBRES_DE_TIRAGES[INDICE_TIRAGES_DEPART]).toBe(100);
  });

  it('chaque issue : la probabilité attendue, et les tirages du jumeau', () => {
    const comptes = tirages(probabilites(EXEMPLE_COMPTES), 100, GRAINE_TIRAGE);
    const lignes = resultatsDesTirages(100, GRAINE_TIRAGE);
    expect(lignes.map((l) => l.compte)).toEqual(comptes);
    expect(lignes[0]).toEqual({
      nom: 'fer',
      proba: 0.6,
      compte: comptes[0],
      attendu: `60${FINE}% attendu`,
      tires: `${comptes[0]} sur 100 tirés (${comptes[0]}${FINE}%)`,
    });
  });

  it('la fréquence a autant de décimales qu’il en faut pour être exacte', () => {
    const comptes = tirages(probabilites(EXEMPLE_COMPTES), 100000, GRAINE_TIRAGE);
    const [fer] = resultatsDesTirages(100000, GRAINE_TIRAGE);
    const pour = (comptes[0] / 1000).toFixed(3).replace('.', ',');
    expect(fer.tires).toBe(`${ecrireNombre(comptes[0])} sur 100${FINE}000 tirés (${pour}${FINE}%)`);
  });
});
