// Les chapitres parus : ceux qui ont un fichier dans la collection
// `chapitres`. Pour l'accueil, les pages de partie, la recherche et la 404,
// au moment de la construction. Un chapitre du parcours sans fichier est « à venir ».
import { getCollection } from 'astro:content';

export interface ChapitreParu {
  numero: string;
  /** Le programme, sans point final : « 7 étapes, 4 paris, environ 15 minutes ». */
  programme: string;
  /** Les clés de ses acquis : le chapitre est fait quand toutes sont gagnées. */
  acquis: string[];
}

/** Les chapitres parus, par numéro. */
export async function chapitresParus(): Promise<Map<string, ChapitreParu>> {
  const entrees = await getCollection('chapitres');
  return new Map(
    entrees.map(({ data }) => [
      data.numero,
      {
        numero: data.numero,
        programme: data.programme.replace(/\.\s*$/, ''),
        acquis: data.acquis.map((a) => a.cle),
      },
    ]),
  );
}
