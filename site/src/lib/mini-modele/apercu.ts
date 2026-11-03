// L'aperçu de la démo du mini-modèle : son état au pas 0, avant tout entraînement.
//
// Astro le calcule une fois par préréglage, au moment de construire la page,
// et le passe à l'îlot (MiniModele.svelte) : l'objet est donc sérialisable
// (des nombres, des textes, des tableaux). Sans JavaScript, la page montre
// déjà ces valeurs et ces prénoms ; avec, la courbe part de là.
//
// Ce module fait tourner le moteur (Entraineur, et la liste des prénoms) : la
// page n'en importe que des types (import type), jamais des valeurs.

import type { Prenom } from './boucle-travailleur';
import { log } from './calcul';
import { Entraineur, PRESETS_MINI, type NomPreset } from './entrainement';
import { nombreParametres } from './modele';

/** L'état du mini-modèle au pas 0, pour un préréglage. */
export interface EtatInitialMini {
  preset: NomPreset;
  /** Le nombre de pas de l'entraînement. */
  pasTotal: number;
  /** V : la taille du vocabulaire (les caractères, plus le bord). */
  tailleVocabulaire: number;
  nbParametres: number;
  /** Le nombre de prénoms d'entraînement. */
  nbEntrainement: number;
  /** L'erreur du pur hasard : ln V. */
  perteHasard: number;
  /** L'erreur de validation au pas 0. */
  perteValidation: number;
  /** Les prénoms inventés au pas 0. */
  echantillons: Prenom[];
}

const calcules = new Map<NomPreset, Readonly<EtatInitialMini>>();

/**
 * L'état au pas 0 du préréglage donné, calculé une fois et figé.
 *
 * Le taux d'apprentissage ne change rien au pas 0 (ni aux poids de départ, ni
 * aux prénoms tirés) : l'aperçu ne dépend que du préréglage.
 */
export function etatInitial(preset: NomPreset): Readonly<EtatInitialMini> {
  if (!Object.hasOwn(PRESETS_MINI, preset)) {
    throw new RangeError(`Préréglage inconnu : « ${String(preset)} ». Choisis « complet » ou « avant-gout ».`);
  }
  let etat = calcules.get(preset);
  if (etat === undefined) {
    const e = new Entraineur(PRESETS_MINI[preset]);
    const v = e.config.tailleVocabulaire;
    etat = Object.freeze({
      preset,
      pasTotal: e.reglages.pasTotal,
      tailleVocabulaire: v,
      nbParametres: nombreParametres(e.config),
      nbEntrainement: e.donnees.entrainement.length,
      perteHasard: log(v),
      perteValidation: e.perteValidation(),
      echantillons: Object.freeze(
        e.echantillons().map((texte) => Object.freeze({ texte, existe: e.donnees.connus.has(texte) })),
      ) as Prenom[],
    });
    calcules.set(preset, etat);
  }
  return etat;
}
