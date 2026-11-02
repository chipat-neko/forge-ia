// Où en est le lecteur dans un chapitre paru, d'après sa progression gardée.
// Sert à l'accueil et aux pages de partie : un chapitre est « fait » quand
// tous ses acquis sont gagnés, « commencé » quand une partie l'est.
import { lireChapitre } from './progression';

export interface Avancement {
  /** Acquis du chapitre déjà gagnés. */
  gagnes: number;
  /** Acquis du chapitre (ceux de son frontmatter). */
  total: number;
  etat: 'disponible' | 'commence' | 'fait';
}

/**
 * Avancement d'un chapitre paru. `acquis` donne les clés de ses acquis : une
 * clé gardée qui n'en fait plus partie (contenu mis à jour) ne compte pas.
 */
export function avancement(numero: string, acquis: string[], stockage?: Storage | null): Avancement {
  const gardes = new Set(lireChapitre(numero, stockage).acquis);
  const cles = [...new Set(acquis)];
  const gagnes = cles.filter((cle) => gardes.has(cle)).length;
  const total = cles.length;
  const etat = total > 0 && gagnes === total ? 'fait' : gagnes > 0 ? 'commence' : 'disponible';
  return { gagnes, total, etat };
}
