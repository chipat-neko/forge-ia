<script lang="ts">
  // Les vraies cartes d'attention de ton IA (chapitre 1.4, « Les vraies cartes de ton IA ») : celles
  // de projets/1.6-evaluation/sorties/cartes-ton-ia.json, lues par le chapitre à la construction
  // (lireCartes, dans evaluation.ts) et passées ici. Ce composant ne lit aucun fichier et ne refait
  // aucun calcul : chaque nombre affiché est un nombre du fichier, arrondi pour se lire.
  //
  // Le lecteur choisit la tête parmi celles du fichier (deux, choisies par `cartes --choisir` : celle
  // qui regarde le jeton d'avant, celle qui regarde le plus loin). Sa carte est un vrai tableau : une
  // ligne par jeton qui regarde, une colonne par jeton regardé, et dans chaque case la part de
  // l'attention, en pour cent. Le fond va du lavande pâle (--teinte-a) à l'indigo : d'autant plus indigo
  // que la part est grande. Au-delà de la moitié, le texte passe en papier ; le fond saute alors de
  // 40 % à 62 % d'indigo, pour que le texte garde le contraste AA des deux côtés (indigo sur un fond
  // jusqu'à 40 % : 5,1 ; papier sur un fond d'au moins 62 % : 5,1).
  //
  // Sans JavaScript, la carte de la première tête se lit en entier ; les boutons, qui ne servent alors
  // à rien, sont cachés (@media (scripting: none)).
  //
  //   <CartesTonIA client:load cartes={CARTES} />
  import { untrack } from 'svelte';
  import { formaterDate } from '../../../lib/calculateur/formats';
  import { nombre, pourcent } from '../../../lib/nombres';
  import type { FichierCartes, RoleDeTete } from '../../../lib/partie-1/evaluation';
  import ZoneDefilable from '../../interactif/ZoneDefilable.svelte';

  interface Props {
    /** Le fichier des cartes (sorties/cartes-ton-ia.json), lu et vérifié par le chapitre. */
    cartes: FichierCartes;
  }

  const { cartes }: Props = $props();
  const FINE = '\u202F';
  const id = $props.id();

  // Le fichier ne change pas en cours de route.
  const F = untrack(() => cartes);
  const N = F.jetons.length;
  const NOMS: Readonly<Record<RoleDeTete, string>> = { 'jeton-d-avant': 'Le jeton d’avant', loin: 'Plus loin' };
  const RELEVE = formaterDate(F.releve_le);
  const BLOC = `bloc ${nombre(F.couche + 1)} sur ${nombre(F.couches)}`;

  let choisie = $state(0);
  const carte = $derived(F.cartes[choisie]);

  /** Un jeton tel qu'on le lit : son espace écrite « ␣ », son retour à la ligne « ↵ ». */
  const visible = (j: string) => j.replace(/ /g, '␣').replace(/\n/g, '↵');
  /** La tête, comptée à partir de 1 pour le lecteur (le projet la compte à partir de 0). */
  const numero = (tete: number) => nombre(tete + 1);
  /** La part d'indigo du fond d'une case, en pour cent : voir l'en-tête. */
  const fond = (p: number) => Number((p <= 0.5 ? 80 * p : 62 + 76 * (p - 0.5)).toFixed(2));
  /** « 1,1 jeton », « 2,7 jetons ». */
  const jetons = (x: number) => `${nombre(x, 1)} ${x < 2 ? 'jeton' : 'jetons'}`;
</script>

<figure class="cartes-ton-ia" data-cartes-ton-ia>
  <div class="choix-tete" role="group" aria-label="La tête à montrer">
    {#each F.cartes as c, k (c.tete)}
      <button type="button" class="bascule-soleil" aria-pressed={choisie === k} onclick={() => (choisie = k)} data-test="cartes-tete" data-tete={c.tete}
        >{NOMS[c.role]}, tête {numero(c.tete)}</button
      >
    {/each}
  </div>

  <p class="resume" data-test="cartes-resume">
    En moyenne, la tête {numero(carte.tete)} donne {pourcent(carte.jeton_d_avant)} de son attention au jeton juste avant, et regarde
    {jetons(carte.distance)} en arrière.
  </p>

  <p class="titre-tableau" id="{id}-titre" data-test="cartes-titre">
    La tête {numero(carte.tete)} du {BLOC}{FINE}: à qui chaque jeton donne son attention
  </p>
  <ZoneDefilable
    etiquette="Carte d’attention de la tête, défilable"
    indice="Fais défiler la carte vers la droite pour voir les autres colonnes."
    seuil={600}
    testIndice="cartes-indice-defile"
  >
    <table aria-labelledby="{id}-titre" data-tete={carte.tete} data-test="cartes-carte">
      <thead>
        <tr>
          <td></td>
          {#each F.jetons as j, colonne (colonne)}
            <th scope="col" data-jeton={j}><span class="jeton vertical" data-pagefind-ignore>{visible(j)}</span></th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each carte.poids as ligne, i (i)}
          <tr>
            <th scope="row" data-jeton={F.jetons[i]}><span class="jeton" data-pagefind-ignore>{visible(F.jetons[i])}</span></th>
            {#each ligne as p, j (j)}
              {#if j > i}
                <td class="masque" data-masque><span aria-hidden="true">·</span><span class="vh">masqué</span></td>
              {:else}
                <td class:claire={p > 0.5} style:--fond="{fond(p)}%" data-poids={p}>{nombre(100 * p)}</td>
              {/if}
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </ZoneDefilable>

  <figcaption class="legende" data-test="cartes-legende">
    La phrase «{FINE}{F.phrase}{FINE}», découpée en {nombre(N - 1)} jetons par le tokenizer de ton IA, après son jeton de début,
    <code>{F.jetons[0]}</code>. Ces nombres ont été calculés sur le processeur par <code>cartes_attention</code>, depuis les poids publiés de {F.nom}, le
    {RELEVE}. Chaque case, en pour cent, est arrondie{FINE}; chaque ligne fait 100 avant l’arrondi. Les cases au-dessus de la diagonale
    sont masquées{FINE}: un jeton ne regarde jamais la suite.
  </figcaption>
</figure>

<style>
  .cartes-ton-ia {
    margin: 1em 0 1.6em;
  }

  .choix-tete {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    margin: 0 0 12px;
  }

  .choix-tete .bascule-soleil {
    font-family: var(--titres);
    font-weight: 700;
    font-size: 17px;
    min-height: 32px;
    padding: 0 8px;
  }

  .resume {
    margin: 0 0 14px;
  }

  .titre-tableau {
    font-family: var(--titres);
    font-weight: 600;
    font-size: 16px;
    line-height: 1.35;
    color: var(--indigo-doux);
    margin: 0 0 6px;
  }

  /* Bordures séparées : avec des bordures fusionnées, celles des cases qui
     défilent passeraient par-dessus la colonne des jetons, restée en place. */
  table {
    font-family: var(--titres);
    font-size: 13px;
    border-collapse: separate;
    border-spacing: 0;
  }

  /* Un jeton tel quel : « <|fin_texte|> » reste écrit avec ses caractères, sans ligature. */
  .jeton {
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre;
    font-variant-ligatures: none;
  }

  /* En tête de colonne, le jeton se lit de bas en haut : les colonnes restent étroites, et la carte
     tient dans la colonne de lecture sur un ordinateur. */
  .jeton.vertical {
    display: inline-block;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }

  thead th {
    font-weight: 400;
    color: var(--indigo);
    padding: 0 0 6px;
    text-align: center;
    vertical-align: bottom;
  }

  /* Le fond d'une case : du lavande pâle à l'indigo (--fond, en pour cent d'indigo). Le filet blanc
     entre deux cases est dessiné dans la case (ombre intérieure). */
  td {
    min-width: 2.1em;
    padding: 4px 1px;
    text-align: center;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    border: 0;
    box-shadow: inset -1px -1px 0 var(--papier);
    background: color-mix(in srgb, var(--indigo) var(--fond, 0%), var(--teinte-a));
    color: var(--indigo);
  }

  td.claire {
    color: var(--papier);
  }

  td.masque {
    background: var(--papier);
    color: var(--lavande);
  }

  /* Quand la carte défile (sur un téléphone), la colonne des jetons reste en place. */
  tbody th,
  thead td {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--papier);
    padding: 0 8px 0 0;
    text-align: right;
    font-weight: 400;
  }

  thead td {
    min-width: 0;
    box-shadow: none;
  }

  .legende {
    font-family: var(--titres);
    font-size: 15px;
    line-height: 1.45;
    color: var(--indigo-doux);
    margin: 14px 0 0;
  }

  .legende code {
    font-size: 0.95em;
  }

  /* Sans JavaScript, les boutons ne servent à rien : la carte de la première tête se lit seule. */
  @media (scripting: none) {
    .choix-tete {
      display: none;
    }
  }
</style>
