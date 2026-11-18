// Les mesures et les sorties des projets 1.2, 1.4, 1.5 et 1.7 que les chapitres lisent à la
// construction : leurs fichiers, en chemins depuis la racine du dépôt.
//
// FICHIERS_PARTIE_1 (fichiers.ts) ne liste que les attendus de parité, ceux que la page
// d'essai refait dans le navigateur. Ce qui a été mesuré (l'aperçu des sources, les volumes du
// corpus, les essais de pause et de reprise) ou affiché par une commande est ici : un chapitre
// le lit tel quel, le site ne le refait pas. Les lecteurs de ces fichiers sont ceux des
// chapitres qui s'en servent.
//
// Les relevés de ton IA, eux, sont listés à côté de leurs lecteurs :
// - les journaux d'entraînement (1.5) : FICHIERS_ENTRAINEMENT, dans journal.ts ;
// - les évaluations et les QCM notés (1.6) : FICHIERS_EVALUATION et FICHIERS_QCM, dans
//   evaluation.ts ;
// - ses cartes d'attention et ses jetons suivants, relevés par le projet 1.6 et montrés par
//   1.4 et 1.1 : FICHIERS_SORTIES_TON_IA, dans evaluation.ts.
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
  /** 1.4 : ce que la commande `comparer` affiche, chaque pièce face à forge (la première ligne est « # relevé le AAAA-MM-JJ »). */
  sortieComparaison: 'projets/1.4-transformer/sorties/comparaison.txt',
  /** 1.5 : ce que la commande `essai` affiche sur le processeur (la première ligne est « # relevé le AAAA-MM-JJ »). */
  sortieEssaiProcesseur: 'projets/1.5-pre-entrainement/sorties/essai-processeur.txt',
  /** 1.5 : le résultat de l'essai de pause et de reprise sur le processeur : les deux pertes finales, leur écart, les secondes. */
  essaiProcesseur: 'projets/1.5-pre-entrainement/mesures/essai-processeur.json',
  /** 1.5 : ce que la commande `essai --appareil cuda` affiche sur la carte graphique de l'auteur (la première ligne est « # relevé le AAAA-MM-JJ »). */
  sortieEssaiCarte: 'projets/1.5-pre-entrainement/sorties/essai-rtx-5070-ti.txt',
  /** 1.5 : le même essai sur la carte graphique de l'auteur, avec en plus les secondes de l'échauffement, hors chronomètre. */
  essaiCarte: 'projets/1.5-pre-entrainement/mesures/essai-rtx-5070-ti.json',
  /** 1.7 : ce que la commande `fuite` affiche, la conversation B face à la même lue seule (la première ligne est « # relevé le AAAA-MM-JJ »). */
  sortieFuiteConversation: 'projets/1.7-conversation/sorties/fuite.txt',
  /** 1.7 : l'écart maximal des logits de B, avec et sans le masque par document. */
  fuiteConversation: 'projets/1.7-conversation/mesures/fuite.json',
  /** 1.7 : ce que la commande `essai --appareil cpu` affiche, le tout petit affinage sur le processeur (« # relevé le … » en tête). */
  sortieEssaiAffinage: 'projets/1.7-conversation/sorties/essai-processeur.txt',
  /** 1.7 : les pertes de ce petit affinage, la part des réponses qui finissent leur tour avant et après, ses réponses. */
  essaiAffinage: 'projets/1.7-conversation/mesures/essai-processeur.json',
} as const);

export type NomMesuresPartie1 = keyof typeof MESURES_PARTIE_1;
