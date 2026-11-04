<script lang="ts">
  // Une page d'essai de parité : refait dans le navigateur les fichiers
  // d'attendus d'un jeu, avec ses fonctions de parité, et les écrit en JSON,
  // chacun dans son <pre>. Le parcours e2e/parite.spec.ts les compare aux
  // fichiers du Python, au bit près, dans Chrome, Firefox et WebKit.
  //
  // Deux jeux (prop `jeu`, lue une fois) :
  //  - « mini-modele » (par défaut) : les quatre fichiers
  //    projets/mini-modele/tests/attendus-<nom>.json, avec mini-modele/parite.ts ;
  //  - « partie-0 » : les fichiers de FICHIERS_PARTIE_0 (partie-0/fichiers.ts),
  //    avec partie-0/parite.ts.
  //
  // Seul le module du jeu demandé est chargé, par import(), dans onMount :
  // une page ne charge ni les attendus ni le code de l'autre jeu. Tout se
  // calcule donc seulement dans le navigateur : le HTML qu'Astro construit
  // dans Node a des <pre> vides, et pas de data-pret. Sinon, le parcours
  // comparerait ce que Node a calculé à la construction, et ne verrait jamais
  // un moteur qui s'écarte. La racine porte aussi le moteur qui a calculé
  // (data-moteur, navigator.userAgent).
  //
  // Quand tous sont écrits, la racine (data-test="parite") porte
  // data-pret="oui" ; si un calcul échoue, data-pret="erreur" et la ligne
  // d'état dit pourquoi.
  //
  // À poser dans le MDX avec client:load :
  //   <ControleParite client:load />
  //   <ControleParite client:load jeu="partie-0" />
  import { onMount, untrack } from 'svelte';
  import { nombre } from '../../lib/nombres';
  import { versJson } from '../../lib/mini-modele/cles-json';
  import type { Attendus } from '../../lib/mini-modele/parite';
  import { FICHIERS_PARTIE_0 } from '../../lib/partie-0/fichiers';

  type NomDuJeu = 'mini-modele' | 'partie-0';

  interface Props {
    /** Le jeu d'attendus à refaire : celui du mini-modèle (par défaut) ou celui de la Partie 0. */
    jeu?: NomDuJeu;
  }

  const { jeu = 'mini-modele' }: Props = $props();

  const FINE = '\u202F';

  /**
   * Un jeu : les noms de ses calculs (connus dès la construction, pour écrire
   * un <pre> vide par calcul), le fichier que refait chacun, et le chargement
   * de ses calculs.
   */
  interface Jeu {
    noms: readonly string[];
    fichier: (nom: string) => string;
    charger: () => Promise<Readonly<Record<string, () => Attendus>>>;
  }

  const JEUX: Readonly<Record<NomDuJeu, Jeu>> = {
    'mini-modele': {
      // Les noms de CALCULS_ATTENDUS (mini-modele/parite.ts), vérifiés après le chargement.
      noms: ['calcul', 'donnees', 'modele', 'attention'],
      fichier: (nom) => `attendus-${nom}.json`,
      charger: async () => (await import('../../lib/mini-modele/parite')).CALCULS_ATTENDUS,
    },
    'partie-0': {
      noms: Object.keys(FICHIERS_PARTIE_0),
      fichier: (nom) => FICHIERS_PARTIE_0[nom],
      charger: async () => (await import('../../lib/partie-0/parite')).CALCULS_PARTIE_0,
    },
  };

  /** Le jeu demandé ; un nom inconnu arrête la construction de la page, avec quoi écrire à la place. */
  function choisirJeu(nom: string): Jeu {
    if (!Object.hasOwn(JEUX, nom)) {
      throw new Error(
        `ControleParite : jeu « ${nom} » inconnu. Dans le MDX, écris jeu="partie-0", ` +
          'ou rien du tout pour le mini-modèle (jeu="mini-modele").',
      );
    }
    return JEUX[nom as NomDuJeu];
  }

  // Le jeu est choisi une fois pour toutes (untrack le dit) : une page ne change pas de jeu.
  const { noms: NOMS, fichier, charger } = choisirJeu(untrack(() => jeu));

  // Les nombres de fichiers en toutes lettres, comme dans une phrase.
  const EN_LETTRES = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix'];

  /** « le fichier d’attendus est refait », ou « les quatre fichiers d’attendus sont refaits ». */
  function fichiersRefaits(n: number): string {
    if (n === 1) return 'le fichier d’attendus est refait';
    return `les ${EN_LETTRES[n] ?? nombre(n)} fichiers d’attendus sont refaits`;
  }

  let phase = $state<'attente' | 'calcul' | 'pret' | 'erreur'>('attente');
  let resultats = $state<Partial<Record<string, string>>>({});
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
        return `Calculé dans ton navigateur en ${nombre(duree)} ms${FINE}: ${fichiersRefaits(NOMS.length)}.`;
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
      try {
        const calculs = await charger();
        const fournis = Object.keys(calculs);
        if (fournis.join() !== NOMS.join()) {
          throw new Error(
            `les calculs chargés (${fournis.join(', ')}) ne sont pas ceux de la page (${NOMS.join(', ')}). ` +
              'Mets la liste de noms du jeu à jour dans ControleParite.svelte.',
          );
        }
        // La durée ne compte que les calculs, pas le chargement du module.
        const debut = performance.now();
        for (const nom of NOMS) {
          await pause();
          if (arrete) return;
          resultats[nom] = versJson(calculs[nom]());
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
      <summary>{fichier(nom)}, refait ici</summary>
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
