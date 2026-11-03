// Un choix de pari : la forme des choix de Pari.astro (son interface Choix,
// recopiée ici pour ne pas toucher au composant du plan 1).
//
// Les fonctions de choix des démos la renvoient : paris de l'attention
// (mini-modele/paris-attention.ts), du mini-modèle (mini-modele/paris.ts) et
// du calculateur (calculateur/paris.ts). Leur bonne réponse est calculée par
// le moteur de la démo, et Pari.astro exige exactement un choix juste.

/** Un choix de pari : son texte, et `juste: true` sur la bonne réponse. */
export interface Choix {
  texte: string;
  juste?: boolean;
}
