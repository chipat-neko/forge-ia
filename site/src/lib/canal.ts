// Canaux : de petits magasins de valeurs partagés par nom, pour que des îlots
// Svelte séparés (la page n'a pas un seul arbre de composants) se parlent.
// Le contrat est celui des magasins Svelte : `subscribe` appelle la fonction
// tout de suite avec la valeur courante et renvoie la fonction qui désabonne,
// donc `$canal` fonctionne dans un composant.

export interface Canal<T> {
  get(): T;
  set(v: T): void;
  subscribe(fn: (v: T) => void): () => void;
}

// Les canaux déjà créés, par nom. Le type de la valeur n'est pas vérifié
// d'un appel à l'autre : c'est à celui qui nomme un canal d'être cohérent.
const canaux = new Map<string, Canal<unknown>>();

// Comme les magasins Svelte : une valeur simple identique ne prévient
// personne, mais un objet ou une fonction oui, car ils ont pu être modifiés.
function aChange(avant: unknown, apres: unknown): boolean {
  if (Object.is(avant, apres)) {
    return (typeof avant === 'object' && avant !== null) || typeof avant === 'function';
  }
  return true;
}

function creer<T>(initiale: T): Canal<T> {
  let valeur = initiale;
  // Un objet par abonnement : la même fonction peut s'abonner deux fois.
  const abonnes = new Set<{ fn: (v: T) => void }>();
  return {
    get: () => valeur,
    set(v) {
      if (!aChange(valeur, v)) return;
      valeur = v;
      // Copie : un abonné peut se désabonner pendant l'envoi.
      for (const abonne of [...abonnes]) {
        if (abonnes.has(abonne)) abonne.fn(valeur);
      }
    },
    subscribe(fn) {
      const abonne = { fn };
      abonnes.add(abonne);
      fn(valeur);
      return () => {
        abonnes.delete(abonne);
      };
    },
  };
}

/** Le canal de ce nom : toujours la même instance, la première valeur initiale gagne. */
export function canal<T>(nom: string, initiale: T): Canal<T> {
  let existant = canaux.get(nom);
  if (!existant) {
    existant = creer<unknown>(initiale);
    canaux.set(nom, existant);
  }
  return existant as Canal<T>;
}

/** Canal vrai/faux « ouvert » d'un panneau ou d'une démo, fermé au départ. */
export function ouverture(nom: string): Canal<boolean> {
  return canal('ouvert:' + nom, false);
}
