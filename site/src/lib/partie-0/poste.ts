// Le diagnostic du projet 0.3 tel que le Python l'a écrit : le fichier
// projets/0.3-poste/tests/attendus.json, lié ici pour le chapitre 0.3 et ses
// paris (paris-0-3.ts), et pour Vitest. Le chapitre ne refait pas le
// diagnostic : il lit ces faits et ces constats.
//
// Ce module importe le fichier .json : un parcours Playwright ne peut pas
// l'importer (B1). Le parcours lit le fichier sur le disque, et passe par les
// fonctions de situations-0-3.ts, qui reçoivent les attendus en argument.

import fichier from '../../../../projets/0.3-poste/tests/attendus.json';
import { trouverSituation, type AttendusPoste, type Constat, type Situation } from './situations-0-3';

const FINE = '\u202F';

/** Les attendus du diagnostic, tels quels. */
export const ATTENDUS_POSTE = fichier as unknown as AttendusPoste;

/**
 * La situation nommée `nom` des attendus : ses faits et ses constats. Un nom
 * absent lève une erreur qui donne les noms présents et dit quoi faire.
 */
export function situation(nom: string): Situation {
  return trouverSituation(ATTENDUS_POSTE, nom);
}

/** Le constat `cle` de la situation `nom`. Un constat absent lève une erreur qui dit quoi faire. */
export function constat(nom: string, cle: string): Constat {
  const s = situation(nom);
  const trouve = s.constats.find((c) => c.cle === cle);
  if (trouve === undefined) {
    throw new Error(
      `Le constat «${FINE}${cle}${FINE}» n’est pas dans la situation «${FINE}${nom}${FINE}» des attendus ` +
        `(constats${FINE}: ${s.constats.map((c) => c.cle).join(', ')}). Revois le texte du chapitre 0.3, ` +
        'ou le diagnostic (projets/0.3-poste/poste/diagnostic.py) et ses attendus.',
    );
  }
  return trouve;
}
