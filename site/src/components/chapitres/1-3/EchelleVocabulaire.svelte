<script lang="ts">
  // L'échelle de l'encadré « Et chez un grand labo ? » (maquette 10) : la
  // taille du vocabulaire du tokenizer du chapitre, réglable avec le même
  // nombre que l'atelier (même canal), face à celle d'un grand modèle, sur la
  // même échelle. Ton vocabulaire y tient dans un trait.
  //
  // À poser dans l'EncadreLabo avec client:load. Le nombre ne porte pas de
  // data-test : sur une page, seul celui de l'atelier en a un.
  import { untrack } from 'svelte';
  import { canal } from '../../../lib/canal';
  import { tokenizer13 } from '../../../lib/bpe';
  import NombreManipulable from '../../interactif/NombreManipulable.svelte';
  import { FUSIONS_AU_DEPART, NB_FUSIONS } from './fusions';

  interface Props {
    /** Le grand modèle de comparaison et la taille de son vocabulaire (sourcée). */
    grandModele: { nom: string; taille: number };
    /** Nom du canal du nombre de fusions ; « fusions » par défaut. */
    canalFusions?: string;
    /** Nom du verrou qui désactive le nombre tant qu'il n'est pas ouvert. */
    verrou?: string;
  }

  const { grandModele, canalFusions = 'fusions', verrou }: Props = $props();

  const fusions = canal<number>(untrack(() => canalFusions), FUSIONS_AU_DEPART);
  const k = $derived($fusions);
  // Le vocabulaire : les caractères de base, plus un morceau par fusion apprise.
  const base = tokenizer13.base.length;
  const vocabulaire = $derived(base + k);
  const largeur = $derived(`${(100 * vocabulaire) / grandModele.taille}%`);

  const FINE = '\u202F';
  const nombre = new Intl.NumberFormat('fr-FR');
  const pluriel = (n: number, un: string, plusieurs: string) => (n > 1 ? plusieurs : un);
</script>

<div class="echelle">
  <p>
    Ton tokenizer connaît en ce moment {base} caractères et <NombreManipulable
      canal={canalFusions}
      min={0}
      max={NB_FUSIONS}
      initiale={FUSIONS_AU_DEPART}
      etiquette="Nombre de fusions apprises"
      {verrou}
    />
    {pluriel(k, 'fusion', 'fusions')}, soit <span class="calcule">{nombre.format(vocabulaire)}</span> morceaux.
  </p>
  <!-- Les barres répètent le texte en image : les lecteurs d'écran ont déjà les nombres. -->
  <div class="barres" aria-hidden="true">
    <div class="rangee">
      <span>Le tien</span>
      <span class="barre"><i style:width={largeur}></i></span>
    </div>
    <div class="rangee">
      <span>{grandModele.nom}</span>
      <span class="barre grande"><i></i></span>
    </div>
  </div>
  <p class="legende">Même échelle pour les deux barres{FINE}: à côté de {grandModele.nom}, ton vocabulaire tient dans un trait.</p>
</div>

<style>
  .echelle {
    margin-top: 18px;
  }

  .calcule {
    font-family: var(--titres);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .rangee {
    display: grid;
    grid-template-columns: 9.5em minmax(0, 1fr);
    gap: 12px;
    align-items: center;
    margin-top: 10px;
    font-family: var(--titres);
    font-size: 16px;
  }

  .barre {
    height: 12px;
    background: color-mix(in srgb, var(--papier) 14%, transparent);
    border-radius: 3px;
    position: relative;
    overflow: hidden;
  }

  .barre i {
    position: absolute;
    inset: 0 auto 0 0;
    min-width: 3px;
    max-width: 100%;
    background: var(--teinte-b);
  }

  .barre.grande i {
    width: 100%;
    background: var(--papier);
  }

  .legende {
    font-family: var(--titres);
    font-size: 15px;
    line-height: 1.5;
    color: var(--brume);
    margin: 10px 0 0;
  }

  @media (max-width: 720px) {
    .rangee {
      grid-template-columns: minmax(0, 1fr);
      gap: 4px;
    }
  }
</style>
