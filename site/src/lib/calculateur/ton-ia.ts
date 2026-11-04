// Ton IA dans le calculateur : le jumeau de trois fonctions de forge, et les
// débits mesurés sur ce PC, comme repère de réalité.
//
// Le calculateur refait trois choses de forge, recopiées ici à l'identique :
//  - largeur_cachee et nombre_parametres (projets/forge/forge/modele/config.py),
//    en calcul entier ;
//  - estimer (projets/forge/forge/mesure.py), une division.
// ton-ia.test.ts lit le code source de forge (sans l'importer, donc sans
// PyTorch) et vérifie les nombres que forge a écrits lui-même. On ne modifie
// jamais projets/forge.
//
// Ce module est en TypeScript pur, sans import propre à Vite : les parcours
// Playwright l'importent directement.

import { DEPOT } from '../depot';
import { materiel, type Source } from './donnees';
import { efficaciteMesuree, efficaciteMesureeAvecAttention, type Forme } from './formules';

const FINE = '\u202F';

/** Les largeurs cachées du MLP sont des multiples de 64 (PAS_LARGEUR_CACHEE de forge). */
export const PAS_LARGEUR_CACHEE = 64;
/** La cible de forge : 20 jetons vus par paramètre (JETONS_PAR_PARAMETRE de forge/mesure.py). */
export const JETONS_PAR_PARAMETRE = 20;
/** Le vocabulaire du tokenizer de ton IA (taille_vocabulaire par défaut de ConfigModele). */
export const VOCABULAIRE_FORGE = 32_768;

/** Les cinq tailles de forge, dans l'ordre de PRESETS. */
export const CLES_FORGE = ['mini', 'petit', 'moyen', 'grand', 'tres_grand'] as const;
export type CleForge = (typeof CLES_FORGE)[number];

/** Le nom de chaque taille, tel que la page l'écrit. */
export const NOMS_TAILLES: Readonly<Record<CleForge, string>> = Object.freeze({
  mini: 'mini',
  petit: 'petit',
  moyen: 'moyen',
  grand: 'grand',
  tres_grand: 'très grand',
});

/** La configuration d'un modèle de forge (ConfigModele, sans base_rope). */
export interface ConfigForge {
  tailleVocabulaire: number;
  dim: number;
  couches: number;
  tetes: number;
  longueurContexte: number;
}

function entier(x: number, nom: string, fonction: string): void {
  if (!(Number.isSafeInteger(x) && x >= 1)) {
    throw new RangeError(`${fonction} : \`${nom}\` vaut ${String(x)}${FINE}: il doit être un entier d’au moins 1, comme dans forge.`);
  }
}

/**
 * La largeur cachée du MLP SwiGLU : le multiple de 64 le plus proche de
 * 8/3 × dim, le plus grand à égalité, jamais moins de 64. Calcul entier comme
 * forge : (dim + 12) // 24, au moins 1, fois 64.
 */
export function largeurCachee(dim: number): number {
  entier(dim, 'dim', 'largeurCachee');
  const multiples = Math.floor((dim + 12) / 24);
  return Math.max(1, multiples) * PAS_LARGEUR_CACHEE;
}

/**
 * Le nombre exact de paramètres d'un modèle de forge (nombre_parametres) :
 * plongement (partagé avec la sortie) vocabulaire × dim ; par couche,
 * attention 4·dim², MLP 3·dim·largeur cachée et deux RMSNorm de dim poids ;
 * une RMSNorm finale de dim poids. Ni biais, ni paramètres pour RoPE.
 *
 * Refuse une forme que ConfigModele refuserait.
 */
export function nombreParametres(c: ConfigForge): number {
  const f = 'nombreParametres';
  entier(c.tailleVocabulaire, 'taille_vocabulaire', f);
  entier(c.dim, 'dim', f);
  entier(c.couches, 'couches', f);
  entier(c.tetes, 'tetes', f);
  entier(c.longueurContexte, 'longueur_contexte', f);
  if (c.dim % c.tetes !== 0) {
    throw new RangeError(`${f} : \`dim\` (${c.dim}) doit être divisible par \`tetes\` (${c.tetes}), comme dans forge.`);
  }
  if ((c.dim / c.tetes) % 2 !== 0) {
    throw new RangeError(`${f} : chaque tête a ${c.dim / c.tetes} dimensions, il en faut un nombre pair (RoPE tourne les valeurs par paire).`);
  }
  const h = largeurCachee(c.dim);
  const plongement = c.tailleVocabulaire * c.dim;
  const attention = 4 * c.dim * c.dim;
  const mlp = 3 * c.dim * h;
  const normes = 2 * c.dim;
  const total = plongement + c.couches * (attention + mlp + normes) + c.dim;
  if (!Number.isSafeInteger(total)) {
    throw new RangeError(`${f} : ${total} paramètres, trop pour un calcul entier exact en JavaScript. Choisis une forme plus petite.`);
  }
  return total;
}

function preset(dim: number, couches: number, tetes: number, contexte: number): Forme {
  const parametres = nombreParametres({ tailleVocabulaire: VOCABULAIRE_FORGE, dim, couches, tetes, longueurContexte: contexte });
  return Object.freeze({ parametres, couches, dim, tetes, tetesKv: tetes, contexte, vocabulaire: VOCABULAIRE_FORGE });
}

/** Les cinq tailles de forge (PRESETS de forge/modele/config.py), dans le même ordre. */
export const PRESETS_FORGE: Readonly<Record<CleForge, Forme>> = Object.freeze({
  mini: preset(384, 6, 6, 512),
  petit: preset(512, 8, 8, 2048),
  moyen: preset(768, 12, 12, 2048),
  grand: preset(1024, 16, 16, 2048),
  tres_grand: preset(1280, 20, 20, 2048),
});

/**
 * La durée en heures pour lire `jetons` jetons à `jetonsParSeconde` :
 * jetons ÷ débit ÷ 3 600, comme forge.mesure.estimer. Un débit qui n'est pas
 * plus grand que 0 est une erreur.
 */
export function dureeHeures(jetons: number, jetonsParSeconde: number): number {
  if (!(jetonsParSeconde > 0)) {
    throw new RangeError(
      `dureeHeures : le débit vaut ${String(jetonsParSeconde)} jetons par seconde${FINE}: il faut un débit plus grand que 0. ` +
        'Un débit nul veut dire que la mesure n’a pas tourné.',
    );
  }
  return jetons / jetonsParSeconde / 3600;
}

// --- Les mesures ------------------------------------------------------------

/** Les débits mesurés d'une taille de ton IA, sur la carte et sur le processeur. */
export interface MesureTonIA {
  /** Sur la RTX 5070 Ti, au micro-lot le plus rapide, avec le pic de mémoire des tenseurs (Go de 1 024³ octets). */
  carte: { jetonsParSeconde: number; microLot: number; memoireGo: number };
  /** Sur le Ryzen 7 9800X3D, ses 16 fils. */
  processeur: { jetonsParSeconde: number };
  source: Source;
}

/** La carte des mesures (celle de ce PC). */
export const MATERIEL_DES_MESURES = 'rtx-5070-ti';

const MESURE = '2026-11-03';
const RAPPORT = Object.freeze({
  titre: 'Forge IA, mesure de la vitesse d’entraînement de ton IA, carte graphique contre processeur (3 novembre 2026)',
  url: `${DEPOT}/blob/main/docs/mesures/entrainement-2026-11.md`,
  releveLe: MESURE,
  statut: 'primaire' as const,
});
const MINI_TOML = Object.freeze({
  titre: 'Forge IA, configuration de la version courte de ton IA (mesure du 3 novembre 2026)',
  url: `${DEPOT}/blob/main/projets/forge/configs/mini.toml`,
  releveLe: MESURE,
  statut: 'primaire' as const,
});

/**
 * Les débits de ton IA mesurés le 3 novembre 2026 : sur la carte (20 pas de
 * 8 micro-lots accumulés, en bf16) et sur le processeur (16 fils, micro-lot 2).
 * « mini » vient de configs/mini.toml, les autres du rapport de mesure.
 */
export const MESURES_TON_IA: Readonly<Record<CleForge, MesureTonIA>> = Object.freeze({
  mini: { carte: { jetonsParSeconde: 231_934, microLot: 16, memoireGo: 4.4 }, processeur: { jetonsParSeconde: 2707 }, source: MINI_TOML },
  petit: { carte: { jetonsParSeconde: 138_433, microLot: 4, memoireGo: 5.5 }, processeur: { jetonsParSeconde: 1749 }, source: RAPPORT },
  moyen: { carte: { jetonsParSeconde: 62_368, microLot: 2, memoireGo: 5.4 }, processeur: { jetonsParSeconde: 776 }, source: RAPPORT },
  grand: { carte: { jetonsParSeconde: 32_704, microLot: 2, memoireGo: 9.1 }, processeur: { jetonsParSeconde: 404 }, source: RAPPORT },
  tres_grand: {
    carte: { jetonsParSeconde: 17_855, microLot: 1, memoireGo: 10.9 },
    processeur: { jetonsParSeconde: 235 },
    source: RAPPORT,
  },
});

/** Une ligne du tableau « Repère mesuré : ton IA sur ce PC ». */
export interface RepereTonIA {
  cle: CleForge;
  nom: string;
  parametres: number;
  /** Les jetons de l'entraînement : 20 par paramètre. */
  jetons: number;
  carte: {
    jetonsParSeconde: number;
    microLot: number;
    memoireGo: number;
    heures: number;
    /** L'efficacité implicite, avec 6N opérations par jeton. */
    efficacite: number;
    /** La même en comptant l'attention (6N + 12·L·h·s). */
    efficaciteAvecAttention: number;
  };
  processeur: { jetonsParSeconde: number; heures: number };
}

/** Les cinq lignes du repère : débits mesurés, durée pour 20 jetons par paramètre, efficacités implicites. */
export function reperesTonIA(): RepereTonIA[] {
  const crete = materiel(MATERIEL_DES_MESURES).creteTflops;
  return CLES_FORGE.map((cle) => {
    const f = PRESETS_FORGE[cle];
    const m = MESURES_TON_IA[cle];
    const jetons = JETONS_PAR_PARAMETRE * f.parametres;
    return {
      cle,
      nom: NOMS_TAILLES[cle],
      parametres: f.parametres,
      jetons,
      carte: {
        ...m.carte,
        heures: dureeHeures(jetons, m.carte.jetonsParSeconde),
        efficacite: efficaciteMesuree(f.parametres, m.carte.jetonsParSeconde, crete),
        efficaciteAvecAttention: efficaciteMesureeAvecAttention(f, m.carte.jetonsParSeconde, crete),
      },
      processeur: { jetonsParSeconde: m.processeur.jetonsParSeconde, heures: dureeHeures(jetons, m.processeur.jetonsParSeconde) },
    };
  });
}
