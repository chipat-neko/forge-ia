<script lang="ts" module>
  // Une seule annonce de l'acquis par chargement de page (le script du
  // chapitre ignore de toute façon un acquis déjà gagné).
  let acquisAnnonce = false;
</script>

<script lang="ts">
  // La phrase de la perte DPO du chapitre 1.8 : trois nombres jaunes, β (de 0,05 à 0,5), l'écart de la réponse
  // choisie à la référence et celui de la rejetée (de −3 à +3 nats, par pas de 0,5). La phrase dit la perte de la
  // paire, puis le sens de son gradient, d'après la dérivée : la choisie vers le haut et la rejetée vers le bas, avec
  // la même force, plus ou moins grande selon que la paire est à l'envers ou déjà dans le bon ordre.
  //
  // Le calcul est celui du jumeau (dpo.ts, comparé au Python à 10⁻¹² près), par phraseDeLaPerteDpo (atelier-1-8.ts).
  //
  // À placer dans le MDX avec client:load :
  //   <PhraseDpo client:load acquis="dpo" />
  // Au premier réglage, l'îlot émet `forge:acquis` avec la clé `acquis`. Sans JavaScript, la phrase se lit telle
  // qu'elle est à l'arrivée : β = 0,1, la choisie à +1 nat, la rejetée à −1.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { nombre } from '../../../lib/nombres';
  import {
    betaDeLIndice,
    ECART_CHOISIE_DEPART,
    ECART_MAX,
    ECART_MIN,
    ECART_REJETEE_DEPART,
    ecartEnTexte,
    INDICE_BETA_DEPART,
    INDICE_BETA_MAX,
    INDICE_BETA_MIN,
    PAS_D_ECART,
    phraseDeLaPerteDpo,
  } from '../../../lib/partie-1/atelier-1-8';
  import type { DetailAcquis } from '../../../scripts/chapitre';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Clé de l'acquis gagné au premier réglage. */
    acquis?: string;
  }

  const { acquis }: Props = $props();
  const FINE = '\u202F';
  const cleAcquis = untrack(() => acquis);

  const BETA = 'dpo:beta';
  const CHOISIE = 'dpo:choisie';
  const REJETEE = 'dpo:rejetee';
  const indiceBeta = canal<number>(BETA, INDICE_BETA_DEPART);
  const ecartChoisie = canal<number>(CHOISIE, ECART_CHOISIE_DEPART);
  const ecartRejetee = canal<number>(REJETEE, ECART_REJETEE_DEPART);

  const p = $derived(phraseDeLaPerteDpo(betaDeLIndice($indiceBeta), $ecartChoisie, $ecartRejetee));
  /** « nat » jusqu'à 2 exclus, « nats » au-delà, comme le pluriel français. */
  const unite = $derived(Number(p.perte.replace(',', '.')) >= 2 ? 'nats' : 'nat');

  // L'acquis : au premier réglage d'un des trois nombres.
  const depart = `${INDICE_BETA_DEPART}|${ECART_CHOISIE_DEPART}|${ECART_REJETEE_DEPART}`;
  $effect(() => {
    const maintenant = `${$indiceBeta}|${$ecartChoisie}|${$ecartRejetee}`;
    if (maintenant === depart || cleAcquis === undefined || acquisAnnonce) return;
    acquisAnnonce = true;
    const detail: DetailAcquis = { cle: cleAcquis };
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail }));
  });

  // Les lecteurs d'écran entendent la perte et la suite quand le lecteur change un nombre (pas à l'arrivée).
  let annonce = $state('');
  let avant = untrack(() => `${p.perte}|${p.suite}`);
  $effect(() => {
    const maintenant = `${p.perte}|${p.suite}`;
    if (maintenant === avant) return;
    avant = maintenant;
    annonce = untrack(() => `La perte vaut ${p.perte} ${unite}. ${p.suite}`);
  });
</script>

<figure class="phrase-dpo" data-figure="phrase-dpo">
  <p class="reglage">
    Avec β = <NombreManipulable
      canal={BETA}
      min={INDICE_BETA_MIN}
      max={INDICE_BETA_MAX}
      initiale={INDICE_BETA_DEPART}
      etiquette="β, la force de la préférence"
      testId="dpo-beta"
      texte={(i) => nombre(betaDeLIndice(i), 2)}
      pixelsParUnite={18}
    />, si la réponse choisie s’écarte de la référence de <NombreManipulable
      canal={CHOISIE}
      min={ECART_MIN}
      max={ECART_MAX}
      pas={PAS_D_ECART}
      initiale={ECART_CHOISIE_DEPART}
      etiquette="L’écart de la réponse choisie à la référence, en nats"
      testId="dpo-choisie"
      texte={ecartEnTexte}
      pixelsParUnite={14}
    /> nat, et la rejetée de <NombreManipulable
      canal={REJETEE}
      min={ECART_MIN}
      max={ECART_MAX}
      pas={PAS_D_ECART}
      initiale={ECART_REJETEE_DEPART}
      etiquette="L’écart de la réponse rejetée à la référence, en nats"
      testId="dpo-rejetee"
      texte={ecartEnTexte}
      pixelsParUnite={14}
    />, la perte de la paire vaut <strong data-test="dpo-perte">{p.perte}</strong>{' '}{unite}.
  </p>
  <p class="suite" data-test="dpo-suite">{p.suite}</p>
  <p class="vh" role="status">{annonce}</p>
  <figcaption>
    Un écart de +1 nat{FINE}: ton IA donne à la réponse environ 2,7 fois (e fois) la probabilité que lui donne la
    référence{FINE}; −1, environ 2,7 fois moins. La perte vient de dpo.ts, le jumeau de la perte à la main du projet.
  </figcaption>
</figure>

<style>
  .phrase-dpo {
    margin: 0.6em 0 1.6em;
  }

  .reglage {
    margin: 0;
    line-height: 1.9;
  }

  strong {
    font-family: var(--titres);
    font-variant-numeric: tabular-nums;
  }

  .suite {
    margin: 0.5em 0 0;
  }

  figcaption {
    margin-top: 8px;
    font-family: var(--titres);
    font-size: 14px;
    line-height: 1.45;
    color: var(--indigo-doux);
  }
</style>
