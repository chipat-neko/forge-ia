// Ce que partagent les îlots du chapitre 1.3 qui montrent le nombre de
// fusions (l'atelier, les dernières fusions en marge, l'échelle du labo) :
// ils lisent tous le même canal, créé avec la même valeur de départ.
import { tokenizer13, visible } from '../../../lib/bpe';

/**
 * Comme dans la maquette : au départ, quelques fusions sont déjà apprises,
 * pour que la phrase arrive à moitié collée et donne envie de pousser.
 */
export const FUSIONS_AU_DEPART = 20;

/** Nombre de fusions apprises par le tokenizer du chapitre. */
export const NB_FUSIONS = tokenizer13.fusions.length;

const FINE = '\u202F';

/**
 * Une fusion telle qu'on la lit : « fusion 30 : é + c → éc » (n compte à
 * partir de 1). Le texte des jetons n'est jamais typographié.
 */
export function ligneFusion(n: number): string {
  const { a, b } = tokenizer13.fusions[n - 1];
  return `fusion ${n}${FINE}: ${visible(a)} + ${visible(b)} → ${visible(a + b)}`;
}
