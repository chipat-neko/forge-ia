// Le pilotage de la démo du mini-modèle, côté page : un réducteur pur.
//
// reduire(état, événement) donne le nouvel état de la démo et, au plus, un
// message pour le Worker. Les événements viennent du lecteur (lancer, pause,
// recommencer, changer le taux, la vitesse), de la page (onglet caché) ou du
// Worker (ses messages). Rien n'est modifié sur place : un état reçu reste tel
// quel, et la même suite d'événements redonne le même état.
//
// Chaque essai a son numéro, la génération. Recommencer ou changer le taux
// ouvre un nouvel essai : un message du Worker qui porte un autre numéro est
// un reste de l'ancien essai, et il est ignoré entièrement.
//
// Ce module entre dans la page : il n'importe des valeurs que de reglages.ts
// et de nombres.ts, et seulement des types d'apercu.ts et de
// boucle-travailleur.ts (le moteur et la liste des prénoms restent dans le
// Worker). pilote.test.ts le vérifie.

import { nombre } from '../nombres';
import type { EtatInitialMini } from './apercu';
import type { MessageDuTravailleur, MessageVersTravailleur, Prenom, Vitesse } from './boucle-travailleur';
import { PRESETS_MINI, TAUX_PROPOSES, type NomPreset } from './reglages';

export type { Prenom, Vitesse } from './boucle-travailleur';

const FINE = '\u202F';

/** Le message d'une pause automatique, quand l'onglet a été caché. */
export const MESSAGE_ONGLET = `En pause${FINE}: l’onglet était caché. Reprends quand tu veux.`;
/** Le message d'un changement de taux. */
export const MESSAGE_NOUVEAU_TAUX = `Nouveau taux${FINE}: l’entraînement repart de zéro.`;
/** Le message d'un entraînement dont l'erreur a explosé. */
export const MESSAGE_DIVERGENCE = `L’erreur a explosé${FINE}: ce taux est trop grand. Recommence avec un taux plus petit.`;

/** « Terminé : 3 000 pas en 21 s. », avec les nombres réels. */
export function messageTermine(pasTotal: number, dureeMs: number): string {
  return `Terminé${FINE}: ${nombre(pasTotal)} pas en ${nombre(Math.round(dureeMs / 1000))} s.`;
}

/** « La démo s'est arrêtée : … », avec le message du moteur. */
export function messageErreur(message: string): string {
  return `La démo s’est arrêtée${FINE}: ${message}`;
}

/** Où en est la démo. « pret » : l'essai n'a pas encore été lancé. */
export type Phase = 'pret' | 'en-cours' | 'en-pause' | 'termine' | 'diverge' | 'erreur';

/** Une courbe : la perte de chaque pas (le pas p est à l'indice p − 1), et les points de validation. */
export interface Courbe {
  pertes: number[];
  validations: { pas: number; perte: number }[];
}

/** L'état de la démo. */
export interface EtatDemo extends Courbe {
  /** Le numéro de l'essai : il change à chaque recommencement ou changement de taux. */
  generation: number;
  phase: Phase;
  raisonPause: 'lecteur' | 'onglet' | null;
  /** L'indice du taux dans TAUX_PROPOSES. */
  tauxIndex: number;
  vitesse: Vitesse;
  pas: number;
  pasTotal: number;
  /** Les prénoms inventés à chaque validation, en commençant par ceux du pas 0. */
  echantillons: { pas: number; prenoms: Prenom[] }[];
  /** La courbe de l'essai précédent, pour comparer, avec son taux. */
  fantome: (Courbe & { tauxIndex: number }) | null;
  pasParSeconde: number;
  dureeMs: number;
  /** Le message à afficher à la place de la ligne d'état, s'il y en a un. */
  message: string | null;
  /**
   * Ce que le Worker a confirmé : « en-cours » depuis le lancement (ou ses
   * derniers progrès), « en-pause » une fois la pause confirmée (plus aucun
   * progrès n'arrivera ensuite), « arrete » avant le lancement et après la fin.
   */
  travailleur: 'arrete' | 'en-cours' | 'en-pause';
}

/** Ce qui arrive à la démo. */
export type Evenement =
  | { type: 'lancer' }
  | { type: 'pause'; raison: 'lecteur' | 'onglet' }
  | { type: 'recommencer' }
  | { type: 'changer-taux'; tauxIndex: number }
  | { type: 'vitesse'; vitesse: Vitesse }
  | { type: 'message'; message: MessageDuTravailleur };

/** Le nouvel état, et le message à envoyer au Worker (null : aucun). */
export interface Reduction {
  etat: EtatDemo;
  envoi: MessageVersTravailleur | null;
}

function verifierTauxIndex(tauxIndex: number): void {
  if (!Number.isInteger(tauxIndex) || tauxIndex < 0 || tauxIndex >= TAUX_PROPOSES.length) {
    throw new RangeError(
      `L'indice du taux va de 0 à ${TAUX_PROPOSES.length - 1} (une place dans TAUX_PROPOSES), reçu ${tauxIndex}.`,
    );
  }
}

/** L'indice dans TAUX_PROPOSES du taux du préréglage. */
export function tauxIndexParDefaut(preset: NomPreset): number {
  const tauxIndex = TAUX_PROPOSES.indexOf(PRESETS_MINI[preset].tauxMax);
  if (tauxIndex < 0) {
    throw new Error(
      `Le taux du préréglage « ${preset} » (${PRESETS_MINI[preset].tauxMax}) n'est pas dans TAUX_PROPOSES : ` +
        'ajoute-le à la liste dans reglages.ts.',
    );
  }
  return tauxIndex;
}

/**
 * L'état de la démo avant tout entraînement : prêt, au pas 0, avec l'erreur
 * de validation et les prénoms du pas 0 calculés par Astro (initial).
 * L'avant-goût va toujours vite ; l'entraînement complet part au rythme normal.
 */
export function etatDeDepart(initial: EtatInitialMini, tauxIndex: number): EtatDemo {
  verifierTauxIndex(tauxIndex);
  return {
    generation: 1,
    phase: 'pret',
    raisonPause: null,
    tauxIndex,
    vitesse: initial.preset === 'avant-gout' ? 'rapide' : 'normale',
    pas: 0,
    pasTotal: initial.pasTotal,
    pertes: [],
    validations: [{ pas: 0, perte: initial.perteValidation }],
    echantillons: [{ pas: 0, prenoms: initial.echantillons.map((p) => ({ texte: p.texte, existe: p.existe })) }],
    fantome: null,
    pasParSeconde: 0,
    dureeMs: 0,
    message: null,
    travailleur: 'arrete',
  };
}

const inchange = (etat: EtatDemo): Reduction => ({ etat, envoi: null });

/**
 * Un nouvel essai : le pas 0 (gardé en tête des validations et des prénoms),
 * le taux donné, la même vitesse ; la courbe en cours devient le fantôme si
 * elle a au moins un pas. L'ancien essai reçoit une pause.
 */
function nouvelEssai(etat: EtatDemo, tauxIndex: number, message: string | null): Reduction {
  return {
    etat: {
      generation: etat.generation + 1,
      phase: 'pret',
      raisonPause: null,
      tauxIndex,
      vitesse: etat.vitesse,
      pas: 0,
      pasTotal: etat.pasTotal,
      pertes: [],
      validations: etat.validations.filter((v) => v.pas === 0),
      echantillons: etat.echantillons.filter((e) => e.pas === 0),
      fantome: etat.pas > 0 ? { pertes: etat.pertes, validations: etat.validations, tauxIndex: etat.tauxIndex } : etat.fantome,
      pasParSeconde: 0,
      dureeMs: 0,
      message,
      travailleur: 'arrete',
    },
    envoi: { type: 'pause', generation: etat.generation },
  };
}

/** Un message du Worker. Celui d'une autre génération ne change rien (le même objet est rendu). */
function recevoir(etat: EtatDemo, m: MessageDuTravailleur): EtatDemo {
  if (m.generation !== etat.generation) return etat;
  switch (m.type) {
    case 'progres':
      return {
        ...etat,
        pas: m.pas,
        pasTotal: m.pasTotal,
        pertes: [...etat.pertes, ...m.pertes],
        validations: m.validation === undefined ? etat.validations : [...etat.validations, m.validation],
        echantillons: m.echantillons === undefined ? etat.echantillons : [...etat.echantillons, m.echantillons],
        dureeMs: m.dureeMs,
        pasParSeconde: m.pasParSeconde,
        travailleur: 'en-cours',
      };
    case 'etat':
      if (m.etat === 'en-pause') {
        // Une confirmation arrivée après une reprise est périmée : seule une pause en cours la reçoit.
        return etat.phase === 'en-pause' ? { ...etat, travailleur: 'en-pause' } : etat;
      }
      return {
        ...etat,
        phase: m.etat,
        raisonPause: null,
        message: m.etat === 'termine' ? messageTermine(etat.pasTotal, etat.dureeMs) : MESSAGE_DIVERGENCE,
        travailleur: 'arrete',
      };
    case 'erreur':
      return { ...etat, phase: 'erreur', raisonPause: null, message: messageErreur(m.message), travailleur: 'arrete' };
  }
}

/**
 * L'état suivant de la démo, et le message pour le Worker (null : aucun).
 *
 * - lancer : depuis « pret » ou « en-pause » seulement (après la fin, il faut recommencer) ;
 * - pause : depuis « en-cours » seulement ; une pause « onglet » le dit ;
 * - recommencer : un nouvel essai au même taux ;
 * - changer-taux : un nouvel essai au nouveau taux, prêt à lancer, avec un message ;
 * - vitesse : retenue pour le prochain lancement, et envoyée tout de suite en cours ;
 * - message : les progrès, la fin ou l'erreur de l'essai en cours.
 */
export function reduire(etat: EtatDemo, ev: Evenement, preset: NomPreset): Reduction {
  switch (ev.type) {
    case 'lancer':
      if (etat.phase !== 'pret' && etat.phase !== 'en-pause') return inchange(etat);
      return {
        etat: { ...etat, phase: 'en-cours', raisonPause: null, message: null, travailleur: 'en-cours' },
        envoi: {
          type: 'lancer',
          generation: etat.generation,
          reglages: { preset, tauxMax: TAUX_PROPOSES[etat.tauxIndex], vitesse: etat.vitesse },
        },
      };
    case 'pause':
      if (etat.phase !== 'en-cours') return inchange(etat);
      return {
        etat: { ...etat, phase: 'en-pause', raisonPause: ev.raison, message: ev.raison === 'onglet' ? MESSAGE_ONGLET : null },
        envoi: { type: 'pause', generation: etat.generation },
      };
    case 'recommencer':
      return nouvelEssai(etat, etat.tauxIndex, null);
    case 'changer-taux':
      verifierTauxIndex(ev.tauxIndex);
      if (ev.tauxIndex === etat.tauxIndex) return inchange(etat);
      return nouvelEssai(etat, ev.tauxIndex, MESSAGE_NOUVEAU_TAUX);
    case 'vitesse':
      if (ev.vitesse === etat.vitesse) return inchange(etat);
      return {
        etat: { ...etat, vitesse: ev.vitesse },
        envoi: etat.phase === 'en-cours' ? { type: 'vitesse', generation: etat.generation, vitesse: ev.vitesse } : null,
      };
    case 'message': {
      const suivant = recevoir(etat, ev.message);
      return { etat: suivant, envoi: null };
    }
  }
}

/**
 * Le bouton principal de la démo : son texte, et l'événement d'un clic
 * (null : le bouton est désactivé). Après un changement de taux, la démo est
 * prête : le bouton dit « Lancer l'entraînement ».
 */
export function actionPrincipale(etat: EtatDemo): { texte: string; evenement: Evenement | null } {
  switch (etat.phase) {
    case 'pret':
      return { texte: 'Lancer l’entraînement', evenement: { type: 'lancer' } };
    case 'en-cours':
      return { texte: 'Pause', evenement: { type: 'pause', raison: 'lecteur' } };
    case 'en-pause':
      return { texte: 'Reprendre', evenement: { type: 'lancer' } };
    default:
      return { texte: 'Terminé', evenement: null };
  }
}

/**
 * Un prénom inventé, prêt à afficher : une capitale au début et après chaque
 * trait d'union (« Jean-Pierre »). Un prénom vide (le modèle a tiré la fin
 * tout de suite) s'affiche « (aucune lettre) ».
 */
export function prenomAffiche(texte: string): string {
  if (texte === '') return '(aucune lettre)';
  return texte.replace(/(^|-)(\p{L})/gu, (_, avant: string, lettre: string) => avant + lettre.toUpperCase());
}
