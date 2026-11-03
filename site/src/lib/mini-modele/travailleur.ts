// Le Web Worker du mini-modèle : il entraîne le modèle hors de la page.
//
// La page le crée au premier « Lancer » (import de travailleur.ts?worker). Il
// relie self.onmessage à la boucle (boucle-travailleur.ts), et enchaîne les
// tranches de pas par setTimeout(…, 0) : une seule tranche planifiée à la
// fois, et le Worker lit ses messages entre deux tranches (une pause est donc
// prise en compte dès la fin de la tranche en cours). Les messages sont
// copiés, jamais transférés, et rien n'est partagé (pas de SharedArrayBuffer).

import { BoucleTravailleur, type MessageDuTravailleur, type MessageVersTravailleur } from './boucle-travailleur';

/** Ce dont on se sert de la portée d'un Worker dédié (DedicatedWorkerGlobalScope). */
interface PorteeTravailleur {
  onmessage: ((evenement: MessageEvent<MessageVersTravailleur>) => void) | null;
  postMessage(message: MessageDuTravailleur): void;
}

const portee = self as unknown as PorteeTravailleur;
const boucle = new BoucleTravailleur(
  (message) => portee.postMessage(message),
  () => performance.now(),
);

let planifiee = false;

/** Planifie une tranche, sauf s'il y en a déjà une. */
function planifier(): void {
  if (planifiee) return;
  planifiee = true;
  setTimeout(() => {
    planifiee = false;
    if (boucle.tranche()) planifier();
  }, 0);
}

portee.onmessage = (evenement) => {
  boucle.recevoir(evenement.data);
  planifier();
};
