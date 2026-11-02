// Aides des pages qui montrent l'état des chapitres (accueil, pages de
// partie) : l'avancement d'un chapitre paru et ses pastilles « Ce que tu sais ».
import { avancement, type Avancement } from '../lib/avancement';

/**
 * L'avancement d'un chapitre paru, lu sur son élément : le numéro dans
 * data-chapitre-carte, les clés de ses acquis dans data-acquis. Null pour
 * un chapitre à venir (sans data-acquis).
 */
export function avancementDe(element: HTMLElement): Avancement | null {
  const numero = element.dataset.chapitreCarte;
  const acquis = element.dataset.acquis;
  if (!numero || acquis === undefined) return null;
  return avancement(numero, acquis.split(' ').filter(Boolean));
}

/** Les pastilles « Ce que tu sais » : `pleines` sur `total`. Décoratives. */
export function pastilles(pleines: number, total: number): HTMLElement {
  const conteneur = document.createElement('span');
  conteneur.className = 'pips';
  conteneur.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < total; i++) {
    const pastille = document.createElement('i');
    if (i < pleines) pastille.className = 'plein';
    conteneur.append(pastille);
  }
  return conteneur;
}
