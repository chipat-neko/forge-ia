<script lang="ts" module>
  // Les acquis déjà annoncés pendant ce chargement de page : chacun ne l'est
  // qu'une fois, même si le lecteur change encore de modèle ou de carte.
  const acquisAnnonces = new Set<string>();
</script>

<script lang="ts">
  // Le calculateur de coût : une phrase que le lecteur règle (le modèle, les
  // jetons lus par paramètre, le nombre de cartes, la carte, l'efficacité),
  // puis le relevé de ce que l'entraînement demande : le calcul, la durée, la
  // mémoire pour l'entraîner et pour s'en servir, le plafond de génération,
  // l'électricité au tarif d'EDF et la location, chaque prix avec sa source
  // et sa date. Dessous, le repère mesuré : ton IA sur ce PC.
  //
  // Tous les nombres et toutes les phrases viennent de
  // src/lib/calculateur/releve.ts, où ils sont testés ; ce composant ne fait
  // que les mettre en page. Les nombres jaunes vivent dans des canaux
  // (« <nom>:jetons », « <nom>:cartes », « <nom>:efficacite »).
  //
  // L'efficacité part de la valeur par défaut de la catégorie de la carte
  // (50 % pour une carte grand public, 40 % sinon), et la suit quand le
  // lecteur change de carte, tant qu'il ne l'a pas réglée lui-même. Le
  // composant le sait par un drapeau, posé dès que le canal de l'efficacité
  // change sans lui. Quand elle suit la carte, la ligne d'état le dit.
  //
  // Sans JavaScript : la phrase, le relevé du réglage de départ, les
  // formules dépliées, le repère et les sources sont dans le HTML ; les
  // sélecteurs, qui ne feraient rien, laissent la place à leur valeur.
  //
  // À poser dans le MDX avec client:load, dans un <Verrou> :
  //   <Calculateur client:load verrou="calculateur" acquis="calcul" />
  // Les réglages restent désactivés tant que le verrou n'est pas ouvert, et
  // l'acquis est annoncé (forge:acquis) au premier changement de modèle ou
  // de carte. Le plan 5 l'ouvrira déjà réglé avec `initial`.
  import { onMount, untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../lib/canal';
  import { decimalesUtiles, nombre } from '../../lib/nombres';
  import { ELECTRICITE, materiel as materielDe, TAUX_DE_CHANGE, type Source } from '../../lib/calculateur/donnees';
  import { formaterDate, formaterPrix } from '../../lib/calculateur/formats';
  import {
    annonce,
    calculerReleve,
    CARTES_PROPOSEES,
    EFFICACITE_MAX_POURCENT,
    EFFICACITE_MIN_POURCENT,
    efficaciteParDefautPourcent,
    formulesDuCalcul,
    GROUPES_MATERIELS,
    GROUPES_MODELES,
    JETONS_PAR_PARAMETRE_PROPOSES,
    lignesReperes,
    phraseCommeLesGrands,
    phraseRepere,
    reglageDeDepart,
    sourcesDesReperes,
    texteCalcul,
    texteDuree,
    texteElectricite,
    texteGeneration,
    texteJetons,
    texteLocation,
    texteMemoire,
    texteService,
    type ReglageInitial,
  } from '../../lib/calculateur/releve';
  import { JETONS_PAR_PARAMETRE, MATERIEL_DES_MESURES, MESURES_TON_IA } from '../../lib/calculateur/ton-ia';
  import type { DetailAcquis } from '../../scripts/chapitre';
  import NombreManipulable from '../interactif/NombreManipulable.svelte';

  interface Props {
    /** Le nom de l'instance : data-calculateur, et le préfixe des canaux ; « calc » par défaut. */
    nom?: string;
    /** Le verrou qui désactive les réglages tant que son pari n'est pas fait. */
    verrou?: string;
    /** La clé de l'acquis gagné au premier changement de modèle ou de carte. */
    acquis?: string;
    /** Le réglage de départ ; l'efficacité est une fraction (0,4 pour 40 %). */
    initial?: ReglageInitial;
  }

  const { nom = 'calc', verrou, acquis, initial }: Props = $props();

  const FINE = '\u202F';
  const INSECABLE = '\u00A0';
  const id = $props.id();

  // Le réglage de départ, les canaux et le verrou sont lus une fois (untrack) :
  // un îlot ne change pas de nom ni de point de départ en cours de route.
  const depart = untrack(() => reglageDeDepart(initial));
  const prefixe = untrack(() => nom);
  const jetonsCanal = canal<number>(`${prefixe}:jetons`, JETONS_PAR_PARAMETRE_PROPOSES.indexOf(depart.jetonsParParametre));
  const cartesCanal = canal<number>(`${prefixe}:cartes`, CARTES_PROPOSEES.indexOf(depart.cartes));
  const efficaciteCanal = canal<number>(`${prefixe}:efficacite`, depart.efficacitePourcent);
  const nomDuVerrou = untrack(() => verrou);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);
  const actif = $derived($ouvert);

  let modele = $state(depart.modele);
  let materiel = $state(depart.materiel);
  let voirCalcul = $state(false);
  // Vrai dès que le lecteur a réglé l'efficacité (ou si `initial` la donne) : elle ne suit plus la carte.
  let efficaciteReglee = untrack(() => initial?.efficacite !== undefined);
  // Vrai pendant que le calculateur pose lui-même l'efficacité : ce n'est pas le lecteur.
  let poseParLeCalculateur = false;
  // Vrai si l'efficacité vient de suivre la carte : la prochaine annonce le dit.
  let efficaciteAAnnoncer = false;

  const rel = $derived(
    calculerReleve({
      modele,
      materiel,
      cartes: CARTES_PROPOSEES[$cartesCanal],
      jetonsParParametre: JETONS_PAR_PARAMETRE_PROPOSES[$jetonsCanal],
      efficacitePourcent: $efficaciteCanal,
    }),
  );
  const generation = $derived(texteGeneration(rel));
  const electricite = $derived(texteElectricite(rel));
  const repere = $derived(phraseRepere(rel));
  const formules = $derived(formulesDuCalcul(rel));
  const lignes = lignesReperes();
  const sourcesReperes = sourcesDesReperes();

  // La ligne d'état ne parle qu'après un réglage du lecteur, pas au chargement.
  let etat = $state('');
  let premierPassage = true;
  $effect(() => {
    const r = rel;
    if (premierPassage) {
      premierPassage = false;
      return;
    }
    const suivie = efficaciteAAnnoncer;
    efficaciteAAnnoncer = false;
    etat = annonce(r, suivie);
  });

  onMount(() => {
    // Le canal prévient tout de suite avec sa valeur : ce premier appel n'est pas un réglage.
    let premier = true;
    return efficaciteCanal.subscribe(() => {
      if (premier) {
        premier = false;
        return;
      }
      if (!poseParLeCalculateur) efficaciteReglee = true;
    });
  });

  function annoncerAcquis(): void {
    if (acquis === undefined || acquisAnnonces.has(acquis)) return;
    acquisAnnonces.add(acquis);
    const detail: DetailAcquis = { cle: acquis };
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
  }

  function changerModele(evenement: Event): void {
    if (!actif) return;
    modele = (evenement.currentTarget as HTMLSelectElement).value;
    annoncerAcquis();
  }

  function changerMateriel(evenement: Event): void {
    if (!actif) return;
    const nouveau = (evenement.currentTarget as HTMLSelectElement).value;
    materiel = nouveau;
    // L'efficacité suit la catégorie de la carte, tant que le lecteur ne l'a pas réglée.
    const defaut = efficaciteParDefautPourcent(nouveau);
    if (!efficaciteReglee && efficaciteCanal.get() !== defaut) {
      poseParLeCalculateur = true;
      efficaciteCanal.set(defaut);
      poseParLeCalculateur = false;
      efficaciteAAnnoncer = true;
    }
    annoncerAcquis();
  }

  const texteJetonsRegle = (i: number) => nombre(JETONS_PAR_PARAMETRE_PROPOSES[i]);
  const texteCartes = (i: number) => nombre(CARTES_PROPOSEES[i]);
  const texteEfficacite = (p: number) => `${nombre(p)}${FINE}%`;
  const date = (s: Source) => `relevé le ${formaterDate(s.releveLe)}`;
  /** Un nombre et son unité, liés par une espace insécable : « 2,69 $ ». */
  const lie = (texte: string) => texte.replace(/ /g, INSECABLE);
  const mesures = MESURES_TON_IA.tres_grand.source;
  const materielDesMesures = materielDe(MATERIEL_DES_MESURES).nom;
  const mesuresMini = MESURES_TON_IA.mini.source;
</script>

<!-- Les sources d'une formule ou d'une donnée : « titre » (lien), séparées par des points-virgules. -->
{#snippet liens(sources: readonly Source[])}{#each sources as s, i (i)}{#if i > 0}{`${FINE}; `}{/if}<a href={s.url}
      >{s.titre}</a
    >{/each}{/snippet}

<div class="calculateur" data-calculateur={nom}>
  <p class="phrase" data-test="calc-phrase">
    Entraîner <select
      class="selecteur"
      aria-label="Le modèle à entraîner"
      data-test="calc-modele"
      value={modele}
      disabled={!actif}
      onchange={changerModele}
    >
      {#each GROUPES_MODELES as groupe (groupe.titre)}
        <optgroup label={groupe.titre}>
          {#each groupe.modeles as m (m.id)}
            <option value={m.id} selected={m.id === modele}>{m.nom}</option>
          {/each}
        </optgroup>
      {/each}
    </select><span class="fixe" data-test="calc-modele-fixe">{rel.modele.nom}</span>
    en lui faisant lire <NombreManipulable
      canal="{nom}:jetons"
      min={0}
      max={JETONS_PAR_PARAMETRE_PROPOSES.length - 1}
      initiale={JETONS_PAR_PARAMETRE_PROPOSES.indexOf(depart.jetonsParParametre)}
      etiquette="Jetons lus par paramètre"
      texte={texteJetonsRegle}
      {verrou}
      testId="calc-jetons"
    />
    {rel.reglage.jetonsParParametre > 1 ? 'jetons' : 'jeton'} par paramètre, soit
    <span class="calcule" data-test="calc-jetons-total">{texteJetons(rel)}</span> de jetons, avec <span class="insecable"
      ><NombreManipulable
        canal="{nom}:cartes"
        min={0}
        max={CARTES_PROPOSEES.length - 1}
        initiale={CARTES_PROPOSEES.indexOf(depart.cartes)}
        etiquette="Nombre de cartes"
        texte={texteCartes}
        {verrou}
        testId="calc-cartes"
      />{INSECABLE}×</span
    >
    <select
      class="selecteur"
      aria-label="La carte graphique"
      data-test="calc-materiel"
      value={materiel}
      disabled={!actif}
      onchange={changerMateriel}
    >
      {#each GROUPES_MATERIELS as groupe (groupe.titre)}
        <optgroup label={groupe.titre}>
          {#each groupe.materiels as m (m.id)}
            <option value={m.id} selected={m.id === materiel}>{m.nom}</option>
          {/each}
        </optgroup>
      {/each}
    </select><span class="fixe" data-test="calc-materiel-fixe">{rel.materiel.nom}</span>, à <NombreManipulable
      canal="{nom}:efficacite"
      min={EFFICACITE_MIN_POURCENT}
      max={EFFICACITE_MAX_POURCENT}
      initiale={depart.efficacitePourcent}
      etiquette="Efficacité"
      texte={texteEfficacite}
      {verrou}
      testId="calc-efficacite"
    />
    d’efficacité.
  </p>
  <p class="sans-js">Sans JavaScript, le calculateur garde son réglage de départ{FINE}: le relevé ci-dessous est le sien.</p>

  <table class="releve">
    <caption>Le relevé</caption>
    <tbody>
      <tr>
        <th scope="row">Calcul</th>
        <td data-test="calc-calcul">{texteCalcul(rel)}</td>
      </tr>
      <tr>
        <th scope="row">Durée</th>
        <td data-test="calc-duree">{texteDuree(rel)}</td>
      </tr>
      <tr>
        <th scope="row">Mémoire pour l’entraîner</th>
        <td data-test="calc-memoire">{texteMemoire(rel)}</td>
      </tr>
      <tr>
        <th scope="row">Mémoire pour s’en servir</th>
        <td data-test="calc-service">{texteService(rel)}</td>
      </tr>
      {#if generation !== null}
        <tr>
          <th scope="row">Génération, au plus</th>
          <td data-test="calc-generation">{generation}</td>
        </tr>
      {/if}
      {#if electricite !== null}
        <tr>
          <th scope="row">Électricité</th>
          <td data-test="calc-electricite">{electricite}</td>
        </tr>
      {/if}
      <tr>
        <th scope="row">Location</th>
        <td data-test="calc-cout">{texteLocation(rel)}</td>
      </tr>
    </tbody>
  </table>

  {#if repere !== null}
    <p class="repere" data-test="calc-repere-phrase">{repere}</p>
  {/if}

  <p class="voir">
    <button
      type="button"
      class="bascule"
      aria-expanded={voirCalcul}
      aria-controls="{id}-formules"
      data-test="calc-voir"
      disabled={!actif}
      onclick={() => (voirCalcul = !voirCalcul)}>{voirCalcul ? 'Cacher le calcul' : 'Voir le calcul'}</button
    >
  </p>
  <div class="formules" class:ouvert={voirCalcul} id="{id}-formules" data-test="calc-formules">
    {#each formules as f (f.cle)}
      <div class="formule" data-formule={f.cle}>
        <p class="titre-formule">{f.titre}</p>
        <p class="calcul">{f.formule}</p>
        <p class="sens">
          {f.explication}
          <span class="sources-formule">{f.sources.length > 1 ? 'Sources' : 'Source'}{FINE}: {@render liens(f.sources)}.</span>
        </p>
      </div>
    {/each}
  </div>

  <h3 class="titre-section">Repère mesuré{FINE}: ton IA sur ce PC</h3>
  <p class="intro-reperes">
    Les débits de ton IA, mesurés pendant son entraînement sur la carte (une {materielDesMesures}, celle de ce PC) et sur
    le processeur, et la durée qu’on en tire pour {nombre(JETONS_PAR_PARAMETRE)} jetons par paramètre.
  </p>
  <p class="indice-defile">Fais défiler le tableau vers la droite pour voir les autres colonnes.</p>
  <div class="defile" role="region" aria-label="Débits mesurés, défilable" tabindex="0" data-test="calc-reperes">
    <table class="reperes">
      <thead>
        <tr>
          <td rowspan="2"></td>
          <th scope="colgroup" colspan="3">Sur la carte</th>
          <th scope="colgroup" colspan="2" class="groupe-processeur">Sur le processeur</th>
        </tr>
        <tr>
          <th scope="col">par seconde</th>
          <th scope="col">durée</th>
          <th scope="col">efficacité</th>
          <th scope="col" class="groupe-processeur">par seconde</th>
          <th scope="col">durée</th>
        </tr>
      </thead>
      <tbody>
        {#each lignes as l (l.cle)}
          <tr class:choisie={rel.modele.tonIA === l.cle}>
            <th scope="row">{l.nom}<span class="parametres">{l.parametres}</span></th>
            <td>{l.carteDebit}</td>
            <td>{l.carteDuree}</td>
            <td>{l.efficacite}</td>
            <td class="groupe-processeur">{l.processeurDebit}</td>
            <td>{l.processeurDuree}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="comme-les-grands" data-test="calc-comme-les-grands">{phraseCommeLesGrands(rel)}</p>
  <ul class="sources-reperes" data-test="calc-sources-reperes">
    {#each sourcesReperes as r (r.modele)}
      <li data-repere={r.modele}>
        {r.texte}{FINE}: <a href={r.source.url}>{r.source.titre}</a>, {date(r.source)}. {r.definition}
      </li>
    {/each}
  </ul>
  <p class="source-mesures">
    Mesures du 3 novembre 2026{FINE}: <a href={mesures.url}>le rapport de mesure</a>, et
    <a href={mesuresMini.url}>la configuration de la version courte</a> pour «{FINE}mini{FINE}».
  </p>

  <div class="liste-sources" data-test="calc-sources">
    <h3 class="titre-section">Les sources</h3>
    <ul>
      <li data-source="materiel">
        La carte, {rel.materiel.nom}{FINE}: {#each [rel.materiel.source, ...(rel.materiel.autresSources ?? [])] as s, i (i)}{#if i > 0}{`${FINE}; `}{/if}<a
            href={s.url}>{s.titre}</a
          >, {date(s)}{/each}.
        {#if rel.materiel.note}<span class="precision">{rel.materiel.note}</span>{/if}
      </li>
      {#if rel.modele.sources.length > 0}
        <li data-source="modele">
          Le modèle, {rel.modele.nom}{FINE}: {#each rel.modele.sources as s, i (i)}{#if i > 0}{`${FINE}; `}{/if}<a href={s.url}
              >{s.titre}</a
            >, {date(s)}{/each}.
          {#if rel.modele.note}<span class="precision">{rel.modele.note}</span>{/if}
        </li>
      {/if}
      {#if rel.location !== null}
        {#each rel.location.prix as p, i (i)}
          <li data-prix={i}>
            <a href={p.source.url}>{p.fournisseur}, {p.offre}</a>{FINE}: {lie(formaterPrix(p.usdParHeure))} par carte et par
            heure, hors taxes, {date(p.source)}.
          </li>
        {/each}
        <li data-source="change">
          Le taux de change{FINE}: 1{INSECABLE}€ = {nombre(TAUX_DE_CHANGE.usdPourUnEur, decimalesUtiles(TAUX_DE_CHANGE.usdPourUnEur))}{INSECABLE}$,
          <a href={TAUX_DE_CHANGE.source.url}>{TAUX_DE_CHANGE.source.titre}</a>, {date(TAUX_DE_CHANGE.source)}.
        </li>
      {/if}
      {#if electricite !== null}
        <li data-source="electricite">
          L’électricité{FINE}: {nombre(ELECTRICITE.eurParKwh, decimalesUtiles(ELECTRICITE.eurParKwh))}{INSECABLE}€ le kWh,
          <a href={ELECTRICITE.source.url}>{ELECTRICITE.source.titre}</a>, {date(ELECTRICITE.source)}.
        </li>
      {/if}
    </ul>
    <p class="avertissement">
      Les prix de location bougent de 20 à 50{FINE}% en quelques mois{FINE}: ceux-ci sont ceux du jour de leur relevé, hors taxes.
    </p>
  </div>

  <p class="vh" role="status" data-test="calc-etat">{etat}</p>
</div>

<style>
  .calculateur {
    margin: 1em 0 1.6em;
  }

  /* La phrase à régler : des lignes assez hautes pour les nombres jaunes et les sélecteurs. */
  .phrase {
    line-height: 2;
    margin: 0 0 0.9em;
  }

  /* Le nombre de cartes et son « × » ne se séparent pas. */
  .insecable {
    white-space: nowrap;
  }

  .insecable :global(.nombre) {
    margin-right: 2px;
  }

  /* Les sélecteurs : comme le champ de l'atelier, fond soleil pâle et souligné
     soleil (le jaune est réservé à ce qui se manipule). */
  .selecteur {
    max-width: 100%;
    font: inherit;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 0.95em;
    line-height: 1.3;
    color: var(--indigo);
    background-color: var(--soleil-pale);
    border: 0;
    border-bottom: 3px solid var(--soleil);
    border-radius: 6px 6px 0 0;
    padding: 1px 4px 2px 6px;
    min-height: 30px;
    vertical-align: baseline;
    cursor: pointer;
  }

  .selecteur:hover:not(:disabled) {
    background-color: var(--soleil-survol);
  }

  .selecteur:focus-visible {
    background-color: var(--soleil-survol);
    border-bottom-color: var(--indigo);
  }

  .selecteur:disabled {
    cursor: default;
    opacity: 1;
    color: var(--indigo);
  }

  .calcule {
    font-family: var(--titres);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  /* Sans JavaScript, les sélecteurs ne feraient rien : leur valeur s'écrit à leur place. */
  .fixe,
  .sans-js {
    display: none;
  }

  @media (scripting: none) {
    .selecteur {
      display: none;
    }

    .fixe {
      display: inline;
      font-family: var(--titres);
      font-weight: 700;
    }

    .sans-js {
      display: block;
      font-style: italic;
    }
  }

  /* ---------- Le relevé : un tableau typographié à deux colonnes ---------- */

  table {
    border-collapse: collapse;
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
  }

  caption {
    caption-side: top;
    text-align: left;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 15px;
    line-height: 1.35;
    color: var(--indigo-doux);
    padding: 0 0 6px;
    margin: 0;
  }

  .releve {
    width: 100%;
    margin: 0 0 1em;
    border-top: 2px solid var(--indigo);
  }

  .releve tr {
    border-bottom: 1px solid var(--brume);
  }

  .releve th {
    width: 36%;
    text-align: left;
    vertical-align: top;
    font-weight: 600;
    font-size: 15px;
    line-height: 1.4;
    color: var(--indigo-doux);
    padding: 11px 16px 10px 0;
  }

  .releve td {
    vertical-align: top;
    font-size: 17px;
    line-height: 1.45;
    font-weight: 500;
    padding: 9px 0 9px;
    overflow-wrap: break-word;
  }

  .repere {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.45;
    margin: 0 0 1em;
    font-variant-numeric: tabular-nums;
  }

  /* ---------- « Voir le calcul » ---------- */

  .voir {
    margin: 0 0 0.6em;
  }

  /* La bascule : un bouton souligné de jaune (règles reprises de AtelierTokenizer.svelte). */
  .bascule {
    font: inherit;
    font-family: var(--titres);
    font-weight: 600;
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
    min-height: 28px;
    cursor: pointer;
  }

  .bascule:hover:not(:disabled) {
    background: var(--soleil-pale);
    text-decoration-color: var(--soleil-vif);
  }

  .bascule:disabled {
    cursor: default;
  }

  .formules {
    display: none;
    margin: 0 0 1.4em;
    border-top: 1px solid var(--brume);
  }

  .formules.ouvert {
    display: block;
  }

  .formule {
    padding: 12px 0 2px;
    border-bottom: 1px solid var(--brume);
  }

  .titre-formule {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 15px;
    line-height: 1.35;
    color: var(--indigo-doux);
    margin: 0 0 4px;
  }

  .calcul {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.5;
    font-variant-numeric: tabular-nums;
    margin: 0 0 6px;
    overflow-wrap: break-word;
  }

  .sens {
    font-size: 17px;
    line-height: 1.5;
    margin: 0 0 10px;
  }

  .sources-formule {
    font-family: var(--titres);
    font-size: 14px;
    color: var(--indigo-doux);
    overflow-wrap: anywhere;
  }

  /* Sans JavaScript, la bascule ne ferait rien : les formules sont dépliées d'office. */
  @media (scripting: none) {
    .voir {
      display: none;
    }

    .formules {
      display: block;
    }
  }

  /* ---------- Le repère mesuré ---------- */

  /* « Repère mesuré » et « Les sources » : de vrais titres, sous celui de l'étape. */
  .titre-section {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 20px;
    line-height: 1.25;
    margin: 1.4em 0 0.35em;
  }

  .intro-reperes {
    font-size: 17px;
    line-height: 1.5;
    margin: 0 0 8px;
  }

  .indice-defile {
    display: none;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.35;
    color: var(--indigo-doux);
    margin: 0 0 8px;
  }

  .defile {
    overflow-x: auto;
    max-width: 100%;
    margin: 0 0 0.8em;
  }

  .reperes {
    min-width: 100%;
    font-size: 15px;
    border-top: 2px solid var(--indigo);
  }

  .reperes thead th {
    font-weight: 600;
    font-size: 14px;
    color: var(--indigo-doux);
    text-align: right;
    white-space: nowrap;
    padding: 6px 0 4px 16px;
  }

  .reperes thead th[scope='colgroup'] {
    text-align: left;
    color: var(--indigo);
    padding-bottom: 0;
  }

  .reperes tbody tr {
    border-top: 1px solid var(--brume);
  }

  .reperes th[scope='row'] {
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
    padding: 6px 4px 6px 0;
  }

  .parametres {
    display: block;
    font-weight: 400;
    font-size: 13px;
    color: var(--indigo-doux);
  }

  .reperes td {
    text-align: right;
    white-space: nowrap;
    padding: 6px 0 6px 16px;
    vertical-align: top;
  }

  /* Un filet sépare la carte du processeur. */
  .reperes .groupe-processeur {
    border-left: 1px solid var(--brume);
  }

  /* La taille de ton IA choisie dans la phrase : en gras sur fond de brume (le jaune reste aux réglages). */
  .reperes tr.choisie {
    background: var(--brume-claire);
    font-weight: 700;
  }

  .comme-les-grands {
    font-size: 17px;
    line-height: 1.5;
    margin: 0 0 6px;
  }

  .sources-reperes {
    list-style: none;
    margin: 0 0 8px;
    padding: 0;
  }

  .sources-reperes li {
    padding: 3px 0;
  }

  .sources-reperes a,
  .source-mesures a {
    color: var(--indigo);
  }

  .source-mesures,
  .sources-reperes,
  .avertissement {
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
    margin: 0;
  }

  /* ---------- Les sources ---------- */

  .liste-sources {
    margin: 0.4em 0 0;
  }

  .liste-sources ul {
    list-style: none;
    margin: 0 0 8px;
    padding: 0;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.5;
    color: var(--indigo-doux);
    overflow-wrap: anywhere;
  }

  .liste-sources li {
    padding: 5px 0;
    border-top: 1px solid var(--brume);
  }

  .liste-sources li a {
    color: var(--indigo);
  }

  .precision {
    display: block;
    margin-top: 2px;
  }

  @media (max-width: 720px) {
    .releve th {
      width: 40%;
      font-size: 14px;
      padding-right: 12px;
    }

    .releve td,
    .repere,
    .calcul {
      font-size: 16px;
    }

    .intro-reperes,
    .sens,
    .comme-les-grands {
      font-size: 16px;
    }
  }

  /* En dessous de 600 px, le tableau des repères est plus large que la colonne :
     la phrase qui invite à le faire défiler s'affiche. */
  @media (max-width: 600px) {
    .indice-defile {
      display: block;
    }
  }
</style>
