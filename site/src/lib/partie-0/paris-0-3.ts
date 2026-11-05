// Les paris du chapitre 0.3, « Installer son poste ».
//
// Leurs bonnes réponses sont lues, jamais écrites à la main : le rapport des
// débits mesurés de ton IA (MESURES_TON_IA, du calculateur) pour le pari
// « vitesse », et les constats du diagnostic du projet (poste.ts, qui lit ses
// attendus) pour les paris « pypi » et « trop-recente ». Chaque choix est juste
// si et seulement si le constat qu'il décrit est dans la situation : si le
// diagnostic change, le choix juste suit, et Pari.astro arrête la construction
// s'il n'y en a plus exactement un.
//
// Ce module passe par poste.ts, qui importe un fichier .json : le parcours du
// chapitre ne l'importe pas (B1), il écrit les choix en toutes lettres.

import type { CleForge } from '../calculateur/ton-ia';
import { MESURES_TON_IA } from '../calculateur/ton-ia';
import type { Choix } from '../choix';
import { exigeur } from '../exiger';
import { nombre } from '../nombres';
import { situation } from './poste';

const exiger = exigeur('src/lib/partie-0/paris-0-3.ts et le texte des paris du chapitre 0.3');

/** La taille de ton IA du pari « vitesse » : la plus grande, celle que la carte entraîne. */
export const TAILLE_DU_PARI: CleForge = 'tres_grand';

/** Combien de fois la carte entraîne ton IA plus vite que le processeur, d'après les débits mesurés. */
export function rapportDesDebits(): number {
  const { carte, processeur } = MESURES_TON_IA[TAILLE_DU_PARI];
  return carte.jetonsParSeconde / processeur.jetonsParSeconde;
}

/** Une nuit d'entraînement, en heures, et deux semaines, en jours : les mesures de « des semaines ». */
export const HEURES_D_UNE_NUIT = 8;
export const JOURS_DE_DEUX_SEMAINES = 14;

/**
 * Combien de jours prendrait sur le processeur une nuit d'entraînement sur la
 * carte : HEURES_D_UNE_NUIT heures fois le rapport des débits. L'étape 1 du
 * chapitre dit « des semaines » : la garde tombe sous deux semaines (revue
 * finale, m5 ; à 20 fois, une nuit ne ferait que 7 jours).
 */
export function joursPourUneNuit(rapport: number = rapportDesDebits()): number {
  const jours = (HEURES_D_UNE_NUIT * rapport) / 24;
  exiger(
    jours >= JOURS_DE_DEUX_SEMAINES,
    `une nuit de ${HEURES_D_UNE_NUIT} h sur la carte ne prendrait plus que ${nombre(jours, 1)} jours sur le processeur, ` +
      `moins de ${JOURS_DE_DEUX_SEMAINES} : « des semaines » (étape 1 du chapitre 0.3) est à revoir`,
  );
  return jours;
}

/** Les clés des constats d'une situation des attendus. */
function cles(nom: string): string[] {
  return situation(nom).constats.map((c) => c.cle);
}

/**
 * Le pari « Pour entraîner ton IA, la carte va combien de fois plus vite que
 * le processeur ? » : le juste est le rapport arrondi des débits mesurés.
 */
export function choixVitesse(): Choix[] {
  const r = Math.round(rapportDesDebits());
  const leurres = [2, 10];
  exiger(r > leurres.at(-1)!, `la carte ne va plus que ${r} fois plus vite que le processeur : revois les leurres du pari`);
  return [...leurres, r].map((n) => ({ texte: `${nombre(n)} fois`, juste: n === r }));
}

/**
 * Le pari « Sous Windows, `pip install torch` : la carte calcule-t-elle ? »,
 * sur la situation windows_pypi_rtx5070ti des attendus.
 */
export function choixRouePypi(): Choix[] {
  const vus = cles('windows_pypi_rtx5070ti');
  return [
    { texte: 'Oui, la carte calcule', juste: vus.includes('carte_prete') },
    { texte: "Non : c'est la version pour processeur", juste: vus.includes('roue_processeur') },
    { texte: "PyTorch refuse de s'importer", juste: vus.includes('torch_absent') },
  ];
}

/**
 * Le pari sur une RTX 5070 Ti avec l'ancienne version de PyTorch pour CUDA
 * 12.6, sur la situation windows_cu126_rtx5070ti des attendus.
 */
export function choixCarteTropRecente(): Choix[] {
  const vus = cles('windows_cu126_rtx5070ti');
  return [
    { texte: 'Tout marche', juste: vus.includes('carte_prete') },
    { texte: 'La carte est trop récente pour cette version', juste: vus.includes('carte_trop_recente') },
    { texte: 'Le pilote est trop ancien', juste: vus.includes('pilote_trop_ancien') },
  ];
}
