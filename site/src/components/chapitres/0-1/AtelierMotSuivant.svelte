<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 0.1 : le lecteur choisit un mot de départ et une
  // longueur, et voit les mots qui suivent ce mot dans le texte, puis la suite
  // que le programme écrit en prenant toujours le suivant le plus fréquent.
  // Tout est calculé par le jumeau exact du Python
  // (src/lib/partie-0/mot-suivant.ts), le même code que les paris du chapitre.
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <AtelierMotSuivant client:load texteInitial={TEXTE_DE_DEPART} motInitial="le" verrou="atelier" acquis="atelier" />
  // La longueur vit dans le canal « ms:longueur ». Le nombre reste désactivé
  // tant que le verrou n'est pas ouvert. Au premier changement du mot de
  // départ, l'atelier émet `forge:acquis` avec la clé `acquis`.
  //
  // Le contenu éventuel du composant (du texte du chapitre) s'affiche sous la
  // suite, avant le défi. Sans JavaScript, Astro rend l'atelier tel qu'il est à
  // l'arrivée : le texte, le tableau et la suite restent lisibles.
  import { untrack, type Snippet } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { compterSuivants, decouperMots, generer, premiereReprise, suivantsTries } from '../../../lib/partie-0/mot-suivant';
  import {
    DEFI_REUSSI,
    defiReussi,
    LONGUEUR_INITIALE,
    LONGUEUR_MAX,
    LONGUEUR_MIN,
    SEUIL_DU_DEFI,
  } from '../../../lib/partie-0/paris-0-1';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Le texte déjà écrit dans le champ, à l'arrivée. */
    texteInitial: string;
    /** Le mot de départ choisi à l'arrivée. */
    motInitial: string;
    /** Nom du verrou qui désactive le nombre tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné au premier changement du mot de départ. */
    acquis?: string;
    /** Texte du chapitre posé sous la suite. */
    children?: Snippet;
  }

  const { texteInitial, motInitial, verrou, acquis, children }: Props = $props();

  const FINE = '\u202F';
  /** Le canal de la longueur de la suite. */
  const CANAL_LONGUEUR = 'ms:longueur';
  /** Le tableau montre au plus ce nombre de suivants : les premiers, ceux qui comptent. */
  const SUIVANTS_MONTRES = 10;
  const idTexte = $props.id();

  // Le canal, le verrou et l'acquis sont lus une fois pour toutes, comme dans
  // NombreManipulable : un îlot ne change pas de canal en cours de route.
  const longueur = canal<number>(CANAL_LONGUEUR, LONGUEUR_INITIALE);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);

  let texte = $state(untrack(() => texteInitial));
  // Le mot choisi par le lecteur. S'il disparaît du texte, la suite part du
  // premier mot du nouveau texte (voir l'effet plus bas).
  let choisi = $state(untrack(() => motInitial));
  let annonce = $state('');

  const pluriel = (n: number, un: string, plusieurs: string) => (n > 1 ? plusieurs : un);

  // Tous les recalculs : le jumeau du Python, dans le même ordre que lui.
  const mots = $derived(decouperMots(texte));
  const suivants = $derived(compterSuivants(mots));
  // Les mots de départ possibles : chaque mot du texte une fois, dans l'ordre où il apparaît.
  const departs = $derived([...new Set(mots)]);
  const depart = $derived(departs.includes(choisi) ? choisi : (departs[0] ?? ''));
  const tries = $derived(suivantsTries(suivants.get(depart) ?? new Map<string, number>()));
  const suite = $derived(depart === '' ? [] : generer(suivants, depart, $longueur));
  const reprise = $derived(premiereReprise(suite));
  // Le mot où la suite s'arrête avant la longueur demandée, parce que rien ne le suit.
  const arret = $derived(suite.length > 0 && suite.length < $longueur ? suite[suite.length - 1] : null);
  // La première apparition du mot qui revient : la suite tourne en rond à partir d'elle.
  const origine = $derived(reprise === null ? -1 : suite.indexOf(suite[reprise]));
  // Le rang de la reprise, compté à partir de 1 comme les rangs affichés sous les mots.
  const rangReprise = $derived(reprise === null ? 0 : reprise + 1);
  const reussi = $derived(defiReussi(suite));
  const etatDuDefi = $derived.by(() => {
    if (reussi) return DEFI_REUSSI;
    if (suite.length === 0) return `Pas encore${FINE}: il faut d’abord un texte.`;
    if (reprise !== null) return `Pas encore${FINE}: la suite tourne en rond dès le mot ${reprise + 1}.`;
    if (arret !== null) {
      return `Pas encore${FINE}: la suite s’arrête au mot ${suite.length}, il en faut ${SEUIL_DU_DEFI}.`;
    }
    return `Pas encore${FINE}: demande au moins ${SEUIL_DU_DEFI} mots.`;
  });

  // Le mot choisi a disparu du texte : la suite part du premier mot du nouveau
  // texte, et on le dit (seulement quand le choix change). Un texte vide garde
  // le choix : si le mot revient, la suite repart de lui.
  $effect(() => {
    const nouveau = depart;
    const ancien = untrack(() => choisi);
    if (nouveau === '' || nouveau === ancien) return;
    choisi = nouveau;
    annonce = `«${FINE}${ancien}${FINE}» n’est plus dans le texte${FINE}: la suite part maintenant de «${FINE}${nouveau}${FINE}».`;
  });

  // Les lecteurs d'écran entendent la réussite du défi au moment où elle
  // arrive, et pas à chaque lettre tapée.
  let annonceDefi = $state('');
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const maintenant = reussi;
    if (maintenant === reussiAvant) return;
    reussiAvant = maintenant;
    annonceDefi = maintenant ? DEFI_REUSSI : '';
  });

  function choisir(evenement: Event): void {
    choisi = (evenement.currentTarget as HTMLSelectElement).value;
    annonce = '';
    if (cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  }
</script>

<div class="atelier" data-atelier>
  <div class="champ">
    <label for={idTexte}>Le texte que le programme lit{FINE}:</label>
    <textarea
      id={idTexte}
      data-test="ms-texte"
      rows="8"
      bind:value={texte}
      autocomplete="off"
      spellcheck="false"
      data-pagefind-ignore></textarea>
  </div>

  <p class="reglage">
    En partant de <span class="choix-mot"
      ><select data-test="ms-depart" aria-label="Mot de départ" value={depart} onchange={choisir} data-pagefind-ignore>
        {#each departs as mot (mot)}
          <option value={mot}>{mot}</option>
        {/each}
      </select></span
    >, génère <NombreManipulable
      canal={CANAL_LONGUEUR}
      min={LONGUEUR_MIN}
      max={LONGUEUR_MAX}
      initiale={LONGUEUR_INITIALE}
      etiquette="Nombre de mots de la suite"
      verrou={nomDuVerrou}
      testId="ms-longueur"
    />
    {pluriel($longueur, 'mot', 'mots')}.
  </p>
  <p class="annonce" role="status" data-test="ms-annonce">{annonce}</p>

  {#if tries.length > 0}
    <table class="suivants" data-test="ms-suivants" data-pagefind-ignore>
      <caption>Après «{FINE}<span data-mot={depart}>{depart}</span>{FINE}», ce texte met{FINE}:</caption>
      <thead>
        <tr><th scope="col">Mot suivant</th><th scope="col">Fois</th></tr>
      </thead>
      <tbody>
        {#each tries.slice(0, SUIVANTS_MONTRES) as [mot, n], i (mot)}
          <tr data-prediction={i === 0 ? '' : undefined}><td data-mot={mot}>{mot}</td><td>{n}</td></tr>
        {/each}
      </tbody>
    </table>
    {#if tries.length > SUIVANTS_MONTRES}
      <p class="autres">
        Et {tries.length - SUIVANTS_MONTRES}
        {pluriel(tries.length - SUIVANTS_MONTRES, 'autre mot, qui ne vient', 'autres mots, qui ne viennent')} pas avant
        ceux-là.
      </p>
    {/if}
    <p class="prediction">
      Le mot suivant le plus probable{FINE}: «{FINE}<span class="calcule" data-mot={tries[0][0]}>{tries[0][0]}</span
      >{FINE}».
    </p>
  {/if}

  {#if suite.length > 0}
    <p class="titre-suite">Une suite de {suite.length} {pluriel(suite.length, 'mot', 'mots')}{FINE}:</p>
    <ol class="suite" data-test="ms-suite" data-pagefind-ignore>
      {#each suite as mot, i (i)}
        <li
          class:b={i % 2 === 1}
          class:origine={i === origine}
          class:redite={reprise !== null && i >= reprise}
          data-mot={mot}
          data-reprise={i === reprise ? '' : undefined}
        >
          <span class="mot">{mot}</span><span class="rang" aria-hidden="true">{i + 1}</span>
        </li>
      {/each}
    </ol>
  {/if}
  {#if reprise !== null}
    <p class="reprise" data-test="ms-reprise">
      La suite revient sur «{FINE}<span data-mot={suite[reprise]}>{suite[reprise]}</span>{FINE}» au mot {rangReprise}{FINE}: à partir de là, elle tourne en rond.
    </p>
  {/if}
  {#if mots.length === 0}
    <p class="message" data-test="ms-message">Écris quelques phrases{FINE}: le programme a besoin de mots à compter.</p>
  {:else if arret !== null}
    <p class="message" data-test="ms-message">
      Rien ne suit «{FINE}<span data-mot={arret}>{arret}</span>{FINE}» dans ce texte{FINE}: la suite s’arrête là.
    </p>
  {/if}

  {#if children}
    <div class="texte-atelier">{@render children()}</div>
  {/if}

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>
      Trouve un départ dont la suite fait au moins {SEUIL_DU_DEFI} mots sans jamais revenir sur un mot déjà écrit.
      Tu peux changer le mot, le nombre de mots, ou même le texte.
    </p>
    {#if reussi}
      <p class="etat" data-test="ms-defi">{DEFI_REUSSI}</p>
    {:else}
      <p class="etat" data-test="ms-defi-etat">{etatDuDefi}</p>
    {/if}
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  /* Un mot du texte peut être très long (un texte collé, sans espace) : où
     qu'il apparaisse (liste, tableau, suite, messages), il passe à la ligne
     plutôt que d'élargir la page. */
  .atelier {
    margin: 1em 0 1.6em;
    overflow-wrap: anywhere;
  }

  /* Le champ du texte : jaune, puisqu'il se manipule, comme celui de 1.3. */
  .champ label {
    display: block;
    margin-bottom: 4px;
  }

  textarea {
    display: block;
    box-sizing: border-box;
    width: 100%;
    font-size: 17px;
    line-height: 1.5;
    color: var(--indigo);
    background: var(--soleil-pale);
    border: 0;
    border-bottom: 3px solid var(--soleil);
    border-radius: 6px 6px 0 0;
    padding: 8px 10px;
    resize: vertical;
  }

  textarea:hover {
    background: var(--soleil-survol);
  }

  /* Le focus se voit au trait du bas, qui passe du jaune à l'encre. */
  textarea:focus-visible {
    outline: none;
    background: var(--soleil-survol);
    border-bottom-color: var(--indigo);
  }

  .reglage {
    margin: 1em 0 0;
    line-height: 1.9;
  }

  /* Le mot de départ : une pastille jaune, comme le nombre de la même phrase. */
  .choix-mot {
    position: relative;
    display: inline-block;
    max-width: 100%;
    vertical-align: baseline;
  }

  select {
    appearance: none;
    /* Aussi large que le mot choisi (et non que le plus long mot du texte), là où le navigateur le sait. */
    field-sizing: content;
    max-width: min(100%, 13em);
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 0.95em;
    line-height: 1.25;
    color: var(--indigo);
    background: var(--soleil);
    border: 0;
    border-radius: 6px;
    box-shadow: 0 2px 0 var(--indigo);
    padding: 0 24px 0 8px;
    cursor: pointer;
  }

  select:hover {
    background: var(--soleil-vif);
  }

  /* La flèche de la liste, dessinée par la police : aucune image. */
  .choix-mot::after {
    content: '\25BE';
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 14px;
    color: var(--indigo);
    pointer-events: none;
  }

  .annonce {
    margin: 0;
    font-family: var(--titres);
    font-size: 16px;
    color: var(--indigo-doux);
  }

  .annonce:not(:empty) {
    margin-top: 6px;
  }

  /* Le tableau des suivants : typographié, sans cadre. */
  .suivants {
    border-collapse: collapse;
    margin: 1.2em 0 0.4em;
    min-width: min(100%, 18em);
    max-width: 100%;
  }

  .suivants caption {
    text-align: left;
    caption-side: top;
    padding-bottom: 6px;
  }

  .suivants th {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 15px;
    color: var(--indigo-doux);
    text-align: left;
    padding: 0 24px 4px 0;
    border-bottom: 2px solid var(--indigo);
  }

  .suivants th:last-child,
  .suivants td:last-child {
    text-align: right;
    padding-right: 0;
  }

  .suivants td {
    padding: 3px 24px 3px 0;
    border-bottom: 1px solid var(--brume);
    overflow-wrap: anywhere;
  }

  .suivants td:last-child {
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
  }

  .suivants [data-prediction] td {
    font-weight: 700;
  }

  .autres {
    margin: 0;
    font-size: 16px;
    color: var(--indigo-doux);
  }

  .prediction {
    margin: 0.6em 0 0;
  }

  .calcule {
    font-family: var(--titres);
    font-weight: 700;
  }

  .titre-suite {
    margin: 1.2em 0 0;
  }

  /* La suite : une bande de mots aux teintes alternées, comme les jetons de 1.3,
     avec le rang de chaque mot dessous. */
  .suite {
    list-style: none;
    margin: 0.3em 0 0.4em;
    padding: 14px 0 6px;
    border-top: 2px solid var(--indigo);
    border-bottom: 1px solid var(--brume);
    font-size: 24px;
    line-height: 1.2;
    font-variation-settings: 'opsz' 36;
  }

  .suite li {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    vertical-align: top;
    min-width: 0;
    max-width: 100%;
    margin: 0 3px 8px 0;
  }

  .mot {
    max-width: 100%;
    padding: 0 5px;
    background: var(--teinte-a);
    border-radius: 4px;
    line-height: 1.32;
    overflow-wrap: anywhere;
  }

  .b .mot {
    background: var(--teinte-b);
  }

  /* Le mot qui revient, à sa première apparition et à sa reprise : cerclé d'encre. */
  .origine .mot,
  [data-reprise] .mot {
    box-shadow: inset 0 0 0 2px var(--indigo);
  }

  /* À partir de la reprise, la suite répète des mots déjà écrits : ils passent en encre douce. */
  .redite .mot {
    color: var(--indigo-doux);
  }

  .rang {
    font-family: var(--titres);
    font-weight: 500;
    font-size: 12px;
    line-height: 1;
    margin-top: 5px;
    color: var(--indigo-doux);
    font-variant-numeric: tabular-nums;
  }

  .reprise {
    margin: 0.4em 0 0;
  }

  .message {
    margin: 0.6em 0 0;
    font-style: italic;
    color: var(--indigo-doux);
    overflow-wrap: anywhere;
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
    textarea {
      font-size: 16px;
    }

    .suite {
      font-size: 20px;
    }
  }
</style>
