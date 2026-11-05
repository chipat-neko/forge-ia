<script lang="ts">
  // La figure des tirages du chapitre 0.2 : les mots qui suivent « le » dans
  // un petit texte (EXEMPLE_COMPTES), tirés au sort selon leurs probabilités,
  // de 10 à 100 000 fois. Pour chaque mot, une barre de la probabilité
  // (contour lavande) et une barre de la fréquence tirée (indigo plein), puis
  // les nombres en toutes lettres : « fer : 60 % attendu, 58 sur 100 tirés (58 %) ».
  //
  // Les tirages sont ceux du jumeau exact du Python (src/lib/partie-0/maths.ts),
  // avec le même Hasard : même graine, mêmes comptes. « Autre graine » passe à
  // la graine suivante.
  //
  // À placer dans le MDX avec client:load :
  //   <FigureTirage client:load />
  // Le nombre de tirages vit dans le canal « tir:n » (son rang dans
  // NOMBRES_DE_TIRAGES). Avec `verrou`, le nombre et le bouton restent
  // désactivés tant que le verrou n'est pas ouvert. Les barres répètent les
  // nombres en image : les lecteurs d'écran ont déjà les nombres.
  //
  // Sans JavaScript, Astro rend la figure telle qu'elle est à l'arrivée.
  import { untrack } from 'svelte';
  import { readable } from 'svelte/store';
  import { canal, ouverture } from '../../../lib/canal';
  import { GRAINE_TIRAGE } from '../../../lib/partie-0/maths';
  import { INDICE_TIRAGES_DEPART, NOMBRES_DE_TIRAGES, resultatsDesTirages } from '../../../lib/partie-0/paris-0-2';
  import { nombre } from '../../../lib/nombres';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';

  interface Props {
    /** Nom du verrou qui désactive le nombre et le bouton tant qu'il n'est pas ouvert. */
    verrou?: string;
  }

  const { verrou }: Props = $props();

  const FINE = '\u202F';
  const CANAL_N = 'tir:n';

  // Le canal et le verrou sont lus une fois pour toutes, comme dans NombreManipulable.
  const indiceN = canal<number>(CANAL_N, INDICE_TIRAGES_DEPART);
  const nomDuVerrou = untrack(() => verrou);
  const ouvert = nomDuVerrou ? ouverture(nomDuVerrou) : readable(true);

  let graine = $state(GRAINE_TIRAGE);
  let annonce = $state('');

  const n = $derived(NOMBRES_DE_TIRAGES[$indiceN]);
  const lignes = $derived(resultatsDesTirages(n, graine));

  function autreGraine(): void {
    if (!$ouvert) return;
    graine += 1;
    // Lu après le clic : les comptes de la nouvelle graine. `lignes` se recalcule
    // ici, une seule fois ; l'affichage reprend ce même calcul.
    const faits = lignes
      .map((l) => `${l.nom} ${nombre(l.compte)}`)
      .join(', ');
    annonce = `Avec la graine ${nombre(graine)}${FINE}: ${faits}, sur ${nombre(n)} tirages.`;
  }

  const texteN = (i: number) => nombre(NOMBRES_DE_TIRAGES[i]);
  /** La largeur d'une barre, en pour cent de la piste. */
  const largeur = (fraction: number) => String(Math.round(fraction * 10000) / 100);
</script>

<div class="figure-tirage" data-figure="tirage">
  <p class="reglage">
    Tire au sort <NombreManipulable
      canal={CANAL_N}
      min={0}
      max={NOMBRES_DE_TIRAGES.length - 1}
      initiale={INDICE_TIRAGES_DEPART}
      etiquette="Nombre de tirages"
      verrou={nomDuVerrou}
      testId="tir-n"
      texte={texteN}
      pixelsParUnite={24}
    /> fois le mot qui suit «{FINE}le{FINE}».
  </p>

  <table class="resultats" data-test="tir-resultats">
    <caption>Sur {nombre(n)} tirages, avec la graine {nombre(graine)}{FINE}:</caption>
    <tbody>
      {#each lignes as l (l.nom)}
        <tr>
          <th scope="row">{l.nom}</th>
          <td>
            <svg class="barres" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true">
              <rect class="piste" x="0" y="0" width="100" height="20" />
              <rect class="probabilite" x="0" y="1" width={largeur(l.proba)} height="18" />
              <rect class="frequence" x="0" y="6" width={largeur(l.compte / n)} height="8" />
            </svg><span class="chiffres">{l.attendu}, {l.tires}</span>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>

  <p class="legende" aria-hidden="true">
    <span
      ><svg class="cle" viewBox="0 0 26 14"><rect class="probabilite" x="1" y="1" width="24" height="12" /></svg> la probabilité</span
    >
    <span><svg class="cle" viewBox="0 0 26 14"><rect class="frequence" x="1" y="4" width="24" height="6" /></svg> la fréquence tirée</span>
  </p>

  <div class="commandes">
    <button type="button" class="bouton-relief" data-test="tir-graine" aria-disabled={$ouvert ? undefined : 'true'} onclick={autreGraine}
      >Autre graine</button
    >
  </div>
  <p class="vh" role="status" data-test="tir-annonce">{annonce}</p>
</div>

<style>
  .figure-tirage {
    margin: 1em 0 1.6em;
  }

  .reglage {
    margin: 0 0 0.6em;
    line-height: 1.9;
  }

  /* Le tableau des tirages : typographié, sans cadre, une issue par ligne. */
  .resultats {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 0.4em;
  }

  .resultats caption {
    text-align: left;
    caption-side: top;
    padding-bottom: 6px;
  }

  .resultats th {
    width: 4.2em;
    padding: 10px 12px 10px 0;
    text-align: left;
    vertical-align: top;
    font-family: var(--titres);
    font-weight: 700;
    border-top: 1px solid var(--brume);
  }

  .resultats tr:first-child th,
  .resultats tr:first-child td {
    border-top: 2px solid var(--indigo);
  }

  .resultats td {
    padding: 10px 0;
    border-top: 1px solid var(--brume);
  }

  .barres {
    display: block;
    width: 100%;
    height: 22px;
    overflow: visible;
  }

  .piste {
    fill: var(--brume-claire);
  }

  .probabilite {
    fill: none;
    stroke: var(--lavande);
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
  }

  .frequence {
    fill: var(--indigo);
  }

  .chiffres {
    display: block;
    margin-top: 4px;
    font-family: var(--titres);
    font-size: 16px;
    font-variant-numeric: tabular-nums;
    color: var(--indigo-doux);
  }

  .legende {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 18px;
    margin: 0 0 1em;
    font-family: var(--titres);
    font-size: 14px;
    color: var(--indigo-doux);
  }

  .legende > span {
    white-space: nowrap;
  }

  .cle {
    display: inline-block;
    width: 26px;
    height: 14px;
    margin-right: 4px;
    vertical-align: middle;
    overflow: visible;
  }

  .commandes {
    margin: 0;
  }

  .bouton-relief {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 18px;
    line-height: 1.15;
    padding: 10px 16px;
  }

  @media (max-width: 720px) {
    .bouton-relief {
      font-size: 17px;
      padding: 9px 14px;
    }
  }
</style>
