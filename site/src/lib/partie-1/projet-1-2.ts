// Ce que le chapitre 1.2 lit du projet 1.2, à la construction : ses exemples (exemples/*.jsonl),
// son aperçu des sources et les volumes du corpus principal (MESURES_PARTIE_1).
//
// Il vit à part de paris-1-2.ts : les imports ?raw et .json passent par Vite, et un parcours
// Playwright, chargé par Node sans Vite, ne pourrait pas importer un module qui les contient
// (P8). Les parcours lisent les mêmes fichiers par readFileSync, et projet-1-2.test.ts vérifie
// que ce module lit bien les fichiers de MESURES_PARTIE_1. L'atelier n'importe pas ce module :
// il reçoit son texte du chapitre.

import code from '../../../../projets/1.2-donnees/exemples/code.jsonl?raw';
import web from '../../../../projets/1.2-donnees/exemples/web.jsonl?raw';
import apercu from '../../../../projets/1.2-donnees/mesures/apercu.json';
import corpus from '../../../../projets/1.2-donnees/mesures/corpus-principal.json';
import type { NomSource } from './donnees';
import type { Ligne } from './nettoyeur';
import { lireJsonl, type Apercu } from './paris-1-2';

/** Les documents de exemples/web.jsonl, dans l'ordre : `{ text }`. */
export const EXEMPLES_WEB: readonly Ligne[] = Object.freeze(lireJsonl(web));

/** Les fichiers de exemples/code.jsonl, dans l'ordre : `{ code, language, license }`. */
export const EXEMPLES_CODE: readonly Ligne[] = Object.freeze(lireJsonl(code));

/** L'aperçu des trois sources (mesures/apercu.json). */
export const APERCU: Apercu = apercu as Apercu;

/** Les volumes du corpus principal de ton IA, lus dans ses jetons (mesures/corpus-principal.json). */
export interface CorpusPrincipal {
  releve_le: string;
  dossier: string;
  jetons_train: number;
  jetons_val: number;
  documents_train: number;
  documents_val: number;
  octets: number;
  octets_par_jeton: number;
  fragments: number;
  fragments_par_source: Record<NomSource, number>;
}

export const CORPUS_PRINCIPAL: CorpusPrincipal = corpus as CorpusPrincipal;
