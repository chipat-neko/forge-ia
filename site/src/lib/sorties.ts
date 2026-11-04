// Les sorties de commande enregistrées dans le dépôt, que montre
// SortieCommande.astro : ce qu'un script a vraiment affiché, pas une copie à
// la main. Un script qui enregistre sa sortie (par exemple `--enregistrer`)
// l'écrit en UTF-8 et LF, précédée d'une ligne `# relevé le AAAA-MM-JJ`.
import { formaterDate } from './calculateur/formats';

const LIGNE_DE_DATE = /^# relevé le (\d{4}-\d{2}-\d{2})[ \t]*$/;

/**
 * Le contenu à afficher d'un fichier de sortie : sans retour chariot, sans
 * lignes vides à la fin, et sans sa première ligne `# relevé le AAAA-MM-JJ`
 * s'il en a une (sa date est alors dans `releveLe`).
 */
export function lireSortie(texte: string): { releveLe: string | null; contenu: string } {
  const lignes = texte.replace(/\r\n?/g, '\n').replace(/\n+$/, '').split('\n');
  const date = LIGNE_DE_DATE.exec(lignes[0]);
  return date === null
    ? { releveLe: null, contenu: lignes.join('\n') }
    : { releveLe: date[1], contenu: lignes.slice(1).join('\n') };
}

/**
 * La légende d'une sortie : « {legende}, relevée le 4 novembre 2026. » avec la
 * date du relevé, « {legende}. » sans. Une date impossible lève une erreur.
 */
export function legendeSortie(legende: string, releveLe: string | null): string {
  return releveLe === null ? `${legende}.` : `${legende}, relevée le ${formaterDate(releveLe)}.`;
}
