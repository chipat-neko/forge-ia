// Les mesures et les sorties des projets de la Partie 1 que les chapitres lisent à la
// construction : leurs fichiers, en chemins depuis la racine du dépôt.
//
// FICHIERS_PARTIE_1 (fichiers.ts) ne liste que les attendus de parité, ceux que la page
// d'essai refait dans le navigateur. Ce qui a été mesuré (l'aperçu des sources, les volumes du
// corpus) ou affiché par une commande est ici : un chapitre le lit tel quel, le site ne le
// refait pas. Les lecteurs de ces fichiers sont ceux des chapitres qui s'en servent.
//
// Ce module n'importe rien (ni .json, ni ?raw, ni node:fs) : un parcours Playwright peut
// l'importer.

/** Les fichiers de mesures et de sorties de la Partie 1. */
export const MESURES_PARTIE_1 = Object.freeze({
  /** 1.2 : combien de documents le tri garde dans les 5 premiers Mio de chaque source, et pourquoi il écarte les autres. */
  apercu: 'projets/1.2-donnees/mesures/apercu.json',
  /** 1.2 : ce que la commande `apercu` affiche (la première ligne est « # relevé le AAAA-MM-JJ »). */
  sortieApercu: 'projets/1.2-donnees/sorties/apercu.txt',
  /** 1.2 : les volumes du corpus principal de ton IA, lus dans `.complet` et `index.json`. */
  corpusPrincipal: 'projets/1.2-donnees/mesures/corpus-principal.json',
} as const);

export type NomMesuresPartie1 = keyof typeof MESURES_PARTIE_1;
