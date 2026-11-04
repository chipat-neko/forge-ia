// Les brouillons de chapitres : src/brouillons/chapitres/<p>-<n>.mdx.
//
// Un chapitre s'écrit d'abord en brouillon, au même niveau de dossiers que
// src/content/chapitres/ : ses imports relatifs restent justes quand il paraît
// (git mv vers src/content/chapitres/, voir « Parution d'un chapitre » dans le
// README). Un brouillon n'est construit qu'avec FORGE_ESSAIS=1, à son adresse
// définitive et hors de la recherche (src/pages/[partie]/[chapitre].astro).

/** Un brouillon : le numéro de son frontmatter et le nom de son fichier. */
export interface Brouillon {
  numero: string;
  fichier: string;
}

/**
 * Vérifie les brouillons face aux chapitres parus (leurs numéros) : chaque
 * fichier porte le nom de son numéro (« 0.1 » dans 0-1.mdx), et aucun numéro
 * n'est à la fois paru et en brouillon. Lève une erreur qui dit quoi faire.
 */
export function verifierBrouillons(parus: string[], brouillons: Brouillon[]): void {
  const dejaParus = new Set(parus);
  for (const { numero, fichier } of brouillons) {
    const [p, n] = numero.split('.');
    if (fichier !== `${p}-${n}.mdx`) {
      throw new Error(`Le brouillon du chapitre ${numero} doit s'appeler ${p}-${n}.mdx (trouvé : ${fichier}).`);
    }
    if (dejaParus.has(numero)) {
      throw new Error(
        `Le chapitre ${numero} est à la fois paru (src/content/chapitres/${p}-${n}.mdx) et en brouillon ` +
          `(src/brouillons/chapitres/${p}-${n}.mdx) : supprime le brouillon.`,
      );
    }
  }
}
