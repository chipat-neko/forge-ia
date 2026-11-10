<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier des QCM du chapitre 1.6 : les questions de MMMLU que la version
  // d'une heure de ton IA a notées (mesures/qcm-mini.json du projet 1.6), une à
  // la fois. Le lecteur lit la question telle qu'elle l'a lue, puis parie sur
  // la réponse qu'elle préfère. Alors seulement, les barres se dévoilent : le
  // score normalisé de chaque réponse (sa vraisemblance divisée par ses
  // octets), la préférence de ton IA, et la bonne réponse, en menthe si ton IA
  // l'a trouvée, en corail sinon. « Question suivante » ; à la fin, le compte :
  // ton IA, et ce que donne le hasard en moyenne.
  //
  // Les choix, les barres, le compte et le défi viennent de paris-1-6.ts, où
  // ils sont testés. Le relevé est lu par le chapitre à la construction et
  // passé ici : ce composant ne lit aucun fichier.
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <AtelierQcm client:load qcm={QCM} acquis="qcm" />
  // L'acquis est gagné au compte final, quand les questions ont toutes leur pari.
  // Sans JavaScript, Astro rend la première question dévoilée : sa question, ses
  // réponses, leurs barres et la bonne réponse restent lisibles.
  import { tick, untrack } from 'svelte';
  import { nombre } from '../../../lib/nombres';
  import type { QcmExemples } from '../../../lib/partie-1/evaluation';
  import { choixPrefere, compteDuQcm, etatDuDefi, largeursDesBarres, texteDuCompte } from '../../../lib/partie-1/paris-1-6';
  import type { DetailAcquis } from '../../../scripts/chapitre';

  interface Props {
    /** Le relevé des QCM notés (qcm-<nom>.json), lu par le chapitre. */
    qcm: QcmExemples;
    /** Clé de l'acquis gagné au compte final. */
    acquis?: string;
  }

  const { qcm, acquis }: Props = $props();
  const FINE = '\u202F';
  const LETTRES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

  // Le relevé ne change pas en cours de route : tout ce qui en dépend se calcule une fois.
  const QCM = untrack(() => qcm);
  const cleAcquis = untrack(() => acquis);
  const N = QCM.questions.length;
  const CHOIX = QCM.questions.map((_, i) => choixPrefere(QCM, i));
  const LARGEURS = QCM.questions.map((q) => largeursDesBarres(q.scores_normalises));
  const COMPTE = texteDuCompte(compteDuQcm(QCM));
  if (QCM.questions.some((q) => q.choix.length > LETTRES.length)) {
    throw new Error(`AtelierQcm : une question a plus de ${LETTRES.length} réponses ; ajoute des lettres à LETTRES.`);
  }

  // Avant l'hydratation (et donc sans JavaScript), la question est dévoilée : rien ne se cache.
  let monte = $state(false);
  $effect(() => {
    monte = true;
  });

  let indice = $state(0);
  let paris = $state<(number | null)[]>(Array.from({ length: N }, () => null));
  let zoneQuestion: HTMLElement | undefined = $state();

  const question = $derived(QCM.questions[indice]);
  const choix = $derived(CHOIX[indice]);
  const largeurs = $derived(LARGEURS[indice]);
  const pari = $derived(paris[indice]);
  const revele = $derived(!monte || pari !== null);
  const vues = $derived(paris.flatMap((p, i) => (p === null ? [] : [i])));
  const fini = $derived(paris.every((p) => p !== null));
  const defi = $derived(etatDuDefi(vues, QCM));

  /** « réponse D » : une réponse désignée par sa lettre. */
  const reponse = (j: number) => `réponse ${LETTRES[j]}`;
  /** Un score normalisé, en nats par octet, avec deux décimales. */
  const score = (s: number) => nombre(s, 2);

  const texteIA = $derived(
    question.juste
      ? `Ton IA préfère la ${reponse(question.prefere)}${FINE}: c’est la bonne.`
      : `Ton IA préfère la ${reponse(question.prefere)}, mais la bonne est la ${reponse(question.bonne)}.`,
  );
  const textePari = $derived(
    pari === null ? '' : pari === question.prefere ? `Ton pari est juste${FINE}: tu as deviné sa préférence.` : `Ton pari est raté${FINE}: elle en préfère une autre.`,
  );

  function parier(j: number): void {
    if (!monte || paris[indice] !== null) return;
    paris[indice] = j;
    if (paris.every((p) => p !== null) && cleAcquis !== undefined && !acquisAnnonce) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: cleAcquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  }

  async function suivante(): Promise<void> {
    if (indice >= N - 1 || paris[indice] === null) return;
    indice += 1;
    await tick();
    zoneQuestion?.focus();
  }

  // Les lecteurs d'écran entendent la réussite du défi au moment où elle arrive.
  let annonceDefi = $state('');
  let defiAvant = untrack(() => defi.trouvees);
  $effect(() => {
    const trouvees = defi.trouvees;
    if (trouvees === defiAvant) return;
    defiAvant = trouvees;
    annonceDefi = untrack(() => defi.texte);
  });
</script>

<div class="atelier-qcm" data-atelier-qcm data-question={indice} data-pret={monte ? 'oui' : 'non'}>
  <p class="position" data-test="qcm-position">Question {nombre(indice + 1)} sur {nombre(N)}</p>
  <div class="lu" tabindex="-1" bind:this={zoneQuestion} data-test="qcm-contexte" data-pagefind-ignore>{question.contexte}</div>

  <p class="consigne" id="qcm-consigne">
    {#if revele}
      Les réponses, et leur score pour ton IA{FINE}:
    {:else}
      Quelle réponse ton IA préfère-t-elle{FINE}? Parie avant de voir ses scores.
    {/if}
  </p>

  <table class="reponses" aria-labelledby="qcm-consigne" data-test="qcm-reponses">
    <tbody>
      {#each choix as c, j (`${indice}-${j}`)}
        {@const prefere = revele && j === question.prefere}
        {@const bonne = revele && j === question.bonne}
        <tr data-reponse={j} data-prefere={prefere ? '' : undefined} data-bonne={bonne ? '' : undefined} data-juste={c.juste ? '' : undefined}>
          <th scope="row">
            <button
              type="button"
              class="pari-reponse"
              class:choisie={pari === j}
              disabled={revele}
              aria-pressed={pari === j}
              onclick={() => parier(j)}
              data-test="qcm-choix"
            >
              <span class="lettre">{LETTRES[j]}</span>
              <span class="texte" data-pagefind-ignore>{c.texte}</span>
            </button>
          </th>
          <td class="scores" class:floues={!revele} inert={!revele} aria-hidden={revele ? undefined : 'true'} data-test="qcm-barres">
            <span class="ligne-barre">
              <span class="piste" aria-hidden="true">
                <span
                  class="barre"
                  class:bonne-juste={bonne && question.juste}
                  class:bonne-fausse={bonne && !question.juste}
                  style:width={`${((revele ? largeurs[j] : 0.6) * 100).toFixed(1)}%`}
                ></span>
              </span>
              <span class="score" data-test="qcm-score">{revele ? score(question.scores_normalises[j]) : '?'}</span>
            </span>
            {#if prefere || bonne}
              <span class="marques">
                {#if prefere}<span class="marque" data-test="qcm-prefere">préférée par ton IA</span>{/if}
                {#if bonne}<span class="marque" class:juste={question.juste} class:faux={!question.juste} data-test="qcm-bonne">bonne réponse</span>{/if}
              </span>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
  <div class="legende-barres">
    Chaque barre{FINE}: la vraisemblance de la réponse, octet par octet, rapportée à celle que ton IA préfère.
    Le nombre est son score, en nats par octet{FINE}: plus il est haut, plus elle y croit.
  </div>

  <div class="apres" role="status">
    {#if revele}
      {#if pari !== null}<p class="pari-du-lecteur" data-test="qcm-pari">{textePari}</p>{/if}
      <p class="avis-ia" class:juste={question.juste} class:faux={!question.juste} data-test="qcm-verdict">{texteIA}</p>
      {#if fini && monte}<p class="compte" data-test="qcm-compte">{COMPTE}</p>{/if}
    {/if}
  </div>

  {#if monte && pari !== null && indice < N - 1}
    <button type="button" class="bouton-relief suivante" data-test="qcm-suivante" onclick={suivante}>Question suivante</button>
  {/if}

  <div class="defi" class:reussi={defi.reussi} data-defi>
    <h3>Défi</h3>
    <p>
      Trouve une question où ton IA préfère la bonne réponse. D’après ses scores, aurait-elle pu tomber juste par hasard{FINE}?
    </p>
    <p class="etat" data-test="qcm-defi">{defi.texte}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .atelier-qcm {
    margin: 1em 0 1.6em;
  }

  .position {
    margin: 0 0 6px;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 16px;
    color: var(--indigo-doux);
  }

  /* La question telle que ton IA l'a lue : le gabarit « Question : … Réponse : » de forge, sans retouche. */
  .lu {
    padding: 14px 16px;
    background: var(--brume-claire);
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 15px;
    line-height: 1.6;
    white-space: pre-line;
    overflow-wrap: anywhere;
  }

  .lu:focus-visible {
    outline: 3px solid var(--indigo);
    outline-offset: 2px;
  }

  .consigne {
    margin: 1em 0 0.4em;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 19px;
  }

  .reponses {
    width: 100%;
    border-collapse: collapse;
  }

  .reponses th,
  .reponses td {
    padding: 6px 0;
    vertical-align: middle;
    border-top: 1px solid var(--brume);
  }

  .reponses tr:first-child th,
  .reponses tr:first-child td {
    border-top: 2px solid var(--indigo);
  }

  .reponses th {
    width: 58%;
    padding-right: 14px;
    text-align: left;
    font-weight: 400;
  }

  /* Une réponse se choisit : bord indigo et soleil au survol, comme les choix des paris. */
  .pari-reponse {
    display: flex;
    gap: 10px;
    align-items: baseline;
    width: 100%;
    min-height: 44px;
    text-align: left;
    font: inherit;
    font-size: 17px;
    line-height: 1.35;
    color: var(--indigo);
    background: var(--papier);
    border: 2px solid var(--indigo);
    border-radius: 10px;
    padding: 8px 12px;
    cursor: pointer;
  }

  .pari-reponse:hover:not(:disabled) {
    background: var(--soleil);
  }

  .pari-reponse:disabled {
    cursor: default;
    border-color: var(--brume);
  }

  .pari-reponse.choisie {
    border-color: var(--indigo);
    background: var(--soleil-pale);
  }

  .lettre {
    font-family: var(--titres);
    font-weight: 700;
  }

  .texte {
    overflow-wrap: anywhere;
  }

  .scores {
    font-family: var(--titres);
    font-size: 15px;
  }

  /* Avant le pari, les barres sont floues, et toutes de la même longueur : elles ne disent rien. */
  .scores.floues {
    filter: blur(3px);
    opacity: 0.4;
    user-select: none;
  }

  /* La barre et son score sur une ligne ; la préférence et la bonne réponse dessous. */
  .ligne-barre {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .piste {
    flex: 1 1 auto;
    min-width: 60px;
  }

  .marques {
    display: flex;
    flex-wrap: wrap;
    gap: 0 12px;
    margin-top: 2px;
  }

  .barre {
    display: block;
    height: 10px;
    min-width: 2px;
    background: var(--indigo-doux);
    border-radius: 2px;
  }

  .barre.bonne-juste {
    background: var(--menthe);
  }

  .barre.bonne-fausse {
    background: var(--corail);
  }

  .score {
    flex: 0 0 auto;
    min-width: 3em;
    text-align: right;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .marque {
    font-size: 14px;
    color: var(--indigo-doux);
  }

  .marque.juste {
    color: var(--menthe);
    font-weight: 600;
  }

  .marque.faux {
    color: var(--corail);
    font-weight: 600;
  }

  .legende-barres {
    margin: 8px 0 0;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
  }

  .apres p {
    margin: 0.7em 0 0;
  }

  .pari-du-lecteur {
    font-style: italic;
  }

  /* Pas de classe « verdict » : la règle globale .verdict des paris (Pari.astro) s'y appliquerait. */
  .avis-ia {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 19px;
  }

  .avis-ia.juste {
    color: var(--menthe);
  }

  .avis-ia.faux {
    color: var(--corail);
  }

  .compte {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 21px;
    padding-top: 10px;
    border-top: 2px solid var(--indigo);
  }

  .suivante {
    margin-top: 1em;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 17px;
    min-height: 40px;
    padding: 4px 16px;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme en 1.1 et 1.4. */
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

  @media (prefers-reduced-motion: no-preference) {
    .scores {
      transition:
        filter 0.3s ease,
        opacity 0.3s ease;
    }
  }

  @media (max-width: 720px) {
    .reponses tr {
      display: block;
      border-top: 1px solid var(--brume);
      padding: 6px 0;
    }

    .reponses tr:first-child {
      border-top: 2px solid var(--indigo);
    }

    .reponses th,
    .reponses td {
      display: block;
      width: auto;
      padding: 0;
      border: 0;
    }

    .reponses tr:first-child th,
    .reponses tr:first-child td {
      border: 0;
    }

    .reponses td {
      padding-top: 6px;
    }

    .pari-reponse {
      font-size: 16px;
    }
  }
</style>
