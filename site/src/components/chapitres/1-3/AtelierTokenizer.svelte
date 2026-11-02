<script lang="ts" module>
  // Une seule annonce de l'acquis « fusions » par chargement de page, même si
  // le lecteur repasse plusieurs fois le cap (le script du chapitre ignore de
  // toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // L'atelier du chapitre 1.3 : le lecteur tape une phrase, fait glisser le
  // nombre de fusions, et voit la phrase découpée en jetons, avec le numéro de
  // chaque jeton dessous. Tout est calculé par tokenizer13, le même code que
  // les paris du chapitre (src/lib/bpe.ts, jumeau exact du Python).
  //
  // À placer dans le MDX avec client:load, en général dans un <Verrou> :
  //   <AtelierTokenizer client:load phraseInitiale="…" verrou="atelier" />
  // Le nombre reste désactivé tant que le verrou n'est pas ouvert. Quand il
  // atteint `acquisA` fusions, l'atelier émet `forge:acquis` (clé « fusions »),
  // que le script du chapitre transforme en acquis gagné.
  //
  // Le contenu éventuel du composant (du texte du chapitre) s'affiche sous la
  // bande de jetons, avant le défi. Le défi (prop `defi`) est vérifié en
  // direct, toujours avec toutes les fusions, quel que soit le nombre jaune.
  import { untrack, type Snippet } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { preDecouper, segmentsVisibles, tokenizer13, type Jeton } from '../../../lib/bpe';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';
  import DernieresFusions from './DernieresFusions.svelte';
  import { FUSIONS_AU_DEPART, NB_FUSIONS } from './fusions';

  /** Le défi : une phrase d'au moins `minCaracteres` caractères, en `maxJetons` jetons ou moins. */
  interface Defi {
    minCaracteres: number;
    maxJetons: number;
  }

  interface Props {
    /** La phrase déjà tapée dans le champ, à l'arrivée. */
    phraseInitiale: string;
    /** Nom du canal du nombre de fusions ; « fusions » par défaut. */
    canalFusions?: string;
    /** Nom du verrou qui désactive le nombre tant qu'il n'est pas ouvert. */
    verrou?: string;
    /** Nombre de fusions qui fait gagner l'acquis « fusions » ; 60 par défaut. */
    acquisA?: number;
    /** Le défi à afficher sous l'atelier, s'il y en a un. */
    defi?: Defi;
    /**
     * Faux si les dernières fusions sont montrées ailleurs (dans la marge,
     * avec DernieresFusions) ; vrai par défaut.
     */
    avecDernieresFusions?: boolean;
    /** Texte du chapitre posé sous la bande de jetons. */
    children?: Snippet;
  }

  const {
    phraseInitiale,
    canalFusions = 'fusions',
    verrou,
    acquisA = 60,
    defi,
    avecDernieresFusions = true,
    children,
  }: Props = $props();

  const FINE = '\u202F';
  const idSaisie = $props.id();

  // Le canal est choisi une fois pour toutes, comme dans NombreManipulable.
  const fusions = canal<number>(untrack(() => canalFusions), FUSIONS_AU_DEPART);

  let texte = $state(untrack(() => phraseInitiale));
  let morceauxCaches = $state(false);
  let annonce = $state('');

  const k = $derived($fusions);
  const jetons = $derived(tokenizer13.decouper(texte, k));
  const nbCaracteres = $derived(Array.from(texte).length);
  // « Mot par mot » : un jeton par mot, c'est-à-dire par pré-jeton qui contient une lettre.
  const nbMots = $derived(preDecouper(texte).filter((mot) => /\p{L}/u.test(mot)).length);

  // Les morceaux qui n'existaient pas dans le découpage précédent s'allument un
  // instant : on voit ce que la dernière fusion vient de coller. Rien au
  // chargement : le mouvement répond seulement à un geste du lecteur.
  let dejaVus = new Set<string>();
  const affiches = $derived.by(() => {
    const avant = dejaVus;
    return jetons.map((jeton, i) => ({ jeton, i, nouveau: avant.size > 0 && !avant.has(jeton.texte) }));
  });
  $effect(() => {
    dejaVus = new Set(jetons.map((j) => j.texte));
  });

  const nombre = new Intl.NumberFormat('fr-FR');
  const pluriel = (n: number, un: string, plusieurs: string) => (n > 1 ? plusieurs : un);

  // Le défi se mesure toujours avec toutes les fusions : il ne dépend que de
  // la phrase, pas du nombre jaune.
  const jetonsDuDefi = $derived(
    defi === undefined ? 0 : k === NB_FUSIONS ? jetons.length : tokenizer13.decouper(texte, NB_FUSIONS).length,
  );
  const defiReussi = $derived(
    defi !== undefined && nbCaracteres >= defi.minCaracteres && jetonsDuDefi <= defi.maxJetons,
  );
  const etatDuDefi = $derived.by(() => {
    if (defi === undefined) return '';
    const caracteres = `${nombre.format(nbCaracteres)} ${pluriel(nbCaracteres, 'caractère', 'caractères')}`;
    const enJetons = `${nombre.format(jetonsDuDefi)} ${pluriel(jetonsDuDefi, 'jeton', 'jetons')}`;
    if (nbCaracteres < defi.minCaracteres) {
      return `Ta phrase fait ${caracteres}${FINE}: il en faut au moins ${defi.minCaracteres}.`;
    }
    if (defiReussi) return `Défi réussi${FINE}: ${caracteres} en ${enJetons}.`;
    const deTrop = jetonsDuDefi - defi.maxJetons;
    return `Avec les ${NB_FUSIONS} fusions, ta phrase tient en ${enJetons}, soit ${nombre.format(deTrop)} de trop.`;
  });

  // Les lecteurs d'écran entendent la réussite du défi au moment où elle
  // arrive, et pas à chaque lettre tapée.
  let annonceDefi = $state('');
  let defiReussiAvant = untrack(() => defiReussi);
  $effect(() => {
    const reussi = defiReussi;
    if (reussi === defiReussiAvant) return;
    defiReussiAvant = reussi;
    annonceDefi = reussi ? untrack(() => etatDuDefi) : '';
  });

  // Quand le nombre de fusions change (et seulement lui : pas pendant la
  // frappe), les lecteurs d'écran entendent le nouveau nombre de jetons ; et
  // l'acquis est annoncé une fois le cap atteint.
  let kPrecedent = untrack(() => k);
  const kDepart = kPrecedent;
  $effect(() => {
    const kActuel = k;
    if (kActuel === kPrecedent) return;
    kPrecedent = kActuel;
    untrack(() => {
      const n = jetons.length;
      annonce = nbCaracteres === 0 ? '' : `${nombre.format(n)} ${pluriel(n, 'jeton', 'jetons')}`;
    });
    if (!acquisAnnonce && kActuel !== kDepart && kActuel >= untrack(() => acquisA)) {
      acquisAnnonce = true;
      const detail: DetailAcquis = { cle: 'fusions' };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  });

  const numeroAffiche = (jeton: Jeton) => (jeton.id === null ? 'inconnu' : String(jeton.id));
</script>

<div class="atelier" data-atelier>
  <div class="ligne-saisie">
    <label for={idSaisie}>Ta phrase{FINE}:</label>
    <input
      id={idSaisie}
      data-test="saisie"
      type="text"
      bind:value={texte}
      autocomplete="off"
      spellcheck="false"
      enterkeyhint="done"
    />
  </div>

  <p class="phrase-fusions">
    Avec <NombreManipulable
      canal={canalFusions}
      min={0}
      max={NB_FUSIONS}
      initiale={FUSIONS_AU_DEPART}
      etiquette="Nombre de fusions apprises"
      {verrou}
      testId="fusions"
    />
    {pluriel(k, 'fusion apprise', 'fusions apprises')},
    {#if nbCaracteres === 0}
      une phrase vide ne donne aucun jeton.
    {:else if nbCaracteres === 1}
      son seul caractère tient en <span class="calcule">{jetons.length}</span> jeton{FINE}:
    {:else}
      ses <span class="calcule">{nombre.format(nbCaracteres)}</span> caractères tiennent en
      <span class="calcule">{nombre.format(jetons.length)}</span>
      {pluriel(jetons.length, 'jeton', 'jetons')}{FINE}:
    {/if}
  </p>
  <p class="lecteur-ecran" aria-live="polite">{annonce}</p>

  <div class="bande" class:numeros={morceauxCaches} data-test="jetons">
    {#each affiches as { jeton, i, nouveau } (i + ':' + jeton.texte)}
      <span class="jeton" class:b={i % 2 === 1} class:nouveau data-jeton={numeroAffiche(jeton)}
        ><span class="morceau"
          >{#each segmentsVisibles(jeton.texte) as segment}{#if segment.blanc}<span class="blanc"
                >{segment.texte}</span
              >{:else}{segment.texte}{/if}{/each}</span
        ><span class="num">{numeroAffiche(jeton)}</span></span
      >
    {:else}
      <p class="vide">Tape une phrase pour la voir découpée.</p>
    {/each}
  </div>

  {#if nbCaracteres > 0}
    <p>
      Pour comparer, lettre par lettre{FINE}: <span class="calcule">{nombre.format(nbCaracteres)}</span>{FINE};
      mot par mot{FINE}: <span class="calcule">{nombre.format(nbMots)}</span>, mais avec un vocabulaire sans limite.
      {morceauxCaches
        ? `Voici la phrase telle que le modèle la reçoit, rien que des nombres${FINE}:`
        : `Sous chaque morceau, son numéro${FINE}:`}
      <button type="button" class="bascule" onclick={() => (morceauxCaches = !morceauxCaches)}
        >{morceauxCaches ? 'voir les morceaux' : 'cacher les morceaux'}</button
      >
      {morceauxCaches ? 'pour retrouver le texte.' : 'pour voir la phrase comme le modèle la reçoit.'}
    </p>
  {/if}

  {#if avecDernieresFusions}
    <DernieresFusions {canalFusions} />
  {/if}

  {@render children?.()}

  {#if defi}
    <div class="defi" class:reussi={defiReussi} data-defi>
      <h3>Défi</h3>
      <p>
        Écris une phrase d’au moins {defi.minCaracteres} caractères qui tient en {defi.maxJetons} jetons ou moins
        avec les {NB_FUSIONS} fusions. Astuce{FINE}: les mots qui reviennent souvent dans le texte d’apprentissage
        sont déjà des jetons entiers.
      </p>
      <p class="etat" data-test="defi">{etatDuDefi}</p>
      <p class="lecteur-ecran" aria-live="polite">{annonceDefi}</p>
    </div>
  {/if}
</div>

<style>
  .atelier {
    margin: 1em 0 1.6em;
  }

  /* Le champ de saisie : jaune, puisqu'il se manipule. */
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

  .calcule {
    font-family: var(--titres);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  /* La phrase découpée, qui reste du texte : elle passe à la ligne comme lui. */
  .bande {
    font-size: 30px;
    line-height: 1.2;
    margin: 0.2em 0 0.7em;
    padding: 16px 0 10px;
    border-top: 2px solid var(--indigo);
    border-bottom: 1px solid var(--brume);
    overflow-wrap: anywhere;
    font-variation-settings: 'opsz' 36;
  }

  .jeton {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    vertical-align: top;
    max-width: 100%;
    margin: 0 3px 8px 0;
  }

  .morceau {
    max-width: 100%;
    padding: 0 4px;
    background: var(--teinte-a);
    border-radius: 4px;
    white-space: pre-wrap;
    line-height: 1.32;
  }

  .jeton.b .morceau {
    background: var(--teinte-b);
  }

  /* Les espaces se voient (« ␣ »), mais plus discrètement que les lettres. */
  .blanc {
    color: var(--indigo-doux);
  }

  .num {
    font-family: var(--titres);
    font-weight: 500;
    font-size: 12px;
    line-height: 1;
    margin-top: 5px;
    color: var(--indigo-doux);
    font-variant-numeric: tabular-nums;
  }

  /* Morceaux cachés : la phrase telle que le modèle la reçoit, des nombres. */
  .numeros .morceau {
    display: none;
  }

  .numeros .num {
    font-size: 22px;
    font-weight: 600;
    color: var(--indigo);
    margin: 0;
    padding: 6px 7px;
    background: var(--teinte-a);
    border-radius: 4px;
  }

  .numeros .jeton.b .num {
    background: var(--teinte-b);
  }

  .vide {
    margin: 0 0 6px;
    font-size: 20px;
    font-style: italic;
    color: var(--indigo-doux);
  }

  /* La bascule : un bouton dans la phrase, souligné de jaune. */
  .bascule {
    font: inherit;
    color: var(--indigo);
    background: none;
    text-decoration: underline;
    text-decoration-color: var(--soleil);
    text-decoration-thickness: 5px;
    text-underline-offset: 4px;
    text-decoration-skip-ink: none;
    border: 0;
    border-radius: 4px;
    padding: 0 2px;
    cursor: pointer;
  }

  .bascule:hover {
    background: var(--soleil-pale);
    text-decoration-color: var(--soleil-vif);
  }

  /* Le défi, sous un filet, un peu plus petit que le texte, comme dans la
     maquette (19 px sur ordinateur : en 18 px, ses lignes dépasseraient 80
     signes dans la colonne de lecture). */
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

  .lecteur-ecran {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }

  @media (prefers-reduced-motion: no-preference) {
    .jeton.nouveau .morceau {
      animation: pose 0.25s ease-out;
    }

    @keyframes pose {
      from {
        opacity: 0.2;
      }

      to {
        opacity: 1;
      }
    }
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

    .bande {
      font-size: 24px;
    }

    .vide {
      font-size: 18px;
    }
  }
</style>
