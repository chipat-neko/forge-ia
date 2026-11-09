// Les angles de RoPE du chapitre 1.4, pour l'AFFICHAGE seulement (la figure des aiguilles de
// l'horloge). Le modèle de forge, lui, calcule ces angles en float32 (rope_cos_sin) : voir
// transformer_pas_a_pas/pieces.py. Ici, comme dans les attendus
// (projets/1.4-transformer/tests/attendus.json, section rope), ils sont en float64.
//
// Math.pow n'est pas exacte entre moteurs, ni entre le moteur et la bibliothèque de Python :
// le test compare donc aux attendus à 10⁻¹² près, pas au bit près.

const FINE = '\u202F';

/**
 * L'angle de chaque paire d'une tête à une position : la paire `i` (ses valeurs `2i` et
 * `2i + 1`) tourne de `position × base^(-2i / dimTete)`. Rend `dimTete / 2` angles, en radians.
 * Les premières paires tournent vite, les dernières lentement.
 */
export function anglesRope(position: number, dimTete: number, base: number): number[] {
  if (!(Number.isSafeInteger(dimTete) && dimTete >= 2 && dimTete % 2 === 0)) {
    throw new RangeError(`anglesRope${FINE}: \`dimTete\` vaut ${String(dimTete)}${FINE}: il doit être un entier pair d’au moins 2 (RoPE tourne les valeurs par paires).`);
  }
  if (!(Number.isSafeInteger(position) && position >= 0)) {
    throw new RangeError(`anglesRope${FINE}: \`position\` vaut ${String(position)}${FINE}: il doit être un entier d’au moins 0.`);
  }
  if (!(base > 1)) {
    throw new RangeError(`anglesRope${FINE}: \`base\` doit être plus grand que 1 (vaut ${String(base)}), comme dans forge.`);
  }
  const angles: number[] = [];
  for (let i = 0; i < dimTete / 2; i++) {
    angles.push(position * Math.pow(base, -(2 * i) / dimTete));
  }
  return angles;
}
