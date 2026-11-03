// Le jumeau TypeScript des prénoms (projets/mini-modele/mini_modele/donnees.py) :
// vocabulaire, encodage, et partage entraînement/validation.
//
// Le mini-modèle lit un prénom caractère par caractère. Chaque caractère a un
// numéro ; le numéro 0 est le « bord » (BORD, un point), qui marque le début et
// la fin de chaque prénom : « ba » devient 0, b, a, 0.
//
// Le partage en deux est le même qu'en Python : la liste est mélangée par
// Hasard(GRAINE_PARTAGE), un prénom sur dix va en validation (ceux que le
// modèle ne voit jamais pendant l'entraînement), le reste en entraînement.
// Les attendus (tests/attendus-donnees.json) le prouvent dans donnees.test.ts.

import prenomsBrut from '../../../../projets/mini-modele/donnees/prenoms.txt?raw';
import { comparerPointsDeCode } from '../points-de-code';
import { Hasard } from './calcul';

export const BORD = '.'; // le numéro 0 : le début et la fin d'un prénom
export const GRAINE_PARTAGE = 20261103; // la graine du mélange, la même pour tous les réglages

/** Les prénoms prêts pour le mini-modèle. */
export interface Donnees {
  vocabulaire: string;
  entrainement: number[][];
  validation: number[][];
  /** Tous les prénoms de la liste : sert à marquer « existe déjà ». */
  connus: Set<string>;
}

/** Un prénom par ligne, coupée au « \n » ; le saut de ligne final ne compte pas. */
export function prenomsDuTexte(texte: string): string[] {
  const prenoms = texte.split('\n');
  if (prenoms[prenoms.length - 1] === '') {
    prenoms.pop();
  }
  return prenoms;
}

/** Les prénoms du fichier donnees/prenoms.txt, lu tel quel (?raw : sans aucune traduction des fins de ligne). */
export function chargerPrenoms(): string[] {
  return prenomsDuTexte(prenomsBrut);
}

/** BORD, puis les caractères distincts des prénoms, triés par point de code. */
export function vocabulaireDe(prenoms: Iterable<string>): string {
  const distincts = new Set<string>();
  for (const prenom of prenoms) {
    if (prenom.includes(BORD)) {
      throw new RangeError(
        `Le caractère « ${BORD} » est réservé au début et à la fin des prénoms : retire-le du prénom « ${prenom} ».`,
      );
    }
    for (const caractere of prenom) {
      distincts.add(caractere);
    }
  }
  return BORD + [...distincts].sort(comparerPointsDeCode).join('');
}

/** Les numéros du prénom, entre deux bords : [0, ...numéros, 0]. */
export function encoder(prenom: string, vocabulaire: string): number[] {
  const caracteres = Array.from(vocabulaire); // par point de code, comme les str de Python
  const numeros = [0];
  for (const caractere of prenom) {
    const numero = caracteres.indexOf(caractere, 1); // à partir de 1 : le bord n'est pas une lettre
    if (numero < 0) {
      throw new RangeError(
        `Caractère inconnu du vocabulaire : « ${caractere} » (dans « ${prenom} »). ` +
          'Le vocabulaire vient de vocabulaireDe, sur une liste qui contient ce caractère.',
      );
    }
    numeros.push(numero);
  }
  numeros.push(0);
  return numeros;
}

/** Le texte des numéros, en ignorant les 0 (les bords). */
export function decoder(ids: Iterable<number>, vocabulaire: string): string {
  const caracteres = Array.from(vocabulaire);
  const taille = caracteres.length;
  let texte = '';
  for (const numero of ids) {
    if (typeof numero !== 'number' || !Number.isInteger(numero) || numero < 0 || numero >= taille) {
      throw new RangeError(
        `Numéro hors du vocabulaire : ${String(numero)} (il y a ${taille} caractères, numérotés de 0 à ${taille - 1}).`,
      );
    }
    if (numero !== 0) {
      texte += caracteres[numero];
    }
  }
  return texte;
}

/**
 * Copie la liste, la mélange avec Hasard(GRAINE_PARTAGE), puis la partage en deux.
 *
 * Les len / 10 premiers prénoms mélangés (arrondi vers le bas) vont en validation, le reste en entraînement.
 */
export function preparer(prenoms: readonly string[]): Donnees {
  const vocabulaire = vocabulaireDe(prenoms);
  const melanges = [...prenoms];
  new Hasard(GRAINE_PARTAGE).melanger(melanges);
  const nbValidation = Math.floor(melanges.length / 10);
  const codes = melanges.map((prenom) => encoder(prenom, vocabulaire));
  return {
    vocabulaire,
    entrainement: codes.slice(nbValidation),
    validation: codes.slice(0, nbValidation),
    connus: new Set(melanges),
  };
}

let parDefaut: Donnees | null = null;

/** Les prénoms versionnés (donnees/prenoms.txt), préparés une seule fois. */
export function donneesParDefaut(): Donnees {
  if (parDefaut === null) {
    parDefaut = preparer(chargerPrenoms());
  }
  return parDefaut;
}
