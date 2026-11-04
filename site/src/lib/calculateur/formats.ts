// Les formats du calculateur : durées, heures, quantités, puissances de dix,
// octets, énergie, euros et dollars, dates de relevé, en français.
//
// Les milliers sont séparés par une espace fine insécable (U+202F) et les
// décimales par une virgule (nombre(), de ../nombres). Rien n'est jamais écrit
// en notation scientifique (« e+ ») : les puissances de dix ont leur format.
//
// Toute entrée non finie ou négative lève une erreur : l'interface ne doit
// jamais en produire. Aux frontières, l'unité suit la valeur arrondie : on lit
// « 1 min », jamais « 60 s ».

import { nombre } from '../nombres';
import { cartesMinimum, OCTETS_PAR_GO } from './formules';

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

/**
 * Des octets toujours en Go (jamais en To ni en Mo), pour la division « total ÷ mémoire d'une
 * carte = au moins N cartes » : « 6 571 Go » et non « 6,4 To », pour que le lecteur retrouve N
 * à la main (« 6,4 To ÷ 16 Go » donnerait 410, et non 411). Une décimale sous 100 Go, un entier
 * au-delà, arrondi comme formaterOctets. Si cet arrondi faisait trouver une carte de moins à la
 * main (le total vraiment un peu au-dessus d'un multiple de la mémoire de la carte), le total est
 * arrondi au-dessus : « au moins N cartes » se refait alors toujours à partir du nombre affiché.
 */
export function formaterGoPourLesCartes(octets: number, memoireGo: number): string {
  verifier(octets, 'formaterGoPourLesCartes');
  const cartes = cartesMinimum(octets, memoireGo);
  const go = octets / OCTETS_PAR_GO;
  const decimales = arrondi(go, 1) < 100 ? 1 : 0;
  const echelle = 10 ** decimales;
  let unites = Math.round(arrondi(go, decimales) * echelle);
  if (Math.ceil(unites / (memoireGo * echelle)) < cartes) unites = Math.ceil(go * echelle);
  return `${nombre(unites / echelle, decimales)} Go`;
}

/** Comment s'écrit une monnaie : sous un, son symbole, et « d’euros » après les millions. */
interface Monnaie {
  moinsDeUn: string;
  symbole: string;
  deGrands: string;
}

const EURO: Monnaie = { moinsDeUn: 'moins d’un euro', symbole: '€', deGrands: 'd’euros' };
const DOLLAR: Monnaie = { moinsDeUn: 'moins d’un dollar', symbole: '$', deGrands: 'de dollars' };

/** De grands montants : une décimale sous 10 (« 1,2 million »), un entier au-delà (« 33 millions »). */
function grandMontant(valeur: number, singulier: string, pluriel: string, m: Monnaie): string {
  const decimales = arrondi(valeur, 1) < 10 ? 1 : 0;
  return `${nombre(valeur, decimales)} ${accord(arrondi(valeur, decimales), singulier, pluriel)} ${m.deGrands}`;
}

function montant(x: number, m: Monnaie, fonction: string): string {
  verifier(x, fonction);
  if (x < 1) return m.moinsDeUn;
  if (arrondi(x, 2) < 10) return `${nombre(x, 2)} ${m.symbole}`;
  if (arrondi(x, 0) < 1000) return `${nombre(x)} ${m.symbole}`;
  const significatifs = Number(x.toPrecision(3));
  if (significatifs < 1e6) return `${nombre(significatifs)} ${m.symbole}`;
  const millions = x / 1e6;
  if (arrondi(millions, 0) < 1000) return grandMontant(millions, 'million', 'millions', m);
  return grandMontant(x / 1e9, 'milliard', 'milliards', m);
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
  return montant(euros, EURO, 'formaterEuros');
}

/** Des dollars, comme les euros : « moins d’un dollar », « 8,56 $ », « 383 $ », « 195 000 $ », « 37 millions de dollars ». */
export function formaterDollars(dollars: number): string {
  return montant(dollars, DOLLAR, 'formaterDollars');
}

/** Un prix horaire en dollars : « 2,69 $ ». */
export function formaterPrix(usd: number): string {
  verifier(usd, 'formaterPrix');
  return `${nombre(usd, 2)} $`;
}

/**
 * Une énergie : « moins de 0,1 kWh », une décimale sous 100 kWh (« 42,8 kWh »),
 * un entier sous 10 000 (« 8 640 kWh »), puis de même en MWh, en GWh et en TWh
 * (« 37,3 GWh »).
 */
export function formaterEnergie(kwh: number): string {
  verifier(kwh, 'formaterEnergie');
  if (arrondi(kwh, 1) < 0.1) return 'moins de 0,1 kWh';
  const unites = ['kWh', 'MWh', 'GWh', 'TWh'];
  let valeur = kwh;
  for (let i = 0; i < unites.length; i++) {
    const derniere = i === unites.length - 1;
    if (arrondi(valeur, 1) < 100) return `${nombre(valeur, 1)} ${unites[i]}`;
    if (arrondi(valeur, 0) < 10_000 || derniere) return `${nombre(valeur)} ${unites[i]}`;
    valeur /= 1000;
  }
  throw new Error('formaterEnergie : inatteignable');
}

/**
 * Des heures (la durée d'une location, facturée à l'heure) : « moins de 0,1 h »,
 * une décimale sous 10 h (« 5,3 h »), un entier sous un million (« 843 h »),
 * puis « 1,0 million d’heures », « 1,38 milliard d’heures ».
 */
export function formaterHeures(heures: number): string {
  verifier(heures, 'formaterHeures');
  if (arrondi(heures, 1) < 0.1) return 'moins de 0,1 h';
  if (arrondi(heures, 1) < 10) return `${nombre(heures, 1)} h`;
  if (arrondi(heures, 0) < 1e6) return `${nombre(heures)} h`;
  return `${formaterQuantite(heures)} d’heures`;
}

const MOIS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
] as const;

/**
 * Une date de relevé (AAAA-MM-JJ) en toutes lettres : « 3 novembre 2026 », « 1er août 2026 ».
 * Le jour et le mois sont liés par une espace insécable : une ligne ne les sépare pas.
 */
export function formaterDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  const date = m ? new Date(`${iso}T00:00:00Z`) : null;
  if (m === null || date === null || Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== iso) {
    throw new RangeError(`formaterDate : «${FINE}${iso}${FINE}» n’est pas une date AAAA-MM-JJ du calendrier. Corrige la date de relevé.`);
  }
  const jour = Number(m[3]);
  return `${jour === 1 ? '1er' : String(jour)}\u00A0${MOIS[Number(m[2]) - 1]} ${m[1]}`;
}
