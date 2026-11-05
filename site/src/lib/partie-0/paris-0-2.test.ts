// Les paris du chapitre 0.2 et les textes de ses trois figures : les bonnes
// réponses viennent du jumeau des maths utiles (maths.ts), jamais écrites à la
// main, et les phrases des figures disent exactement ce que la tâche demande.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { etatInitial } from '../mini-modele/apercu';
import { FICHIERS_PARTIE_0 } from './fichiers';
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
  choixErreur,
  choixFormeMatrice,
  choixPente,
  choixProduitScalaire,
  choixTauxGrand,
  choixTauxMoitie,
  choixTirage,
  directionSelonCosinus,
  ecrireApprochee,
  ecrireNombre,
  ecrireVecteur,
  ECART_EXPLOSION,
  etatDescente,
  faitsChaine,
  faitsDuPariTirage,
  faitsTauxGrand,
  FOND,
  INDICE_TAUX_DEPART,
  INDICE_TIRAGES_DEPART,
  lignePas,
  MATRICE_DU_PARI,
  MATRICE_EXEMPLE,
  MESSAGE_EXPLOSION,
  messageVecteurNul,
  NOMBRES_DE_TIRAGES,
  PAS_MAX,
  perpendiculaires,
  phrasePente,
  resultatsDesTirages,
  SEUIL_DU_PARI,
  tableauErreur,
  tableauMatrice,
  tableauSoftmax,
  TAUX_DEPART,
  TAUX_GRAND,
  TAUX_MOITIE,
  texteCosinus,
  texteOuverture,
  texteScalaire,
  VECTEUR_EXEMPLE,
  VECTEURS_DU_PARI,
  X0_DEPART,
  type ChaineAttendue,
  type ErreurAttendue,
  type SoftmaxAttendu,
} from './paris-0-2';

const FINE = '\u202F';
const MOINS = '\u2212';
const INSECABLE = '\u00A0';

/** Les sections des attendus du Python que lisent l'étape 2, l'étape 5 et l'étape 7 (Vitest tourne dans site/). */
interface AttendusLus {
  matrices: { m: number[][]; v: number[]; resultat: number[] | null }[];
  chaine: ChaineAttendue;
  softmax: SoftmaxAttendu[];
  erreur: ErreurAttendue[];
}
const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_0.maths}`, 'utf8')) as AttendusLus;

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

describe('l’ouverture et la matrice de l’étape 2', () => {
  it('l’ouverture : (3, 1) · (1, 2) = 5, calculé', () => {
    expect(texteOuverture()).toBe(`(3,${INSECABLE}1) · (1,${INSECABLE}2) = 5`);
    expect(produitScalaire(A_DEPART, B_DEPART)).toBe(5);
  });

  it('[[1, 2, 3], [0, 1, 0]] × [1, 1, 1] : un produit scalaire par ligne, comme les attendus', () => {
    expect(MATRICE_EXEMPLE).toEqual([
      [1, 2, 3],
      [0, 1, 0],
    ]);
    expect(VECTEUR_EXEMPLE).toEqual([1, 1, 1]);
    expect(tableauMatrice(MATRICE_EXEMPLE, VECTEUR_EXEMPLE)).toEqual([
      [`(1,${INSECABLE}2,${INSECABLE}3)`, '1 × 1 + 2 × 1 + 3 × 1', '6'],
      [`(0,${INSECABLE}1,${INSECABLE}0)`, '0 × 1 + 1 × 1 + 0 × 1', '1'],
    ]);
    // Le premier cas des attendus du Python est cet exemple, et il trouve le même résultat.
    const [premier] = ATTENDUS.matrices;
    expect(premier.m).toEqual(MATRICE_EXEMPLE);
    expect(premier.v).toEqual(VECTEUR_EXEMPLE);
    expect(premier.resultat).toEqual([6, 1]);
  });

  it('une ligne qui ne va pas avec le vecteur arrête le tableau, avec le message du jumeau', () => {
    expect(() => tableauMatrice([[1, 2, 3, 4]], [1, 2, 3])).toThrow(/il en faut autant/);
  });
});

describe('la règle de la chaîne et la pente approchée (attendus du Python)', () => {
  it('écrit la pente approchée avec juste assez de décimales pour qu’elle diffère de l’exacte', () => {
    expect(ecrireApprochee(-6.000000000838668, -6)).toBe(`${MOINS}6,000000001`);
    expect(ecrireApprochee(11.999999999900979, 12)).toBe('11,9999999999');
    expect(ecrireApprochee(2.5, 2)).toBe('2,5');
  });

  it('h(x) = (2x + 1)² en x = 1 : u = 3, h = 9, pente 6 × 2 = 12, approchée 11,9999999999', () => {
    expect(ATTENDUS.chaine).toEqual({ x: 1, h: 9, exacte: 12, approchee: 11.999999999900979 });
    expect(faitsChaine(ATTENDUS.chaine)).toEqual({
      x: '1',
      u: '3',
      h: '9',
      penteExterieur: '6',
      penteInterieur: '2',
      exacte: '12',
      approchee: '11,9999999999',
    });
  });

  it('refuse des attendus qui ne suivent plus la règle', () => {
    expect(() => faitsChaine({ ...ATTENDUS.chaine, exacte: 13 })).toThrow(/Exemple devenu faux/);
    expect(() => faitsChaine({ ...ATTENDUS.chaine, h: 10 })).toThrow(/Exemple devenu faux/);
    expect(() => faitsChaine({ ...ATTENDUS.chaine, approchee: 12.5 })).toThrow(/Exemple devenu faux/);
  });
});

describe('les tableaux et le pari de l’étape 7 (valeurs des attendus, jamais recalculées)', () => {
  it('softmax : une ligne par température, une colonne par mot de l’exemple, en pourcentages', () => {
    expect(tableauSoftmax(ATTENDUS.softmax)).toEqual({
      colonnes: [
        `«${FINE}fer${FINE}», score 2`,
        `«${FINE}métal${FINE}», score 1`,
        `«${FINE}feu${FINE}», score 0,1`,
      ],
      lignes: [
        ['0,5', `86,4${FINE}%`, `11,7${FINE}%`, `1,9${FINE}%`],
        ['1', `65,9${FINE}%`, `24,2${FINE}%`, `9,9${FINE}%`],
        ['2', `50,2${FINE}%`, `30,4${FINE}%`, `19,4${FINE}%`],
      ],
    });
  });

  it('softmax : refuse des probabilités qui contrediraient le texte', () => {
    const [basse, moyenne, haute] = ATTENDUS.softmax;
    // Les températures dans le désordre : le plus grand score ne perdrait plus de terrain en montant.
    expect(() => tableauSoftmax([haute, moyenne, basse])).toThrow(/Exemple devenu faux/);
    // Des probabilités dont la somme ne fait pas 1.
    expect(() => tableauSoftmax([{ ...basse, probabilites: [0.5, 0.3, 0.1] }, moyenne, haute])).toThrow(
      /Exemple devenu faux/,
    );
    // Des scores qui changent d'une ligne à l'autre.
    expect(() => tableauSoftmax([basse, { ...moyenne, scores: [3, 1, 0.1] }, haute])).toThrow(/Exemple devenu faux/);
    // Des probabilités de somme 1, mais dont les pourcentages affichés font 99,9 % (50,0 + 30,0 + 19,9).
    expect(() => tableauSoftmax([basse, moyenne, { ...haute, probabilites: [0.5004, 0.3004, 0.1992] }])).toThrow(
      /pourcentages arrondis/,
    );
  });

  it('−ln p : p, une chance sur…, et l’erreur à trois décimales, jamais « −0 »', () => {
    // Python écrit −ln 1 comme −0.0 : le tableau doit afficher 0.
    expect(Object.is(ATTENDUS.erreur[0].erreur, -0)).toBe(true);
    expect(tableauErreur(ATTENDUS.erreur)).toEqual([
      ['1', '1', '0,000'],
      ['0,5', '2', '0,693'],
      ['0,1', '10', '2,303'],
      ['0,025', '40', '3,689'],
    ]);
  });

  it('−ln p : refuse une erreur qui ne grandit pas quand la chance baisse', () => {
    const [un, demi, dixieme, petit] = ATTENDUS.erreur;
    expect(() => tableauErreur([un, dixieme, demi, petit])).toThrow(/Exemple devenu faux/);
    expect(() => tableauErreur([{ p: 1, erreur: 0.1 }, demi])).toThrow(/Exemple devenu faux/);
  });

  it('le pari « erreur » : 0,025, 3,689 (juste, la valeur des attendus pour p = 1/40) et 40', () => {
    const choix = choixErreur(ATTENDUS.erreur, 40);
    expect(choix.map((c) => c.texte)).toEqual(['0,025', '3,689', '40']);
    expect(choix.filter((c) => c.juste).map((c) => c.texte)).toEqual(['3,689']);
    const ligne = ATTENDUS.erreur.find((e) => e.p === 1 / 40);
    expect(ligne).toBeDefined();
    expect(choix[1].texte).toBe(ecrireNombre(ligne!.erreur, 3));
  });

  it('le pari « erreur » refuse un vocabulaire dont la chance 1/V manque aux attendus', () => {
    expect(() => choixErreur(ATTENDUS.erreur, 39)).toThrow(/Exemple devenu faux/);
    expect(() => choixErreur(ATTENDUS.erreur, 1)).toThrow(/Exemple devenu faux/);
  });
});

describe('le « 40 » du mini-modèle (M7)', { timeout: 60_000 }, () => {
  it('le vocabulaire du mini-modèle est bien celui de la section « erreur » des attendus', () => {
    const V = etatInitial('complet').tailleVocabulaire;
    expect(choixErreur(ATTENDUS.erreur, V).filter((c) => c.juste)).toHaveLength(1);
    expect(choixErreur(ATTENDUS.erreur, V).at(-1)?.texte).toBe(String(V));
  });

  it('le notebook de 0.2 et attendus.py disent le même nombre de caractères', () => {
    const V = etatInitial('complet').tailleVocabulaire;
    // Les nombres que ces deux textes donnent pour le mini-modèle : tous doivent valoir V.
    const nombres = (texte: string, motif: RegExp) => [...texte.matchAll(motif)].map((m) => Number(m[1]));

    const notebook = JSON.parse(readFileSync('../notebooks/0.2-maths.ipynb', 'utf8')) as {
      cells: { cell_type: string; source: string | string[] }[];
    };
    const sources = notebook.cells.map((c) => (Array.isArray(c.source) ? c.source.join('') : c.source));
    const texte = sources.find((s) => s.includes('comme le mini-modèle du site'));
    expect(texte, 'la cellule du notebook qui parle du mini-modèle').toBeDefined();
    const dansLeTexte = nombres(texte!, /(?:parmi|sur|ln) (\d+)/g);
    expect(dansLeTexte.length).toBeGreaterThanOrEqual(3);
    const code = sources.find((s) => s.includes('erreur_de_prediction(p)'));
    expect(code, 'la cellule de code de l’erreur d’une prédiction').toBeDefined();
    const dansLeCode = [
      ...nombres(code!, /1 \/ (\d+)/g),
      ...nombres(code!, /math\.log\((\d+)\)/g),
      ...nombres(code!, /ln (\d+)/g),
    ];
    expect(dansLeCode.length).toBeGreaterThanOrEqual(3);

    const attendusPy = readFileSync('../projets/0.2-maths/maths_utiles/attendus.py', 'utf8');
    const commentaire = attendusPy.split('\n').find((l) => l.includes('comme le mini-modèle'));
    expect(commentaire, 'le commentaire de PROBAS_ERREUR').toBeDefined();
    const dansAttendus = [
      ...nombres(commentaire!, /1\/(\d+)/g),
      ...nombres(commentaire!, /parmi (\d+)/g),
      ...nombres(attendusPy, /PROBAS_ERREUR = \[[^\]]*1 \/ (\d+)\]/g),
    ];
    expect(dansAttendus).toHaveLength(3);

    for (const n of [...dansLeTexte, ...dansLeCode, ...dansAttendus]) expect(n).toBe(V);
  });
});
