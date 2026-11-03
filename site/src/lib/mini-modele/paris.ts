// Les paris du mini-modèle, et ce que leurs explications affirment.
//
// Leurs bonnes réponses sont calculées par le moteur (Entraineur, etatInitial) :
// rien n'est recopié. Si le moteur change et qu'une phrase de la page devient
// fausse, la construction s'arrête (« Exemple devenu faux : … »).
//
// Ce module fait tourner le moteur : seule la page Astro l'importe (au moment
// de la construction), jamais l'îlot. formaterPerte vit dans nombres.ts, que
// l'îlot peut importer sans rien embarquer d'autre ; elle est réexportée ici.

import type { Choix } from '../choix';
import { decimalesUtiles, formaterPerte, nombre } from '../nombres';
import { etatInitial, type EtatInitialMini } from './apercu';
import { Entraineur, PRESETS_MINI, TAUX_PROPOSES } from './entrainement';

export { formaterPerte } from '../nombres';

const FINE = '\u202F';

/** Le pari sur le taux compare les erreurs de validation à ce pas. */
export const PAS_COMPARES = 200;
/** Le taux « trop grand » du pari (le plus grand des taux proposés). */
export const TAUX_GRAND = 0.3;
/** En deçà de cet écart entre les deux erreurs, les deux taux font « à peu près pareil ». */
export const SEUIL_VERDICT = 0.05;
/** L'erreur de départ doit être à moins de 0,15 de ln V (le pur hasard). */
export const ECART_DEPART_MAX = 0.15;

export type Verdict = 'plus-vite' | 'pareil' | 'moins-bien';
/** Ce que le texte de la page affirme du taux trop grand : il apprend moins bien, ou plus du tout. */
export const VERDICT_ATTENDU: Verdict = 'moins-bien';

/** Le résultat du pari sur le taux, calculé par le moteur. */
export interface ResultatTauxTropGrand {
  /** Le taux du préréglage complet. */
  tauxNormal: number;
  tauxGrand: number;
  /** L'erreur de validation au pas 200, au taux normal. */
  normal: number;
  /** L'erreur de validation au pas 200, au grand taux ; Infinity si elle a explosé. */
  grand: number;
  /** Le pas où l'erreur du grand taux a explosé, ou null. */
  explosionAuPas: number | null;
  verdict: Verdict;
}

function exiger(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(
      `Exemple devenu faux : ${message}. Revoir src/lib/mini-modele/paris.ts, ` +
        'et le texte des paris et de leurs explications sur la page du mini-modèle.',
    );
  }
}

/** Un taux écrit tel qu'il est réglé : « 0,01 », « 0,3 ». */
function texteTaux(taux: number): string {
  return nombre(taux, decimalesUtiles(taux));
}

/**
 * Le pari « Avant tout entraînement, quelle erreur le modèle fera-t-il sur des
 * prénoms qu'il n'a jamais vus ? ».
 *
 * Les choix : 0, l'erreur de validation du pas 0 (la bonne) et V, dans
 * l'ordre croissant. L'erreur de départ doit être proche de ln V, l'erreur du
 * pur hasard (à moins de 0,15), sinon l'exemple est devenu faux.
 */
export function choixErreurDeDepart(initial: EtatInitialMini = etatInitial('complet')): Choix[] {
  const perte = initial.perteValidation;
  const v = initial.tailleVocabulaire;
  exiger(
    Math.abs(perte - initial.perteHasard) < ECART_DEPART_MAX,
    `l'erreur de départ (${formaterPerte(perte)}) s'écarte de ln V (${formaterPerte(initial.perteHasard)}) ` +
      `de ${nombre(ECART_DEPART_MAX, 2)} ou plus : le modèle de départ ne devine plus au hasard`,
  );
  const choix = [
    { valeur: 0, texte: '0', juste: false },
    { valeur: perte, texte: formaterPerte(perte), juste: true },
    { valeur: v, texte: String(v), juste: false },
  ].sort((a, b) => a.valeur - b.valeur);
  exiger(new Set(choix.map((c) => c.texte)).size === 3, 'deux choix du pari sur l’erreur de départ ont le même texte');
  return choix.map(({ texte, juste }) => ({ texte, juste }));
}

/** L'erreur de validation au pas 200 du préréglage complet, au taux donné (Infinity si elle explose). */
function erreurAuPasCompare(tauxMax: number): { perte: number; explosionAuPas: number | null } {
  const e = new Entraineur({ ...PRESETS_MINI.complet, tauxMax });
  while (e.pas < PAS_COMPARES && !e.diverge) e.faireUnPas();
  if (e.diverge) return { perte: Infinity, explosionAuPas: e.pas };
  const perte = e.perteValidation();
  return Number.isFinite(perte) ? { perte, explosionAuPas: null } : { perte: Infinity, explosionAuPas: e.pas };
}

let resultat: ResultatTauxTropGrand | null = null;

/**
 * Le résultat du pari sur le taux, calculé une fois et gardé : 200 pas du
 * préréglage complet à son taux (0,01), puis 200 pas au taux de 0,3, et les
 * deux erreurs de validation au pas 200.
 *
 * Une erreur qui explose (l'entraînement diverge, ou la validation n'est pas
 * finie) vaut Infinity. Le verdict compare les deux erreurs, à 0,05 près.
 */
export function resultatTauxTropGrand(): ResultatTauxTropGrand {
  if (resultat === null) {
    const tauxNormal = PRESETS_MINI.complet.tauxMax;
    exiger(TAUX_PROPOSES.includes(TAUX_GRAND), `le taux de ${texteTaux(TAUX_GRAND)} n'est plus dans les taux proposés`);
    exiger(TAUX_GRAND > tauxNormal, `le taux du préréglage complet (${texteTaux(tauxNormal)}) n'est plus plus petit que ${texteTaux(TAUX_GRAND)}`);
    const normal = erreurAuPasCompare(tauxNormal);
    exiger(
      normal.explosionAuPas === null,
      `au taux du préréglage complet (${texteTaux(tauxNormal)}), l'erreur explose au pas ${normal.explosionAuPas}`,
    );
    const grand = erreurAuPasCompare(TAUX_GRAND);
    const ecart = grand.perte - normal.perte;
    const verdict: Verdict = ecart < -SEUIL_VERDICT ? 'plus-vite' : ecart > SEUIL_VERDICT ? 'moins-bien' : 'pareil';
    resultat = Object.freeze({
      tauxNormal,
      tauxGrand: TAUX_GRAND,
      normal: normal.perte,
      grand: grand.perte,
      explosionAuPas: grand.explosionAuPas,
      verdict,
    });
  }
  return resultat;
}

/** Le verdict doit être celui que le texte de la page affirme. */
function verifierVerdict(r: ResultatTauxTropGrand): void {
  exiger(
    r.verdict === VERDICT_ATTENDU,
    `au pas ${PAS_COMPARES}, le taux de ${texteTaux(r.tauxGrand)} donne le verdict « ${r.verdict} », ` +
      `mais la page affirme « ${VERDICT_ATTENDU} » (il apprend moins bien, ou plus du tout)`,
  );
}

const TEXTES_VERDICT: readonly [Verdict, string][] = [
  ['plus-vite', 'Il apprend plus vite'],
  ['pareil', 'À peu près pareil'],
  ['moins-bien', 'Il apprend moins bien, ou plus du tout'],
];

/**
 * Le pari « Avec un taux trente fois plus grand (0,3), que se passe-t-il
 * pendant les 200 premiers pas ? ». Le choix juste suit le verdict du moteur,
 * qui doit être celui du texte (moins bien).
 */
export function choixTauxTropGrand(r: ResultatTauxTropGrand = resultatTauxTropGrand()): Choix[] {
  verifierVerdict(r);
  return TEXTES_VERDICT.map(([verdict, texte]) => ({ texte, juste: verdict === r.verdict }));
}

// Les rapports possibles entre deux taux proposés, en toutes lettres.
const EN_LETTRES: Readonly<Record<number, string>> = { 3: 'trois', 10: 'dix', 30: 'trente', 100: 'cent', 300: 'trois cents' };

/**
 * La question du pari sur le taux, avec le rapport calculé entre le grand taux
 * et celui du préréglage : « Avec un taux trente fois plus grand (0,3), que
 * se passe-t-il pendant les 200 premiers pas ? ».
 */
export function questionTauxTropGrand(): string {
  const rapport = TAUX_GRAND / PRESETS_MINI.complet.tauxMax;
  const entier = Math.round(rapport);
  exiger(Math.abs(rapport - entier) < 1e-9 * rapport, `le grand taux n'est plus un multiple entier du taux du préréglage`);
  const fois = EN_LETTRES[entier] ?? nombre(entier);
  return (
    `Avec un taux ${fois} fois plus grand (${texteTaux(TAUX_GRAND)}), ` +
    `que se passe-t-il pendant les ${nombre(PAS_COMPARES)} premiers pas${FINE}?`
  );
}

/**
 * L'explication du pari sur le taux, avec les nombres calculés. Si l'erreur
 * du grand taux a explosé, elle dit au pas où, sans citer d'erreur (ni NaN ni
 * Infinity) pour ce taux. Sinon, elle compare les deux erreurs au pas 200, et
 * dit si le grand taux apprend quand même (son erreur passe sous celle du
 * départ : il apprend, bien plus lentement) ou plus du tout.
 */
export function explicationTauxTropGrand(r: ResultatTauxTropGrand = resultatTauxTropGrand()): string {
  verifierVerdict(r);
  const depart = etatInitial('complet').perteValidation;
  exiger(r.normal < depart, `au taux de ${texteTaux(r.tauxNormal)}, l'erreur ne baisse plus en ${PAS_COMPARES} pas`);
  const normal =
    `Au taux de ${texteTaux(r.tauxNormal)}, l’erreur de validation passe de ${formaterPerte(depart)} ` +
    `à ${formaterPerte(r.normal)} en ${nombre(PAS_COMPARES)} pas.`;
  if (r.explosionAuPas !== null) {
    return (
      `Au taux de ${texteTaux(r.tauxGrand)}, l’erreur a explosé au pas ${nombre(r.explosionAuPas)}${FINE}: ` +
      'chaque correction est si grande que le modèle saute par-dessus les bonnes valeurs, ' +
      `et il n’apprend plus rien. ${normal}`
    );
  }
  const comparaison =
    `Au pas ${nombre(PAS_COMPARES)}, l’erreur de validation vaut ${formaterPerte(r.grand)} au taux de ` +
    `${texteTaux(r.tauxGrand)}, contre ${formaterPerte(r.normal)} au taux de ${texteTaux(r.tauxNormal)}.`;
  if (r.grand < depart) {
    // Le grand taux apprend aussi (son erreur passe sous celle du départ), seulement bien plus lentement.
    return (
      `${comparaison} Les deux partent de ${formaterPerte(depart)}${FINE}: le grand taux apprend aussi, ` +
      'mais bien plus lentement, car ses corrections trop grandes font sauter le modèle par-dessus ' +
      'les bonnes valeurs au lieu de s’y poser.'
    );
  }
  return (
    `${comparaison} Au départ, elle valait ${formaterPerte(depart)}${FINE}: avec des corrections trop grandes, ` +
    'le modèle saute par-dessus les bonnes valeurs sans s’en approcher, et il n’apprend plus rien.'
  );
}
