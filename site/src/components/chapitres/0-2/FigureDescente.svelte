<script lang="ts">
  // La figure de la descente du chapitre 0.2 : la courbe de l'erreur
  // (x − 3)² + 1, de x = −2 à 8, le point x, sa tangente (la droite de la
  // pente) et les points déjà visités. Le lecteur règle le départ x0 et le
  // taux, puis fait descendre le point, un pas ou dix à la fois, avec la règle
  // x ← x − taux × pente(x).
  //
  // Tout est calculé par le jumeau exact du Python (src/lib/partie-0/maths.ts),
  // et les phrases viennent de paris-0-2.ts. Une position à plus de 1 000 du
  // fond arrête la descente : la figure ne calcule jamais au-delà, et n'écrit
  // donc jamais ni NaN ni Infinity.
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <FigureDescente client:load verrou="descente" />
  // Le départ et le taux vivent dans les canaux « desc:x0 » et « desc:taux »
  // (le rang du taux dans TAUX_DESCENTE). Changer l'un des deux repart du pas 0.
  // La ligne d'état n'est annoncée aux lecteurs d'écran qu'après un clic.
  //
  // Le dessin suit CourbePerte : le SVG ne porte que les tracés, étirés à la
  // largeur de la figure ; les graduations et le repère « hors du dessin » sont
  // du HTML posé par-dessus, qui garde sa taille.
  //
  // Sans JavaScript, Astro rend la figure telle qu'elle est à l'arrivée.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../../lib/canal';
  import { erreur, pente, TAUX_DESCENTE } from '../../../lib/partie-0/maths';
  import {
    cheminDeDescente,
    ecrireNombre,
    ecrireReglage,
    etatDescente,
    explose,
    FOND,
    INDICE_TAUX_DEPART,
    PAS_MAX,
    X0_DEPART,
    X0_MAX,
    X0_MIN,
    X0_PAS,
  } from '../../../lib/partie-0/paris-0-2';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive les réglages et les boutons tant qu'il n'est pas ouvert. */
    verrou?: string;
  }

  const { verrou }: Props = $props();

  const FINE = '\u202F';
  const MOINS = '\u2212';
  const CANAL_X0 = 'desc:x0';
  const CANAL_TAUX = 'desc:taux';

  // Les canaux et le verrou sont lus une fois pour toutes, comme dans NombreManipulable.
  const x0 = canal<number>(CANAL_X0, X0_DEPART);
  const indiceTaux = canal<number>(CANAL_TAUX, INDICE_TAUX_DEPART);
  const nomDuVerrou = untrack(() => verrou);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);

  // La descente faite par les boutons : ses réglages, son nombre de pas, et ce
  // qui a été annoncé. Dès que le départ ou le taux change, elle ne vaut plus :
  // la figure repart du pas 0, sans rien annoncer.
  let faite = $state({ x0: X0_DEPART, indiceTaux: INDICE_TAUX_DEPART, nbPas: 0, annonce: '' });
  const aJour = $derived(faite.x0 === $x0 && faite.indiceTaux === $indiceTaux);
  const nbPas = $derived(aJour ? faite.nbPas : 0);
  const annonce = $derived(aJour ? faite.annonce : '');

  const taux = $derived(TAUX_DESCENTE[$indiceTaux]);
  const positions = $derived(cheminDeDescente($x0, taux, nbPas));
  const n = $derived(positions.length - 1);
  const x = $derived(positions[n]);
  const etat = $derived(etatDescente(positions));
  // La ligne d'état en morceaux : chaque « nom = valeur » (aux rangs impairs) ne se coupe pas en fin de ligne.
  const morceauxEtat = $derived(etat.split(/(\S+ = \S+)/));
  const finie = $derived(explose(x) || n >= PAS_MAX);
  const pasBloques = $derived(finie || !$ouvert);

  function avancer(pas: number): void {
    if (pasBloques) return;
    const chemin = cheminDeDescente($x0, taux, nbPas + pas);
    faite = { x0: $x0, indiceTaux: $indiceTaux, nbPas: chemin.length - 1, annonce: etatDescente(chemin) };
  }

  function recommencer(): void {
    if (nbPas === 0 || !$ouvert) return;
    faite = { x0: $x0, indiceTaux: $indiceTaux, nbPas: 0, annonce: etatDescente([$x0]) };
  }

  // ---------- Le dessin ----------

  const LARGEUR = 640;
  const HAUTEUR = 300;
  const X_MIN = X0_MIN;
  const X_MAX = X0_MAX;
  const Y_MAX = 28;
  /** La tangente s'étend de part et d'autre du point, sur DEMI_TANGENTE unités de x. */
  const DEMI_TANGENTE = 1.5;

  const sx = (v: number) => ((v - X_MIN) / (X_MAX - X_MIN)) * LARGEUR;
  const sy = (v: number) => HAUTEUR - (v / Y_MAX) * HAUTEUR;
  const f = (v: number) => String(Math.round(v * 10) / 10);
  const dedans = (v: number) => v >= X_MIN && v <= X_MAX;

  // La courbe, échantillonnée tous les seizièmes d'unité.
  const ECHANTILLONS = (X_MAX - X_MIN) * 16;
  const courbe = Array.from({ length: ECHANTILLONS + 1 }, (_, i) => {
    const v = X_MIN + (i * (X_MAX - X_MIN)) / ECHANTILLONS;
    return `${i === 0 ? 'M' : 'L'}${f(sx(v))},${f(sy(erreur(v)))}`;
  }).join('');

  /** Un point du dessin : un trait de longueur nulle à bouts ronds, rond à toute largeur. */
  const point = (v: number) => `M${f(sx(v))},${f(sy(erreur(v)))}h0`;

  // Les points déjà visités (dans le dessin), et les sauts de l'un au suivant.
  const visites = $derived(
    positions
      .slice(0, -1)
      .filter(dedans)
      .map(point)
      .join(''),
  );
  const sauts = $derived(
    positions
      .slice(1)
      .map((v, i) => [positions[i], v])
      .filter(([a, b]) => dedans(a) && dedans(b))
      .map(([a, b]) => `M${f(sx(a))},${f(sy(erreur(a)))}L${f(sx(b))},${f(sy(erreur(b)))}`)
      .join(''),
  );
  const tangente = $derived.by(() => {
    if (!dedans(x)) return null;
    const [a, b] = [x - DEMI_TANGENTE, x + DEMI_TANGENTE];
    const y = (v: number) => erreur(x) + pente(x) * (v - x);
    return `M${f(sx(a))},${f(sy(y(a)))}L${f(sx(b))},${f(sy(y(b)))}`;
  });
  // Le point courant sorti du dessin : à gauche ou à droite.
  const hors = $derived(dedans(x) ? null : x < X_MIN ? 'gauche' : 'droite');

  const gradX = [-2, 0, 2, 4, 6, 8];
  const gradY = [0, 5, 10, 15, 20, 25];
  const enX = (v: number) => (sx(v) / LARGEUR) * 100;
  const enY = (v: number) => (sy(v) / HAUTEUR) * 100;

  const nomDuDessin = $derived.by(() => {
    const debut =
      `Courbe de l’erreur (x ${MOINS} ${ecrireNombre(FOND)})² + 1, de x = ${ecrireNombre(X_MIN)} à x = ${ecrireNombre(X_MAX)}, ` +
      `la plus basse en x = ${ecrireNombre(FOND)}.`;
    const ou = dedans(x)
      ? ` Au pas ${n}, le point est en x = ${ecrireNombre(x, 3)}, avec sa tangente, de pente ${ecrireNombre(pente(x), 3)}.`
      : ` Au pas ${n}, le point est sorti du dessin, en x = ${ecrireNombre(x, 3)}.`;
    const deja = n === 0 ? '' : n === 1 ? ' Un point déjà visité.' : ` ${n} points déjà visités.`;
    return debut + ou + deja;
  });

  const texteTaux = (i: number) => ecrireReglage(TAUX_DESCENTE[i]);

  // Le nom du rectangle qui rogne la tangente au bord du dessin : unique dans la page.
  const idUnique = $props.id();
  const idCadre = `cadre-${idUnique}`;
</script>

<div class="figure-descente" data-figure="descente">
  <p class="reglage">
    Pars de x = <NombreManipulable
      canal={CANAL_X0}
      min={X0_MIN}
      max={X0_MAX}
      pas={X0_PAS}
      initiale={X0_DEPART}
      etiquette="Départ de x"
      verrou={nomDuVerrou}
      testId="desc-x0"
      texte={ecrireReglage}
    />, avec un taux de <NombreManipulable
      canal={CANAL_TAUX}
      min={0}
      max={TAUX_DESCENTE.length - 1}
      initiale={INDICE_TAUX_DEPART}
      etiquette="Taux"
      verrou={nomDuVerrou}
      testId="desc-taux"
      texte={texteTaux}
      pixelsParUnite={24}
    /> à chaque pas.
  </p>

  <figure class="courbe">
    <div class="cadre">
      <span class="titre-axe titre-y" aria-hidden="true">erreur</span>
      <div class="graduations-y" aria-hidden="true">
        {#each gradY as v (v)}
          <span style:top="{enY(v)}%">{ecrireNombre(v)}</span>
        {/each}
      </div>
      <div class="trace">
        <svg
          viewBox="0 0 {LARGEUR} {HAUTEUR}"
          preserveAspectRatio="none"
          role="img"
          aria-label={nomDuDessin}
          data-test="desc-dessin"
        >
          <defs>
            <clipPath id={idCadre}><rect x="0" y="0" width={LARGEUR} height={HAUTEUR} /></clipPath>
          </defs>
          {#each gradY.filter((v) => v > 0) as v (v)}
            <line class="grille" x1="0" x2={LARGEUR} y1={sy(v)} y2={sy(v)} />
          {/each}
          <path class="courbe-erreur" d={courbe} />
          {#if sauts !== ''}
            <path class="sauts" d={sauts} />
          {/if}
          {#if visites !== ''}
            <path class="visite" d={visites} />
          {/if}
          {#if tangente !== null}
            <path class="tangente" d={tangente} clip-path="url(#{idCadre})" />
            <path class="anneau" d={point(x)} />
            <path class="courant" d={point(x)} />
          {/if}
        </svg>
        {#if hors !== null}
          <span class="hors {hors}" data-test="desc-hors">hors du dessin</span>
        {/if}
      </div>
    </div>
    <div class="graduations-x" aria-hidden="true">
      {#each gradX as v (v)}
        <span style:left="{enX(v)}%">{ecrireNombre(v)}</span>
      {/each}
    </div>
    <span class="titre-axe titre-x" aria-hidden="true">x</span>
  </figure>

  <div class="commandes">
    <button type="button" class="bouton-relief" data-test="desc-pas" aria-disabled={pasBloques ? 'true' : undefined} onclick={() => avancer(1)}
      >Un pas</button
    >
    <button type="button" class="bouton-relief" data-test="desc-dix" aria-disabled={pasBloques ? 'true' : undefined} onclick={() => avancer(10)}
      >Dix pas</button
    >
    <button
      type="button"
      class="bouton-relief"
      data-test="desc-recommencer"
      aria-disabled={nbPas === 0 || !$ouvert ? 'true' : undefined}
      onclick={recommencer}>Recommencer</button
    >
  </div>

  <p class="etat" data-test="desc-etat">{#each morceauxEtat as morceau, i (i)}{#if i % 2 === 1}<span class="insecable"
          >{morceau}</span
        >{:else}{morceau}{/if}{/each}</p>
  <p class="vh" role="status" data-test="desc-annonce">{annonce}</p>

  <p class="titre-liste">Les positions de x, pas après pas{FINE}:</p>
  <ol class="positions" data-test="desc-liste">
    {#each positions as v, i (i)}
      <li class:courante={i === n}><span data-x>{ecrireNombre(v, 3)}</span><span class="rang" aria-hidden="true">{i}</span></li>
    {/each}
  </ol>
</div>

<style>
  .figure-descente {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.6em;
    line-height: 1.9;
  }

  /* ---------- Le dessin, comme CourbePerte ---------- */

  .courbe {
    margin: 0 0 1em;
    font-family: var(--titres);
    font-size: 13px;
    line-height: 1.2;
    color: var(--indigo-doux);
    /* La place des graduations de l'erreur, à gauche de la courbe. */
    --gauche: 2.2em;
  }

  .cadre {
    position: relative;
    padding: 1.6em 0 0 var(--gauche);
  }

  .titre-axe {
    font-weight: 600;
  }

  .titre-y {
    position: absolute;
    top: 0;
    left: 0;
  }

  .titre-x {
    display: block;
    text-align: right;
    margin-top: 2px;
  }

  .graduations-y {
    position: absolute;
    top: 1.6em;
    bottom: 0;
    left: 0;
    width: var(--gauche);
  }

  .graduations-y span,
  .graduations-x span {
    position: absolute;
    font-variant-numeric: tabular-nums;
  }

  .graduations-y span {
    right: 0.7em;
    transform: translateY(-50%);
  }

  .graduations-x {
    position: relative;
    height: 1.4em;
    margin: 4px 0 0 var(--gauche);
  }

  .graduations-x span {
    top: 0;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .graduations-x span:first-child {
    transform: none;
  }

  .graduations-x span:last-child {
    transform: translateX(-100%);
  }

  .trace {
    position: relative;
  }

  .trace svg {
    display: block;
    width: 100%;
    max-width: none;
    height: auto;
    aspect-ratio: 640 / 300;
    /* Un point au bord du dessin (x = −2 ou 8) reste rond : seule la tangente est rognée. */
    overflow: visible;
    border-bottom: 1px solid var(--indigo-doux);
    border-left: 1px solid var(--indigo-doux);
  }

  line,
  path {
    vector-effect: non-scaling-stroke;
    fill: none;
  }

  .grille {
    stroke: var(--brume);
    stroke-width: 1;
  }

  .courbe-erreur {
    stroke: var(--indigo);
    stroke-width: 2;
    stroke-linejoin: round;
  }

  .sauts {
    stroke: var(--lavande);
    stroke-width: 1.5;
    stroke-dasharray: 4 4;
  }

  .visite {
    stroke: var(--lavande);
    stroke-width: 8;
    stroke-linecap: round;
  }

  .tangente {
    stroke: var(--indigo-doux);
    stroke-width: 2;
    stroke-linecap: round;
  }

  .anneau {
    stroke: var(--papier);
    stroke-width: 17;
    stroke-linecap: round;
  }

  .courant {
    stroke: var(--indigo);
    stroke-width: 12;
    stroke-linecap: round;
  }

  /* Le point est parti hors du dessin : une flèche vers le bord par où il est sorti. */
  /* En bas, dans un coin que la courbe ne traverse jamais (elle y est au-dessus de 10). */
  .hors {
    position: absolute;
    bottom: 8px;
    font-weight: 700;
    color: var(--indigo);
    white-space: nowrap;
    background: var(--papier);
    padding: 0 4px;
  }

  .hors.gauche {
    left: 6px;
  }

  .hors.droite {
    right: 6px;
  }

  .hors.gauche::before {
    content: '\2190\00a0' / '';
  }

  .hors.droite::after {
    content: '\00a0\2192' / '';
  }

  /* ---------- Les commandes et la ligne d'état ---------- */

  .commandes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 14px;
    margin: 0 0 0.8em;
  }

  .bouton-relief {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 18px;
    line-height: 1.15;
    padding: 10px 16px;
  }

  .etat {
    margin: 0 0 0.8em;
    font-family: var(--titres);
    font-size: 18px;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }

  .insecable {
    white-space: nowrap;
  }

  /* ---------- Les positions, en bande, comme la suite de l'atelier de 0.1 ---------- */

  .titre-liste {
    margin: 0;
    font-size: 0.9em;
    color: var(--indigo-doux);
  }

  .positions {
    list-style: none;
    margin: 0.3em 0 0;
    padding: 10px 0 4px;
    border-top: 2px solid var(--indigo);
    border-bottom: 1px solid var(--brume);
    font-family: var(--titres);
    font-size: 16px;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }

  .positions li {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    vertical-align: top;
    max-width: 100%;
    margin: 0 4px 8px 0;
  }

  .positions [data-x] {
    padding: 1px 6px;
    background: var(--brume-claire);
    border-radius: 4px;
    overflow-wrap: anywhere;
  }

  .positions .courante [data-x] {
    font-weight: 700;
    box-shadow: inset 0 0 0 2px var(--indigo);
  }

  .rang {
    font-size: 12px;
    line-height: 1;
    margin-top: 4px;
    color: var(--indigo-doux);
  }

  @media (max-width: 720px) {
    /* Sur un téléphone, la courbe gagne en hauteur ce qu'elle perd en largeur. */
    .trace svg {
      aspect-ratio: 640 / 420;
    }

    .bouton-relief {
      font-size: 17px;
      padding: 9px 14px;
    }

    .etat {
      font-size: 17px;
    }
  }
</style>
