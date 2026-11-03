<script lang="ts" module>
  // Les acquis déjà annoncés pendant ce chargement de page : chacun ne l'est
  // qu'une fois, même si le lecteur recommence et termine plusieurs fois.
  const acquisAnnonces = new Set<string>();
</script>

<script lang="ts">
  // La démo du mini-modèle qui apprend : un petit transformer apprend à
  // inventer des prénoms, dans le navigateur du lecteur.
  //
  // Rien de lourd dans la page : ce composant n'importe des valeurs que de
  // reglages.ts, nombres.ts, courbe.ts (par CourbePerte) et pilote.ts, et
  // seulement des types d'apercu.ts et de boucle-travailleur.ts. Le moteur et
  // la liste des prénoms n'entrent que dans le Worker, créé au premier
  // « Lancer » (import de travailleur.ts?worker). Le test
  // src/components/demos/imports.test.ts relit ces imports, et le parcours
  // e2e/mini-modele.spec.ts vérifie le paquet réel.
  //
  // L'état vit dans le réducteur pur de pilote.ts : chaque clic, chaque
  // message du Worker et l'onglet caché passent par appliquer(), qui garde le
  // nouvel état et envoie au Worker ce que le réducteur demande.
  //
  // À poser par DemoMiniModele.astro, qui calcule l'état du pas 0 (initial)
  // au moment de la construction : sans JavaScript, la page montre déjà ces
  // valeurs et ces prénoms.
  import { onMount, untrack } from 'svelte';
  import { canal } from '../../lib/canal';
  import { decimalesUtiles, formaterPerte, nombre } from '../../lib/nombres';
  import { typographier } from '../../lib/typo';
  import { PRESETS_MINI, TAUX_PROPOSES, type NomPreset } from '../../lib/mini-modele/reglages';
  import {
    actionPrincipale,
    etatDeDepart,
    prenomAffiche,
    reduire,
    tauxIndexParDefaut,
    type EtatDemo,
    type Evenement,
  } from '../../lib/mini-modele/pilote';
  import type { EtatInitialMini } from '../../lib/mini-modele/apercu';
  import type { MessageDuTravailleur, MessageVersTravailleur } from '../../lib/mini-modele/boucle-travailleur';
  import type { DetailAcquis } from '../../scripts/chapitre';
  import NombreManipulable from '../interactif/NombreManipulable.svelte';
  import CourbePerte from './CourbePerte.svelte';

  interface Props {
    /** « complet » (le réglage du taux, 3 000 pas) ou « avant-gout » (600 pas, toujours vite). */
    preset: NomPreset;
    /** Le nom de l'instance : data-mini, et le canal du taux (« <nom>:taux »). */
    nom: string;
    /** Le verrou qui désactive le réglage du taux tant que son pari n'est pas fait. */
    verrou?: string;
    /** La clé de l'acquis gagné à la fin du premier entraînement complet. */
    acquis?: string;
    /** L'état au pas 0, calculé par Astro (apercu.ts). */
    initial: EtatInitialMini;
    /** Le lien du chapitre 1.5 s'il est paru, sinon null. */
    lien15: string | null;
  }

  const { preset, nom, verrou, acquis, initial, lien15 }: Props = $props();

  const FINE = ' ';
  const avantGout = untrack(() => preset) === 'avant-gout';
  const tauxDepart = untrack(() => tauxIndexParDefaut(preset));
  const nbValidation = untrack(() => PRESETS_MINI[preset].nbValidation);

  let etat: EtatDemo = $state.raw(untrack(() => etatDeDepart(initial, tauxDepart)));
  // Ce que dit la ligne d'état en cours d'entraînement : le dernier point de
  // validation, avec la vitesse mesurée à ce moment-là. Elle ne change qu'à
  // chaque validation (pas à chaque image) : les lecteurs d'écran ne
  // l'entendent qu'à ces moments-là, ou à une pause, ou à la fin.
  let vitesseALaValidation = $state(0);

  // Le canal du taux est choisi une fois pour toutes, comme dans NombreManipulable.
  const tauxCanal = canal<number>(untrack(() => `${nom}:taux`), tauxDepart);

  /** Un nombre entier, ou « ? » s'il n'est pas fini : l'affichage ne lève jamais d'erreur. */
  const entier = (x: number) => (Number.isFinite(x) ? nombre(Math.round(x)) : '?');

  /** Le taux d'indice i, écrit tel qu'il est réglé : « 0,01 », « 0,3 ». */
  function texteTaux(i: number): string {
    const taux = TAUX_PROPOSES[i];
    return Number.isFinite(taux) ? nombre(taux, decimalesUtiles(taux)) : '?';
  }

  // ---------- Le Worker ----------

  let travailleur: Worker | null = null;
  let creation = false;
  let detruit = false;
  // Les messages partis avant que le Worker soit prêt, envoyés dès qu'il l'est.
  let enAttente: MessageVersTravailleur[] = [];

  function erreurDuTravailleur(message: string): void {
    appliquer({ type: 'message', message: { type: 'erreur', generation: etat.generation, message } });
  }

  async function creerTravailleur(): Promise<void> {
    creation = true;
    try {
      const { default: Travailleur } = await import('../../lib/mini-modele/travailleur.ts?worker');
      if (detruit) return;
      const w = new Travailleur({ name: `mini-modele ${nom}` });
      w.onmessage = (evenement: MessageEvent<MessageDuTravailleur>) => appliquer({ type: 'message', message: evenement.data });
      w.onerror = (evenement) => {
        evenement.preventDefault();
        erreurDuTravailleur(evenement.message ?? '');
      };
      w.onmessageerror = () => erreurDuTravailleur('');
      travailleur = w;
      for (const m of enAttente) w.postMessage(m);
      enAttente = [];
    } catch (erreur) {
      // Le Worker n'a pas pu se charger (réseau coupé…) : un prochain essai le retentera.
      creation = false;
      enAttente = [];
      erreurDuTravailleur(erreur instanceof Error ? erreur.message : String(erreur));
    }
  }

  function envoyer(m: MessageVersTravailleur): void {
    if (travailleur !== null) {
      travailleur.postMessage(m);
      return;
    }
    // Sans Worker, rien ne tourne : une pause ou une vitesse n'a rien à changer.
    if (!creation && m.type !== 'lancer') return;
    enAttente.push(m);
    if (!creation) void creerTravailleur();
  }

  // ---------- Le réducteur ----------

  function appliquer(ev: Evenement): void {
    const avant = etat;
    const { etat: apres, envoi } = reduire(avant, ev, preset);
    etat = apres;
    if (apres.validations !== avant.validations) {
      vitesseALaValidation = apres.validations.length > 1 ? apres.pasParSeconde : 0;
    }
    if (envoi !== null) envoyer(envoi);
    if (apres.phase === 'termine' && avant.phase !== 'termine' && acquis !== undefined && !acquisAnnonces.has(acquis)) {
      acquisAnnonces.add(acquis);
      const detail: DetailAcquis = { cle: acquis };
      window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
    }
  }

  onMount(() => {
    // Le taux réglé par le nombre jaune : un changement repart de zéro.
    const desabonner = tauxCanal.subscribe((tauxIndex) => {
      if (tauxIndex !== etat.tauxIndex) appliquer({ type: 'changer-taux', tauxIndex });
    });
    // Onglet caché pendant l'entraînement : pause, et la ligne d'état le dit.
    const surVisibilite = () => {
      if (document.hidden) appliquer({ type: 'pause', raison: 'onglet' });
    };
    document.addEventListener('visibilitychange', surVisibilite);
    return () => {
      detruit = true;
      desabonner();
      document.removeEventListener('visibilitychange', surVisibilite);
      travailleur?.terminate();
      travailleur = null;
    };
  });

  // ---------- Ce qui s'affiche ----------

  const action = $derived(actionPrincipale(etat));
  const derniere = $derived(etat.validations[etat.validations.length - 1]);
  const ligneEtat = $derived.by(() => {
    if (etat.message !== null) return typographier(etat.message);
    if (etat.phase === 'en-pause') return `En pause au pas ${entier(etat.pas)} sur ${entier(etat.pasTotal)}.`;
    const vitesse = vitesseALaValidation > 0 ? `, ${entier(vitesseALaValidation)} pas par seconde` : '';
    return `Pas ${entier(derniere.pas)} sur ${entier(etat.pasTotal)}${FINE}: erreur ${formaterPerte(derniere.perte)}${vitesse}.`;
  });
  const echantillons = $derived(etat.echantillons[etat.echantillons.length - 1]);
  const echantillonsAvant = $derived(etat.echantillons.slice(0, -1));
  const legendeFantome = $derived(
    etat.fantome === null ? undefined : `l’essai d’avant, au taux de ${texteTaux(etat.fantome.tauxIndex)}`,
  );
  const peutRecommencer = $derived(etat.pas > 0 || etat.phase !== 'pret' || etat.message !== null);

  function cliquerAction(): void {
    if (action.evenement !== null) appliquer(action.evenement);
  }
</script>

<div class="mini-modele" data-mini={nom} data-phase={etat.phase} data-travailleur={etat.travailleur}>
  {#if avantGout}
    <p class="reglage">Il va s’entraîner pendant {entier(etat.pasTotal)} pas.</p>
  {:else}
    <p class="reglage">
      Entraîne-le sur {entier(initial.nbEntrainement)} prénoms pendant {entier(etat.pasTotal)} pas, avec un taux
      d’apprentissage <span class="insecable"
        >de <NombreManipulable
          canal="{nom}:taux"
          min={0}
          max={TAUX_PROPOSES.length - 1}
          initiale={tauxDepart}
          etiquette="Taux d’apprentissage"
          texte={texteTaux}
          {verrou}
          testId="taux"
        />.</span
      >
    </p>
  {/if}

  <div class="commandes">
    <button type="button" class="bouton" data-test="mini-action" disabled={action.evenement === null} onclick={cliquerAction}
      >{action.texte}</button
    >
    <button
      type="button"
      class="bouton"
      data-test="mini-recommencer"
      disabled={!peutRecommencer}
      onclick={() => appliquer({ type: 'recommencer' })}>Recommencer</button
    >
    {#if !avantGout}
      <button
        type="button"
        class="bascule"
        data-test="mini-vitesse"
        onclick={() => appliquer({ type: 'vitesse', vitesse: etat.vitesse === 'rapide' ? 'normale' : 'rapide' })}
        >{etat.vitesse === 'rapide' ? 'Revenir au rythme normal' : 'Aller plus vite'}</button
      >
    {/if}
  </div>
  <p class="sans-js">Cette démo calcule dans ton navigateur{FINE}: elle a besoin de JavaScript.</p>

  <p class="etat" role="status" data-test="mini-etat" data-pas={etat.pas}>{ligneEtat}</p>

  <CourbePerte
    pertes={etat.pertes}
    validations={etat.validations}
    pasTotal={etat.pasTotal}
    perteHasard={initial.perteHasard}
    fantome={etat.fantome}
    etiquette="Courbe de l’erreur"
    {legendeFantome}
  />

  <p class="intro-liste">
    L’erreur sur {entier(nbValidation)} prénoms qu’il ne voit jamais pendant l’entraînement{FINE}:
  </p>
  <ol class="validations" data-test="mini-validations">
    {#each etat.validations as v (v.pas)}
      <li>au pas {entier(v.pas)}{FINE}: <span class="valeur">{formaterPerte(v.perte)}</span></li>
    {/each}
  </ol>

  <p class="intro-liste">Les prénoms qu’il invente au pas {entier(echantillons.pas)}{FINE}:</p>
  <ul class="prenoms" data-test="mini-echantillons">
    {#each echantillons.prenoms as p, i (i)}
      <li class:vide={p.texte === ''}>
        {prenomAffiche(p.texte)}{#if p.existe}{' '}<span class="existe">(existe déjà)</span>{/if}
      </li>
    {/each}
  </ul>
  {#if echantillonsAvant.length > 0}
    <details class="avant">
      <summary>Les prénoms des étapes d’avant</summary>
      {#each echantillonsAvant as groupe (groupe.pas)}
        <p>
          <span class="pas-groupe">au pas {entier(groupe.pas)}{FINE}:</span>
          {#each groupe.prenoms as p, i (i)}{prenomAffiche(p.texte)}{#if p.existe}{' '}<span class="existe"
                >(existe déjà)</span
              >{/if}{i < groupe.prenoms.length - 1 ? ', ' : '.'}{/each}
        </p>
      {/each}
    </details>
  {/if}

  <p class="credit">
    Source{FINE}: Insee, <a href="https://www.insee.fr/fr/statistiques/8595130">Fichier des prénoms 1900–2025</a>,
    édition du 16/07/2026,
    <a href="https://www.insee.fr/fr/information/2008466">Licence Ouverte 2.0</a>.
  </p>

  {#if avantGout}
    <p class="suite">
      Tu le fabriqueras au {#if lien15 !== null}<a href={lien15}>chapitre 1.5</a>{:else}chapitre 1.5{/if}.
    </p>
  {/if}
</div>

<style>
  .mini-modele {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin-bottom: 0.8em;
  }

  /* Le nombre jaune ne part pas seul à la ligne : « de 0,01. » reste ensemble. */
  .insecable {
    white-space: nowrap;
  }

  /* Les boutons reprennent les choix des paris : bord indigo, ombre décalée,
     soleil au survol (le jaune est réservé à ce qui se manipule). */
  .commandes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 14px;
    margin: 0 0 14px;
  }

  .bouton {
    cursor: pointer;
    font-family: var(--titres);
    font-weight: 700;
    font-size: 18px;
    line-height: 1.15;
    background: var(--papier);
    color: var(--indigo);
    border: 2px solid var(--indigo);
    border-radius: 12px;
    padding: 10px 16px;
    margin-bottom: 4px; /* la place de l'ombre */
    box-shadow: 0 4px 0 var(--indigo);
    transition:
      transform 0.08s ease,
      box-shadow 0.08s ease,
      background-color 0.15s ease;
  }

  .bouton:hover:not(:disabled) {
    background: var(--soleil);
  }

  .bouton:active:not(:disabled) {
    transform: translateY(3px);
    box-shadow: 0 1px 0 var(--indigo);
  }

  .bouton:disabled {
    cursor: default;
    color: var(--indigo-doux);
    border-color: color-mix(in srgb, var(--lavande) 50%, var(--papier));
    box-shadow: 0 4px 0 color-mix(in srgb, var(--lavande) 50%, var(--papier));
  }

  /* La bascule de vitesse : un bouton souligné de jaune, comme dans la maquette 10
     (règles reprises de AtelierTokenizer.svelte). */
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

  /* Sans JavaScript, les boutons ne feraient rien : ils laissent la place à une phrase. */
  .sans-js {
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
  }

  .etat {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.4;
    margin: 0 0 4px;
    min-height: 1.4em;
    font-variant-numeric: tabular-nums;
  }

  .intro-liste {
    margin: 0 0 0.3em;
  }

  /* Les erreurs de validation : une liste typographiée, en colonnes. */
  .validations {
    list-style: none;
    margin: 0 0 1.2em;
    padding: 0;
    columns: 4 8.5em;
    column-gap: 1.5em;
    font-family: var(--titres);
    font-size: 15px;
    line-height: 1.55;
    color: var(--indigo-doux);
    font-variant-numeric: tabular-nums;
  }

  .validations li {
    break-inside: avoid;
  }

  .validations .valeur {
    font-weight: 600;
    color: var(--indigo);
  }

  /* Les prénoms inventés, deux par ligne sur ordinateur. */
  .prenoms {
    list-style: none;
    margin: 0 0 0.6em;
    padding: 0;
    columns: 2 12em;
    column-gap: 1.5em;
    font-size: 22px;
    line-height: 1.45;
    font-variation-settings: 'opsz' 36;
  }

  .prenoms li {
    break-inside: avoid;
    overflow-wrap: anywhere;
  }

  .prenoms li.vide {
    font-style: italic;
    color: var(--indigo-doux);
    font-size: 19px;
  }

  .existe {
    font-family: var(--titres);
    font-size: 14px;
    color: var(--indigo-doux);
  }

  .avant {
    margin: 0 0 1em;
    font-size: 17px;
    line-height: 1.5;
  }

  .avant summary {
    cursor: pointer;
    font-family: var(--titres);
    font-weight: 600;
    font-size: 16px;
    width: fit-content;
    padding: 2px 0;
  }

  .avant p {
    margin: 0.4em 0 0;
    overflow-wrap: anywhere;
  }

  .pas-groupe {
    font-family: var(--titres);
    font-size: 15px;
    font-weight: 600;
    color: var(--indigo-doux);
    font-variant-numeric: tabular-nums;
  }

  .credit {
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
    margin: 0;
  }

  .suite {
    margin: 1em 0 0;
  }

  @media (prefers-reduced-motion: reduce) {
    .bouton {
      transition: none;
    }
  }

  @media (max-width: 720px) {
    .bouton {
      font-size: 17px;
      padding: 9px 14px;
    }

    .validations {
      font-size: 14px;
    }

    .prenoms {
      font-size: 20px;
    }
  }
</style>
