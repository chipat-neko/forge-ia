<script lang="ts">
  // La figure de l'empaquetage du chapitre 1.7 : des conversations de toutes longueurs, rangées par BFD
  // (« best-fit decreasing », celui de forge) dans des rangées de L jetons. Le lecteur règle L (512, 1 024,
  // 2 048 ou 4 096, le nombre jaune) ; la phrase dit quelle part des places BFD remplit et combien d'exemples
  // trop longs il écarte, et le dessin montre les premières rangées : un morceau par exemple, du blanc pour
  // le bourrage.
  //
  // Les quatre empaquetages sont calculés à la construction par le jumeau de BFD (empaqueterLongueurs, bfd.ts),
  // par paris-1-7.ts, sur les longueurs du jeu d'affinage de ton IA quand elles sont relevées
  // (mesures/longueurs-sft-1.7.json), sinon sur la liste de référence des attendus du projet : la figure le dit.
  // Avec les 135 471 exemples du vrai jeu, un empaquetage prendrait trop de temps sur un téléphone à chaque geste.
  //
  // À placer dans le MDX avec client:load :
  //   <FigureEmpaquetage client:load resultats={…} source="reference" exemples={300} plusLong={1600} />
  // Sans JavaScript, la figure se lit telle qu'elle est à l'arrivée : des rangées de 2 048 jetons.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { nombre } from '../../../lib/nombres';
  import {
    LONGUEUR_DE_TON_IA,
    LONGUEURS_DE_RANGEE,
    phraseDeLEmpaquetage,
    type EmpaquetageDeLaFigure,
  } from '../../../lib/partie-1/atelier-1-7';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Les quatre empaquetages, un par longueur de LONGUEURS_DE_RANGEE, calculés à la construction. */
    resultats: EmpaquetageDeLaFigure[];
    /** Ce qui est rangé : le jeu d'affinage de ton IA, ou la liste de référence des attendus. */
    source: 'jeu' | 'reference';
    /** Le nombre d'exemples rangés, et le plus long. */
    exemples: number;
    plusLong: number;
  }

  const { resultats, source, exemples, plusLong }: Props = $props();
  const FINE = '\u202F';
  const CANAL = 'empaquetage:longueur';
  const RESULTATS = untrack(() => resultats);
  if (RESULTATS.length !== LONGUEURS_DE_RANGEE.length || RESULTATS.some((r, i) => r.longueur !== LONGUEURS_DE_RANGEE[i])) {
    throw new Error('FigureEmpaquetage : il faut un empaquetage par longueur de LONGUEURS_DE_RANGEE, dans le même ordre.');
  }
  const DEPART = LONGUEURS_DE_RANGEE.indexOf(LONGUEUR_DE_TON_IA);

  const rang = canal<number>(CANAL, DEPART);
  const r = $derived(RESULTATS[$rang]);
  const phrase = $derived(phraseDeLEmpaquetage(r));
  /** La largeur d'un exemple dans sa rangée, en pourcentage des places. */
  const largeur = (n: number) => `${((100 * n) / r.places).toFixed(3)}%`;

  // Les lecteurs d'écran entendent la phrase quand le lecteur change la longueur (pas à l'arrivée).
  let annonce = $state('');
  let rangAvant = untrack(() => $rang);
  $effect(() => {
    const i = $rang;
    if (i === rangAvant) return;
    rangAvant = i;
    annonce = `Avec des rangées de ${nombre(LONGUEURS_DE_RANGEE[i])} ${untrack(() => phrase)}`;
  });
</script>

<figure class="figure-empaquetage" data-figure="empaquetage" data-longueur={r.longueur}>
  <p class="reglage">
    Avec des rangées de <NombreManipulable
      canal={CANAL}
      min={0}
      max={LONGUEURS_DE_RANGEE.length - 1}
      initiale={DEPART}
      etiquette="Longueur des rangées, en jetons"
      testId="emp-longueur"
      texte={(i) => nombre(LONGUEURS_DE_RANGEE[i])}
      pixelsParUnite={28}
    /> <span data-test="emp-phrase">{phrase}</span>
  </p>
  <!-- Le dessin répète la phrase en image : les lecteurs d'écran ont déjà les nombres. -->
  <ol class="rangees" aria-hidden="true" data-pagefind-ignore>
    {#each r.premieres as rangee, i (`${r.longueur}-${i}`)}
      <li class="rangee" data-test="emp-rangee">
        {#each rangee as n, j (j)}<span class="exemple" class:b={j % 2 === 1} style:width={largeur(n)}></span>{/each}
      </li>
    {/each}
  </ol>
  <p class="vh" role="status">{annonce}</p>
  <figcaption>
    Les {nombre(r.premieres.length)} premières rangées sur {nombre(r.rangees)}{FINE}: chaque morceau est un exemple, le blanc
    est du bourrage. BFD range les plus longs d’abord, chacun dans la rangée où il laisse le moins de place.
    {#if source === 'reference'}
      Avant le relevé du jeu d’affinage de ton IA, la figure range une liste de référence du projet{FINE}: {nombre(exemples)}
      longueurs tirées au sort, jusqu’à {nombre(plusLong)} jetons.
    {:else}
      Ce sont les {nombre(exemples)} conversations du jeu d’affinage de ton IA, jusqu’à {nombre(plusLong)} jetons.
    {/if}
  </figcaption>
</figure>

<style>
  .figure-empaquetage {
    margin: 0.6em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.8em;
    line-height: 1.9;
  }

  /* Une rangée par ligne : une barre aussi large que ses places, sous un trait d'encre. */
  .rangees {
    list-style: none;
    margin: 0;
    padding: 10px 0 2px;
    border-top: 2px solid var(--indigo);
  }

  .rangee {
    display: flex;
    height: 18px;
    margin: 0 0 6px;
    background: var(--papier);
    border: 1px solid var(--lavande);
    border-radius: 3px;
    overflow: hidden;
  }

  /* Les exemples, aux teintes alternées des jetons, séparés d'un trait. */
  .exemple {
    flex: 0 0 auto;
    height: 100%;
    background: var(--teinte-a);
    border-right: 1px solid var(--teinte-a-trait);
  }

  .exemple.b {
    background: var(--teinte-b);
    border-right-color: var(--teinte-b-trait);
  }

  figcaption {
    margin-top: 8px;
    font-family: var(--titres);
    font-size: 15px;
    line-height: 1.45;
    color: var(--indigo-doux);
  }
</style>
