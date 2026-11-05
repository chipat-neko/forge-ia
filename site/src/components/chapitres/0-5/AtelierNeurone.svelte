<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du neurone du chapitre 0.5 : un neurone à seuil à deux entrées,
  // x1 et x2, réglé par trois nombres jaunes (w1, w2 et b, de −2 à 2 par pas
  // de 0,5), et une porte à imiter, choisie par trois bascules : ET, OU ou OU
  // exclusif. Dessous, le dessin : le carré de 0 à 1 et ses 4 points (plein
  // pour une bonne réponse 1, vide pour 0), la droite où la somme pondérée
  // vaut 0, et le côté où le neurone répond 1, en fond brume ; une coche menthe
  // sur chaque point bien classé, une croix corail sur chaque point mal
  // classé. Le texte le dit aussi, point par point, puis le bilan.
  //
  // Les réponses et les comptes viennent du jumeau du Python
  // (src/lib/partie-0/neurone.ts), les phrases, le dessin, l'acquis et le défi
  // d'atelier-neurone.ts.
  //
  // À placer dans le MDX avec client:load, sans verrou au chapitre 0.5 :
  //   <AtelierNeurone client:load acquis="neurone" />
  // Les réglages vivent dans les canaux « neu:w1 », « neu:w2 » et « neu:b ». Avec
  // un verrou, les nombres et les bascules restent désactivés tant qu'il n'est
  // pas ouvert. La première fois que les 4 points sont classés, sur ET ou sur OU,
  // par un réglage du lecteur, l'atelier émet `forge:acquis` avec la clé `acquis`.
  //
  // Sans JavaScript, Astro rend l'atelier tel qu'il est à l'arrivée : la porte
  // ET, w1 = w2 = 1 et b = 0, soit 2 points sur 4 bien classés.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../../lib/canal';
  import {
    B_DEPART,
    bilan,
    defiReussi,
    DEFI_NEURONE_REUSSI,
    DOMAINE_MAX,
    DOMAINE_MIN,
    droite,
    ecrirePoint,
    ecrireReglage,
    etatDesPoints,
    etatDuDefi,
    gagneNeurone,
    morceauxDuPoint,
    NB_POINTS,
    noterReussite,
    PORTE_DEPART,
    PORTES_ATELIER,
    REGLAGE_MAX,
    REGLAGE_MIN,
    REGLAGE_PAS,
    regionUn,
    remarque,
    W1_DEPART,
    W2_DEPART,
    type Coordonnees,
    type Reussites,
  } from '../../../lib/partie-0/atelier-neurone';
  import type { Porte } from '../../../lib/partie-0/neurone';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive l'atelier tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné aux 4 points classés, sur ET ou sur OU, par un réglage du lecteur. */
    acquis?: string;
  }

  const { verrou, acquis }: Props = $props();

  const FINE = '\u202F';
  const id = $props.id();

  // Les canaux, le verrou et l'acquis sont lus une fois pour toutes, comme dans
  // NombreManipulable : un îlot ne change pas de canal en cours de route.
  const w1 = canal<number>('neu:w1', W1_DEPART);
  const w2 = canal<number>('neu:w2', W2_DEPART);
  const b = canal<number>('neu:b', B_DEPART);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let porte: Porte = $state(PORTE_DEPART);

  const etats = $derived(etatDesPoints($w1, $w2, $b, porte));
  const compte = $derived(etats.filter((e) => e.juste).length);
  const nomPorte = $derived(PORTES_ATELIER.find((p) => p.porte === porte)?.nom ?? '');
  const region = $derived(regionUn($w1, $w2, $b));
  const ligne = $derived(droite($w1, $w2, $b));
  const remarqueDuDessin = $derived(remarque($w1, $w2, $b));
  const gagne = $derived(gagneNeurone($w1, $w2, $b, porte));

  // ---------- Le dessin ----------

  // Le plan de DOMAINE_MIN à DOMAINE_MAX, COTE pixels de côté, avec une marge
  // à gauche et en bas pour les graduations et les noms des axes.
  const COTE = 240;
  const GAUCHE = 34;
  const HAUT = 8;
  const LARGEUR = GAUCHE + COTE + 8;
  const HAUTEUR = HAUT + COTE + 32;
  const UNITE = COTE / (DOMAINE_MAX - DOMAINE_MIN);
  const RAYON = 9;
  /** Le décalage de la coche ou de la croix, en haut à droite de son point. */
  const DECALAGE = 16;

  const px = (x: number) => GAUCHE + (x - DOMAINE_MIN) * UNITE;
  const py = (y: number) => HAUT + COTE - (y - DOMAINE_MIN) * UNITE;
  /** Un nombre de pixels écrit court, pour les attributs du SVG. */
  const f = (x: number) => String(Math.round(x * 100) / 100);
  const enPixels = (c: Coordonnees) => `${f(px(c[0]))},${f(py(c[1]))}`;

  const pointsRegion = $derived(region.map(enPixels).join(' '));

  const nomDuDessin = $derived.by(() => {
    const plan =
      `Le plan des entrées x1 et x2, de ${ecrireReglage(DOMAINE_MIN)} à ${ecrireReglage(DOMAINE_MAX)}, ` +
      `avec les ${NB_POINTS} points du carré de 0 à 1 pour la porte ${nomPorte}`;
    const trait =
      ligne !== null
        ? `, et la droite où la somme du neurone vaut 0${FINE}: d’un côté il répond 1, de l’autre 0.`
        : `. ${remarqueDuDessin ?? ''}`;
    return `${plan}${trait} ${bilan(compte)}`;
  });

  // ---------- L'acquis, le défi et les annonces ----------

  // L'acquis : la première fois que gagneNeurone devient vrai.
  let gagneAvant = untrack(() => gagne);
  $effect(() => {
    const maintenant = gagne;
    if (maintenant === gagneAvant) return;
    gagneAvant = maintenant;
    if (maintenant && cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  });

  // Le défi : les portes classées en entier, pour chaque paire de poids.
  let reussites: Reussites = $state({});
  $effect(() => {
    const avant = untrack(() => reussites);
    const apres = noterReussite(avant, $w1, $w2, $b, porte);
    if (apres !== avant) reussites = apres;
  });
  const reussi = $derived(defiReussi(reussites));
  const etatDefi = $derived(etatDuDefi(reussites, $w1, $w2));

  // Les moments qui comptent, annoncés aux lecteurs d'écran : les 4 points classés, puis le défi.
  let annonce = $state('');
  let compteAvant = untrack(() => compte);
  $effect(() => {
    const maintenant = compte;
    if (maintenant === compteAvant) return;
    const avant = compteAvant;
    compteAvant = maintenant;
    if (maintenant === NB_POINTS) annonce = bilan(maintenant);
    else if (avant === NB_POINTS) annonce = '';
  });
  let annonceDefi = $state('');
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const maintenant = reussi;
    if (maintenant === reussiAvant) return;
    reussiAvant = maintenant;
    annonceDefi = maintenant ? DEFI_NEURONE_REUSSI : '';
  });
</script>

{#snippet reglage(nomDuCanal: string, initiale: number, etiquette: string, testId: string)}
  <NombreManipulable
    canal={nomDuCanal}
    min={REGLAGE_MIN}
    max={REGLAGE_MAX}
    pas={REGLAGE_PAS}
    {initiale}
    {etiquette}
    verrou={nomDuVerrou}
    {testId}
    texte={ecrireReglage}
  />
{/snippet}

{#snippet marque(juste: boolean)}
  <circle class="halo" r="8" />
  {#if juste}
    <path class="marque-juste" d="M-4.5,0.5L-1.2,3.8L4.8,-3.6" />
  {:else}
    <path class="marque-faux" d="M-3.8,-3.8L3.8,3.8M3.8,-3.8L-3.8,3.8" />
  {/if}
{/snippet}

<div class="atelier-neurone" data-atelier="neurone">
  <div class="portes-neurone" role="group" aria-labelledby="{id}-porte">
    <span class="intitule" id="{id}-porte">La porte{FINE}:</span>
    {#each PORTES_ATELIER as p (p.porte)}
      <button
        type="button"
        class="bascule-soleil"
        aria-pressed={porte === p.porte}
        data-test="neu-porte"
        data-porte={p.porte}
        disabled={!actif}
        onclick={() => (porte = p.porte)}>{p.nom}</button
      >
    {/each}
  </div>

  <p class="reglage-neurone" data-test="neu-reglage">
    <span class="paire">w1 = {@render reglage('neu:w1', W1_DEPART, 'Le poids w1', 'neu-w1')},</span>
    <span class="paire">w2 = {@render reglage('neu:w2', W2_DEPART, 'Le poids w2', 'neu-w2')}</span>
    et <span class="paire">b = {@render reglage('neu:b', B_DEPART, 'Le biais b', 'neu-b')}.</span>
  </p>

  <div class="vue-neurone">
    <figure class="figure-neurone">
      <svg class="dessin-neurone" viewBox="0 0 {LARGEUR} {HAUTEUR}" role="img" aria-label={nomDuDessin} data-test="neu-dessin">
        <rect class="fond" x={GAUCHE} y={HAUT} width={COTE} height={COTE} />
        {#if pointsRegion !== ''}
          <polygon class="region" points={pointsRegion} data-test="neu-region" />
        {/if}
        <rect class="carre-unite" x={px(0)} y={py(1)} width={UNITE} height={UNITE} />
        <rect class="bord" x={GAUCHE} y={HAUT} width={COTE} height={COTE} />
        {#each [0, 1] as v (v)}
          <text class="graduation" x={px(v)} y={HAUT + COTE + 14}>{v}</text>
          <text class="graduation graduation-y" x={GAUCHE - 7} y={py(v)}>{v}</text>
        {/each}
        <text class="nom-axe" x={GAUCHE + COTE} y={HAUT + COTE + 27}>x1</text>
        <text class="nom-axe nom-axe-y" x={GAUCHE - 7} y={HAUT + 10}>x2</text>
        {#if ligne !== null}
          <line
            class="droite-neurone"
            data-test="neu-droite"
            x1={f(px(ligne[0][0]))}
            y1={f(py(ligne[0][1]))}
            x2={f(px(ligne[1][0]))}
            y2={f(py(ligne[1][1]))}
          />
        {/if}
        {#each etats as e, i (i)}
          <circle class={e.attendu === 1 ? 'point-un' : 'point-zero'} cx={px(e.point[0])} cy={py(e.point[1])} r={RAYON} />
        {/each}
        {#each etats as e, i (i)}
          <g
            data-test="neu-marque"
            data-point={e.point.join(',')}
            data-juste={e.juste ? 'oui' : 'non'}
            transform="translate({f(px(e.point[0]) + DECALAGE)} {f(py(e.point[1]) - DECALAGE)})"
            >{@render marque(e.juste)}</g
          >
        {/each}
      </svg>
      <figcaption class="legende-neurone">
        <span><svg class="cle" viewBox="0 0 16 16" aria-hidden="true"><rect class="region" x="1" y="1" width="14" height="14" /></svg
          >le neurone répond 1</span
        >
        <span><svg class="cle" viewBox="0 0 16 16" aria-hidden="true"><circle class="point-un" cx="8" cy="8" r="6" /></svg>il faut 1</span>
        <span><svg class="cle" viewBox="0 0 16 16" aria-hidden="true"><circle class="point-zero" cx="8" cy="8" r="6" /></svg>il faut 0</span>
      </figcaption>
    </figure>

    <div class="lecture-neurone">
      {#if remarqueDuDessin !== null}
        <p class="remarque-neurone" data-test="neu-remarque">{remarqueDuDessin}</p>
      {/if}
      <ul class="points-neurone" data-test="neu-points" aria-label="Les {NB_POINTS} points, pour la porte {nomPorte}">
        {#each etats as e, i (i)}
          <li data-point={ecrirePoint(e.point)} data-juste={e.juste ? 'oui' : 'non'}>
            <svg class="cle-marque" viewBox="-9 -9 18 18" aria-hidden="true">{@render marque(e.juste)}</svg
            >{#each morceauxDuPoint(e) as m, k (k)}{#if k > 0}{' '}{/if}<span class="morceau">{m}</span>{/each}
          </li>
        {/each}
      </ul>
      <p class="bilan-neurone" class:complet={compte === NB_POINTS} data-test="neu-bilan">{bilan(compte)}</p>
      <p class="vh" role="status">{annonce}</p>
    </div>
  </div>

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>Avec les mêmes w1 et w2, classe les {NB_POINTS} points de ET, puis ceux de OU, en ne changeant que b.</p>
    <p class="etat" data-test={reussi ? 'neu-defi' : 'neu-defi-etat'}>{etatDefi}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .atelier-neurone {
    margin: 1em 0 1.6em;
  }

  /* La porte : trois bascules soulignées de jaune (.bascule-soleil, src/styles/commandes.css) ;
     celle qui est choisie est en soleil. Ici, leur police et leurs marges intérieures. */
  .portes-neurone {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    margin: 0 0 0.4em;
  }

  .bascule-soleil {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 19px;
    line-height: 1.3;
    padding: 4px 8px;
    min-height: 32px;
  }

  .reglage-neurone {
    margin: 0 0 0.6em;
    line-height: 1.9;
  }

  /* « w1 = 1, » ne se coupe pas : la phrase passe à la ligne entre deux réglages. */
  .paire {
    white-space: nowrap;
  }

  /* La virgule ou le point colle au nombre qui le précède : sa marge de droite, faite pour loger
     le chevron, est réduite. */
  .paire > :global(.nombre) {
    margin-right: 2px;
  }

  /* Le dessin, puis ce qu'il montre en mots ; côte à côte sur un écran assez large. */
  .vue-neurone {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 10px 26px;
  }

  .figure-neurone {
    margin: 0;
    flex: 0 1 282px;
    min-width: 0;
  }

  .dessin-neurone {
    display: block;
    width: 100%;
    max-width: 282px;
    height: auto;
  }

  .fond {
    fill: var(--papier);
  }

  /* Le côté où le neurone répond 1. */
  .region {
    fill: var(--brume);
  }

  .bord {
    fill: none;
    stroke: var(--brume);
    stroke-width: 1;
  }

  /* Le carré de 0 à 1, où vivent les points : un trait de décor. */
  .carre-unite {
    fill: none;
    stroke: var(--lavande);
    stroke-width: 1.5;
    stroke-dasharray: 5 4;
  }

  .droite-neurone {
    stroke: var(--indigo);
    stroke-width: 2.5;
    stroke-linecap: round;
  }

  /* Un point dont la bonne réponse est 1 : plein ; 0 : vide. */
  .point-un {
    fill: var(--indigo);
  }

  .point-zero {
    fill: var(--papier);
    stroke: var(--indigo);
    stroke-width: 2.5;
  }

  .halo {
    fill: var(--papier);
  }

  .marque-juste,
  .marque-faux {
    fill: none;
    stroke-width: 2.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .marque-juste {
    stroke: var(--menthe);
  }

  .marque-faux {
    stroke: var(--corail);
  }

  .graduation,
  .nom-axe {
    font-family: var(--titres);
    font-size: 13px;
    fill: var(--indigo-doux);
    dominant-baseline: central;
  }

  .graduation {
    font-variant-numeric: tabular-nums;
    text-anchor: middle;
  }

  .graduation-y,
  .nom-axe-y {
    text-anchor: end;
  }

  .nom-axe {
    font-family: var(--texte);
    font-style: italic;
    font-size: 15px;
    text-anchor: end;
  }

  .legende-neurone {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 14px;
    margin-top: 4px;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.3;
    color: var(--indigo-doux);
  }

  .legende-neurone > span {
    white-space: nowrap;
  }

  .cle {
    display: inline-block;
    width: 14px;
    height: 14px;
    margin-right: 5px;
    vertical-align: -2px;
    overflow: visible;
  }

  .lecture-neurone {
    flex: 1 1 240px;
    min-width: 0;
  }

  .remarque-neurone {
    margin: 0 0 0.5em;
    font-style: italic;
    color: var(--indigo-doux);
  }

  .points-neurone {
    list-style: none;
    margin: 0;
    padding: 0;
    font-size: 0.92em;
    line-height: 1.45;
  }

  .points-neurone li {
    margin: 0 0 0.35em;
    padding-left: 24px;
    text-indent: -24px;
  }

  /* Une phrase de point ne se coupe qu'entre ses morceaux : « il faut 0, » reste d'un bloc. */
  .morceau {
    white-space: nowrap;
  }

  .cle-marque {
    display: inline-block;
    width: 18px;
    height: 18px;
    margin-right: 6px;
    vertical-align: -3px;
    overflow: visible;
  }

  .bilan-neurone {
    margin: 0.5em 0 0;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 19px;
  }

  .bilan-neurone.complet {
    color: var(--menthe);
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme dans les ateliers de 0.1 à 0.4. */
  .defi {
    margin-top: 1.2em;
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
    .bascule-soleil {
      font-size: 18px;
    }

    .bilan-neurone {
      font-size: 18px;
    }
  }
</style>
