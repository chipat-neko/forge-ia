<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // La figure des vecteurs du chapitre 0.2 : deux vecteurs du plan, a et b,
  // réglés par quatre nombres jaunes, dessinés en flèches sur un quadrillage
  // de −5 à 5, avec leur somme en pointillé. Sous le dessin, leur produit
  // scalaire terme à terme, et le cosinus de leur angle.
  //
  // Tout est calculé par le jumeau exact du Python (src/lib/partie-0/maths.ts),
  // et les phrases viennent de paris-0-2.ts, le même code que les paris.
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <FigureVecteurs client:load verrou="vecteurs" acquis="perpendiculaires" />
  // Les coordonnées vivent dans les canaux « vec:ax », « vec:ay », « vec:bx » et
  // « vec:by ». Les nombres restent désactivés tant que le verrou n'est pas
  // ouvert. La première fois que a et b sont perpendiculaires (a · b = 0, aucun
  // des deux nul), la figure émet `forge:acquis` avec la clé `acquis` : c'est
  // le défi du chapitre.
  //
  // Sans JavaScript, Astro rend la figure telle qu'elle est à l'arrivée.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { produitScalaire, somme } from '../../../lib/partie-0/maths';
  import {
    A_DEPART,
    B_DEPART,
    COORDONNEE_MAX,
    COORDONNEE_MIN,
    DEFI_VECTEURS_REUSSI,
    DEMI_GRILLE,
    ecrireNombre,
    ecrireVecteur,
    estNul,
    perpendiculaires,
    texteCosinus,
    texteScalaire,
    type Vecteur,
  } from '../../../lib/partie-0/paris-0-2';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive les nombres tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné la première fois que a et b sont perpendiculaires. */
    acquis?: string;
  }

  const { verrou, acquis }: Props = $props();

  const FINE = '\u202F';
  // Le nom du rectangle qui rogne la somme au bord du quadrillage : unique dans la page.
  const idUnique = $props.id();
  const idGrille = `grille-${idUnique}`;

  // Les canaux, le verrou et l'acquis sont lus une fois pour toutes, comme dans
  // NombreManipulable : un îlot ne change pas de canal en cours de route.
  const ax = canal<number>('vec:ax', A_DEPART[0]);
  const ay = canal<number>('vec:ay', A_DEPART[1]);
  const bx = canal<number>('vec:bx', B_DEPART[0]);
  const by = canal<number>('vec:by', B_DEPART[1]);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);

  const a = $derived<Vecteur>([$ax, $ay]);
  const b = $derived<Vecteur>([$bx, $by]);
  const s = $derived(somme(a, b));
  const scalaire = $derived(produitScalaire(a, b));
  const reussi = $derived(perpendiculaires(a, b));

  // ---------- Le dessin ----------

  // Le quadrillage va de −DEMI_GRILLE à DEMI_GRILLE, UNITE pixels par unité,
  // centré dans un carré de TAILLE pixels : la marge loge les étiquettes.
  const TAILLE = 300;
  const UNITE = 25;
  const CENTRE = TAILLE / 2;
  const BORD = DEMI_GRILLE * UNITE;
  const TETE = 10;
  const DEMI_TETE = 5;
  const RAYON_ANGLE = 22;
  const crans = Array.from({ length: 2 * DEMI_GRILLE + 1 }, (_, i) => i - DEMI_GRILLE);
  /** Les graduations écrites sur les axes : une sur deux, sans le 0 ni les bords. */
  const graduations = crans.filter((k) => k !== 0 && k % 2 === 0);

  const px = (x: number) => CENTRE + UNITE * x;
  const py = (y: number) => CENTRE - UNITE * y;
  /** Le point au bout d'un vecteur, en pixels du dessin. */
  const bout = (v: readonly number[]) => [px(v[0]), py(v[1])] as const;
  /** Un nombre de pixels écrit court, pour les attributs du SVG. */
  const f = (x: number) => String(Math.round(x * 100) / 100);
  const dansLaGrille = (v: readonly number[]) => v.every((c) => Math.abs(c) <= DEMI_GRILLE);

  /** La direction d'un vecteur non nul, en pixels du dessin (l'axe des y descend). */
  function direction(v: readonly number[]): [number, number] {
    const dx = v[0];
    const dy = -v[1];
    const l = Math.hypot(dx, dy);
    return [dx / l, dy / l];
  }

  /**
   * Une flèche de l'origine au bout du vecteur (non nul) : le trait, arrêté
   * sous la pointe, la pointe, et la place de l'étiquette, un peu au-delà.
   */
  function fleche(v: readonly number[]) {
    const [tx, ty] = bout(v);
    const [ux, uy] = direction(v);
    const [nx, ny] = [-uy, ux];
    const [baseX, baseY] = [tx - TETE * ux, ty - TETE * uy];
    const borne = (x: number, min: number, max: number) => Math.min(max, Math.max(min, x));
    return {
      x2: f(tx - (TETE - 2) * ux),
      y2: f(ty - (TETE - 2) * uy),
      pointe: [
        [tx, ty],
        [baseX + DEMI_TETE * nx, baseY + DEMI_TETE * ny],
        [baseX - DEMI_TETE * nx, baseY - DEMI_TETE * ny],
      ]
        .map(([x, y]) => `${f(x)},${f(y)}`)
        .join(' '),
      // L'étiquette reste dans le carré, même au bout d'un vecteur du bord.
      etiquetteX: f(borne(tx + 15 * ux, 16, TAILLE - 16)),
      etiquetteY: f(borne(ty + 15 * uy, 14, TAILLE - 10)),
    };
  }

  const memeBout = $derived(a[0] === b[0] && a[1] === b[1]);
  const flecheA = $derived(estNul(a) ? null : fleche(a));
  const flecheB = $derived(estNul(b) ? null : fleche(b));
  // La somme n'est dessinée qu'avec deux vecteurs non nuls : sinon elle se confond avec l'autre flèche.
  const flecheS = $derived(estNul(a) || estNul(b) || estNul(s) ? null : fleche(s));
  const sommeDedans = $derived(dansLaGrille(s));

  // Le petit arc de l'angle entre a et b, ou l'équerre quand ils sont perpendiculaires.
  const angle = $derived.by(() => {
    if (estNul(a) || estNul(b)) return null;
    const [uax, uay] = direction(a);
    const [ubx, uby] = direction(b);
    if (reussi) {
      const r = 11;
      const coin = [
        [CENTRE + r * uax, CENTRE + r * uay],
        [CENTRE + r * (uax + ubx), CENTRE + r * (uay + uby)],
        [CENTRE + r * ubx, CENTRE + r * uby],
      ];
      return { equerre: true, d: `M${coin.map(([x, y]) => `${f(x)},${f(y)}`).join('L')}` };
    }
    const produit = uax * ubx + uay * uby;
    if (produit > 0.999) return null; // même direction : pas d'angle à montrer
    // Dans le dessin, l'axe des y descend : un produit vectoriel positif tourne dans le sens des aiguilles d'une montre.
    const sens = uax * uby - uay * ubx >= 0 ? 1 : 0;
    const d =
      `M${f(CENTRE + RAYON_ANGLE * uax)},${f(CENTRE + RAYON_ANGLE * uay)}` +
      `A${RAYON_ANGLE},${RAYON_ANGLE} 0 0 ${sens} ${f(CENTRE + RAYON_ANGLE * ubx)},${f(CENTRE + RAYON_ANGLE * uby)}`;
    return { equerre: false, d };
  });

  // Le nom du dessin, pour les lecteurs d'écran.
  const nomDuDessin = $derived.by(() => {
    const decrire = (nom: string, v: readonly number[]) =>
      estNul(v) ? `${nom} = ${ecrireVecteur(v)}, nul, n’est qu’un point à l’origine` : `${nom} = ${ecrireVecteur(v)}`;
    const sommeDite = estNul(s)
      ? `leur somme a + b = ${ecrireVecteur(s)} est nulle`
      : estNul(a) || estNul(b)
        ? `leur somme a + b = ${ecrireVecteur(s)} se confond avec l’autre flèche`
      : `leur somme a + b = ${ecrireVecteur(s)} est en pointillé${sommeDedans ? '' : ', et sort du quadrillage'}`;
    const droit = reussi ? ' a et b forment un angle droit.' : '';
    return (
      `Quadrillage de ${ecrireNombre(-DEMI_GRILLE)} à ${DEMI_GRILLE}, ` +
      `${decrire('a', a)} et ${decrire('b', b)}, en flèches depuis l’origine${FINE}; ${sommeDite}.${droit}`
    );
  });

  // ---------- Le défi ----------

  const etatDuDefi = $derived.by(() => {
    if (reussi) return DEFI_VECTEURS_REUSSI;
    if (scalaire === 0) return `Pas encore${FINE}: a · b vaut 0, mais un vecteur nul n’a pas de direction.`;
    return `Pas encore${FINE}: a · b vaut ${ecrireNombre(scalaire)}.`;
  });

  // La réussite est annoncée aux lecteurs d'écran au moment où elle arrive, et
  // l'acquis est gagné la première fois.
  let annonceDefi = $state('');
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const maintenant = reussi;
    if (maintenant === reussiAvant) return;
    reussiAvant = maintenant;
    annonceDefi = maintenant ? DEFI_VECTEURS_REUSSI : '';
    if (maintenant && cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  });

  const coordonnee = (v: number) => ecrireNombre(v);
</script>

{#snippet nombre(nomDuCanal: string, initiale: number, etiquette: string, testId: string)}
  <NombreManipulable
    canal={nomDuCanal}
    min={COORDONNEE_MIN}
    max={COORDONNEE_MAX}
    {initiale}
    {etiquette}
    verrou={nomDuVerrou}
    {testId}
    texte={coordonnee}
  />
{/snippet}

<div class="figure-vecteurs" data-figure="vecteurs">
  <p class="reglage">
    <span class="paire"
      ><svg class="cle" viewBox="0 0 26 10" aria-hidden="true"><line class="trait-a" x1="1" x2="25" y1="5" y2="5" /></svg
      >a = ({@render nombre('vec:ax', A_DEPART[0], 'Première coordonnée de a', 'vec-ax')},{@render nombre(
        'vec:ay',
        A_DEPART[1],
        'Seconde coordonnée de a',
        'vec-ay',
      )})</span
    >
    et
    <span class="paire"
      ><svg class="cle" viewBox="0 0 26 10" aria-hidden="true"><line class="trait-b" x1="1" x2="25" y1="5" y2="5" /></svg
      >b = ({@render nombre('vec:bx', B_DEPART[0], 'Première coordonnée de b', 'vec-bx')},{@render nombre(
        'vec:by',
        B_DEPART[1],
        'Seconde coordonnée de b',
        'vec-by',
      )})</span
    >
  </p>

  <svg class="dessin" viewBox="0 0 {TAILLE} {TAILLE}" role="img" aria-label={nomDuDessin} data-test="vec-dessin">
    <defs>
      <clipPath id={idGrille}>
        <rect x={CENTRE - BORD} y={CENTRE - BORD} width={2 * BORD} height={2 * BORD} />
      </clipPath>
    </defs>
    {#each crans as k (k)}
      <line class={k === 0 ? 'axe' : 'grille'} x1={px(k)} x2={px(k)} y1={CENTRE - BORD} y2={CENTRE + BORD} />
      <line class={k === 0 ? 'axe' : 'grille'} x1={CENTRE - BORD} x2={CENTRE + BORD} y1={py(k)} y2={py(k)} />
    {/each}
    {#each graduations as k (k)}
      <text class="graduation" x={px(k)} y={CENTRE + 14}>{ecrireNombre(k)}</text>
      <text class="graduation graduation-y" x={CENTRE - 6} y={py(k)}>{ecrireNombre(k)}</text>
    {/each}
    {#if angle !== null}
      <path class="angle" d={angle.d} />
    {/if}
    {#if flecheS !== null}
      <g clip-path="url(#{idGrille})">
        <line class="trait-s" x1={CENTRE} y1={CENTRE} x2={sommeDedans ? flecheS.x2 : f(bout(s)[0])} y2={sommeDedans ? flecheS.y2 : f(bout(s)[1])} />
      </g>
      {#if sommeDedans}
        <polygon class="pointe-s" points={flecheS.pointe} />
        <text class="nom nom-s" x={flecheS.etiquetteX} y={flecheS.etiquetteY}>a + b</text>
      {/if}
    {/if}
    {#if flecheB !== null}
      <line class="trait-b" x1={CENTRE} y1={CENTRE} x2={flecheB.x2} y2={flecheB.y2} />
      <polygon class="pointe-b" points={flecheB.pointe} />
      {#if !memeBout}
        <text class="nom nom-b" x={flecheB.etiquetteX} y={flecheB.etiquetteY}>b</text>
      {/if}
    {:else}
      <circle class="nul-b" cx={CENTRE} cy={CENTRE} r="7" />
    {/if}
    {#if flecheA !== null}
      <line class="trait-a" x1={CENTRE} y1={CENTRE} x2={flecheA.x2} y2={flecheA.y2} />
      <polygon class="pointe-a" points={flecheA.pointe} />
      <text class="nom nom-a" x={flecheA.etiquetteX} y={flecheA.etiquetteY}>{memeBout ? 'a, b' : 'a'}</text>
    {:else}
      <circle class="nul-a" cx={CENTRE} cy={CENTRE} r="4" />
    {/if}
  </svg>

  <p class="somme" data-test="vec-somme">
    <svg class="cle" viewBox="0 0 26 10" aria-hidden="true"><line class="trait-s" x1="1" x2="25" y1="5" y2="5" /></svg
    >Leur somme{FINE}: a + b = {ecrireVecteur(s)}{sommeDedans ? '' : ', hors du dessin'}
  </p>

  <p class="calcul" data-test="vec-scalaire">{texteScalaire(a, b)}</p>
  <p class="calcul" data-test="vec-cosinus">{texteCosinus(a, b)}</p>

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>
      Règle a et b pour qu’ils soient perpendiculaires{FINE}: <span class="insecable">a · b</span> doit valoir 0, sans qu’aucun
      des deux soit nul.
    </p>
    {#if reussi}
      <p class="etat" data-test="vec-defi">{DEFI_VECTEURS_REUSSI}</p>
    {:else}
      <p class="etat" data-test="vec-defi-etat">{etatDuDefi}</p>
    {/if}
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .figure-vecteurs {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.4em;
    line-height: 1.9;
  }

  /* La virgule de « (3, 1) » colle au premier nombre : sa marge de droite, faite
     pour loger le chevron, est réduite ici (et seulement ici). */
  .paire > :global(.nombre:first-of-type) {
    margin-right: 1px;
  }

  /* « a = (3, 1) » ne se coupe pas : la phrase passe à la ligne entre les deux vecteurs. */
  .paire {
    white-space: nowrap;
  }

  /* La clé de couleur devant chaque vecteur, et devant la somme. */
  .cle {
    display: inline-block;
    width: 26px;
    height: 10px;
    margin-right: 6px;
    vertical-align: middle;
    overflow: visible;
  }

  .dessin {
    display: block;
    width: 100%;
    max-width: 300px;
    height: auto;
    margin: 0.4em 0 0;
  }

  .grille {
    stroke: var(--brume);
    stroke-width: 1;
  }

  .axe {
    stroke: var(--lavande);
    stroke-width: 1.5;
  }

  .trait-a,
  .trait-b,
  .trait-s {
    stroke-width: 2.5;
    stroke-linecap: round;
  }

  .trait-a {
    stroke: var(--indigo);
  }

  .trait-b {
    stroke: var(--indigo-doux);
  }

  .trait-s {
    stroke: var(--lavande);
    stroke-width: 2;
    stroke-dasharray: 6 5;
    stroke-linecap: butt;
  }

  .pointe-a {
    fill: var(--indigo);
  }

  .pointe-b {
    fill: var(--indigo-doux);
  }

  .pointe-s {
    fill: var(--lavande);
  }

  /* Un vecteur nul n'est qu'un point à l'origine : un rond creux. */
  .nul-a,
  .nul-b {
    fill: var(--papier);
    stroke-width: 2.5;
  }

  .nul-a {
    stroke: var(--indigo);
  }

  .nul-b {
    stroke: var(--indigo-doux);
  }

  /* Les graduations des axes, discrètes : une sur deux, en encre douce. */
  .graduation {
    font-family: var(--titres);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    fill: var(--indigo-doux);
    text-anchor: middle;
    dominant-baseline: central;
    paint-order: stroke;
    stroke: var(--papier);
    stroke-width: 3px;
    stroke-linejoin: round;
  }

  .graduation-y {
    text-anchor: end;
  }

  .angle {
    fill: none;
    stroke: var(--indigo-doux);
    stroke-width: 1.25;
  }

  /* Les noms des flèches, en italique, détachés du quadrillage par un liseré de papier. */
  .nom {
    font-family: var(--texte);
    font-style: italic;
    font-size: 19px;
    text-anchor: middle;
    dominant-baseline: central;
    paint-order: stroke;
    stroke: var(--papier);
    stroke-width: 5px;
    stroke-linejoin: round;
  }

  .nom-a {
    fill: var(--indigo);
  }

  .nom-b,
  .nom-s {
    fill: var(--indigo-doux);
  }

  .somme {
    margin: 0.3em 0 0.8em;
    font-size: 0.9em;
    color: var(--indigo-doux);
  }

  /* Les deux calculs, détachés comme des formules : chiffres de titre, à chasse fixe. */
  .calcul {
    margin: 0 0 0.3em;
    font-family: var(--titres);
    font-size: 19px;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme dans l'atelier de 0.1. */
  .defi {
    margin-top: 1em;
    padding-top: 14px;
    border-top: 1px solid var(--brume);
    font-size: 0.95em;
  }

  .defi h3 {
    font-weight: 700;
    font-size: 20px;
    margin: 0 0 4px;
  }

  .defi p {
    margin: 0 0 0.4em;
  }

  /* « a · b » ne se coupe pas en fin de ligne. */
  .insecable {
    white-space: nowrap;
  }

  .defi .etat {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 16px;
    color: var(--indigo-doux);
    margin: 0;
  }

  .defi.reussi .etat {
    color: var(--menthe);
  }

  @media (max-width: 720px) {
    .calcul {
      font-size: 17px;
    }
  }
</style>
