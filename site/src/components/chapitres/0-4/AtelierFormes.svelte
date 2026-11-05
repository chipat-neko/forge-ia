<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier des formes du chapitre 0.4 : deux formes, A et B, réglées par
  // des nombres jaunes (de 1 à 3 dimensions, chacune de taille 1 à 6), et une
  // opération, A + B (la diffusion) ou A @ B (le produit matriciel). Dessous, la
  // grille des deux formes alignées par la droite, le résultat, et une phrase
  // qui dit ce qui s'étire, ce qui doit être égal, ou pourquoi PyTorch refuse.
  //
  // Le résultat vient du jumeau des formes (src/lib/partie-0/formes.ts, vérifié
  // contre PyTorch), la grille et les phrases d'atelier-formes.ts.
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <AtelierFormes client:load verrou="formes" acquis="formes" />
  // Les réglages vivent dans les canaux « formes:na » et « formes:nb » (le
  // nombre de dimensions), « formes:a0 » à « formes:a2 » et « formes:b0 » à
  // « formes:b2 » (les tailles ; la forme prend les premières). Les nombres et
  // les bascules restent désactivés tant que le verrou n'est pas ouvert. Au
  // premier produit A @ B possible avec un A de 3 dimensions, l'atelier émet
  // `forge:acquis` avec la clé `acquis`.
  //
  // Sans JavaScript, Astro rend l'atelier tel qu'il est à l'arrivée :
  // (3, 1) + (4,), qui donne (3, 4).
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../../lib/canal';
  import {
    A_DEPART,
    B_DEPART,
    DEFI_FORMES_REUSSI,
    defiReussi,
    DIMENSIONS_MAX,
    DIMENSIONS_MIN,
    ecrireResultat,
    etatDuDefi,
    expliquer,
    forme,
    gagneFormes,
    grille,
    resultat,
    TAILLE_MAX,
    TAILLE_MIN,
    TAILLES_A,
    TAILLES_B,
    type Case,
    type Operation,
  } from '../../../lib/partie-0/atelier-formes';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive l'atelier tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné au premier produit A @ B possible avec un A de 3 dimensions. */
    acquis?: string;
  }

  const { verrou, acquis }: Props = $props();

  const FINE = '\u202F';
  const id = $props.id();
  /** Le rang d'une dimension, pour le nom lu par les lecteurs d'écran. */
  const RANGS = ['première', 'deuxième', 'troisième'];

  // Les canaux, le verrou et l'acquis sont lus une fois pour toutes, comme dans
  // NombreManipulable : un îlot ne change pas de canal en cours de route.
  const na = canal<number>('formes:na', A_DEPART.length);
  const nb = canal<number>('formes:nb', B_DEPART.length);
  const a0 = canal<number>('formes:a0', TAILLES_A[0]);
  const a1 = canal<number>('formes:a1', TAILLES_A[1]);
  const a2 = canal<number>('formes:a2', TAILLES_A[2]);
  const b0 = canal<number>('formes:b0', TAILLES_B[0]);
  const b1 = canal<number>('formes:b1', TAILLES_B[1]);
  const b2 = canal<number>('formes:b2', TAILLES_B[2]);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let op: Operation = $state('plus');

  const a = $derived(forme([$a0, $a1, $a2], $na));
  const b = $derived(forme([$b0, $b1, $b2], $nb));
  const r = $derived(resultat(a, b, op));
  const g = $derived(grille(a, b, op));
  const explication = $derived(expliquer(a, b, op));
  const nomOperation = $derived(op === 'plus' ? 'A + B' : 'A @ B');
  const reussi = $derived(defiReussi(a, b, op));
  const gagne = $derived(gagneFormes(a, b, op));
  const etatDefi = $derived(etatDuDefi(a, b, op));

  // L'acquis : au premier produit A @ B possible avec un A de 3 dimensions.
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

  // La réussite du défi est annoncée aux lecteurs d'écran au moment où elle arrive.
  let annonceDefi = $state('');
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const maintenant = reussi;
    if (maintenant === reussiAvant) return;
    reussiAvant = maintenant;
    annonceDefi = maintenant ? DEFI_FORMES_REUSSI : '';
  });
</script>

{#snippet taille(nom: 'a' | 'b', i: number, initiale: number)}
  <NombreManipulable
    canal="formes:{nom}{i}"
    min={TAILLE_MIN}
    max={TAILLE_MAX}
    {initiale}
    etiquette="Taille de la {RANGS[i]} dimension de {nom.toUpperCase()}"
    verrou={nomDuVerrou}
    testId="formes-{nom}-{i}"
  />
{/snippet}

{#snippet laForme(nom: 'a' | 'b', n: number, tailles: readonly number[])}
  <span class="forme"
    >({#each tailles.slice(0, n) as t, i (i)}{#if i > 0}{', '}{/if}{@render taille(nom, i, t)}{/each}{#if n === 1},{/if})</span
  >
{/snippet}

{#snippet cellule(c: Case, i: number)}
  <td
    data-colonne={i}
    data-etire={c.etire ? 'oui' : undefined}
    data-souligne={c.souligne ? 'oui' : undefined}
    data-conflit={c.conflit ? 'oui' : undefined}
    data-manque={c.manque ? 'oui' : undefined}
    >{#if c.taille !== null}<span
        class="taille"
        class:etire={c.etire}
        class:souligne={c.souligne}
        class:conflit={c.conflit}
        class:manque={c.manque}>{c.taille}</span
      >{#if c.manque}<span class="vh">, dimension qui manque, comptée pour 1</span>{/if}{#if c.etire}<span class="vh"
          >, s’étire</span
        >{/if}{#if c.souligne}<span class="vh"
          >{c.conflit ? ', différente de l’autre taille soulignée' : ', égale à l’autre taille soulignée'}</span
        >{/if}{/if}</td
  >
{/snippet}

{#snippet rangee(cle: string, nom: string, cases: Case[])}
  <tr data-rangee={cle}>
    <th scope="row">{nom}</th>
    {#each cases as c, i (i)}{@render cellule(c, i)}{/each}
  </tr>
{/snippet}

<div class="atelier-formes" data-atelier="formes">
  <p class="reglage" data-test="formes-dims">
    Dimensions{FINE}: <NombreManipulable
      canal="formes:na"
      min={DIMENSIONS_MIN}
      max={DIMENSIONS_MAX}
      initiale={A_DEPART.length}
      etiquette="Nombre de dimensions de A"
      verrou={nomDuVerrou}
      testId="formes-a-dims"
    />
    pour A, <NombreManipulable
      canal="formes:nb"
      min={DIMENSIONS_MIN}
      max={DIMENSIONS_MAX}
      initiale={B_DEPART.length}
      etiquette="Nombre de dimensions de B"
      verrou={nomDuVerrou}
      testId="formes-b-dims"
    />
    pour B.
  </p>
  <p class="reglage" data-test="formes-phrase">
    <span class="paire">A a la forme {@render laForme('a', $na, [$a0, $a1, $a2])}</span>{FINE}; <span class="paire"
      >B a la forme {@render laForme('b', $nb, [$b0, $b1, $b2])}</span
    >.
  </p>

  <div class="operation" role="group" aria-labelledby="{id}-operation">
    <span class="intitule" id="{id}-operation">L’opération{FINE}:</span>
    <button
      type="button"
      class="bascule-soleil"
      aria-pressed={op === 'plus'}
      data-test="formes-op-plus"
      disabled={!actif}
      onclick={() => (op = 'plus')}>A + B</button
    >
    <button
      type="button"
      class="bascule-soleil"
      aria-pressed={op === 'produit'}
      data-test="formes-op-produit"
      disabled={!actif}
      onclick={() => (op = 'produit')}>A @ B</button
    >
  </div>

  <!-- La légende de la grille est un paragraphe, pas un <caption> : un caption ne passe pas la largeur
       du tableau, et se couperait en trois lignes. -->
  <p class="titre-grille" id="{id}-grille">Les deux formes, alignées par la droite{FINE}:</p>
  <table class="grille" data-test="formes-grille" aria-labelledby="{id}-grille" data-pagefind-ignore>
    <tbody>
      {@render rangee('a', 'A', g.a)}
      {@render rangee('b', 'B', g.b)}
      <tr data-rangee="resultat" class="ligne-resultat">
        <th scope="row">{nomOperation}</th>
        {#if r === null}
          <td colspan={DIMENSIONS_MAX} class="impossible">impossible</td>
        {:else if r.length === 0}
          <!-- Un nombre seul (vecteur @ vecteur) n'a aucune dimension : la rangée l'écrit (), comme le résultat. -->
          <td colspan={DIMENSIONS_MAX} class="nombre-seul">()</td>
        {:else}
          {#each g.resultat ?? [] as c, i (i)}{@render cellule(c, i)}{/each}
        {/if}
      </tr>
    </tbody>
  </table>

  <p class="resultat">
    {nomOperation}
    {r === null ? 'est' : 'a la forme'}
    <strong data-test="formes-resultat">{ecrireResultat(r)}</strong>.
  </p>
  <p class="explication" data-test="formes-explication">{explication}</p>

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>Trouve deux formes à 3 dimensions qui se multiplient{FINE}: A @ B doit être possible.</p>
    {#if reussi}
      <p class="etat" data-test="formes-defi">{DEFI_FORMES_REUSSI}</p>
    {:else}
      <p class="etat" data-test="formes-defi-etat">{etatDefi}</p>
    {/if}
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .atelier-formes {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.3em;
    line-height: 1.9;
  }

  /* « A a la forme (3, 1) » ne se coupe pas : la phrase passe à la ligne entre les deux formes. */
  .paire {
    white-space: nowrap;
  }

  /* Dans une forme, la virgule colle au nombre qui la précède : sa marge de droite,
     faite pour loger le chevron, est réduite, sauf pour le dernier nombre d'une
     forme de plusieurs dimensions, que suit la parenthèse. */
  .forme > :global(.nombre) {
    margin-right: 1px;
  }

  .forme > :global(.nombre:last-of-type:not(:first-of-type)) {
    margin-right: 11px;
  }

  /* L'opération : deux bascules soulignées de jaune (.bascule-soleil, src/styles/commandes.css) ;
     celle qui est choisie est en soleil. Ici, leur police et leurs marges intérieures. */
  .operation {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    margin: 0.6em 0 0;
  }

  .bascule-soleil {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 19px;
    line-height: 1.3;
    padding: 4px 8px;
    min-height: 32px;
  }

  /* La grille : les tailles de A et de B, une colonne par dimension, alignées par la
     droite, et le résultat sous un trait, comme une addition posée. */
  .titre-grille {
    margin: 1.1em 0 6px;
  }

  .grille {
    border-collapse: collapse;
    margin: 0 0 0.6em;
  }

  .grille th {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    color: var(--indigo-doux);
    text-align: left;
    white-space: nowrap;
    padding: 4px 18px 4px 0;
  }

  .grille td {
    min-width: 3.2em;
    padding: 4px 3px;
    text-align: center;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 22px;
    font-variant-numeric: tabular-nums;
  }

  .ligne-resultat th,
  .ligne-resultat td {
    border-top: 2px solid var(--indigo);
    padding-top: 8px;
  }

  .grille td.nombre-seul {
    text-align: right;
  }

  .grille td.impossible {
    font-family: var(--texte);
    font-weight: 400;
    font-style: italic;
    font-size: 18px;
    color: var(--indigo-doux);
    text-align: right;
  }

  /* Une taille : une pastille au trait invisible, qui se voit quand elle s'étire, est
     soulignée ou bloque l'opération. */
  .taille {
    display: inline-block;
    min-width: 1.4em;
    padding: 0 6px;
    line-height: 1.4;
    border: 2px solid transparent;
    border-radius: 6px;
  }

  /* Une taille 1 qui s'étire : un trait lavande en pointillé. */
  .taille.etire {
    border: 2px dashed var(--lavande);
  }

  /* Une dimension qui manque, comptée pour 1 : en encre douce. */
  .taille.manque {
    font-weight: 500;
    color: var(--indigo-doux);
  }

  /* Pour A @ B, les deux tailles qui doivent être égales : soulignées, en menthe si elles le sont. */
  .taille.souligne {
    text-decoration: underline;
    text-decoration-thickness: 3px;
    text-underline-offset: 5px;
    text-decoration-color: var(--menthe);
  }

  /* Une taille qui bloque l'opération : en corail. */
  .taille.conflit {
    border-color: var(--corail);
  }

  /* Deux tailles soulignées différentes : soulignées et encadrées de corail, comme les conflits de
     A + B. La différence ne tient donc pas qu'à la couleur du trait. */
  .taille.souligne.conflit {
    text-decoration-color: var(--corail);
  }

  .resultat {
    margin: 0.2em 0 0;
    font-family: var(--titres);
    font-size: 19px;
  }

  .resultat strong {
    font-weight: 700;
  }

  .explication {
    margin: 0.4em 0 0;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme dans les ateliers de 0.1 et 0.2. */
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
    .grille td {
      font-size: 20px;
      min-width: 2.8em;
    }

    .bascule-soleil {
      font-size: 18px;
    }
  }
</style>
