<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier des paramètres du chapitre 1.4 : une phrase à régler. « Avec
  // [dim] nombres par jeton, [couches] blocs et [têtes] têtes, ton IA aurait N
  // paramètres : … ». Dessous, la répartition par famille, et les cinq tailles
  // de forge en repères, chacune à essayer d'un clic.
  //
  // Le compte est celui du jumeau de forge (nombreParametres, ton-ia.ts ;
  // repartitionParametres, parametres.ts), et les phrases viennent de
  // paris-1-4.ts, où elles sont testées.
  //
  // Les têtes ne prennent que les nombres que forge accepte : ceux qui partagent
  // les dim nombres en parts égales et paires (nombresDeTetes). Le nombre jaune
  // des têtes règle donc un rang dans cette liste, et montre le nombre de têtes.
  // Quand la largeur change, il garde le nombre de têtes s'il est encore
  // possible, sinon prend le plus proche (tetesVoisines). La largeur se règle de
  // même par son rang, de 64 en 64 : les sauts de dix crans (Page précédente,
  // Page suivante) restent sur la grille.
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <AtelierParametres client:load verrou="atelier" acquis="atelier" />
  // Les réglages vivent dans les canaux « par:dim », « par:couches » et
  // « par:tetes », désactivés tant que le verrou n'est pas ouvert. Au premier
  // changement d'un réglage, l'atelier émet `forge:acquis` avec la clé `acquis`.
  // Sans JavaScript, Astro rend l'atelier tel qu'il est à l'arrivée : ton IA.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../../lib/canal';
  import { formaterQuantite } from '../../../lib/calculateur/formats';
  import { CLES_FORGE, NOMS_TAILLES, PRESETS_FORGE, type CleForge } from '../../../lib/calculateur/ton-ia';
  import { nombre, pourcent } from '../../../lib/nombres';
  import { nombresDeTetes } from '../../../lib/partie-1/parametres';
  import {
    COUCHES_MAX,
    COUCHES_MIN,
    DIM_MAX,
    DIM_MIN,
    etatDeLAtelier,
    etatDuDefi,
    nomDeLaFamille,
    PAS_DIM,
    phraseDeLAtelier,
    placeParmiLesTailles,
    tetesVoisines,
  } from '../../../lib/partie-1/paris-1-4';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive les réglages tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné au premier changement d'un réglage. */
    acquis?: string;
    /** La taille de forge à l'arrivée : très grand, ton IA. */
    depart?: CleForge;
  }

  const { verrou, acquis, depart = 'tres_grand' }: Props = $props();
  const FINE = '\u202F';
  const CANAL_DIM = 'par:dim';
  const CANAL_COUCHES = 'par:couches';
  const CANAL_TETES = 'par:tetes';

  const DEPART = PRESETS_FORGE[untrack(() => depart)];
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  /** Le rang d'une largeur sur la grille de 64 en 64 (1 pour 64), et la largeur d'un rang. */
  const rangDeDim = (dim: number) => dim / PAS_DIM;
  const dimDuRang = (rang: number) => rang * PAS_DIM;

  // Les canaux, lus une fois pour toutes, comme dans NombreManipulable.
  const rangDim = canal<number>(CANAL_DIM, rangDeDim(DEPART.dim));
  const couches = canal<number>(CANAL_COUCHES, DEPART.couches);
  const rangTetes = canal<number>(CANAL_TETES, nombresDeTetes(DEPART.dim).indexOf(DEPART.tetes));

  // Le nombre de têtes suit la largeur : à chaque nouvelle largeur, le même s'il est encore
  // possible, sinon le plus proche. Les abonnements aux canaux sont appelés tout de suite, au
  // moment du changement, avant que la page ne se redessine : le réglage reste toujours cohérent.
  let dimCourante = dimDuRang(rangDim.get());
  let tetesCourantes = nombresDeTetes(dimCourante)[rangTetes.get()];
  let reglagesChanges = false;

  function premierChangement(): void {
    if (reglagesChanges) return;
    reglagesChanges = true;
    if (cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  }

  $effect(() =>
    untrack(() => {
      const sansDim = rangDim.subscribe((rang) => {
        const dim = dimDuRang(rang);
        if (dim === dimCourante) return;
        dimCourante = dim;
        tetesCourantes = tetesVoisines(dim, tetesCourantes);
        rangTetes.set(nombresDeTetes(dim).indexOf(tetesCourantes));
        premierChangement();
      });
      const sansTetes = rangTetes.subscribe((rang) => {
        const t = nombresDeTetes(dimCourante)[rang];
        if (t === undefined || t === tetesCourantes) return;
        tetesCourantes = t;
        premierChangement();
      });
      let couchesAvant = couches.get();
      const sansCouches = couches.subscribe((c) => {
        if (c === couchesAvant) return;
        couchesAvant = c;
        premierChangement();
      });
      return () => {
        sansDim();
        sansTetes();
        sansCouches();
      };
    }),
  );

  const dim = $derived(dimDuRang($rangDim));
  const possibles = $derived(nombresDeTetes(dim));
  const tetes = $derived(possibles[Math.min(Math.max(0, $rangTetes), possibles.length - 1)]);
  const etat = $derived(etatDeLAtelier(dim, $couches, tetes));
  const defi = $derived(etatDuDefi(etat));
  const familles = $derived(Object.entries(etat.repartition) as [keyof typeof etat.repartition, number][]);

  const texteDim = (rang: number) => nombre(dimDuRang(rang));
  const texteTetes = $derived((rang: number) => nombre(possibles[Math.min(Math.max(0, rang), possibles.length - 1)]));

  /** Une part en pour cent : sans décimale à partir de 1 %, assez de décimales en dessous pour ne pas écrire « 0 % ». */
  const part = (p: number) => pourcent(p, p >= 0.01 ? 0 : p >= 0.001 ? 1 : 2);

  /** Essaie une taille de forge : ses trois réglages d'un coup. */
  function essayer(cle: CleForge): void {
    if (!actif) return;
    const f = PRESETS_FORGE[cle];
    rangDim.set(rangDeDim(f.dim));
    couches.set(f.couches);
    rangTetes.set(nombresDeTetes(f.dim).indexOf(f.tetes));
  }

  // Les lecteurs d'écran entendent le nouveau total quand un réglage change, et la réussite du
  // défi au moment où elle arrive.
  let annonce = $state('');
  let totalAvant = untrack(() => etat.total);
  $effect(() => {
    const total = etat.total;
    if (total === totalAvant) return;
    totalAvant = total;
    annonce = `${untrack(() => etat.totalTexte)} paramètres.`;
  });
  let annonceDefi = $state('');
  let defiAvant = untrack(() => defi.reussi);
  $effect(() => {
    const reussi = defi.reussi;
    if (reussi === defiAvant) return;
    defiAvant = reussi;
    annonceDefi = reussi ? untrack(() => defi.texte) : '';
  });
</script>

<div class="atelier-parametres" data-atelier-parametres>
  <p class="phrase">
    Avec <NombreManipulable
      canal={CANAL_DIM}
      min={rangDeDim(DIM_MIN)}
      max={rangDeDim(DIM_MAX)}
      initiale={rangDeDim(DEPART.dim)}
      etiquette="Nombres par jeton"
      verrou={nomDuVerrou}
      testId="par-dim"
      texte={texteDim}
    /> nombres par jeton, <NombreManipulable
      canal={CANAL_COUCHES}
      min={COUCHES_MIN}
      max={COUCHES_MAX}
      initiale={DEPART.couches}
      etiquette="Nombre de blocs"
      verrou={nomDuVerrou}
      testId="par-couches"
      texte={nombre}
    />
    {$couches > 1 ? 'blocs' : 'bloc'} et <NombreManipulable
      canal={CANAL_TETES}
      min={0}
      max={possibles.length - 1}
      initiale={nombresDeTetes(DEPART.dim).indexOf(DEPART.tetes)}
      etiquette="Nombre de têtes"
      verrou={nomDuVerrou}
      testId="par-tetes"
      texte={texteTetes}
    />
    {tetes > 1 ? 'têtes' : 'tête'}, <span data-test="par-phrase">{phraseDeLAtelier(etat)}</span>
  </p>
  <p class="detail">
    {tetes > 1 ? 'Chaque tête lit' : 'La tête lit'}
    {nombre(dim / tetes)} des {nombre(dim)} nombres.
    <span data-test="par-place">{placeParmiLesTailles(etat)}</span>
  </p>
  <p class="vh" role="status">{annonce}</p>

  <table class="repartition" data-test="par-repartition">
    <caption>Où sont les paramètres{FINE}:</caption>
    <thead>
      <tr>
        <th scope="col">Famille</th>
        <th scope="col" class="nombre">Paramètres</th>
        <th scope="col" class="nombre">Part</th>
      </tr>
    </thead>
    <tbody>
      {#each familles as [famille, n] (famille)}
        <tr data-famille={famille} data-parametres={String(n)}>
          <th scope="row">{nomDeLaFamille(famille)}</th>
          <td class="nombre">{nombre(n)}</td>
          <td class="nombre">{part(n / etat.total)}</td>
        </tr>
      {/each}
    </tbody>
    <tfoot>
      <tr>
        <th scope="row">Total</th>
        <td class="nombre" data-test="par-total">{etat.totalTexte}</td>
        <td></td>
      </tr>
    </tfoot>
  </table>

  <table class="tailles" data-test="par-tailles">
    <caption>Les cinq tailles de forge, à essayer{FINE}:</caption>
    <thead>
      <tr>
        <th scope="col">Taille</th>
        <th scope="col" class="nombre">Nombres par jeton</th>
        <th scope="col" class="nombre">Blocs</th>
        <th scope="col" class="nombre">Paramètres</th>
      </tr>
    </thead>
    <tbody>
      {#each CLES_FORGE as cle (cle)}
        {@const f = PRESETS_FORGE[cle]}
        <tr>
          <th scope="row">
            <button
              type="button"
              class="bascule-soleil"
              data-preset={cle}
              aria-pressed={etat.preset === cle}
              aria-disabled={!actif}
              onclick={() => essayer(cle)}>{NOMS_TAILLES[cle]}</button
            >
          </th>
          <td class="nombre">{nombre(f.dim)}</td>
          <td class="nombre">{nombre(f.couches)}</td>
          <td class="nombre">{formaterQuantite(f.parametres)}</td>
        </tr>
      {/each}
    </tbody>
  </table>

  <div class="defi" class:reussi={defi.reussi} data-defi>
    <h3>Défi</h3>
    <p>Trouve une taille sous 100 millions de paramètres où les MLP pèsent plus que le plongement.</p>
    <p class="etat" data-test="par-defi">{defi.texte}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .atelier-parametres {
    margin: 1em 0 1.6em;
  }

  .phrase {
    margin: 0;
    line-height: 1.95;
  }

  .detail {
    margin: 0.5em 0 0;
    color: var(--indigo-doux);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.2em 0 0;
    font-size: 17px;
  }

  caption {
    text-align: left;
    caption-side: top;
    padding-bottom: 6px;
    font-size: 19px;
  }

  th,
  td {
    padding: 4px 10px 4px 0;
    text-align: left;
    vertical-align: middle;
    border-top: 1px solid var(--brume);
  }

  thead th {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 14px;
    color: var(--indigo-doux);
    border-top: 0;
    border-bottom: 2px solid var(--indigo);
  }

  tbody th {
    font-weight: 400;
  }

  .nombre {
    text-align: right;
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  td:last-child,
  th:last-child {
    padding-right: 0;
  }

  tfoot th,
  tfoot td {
    border-top: 2px solid var(--indigo);
    font-weight: 700;
  }

  .tailles .bascule-soleil {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 16px;
    min-height: 28px;
    padding: 0 8px;
    margin-left: -8px;
    white-space: nowrap;
  }

  .tailles .bascule-soleil[aria-disabled='true'] {
    cursor: default;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme en 1.1. */
  .defi {
    margin-top: 1.4em;
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
    table {
      font-size: 16px;
    }

    thead th {
      font-size: 13px;
      white-space: normal;
    }
  }
</style>
