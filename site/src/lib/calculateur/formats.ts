// Les formats du calculateur : durées, quantités, puissances de dix, octets,
// euros et dollars, en français.
//
// Les milliers sont séparés par une espace fine insécable (U+202F) et les
// décimales par une virgule (nombre(), de ../nombres). Rien n'est jamais écrit
// en notation scientifique (« e+ ») : les puissances de dix ont leur format.
//
// Toute entrée non finie ou négative lève une erreur : l'interface ne doit
// jamais en produire. Aux frontières, l'unité suit la valeur arrondie : on lit
// « 1 min », jamais « 60 s ».

import { nombre } from '../nombres';
import { OCTETS_PAR_GO } from './formules';

const FINE = '\u202F';
const SECONDES_PAR_HEURE = 3600;
const SECONDES_PAR_JOUR = 86_400;
/** Une année julienne : 365,25 jours. */
export const SECONDES_PAR_AN = 31_557_600;
const OCTETS_PAR_MO = 1024 * 1024;
const CHIFFRES_SUPERIEURS = '⁰¹²³⁴⁵⁶⁷⁸⁹';

function verifier(x: number, fonction: string): void {
  if (!(Number.isFinite(x) && x >= 0)) {
    throw new RangeError(
      `${fonction} : la valeur doit être un nombre fini, positif ou nul (reçu ${String(x)}). ` +
        'Corrige le calcul avant de l’afficher : la page ne doit jamais montrer NaN, Infinity ni une valeur négative.',
    );
  }
}

/** x arrondi à `decimales` décimales, comme l'arrondit nombre() (la valeur décimale exacte, la moitié vers le haut). */
function arrondi(x: number, decimales: number): number {
  return Number(x.toFixed(decimales));
}

/** Le pluriel français : singulier sous 2 (« 1,5 million »). */
function accord(valeurAffichee: number, singulier: string, pluriel: string): string {
  return valeurAffichee < 2 ? singulier : pluriel;
}

/**
 * Une durée lisible :
 * - moins d'une demi-seconde : « moins d’une seconde » ;
 * - moins de 60 s : « 42 s » ; moins d'une heure : « 17 min » ;
 * - moins de 48 h : « 5,3 h » sous 10 h, « 16 h » au-delà ;
 * - moins d'un an (365,25 jours) : « 5,9 jours » sous 10 jours, « 135 jours » au-delà ;
 * - puis « 1,2 an », « 2,0 ans », « 27 315 ans » (une décimale sous 10 ans).
 */
export function formaterDuree(secondes: number): string {
  verifier(secondes, 'formaterDuree');
  if (secondes < 0.5) return 'moins d’une seconde';
  if (arrondi(secondes, 0) < 60) return `${nombre(secondes)} s`;
  const minutes = secondes / 60;
  if (arrondi(minutes, 0) < 60) return `${nombre(minutes)} min`;
  const heures = secondes / SECONDES_PAR_HEURE;
  if (arrondi(heures, 1) < 10) return `${nombre(heures, 1)} h`;
  if (arrondi(heures, 0) < 48) return `${nombre(heures)} h`;
  if (secondes < SECONDES_PAR_AN) {
    const jours = secondes / SECONDES_PAR_JOUR;
    return `${nombre(jours, arrondi(jours, 1) < 10 ? 1 : 0)} jours`;
  }
  const ans = secondes / SECONDES_PAR_AN;
  const decimales = arrondi(ans, 1) < 10 ? 1 : 0;
  return `${nombre(ans, decimales)} ${accord(arrondi(ans, decimales), 'an', 'ans')}`;
}

/** Trois chiffres significatifs, écrits sans « e+ » : 8,67 ; 86,7 ; 867 ; 15 600. */
function troisChiffres(x: number): string {
  const r = Number(x.toPrecision(3));
  return nombre(r, r < 10 ? 2 : r < 100 ? 1 : 0);
}

/**
 * Une quantité (paramètres, jetons) :
 * - un entier sous un million : « 999 999 » ;
 * - en millions avec une décimale : « 433,6 millions », « 1,5 million » ;
 * - en milliards à trois chiffres significatifs : « 8,67 milliards », et
 *   au-delà de 10¹² toujours en milliards : « 15 600 milliards ».
 */
export function formaterQuantite(n: number): string {
  verifier(n, 'formaterQuantite');
  if (arrondi(n, 0) < 1e6) return nombre(n);
  const millions = n / 1e6;
  if (arrondi(millions, 1) < 1000) return `${nombre(millions, 1)} ${accord(arrondi(millions, 1), 'million', 'millions')}`;
  const milliards = Number((n / 1e9).toPrecision(3));
  return `${troisChiffres(milliards)} ${accord(milliards, 'milliard', 'milliards')}`;
}

/** 10 et son exposant en chiffres supérieurs : dixPuissance(19) donne « 10¹⁹ ». */
export function dixPuissance(exposant: number): string {
  if (!Number.isSafeInteger(exposant)) {
    throw new RangeError(`dixPuissance : l’exposant doit être un entier (reçu ${String(exposant)}).`);
  }
  const chiffres = String(Math.abs(exposant))
    .split('')
    .map((c) => CHIFFRES_SUPERIEURS[Number(c)])
    .join('');
  return `10${exposant < 0 ? '⁻' : ''}${chiffres}`;
}

/** Une puissance de dix à trois chiffres : « 2,26 × 10¹⁹ », avec des espaces fines autour de ×. */
export function formaterPuissanceDeDix(x: number): string {
  verifier(x, 'formaterPuissanceDeDix');
  const [mantisse, exposant] = x.toExponential(2).split('e');
  return `${nombre(Number(mantisse), 2)}${FINE}×${FINE}${dixPuissance(Number(exposant))}`;
}

/**
 * Des octets en Go de 1 024³ octets : une décimale sous 100 Go (« 8,1 Go »),
 * un entier au-delà, en To au-delà de 1 024 Go (« 6,4 To »). Sous 1 Go, en Mo
 * de 1 024² octets (« 44 Mo »), pour ne jamais lire « 0,0 Go ».
 */
export function formaterOctets(octets: number): string {
  verifier(octets, 'formaterOctets');
  const mo = octets / OCTETS_PAR_MO;
  if (arrondi(mo, 0) < 1024) return `${nombre(mo)} Mo`;
  const go = octets / OCTETS_PAR_GO;
  if (arrondi(go, 1) < 100) return `${nombre(go, 1)} Go`;
  if (arrondi(go, 0) < 1024) return `${nombre(go)} Go`;
  const to = go / 1024;
  return `${nombre(to, arrondi(to, 1) < 100 ? 1 : 0)} To`;
}

/** De grands montants : une décimale sous 10 (« 1,2 million »), un entier au-delà (« 33 millions »). */
function grandMontant(valeur: number, singulier: string, pluriel: string): string {
  const decimales = arrondi(valeur, 1) < 10 ? 1 : 0;
  return `${nombre(valeur, decimales)} ${accord(arrondi(valeur, decimales), singulier, pluriel)} d’euros`;
}

/**
 * Des euros :
 * - « moins d’un euro » ;
 * - deux décimales sous 10 € (« 8,56 € ») ;
 * - un entier sous 1 000 € (« 38 € ») ;
 * - trois chiffres significatifs sous un million (« 174 000 € ») ;
 * - « 1,2 million d’euros », « 33 millions d’euros », puis les milliards de la même façon.
 */
export function formaterEuros(euros: number): string {
  verifier(euros, 'formaterEuros');
  if (euros < 1) return 'moins d’un euro';
  if (arrondi(euros, 2) < 10) return `${nombre(euros, 2)} €`;
  if (arrondi(euros, 0) < 1000) return `${nombre(euros)} €`;
  const significatifs = Number(euros.toPrecision(3));
  if (significatifs < 1e6) return `${nombre(significatifs)} €`;
  const millions = euros / 1e6;
  if (arrondi(millions, 0) < 1000) return grandMontant(millions, 'million', 'millions');
  return grandMontant(euros / 1e9, 'milliard', 'milliards');
}

/** Un prix horaire en dollars : « 2,69 $ ». */
export function formaterPrix(usd: number): string {
  verifier(usd, 'formaterPrix');
  return `${nombre(usd, 2)} $`;
}
