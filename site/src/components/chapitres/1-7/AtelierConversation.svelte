<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 1.7 : une conversation devient des jetons, et le lecteur voit lesquels ton IA
  // apprend. Il choisit une des six conversations de référence du projet 1.7, et deux bascules lui ajoutent
  // ou lui retirent un message système et un deuxième tour. La page montre la conversation jeton par jeton,
  // un tour par ligne : les jetons appris en indigo plein, les autres bordés de lavande, les jetons spéciaux
  // en chasse fixe ; puis leur compte, « 30 jetons, dont 9 appris ».
  //
  // Tout vient du jumeau d'encoder_conversation (assemblerConversation, conversation.ts), par atelier-1-7.ts,
  // sur les textes que le Python a encodés (tests/attendus.json) : le navigateur n'encode rien. Le texte de
  // chaque jeton est lu dans le tokenizer de ton IA à la construction, et passé ici. La conversation à la
  // réponse vide montre l'erreur de forge, mot pour mot. Avant le jumeau, la page refuse elle-même un texte
  // vide ou fait de blancs, comme Python (refuserLesTextesBlancs).
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <AtelierConversation client:load conversations={…} textes={…} verrou="atelier" acquis="atelier" />
  // Les boutons restent inactifs tant que le verrou n'est pas ouvert. Au premier réglage, l'atelier émet
  // `forge:acquis` avec la clé `acquis`. Sans JavaScript, la première conversation se lit telle que forge l'a
  // assemblée.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { ouverture } from '../../../lib/canal';
  import {
    etatDeLAtelier,
    LIBELLES_DE_L_ATELIER,
    morceauxDuJeton,
    NOMS_DE_L_ATELIER,
    reglageDeReference,
    texteDuCompte,
    texteDuDefi,
    defiReussi,
    type ConversationDeReference,
    type NomDeConversation,
    type ReglageDeLAtelier,
  } from '../../../lib/partie-1/atelier-1-7';
  import type { DetailAcquis } from '../../../scripts/chapitre';

  interface Props {
    /** Les six conversations de référence (tests/attendus.json du projet 1.7), lues par le chapitre. */
    conversations: ConversationDeReference[];
    /** Le texte de chaque jeton qu'elles utilisent, lu dans le tokenizer de ton IA à la construction. */
    textes: Record<number, string>;
    /** Nom du verrou qui garde les boutons inactifs tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné au premier réglage. */
    acquis?: string;
  }

  const { conversations, textes, verrou, acquis }: Props = $props();
  const FINE = '\u202F';

  const CONVERSATIONS = untrack(() => conversations);
  const TEXTES = untrack(() => textes);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let monte = $state(false);
  $effect(() => {
    monte = true;
  });

  let reglage = $state<ReglageDeLAtelier>(reglageDeReference(CONVERSATIONS, NOMS_DE_L_ATELIER[0]));
  const etat = $derived(etatDeLAtelier(CONVERSATIONS, reglage));
  const reussi = $derived(defiReussi(etat, reglage));

  /** Le texte d'un jeton : celui du tokenizer, lu à la construction. */
  const texteDe = (id: number): string => {
    const t = TEXTES[id];
    if (t === undefined) throw new Error(`AtelierConversation : le texte du jeton ${id} manque ; le chapitre doit le lire dans le tokenizer.`);
    return t;
  };

  // Pour les lecteurs d'écran, les pastilles ne se lisent pas une à une : une phrase dit ce qui est appris.
  const apprisEnMots = $derived(
    etat.erreur !== null
      ? ''
      : `Les jetons appris${FINE}: « ${etat.lignes
          .flatMap((l) => l.jetons)
          .filter((j) => j.appris)
          .map((j) => texteDe(j.id))
          .join('')} ».`,
  );

  function gagner(): void {
    if (cleAcquis === undefined || acquisAnnonce) return;
    acquisAnnonce = true;
    const detail: DetailAcquis = { cle: cleAcquis };
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
  }

  function choisir(nom: NomDeConversation): void {
    if (!actif) return;
    reglage = reglageDeReference(CONVERSATIONS, nom);
    gagner();
  }

  function basculer(quoi: 'systeme' | 'deuxieme'): void {
    if (!actif) return;
    reglage = { ...reglage, [quoi]: !reglage[quoi] };
    gagner();
  }

  // Les lecteurs d'écran entendent le compte quand le lecteur change la conversation (pas à l'arrivée), et la
  // réussite du défi quand elle arrive.
  let annonce = $state('');
  let avant = untrack(() => JSON.stringify(reglage));
  $effect(() => {
    const r = JSON.stringify(reglage);
    if (r === avant) return;
    avant = r;
    const e = untrack(() => etat);
    annonce = e.erreur !== null ? e.erreur : texteDuCompte(e.jetons, e.appris);
  });
  let annonceDefi = $state('');
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const r = reussi;
    if (r === reussiAvant) return;
    reussiAvant = r;
    annonceDefi = r ? untrack(() => texteDuDefi(etat, reglage)) : '';
  });
</script>

<div class="atelier-conversation" data-atelier-conversation data-pret={monte ? 'oui' : 'non'}>
  <p class="reglage">
    La conversation{FINE}:
    <span class="conversations" role="group" aria-label="Conversation à montrer">
      {#each NOMS_DE_L_ATELIER as nom, i (nom)}
        <!-- Le bouton et sa ponctuation restent sur la même ligne. -->
        <span class="sans-coupure"><button
          type="button"
          class="bascule-soleil"
          data-test="cv-conversation"
          data-nom={nom}
          aria-pressed={reglage.nom === nom}
          aria-disabled={!actif}
          onclick={() => choisir(nom)}>{LIBELLES_DE_L_ATELIER[nom]}</button
          >{i < NOMS_DE_L_ATELIER.length - 1 ? ',' : '.'}</span
        >
      {/each}
    </span>
  </p>
  <p class="reglage">
    Change-la{FINE}:
    <span class="sans-coupure"><button
      type="button"
      class="bascule-soleil"
      data-test="cv-systeme"
      aria-pressed={reglage.systeme}
      aria-disabled={!actif}
      onclick={() => basculer('systeme')}>avec un message système</button
      >,</span
    >
    <span class="sans-coupure"><button
      type="button"
      class="bascule-soleil"
      data-test="cv-deuxieme"
      aria-pressed={reglage.deuxieme}
      aria-disabled={!actif}
      onclick={() => basculer('deuxieme')}>un deuxième tour</button
      >.</span
    >
  </p>

  {#if etat.erreur !== null}
    <p class="erreur" data-test="cv-erreur" data-pagefind-ignore>{etat.erreur}</p>
  {:else}
    <!-- Les pastilles répètent en image la phrase « apprisEnMots » : les lecteurs d'écran lisent la phrase. -->
    <div class="jetons" data-test="cv-jetons" data-pagefind-ignore aria-hidden="true">
      {#each etat.lignes as ligne, l (l)}
        <div class="ligne" data-role={ligne.role}>
          {#each ligne.jetons as jeton, j (j)}
            <span
              class="jeton"
              class:appris={jeton.appris}
              class:special={jeton.special}
              data-jeton
              data-id={jeton.id}
              data-appris={jeton.appris ? 'oui' : 'non'}
              data-special={jeton.special ? '' : undefined}
              >{#each morceauxDuJeton(texteDe(jeton.id)) as m, k (k)}{#if m.blanc}<span class="blanc">{m.texte}</span
                  >{:else}{m.texte}{/if}{/each}</span
            >
          {/each}
        </div>
      {/each}
    </div>
    <p class="vh" data-test="cv-appris-en-mots" data-pagefind-ignore>{apprisEnMots}</p>
    <p class="compte" data-test="cv-compte">{texteDuCompte(etat.jetons, etat.appris)}</p>
  {/if}
  <!-- Une légende en petit, comme celle des barres de l'atelier de 1.6 : un bloc, pas un paragraphe du texte. -->
  <div class="legende">
    En indigo plein, les jetons appris{FINE}: ceux dont ton IA apprend à prédire qu’ils viennent. Bordés de lavande, ceux
    qu’elle lit sans les apprendre. En chasse fixe, les jetons spéciaux. Un tour par ligne{FINE}; «{FINE}␣{FINE}» est une
    espace.
  </div>
  <p class="vh" role="status">{annonce}</p>

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>Avec un message système et un deuxième tour, trouve une conversation dont plus de la moitié des jetons sont appris.</p>
    <p class="etat" data-test="cv-defi">{texteDuDefi(etat, reglage)}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  .atelier-conversation {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.5em;
    line-height: 1.9;
  }

  .reglage .bascule-soleil {
    font: inherit;
    padding: 0 1px; /* presque rien : la virgule qui suit reste collée au mot */
    min-height: 24px;
  }

  .sans-coupure {
    white-space: nowrap;
  }

  .reglage .bascule-soleil[aria-disabled='true'] {
    cursor: default;
  }

  /* La conversation, un tour par ligne, sous un trait d'encre. */
  .jetons {
    margin: 0.8em 0 0.4em;
    padding: 12px 0 4px;
    border-top: 2px solid var(--indigo);
    border-bottom: 1px solid var(--brume);
  }

  .ligne {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 3px;
    margin-bottom: 9px;
  }

  /* Une pastille par jeton : bordée de lavande si elle n'est pas apprise, indigo plein si elle l'est. */
  .jeton {
    display: inline-block;
    max-width: 100%;
    padding: 1px 5px;
    border: 1.5px solid var(--lavande);
    border-radius: 5px;
    background: var(--papier);
    color: var(--indigo);
    font-family: var(--texte);
    font-size: 17px;
    line-height: 1.35;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .jeton.appris {
    background: var(--indigo);
    border-color: var(--indigo);
    color: var(--papier);
  }

  .jeton.special {
    font-family: var(--mono);
    font-variant-ligatures: none; /* « <| » reste « <| », pas une flèche : on montre le nom du jeton */
    font-size: 13px;
    line-height: 1.75;
  }

  /* Les espaces se voient (« ␣ »), plus discrètement que les lettres. */
  .blanc {
    color: var(--indigo-doux);
  }

  .jeton.appris .blanc {
    color: var(--brume);
  }

  .compte {
    margin: 0.4em 0 0;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 21px;
    font-variant-numeric: tabular-nums;
  }

  .erreur {
    font-variant-ligatures: none;
    margin: 0.8em 0 0;
    padding: 12px 0;
    border-top: 2px solid var(--indigo);
    font-family: var(--mono);
    font-size: 15px;
    line-height: 1.55;
  }

  .legende {
    margin: 8px 0 0;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme dans les autres ateliers. */
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
    .jeton {
      font-size: 16px;
    }
  }
</style>
