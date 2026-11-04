// Les sorties de commande enregistrées dans le dépôt, que montre
// SortieCommande.astro : ce qu'un script a vraiment affiché, pas une copie à
// la main. Un script qui enregistre sa sortie (par exemple `--enregistrer`)
// l'écrit en UTF-8 et LF, précédée d'une ligne `# relevé le AAAA-MM-JJ`.
import { formaterDate } from './calculateur/formats';

const LIGNE_DE_DATE = /^# relevé le (\d{4}-\d{2}-\d{2})[ \t]*$/;

/** Ce que SortieCommande affiche d'un fichier de sortie. */
export interface Sortie {
  /** La date de la ligne `# relevé le`, au format AAAA-MM-JJ, ou null sans cette ligne. */
  releveLe: string | null;
  contenu: string;
}

/**
 * Le contenu à afficher d'un fichier de sortie (`fichier` : son chemin, pour
 * les messages d'erreur) : sans BOM, sans retour chariot, sans lignes vides à
 * la fin, et sans sa première ligne `# relevé le AAAA-MM-JJ` s'il en a une (sa
 * date est alors dans `releveLe`). Null s'il ne reste rien à afficher : un
 * fichier vide, ou réduit à sa ligne de date, compte comme absent. Une date de
 * relevé impossible lève une erreur qui nomme le fichier.
 */
export function lireSortie(texte: string, fichier: string): Sortie | null {
  const lignes = texte
    .replace(/^\uFEFF/, '')
    .replace(/\r\n?/g, '\n')
    .replace(/\n+$/, '')
    .split('\n');
  const date = LIGNE_DE_DATE.exec(lignes[0]);
  if (date !== null) {
    try {
      formaterDate(date[1]);
    } catch {
      throw new RangeError(
        `${fichier} : la ligne «\u202F# relevé le ${date[1]}\u202F» n’a pas une date du calendrier (AAAA-MM-JJ). ` +
          'Corrige-la, ou relance le script qui enregistre cette sortie.',
      );
    }
  }
  const contenu = (date === null ? lignes : lignes.slice(1)).join('\n');
  if (contenu.trim() === '') return null;
  return { releveLe: date === null ? null : date[1], contenu };
}

/**
 * La légende d'une sortie : « {legende}, relevée le 4 novembre 2026. » avec la
 * date du relevé, « {legende}. » sans.
 */
export function legendeSortie(legende: string, releveLe: string | null): string {
  return releveLe === null ? `${legende}.` : `${legende}, relevée le ${formaterDate(releveLe)}.`;
}
