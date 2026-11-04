<script lang="ts">
  // La page d'essai de parité : refait dans le navigateur les quatre fichiers
  // d'attendus du Python (projets/mini-modele/tests/attendus-<nom>.json), avec
  // les fonctions de parite.ts, et les écrit en JSON, chacun dans son <pre>.
  // Le parcours e2e/parite.spec.ts les compare aux fichiers du Python, au bit
  // près, dans Chrome, Firefox et WebKit.
  //
  // Tout se calcule dans onMount, donc seulement dans le navigateur : le HTML
  // qu'Astro construit dans Node a des <pre> vides, et pas de data-pret.
  // Sinon, le parcours comparerait ce que Node a calculé à la construction, et
  // ne verrait jamais un moteur qui s'écarte. La racine porte aussi le moteur
  // qui a calculé (data-moteur, navigator.userAgent).
  //
  // Quand les quatre sont écrits, la racine (data-test="parite") porte
  // data-pret="oui" ; si un calcul échoue, data-pret="erreur" et la ligne
  // d'état dit pourquoi.
  //
  // À poser dans le MDX avec client:load :
  //   <ControleParite client:load />
  import { onMount } from 'svelte';
  import { nombre } from '../../lib/nombres';
  import { CALCULS_ATTENDUS, versJson, type NomAttendus } from '../../lib/mini-modele/parite';

  const FINE = '\u202F';
  const NOMS = Object.keys(CALCULS_ATTENDUS) as NomAttendus[];

  let phase = $state<'attente' | 'calcul' | 'pret' | 'erreur'>('attente');
  let resultats = $state<Partial<Record<NomAttendus, string>>>({});
  let moteur = $state<string | undefined>(undefined);
  let duree = $state(0);
  let erreur = $state('');

  const pret = $derived(phase === 'pret' ? 'oui' : phase === 'erreur' ? 'erreur' : undefined);
  const ligneEtat = $derived.by(() => {
    switch (phase) {
      case 'attente':
        return `Ton navigateur refait ici les calculs du Python${FINE}; sans JavaScript, rien n’est calculé.`;
      case 'calcul':
        return 'Calcul en cours dans ton navigateur…';
      case 'pret':
        return `Calculé dans ton navigateur en ${nombre(duree)} ms${FINE}: les quatre fichiers d’attendus sont refaits.`;
      case 'erreur':
        return `Le calcul a échoué${FINE}: ${erreur}`;
    }
  });

  /** Rend la main au navigateur : la page s'affiche et la ligne d'état se met à jour entre deux calculs. */
  function pause(): Promise<void> {
    return new Promise((fin) => setTimeout(fin, 0));
  }

  onMount(() => {
    let arrete = false;
    moteur = navigator.userAgent;
    phase = 'calcul';
    (async () => {
      const debut = performance.now();
      try {
        for (const nom of NOMS) {
          await pause();
          if (arrete) return;
          resultats[nom] = versJson(CALCULS_ATTENDUS[nom]());
        }
        duree = performance.now() - debut;
        phase = 'pret';
      } catch (e) {
        erreur = e instanceof Error ? e.message : String(e);
        phase = 'erreur';
      }
    })();
    return () => {
      arrete = true;
    };
  });
</script>

<section class="parite" data-test="parite" data-pret={pret} data-moteur={moteur}>
  <p class="etat" role="status" data-test="parite-etat">{ligneEtat}</p>
  {#each NOMS as nom (nom)}
    <details>
      <summary>attendus-{nom}.json, refait ici</summary>
      <pre data-test="parite-{nom}">{resultats[nom] ?? ''}</pre>
    </details>
  {/each}
</section>

<style>
  .parite {
    margin: 1em 0 1.6em;
  }

  .etat {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 17px;
    line-height: 1.4;
    margin: 0 0 12px;
    font-variant-numeric: tabular-nums;
  }

  details {
    border-top: 1px solid var(--brume);
    padding: 6px 0;
  }

  summary {
    font-family: var(--mono);
    font-size: 15px;
    min-height: 24px;
    cursor: pointer;
  }

  /* Le JSON revient à la ligne où il faut : jamais de défilement en largeur, même à 390 px. */
  pre {
    font-family: var(--mono);
    font-size: 13px;
    line-height: 1.4;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 8px 0 0;
  }
</style>
