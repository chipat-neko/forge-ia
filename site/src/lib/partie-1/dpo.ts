// La perte DPO d'une paire, chapitre 1.8 : le jumeau TypeScript de `perte_dpo_a_la_main`
// (projets/1.8-alignement/alignement_pas_a_pas/perte_dpo.py).
//
// Pour une paire (réponse choisie, réponse rejetée), le gain d'une réponse est l'écart entre sa log-probabilité
// selon la politique (le modèle qu'on entraîne) et selon la référence (la version de départ). La perte pousse le
// gain de la choisie au-dessus de celui de la rejetée :
//
//   z = β ((pc − qc) − (pr − qr))        perte = −ln σ(z) = ln(1 + e^(−z))
//
// Les fonctions prennent les deux écarts (pc − qc et pr − qr) : c'est ce qu'un atelier fait varier.
//
// Hors de la page de parité : Math.exp et Math.log1p ne sont pas exacts d'un moteur à l'autre (le dernier chiffre
// change), donc les attendus (la section grille_dpo de projets/1.8-alignement/tests/attendus.json) se comparent à
// 10⁻¹² près (dpo.test.ts), pas à l'identique. Les mêmes opérations dans le même ordre que le Python.
//
// Ce module n'importe rien.

/** σ(x) = 1 / (1 + e^(−x)), sans dépassement : e^(−x) n'est calculé que pour un exposant négatif ou nul. */
export function sigmoide(x: number): number {
  if (x >= 0) return 1 / (1 + Math.exp(-x));
  const e = Math.exp(x);
  return e / (1 + e);
}

/** −ln σ(z) = ln(1 + e^(−z)), écrit pour rester exact quand z est très grand ou très négatif. */
export function moinsLogSigmoide(z: number): number {
  return Math.max(-z, 0) + Math.log1p(Math.exp(-Math.abs(z)));
}

/**
 * La perte DPO d'une paire, sans le terme SFT : −ln σ(β ((pc − qc) − (pr − qr))).
 * `ecartChoisie` vaut pc − qc, `ecartRejetee` vaut pr − qr.
 */
export function perteDpo(beta: number, ecartChoisie: number, ecartRejetee: number): number {
  const z = beta * (ecartChoisie - ecartRejetee);
  return moinsLogSigmoide(z);
}

/**
 * La dérivée de la perte selon l'écart de la choisie : −β σ(−z). Elle est négative : monter la choisie fait baisser
 * la perte. Selon l'écart de la rejetée, c'est l'opposée.
 */
export function deriveeDpo(beta: number, ecartChoisie: number, ecartRejetee: number): number {
  const z = beta * (ecartChoisie - ecartRejetee);
  return -beta * sigmoide(-z);
}
