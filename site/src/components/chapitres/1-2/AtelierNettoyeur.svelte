<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 1.2 : le lecteur écrit un texte, choisit ses fins de
  // ligne (celles de Linux et macOS, \n, ou celles de Windows, \r\n), et voit
  // ce que le nettoyage de forge en fait. Le texte nettoyé montre chaque
  // retrait à sa place, en encre douce : ␍ pour un retour chariot, · pour un
  // autre caractère invisible (un contrôle, ou un blanc en fin de texte).
  // Dessous, la longueur, le verdict, l'empreinte et le côté où ira le texte,
  // puis un second champ qui compare son empreinte à celle du premier.
  //
  // Tout vient du jumeau exact du Python (src/lib/partie-1/nettoyeur.ts), et
  // les phrases de paris-1-2.ts. Un champ de saisie ne garde jamais de \r (le
  // navigateur ramène toute fin de ligne à \n) : ce sont les bascules des fins
  // de ligne qui remettent \r\n, comme un fichier enregistré sous Windows. Le
  // second champ garde ses \n.
  //
  // L'empreinte (SHA-1, par crypto.subtle) est asynchrone : la longueur et le
  // verdict s'affichent tout de suite, et l'empreinte affichée reste celle du
  // texte précédent (marquée data-en-cours) jusqu'à l'arrivée de la nouvelle.
  // Le côté, le doublon et le défi, eux, ne se calculent qu'avec des empreintes à
  // jour, celles des textes à l'écran (messagesDeLAtelier) : pendant un calcul, ils
  // gardent leur message d'avant. Rien ne disparaît, rien ne clignote, et les zones
  // role="status" n'annoncent que les changements de verdict : gardé ou écarté,
  // doublon ou non, défi réussi. Sans crypto.subtle (une page ouverte en http://
  // sur le réseau local), l'atelier dit qu'il ne peut pas calculer l'empreinte, et
  // n'affiche plus celle d'un autre texte.
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <AtelierNettoyeur client:load texteInitial={…} empreinteInitiale={…} verrou="atelier" acquis="atelier" />
  // `empreinteInitiale`, l'empreinte du texte de départ écrit sous Windows,
  // calculée à la construction, la montre aussi sans JavaScript. Les champs et
  // les bascules restent inactifs tant que le verrou n'est pas ouvert. À la
  // première modification (texte ou fins de ligne), l'atelier émet
  // `forge:acquis` avec la clé `acquis`.
  import { untrack, type Snippet } from 'svelte';
  import { readable } from 'svelte/store';
  import { ouverture } from '../../../lib/canal';
  import { nombre } from '../../../lib/nombres';
  import { empreinte } from '../../../lib/partie-1/nettoyeur';
  import {
    CONTROLE_RETIRE,
    EMPREINTE_IMPOSSIBLE,
    etatDuDefi,
    etatDuNettoyage,
    messageDoublon,
    messagesDeLAtelier,
    phraseLongueur,
    type EmpreinteCalculee,
    type MessagesDeLAtelier,
    RETOUR_CHARIOT,
    verdictDuTexte,
    versWindows,
  } from '../../../lib/partie-1/paris-1-2';
  import type { DetailAcquis } from '../../../scripts/chapitre';

  interface Props {
    /** Le texte écrit dans le premier champ, à l'arrivée (avec des fins de ligne \n). */
    texteInitial: string;
    /** Son empreinte une fois écrit sous Windows (versWindows), calculée à la construction. */
    empreinteInitiale?: string;
    /** Nom du verrou qui garde les champs inactifs tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Clé de l'acquis gagné à la première modification. */
    acquis?: string;
    /** Texte du chapitre posé sous le second champ, avant le défi. */
    children?: Snippet;
  }

  const { texteInitial, empreinteInitiale, verrou, acquis, children }: Props = $props();

  const FINE = '\u202F';
  const idTexte = $props.id();
  const idAutre = `${idTexte}-autre`;

  const nomDuVerrou = untrack(() => verrou);
  const cleAcquis = untrack(() => acquis);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let texte = $state(untrack(() => texteInitial));
  let windows = $state(true);
  let autre = $state('');

  // Le texte tel que le nettoyage le reçoit : celui du champ, avec ses fins de ligne.
  const brut = $derived(windows ? versWindows(texte) : texte);
  const etat = $derived(etatDuNettoyage(brut));
  const verdict = $derived(verdictDuTexte(etat));
  const retours = $derived(etat.morceaux.reduce((n, m) => (m.retire && m.texte[0] === RETOUR_CHARIOT ? n + m.nombre : n), 0));
  const autresRetraits = $derived(etat.morceaux.reduce((n, m) => (m.retire && m.texte[0] === CONTROLE_RETIRE ? n + m.nombre : n), 0));

  // ---------- Les empreintes, asynchrones ----------
  // Chaque empreinte garde le texte pour lequel elle a été calculée (`pour`). Chaque
  // calcul porte un numéro : seul le dernier lancé compte, même si un précédent
  // arrive après lui. Un échec (pas de crypto.subtle) donne une empreinte nulle,
  // marquée `erreur`.
  let a = $state<EmpreinteCalculee | null>(
    untrack(() =>
      empreinteInitiale === undefined
        ? null
        : { pour: versWindows(texteInitial), empreinte: empreinteInitiale, erreur: false },
    ),
  );
  let enCoursA = $state(false);
  let numeroA = 0;
  $effect(() => {
    const t = brut;
    const n = ++numeroA;
    // Retour au texte dont l'empreinte est connue : rien à calculer, et un calcul
    // encore en route (celui d'un texte intermédiaire) ne compte plus.
    if (t === untrack(() => a?.pour)) {
      enCoursA = false;
      return;
    }
    enCoursA = true;
    empreinte(t).then(
      (e) => {
        if (n !== numeroA) return;
        a = { pour: t, empreinte: e, erreur: false };
        enCoursA = false;
      },
      () => {
        if (n !== numeroA) return;
        a = { pour: t, empreinte: null, erreur: true };
        enCoursA = false;
      },
    );
  });

  let b = $state<EmpreinteCalculee | null>(null);
  let enCoursB = $state(false);
  let numeroB = 0;
  $effect(() => {
    const t = autre;
    const n = ++numeroB;
    if (t === '' || t === untrack(() => b?.pour)) {
      enCoursB = false;
      return;
    }
    enCoursB = true;
    empreinte(t).then(
      (e) => {
        if (n !== numeroB) return;
        b = { pour: t, empreinte: e, erreur: false };
        enCoursB = false;
      },
      () => {
        if (n !== numeroB) return;
        b = { pour: t, empreinte: null, erreur: true };
        enCoursB = false;
      },
    );
  });

  // L'empreinte montrée sous chaque champ : la dernière calculée, même pendant un
  // calcul (data-en-cours), sauf après un échec.
  const empreinteA = $derived(a === null || a.erreur ? null : a.empreinte);
  const empreinteB = $derived(b === null || b.erreur || autre === '' ? null : b.empreinte);

  // Le côté, le doublon et le défi : seulement avec des empreintes à jour ; sinon,
  // ceux d'avant. Au départ (et sans JavaScript), ceux du texte de départ.
  const SANS_EMPREINTE: MessagesDeLAtelier = {
    cote: '',
    doublon: messageDoublon(etatDuNettoyage(''), '', null, null),
    defi: etatDuDefi('', '', null, null),
  };
  let derniers: MessagesDeLAtelier = untrack(
    () => messagesDeLAtelier(etat, brut, texte, autre, a, b) ?? SANS_EMPREINTE,
  );
  const messages = $derived.by(() => {
    const m = messagesDeLAtelier(etat, brut, texte, autre, a, b);
    if (m !== null) derniers = m;
    return derniers;
  });
  const cote = $derived(messages.cote);
  const doublon = $derived(messages.doublon);
  const defi = $derived(messages.defi);

  // ---------- Les annonces : seulement quand un verdict change ----------
  let annonce = $state('');
  let gardeAvant = untrack(() => etat.garde);
  $effect(() => {
    const g = etat.garde;
    if (g === gardeAvant) return;
    gardeAvant = g;
    annonce = untrack(() => verdict);
  });

  // Le message du doublon change seulement quand ses empreintes sont à jour.
  let annonceDoublon = $state('');
  let doublonAvant = untrack(() => doublon);
  $effect(() => {
    const d = doublon;
    if (d === doublonAvant) return;
    doublonAvant = d;
    annonceDoublon = autre === '' ? '' : d;
  });

  let annonceDefi = $state('');
  let defiAvant = untrack(() => defi.reussi);
  $effect(() => {
    const reussi = defi.reussi;
    if (reussi === defiAvant) return;
    defiAvant = reussi;
    annonceDefi = reussi ? untrack(() => defi.texte) : '';
  });

  // ---------- L'acquis : à la première modification ----------
  function gagner(): void {
    if (cleAcquis === undefined || acquisAnnonce) return;
    acquisAnnonce = true;
    const detail: DetailAcquis = { cle: cleAcquis };
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
  }

  function choisirFins(versWindowsOuNon: boolean): void {
    if (!actif || versWindowsOuNon === windows) return;
    windows = versWindowsOuNon;
    gagner();
  }

  /** « 3 retours chariot », « 1 autre caractère invisible » : ce que le texte nettoyé a perdu, en mots. */
  function retraitsEnMots(): string {
    if (retours === 0 && autresRetraits === 0) return `Rien n’est retiré${FINE}: le texte est déjà propre.`;
    const morceaux: string[] = [];
    if (retours > 0) morceaux.push(`${nombre(retours)} ${retours > 1 ? 'retours chariot' : 'retour chariot'} (${RETOUR_CHARIOT})`);
    if (autresRetraits > 0) {
      morceaux.push(
        `${nombre(autresRetraits)} ${autresRetraits > 1 ? 'autres caractères invisibles' : 'autre caractère invisible'} (${CONTROLE_RETIRE})`,
      );
    }
    return `${retours + autresRetraits > 1 ? 'Retirés' : 'Retiré'}${FINE}: ${morceaux.join(' et ')}.`;
  }
</script>

<div class="atelier" data-atelier-nettoyeur>
  <div class="champ">
    <label for={idTexte}>Ton texte{FINE}:</label>
    <textarea
      id={idTexte}
      data-test="nt-texte"
      rows="7"
      bind:value={texte}
      oninput={gagner}
      readonly={!actif}
      autocomplete="off"
      spellcheck="false"
      data-pagefind-ignore
    ></textarea>
  </div>

  <p class="reglage">
    Ses fins de ligne, comme sous{FINE}:
    <span class="fins" role="group" aria-label="Fins de ligne">
      <button
        type="button"
        class="bascule-soleil"
        data-test="nt-fins-unix"
        aria-pressed={!windows}
        aria-disabled={!actif}
        onclick={() => choisirFins(false)}>Linux ou macOS</button
      >
      <button
        type="button"
        class="bascule-soleil"
        data-test="nt-fins-windows"
        aria-pressed={windows}
        aria-disabled={!actif}
        onclick={() => choisirFins(true)}>Windows</button
      ></span
    >
  </p>

  <p class="titre-nettoye">Le texte nettoyé{FINE}:</p>
  <!-- Pas de blanc entre les balises : dans un <pre>, il s'afficherait. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex (un long texte défile dans son cadre, qui doit prendre le focus pour se parcourir au clavier : WCAG 2.1.1) -->
  <pre class="nettoye" data-test="nt-nettoye" role="region" aria-label="Le texte nettoyé" tabindex="0" data-pagefind-ignore>{#each etat.morceaux as m, i (i)}{#if m.retire}<span class="retrait" data-retrait aria-hidden="true">{m.texte}</span>{:else}{m.texte}{/if}{/each}</pre>
  <p class="retraits" data-test="nt-retraits">{retraitsEnMots()}</p>

  <div class="bilan">
    <p data-test="nt-longueur">{phraseLongueur(etat.longueur)}.</p>
    <p class="jugement"><strong data-test="nt-verdict">{verdict}</strong></p>
    <p>
      {#if a !== null && a.erreur && !enCoursA}
        Son empreinte{FINE}: <span data-test="nt-empreinte-impossible">{EMPREINTE_IMPOSSIBLE}</span>.
      {:else}
        Son empreinte{FINE}: <code data-test="nt-empreinte" data-en-cours={enCoursA ? 'oui' : undefined}
          >{empreinteA === null ? '' : empreinteA.slice(0, 8)}</code
        >, les 8 premiers de ses 40 chiffres.
      {/if}
    </p>
    <p data-test="nt-cote">{cote}</p>
  </div>
  <p class="vh" role="status" data-test="nt-annonce">{annonce}</p>

  <div class="champ autre">
    <label for={idAutre}>Un autre texte{FINE}:</label>
    <textarea
      id={idAutre}
      data-test="nt-autre"
      rows="3"
      bind:value={autre}
      oninput={gagner}
      readonly={!actif}
      autocomplete="off"
      spellcheck="false"
      data-pagefind-ignore
    ></textarea>
  </div>
  <p class="comparaison">
    {#if autre !== '' && b !== null && b.erreur && !enCoursB}
      Son empreinte{FINE}: <span data-test="nt-autre-empreinte-impossible">{EMPREINTE_IMPOSSIBLE}</span>.
    {:else if autre !== ''}
      Son empreinte{FINE}: <code data-test="nt-autre-empreinte" data-en-cours={enCoursB ? 'oui' : undefined}
        >{empreinteB === null ? '' : empreinteB.slice(0, 8)}</code
      >.
    {/if}
    <span data-test="nt-doublon">{doublon}</span>
  </p>
  <p class="vh" role="status">{annonceDoublon}</p>

  {#if children}
    <div class="texte-atelier">{@render children()}</div>
  {/if}

  <div class="defi" class:reussi={defi.reussi} data-defi>
    <h3>Défi</h3>
    <p>Écris dans les deux champs deux textes différents, mais qui ont la même empreinte.</p>
    <p class="etat" data-test="nt-defi">{defi.texte}</p>
    <p class="vh" role="status">{annonceDefi}</p>
  </div>
</div>

<style>
  /* Un texte collé, sans espace, passe à la ligne plutôt que d'élargir la page. */
  .atelier {
    margin: 1em 0 1.6em;
    overflow-wrap: anywhere;
  }

  .champ label {
    display: block;
    margin-bottom: 4px;
  }

  /* Les champs : jaunes, puisqu'ils se manipulent, comme ceux de 1.1 et 1.3. */
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
    /* Le champ prend la hauteur de son texte (là où le navigateur le sait), sans dépasser 22 lignes. */
    field-sizing: content;
    min-height: 3lh;
    max-height: 22lh;
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
    margin: 0.8em 0 0;
    line-height: 1.9;
  }

  .fins .bascule-soleil {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 0.9em;
    min-height: 26px;
    padding: 0 8px;
    margin: 0 2px;
    white-space: nowrap;
  }

  .fins .bascule-soleil[aria-disabled='true'] {
    cursor: default;
  }

  .titre-nettoye {
    margin: 1.1em 0 0.4em;
  }

  /* Le texte nettoyé, en chasse fixe, comme une sortie de terminal ; les retraits en encre douce. */
  .nettoye {
    margin: 0;
    padding: 14px 16px;
    background: var(--brume-claire);
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 15px;
    line-height: 1.6;
    color: var(--indigo);
    font-variant-ligatures: none;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 22em;
    overflow-y: auto;
  }

  /* Un long texte défile dans son cadre : atteint au clavier, le cadre montre son focus. */
  .nettoye:focus-visible {
    outline: 2px solid var(--indigo);
    outline-offset: 2px;
  }

  .retrait {
    color: var(--indigo-doux);
  }

  .retraits {
    margin: 4px 0 0;
    font-family: var(--titres);
    font-size: 14px;
    color: var(--indigo-doux);
  }

  .bilan {
    margin-top: 1em;
  }

  .bilan p,
  .comparaison {
    margin: 0 0 0.3em;
  }

  .jugement strong {
    font-family: var(--titres);
    font-weight: 700;
  }

  code {
    font-family: var(--mono);
    font-size: 0.9em;
    font-variant-ligatures: none;
  }

  .autre {
    margin-top: 1.4em;
  }

  .comparaison {
    margin-top: 0.5em;
  }

  /* Le texte du chapitre posé sous les champs : détaché des résultats calculés. */
  .texte-atelier {
    margin-top: 1.2em;
  }

  .texte-atelier :global(p) {
    margin: 0 0 0.6em;
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme en 1.1 et 1.3. */
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
    .nettoye {
      font-size: 14px;
      padding: 12px 14px;
    }
  }
</style>
