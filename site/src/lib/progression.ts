// Progression du lecteur : paris, acquis et étapes de chaque chapitre.
//
// Tout est gardé dans localStorage, sous une seule clé, sans compte ni
// statistique. Si localStorage est absent (navigation privée, accès refusé),
// plein ou corrompu, la page fonctionne comme si de rien n'était : la
// progression reste alors en mémoire, le temps de la visite, sans erreur.

export const CLE_PROGRESSION = 'forge-ia:progression:v1';

export interface EtatChapitre {
  /** Choix fait à chaque pari : identifiant du pari vers indice du choix. */
  paris: Record<string, number>;
  /** Notions que le lecteur a marquées comme comprises. */
  acquis: string[];
  /** Étapes du chapitre déjà faites (barre du haut). */
  etapes: string[];
}

// Tout le contenu du stockage : numéro de chapitre vers état du chapitre.
type Racine = Record<string, EtatChapitre>;

// Copie de secours, en mémoire. `actif` vaut vrai quand la dernière écriture
// dans le stockage a échoué : la copie est alors plus récente que lui.
interface Repli {
  racine: Racine;
  actif: boolean;
}

const repliSansStockage: Repli = { racine: {}, actif: true };
const replis = new WeakMap<Storage, Repli>();

function repliDe(stockage: Storage | null): Repli {
  if (!stockage) return repliSansStockage;
  let repli = replis.get(stockage);
  if (!repli) {
    repli = { racine: {}, actif: false };
    replis.set(stockage, repli);
  }
  return repli;
}

// Le stockage à utiliser : celui qu'on donne, sinon localStorage. Lire
// localStorage peut lui-même lever une erreur (SecurityError).
function choisirStockage(stockage?: Storage | null): Storage | null {
  if (stockage !== undefined) return stockage;
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

function etatVide(): EtatChapitre {
  return { paris: {}, acquis: [], etapes: [] };
}

function estObjet(valeur: unknown): valeur is Record<string, unknown> {
  return typeof valeur === 'object' && valeur !== null && !Array.isArray(valeur);
}

// Ne garde de l'état d'un chapitre que ce qui a la bonne forme. Les
// `Object.fromEntries` créent des propriétés propres, même pour « __proto__ ».
function assainir(brut: unknown): EtatChapitre {
  if (!estObjet(brut)) return etatVide();
  const paris = estObjet(brut.paris)
    ? Object.fromEntries(
        Object.entries(brut.paris).filter(
          (entree): entree is [string, number] =>
            typeof entree[1] === 'number' && Number.isFinite(entree[1]),
        ),
      )
    : {};
  const textes = (valeur: unknown): string[] =>
    Array.isArray(valeur) ? valeur.filter((v): v is string => typeof v === 'string') : [];
  return { paris, acquis: textes(brut.acquis), etapes: textes(brut.etapes) };
}

function lireRacine(stockage: Storage | null): Racine {
  const repli = repliDe(stockage);
  if (!stockage || repli.actif) return repli.racine;
  try {
    const brut = stockage.getItem(CLE_PROGRESSION);
    if (brut === null) return {};
    const donnees: unknown = JSON.parse(brut);
    if (!estObjet(donnees)) return {};
    return Object.fromEntries(
      Object.entries(donnees)
        .filter(([, etat]) => estObjet(etat))
        .map(([numero, etat]): [string, EtatChapitre] => [numero, assainir(etat)]),
    );
  } catch (erreur) {
    // JSON abîmé : on repart de zéro. Lecture impossible : copie en mémoire.
    return erreur instanceof SyntaxError ? {} : repli.racine;
  }
}

function ecrireRacine(stockage: Storage | null, racine: Racine): void {
  const repli = repliDe(stockage);
  repli.racine = racine;
  if (!stockage) return;
  try {
    if (Object.keys(racine).length === 0) stockage.removeItem(CLE_PROGRESSION);
    else stockage.setItem(CLE_PROGRESSION, JSON.stringify(racine));
    repli.actif = false;
  } catch {
    // Stockage plein ou refusé : la copie en mémoire fait foi jusqu'à
    // la prochaine écriture réussie.
    repli.actif = true;
  }
}

function chapitreDans(racine: Racine, numero: string): EtatChapitre {
  return Object.hasOwn(racine, numero) ? racine[numero] : etatVide();
}

function modifier(
  numero: string,
  stockage: Storage | null | undefined,
  changer: (etat: EtatChapitre) => EtatChapitre,
): void {
  const choisi = choisirStockage(stockage);
  const racine = lireRacine(choisi);
  ecrireRacine(choisi, { ...racine, [numero]: changer(chapitreDans(racine, numero)) });
}

// Copie d'un état, pour ne jamais rendre l'objet gardé en mémoire.
function copie(etat: EtatChapitre): EtatChapitre {
  return { paris: { ...etat.paris }, acquis: [...etat.acquis], etapes: [...etat.etapes] };
}

/** État d'un chapitre. Toujours un objet neuf, vide si rien n'est gardé. */
export function lireChapitre(numero: string, stockage?: Storage | null): EtatChapitre {
  return copie(chapitreDans(lireRacine(choisirStockage(stockage)), numero));
}

/** Note le choix (indice de la réponse) fait à un pari. */
export function noterPari(
  numero: string,
  idPari: string,
  choix: number,
  stockage?: Storage | null,
): void {
  modifier(numero, stockage, (etat) => ({ ...etat, paris: { ...etat.paris, [idPari]: choix } }));
}

/** Note qu'une notion est acquise. Sans effet si elle l'est déjà. */
export function noterAcquis(numero: string, cle: string, stockage?: Storage | null): void {
  modifier(numero, stockage, (etat) =>
    etat.acquis.includes(cle) ? etat : { ...etat, acquis: [...etat.acquis, cle] },
  );
}

/** Note qu'une étape du chapitre est faite. Sans effet si elle l'est déjà. */
export function noterEtape(numero: string, idEtape: string, stockage?: Storage | null): void {
  modifier(numero, stockage, (etat) =>
    etat.etapes.includes(idEtape) ? etat : { ...etat, etapes: [...etat.etapes, idEtape] },
  );
}

/** Efface un chapitre, ou toute la progression si aucun numéro n'est donné. */
export function effacer(numero?: string, stockage?: Storage | null): void {
  const choisi = choisirStockage(stockage);
  if (numero === undefined) {
    ecrireRacine(choisi, {});
    return;
  }
  const racine = { ...lireRacine(choisi) };
  delete racine[numero];
  ecrireRacine(choisi, racine);
}

/**
 * Retire les paris devenus obsolètes après une mise à jour du contenu : ceux
 * dont l'identifiant n'existe plus et ceux dont le choix n'est plus un indice
 * valide. `parisValides` donne le nombre de choix de chaque pari. Renvoie
 * l'état propre ; le pari retiré redevient jouable.
 */
export function nettoyer(
  numero: string,
  parisValides: Record<string, number>,
  stockage?: Storage | null,
): EtatChapitre {
  const choisi = choisirStockage(stockage);
  const racine = lireRacine(choisi);
  const etat = chapitreDans(racine, numero);
  const gardes = Object.entries(etat.paris).filter(([id, choix]) => {
    if (!Object.hasOwn(parisValides, id)) return false;
    return Number.isInteger(choix) && choix >= 0 && choix < parisValides[id];
  });
  if (gardes.length === Object.keys(etat.paris).length) return copie(etat);
  const propre: EtatChapitre = { ...etat, paris: Object.fromEntries(gardes) };
  ecrireRacine(choisi, { ...racine, [numero]: propre });
  return copie(propre);
}
