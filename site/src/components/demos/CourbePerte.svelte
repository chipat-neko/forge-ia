<script lang="ts">
  // La courbe de l'erreur du mini-modèle, dessinée à la main en SVG (aucune
  // bibliothèque de graphiques) : l'erreur de chaque pas d'entraînement
  // (moyennée par petits paquets), les points de validation, la ligne du
  // hasard, et l'essai d'avant en pointillé (le fantôme), pour comparer.
  //
  // Le SVG ne porte que les tracés. Les textes (graduations, « hasard »,
  // « hors échelle », légende) sont du HTML posé par-dessus : ils gardent leur
  // taille de 13 px quelle que soit la largeur de la courbe. Les traits ne
  // s'épaississent pas non plus quand la courbe s'étire (non-scaling-stroke).
  //
  // Le SVG a un nom accessible qui donne l'erreur de validation au départ et
  // au dernier point ; la liste des erreurs, sous la courbe, donne le détail.
  import {
    cheminCourbe,
    echelleCourbe,
    graduations,
    moyennesParPaquets,
    sortieDeLEchelle,
    taillePaquet,
    type Point,
  } from '../../lib/courbe';
  import { formaterPerte, nombre } from '../../lib/nombres';
  import type { Courbe } from '../../lib/mini-modele/pilote';

  interface Props {
    /** L'erreur de chaque pas d'entraînement (le pas p est à l'indice p − 1). */
    pertes: number[];
    /** Les erreurs de validation, du pas 0 au dernier point. */
    validations: Point[];
    pasTotal: number;
    /** L'erreur du pur hasard (ln V) : la ligne « hasard », et l'échelle. */
    perteHasard: number;
    /** L'essai d'avant, en pointillé ; null s'il n'y en a pas. */
    fantome: Courbe | null;
    /** Le début du nom accessible : « Courbe de l'erreur ». */
    etiquette: string;
    /** Ce que la légende dit du fantôme : « l'essai d'avant, au taux de 0,01 ». */
    legendeFantome?: string;
    /** Vrai quand l'erreur a explosé (le Worker l'a dit) : la courbe est hors échelle. */
    explose?: boolean;
  }

  const {
    pertes,
    validations,
    pasTotal,
    perteHasard,
    fantome,
    etiquette,
    legendeFantome = 'l’essai d’avant',
    explose = false,
  }: Props = $props();

  const FINE = '\u202F';
  // 120 points au plus : des paquets de 25 pas pour 3 000 pas, de 5 pour 600.
  // L'erreur d'un seul pas (8 prénoms) varie beaucoup d'un pas à l'autre : la
  // moyenne d'un paquet montre la tendance. La taille dépend du nombre total
  // de pas, pas de l'avancement : le lissage reste le même du début à la fin
  // de l'entraînement.
  const POINTS_MAX = 120;

  const e = $derived(echelleCourbe(pasTotal, perteHasard));
  const taille = $derived(taillePaquet(pasTotal, POINTS_MAX));
  const trace = $derived(cheminCourbe(moyennesParPaquets(pertes, taille), e));
  const traceFantome = $derived(fantome === null ? null : cheminCourbe(moyennesParPaquets(fantome.pertes, taille), e));
  // Chaque point de validation est un trait de longueur nulle à bouts ronds :
  // un rond de 6 px de diamètre (rayon 3) à toute largeur de courbe.
  const dPoints = $derived(
    validations
      .map((v) => cheminCourbe([v], e).d)
      .filter((d) => d !== '')
      .map((d) => `${d}h0`)
      .join(''),
  );

  // Où la courbe sort par le haut : le premier pas dont l'erreur brute (avant
  // les moyennes, qui noient un pas qui explose et ignorent NaN) est non finie
  // ou au-dessus du cadre. Une explosion annoncée par le Worker la marque
  // aussi, au dernier pas. Le fantôme peut sortir du cadre lui aussi.
  const sortieCourante = $derived(sortieDeLEchelle(pertes, validations, e) ?? (explose ? Math.max(pertes.length, 1) : null));
  const sortieFantome = $derived(fantome === null ? null : sortieDeLEchelle(fantome.pertes, fantome.validations, e));

  // Les positions en pourcentage du cadre, pour les textes posés par-dessus.
  const enX = (pas: number) => (Math.min(Math.max(pas, 0), e.xMax) / e.xMax) * 100;
  const enY = (perte: number) => 100 - (Math.min(Math.max(perte, e.yMin), e.yMax) / (e.yMax - e.yMin)) * 100;
  const sur = (x: number, decimales = 0) => (Number.isFinite(x) ? nombre(x, decimales) : '?');

  const gradX = $derived(graduations(e.xMax, 3));
  const gradY = $derived(graduations(e.yMax, 5).filter((v) => v < e.yMax));
  const yHasard = $derived((e.hauteur * (1 - (perteHasard - e.yMin) / (e.yMax - e.yMin))).toFixed(1));

  // La position du repère « hors échelle », en pourcentage de la largeur.
  const sortie = $derived.by(() => {
    const pas = [sortieCourante, sortieFantome].filter((p): p is number => p !== null);
    return pas.length === 0 ? null : enX(Math.min(...pas));
  });

  const nomAccessible = $derived.by(() => {
    const premier = validations[0];
    const dernier = validations[validations.length - 1];
    const morceaux: string[] = [];
    if (premier !== undefined) morceaux.push(`${formaterPerte(premier.perte)} au pas ${sur(premier.pas)}`);
    if (dernier !== undefined && dernier !== premier) morceaux.push(`${formaterPerte(dernier.perte)} au pas ${sur(dernier.pas)}`);
    let texte = morceaux.length > 0 ? `${etiquette}${FINE}: ${morceaux.join(', ')}.` : `${etiquette}.`;
    if (sortieCourante !== null) texte += ' La courbe sort du cadre par le haut.';
    if (sortieFantome !== null) texte += ' L’essai d’avant, en pointillé, sort du cadre par le haut.';
    const finFantome = fantome?.validations[fantome.validations.length - 1];
    if (finFantome !== undefined) {
      texte += ` En pointillé, ${legendeFantome}${FINE}: ${formaterPerte(finFantome.perte)} au pas ${sur(finFantome.pas)}.`;
    }
    return texte;
  });
</script>

<figure class="courbe-perte">
  <div class="cadre">
    <span class="titre-axe titre-y" aria-hidden="true">erreur</span>
    <div class="graduations-y" aria-hidden="true">
      {#each gradY as v (v)}
        <span style:top="{enY(v)}%">{sur(v)}</span>
      {/each}
    </div>
    <div class="trace">
      <svg
        viewBox="0 0 {e.largeur} {e.hauteur}"
        preserveAspectRatio="none"
        role="img"
        aria-label={nomAccessible}
        data-test="courbe"
      >
        {#each gradY.filter((v) => v > 0) as v (v)}
          <line class="grille" x1="0" x2={e.largeur} y1={(e.hauteur * enY(v)) / 100} y2={(e.hauteur * enY(v)) / 100} />
        {/each}
        <line class="hasard" x1="0" x2={e.largeur} y1={yHasard} y2={yHasard} />
        {#if traceFantome !== null && traceFantome.d !== ''}
          <path class="fantome" d={traceFantome.d} data-test="courbe-fantome" />
        {/if}
        <!-- Les points de validation d'abord : la ligne d'entraînement passe par-dessus, et reste visible. -->
        {#if dPoints !== ''}
          <path class="validation" d={dPoints} />
        {/if}
        {#if trace.d !== ''}
          <path class="entrainement" d={trace.d} data-test="courbe-entrainement" />
        {/if}
      </svg>
      <span class="repere-hasard" style:top="{enY(perteHasard)}%" aria-hidden="true">hasard</span>
      {#if sortie !== null}
        <span class="hors-echelle" style:--x="{sortie}%" data-test="hors-echelle">hors échelle</span>
      {/if}
    </div>
  </div>
  <div class="graduations-x" aria-hidden="true">
    {#each gradX as v (v)}
      <span style:left="{enX(v)}%">{sur(v)}</span>
    {/each}
  </div>
  <span class="titre-axe titre-x" aria-hidden="true">pas</span>
  <figcaption class="legende">
    <span><svg class="cle" viewBox="0 0 24 8" aria-hidden="true"><line class="entrainement" x1="1" x2="23" y1="4" y2="4" /></svg>
      l’erreur pendant l’entraînement</span
    >
    <span><svg class="cle" viewBox="0 0 24 8" aria-hidden="true"><path class="validation" d="M12,4h0" /></svg>
      l’erreur sur des prénoms jamais vus</span
    >
    {#if fantome !== null}
      <span><svg class="cle" viewBox="0 0 24 8" aria-hidden="true"><line class="fantome" x1="1" x2="23" y1="4" y2="4" /></svg>
        {legendeFantome}</span
      >
    {/if}
  </figcaption>
</figure>

<style>
  .courbe-perte {
    margin: 0.6em 0 1.2em;
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

  /* Les graduations des bords restent dans le cadre. */
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
    aspect-ratio: 640 / 280;
    overflow: visible;
    border-bottom: 1px solid var(--indigo-doux);
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

  .hasard,
  .fantome {
    stroke: var(--lavande);
    stroke-width: 2;
    stroke-dasharray: 6 5;
  }

  .entrainement {
    stroke: var(--indigo);
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
  }

  .validation {
    stroke: var(--indigo);
    stroke-width: 6;
    stroke-linecap: round;
  }


  .repere-hasard {
    position: absolute;
    right: 0;
    transform: translateY(-120%);
    padding: 0 2px;
    background: var(--papier);
  }

  .hors-echelle {
    position: absolute;
    top: 0;
    /* Jamais sous le titre « erreur », même quand la courbe sort près du pas 0. */
    left: clamp(2.2em, var(--x), calc(100% - 7em));
    transform: translateY(-110%);
    font-weight: 700;
    color: var(--corail);
    white-space: nowrap;
  }

  .hors-echelle::before {
    content: '\2191\00a0';
  }

  .legende {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 18px;
    margin-top: 8px;
  }

  .legende > span {
    white-space: nowrap;
  }

  .cle {
    display: inline-block;
    width: 24px;
    height: 8px;
    max-width: none;
    margin-right: 4px;
    vertical-align: middle;
    overflow: visible;
  }

  @media (max-width: 720px) {
    /* Sur un téléphone, la courbe gagne en hauteur ce qu'elle perd en largeur. */
    .trace svg {
      aspect-ratio: 640 / 400;
    }

    .legende > span {
      white-space: normal;
    }
  }
</style>
