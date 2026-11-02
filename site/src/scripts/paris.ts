// Les paris hors chapitre : celui de l'accueil, gardé dans la progression sous
// la clé « accueil » (il reste répondu au rechargement), et celui de la page
// 404, qui n'est pas gardé. Même révélation que dans les chapitres (pari.ts).
import { nettoyer, noterPari } from '../lib/progression';
import { boutonsDuPari, revelerPari } from './pari';

export interface OptionsParis {
  /** Clé de la progression où garder les paris. Sans clé, rien n'est gardé. */
  cle?: string;
  /** Appelé quand un pari est répondu ; `anime` est faux pendant la restauration. */
  quandRepondu?: (pari: HTMLElement, juste: boolean, anime: boolean) => void;
}

/** Fait jouer les paris [data-pari] d'une zone de la page. */
export function brancherParis(zone: HTMLElement, options: OptionsParis = {}): void {
  const { cle, quandRepondu } = options;
  const paris = [...zone.querySelectorAll<HTMLElement>('[data-pari]')];
  // Un pari gardé dont l'identifiant ou le choix n'existe plus est oublié.
  const valides = Object.fromEntries(paris.map((p) => [p.dataset.pari ?? '', boutonsDuPari(p).length]));
  const gardes = cle ? nettoyer(cle, valides).paris : {};

  for (const pari of paris) {
    const id = pari.dataset.pari ?? '';
    const repondre = (choix: number, anime: boolean): void => {
      const juste = revelerPari(pari, choix, anime);
      quandRepondu?.(pari, juste, anime);
    };
    const deja = gardes[id];
    if (deja !== undefined) {
      repondre(deja, false);
    } else {
      // Firefox peut garder l'état « désactivé » d'un bouton au rechargement.
      for (const bouton of boutonsDuPari(pari)) bouton.disabled = false;
    }
    pari.addEventListener('click', (evenement) => {
      const bouton = (evenement.target as Element).closest<HTMLButtonElement>('button[data-choix]');
      if (!bouton || bouton.disabled || pari.hasAttribute('data-repondu')) return;
      const choix = Number(bouton.dataset.choix);
      if (cle) noterPari(cle, id, choix);
      repondre(choix, true);
    });
  }
}
