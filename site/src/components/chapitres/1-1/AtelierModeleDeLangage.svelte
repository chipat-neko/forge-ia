<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 1.1 : le lecteur écrit un début de texte, règle le
  // nombre de caractères de contexte (0 à 6) et la température, et voit ce que
  // le modèle tirerait ensuite (les barres), puis la suite qu'il écrit,
  // caractère par caractère. Les barres et la suite racontent le même tirage :
  // celui du jumeau exact du Python (tirage et generer, dans
  // src/lib/partie-1/ngrammes.ts), avec le même recul quand le contexte n'a
  // jamais été vu. L'état vient d'etatDeLAtelier (paris-1-1.ts), comme les
  // messages et le défi.
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <AtelierModeleDeLangage client:load texteInitial={CONTEXTE_INITIAL} verrou="atelier" acquis="atelier" />
  // Le nombre vit dans le canal « ml:n ». Il reste désactivé tant que le verrou
  // n'est pas ouvert. Au premier changement du nombre, l'atelier émet
  // `forge:acquis` avec la clé `acquis`.
  //
  // Le contenu éventuel du composant (du texte du chapitre) s'affiche sous la
  // suite, avant le défi. Sans JavaScript, Astro rend l'atelier tel qu'il est à
  // l'arrivée : les barres et la suite du départ restent lisibles.
  import { untrack, type Snippet } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { decimalesUtiles, nombre, pourcent } from '../../../lib/nombres';
  import { compterParOrdre, couper, ORDRE_MAX } from '../../../lib/partie-1/ngrammes';
  import {
    BARRES_MONTREES,
    etatDeLAtelier,
    etatDuDefi,
    GRAINE_INITIALE,
    LONGUEUR_SUITE,
    messageBoucle,
    N_DU_DEFI,
    N_INITIAL,
    N_MAX,
    N_MIN,
    nomDuBlanc,
    TEMPERATURE_INITIALE,
    TEMPERATURES_ATELIER,
    visible,
  } from '../../../lib/partie-1/paris-1-1';
  import { ALPHABET, TEXTE_DU_SITE } from '../../../lib/partie-1/texte-1-1';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Le début de texte déjà écrit dans le champ, à l'arrivée. */
    texteInitial: string;
    /** Nom du verrou qui désactive le nombre tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné au premier changement du nombre de caractères de contexte. */
    acquis?: string;
    /** Texte du chapitre posé sous la suite. */
    children?: Snippet;
  }

  const { texteInitial, verrou, acquis, children }: Props = $props();

  const FINE = '\u202F';
  const CANAL_N = 'ml:n';
  const idSaisie = $props.id();

  // Le canal, le verrou et l'acquis sont lus une fois pour toutes, comme dans
  // NombreManipulable : un îlot ne change pas de canal en cours de route.
  const n = canal<number>(CANAL_N, N_INITIAL);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);

  // Le modèle : les comptes de tous les ordres, de 0 à 6, sur les 90 premiers %
  // du texte du site. Calculés une seule fois : le texte ne change pas.
  const COMPTES = compterParOrdre(couper(TEXTE_DU_SITE)[0], ORDRE_MAX);

  let contexte = $state(untrack(() => texteInitial));
  let temperature = $state(TEMPERATURE_INITIALE);
  let graine = $state(GRAINE_INITIALE);
  let annonce = $state('');

  const etat = $derived(etatDeLAtelier(COMPTES, ALPHABET, contexte, $n, temperature, graine));
  const barres = $derived(etat.chances.slice(0, BARRES_MONTREES));
  const autres = $derived(etat.chances.length - barres.length);
  const defi = $derived(etatDuDefi(etat, $n));
  // Le message de la boucle décrit la suite : il va sous elle ; les autres décrivent le contexte.
  const boucle = $derived(etat.messages.includes(messageBoucle()));
  const messagesDuContexte = $derived(etat.messages.filter((m) => m !== messageBoucle()));
  // La suite écrite après le contexte : generer rend le contexte, puis les caractères tirés.
  const tires = $derived(etat.suite.slice(contexte.length));

  const texteT = (t: number) => nombre(t, decimalesUtiles(t));

  /** Une chance en pour cent : sans décimale à partir de 10 %, une en dessous, et jamais « 0 % » pour une chance réelle. */
  function chance(p: number): string {
    if (p >= 0.1) return pourcent(p);
    if (p >= 0.001) return pourcent(p, 1);
    return `moins de ${pourcent(0.001, 1)}`;
  }

  /** « «␣appe␣» » : un texte cité, ses blancs rendus visibles. */
  const cite = (s: string) => `«${FINE}${visible(s)}${FINE}»`;

  const titreDesBarres = $derived.by(() => {
    const k = etat.chances.length;
    const debut = etat.ordre === 0 ? 'Sans regarder le contexte' : `Après ${cite(etat.regarde)}`;
    if (k === 1) return `${debut}, le modèle prend toujours le même caractère${FINE}:`;
    return `${debut}, le modèle tire au sort parmi ${nombre(k)} caractères${FINE}:`;
  });

  /** Ce que les lecteurs d'écran entendent quand le nombre ou la température change : le caractère en tête. */
  function decrireLaTete(): string {
    if (etat.court) return '';
    const [c, p] = etat.chances[0];
    const nom = nomDuBlanc(c);
    return `${titreDesBarres.replace(/\u202F:$/, '')}${FINE}; en tête, ${nom ?? cite(c)}, ${chance(p)}.`;
  }

  // Le nombre a changé (et seulement lui) : l'acquis est gagné, une fois.
  let nPrecedent = untrack(() => $n);
  $effect(() => {
    const nActuel = $n;
    if (nActuel === nPrecedent) return;
    nPrecedent = nActuel;
    annonce = untrack(decrireLaTete);
    if (cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  });

  function choisirTemperature(t: number): void {
    if (t === temperature) return;
    temperature = t;
    annonce = decrireLaTete();
  }

  function tirerEncore(): void {
    graine += 1;
    annonce =
      temperature === 0
        ? `À température 0, il n’y a pas de hasard${FINE}: la suite reste la même.`
        : `Nouvelle suite, tirée avec la graine ${nombre(graine)}.`;
  }

  // Les lecteurs d'écran entendent la réussite du défi au moment où elle
  // arrive, et pas à chaque lettre tapée.
  let annonceDefi = $state('');
  let defiAvant = untrack(() => etat.defi);
  $effect(() => {
    const reussi = etat.defi;
    if (reussi === defiAvant) return;
    defiAvant = reussi;
    annonceDefi = reussi ? untrack(() => defi) : '';
  });
</script>

<div class="atelier" data-atelier>
  <div class="ligne-saisie">
    <label for={idSaisie}>Le début de ton texte{FINE}:</label>
    <input
      id={idSaisie}
      data-test="ml-contexte"
      type="text"
      bind:value={contexte}
      autocomplete="off"
      spellcheck="false"
      enterkeyhint="done"
      data-pagefind-ignore
    />
  </div>

  <p class="reglage">
    Avec <NombreManipulable
      canal={CANAL_N}
      min={N_MIN}
      max={N_MAX}
      initiale={N_INITIAL}
      etiquette="Nombre de caractères de contexte"
      verrou={nomDuVerrou}
      testId="ml-n"
    />
    {$n > 1 ? 'caractères' : 'caractère'} de contexte, à la température
    <span class="temperatures" role="group" aria-label="Température">
      {#each TEMPERATURES_ATELIER as t (t)}
        <button
          type="button"
          class="bascule-soleil"
          data-test={`ml-t-${t}`}
          aria-pressed={t === temperature}
          onclick={() => choisirTemperature(t)}>{texteT(t)}</button
        >
      {/each}</span
    >
  </p>

  <!-- Les messages sur le contexte, au-dessus des barres ; celui de la boucle, sous la suite qu'il décrit. -->
  <div class="messages" role="status">
    {#each messagesDuContexte as message (message)}
      <p class="message" data-test="ml-message">{message}</p>
    {/each}
  </div>
  <p class="vh" role="status">{annonce}</p>

  {#if !etat.court}
    <div class="tirage" data-test="ml-distribution" data-ordre={etat.ordre} data-pagefind-ignore>
      <table>
        <caption>{titreDesBarres}</caption>
        <tbody>
          {#each barres as [c, p] (c)}
            <tr data-caractere={c} data-chance={String(p)}>
              <th scope="row">
                {#if nomDuBlanc(c) === null}
                  <span class="car">{c}</span>
                {:else}
                  <span class="car nom">{nomDuBlanc(c)}</span>
                {/if}
              </th>
              <td class="piste"><span class="barre" style:width={`${(p * 100).toFixed(2)}%`}></span></td>
              <td class="chance">{chance(p)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      {#if autres > 0}
        <p class="autres">Et {nombre(autres)} {autres > 1 ? 'autres caractères, moins probables' : 'autre caractère, moins probable'}.</p>
      {/if}
    </div>

    <p class="titre-suite">
      La suite, {nombre(LONGUEUR_SUITE)} caractères tirés un à un{FINE}:
      <button type="button" class="bouton-relief" data-test="ml-tirer" onclick={tirerEncore}>Tirer encore</button>
    </p>
    <p class="suite" data-test="ml-suite" data-pagefind-ignore><span class="depart">{contexte}</span>{tires}</p>
    <p class="graine">Graine du hasard{FINE}: {nombre(graine)}.</p>
  {/if}
  <div class="messages" role="status">
    {#if boucle}
      <p class="message" data-test="ml-message">{messageBoucle()}</p>
    {/if}
  </div>

  {#if children}
    <div class="texte-atelier">{@render children()}</div>
  {/if}

  <div class="defi" class:reussi={etat.defi} data-defi>
    <h3>Défi</h3>
    <p>
      Trouve un contexte de {N_DU_DEFI} caractères après lequel le caractère le plus probable est une espace{FINE}:
      règle le nombre jaune sur {N_DU_DEFI}, puis écris ce contexte à la fin de ton texte.
    </p>
    <p class="etat" data-test="ml-defi">{defi}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  /* Un texte collé, sans espace, passe à la ligne plutôt que d'élargir la page. */
  .atelier {
    margin: 1em 0 1.6em;
    overflow-wrap: anywhere;
  }

  /* Le champ du texte : jaune, puisqu'il se manipule, comme celui de 1.3. */
  .ligne-saisie {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin: 0 0 1em;
  }

  .ligne-saisie label {
    white-space: nowrap;
  }

  .ligne-saisie input {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-style: italic;
    color: var(--indigo);
    background: var(--soleil-pale);
    border: 0;
    border-bottom: 3px solid var(--soleil);
    border-radius: 6px 6px 0 0;
    padding: 3px 8px 4px;
  }

  .ligne-saisie input:hover {
    background: var(--soleil-survol);
  }

  /* Le focus se voit au trait du bas, qui passe du jaune à l'encre. */
  .ligne-saisie input:focus-visible {
    outline: none;
    background: var(--soleil-survol);
    border-bottom-color: var(--indigo);
  }

  .reglage {
    margin: 0;
    line-height: 1.9;
  }

  /* Les quatre températures : des bascules soulignées de soleil, dans la phrase. */
  .temperatures {
    white-space: nowrap;
  }

  .temperatures .bascule-soleil {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 0.95em;
    min-width: 2em;
    min-height: 26px;
    padding: 0 6px;
    margin: 0 2px;
    font-variant-numeric: tabular-nums;
  }

  .message {
    margin: 0.6em 0 0;
    font-style: italic;
    color: var(--indigo-doux);
  }

  /* Les chances du tirage : un tableau typographié, une barre indigo doux par caractère. */
  .tirage {
    margin: 1em 0 0;
  }

  .tirage table {
    width: 100%;
    border-collapse: collapse;
  }

  .tirage caption {
    text-align: left;
    caption-side: top;
    padding-bottom: 6px;
  }

  /* Des lignes aussi hautes que le caractère : sa case et sa barre, centrées l'une sur l'autre. */
  .tirage th,
  .tirage td {
    line-height: 1.3;
    vertical-align: middle;
  }

  .tirage th {
    width: 6.5em;
    padding: 3px 12px 3px 0;
    text-align: left;
    font-weight: 400;
    border-top: 1px solid var(--brume);
  }

  .tirage tr:first-child th,
  .tirage tr:first-child td {
    border-top: 2px solid var(--indigo);
  }

  .tirage td {
    padding: 3px 0;
    border-top: 1px solid var(--brume);
  }

  .car {
    display: inline-block;
    min-width: 1.4em;
    padding: 0 5px;
    background: var(--teinte-a);
    border-radius: 4px;
    text-align: center;
    font-size: 21px;
    line-height: 1.3;
  }

  tr:nth-child(even) .car {
    background: var(--teinte-b);
  }

  /* Un blanc ne se voit pas : on écrit son nom, plus petit. */
  .car.nom {
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.95;
    color: var(--indigo-doux);
  }

  .tirage td.piste {
    width: 100%;
  }

  .barre {
    display: block;
    height: 10px;
    min-width: 1px;
    background: var(--indigo-doux);
    border-radius: 2px;
  }

  .tirage td.chance {
    padding-left: 12px;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 16px;
    font-variant-numeric: tabular-nums;
    text-align: right;
    white-space: nowrap;
  }

  .autres {
    margin: 4px 0 0;
    font-size: 16px;
    color: var(--indigo-doux);
  }

  .titre-suite {
    margin: 1.2em 0 0.4em;
    line-height: 2;
  }

  .titre-suite .bouton-relief {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 16px;
    padding: 2px 12px;
    margin-left: 4px;
    min-height: 32px;
  }

  /* La suite, en chasse fixe, comme une sortie de terminal : le début écrit par le lecteur en encre douce. */
  .suite {
    margin: 0;
    padding: 14px 16px;
    background: var(--brume-claire);
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 15px;
    line-height: 1.6;
    font-variant-ligatures: none;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .depart {
    color: var(--indigo-doux);
  }

  .graine {
    margin: 4px 0 0;
    font-family: var(--titres);
    font-size: 14px;
    color: var(--indigo-doux);
  }

  /* Le texte du chapitre posé sous la suite : détaché des résultats calculés. */
  .texte-atelier {
    margin-top: 1.2em;
  }

  .texte-atelier :global(p) {
    margin: 0 0 0.6em;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme en 1.3. */
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
    .ligne-saisie {
      display: block;
    }

    .ligne-saisie label {
      display: block;
      margin-bottom: 4px;
    }

    .ligne-saisie input {
      width: 100%;
    }

    .tirage th {
      width: 5.5em;
    }

    .suite {
      font-size: 14px;
      padding: 12px 14px;
    }
  }
</style>
