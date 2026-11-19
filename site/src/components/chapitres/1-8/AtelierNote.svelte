<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 1.8 : le lecteur écrit sa propre réponse à une invite à consignes, et voit la note que les
  // contrôles de forge lui donnent, critère par critère, avec la raison de chacun, recalculée à chaque frappe : finie
  // (une bascule : elle a fini son tour, ou forge l'a coupée), juste (acquis pour une question), les consignes
  // respectées, le français, la longueur de 3 à 300 mots. Puis il peut comparer avec les deux réponses de la paire.
  //
  // Tout vient du jumeau des contrôles de forge (notes.ts), par atelier-1-8.ts : la page ne note rien autrement. Le
  // texte du lecteur n'est pas du texte du site : data-pagefind-ignore.
  //
  // À placer dans le MDX avec client:load, dans un <Verrou> :
  //   <AtelierNote client:load invite={…} consignes={…} depart={…} comparaison={…} verrou="atelier" acquis="atelier" />
  // Le champ et les boutons restent inactifs tant que le verrou n'est pas ouvert. À la première frappe, l'atelier
  // émet `forge:acquis` avec la clé `acquis`. Sans JavaScript, la note du texte de départ se lit telle quelle.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { ouverture } from '../../../lib/canal';
  import {
    comparerNotes,
    defiReussi,
    estLaPlusHaute,
    expliquerNote,
    LIBELLES_DES_CRITERES,
    noteEnTexte,
    noteMaximale,
    texteDuDefi,
  } from '../../../lib/partie-1/atelier-1-8';
  import type { ConsigneDInvite } from '../../../lib/partie-1/notes';
  import type { DetailAcquis } from '../../../scripts/chapitre';

  interface ReponseAComparer {
    lettre: string;
    texte: string;
    terminee: boolean;
  }

  interface Props {
    /** Le message de l'utilisateur, consignes comprises, tel que ton IA l'a lu. */
    invite: string;
    /** Les consignes de l'invite, que la note vérifie. */
    consignes: ConsigneDInvite[];
    /** Le texte du champ à l'arrivée. */
    depart: string;
    /** Les deux réponses de la paire, à comparer ; `reelle` dit si ce sont celles de ton IA ou celles de l'exemple. */
    comparaison: { reelle: boolean; reponses: ReponseAComparer[] };
    /** Nom du verrou qui garde le champ inactif tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné à la première frappe. */
    acquis?: string;
  }

  const { invite, consignes, depart, comparaison, verrou, acquis }: Props = $props();
  const FINE = '\u202F';
  const idTexte = $props.id();

  const CONSIGNES = untrack(() => consignes);
  const COMPARAISON = untrack(() => comparaison);
  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let monte = $state(false);
  $effect(() => {
    monte = true;
  });

  let texte = $state(untrack(() => depart));
  let finie = $state(true);
  let comparer = $state(false);

  const e = $derived(expliquerNote(texte, finie, CONSIGNES));
  const max = noteMaximale(CONSIGNES.length);
  const phraseDeLaNote = $derived(
    estLaPlusHaute(e)
      ? `Sa note${FINE}: ${noteEnTexte(e.note)}, la plus haute possible ici.`
      : `Sa note${FINE}: ${noteEnTexte(e.note)}, sous la plus haute possible ici, ${noteEnTexte(max)}.`,
  );

  const comparees = COMPARAISON.reponses.map((r) => ({ ...r, e: expliquerNote(r.texte, r.terminee, CONSIGNES) }));
  const ordre = comparerNotes(comparees[0].e.note, comparees[1].e.note);
  const preferee = ordre > 0 ? comparees[0].lettre : ordre < 0 ? comparees[1].lettre : null;

  function gagner(): void {
    if (cleAcquis === undefined || acquisAnnonce) return;
    acquisAnnonce = true;
    const detail: DetailAcquis = { cle: cleAcquis };
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
  }

  function basculer(): void {
    if (!actif) return;
    finie = !finie;
    gagner();
  }

  function ouvrirLaComparaison(): void {
    if (!actif) return;
    comparer = !comparer;
  }

  // Les lecteurs d'écran entendent la note quand elle change (pas à chaque frappe), et la réussite du défi.
  let annonce = $state('');
  let noteAvant = untrack(() => noteEnTexte(e.note));
  $effect(() => {
    const n = noteEnTexte(e.note);
    if (n === noteAvant) return;
    noteAvant = n;
    annonce = untrack(() => phraseDeLaNote);
  });
  let annonceDefi = $state('');
  const reussi = $derived(defiReussi(e, texte, COMPARAISON.reponses));
  let reussiAvant = untrack(() => reussi);
  $effect(() => {
    const r = reussi;
    if (r === reussiAvant) return;
    reussiAvant = r;
    annonceDefi = r ? untrack(() => texteDuDefi(e, texte, COMPARAISON.reponses)) : '';
  });
</script>

<div class="atelier-note" data-atelier-note data-pret={monte ? 'oui' : 'non'}>
  <p class="titre-invite">L’invite{FINE}:</p>
  <div class="invite" data-pagefind-ignore>{invite}</div>

  <div class="champ">
    <label for={idTexte}>Ta réponse{FINE}:</label>
    <textarea
      id={idTexte}
      data-test="an-texte"
      rows="3"
      bind:value={texte}
      oninput={gagner}
      readonly={!actif}
      autocomplete="off"
      spellcheck="false"
      data-pagefind-ignore
    ></textarea>
  </div>
  <p class="reglage">
    <button
      type="button"
      class="bascule-soleil"
      data-test="an-terminee"
      aria-pressed={finie}
      aria-disabled={!actif}
      onclick={basculer}>Elle a fini son tour</button
    >{FINE}: sinon, forge l’a coupée à la limite de jetons.
  </p>

  <ol class="criteres">
    {#each e.criteres as c (c.nom)}
      <li
        data-test="an-critere"
        data-nom={c.nom}
        data-valeur={c.valeur}
        data-maximum={c.maximum}
        data-verdict={c.verdict ? 'oui' : 'non'}
        class:manque={!c.verdict}
      >
        <span class="nom">{LIBELLES_DES_CRITERES[c.nom]}</span>
        <span class="valeur">{c.valeur} sur {c.maximum}</span>
        <span class="raison">{c.raison}</span>
        {#if c.nom === 'consignes' && e.consignes.length > 0}
          <ul class="consignes">
            {#each e.consignes as k, i (i)}
              <li data-test="an-consigne" data-id={k.id} data-respectee={k.respectee ? 'oui' : 'non'}>
                <span class="phrase" data-pagefind-ignore>{k.consigne}</span>
                <span class="sort">{k.respectee ? 'respectée' : 'oubliée'}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </li>
    {/each}
  </ol>
  <p class="note-totale" data-test="an-note">{phraseDeLaNote}</p>
  <p class="vh" role="status">{annonce}</p>
  <!-- Une légende en petit, comme celle de l'atelier de 1.7 : un bloc, pas un paragraphe du texte. -->
  <div class="legende">
    Forge compare deux notes critère par critère, dans cet ordre{FINE}: le premier qui diffère décide, et les suivants ne
    comptent plus.
  </div>

  <p class="reglage">
    <button
      type="button"
      class="bascule-soleil"
      data-test="an-comparer"
      aria-expanded={comparer}
      aria-disabled={!actif}
      onclick={ouvrirLaComparaison}>{COMPARAISON.reelle ? 'Comparer avec ton IA' : 'Comparer avec les deux réponses de l’exemple'}</button
    >
  </p>
  {#if comparer}
    <div class="comparaison" data-test="an-comparaison">
      {#each comparees as r (r.lettre)}
        <div class="comparee" data-test="an-reponse-comparee" data-lettre={r.lettre}>
          <p class="qui">Réponse {r.lettre}</p>
          <div class="texte" data-pagefind-ignore>{r.texte}</div>
          <p class="note-comparee">
            {r.terminee ? 'Finie' : 'Coupée'}, sa note{FINE}: {noteEnTexte(r.e.note)}.{r.lettre === preferee ? ' Forge la préfère.' : ''}
          </p>
        </div>
      {/each}
      {#if !COMPARAISON.reelle}
        <p class="a-mesurer" data-a-mesurer data-comparaison-a-mesurer>
          Les deux réponses de ton IA 1.7 à une vraie invite{FINE}: à mesurer, quand forge aura construit ses paires.
        </p>
      {/if}
    </div>
  {/if}

  <div class="defi" class:reussi data-defi>
    <h3>Défi</h3>
    <p>Écris ta propre réponse, pas une copie de celles de la paire, et obtiens la note la plus haute.</p>
    <p class="etat" data-test="an-defi">{texteDuDefi(e, texte, COMPARAISON.reponses)}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  /* Un texte collé, sans espace, passe à la ligne plutôt que d'élargir la page. */
  .atelier-note {
    margin: 1em 0 1.6em;
    overflow-wrap: anywhere;
  }

  .titre-invite {
    margin: 0 0 4px;
  }

  /* L'invite telle que ton IA la lit, en chasse fixe, comme une donnée. */
  .invite {
    margin: 0 0 1em;
    padding: 10px 14px;
    background: var(--brume-claire);
    border-radius: 10px;
    font-family: var(--mono);
    font-variant-ligatures: none;
    font-size: 14px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .champ label {
    display: block;
    margin-bottom: 4px;
  }

  /* Le champ : jaune, puisqu'il se manipule, comme ceux de 1.2 et 1.3. */
  .champ textarea {
    display: block;
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    font-size: 0.95em;
    line-height: 1.5;
    color: var(--indigo);
    background: var(--soleil-pale);
    border: 0;
    border-bottom: 3px solid var(--soleil);
    border-radius: 6px 6px 0 0;
    padding: 6px 10px 8px;
    resize: vertical;
    field-sizing: content;
    min-height: 3lh;
    max-height: 16lh;
  }

  .champ textarea:hover {
    background: var(--soleil-survol);
  }

  /* Le focus se voit au trait du bas, qui passe du jaune à l'encre. */
  .champ textarea:focus-visible {
    outline: none;
    background: var(--soleil-survol);
    border-bottom-color: var(--indigo);
  }

  .reglage {
    margin: 0.7em 0 0;
    line-height: 1.9;
  }

  .reglage .bascule-soleil {
    font: inherit;
    padding: 0 2px;
    min-height: 24px;
  }

  .reglage .bascule-soleil[aria-disabled='true'] {
    cursor: default;
  }

  /* Les critères : une ligne chacun, sous un trait d'encre, dans l'ordre où forge les compare. */
  .criteres {
    list-style: none;
    margin: 1em 0 0.4em;
    padding: 10px 0 0;
    border-top: 2px solid var(--indigo);
  }

  .criteres > li {
    display: grid;
    grid-template-columns: 8.5em 4.5em 1fr;
    gap: 2px 12px;
    padding: 5px 0;
    border-bottom: 1px solid var(--brume);
  }

  .nom {
    font-family: var(--titres);
    font-weight: 600;
  }

  .valeur {
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
  }

  /* Un critère sous son maximum : sa valeur en gras, sa raison en encre pleine ; les autres en encre douce. */
  .raison {
    color: var(--indigo-doux);
  }

  .manque .valeur {
    font-weight: 700;
  }

  .manque .raison {
    color: var(--indigo);
  }

  .consignes {
    grid-column: 2 / -1;
    list-style: none;
    margin: 2px 0 0;
    padding: 0;
    font-size: 0.92em;
  }

  .consignes li {
    margin: 2px 0;
  }

  .phrase {
    font-family: var(--mono);
    font-variant-ligatures: none;
    font-size: 0.9em;
  }

  .sort {
    margin-left: 6px;
    font-family: var(--titres);
    color: var(--indigo-doux);
  }

  /* Pas de classe « note » : la règle globale des notes en marge s'y appliquerait. */
  .note-totale {
    margin: 0.6em 0 0;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 19px;
    font-variant-numeric: tabular-nums;
  }

  .legende {
    margin: 6px 0 0;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
  }

  .comparaison {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin: 0.8em 0 0;
  }

  .comparaison .qui {
    margin: 0 0 4px;
    font-family: var(--titres);
    font-weight: 600;
    color: var(--indigo-doux);
  }

  .comparaison .texte {
    padding: 10px 14px;
    background: var(--brume-claire);
    border-radius: 10px;
    font-family: var(--mono);
    font-variant-ligatures: none;
    font-size: 14px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .note-comparee {
    margin: 6px 0 0;
    font-family: var(--titres);
    font-size: 15px;
    font-variant-numeric: tabular-nums;
  }

  .a-mesurer {
    grid-column: 1 / -1;
    margin: 0;
    font-style: italic;
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
    .criteres > li {
      grid-template-columns: 7.5em 1fr;
    }

    .raison {
      grid-column: 1 / -1;
    }

    .consignes {
      grid-column: 1 / -1;
    }

    .comparaison {
      grid-template-columns: 1fr;
    }
  }
</style>
