// Les paris du calculateur, et ce que leurs questions affirment.
//
// Leurs bonnes réponses sont calculées par les formules (formules.ts), sur les
// données relevées (donnees.ts) et la forme de ton IA (ton-ia.ts) : rien n'est
// recopié. Si une donnée change (un prix, une forme) et qu'une question ou un
// choix devient faux, la construction s'arrête (« Exemple devenu faux : … »).
//
// choixMemoireTonIA n'a pas encore de pari sur la page d'essai : le plan 5
// s'en servira.

import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre } from '../nombres';
import { materiel, PRIX_LOCATION, TAUX_DE_CHANGE, type PrixLocation } from './donnees';
import { dixPuissance, formaterEuros, formaterQuantite } from './formats';
import {
  coutLocationUsd,
  dureeSecondes,
  memoireEntrainementOctets,
  OCTETS_PAR_GO,
  operationsEntrainement,
  usdEnEur,
  type Forme,
} from './formules';
import { JETONS_PAR_PARAMETRE, MATERIEL_DES_MESURES, MESURES_TON_IA, PRESETS_FORGE } from './ton-ia';

const FINE = '\u202F';

/** L'efficacité supposée des H100 dans le pari sur le coût. */
export const EFFICACITE_PARI_H100 = 0.4;
/** Le matériel du pari sur le coût. */
export const MATERIEL_PARI_H100 = 'h100-sxm';
/** Ce que la question du pari « opérations » dit de ton IA. */
export const PARAMETRES_DE_LA_QUESTION = '433,6 millions';

const exiger = exigeur('src/lib/calculateur/paris.ts, ses données, et le texte des paris du calculateur');

/**
 * Le pari « Combien d'opérations faut-il pour entraîner ton IA (433,6 millions
 * de paramètres, 20 jetons par paramètre) ? ».
 *
 * L'exposant juste e est lu par toExponential() sur 6·N·20N ; les leurres
 * valent e − 6 et e − 3. Les choix sont dans l'ordre croissant.
 */
export function choixOperationsTonIA(forme: Forme = PRESETS_FORGE.tres_grand): Choix[] {
  exiger(
    formaterQuantite(forme.parametres) === PARAMETRES_DE_LA_QUESTION,
    `la question parle de ${PARAMETRES_DE_LA_QUESTION} de paramètres, mais le modèle en a ${formaterQuantite(forme.parametres)}`,
  );
  exiger(JETONS_PAR_PARAMETRE === 20, `la question parle de 20 jetons par paramètre, forge en vise ${JETONS_PAR_PARAMETRE}`);
  const operations = operationsEntrainement(forme.parametres, JETONS_PAR_PARAMETRE * forme.parametres);
  const e = Number(operations.toExponential().split('e')[1]);
  return [e - 6, e - 3, e].map((exposant) => ({ texte: `${dixPuissance(exposant)} opérations`, juste: exposant === e }));
}

/** Le coût de ton IA sur des H100, du prix primaire le plus bas au plus haut. */
export interface FourchetteCoutH100 {
  /** La durée sur une seule H100 SXM à 40 %. */
  secondes: number;
  usdParHeureMin: number;
  usdParHeureMax: number;
  eurMin: number;
  eurMax: number;
}

/**
 * Le coût de l'entraînement de ton IA (20 jetons par paramètre) sur une H100
 * SXM à 40 %, à chaque bout de la fourchette des prix primaires, en euros au
 * taux de la BCE. Le nombre de cartes ne change pas le coût : deux fois plus
 * de cartes, c'est deux fois moins longtemps.
 */
export function fourchetteCoutH100(prix: readonly PrixLocation[] = PRIX_LOCATION): FourchetteCoutH100 {
  const f = PRESETS_FORGE.tres_grand;
  const h100 = materiel(MATERIEL_PARI_H100);
  const secondes = dureeSecondes(operationsEntrainement(f.parametres, JETONS_PAR_PARAMETRE * f.parametres), h100.creteTflops, EFFICACITE_PARI_H100, 1);
  const tarifs = prix.filter((p) => p.materiel === MATERIEL_PARI_H100).map((p) => p.usdParHeure);
  exiger(tarifs.length > 0, 'aucun prix de location n’est relevé pour la H100 SXM');
  let min = tarifs[0];
  let max = tarifs[0];
  for (const t of tarifs) {
    if (t < min) min = t;
    if (t > max) max = t;
  }
  const enEuros = (usdParHeure: number) => usdEnEur(coutLocationUsd(secondes, 1, usdParHeure), TAUX_DE_CHANGE.usdPourUnEur);
  return { secondes, usdParHeureMin: min, usdParHeureMax: max, eurMin: enEuros(min), eurMax: enEuros(max) };
}

const TEXTES_COUT = ['Quelques euros', 'Des dizaines à des centaines d’euros', 'Des dizaines de milliers d’euros'] as const;

/**
 * Le pari « Louer des H100 pour entraîner ton IA coûterait plutôt… ».
 *
 * Juste : « Quelques euros » si toute la fourchette tient entre 1 et 10 € ;
 * « Des dizaines à des centaines d’euros » entre 10 et 1 000 € ; « Des
 * dizaines de milliers d’euros » à partir de 10 000 €. Sinon, l'exemple est
 * devenu faux.
 */
export function choixCoutH100(prix: readonly PrixLocation[] = PRIX_LOCATION): Choix[] {
  const { eurMin, eurMax } = fourchetteCoutH100(prix);
  const dans = (bas: number, haut: number) => eurMin >= bas && eurMax <= haut;
  const juste = dans(1, 10) ? 0 : dans(10, 1000) ? 1 : eurMin >= 10_000 ? 2 : -1;
  exiger(
    juste >= 0,
    `ton IA coûterait de ${formaterEuros(eurMin)} à ${formaterEuros(eurMax)} sur des H100${FINE}: ` +
      'aucun choix du pari ne couvre toute cette fourchette',
  );
  return TEXTES_COUT.map((texte, i) => ({ texte, juste: i === juste }));
}

/**
 * Le pari « La mémoire pour entraîner ton IA tient-elle sur la carte de ce PC ? ».
 *
 * La réponse vient de memoireEntrainementOctets (16·N plus les activations),
 * comparée à la mémoire de la RTX 5070 Ti. Garde-fou : le verdict doit être
 * celui du pic mesuré (10,9 Go), sinon l'exemple est devenu faux.
 */
export function choixMemoireTonIA(picMesureGo: number = MESURES_TON_IA.tres_grand.carte.memoireGo): Choix[] {
  const carte = materiel(MATERIEL_DES_MESURES);
  const calculeTient = memoireEntrainementOctets(PRESETS_FORGE.tres_grand).total < carte.memoireGo * OCTETS_PAR_GO;
  const mesureTient = picMesureGo < carte.memoireGo;
  exiger(
    calculeTient === mesureTient,
    `la formule dit que ton IA ${calculeTient ? 'tient' : 'ne tient pas'} sur ${nombre(carte.memoireGo)} Go, ` +
      `mais le pic mesuré (${String(picMesureGo)} Go) dit le contraire`,
  );
  const go = nombre(carte.memoireGo);
  return [
    { texte: `Moins de ${go} Go`, juste: calculeTient },
    { texte: `Plus de ${go} Go`, juste: !calculeTient },
  ];
}
