// L'avantage d'une réponse dans son groupe, et la chance qu'un groupe n'apprenne rien, chapitre 1.9 : le jumeau
// TypeScript de `avantages_a_la_main` et de `sans_signal`
// (projets/1.9-raisonnement/raisonnement_pas_a_pas/avantages.py).
//
// Le GRPO fait écrire plusieurs réponses à chaque problème (un groupe). Chaque réponse reçoit une récompense, 1 si elle
// est juste et 0 sinon ; son avantage est sa récompense moins la moyenne de son groupe. Un groupe aux avantages nuls
// n'apprend rien. `sansSignal(p, n)` est la chance qu'un groupe de n réponses soit sans signal quand chacune est juste
// avec la chance p : pⁿ + (1 − p)ⁿ.
//
// Exacts, pas seulement proches : la moyenne est une somme faite par une boucle de gauche à droite, divisée par le
// nombre de réponses, et les deux puissances sont deux produits en boucle, comme en Python. Les deux langages font les
// mêmes opérations IEEE 754 dans le même ordre, donc les mêmes flottants (les attendus se comparent sans tolérance).
//
// Ce module n'importe rien.

/** Pour chaque groupe, la récompense de chaque réponse moins la moyenne du groupe (sans division par l'écart-type). */
export function avantages(recompenses: readonly (readonly number[])[]): number[][] {
  return recompenses.map((groupe) => {
    if (groupe.length === 0) {
      throw new Error('Un groupe sans aucune réponse n’a pas de moyenne : donne au moins une récompense par groupe.');
    }
    let somme = 0.0;
    for (const r of groupe) somme += r;
    const moyenne = somme / groupe.length;
    return groupe.map((r) => r - moyenne);
  });
}

/** La chance qu'un groupe de n réponses soit sans signal : pⁿ + (1 − p)ⁿ, deux produits en boucle. */
export function sansSignal(p: number, n: number): number {
  if (!(p >= 0 && p <= 1)) throw new Error(`p vaut ${p} : c’est une chance, elle est entre 0 et 1.`);
  if (!Number.isInteger(n) || n < 1) throw new Error(`n vaut ${n} : un groupe a au moins une réponse (un nombre entier).`);
  const q = 1 - p;
  let toutesJustes = 1.0;
  let toutesFausses = 1.0;
  for (let i = 0; i < n; i++) {
    toutesJustes *= p;
    toutesFausses *= q;
  }
  return toutesJustes + toutesFausses;
}
