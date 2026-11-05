<script lang="ts">
  // Un nombre réglable posé dans une phrase : une pastille jaune soleil (le
  // jaune est réservé à ce qui se manipule). On la fait glisser à la souris ou
  // au doigt, une unité tous les 6 px horizontaux (prop `pixelsParUnite`), ou on
  // la règle au clavier :
  //   - flèches droite et haut : + pas ; flèches gauche et bas : - pas ;
  //   - Page précédente / Page suivante : + 10 / - 10 ;
  //   - Début : minimum ; Fin : maximum.
  //
  // La valeur vit dans un canal nommé (src/lib/canal.ts) : tous les îlots qui
  // nomment le même canal voient et règlent la même valeur.
  //
  // Tant que le verrou nommé n'est pas ouvert (le pari dont `ouvre` vaut ce
  // nom), le nombre est désactivé : hors de la tabulation, aria-disabled, et
  // sourd au clavier comme au glissé.
  //
  // La valeur du canal est un nombre, mais ce qui s'affiche peut être un autre
  // texte (prop `texte`) : le mini-modèle règle l'indice d'un taux (0 à 5) et
  // montre le taux lui-même (« 0,01 »). Ce texte est aussi celui que lisent
  // les lecteurs d'écran (aria-valuetext).
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal as canalNomme, ouverture } from '../../lib/canal';

  interface Props {
    /** Nom du canal qui porte la valeur. */
    canal: string;
    min: number;
    max: number;
    /** Valeur de départ du canal, s'il n'a pas encore été créé. */
    initiale: number;
    /** Nom lu par les lecteurs d'écran (aria-label). */
    etiquette: string;
    /** Pas des flèches et du glissé ; 1 par défaut. */
    pas?: number;
    /** Nom du verrou : le nombre reste désactivé tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Valeur de data-test, pour les parcours de test. */
    testId?: string;
    /** Le texte affiché pour une valeur (et lu par aria-valuetext) ; la valeur elle-même par défaut. */
    texte?: (v: number) => string;
    /**
     * Les pixels de glissé horizontal pour une unité ; 6 par défaut. Plus grand pour un réglage à
     * peu de crans, que le doigt ne doit pas faire sauter d'un bout à l'autre (le taux du mini-modèle).
     */
    pixelsParUnite?: number;
  }

  const {
    canal: nomDuCanal,
    min,
    max,
    initiale,
    etiquette,
    pas = 1,
    verrou,
    testId,
    texte,
    pixelsParUnite = 6,
  }: Props = $props();
  const SAUT_PAGE = 10;

  // Le canal et le verrou sont choisis une fois pour toutes (untrack le dit) :
  // un îlot ne change pas de canal en cours de route.
  const valeur = canalNomme<number>(
    untrack(() => nomDuCanal),
    untrack(() => initiale),
  );
  const nomDuVerrou = untrack(() => verrou);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  // Assez large pour le plus long nombre possible : la phrase ne bouge pas
  // pendant qu'on fait glisser le nombre de 9 à 10, ou de 99 à 100. Avec un
  // texte, c'est le plus long des textes de min à max (de pas en pas, s'il y en
  // a au plus 200 ; au-delà, celui de min ou celui de max). Un pas de 0,5 compte
  // donc « −1,5 », plus long que « −2 ».
  const CRANS_MESURES_MAX = 200;
  const chiffres = $derived.by(() => {
    if (texte === undefined) return Math.max(String(min).length, String(max).length);
    let longueur = Math.max(texte(min).length, texte(max).length);
    if ((max - min) / pas <= CRANS_MESURES_MAX) {
      // min + i × pas, plutôt qu'une somme de pas : aucun arrondi ne s'accumule.
      for (let i = 0; min + i * pas < max; i += 1) longueur = Math.max(longueur, texte(min + i * pas).length);
    }
    return longueur;
  });
  const affiche = $derived(texte === undefined ? String($valeur) : texte($valeur));

  let element: HTMLSpanElement | undefined = $state();
  let glisse = $state(false);
  // Le geste en cours : le doigt ou la souris, où il a commencé, et la valeur d'alors.
  let geste: { pointeur: number; x: number; depart: number } | null = null;

  function regler(v: number): void {
    valeur.set(Math.min(max, Math.max(min, v)));
  }

  function auClavier(evenement: KeyboardEvent): void {
    if (!actif) return;
    const v = $valeur;
    const cible: Record<string, number> = {
      ArrowRight: v + pas,
      ArrowUp: v + pas,
      ArrowLeft: v - pas,
      ArrowDown: v - pas,
      PageUp: v + SAUT_PAGE,
      PageDown: v - SAUT_PAGE,
      Home: min,
      End: max,
    };
    if (!Object.hasOwn(cible, evenement.key)) return;
    evenement.preventDefault(); // pas de défilement de la page
    regler(cible[evenement.key]);
  }

  function presse(evenement: PointerEvent): void {
    if (!actif || !element || geste) return;
    if (evenement.pointerType === 'mouse' && evenement.button !== 0) return;
    geste = { pointeur: evenement.pointerId, x: evenement.clientX, depart: $valeur };
    element.setPointerCapture(evenement.pointerId);
    // Pas de sélection de texte pendant le geste ; le focus, lui, vient ici
    // pour que le clavier puisse prendre le relais.
    evenement.preventDefault();
    element.focus({ preventScroll: true });
    glisse = true;
    document.documentElement.classList.add('nombre-glisse');
  }

  function bouge(evenement: PointerEvent): void {
    if (!geste || evenement.pointerId !== geste.pointeur) return;
    const unites = Math.trunc((evenement.clientX - geste.x) / pixelsParUnite);
    regler(geste.depart + unites * pas);
  }

  function lache(evenement: PointerEvent): void {
    if (!geste || evenement.pointerId !== geste.pointeur) return;
    geste = null;
    glisse = false;
    document.documentElement.classList.remove('nombre-glisse');
  }
</script>

<span
  bind:this={element}
  class="nombre"
  class:glisse
  style:--chiffres={chiffres}
  role="slider"
  tabindex={actif ? 0 : -1}
  aria-label={etiquette}
  aria-valuemin={min}
  aria-valuemax={max}
  aria-valuenow={$valeur}
  aria-valuetext={texte === undefined ? undefined : affiche}
  aria-disabled={actif ? undefined : 'true'}
  data-test={testId}
  onkeydown={auClavier}
  onpointerdown={presse}
  onpointermove={bouge}
  onpointerup={lache}
  onpointercancel={lache}
  onlostpointercapture={lache}>{affiche}</span
>

<style>
  .nombre {
    display: inline-block;
    /* Les chiffres ont tous la même largeur (tabular-nums) : 1ch chacun. */
    min-width: calc(var(--chiffres) * 1ch + 12px);
    padding: 0 6px;
    /* De quoi loger les chevrons et le cadre du focus sans toucher les mots voisins. */
    margin: 0 11px;
    font-family: var(--titres);
    font-weight: 800;
    font-size: 0.95em;
    line-height: 1.25;
    font-variant-numeric: tabular-nums;
    text-align: center;
    color: var(--indigo);
    background: var(--soleil);
    border-radius: 6px;
    box-shadow: 0 2px 0 var(--indigo);
    cursor: ew-resize;
    user-select: none;
    -webkit-user-select: none;
    /* Le doigt fait défiler la page à la verticale, et glisse le nombre à
       l'horizontale : poser le pouce dessus en lisant ne bloque pas la page. */
    touch-action: pan-y;
    position: relative;
  }

  .nombre:focus-visible {
    outline-offset: 2px;
  }

  .nombre:not([aria-disabled='true']):hover,
  .nombre.glisse {
    background: var(--soleil-vif);
  }

  .nombre[aria-disabled='true'] {
    cursor: default;
  }

  /* Les chevrons ‹ › disent « ça se fait glisser », au survol et au focus. */
  .nombre::before,
  .nombre::after {
    position: absolute;
    top: 50%;
    transform: translateY(-52%);
    font-size: 13px;
    font-weight: 800;
    color: var(--indigo);
    opacity: 0;
    transition: opacity 0.12s ease;
    pointer-events: none;
  }

  .nombre::before {
    content: '\2039';
    left: -12px;
  }

  .nombre::after {
    content: '\203A';
    right: -12px;
  }

  .nombre:not([aria-disabled='true']):is(:hover, :focus-visible, .glisse)::before,
  .nombre:not([aria-disabled='true']):is(:hover, :focus-visible, .glisse)::after {
    opacity: 1;
  }

  /* Pendant le glissé, la flèche double suit le pointeur partout dans la page. */
  :global(html.nombre-glisse),
  :global(html.nombre-glisse *) {
    cursor: ew-resize !important;
  }

  @media (prefers-reduced-motion: reduce) {
    .nombre::before,
    .nombre::after {
      transition: none;
    }
  }
</style>
