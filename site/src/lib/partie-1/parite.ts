// La parité de la Partie 1 : refait en TypeScript les attendus des projets 1.x
// dont le jumeau tourne dans le navigateur.
//
// Chacun de ces projets écrit un fichier projets/<projet>/tests/attendus.json :
// des entrées, et ce que le Python en tire. Chaque calcul ci-dessous relit les
// entrées de son fichier et refait les sorties avec les fonctions du jumeau. La
// liste des fichiers, sous le nom de leur calcul, est FICHIERS_PARTIE_1
// (fichiers.ts).
//
// - les tests Vitest du jumeau lisent le fichier de FICHIERS_PARTIE_1 et le
//   comparent à ces calculs dans Node ;
// - la page d'essai parite-partie-1 (ControleParite.svelte, jeu="partie-1") les
//   fait dans le navigateur, et e2e/parite.spec.ts compare ce qu'elle écrit aux
//   mêmes fichiers, dans Chrome, Firefox et WebKit. C'est la seule façon de voir
//   qu'un moteur JavaScript s'écarte du Python (l'ordre des points de code, les
//   caractères hors du premier plan d'Unicode).
//
// Un calcul peut être asynchrone : ControleParite attend (await) chacun.
//
// Les clés que le site ne refait pas (CLES_NON_REFAITES, fichiers.ts : les
// perplexités de 1.1, qui passent par exp et log) ne sont pas écrites par ces
// calculs : les comparaisons les retirent du fichier avant de comparer
// (partieRefaite).
//
// Ce module importe les fichiers d'attendus (.json) et, par texte-1-1.ts, le texte
// du site (?raw), par Vite : un parcours Playwright ne peut pas l'importer. Les parcours lisent
// ces fichiers par readFileSync, d'après FICHIERS_PARTIE_1.

import fichierNgrammes from '../../../../projets/1.1-modele-de-langage/tests/attendus.json';
import type { Attendus } from '../mini-modele/parite';
import {
  alphabet,
  compter,
  compterParOrdre,
  couper,
  distribution,
  generer,
  ORDRE_MAX,
  partJamaisVue,
  tirage,
  type Comptes,
} from './ngrammes';
import { TEXTE_DU_SITE } from './texte-1-1';

export { FICHIERS_PARTIE_1 } from './fichiers';

/** Un cas limite, tel que le fichier l'écrit : seules ses quatre premières clés sont des entrées. */
interface EntreesCasLimite {
  nom: string;
  texte: string;
  n: number;
  contexte: string;
}

/** Les entrées du fichier d'attendus des n-grammes : tout ce que la page relit, et rien de ce qu'elle refait. */
export interface EntreesNgrammes {
  ordres: { n: number; distributions: { contexte: string }[] }[];
  suites: { n: number; temperature: number; graine: number; depart: string; longueur: number }[];
  tirages: { n: number; temperature: number; contexte: string }[];
  cas_limites: EntreesCasLimite[];
}

/** Le message de l'erreur que lève l'appel, ou null s'il n'en lève pas (la comparaison le verra). */
function messageDe(appel: () => unknown): string | null {
  try {
    appel();
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : String(e);
  }
}

/** Les comptes d'un cas limite, en paires [contexte, [[caractère, compte]…]], comme le fichier. */
function comptesEnPaires(comptes: Comptes): [string, [string, number][]][] {
  return [...comptes].map(([contexte, suivants]) => [contexte, [...suivants]]);
}

/**
 * Les sections alphabet, ordres (sans les perplexités), suites, tirages et
 * cas_limites du fichier des n-grammes, refaites à partir de ses seules
 * entrées et du texte du site.
 */
export function refaireNgrammes(texte: string, entrees: EntreesNgrammes): Attendus {
  const [entrainement, validation] = couper(texte);
  const lettres = alphabet(texte);
  const comptesParOrdre = new Map<number, Comptes>();
  const comptesDeLOrdre = (n: number): Comptes => {
    let comptes = comptesParOrdre.get(n);
    if (comptes === undefined) {
      comptes = compter(entrainement, n);
      comptesParOrdre.set(n, comptes);
    }
    return comptes;
  };
  // Les comptes de tous les ordres, pour les tirages : calculés une fois, au premier tirage.
  let tousLesOrdres: Comptes[] | null = null;
  return {
    alphabet: lettres,
    ordres: entrees.ordres.map(({ n, distributions }) => {
      const comptes = comptesDeLOrdre(n);
      return {
        n,
        jamais_vus: partJamaisVue(comptes, validation, n),
        distributions: distributions.map(({ contexte }) => ({
          contexte,
          rangs: distribution(comptes, lettres, contexte, n).slice(0, 10),
        })),
      };
    }),
    suites: entrees.suites.map(({ n, temperature, graine, depart, longueur }) => ({
      n,
      temperature,
      graine,
      depart,
      longueur,
      suite: generer(compterParOrdre(entrainement, n), lettres, n, depart, longueur, temperature, graine),
    })),
    tirages: entrees.tirages.map(({ n, temperature, contexte }) => {
      tousLesOrdres ??= compterParOrdre(entrainement, ORDRE_MAX);
      const [ordre, chances] = tirage(tousLesOrdres, lettres, contexte, n, temperature);
      return { n, temperature, contexte, ordre, nombre: chances.length, rangs: chances.slice(0, 10) };
    }),
    cas_limites: entrees.cas_limites.map(({ nom, texte: texteDuCas, n, contexte }) => {
      const [apprendre, verifier] = couper(texteDuCas);
      const lettresDuCas = alphabet(texteDuCas);
      const comptes = compter(texteDuCas, n);
      let rangs: [string, number][] | null = null;
      let suite: string | null = null;
      const erreur = messageDe(() => {
        rangs = distribution(comptes, lettresDuCas, contexte, n);
      });
      const erreurSuite = messageDe(() => {
        suite = generer(compterParOrdre(texteDuCas, n), lettresDuCas, n, contexte, 8, 1, 0);
      });
      let leTirage: [number, [string, number][]] | null = null;
      const erreurTirage = messageDe(() => {
        leTirage = tirage(compterParOrdre(texteDuCas, n), lettresDuCas, contexte, n, 1);
      });
      return {
        nom,
        texte: texteDuCas,
        n,
        contexte,
        alphabet: lettresDuCas,
        coupe: [apprendre, verifier],
        comptes: comptesEnPaires(comptes),
        distribution: rangs,
        erreur,
        suite,
        erreur_suite: erreurSuite,
        tirage: leTirage,
        erreur_tirage: erreurTirage,
      };
    }),
  };
}

/** Les attendus des n-grammes (FICHIERS_PARTIE_1.ngrammes), sans les perplexités, refaits ici. */
export function attendusNgrammes(): Attendus {
  return refaireNgrammes(TEXTE_DU_SITE, fichierNgrammes as unknown as EntreesNgrammes);
}

/** Chaque calcul de parité de la Partie 1, sous le nom de son fichier dans FICHIERS_PARTIE_1. */
export const CALCULS_PARTIE_1: Record<string, () => unknown | Promise<unknown>> = {
  ngrammes: attendusNgrammes,
};
