// Le défi de l'atelier du chapitre 1.5 : trouver le plus grand taux d'apprentissage dont l'erreur
// de validation, au dernier pas, ne dépasse pas de plus de 0,05 celle du taux par défaut.
//
// Ses pertes viennent du moteur du mini-modèle (Entraineur), celui que la démo fait tourner dans
// son Worker, avec les mêmes réglages et la même graine : ce sont, au bit près, les erreurs que le
// lecteur lit dans la liste de la démo au dernier pas. La réponse se choisit sur ces pertes dans
// paris-1-5.ts (reponseDuDefi), qui garde aussi que le défi en a une.
//
// Ce module fait tourner le moteur, quelques secondes par taux : seule la page Astro l'importe, au
// moment de la construction, et le résultat est gardé. Un parcours Playwright ne peut pas
// l'importer (le moteur lit ses prénoms en ?raw) : il relit les nombres de la page.

import { Entraineur, PRESETS_MINI, TAUX_PROPOSES } from '../mini-modele/entrainement';
import { reponseDuDefi, type FinAuTaux, type ReponseDuDefi } from './paris-1-5';

/** Les taux du défi : celui du préréglage complet, et les taux proposés plus grands que lui. */
export const TAUX_DU_DEFI = Object.freeze({
  defaut: PRESETS_MINI.complet.tauxMax,
  plusGrands: Object.freeze(TAUX_PROPOSES.filter((t) => t > PRESETS_MINI.complet.tauxMax)),
});

/** L'erreur de validation après tous les pas du préréglage complet, au taux donné (Infinity s'il explose). */
function finAuTaux(taux: number): FinAuTaux {
  const e = new Entraineur({ ...PRESETS_MINI.complet, tauxMax: taux });
  while (e.pas < PRESETS_MINI.complet.pasTotal && !e.diverge) e.faireUnPas();
  const fin = e.diverge ? Infinity : e.perteValidation();
  return { taux, fin: Number.isFinite(fin) ? fin : Infinity };
}

let resultat: ReponseDuDefi | null = null;

/** La réponse du défi, calculée une fois par le moteur, puis gardée. */
export function resultatDuDefi(): ReponseDuDefi {
  if (resultat === null) {
    resultat = Object.freeze(reponseDuDefi(finAuTaux(TAUX_DU_DEFI.defaut), TAUX_DU_DEFI.plusGrands.map(finAuTaux)));
  }
  return resultat;
}
