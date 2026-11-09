<script lang="ts">
  // La figure de RoPE du chapitre 1.4 : une tête de 8 valeurs, coupée en 4
  // paires, et un cadran par paire. Le lecteur règle la position du jeton (de 0
  // à 32, le nombre jaune) ; l'aiguille de chaque cadran tourne de l'angle de
  // sa paire à cette position, celui du jumeau anglesRope (rope.ts), en float64
  // comme les attendus : la figure montre le calcul, forge fait celui du modèle.
  //
  // Mouvement : l'aiguille glisse vers son nouvel angle (une transition CSS),
  // seulement après un geste du lecteur. Sous prefers-reduced-motion: reduce,
  // elle se pose tout de suite, sans glisser.
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <FigureRope client:load verrou="rope" />
  // La position vit dans le canal « rope:position », désactivée tant que le
  // verrou n'est pas ouvert. Sans JavaScript, Astro rend la figure telle
  // qu'elle est à l'arrivée.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { BASE_ROPE, FIGURE_ROPE, POSITION_INITIALE, texteDegres } from '../../../lib/partie-1/paris-1-4';
  import { anglesRope } from '../../../lib/partie-1/rope';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive la position tant qu'il n'est pas ouvert. */
    verrou?: string;
  }

  const { verrou }: Props = $props();
  const FINE = '\u202F';
  const CANAL = 'rope:position';

  const position = canal<number>(CANAL, POSITION_INITIALE);
  const nomDuVerrou = untrack(() => verrou);
  const angles = $derived(anglesRope($position, FIGURE_ROPE.dimTete, BASE_ROPE));
  /** Les graduations du cadran : une tous les 30°, comme les heures d'une horloge. */
  const graduations = Array.from({ length: 12 }, (_, i) => (i * Math.PI) / 6);
  const degres = (a: number) => (a * 180) / Math.PI;

  // Les lecteurs d'écran entendent les angles quand la position change (pas à l'arrivée).
  let annonce = $state('');
  let positionAvant = untrack(() => $position);
  $effect(() => {
    const p = $position;
    if (p === positionAvant) return;
    positionAvant = p;
    const a = untrack(() => angles);
    annonce = `Position ${p}${FINE}: la paire 1 a tourné de ${texteDegres(a[0])}, la paire ${a.length} de ${texteDegres(a[a.length - 1])}.`;
  });
</script>

<figure class="figure-rope" data-figure="rope">
  <p class="reglage">
    Le jeton est à la position <NombreManipulable
      canal={CANAL}
      min={0}
      max={FIGURE_ROPE.positionMax}
      initiale={POSITION_INITIALE}
      etiquette="Position du jeton"
      verrou={nomDuVerrou}
      testId="rope-position"
    />.
  </p>
  <ol class="cadrans">
    {#each angles as a, i (i)}
      <li>
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle class="cadran" cx="50" cy="50" r="44" />
          {#each graduations as g (g)}
            <line
              class={g === 0 ? 'midi' : 'graduation'}
              x1={50 + 38 * Math.sin(g)}
              y1={50 - 38 * Math.cos(g)}
              x2={50 + 44 * Math.sin(g)}
              y2={50 - 44 * Math.cos(g)}
            />
          {/each}
          <g class="aiguille" data-aiguille={i} data-angle={String(a)} style:transform={`rotate(${degres(a)}deg)`}>
            <line x1="50" y1="56" x2="50" y2="14" />
            <polygon points="50,9 45.5,18 54.5,18" />
          </g>
          <circle class="axe" cx="50" cy="50" r="4" />
        </svg>
        <p class="legende-cadran">
          <!-- Le deux-points ne sert qu'aux lecteurs d'écran : à l'écran, le nom et l'angle sont sur deux lignes. -->
          <span class="nom">Paire {i + 1}<span class="vh">{FINE}:</span></span>
          <span class="angle" data-test={`rope-angle-${i}`}>{texteDegres(a)}</span>
        </p>
      </li>
    {/each}
  </ol>
  <p class="vh" role="status">{annonce}</p>
  <figcaption>
    Une tête de {FIGURE_ROPE.dimTete} valeurs, soit {FIGURE_ROPE.dimTete / 2} paires{FINE}: chaque paire est une aiguille. À la
    position 0, toutes sont à midi. Puis chacune tourne de son pas à chaque position, la paire 1 le plus vite.
  </figcaption>
</figure>

<style>
  .figure-rope {
    margin: 0.6em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.6em;
    line-height: 1.9;
  }

  /* Quatre cadrans côte à côte ; deux par ligne sur un téléphone. */
  .cadrans {
    list-style: none;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px 18px;
    padding: 0;
    margin: 0;
  }

  .cadrans svg {
    display: block;
    width: 100%;
    max-width: 128px;
    height: auto;
    margin: 0 auto;
  }

  .cadran {
    fill: var(--brume-claire);
    stroke: var(--lavande);
    stroke-width: 1.5;
  }

  .graduation {
    stroke: var(--lavande);
    stroke-width: 1.5;
  }

  /* Midi, le départ de chaque aiguille : un trait plus marqué. */
  .midi {
    stroke: var(--indigo);
    stroke-width: 2.5;
  }

  /* L'aiguille tourne autour du centre du cadran (50, 50, dans les unités du dessin). */
  .aiguille {
    transform-box: view-box;
    transform-origin: 50px 50px;
  }

  .aiguille line {
    stroke: var(--indigo);
    stroke-width: 3;
    stroke-linecap: round;
  }

  .aiguille polygon,
  .axe {
    fill: var(--indigo);
  }

  /* Elle glisse seulement si le lecteur accepte le mouvement ; sinon elle se pose. Sous
     prefers-reduced-motion, la feuille commune (base.css) ramène toute transition à 0,01 ms, sans
     en changer la propriété : l'aiguille n'en a aucune, et prend son angle dès le changement. */
  @media (prefers-reduced-motion: no-preference) {
    .aiguille {
      transition: transform 0.45s cubic-bezier(0.2, 0.8, 0.3, 1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .aiguille {
      transition-property: none;
    }
  }

  .legende-cadran {
    margin: 6px 0 0;
    text-align: center;
    line-height: 1.3;
  }

  .legende-cadran .nom {
    display: block;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 16px;
  }

  .legende-cadran .angle {
    font-family: var(--titres);
    font-size: 16px;
    font-variant-numeric: tabular-nums;
    color: var(--indigo-doux);
  }

  figcaption {
    margin-top: 12px;
    color: var(--indigo-doux);
  }

  @media (max-width: 720px) {
    .cadrans {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
