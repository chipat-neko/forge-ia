<script lang="ts">
  // Les trois dernières fusions apprises, de la plus récente à la plus
  // ancienne : « fusion 30 : é + c → éc ». La liste suit le canal du nombre de
  // fusions : on peut la poser dans l'atelier, ou dans la marge, à côté (îlot
  // séparé, avec client:load), comme dans la maquette.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { FUSIONS_AU_DEPART, ligneFusion } from './fusions';

  interface Props {
    /** Nom du canal du nombre de fusions ; « fusions » par défaut. */
    canalFusions?: string;
  }

  const { canalFusions = 'fusions' }: Props = $props();
  const FINE = '\u202F';

  // Le canal est choisi une fois pour toutes, comme dans NombreManipulable.
  const fusions = canal<number>(untrack(() => canalFusions), FUSIONS_AU_DEPART);
  const k = $derived($fusions);
  const dernieres = $derived(Array.from({ length: Math.min(3, k) }, (_, i) => ligneFusion(k - i)));
</script>

<div class="dernieres" data-dernieres-fusions>
  <p><strong>Dernières fusions apprises</strong></p>
  {#if dernieres.length > 0}
    <ul>
      {#each dernieres as ligne (ligne)}
        <li>{ligne}</li>
      {/each}
    </ul>
  {:else}
    <p>aucune pour l’instant{FINE}: chaque lettre reste seule.</p>
  {/if}
</div>

<style>
  /* À la manière d'une note de marge. */
  .dernieres {
    font-size: 16px;
    line-height: 1.5;
    color: var(--indigo-doux);
  }

  /* Dans une vraie note de marge, la taille est celle de la note. */
  :global(.note) .dernieres {
    font-size: inherit;
  }

  .dernieres p {
    margin: 0 0 0.3em;
  }

  .dernieres strong {
    font-family: var(--titres);
    font-weight: 600;
    color: var(--indigo);
  }

  .dernieres ul {
    list-style: none;
    margin: 0;
    padding: 0;
    font-variant-numeric: tabular-nums;
  }

  .dernieres li {
    padding: 1px 0;
  }
</style>
