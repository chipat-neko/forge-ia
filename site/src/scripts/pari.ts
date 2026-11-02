// La révélation d'un pari, commune aux chapitres (scripts/chapitre.ts), au
// pari d'ouverture de l'accueil et à celui de la page 404 (scripts/paris.ts).
//
// Un pari est un élément [data-pari] qui contient ses choix
// (button[data-choix], le juste porte data-juste) et un .verdict caché, dont
// le .titre-v reçoit « Juste. » ou « Pas tout à fait. ».

/** Les boutons de choix d'un pari, dans l'ordre. */
export function boutonsDuPari(pari: HTMLElement): HTMLButtonElement[] {
  return [...pari.querySelectorAll<HTMLButtonElement>('button[data-choix]')];
}

function ajouterMention(bouton: HTMLButtonElement, texte: string): void {
  const mention = document.createElement('span');
  mention.className = 'rep';
  mention.textContent = texte;
  // L'espace sépare la mention du choix dans le nom lu par les lecteurs d'écran.
  bouton.append(' ', mention);
}

/**
 * Révèle le verdict d'un pari pour le choix d'indice `choix` : boutons figés,
 * bonne réponse signalée, verdict montré. `anime` est faux quand on restaure
 * un pari déjà fait (rechargement) : rien ne bouge, le focus ne saute pas.
 * Renvoie vrai si le choix est juste. Sans effet si le pari est déjà répondu.
 */
export function revelerPari(pari: HTMLElement, choix: number, anime: boolean): boolean {
  const boutons = boutonsDuPari(pari);
  const choisi = boutons[choix];
  const juste = choisi?.hasAttribute('data-juste') ?? false;
  if (pari.hasAttribute('data-repondu') || !choisi) return juste;
  pari.setAttribute('data-repondu', '');
  for (const bouton of boutons) {
    bouton.disabled = true;
    if (bouton.hasAttribute('data-juste')) {
      bouton.classList.add('juste');
      ajouterMention(bouton, bouton === choisi ? 'ton choix, juste' : 'bonne réponse');
    } else if (bouton === choisi) {
      bouton.classList.add('faux');
      ajouterMention(bouton, 'ton choix');
    } else {
      bouton.classList.add('attenue');
    }
  }
  const verdict = pari.querySelector<HTMLElement>('.verdict');
  if (!verdict) return juste;
  verdict.classList.add(juste ? 'ok' : 'ko');
  const titre = verdict.querySelector('.titre-v');
  if (titre) titre.textContent = juste ? 'Juste.' : 'Pas tout à fait.';
  verdict.hidden = false;
  if (anime) {
    verdict.classList.add('revele');
    // Le bouton choisi vient d'être désactivé : le focus passe au verdict,
    // que les lecteurs d'écran lisent aussitôt. S'il dépasse du bas de
    // l'écran, on le fait juste entrer (en douceur, sauf si le lecteur a
    // demandé moins de mouvement).
    verdict.focus({ preventScroll: true });
    const doux = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    verdict.scrollIntoView({ block: 'nearest', behavior: doux ? 'smooth' : 'auto' });
  }
  return juste;
}
