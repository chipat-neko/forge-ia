<script lang="ts">
  // Une zone qui défile en largeur, pour un tableau plus large que la
  // colonne : la page, elle, ne déborde jamais. La zone porte un nom
  // (role="region", aria-label) et prend le focus, pour se parcourir au
  // clavier.
  //
  // Avec `indice`, une phrase au-dessus invite à la faire défiler : à l'œil,
  // car « défilable » n'est que dans le nom de la zone. Elle ne s'affiche que
  // sous la largeur de fenêtre `seuil`, celle où le tableau ne tient plus dans
  // la colonne. Les règles sont dans src/styles/commandes.css.
  //
  // Une marge propre à un usage passe par `classe`, réglée dans le parent
  // avec :global (une règle locale du parent n'atteint pas ce div).
  import type { Snippet } from 'svelte';

  interface Props {
    /** Le nom de la zone, lu par les lecteurs d'écran : « Débits mesurés, défilable ». */
    etiquette: string;
    /** La phrase qui invite à faire défiler, au-dessus de la zone ; aucune par défaut. */
    indice?: string;
    /** La largeur de fenêtre, en pixels, sous laquelle l'indice s'affiche ; 480 par défaut. */
    seuil?: 480 | 600;
    /** Valeur de data-test de la zone, pour les parcours de test. */
    testId?: string;
    /** Valeur de data-test de l'indice. */
    testIndice?: string;
    /** Une classe de plus pour la zone. */
    classe?: string;
    children: Snippet;
  }

  const { etiquette, indice, seuil = 480, testId, testIndice, classe, children }: Props = $props();
</script>

{#if indice}
  <p class="indice-defilement" data-seuil={seuil} data-test={testIndice}>{indice}</p>
{/if}
<!-- svelte-ignore a11y_no_noninteractive_tabindex (une zone qui défile doit prendre le focus pour se parcourir au clavier : WCAG 2.1.1) -->
<div class={['zone-defilable', classe]} role="region" aria-label={etiquette} tabindex="0" data-test={testId}>
  {@render children()}
</div>
