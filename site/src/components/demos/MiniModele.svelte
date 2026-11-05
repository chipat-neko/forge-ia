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
    annonceApres,
    etatDeDepart,
    prenomAffiche,
    reduire,
    tableauAvantApres,
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

  const FINE = '\u202F';
  const avantGout = untrack(() => preset) === 'avant-gout';
  const tauxDepart = untrack(() => tauxIndexParDefaut(preset));
  // Le taux n'a que 6 crans : sur un téléphone, un cran tous les 24 px au doigt (6 px par défaut).
  const PIXELS_PAR_TAUX = 24;
  const nbValidation = untrack(() => PRESETS_MINI[preset].nbValidation);

  let etat: EtatDemo = $state.raw(untrack(() => etatDeDepart(initial, tauxDepart)));
  // Ce que dit la ligne d'état en cours d'entraînement : le dernier point de
  // validation, avec la vitesse mesurée à ce moment-là. Elle ne change qu'à
  // chaque validation (pas à chaque image), mais c'est encore tous les 100 pas :
  // elle n'est pas lue d'office (voir `annonce`).
  let vitesseALaValidation = $state(0);
  // Au lancement ou à la reprise, la ligne d'état le dit tout de suite (les
  // lecteurs d'écran entendent quelque chose avant la première validation),
  // jusqu'au point de validation suivant. `validations` : leur nombre d'alors.
  let lancement: { texte: string; validations: number } | null = $state(null);
  // Ce qu'entendent les lecteurs d'écran (une zone role="status" cachée à l'œil) :
  // la ligne d'état, reprise seulement au lancement, à la pause, à la reprise,
  // tous les 1 000 pas, à la fin et à une explosion ou une erreur (annonceApres,
  // dans pilote.ts). Vide au départ : rien n'est dit au chargement.
  let annonce = $state('');

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
      // Astro type `?worker` sans argument ; Vite, qui construit le Worker, accepte `{ name }` (son propre type le dit).
      const { default: Travailleur } = (await import('../../lib/mini-modele/travailleur.ts?worker')) as {
        default: new (options?: { name?: string }) => Worker;
      };
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
    if (apres.phase === 'en-cours' && avant.phase !== 'en-cours') {
      lancement = {
        texte: avant.phase === 'en-pause' ? `Entraînement repris au pas ${entier(apres.pas)}.` : 'Entraînement lancé.',
        validations: apres.validations.length,
      };
    }
    // La ligne d'état du nouvel état (ligneEtat se recalcule à la lecture).
    annonce = annonceApres(avant, apres, ligneEtat, annonce);
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
    if (etat.phase === 'en-cours' && lancement !== null && etat.validations.length === lancement.validations) {
      return lancement.texte;
    }
    const vitesse = vitesseALaValidation > 0 ? `, ${entier(vitesseALaValidation)} pas par seconde` : '';
    return `Pas ${entier(derniere.pas)} sur ${entier(etat.pasTotal)}${FINE}: erreur ${formaterPerte(derniere.perte)}${vitesse}.`;
  });
  const echantillons = $derived(etat.echantillons[etat.echantillons.length - 1]);
  // L'avant-goût montre le départ et la fin côte à côte (tableauAvantApres) : ses étapes d'avant
  // ne gardent que les pas d'entre les deux. L'entraînement complet garde sa liste du dernier pas,
  // et toutes les étapes d'avant, pas 0 compris.
  const tableau = $derived(avantGout ? tableauAvantApres(etat) : null);
  const echantillonsAvant = $derived(avantGout ? etat.echantillons.slice(1, -1) : etat.echantillons.slice(0, -1));
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
          pixelsParUnite={PIXELS_PAR_TAUX}
        />.</span
      >
    </p>
  {/if}

  <div class="commandes">
    <!-- À la fin (« Terminé », « Entraînement arrêté »), le bouton principal ne fait plus rien, et « Recommencer »
         non plus juste après un clic (rien à recommencer au pas 0). Ils restent focalisables (aria-disabled plutôt
         que disabled) : le focus du clavier ne tombe pas sur la page. -->
    <button
      type="button"
      class="bouton-relief"
      data-test="mini-action"
      aria-disabled={action.evenement === null}
      onclick={cliquerAction}>{action.texte}</button
    >
    <button
      type="button"
      class="bouton-relief"
      data-test="mini-recommencer"
      aria-disabled={!peutRecommencer}
      onclick={() => {
        if (peutRecommencer) appliquer({ type: 'recommencer' });
      }}>Recommencer</button
    >
    {#if !avantGout}
      <button
        type="button"
        class="bascule-soleil"
        data-test="mini-vitesse"
        onclick={() => appliquer({ type: 'vitesse', vitesse: etat.vitesse === 'rapide' ? 'normale' : 'rapide' })}
        >{etat.vitesse === 'rapide' ? 'Revenir au rythme normal' : 'Aller plus vite'}</button
      >
    {/if}
  </div>
  <p class="sans-js">Cette démo calcule dans ton navigateur{FINE}: elle a besoin de JavaScript.</p>

  <!-- La ligne d'état change à chaque validation : elle n'est pas une zone lue d'office. Les lecteurs d'écran
       entendent la zone cachée qui la suit, aux seuls moments qui comptent. -->
  <p class="etat" data-test="mini-etat" data-pas={etat.pas}>{ligneEtat}</p>
  <p class="vh" role="status" data-test="mini-annonce">{annonce}</p>

  <CourbePerte
    pertes={etat.pertes}
    validations={etat.validations}
    pasTotal={etat.pasTotal}
    perteHasard={initial.perteHasard}
    fantome={etat.fantome}
    etiquette="Courbe de l’erreur"
    {legendeFantome}
    explose={etat.phase === 'diverge'}
  />

  <p class="intro-liste">
    L’erreur sur {entier(nbValidation)} prénoms qu’il ne voit jamais pendant l’entraînement{FINE}:
  </p>
  <ol class="validations" data-test="mini-validations">
    {#each etat.validations as v (v.pas)}
      <li>au pas {entier(v.pas)}{FINE}: <span class="valeur">{formaterPerte(v.perte)}</span></li>
    {/each}
  </ol>

  {#if tableau !== null}
    <!-- L'avant-goût : les prénoms du départ et ceux du dernier pas, ligne à ligne. Une case pas encore remplie
         montre un tiret, que les lecteurs d'écran lisent « pas encore ». Le tableau change à chaque validation :
         il n'est pas une zone lue d'office (la fin s'annonce par la zone cachée, avec la ligne d'état). -->
    <table class="avant-apres" data-test="mini-avant-apres">
      <caption class="intro-liste">Les prénoms inventés, avant et après l’entraînement</caption>
      <thead>
        <tr>
          <th scope="col">{tableau.enTetes[0]}</th>
          <th scope="col">{tableau.enTetes[1]}</th>
        </tr>
      </thead>
      <tbody>
        {#each tableau.lignes as ligne, i (i)}
          <tr>
            <td class:vide={ligne.depart.vide}>
              {ligne.depart.texte}{#if ligne.depart.existe}{' '}<span class="existe">(existe déjà)</span>{/if}
            </td>
            {#if ligne.fin === null}
              <td class="pas-encore"><span aria-hidden="true">—</span><span class="vh">pas encore</span></td>
            {:else}
              <td class:vide={ligne.fin.vide}>
                {ligne.fin.texte}{#if ligne.fin.existe}{' '}<span class="existe">(existe déjà)</span>{/if}
              </td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if etat.phase === 'pret'}
      <p class="invite" data-test="mini-avant-apres-invite">
        Lance l’entraînement{FINE}: ses prénoms viendront se ranger à droite.
      </p>
    {/if}
  {:else}
    <p class="intro-liste">Les prénoms qu’il invente au pas {entier(echantillons.pas)}{FINE}:</p>
    <ul class="prenoms" data-test="mini-echantillons">
      {#each echantillons.prenoms as p, i (i)}
        <li class:vide={p.texte === ''}>
          {prenomAffiche(p.texte)}{#if p.existe}{' '}<span class="existe">(existe déjà)</span>{/if}
        </li>
      {/each}
    </ul>
  {/if}
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

  /* Le nombre jaune ne part pas seul à la ligne : « de 0,01. » reste ensemble.
     Sa marge droite, réservée au chevron ›, est réduite ici pour que le point
     final ne flotte pas ; le chevron ne le recouvre qu'au survol ou au focus. */
  .insecable {
    white-space: nowrap;
  }

  .insecable :global(.nombre) {
    margin-right: 2px;
  }

  /* Les boutons reprennent les choix des paris : bord indigo, ombre décalée,
     soleil au survol (.bouton-relief, src/styles/commandes.css). Ici, leur
     police et leurs marges intérieures. */
  .commandes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 14px;
    margin: 0 0 14px;
  }

  .bouton-relief {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 18px;
    line-height: 1.15;
    padding: 10px 16px;
  }

  /* La bascule de vitesse : un bouton souligné de jaune (.bascule-soleil), dans la police du texte. */
  .bascule-soleil {
    font: inherit;
    padding: 0 2px;
  }

  /* Sans JavaScript, les boutons ne feraient rien : ils laissent la place à une phrase. */
  .sans-js {
    display: none;
  }

  @media (scripting: none) {
    .commandes,
    .invite {
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

  /* L'avant-goût : un tableau typographié, sans cadre, comme ceux des chapitres (TableauChronos) :
     un trait d'encre en haut et sous les en-têtes, des filets brume entre les lignes. Deux colonnes
     égales : un prénom trop long se coupe dans sa case, la page ne s'élargit pas. */
  .avant-apres {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    border-top: 2px solid var(--indigo);
    margin: 0 0 0.6em;
    font-size: 21px;
    line-height: 1.35;
    font-variation-settings: 'opsz' 36;
  }

  .avant-apres caption {
    text-align: left;
  }

  .avant-apres th {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 14px;
    color: var(--indigo-doux);
    text-align: left;
    vertical-align: bottom;
    padding: 6px 0 4px;
    border-bottom: 2px solid var(--indigo);
    font-variant-numeric: tabular-nums;
  }

  .avant-apres td {
    padding: 5px 0;
    border-bottom: 1px solid var(--brume);
    vertical-align: baseline;
    overflow-wrap: anywhere;
  }

  .avant-apres th + th,
  .avant-apres td + td {
    padding-left: 20px;
  }

  .avant-apres td.vide {
    font-style: italic;
    color: var(--indigo-doux);
    font-size: 18px;
  }

  /* Le tiret d'une case pas encore remplie ; son texte caché (.vh) se place dans la case. */
  .pas-encore {
    position: relative;
    color: var(--indigo-doux);
  }

  .invite {
    color: var(--indigo-doux);
    margin: 0 0 1em;
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

  @media (max-width: 720px) {
    .bouton-relief {
      font-size: 17px;
      padding: 9px 14px;
    }

    .validations {
      font-size: 14px;
    }

    .prenoms {
      font-size: 20px;
    }

    .avant-apres {
      font-size: 19px;
    }

    .avant-apres th + th,
    .avant-apres td + td {
      padding-left: 14px;
    }
  }
</style>
