<script lang="ts" module>
  // Les acquis déjà annoncés pendant ce chargement de page : chacun ne l'est
  // qu'une fois, même si le lecteur revient plusieurs fois à la septième étape.
  const acquisAnnonces = new Set<string>();
</script>

<script lang="ts">
  // L'animation de l'attention, pilotée par le lecteur : dans « Le forgeron
  // chauffe le fer puis il le tord », un mot pose une question aux autres, en
  // sept étapes (traits ; requête, clé, valeur ; scores ; division par √4 ;
  // masque ; softmax ; mélange). Le lecteur choisit le mot qui pose la
  // question et la tête, et avance d'une étape à la fois. Aux étapes 6 et 7,
  // la carte complète de la tête est un vrai tableau.
  //
  // Tous les nombres viennent du moteur du mini-modèle (detaillerExemple) ;
  // les textes, les barres et les couleurs de la carte, de
  // animation-attention.ts, où ils sont testés.
  //
  // Mouvement : les barres glissent en 300 ms (Tween), seulement après un
  // geste du lecteur. S'il préfère moins de mouvement, elles se posent tout
  // de suite, et la racine porte data-mouvement="reduit".
  //
  // Sans JavaScript : l'étape 1 et la carte complète de la tête de départ
  // (« de qui on parle ») sont dans le HTML, et les commandes sont cachées.
  //
  // À poser dans le MDX avec client:load, dans un <Verrou> :
  //   <AnimationAttention client:load verrou="attention" acquis="attention" />
  // Les commandes restent désactivées tant que le verrou n'est pas ouvert, et
  // l'acquis est annoncé (forge:acquis) la première fois que la septième
  // étape est atteinte.
  import { untrack } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { prefersReducedMotion, Tween } from 'svelte/motion';
  import { readable } from 'svelte/store';
  import { ouverture } from '../../lib/canal';
  import { typographier } from '../../lib/typo';
  import {
    arrondi2,
    caseClaire,
    classement,
    etapesAttention,
    explication,
    fondCarte,
    LEGENDE_CARTE_APRES,
    LEGENDE_CARTE_AVANT,
    legendeCarte,
    legendeVecteurs,
    lignesEtape,
    messageSansJs,
    NB_ETAPES,
    nomTete,
    partiesLigneEtat,
    phraseMelange,
    phraseRequeteNulle,
    pourcentPoids,
    repete,
    SOURCE_POIDS_NON_EXPLICATION,
    valeur,
    vecteur,
    type LigneMot,
  } from '../../lib/mini-modele/animation-attention';
  import { detaillerExemple, exempleAttention, type ExempleAttention } from '../../lib/mini-modele/exemple-attention';
  import type { DetailAcquis } from '../../scripts/chapitre';
  import ZoneDefilable from '../interactif/ZoneDefilable.svelte';

  interface Props {
    /** L'exemple à montrer ; celui de « Le forgeron chauffe le fer puis il le tord » par défaut. */
    exemple?: ExempleAttention;
    /** Le verrou qui désactive les commandes tant que son pari n'est pas fait. */
    verrou?: string;
    /** La clé de l'acquis gagné la première fois que la septième étape est atteinte. */
    acquis?: string;
    /** Le mot qui pose la question au départ, compté à partir de 0 : 6, « il ». */
    requeteInitiale?: number;
    /** La tête de départ, comptée à partir de 0 : 1, « de qui on parle » (la « Tête 2 »). */
    teteInitiale?: number;
  }

  const { exemple = exempleAttention, verrou, acquis, requeteInitiale = 6, teteInitiale = 1 }: Props = $props();

  const DUREE_MS = 300;
  const id = $props.id();

  // L'exemple, son détail et le verrou sont lus une fois (untrack) : un îlot
  // ne change pas d'exemple en cours de route.
  const ex = untrack(() => exemple);
  const details = detaillerExemple(ex);
  // Ce que la légende dit des vecteurs vient de l'exemple : null s'il n'en dit rien.
  const vecteursLegende = legendeVecteurs(ex);
  const depart = untrack(() => ({ requete: requeteInitiale, tete: teteInitiale }));
  if (!Number.isInteger(depart.requete) || depart.requete < 0 || depart.requete >= ex.jetons.length) {
    throw new RangeError(
      `AnimationAttention : requeteInitiale va de 0 à ${ex.jetons.length - 1} (reçu ${depart.requete}).`,
    );
  }
  if (!Number.isInteger(depart.tete) || depart.tete < 0 || depart.tete >= details.length) {
    throw new RangeError(`AnimationAttention : teteInitiale va de 0 à ${details.length - 1} (reçu ${depart.tete}).`);
  }

  const nomDuVerrou = untrack(() => verrou);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let etape = $state(1);
  let tete = $state(depart.tete);
  let requete = $state(depart.requete);

  const d = $derived(details[tete]);
  const taille = $derived(d.requetes[0].length);
  const titres = $derived(etapesAttention(taille));
  const lignes = $derived(lignesEtape(etape, d, requete));
  const etat = $derived(partiesLigneEtat(etape, ex, d, requete));
  const texteExplication = $derived(explication(etape, ex, d, requete));
  const noteCarte = $derived(phraseRequeteNulle(ex, d));
  // Le mot le plus regardé, pour comparer sa valeur à la sortie (étape 7) ;
  // null si le mot choisi ne voit que lui-même ou partage à parts égales.
  const plusRegarde = $derived.by(() => {
    if (requete === 0) return null;
    const rangs = classement(d, requete);
    return d.poids[requete][rangs[0]] === d.poids[requete][rangs[rangs.length - 1]] ? null : rangs[0];
  });

  /** Le mot entre guillemets, avec ses espaces fines : « il ». */
  const cite = (i: number) => typographier(`« ${ex.jetons[i]} »`);

  // ---------- Les barres ----------

  interface Barre {
    debut: number;
    largeur: number;
  }

  const barres = (ls: LigneMot[]): Barre[] => ls.map(({ debut, largeur }) => ({ debut, largeur }));

  // Au chargement, les barres sont déjà à leur place : pas d'animation d'entrée.
  const glisse = new Tween<Barre[]>(
    untrack(() => barres(lignes)),
    { duration: DUREE_MS, easing: cubicOut },
  );

  /** Après un geste du lecteur : les barres glissent vers leur nouvelle place, ou s'y posent. */
  function poserBarres(): void {
    void glisse.set(barres(lignes), { duration: prefersReducedMotion.current ? 0 : DUREE_MS });
  }

  // ---------- Les gestes du lecteur ----------

  function allerA(nouvelle: number): void {
    if (!actif || nouvelle < 1 || nouvelle > NB_ETAPES || nouvelle === etape) return;
    etape = nouvelle;
    poserBarres();
    if (nouvelle === NB_ETAPES && acquis !== undefined && !acquisAnnonces.has(acquis)) {
      acquisAnnonces.add(acquis);
      const detail: DetailAcquis = { cle: acquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  }

  function choisirMot(i: number): void {
    if (!actif || i === requete) return;
    requete = i;
    poserBarres();
  }

  function choisirTete(t: number): void {
    if (!actif || t === tete) return;
    tete = t;
    poserBarres();
  }
</script>

<!-- Le nom d'un mot ; s'il revient dans la phrase (« Le », « le », « le »), les lecteurs d'écran entendent aussi sa place.
     L'espace est dans l'expression : Svelte retire celle qui ouvrirait la balise. -->
{#snippet nomMot(i: number)}{ex.jetons[i]}{#if repete(ex, i)}<span class="vh">{` (mot ${i + 1})`}</span>{/if}{/snippet}

<figure
  class="attention"
  data-attention
  data-mouvement={prefersReducedMotion.current ? 'reduit' : 'normal'}
  data-etape={etape}
  data-tete={tete}
  data-requete={requete}
>
  <div class="commandes">
    <div class="choix-mot" role="group" aria-labelledby="{id}-mots">
      <span class="intitule" id="{id}-mots">Le mot qui pose la question</span>
      <span class="phrase">
        {#each ex.jetons as _, i (i)}
          <button
            type="button"
            class="mot"
            aria-pressed={i === requete}
            data-test="att-mot"
            data-mot={i}
            disabled={!actif}
            onclick={() => choisirMot(i)}>{@render nomMot(i)}</button
          >
        {/each}
      </span>
    </div>

    <div class="choix-tete" role="group" aria-labelledby="{id}-tetes">
      <span class="intitule" id="{id}-tetes">La tête</span>
      <span class="tetes">
        {#each ex.tetes as _, t (t)}
          <button
            type="button"
            class="bascule-soleil"
            aria-pressed={t === tete}
            data-test="att-tete"
            data-tete={t}
            disabled={!actif}
            onclick={() => choisirTete(t)}>{nomTete(ex, t)}</button
          >
        {/each}
      </span>
    </div>

    <div class="pas-a-pas">
      <button
        type="button"
        class="bouton-relief"
        data-test="att-precedente"
        aria-disabled={!actif || etape === 1}
        onclick={() => allerA(etape - 1)}>Étape précédente</button
      >
      <span class="compteur" data-test="att-compteur">Étape {etape} sur {NB_ETAPES}</span>
      <button
        type="button"
        class="bouton-relief"
        data-test="att-suivante"
        aria-disabled={!actif || etape === NB_ETAPES}
        onclick={() => allerA(etape + 1)}>Étape suivante</button
      >
    </div>
  </div>
  <p class="sans-js">{messageSansJs(ex, depart.tete)}</p>

  <p class="titre-etape" data-test="att-titre">{titres[etape - 1].titre}</p>
  <p class="explication">{texteExplication}</p>

  {#if etape === 1}
    <!-- Les tableaux sont dans des zones qui défilent : un exemple plus large ne fait jamais déborder la page. -->
    <ZoneDefilable etiquette="Traits de chaque mot, défilable">
      <table class="traits" data-test="att-traits">
        <caption class="vh">Les traits de chaque mot</caption>
        <thead>
          <tr>
            <td></td>
            {#each ex.traits as trait (trait)}
              <th scope="col"><span>{trait}</span></th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each ex.jetons as _, i (i)}
            <tr>
              <th scope="row" class:choisi={i === requete}>{@render nomMot(i)}</th>
              {#each ex.x[i] as v, k (k)}
                <td class:actif={v !== 0}>{valeur(v)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </ZoneDefilable>
  {:else if etape === 2}
    <dl class="vecteurs">
      <div>
        <dt>requête q de {cite(requete)}</dt>
        <dd>{vecteur(d.requetes[requete])}</dd>
      </div>
      <div>
        <dt>clé k de {cite(requete)}</dt>
        <dd>{vecteur(d.cles[requete])}</dd>
      </div>
      <div>
        <dt>valeur v de {cite(requete)}</dt>
        <dd>{vecteur(d.valeurs[requete])}</dd>
      </div>
    </dl>
    <p class="titre-tableau" id="{id}-cles">La clé k de chaque mot</p>
    <ZoneDefilable etiquette="Clés de chaque mot, défilable">
      <table class="cles" data-test="att-cles" aria-labelledby="{id}-cles">
        <thead>
          <tr>
            <td></td>
            <th scope="col" colspan={taille}>clé k</th>
          </tr>
        </thead>
        <tbody>
          {#each ex.jetons as _, i (i)}
            <tr>
              <th scope="row" class:choisi={i === requete}>{@render nomMot(i)}</th>
              {#each d.cles[i] as v, k (k)}
                <td>{valeur(v)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </ZoneDefilable>
  {:else}
    <ol class="lignes" class:axe={etape <= 5} data-test="att-lignes">
      {#each lignes as l (l.mot)}
        {@const b = glisse.current[l.mot]}
        <li class="ligne" class:masquee={l.masque}>
          <span class="etiquette" class:choisi={l.mot === requete}>{@render nomMot(l.mot)}</span>
          <span class="piste" aria-hidden="true">
            <span
              class="barre"
              class:negative={l.negatif}
              data-test="att-barre"
              data-mot={l.mot}
              data-cible={String(l.largeur)}
              style:left="{arrondi2(b.debut)}%"
              style:width="{arrondi2(b.largeur)}%"
            ></span>
          </span>
          <span class="nombre" data-test="att-nombre" data-mot={l.mot}>{l.texte}</span>
        </li>
      {/each}
    </ol>
    {#if etape === NB_ETAPES}
      <dl class="vecteurs sortie" data-test="att-sortie">
        <div>
          <dt>nouvelle valeur de {cite(requete)}</dt>
          <dd>{vecteur(d.sorties[requete])}</dd>
        </div>
        {#if plusRegarde !== null}
          <div>
            <dt>valeur v de {cite(plusRegarde)}</dt>
            <dd>{vecteur(d.valeurs[plusRegarde])}</dd>
          </div>
        {/if}
      </dl>
      <p class="phrase-fin" data-test="att-phrase">{phraseMelange(ex, d, requete)}</p>
    {/if}
  {/if}

  <!-- « Étape 6 sur 7 : softmax. » n'est lu qu'aux lecteurs d'écran : le compteur et le titre le montrent
       déjà. À l'étape 7, toute la ligne l'est : la phrase calculée, juste au-dessus, dit la même chose. -->
  <p class="etat" class:vh={etape === NB_ETAPES} role="status" data-test="att-etat">
    <span class="vh">{`${etat.ou} `}</span>{etat.phrase}
  </p>

  <!-- La carte complète : aux étapes 6 et 7, et sans JavaScript (la tête de départ, à l'étape 1). -->
  <div class="carte" class:seulement-sans-js={etape < 6}>
    <!-- Le titre du tableau est hors de la zone qui défile : sur un téléphone, il reste lisible en entier. -->
    <p class="titre-tableau" id="{id}-carte" data-test="att-carte-titre">{legendeCarte(ex, tete)}</p>
    <!-- Sur un téléphone (fenêtre de moins de 480 px, le seuil par défaut), la carte est plus large que la colonne :
         l'indice invite à la faire défiler, et une colonne coupée au bord le montre. -->
    <ZoneDefilable
      etiquette="Carte complète de la tête, défilable"
      indice="Fais défiler la carte vers la droite pour voir les autres colonnes."
      testIndice="att-indice-defile"
    >
      <table data-test="att-carte" aria-labelledby="{id}-carte">
        <thead>
          <tr>
            <td></td>
            {#each ex.jetons as _, j (j)}
              <th scope="col">{@render nomMot(j)}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each ex.jetons as _, i (i)}
            <tr>
              <th scope="row" class:choisi={i === requete}>{@render nomMot(i)}</th>
              {#each d.scores[i] as score, j (j)}
                {#if score === null}
                  <td class="masque"><span aria-hidden="true">—</span><span class="vh">masqué</span></td>
                {:else}
                  {@const p = arrondi2(d.poids[i][j] * 100) / 100}
                  <td class:claire={caseClaire(p)} style:--fond="{fondCarte(p)}%">{pourcentPoids(d.poids[i][j])}</td>
                {/if}
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </ZoneDefilable>
    {#if noteCarte !== null}
      <p class="note-carte">{noteCarte}</p>
    {/if}
  </div>

  <!-- La première partie de la légende vient de l'exemple (d'où viennent ses vecteurs). La seconde parle de
       la carte, avec sa source : elle ne s'affiche qu'avec elle. -->
  <figcaption class="legende" data-test="att-legende">
    {#if vecteursLegende !== null}{vecteursLegende}{/if}<span class="legende-carte" class:seulement-sans-js={etape < 6}
      >{`${vecteursLegende !== null ? ' ' : ''}${LEGENDE_CARTE_AVANT}`}<a
        href={SOURCE_POIDS_NON_EXPLICATION.url}
        lang="en"
        data-test="att-source">{SOURCE_POIDS_NON_EXPLICATION.titre}</a
      >{LEGENDE_CARTE_APRES}</span
    >
  </figcaption>
</figure>

<style>
  .attention {
    margin: 1em 0 1.6em;
  }

  /* ---------- Les commandes ---------- */

  .commandes {
    margin: 0 0 20px;
  }

  .intitule {
    display: block;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 15px;
    line-height: 1.3;
    color: var(--indigo-doux);
    margin: 0 0 4px;
  }

  .choix-mot,
  .choix-tete {
    margin: 0 0 14px;
  }

  /* Le mot qui pose la question : la phrase elle-même, un bouton par mot,
     souligné de jaune (ça se manipule) ; le mot choisi est en soleil. */
  .phrase {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 2px;
    font-size: 25px;
    line-height: 1.25;
    font-variation-settings: 'opsz' 36;
  }

  .mot {
    font: inherit;
    color: var(--indigo);
    background: none;
    border: 0;
    border-radius: 6px;
    padding: 3px 6px 5px;
    cursor: pointer;
    text-decoration: underline;
    text-decoration-color: var(--soleil);
    text-decoration-thickness: 3px;
    text-underline-offset: 6px;
    text-decoration-skip-ink: none;
  }

  .mot:hover:not(:disabled) {
    background: var(--soleil-pale);
    text-decoration-color: var(--soleil-vif);
  }

  .mot[aria-pressed='true'] {
    background: var(--soleil);
    text-decoration-color: transparent;
  }

  .mot:disabled {
    cursor: default;
  }

  /* Les têtes : deux bascules soulignées de jaune (.bascule-soleil, src/styles/commandes.css) ;
     celle qui est choisie est en soleil. Ici, leur police et leurs marges intérieures. */
  .tetes {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 12px;
  }

  .bascule-soleil {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.3;
    padding: 4px 6px;
  }

  /* Les étapes : les boutons reprennent ceux du mini-modèle (.bouton-relief :
     bord indigo, ombre décalée, soleil au survol). Ici, leur police et leurs
     marges intérieures. */
  .pas-a-pas {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 18px;
  }

  .compteur {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    font-variant-numeric: tabular-nums;
  }

  .bouton-relief {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 18px;
    line-height: 1.15;
    padding: 10px 16px;
  }

  /* Sans JavaScript, les commandes ne feraient rien : une phrase les remplace,
     et la carte de la tête de départ s'affiche. */
  .sans-js,
  .seulement-sans-js {
    display: none;
  }

  @media (scripting: none) {
    .commandes {
      display: none;
    }

    .sans-js {
      display: block;
      font-style: italic;
    }

    .seulement-sans-js {
      display: block;
    }

    .legende-carte.seulement-sans-js {
      display: inline;
    }
  }

  /* ---------- L'étape ---------- */

  .titre-etape {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 22px;
    line-height: 1.25;
    margin: 0 0 6px;
  }

  .explication {
    margin: 0 0 16px;
  }

  table {
    border-collapse: collapse;
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
  }

  caption,
  .titre-tableau {
    caption-side: top;
    text-align: left;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 15px;
    line-height: 1.35;
    color: var(--indigo-doux);
    padding: 0 0 6px;
  }

  .titre-tableau {
    margin: 0;
  }

  th[scope='row'] {
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
    padding: 0 10px 0 4px;
    border-radius: 4px;
  }

  th.choisi,
  .etiquette.choisi {
    background: var(--soleil);
  }

  /* Étape 1 : les traits, un carré par trait ; les noms des traits, debout. */
  .traits {
    font-size: 15px;
  }

  .traits thead th {
    vertical-align: bottom;
    padding: 0 0 6px;
    font-weight: 600;
    font-size: 14px;
    color: var(--indigo-doux);
  }

  .traits thead th span {
    display: inline-block;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    white-space: nowrap;
    line-height: 1;
  }

  .traits thead td {
    background: none;
  }

  .traits td {
    width: 28px;
    height: 28px;
    padding: 0;
    text-align: center;
    border: 2px solid var(--papier);
    background: var(--brume-claire);
    color: var(--indigo-doux);
  }

  .traits td.actif {
    background: var(--indigo);
    color: var(--papier);
    font-weight: 700;
  }

  /* Étape 2 : les trois vecteurs du mot choisi, puis la clé de chaque mot. */
  .vecteurs {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 2px 16px;
    margin: 0 0 16px;
    font-family: var(--titres);
    font-size: 17px;
  }

  .vecteurs > div {
    display: contents;
  }

  .vecteurs dt {
    color: var(--indigo-doux);
  }

  .vecteurs dd {
    margin: 0;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .cles {
    font-size: 16px;
  }

  .cles thead th {
    font-weight: 600;
    font-size: 14px;
    color: var(--indigo-doux);
    padding: 0 0 4px;
  }

  .cles td {
    min-width: 2.2em;
    padding: 3px 6px;
    text-align: right;
  }

  .cles tbody tr {
    border-top: 1px solid var(--brume);
  }

  /* Étapes 3 à 7 : une ligne par mot, sa barre et son nombre. */
  .lignes {
    list-style: none;
    margin: 0;
    padding: 0;
    font-family: var(--titres);
    font-size: 16px;
  }

  .ligne {
    display: grid;
    grid-template-columns: 6.4em minmax(0, 1fr) 4.4em;
    align-items: center;
    gap: 10px;
    min-height: 30px;
  }

  .etiquette {
    justify-self: start;
    font-weight: 600;
    padding: 0 4px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .piste {
    position: relative;
    height: 14px;
    background: var(--brume-claire);
  }

  /* Aux étapes 3 à 5, l'axe central : les scores négatifs partent à gauche. */
  .axe .piste::before {
    content: '';
    position: absolute;
    left: 50%;
    top: -8px;
    bottom: -8px;
    border-left: 1px solid var(--indigo-doux);
  }

  .barre {
    position: absolute;
    top: 0;
    bottom: 0;
    background: var(--indigo);
  }

  .barre.negative {
    background: var(--lavande);
  }

  .nombre {
    text-align: right;
    font-weight: 600;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .masquee .etiquette {
    color: var(--indigo-doux);
  }

  .masquee .piste {
    background: none;
    outline: 1px dashed var(--lavande);
    outline-offset: -1px;
  }

  .masquee .nombre {
    font-weight: 400;
    font-style: italic;
    color: var(--indigo-doux);
  }

  .sortie {
    margin: 16px 0 6px;
  }

  .phrase-fin {
    margin: 0;
  }

  .etat {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.4;
    margin: 16px 0 0;
    min-height: 1.4em;
  }

  /* ---------- La carte ---------- */

  .carte {
    margin: 22px 0 0;
  }

  /* Bordures séparées : avec des bordures fusionnées, celles des cases qui
     défilent passeraient par-dessus la colonne des mots, restée en place. */
  .carte table {
    font-size: 14px;
    border-collapse: separate;
    border-spacing: 0;
  }

  .carte thead th {
    font-weight: 600;
    font-size: 13px;
    color: var(--indigo-doux);
    padding: 0 3px 4px;
    white-space: nowrap;
    text-align: center;
  }

  /* Le fond d'une case : d'autant plus indigo que le poids est grand
     (--fond, calculé par fondCarte) ; au-delà de 0,5, le texte passe en papier.
     Le filet blanc entre deux cases est dessiné dans la case (ombre intérieure). */
  .carte td {
    min-width: 3.3em;
    padding: 5px 4px;
    text-align: center;
    white-space: nowrap;
    border: 0;
    box-shadow: inset -1px -1px 0 var(--papier);
    background: color-mix(in srgb, var(--indigo) var(--fond, 0%), var(--papier));
    color: var(--indigo);
  }

  .carte td.claire {
    color: var(--papier);
  }

  .carte td.masque {
    background: var(--brume-claire);
    color: var(--indigo-doux);
  }

  /* Quand la carte défile (sur un téléphone), la colonne des mots reste en place. */
  .carte th[scope='row'],
  .carte thead td {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--papier);
    border-radius: 0; /* des coins arrondis laisseraient voir les cases qui passent dessous */
  }

  .carte th[scope='row'].choisi {
    background: var(--soleil);
  }

  .carte thead td {
    min-width: 0;
    box-shadow: none;
  }

  .note-carte {
    font-size: 17px;
    line-height: 1.5;
    margin: 10px 0 0;
  }

  .legende {
    font-family: var(--titres);
    font-size: 15px;
    line-height: 1.45;
    color: var(--indigo-doux);
    margin: 14px 0 0;
  }

  @media (max-width: 720px) {
    .phrase {
      font-size: 22px;
    }

    /* Le compteur au-dessus, les deux boutons côte à côte en dessous. */
    .pas-a-pas {
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    .compteur {
      grid-column: 1 / -1;
      grid-row: 1;
    }

    .bouton-relief {
      font-size: 16px;
      padding: 9px 8px;
    }

    .ligne {
      grid-template-columns: 5.6em minmax(0, 1fr) 4.2em;
      gap: 8px;
    }

    /* Des colonnes plus étroites : sur un téléphone, une colonne coupée au
       bord de la zone montre qu'il en reste d'autres à droite. */
    .carte table {
      font-size: 13px;
    }

    .carte td {
      min-width: 2.9em;
      padding: 5px 3px;
    }
  }
</style>
