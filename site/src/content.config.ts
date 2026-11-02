// Collection des chapitres : un fichier MDX par chapitre écrit,
// src/content/chapitres/<p>-<n>.mdx (par exemple 1-3.mdx pour le chapitre 1.3).
// Un chapitre du parcours sans fichier s'affiche « à venir ».
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { PARCOURS } from './lib/parcours';

const NUMEROS = new Set(PARCOURS.flatMap((partie) => partie.chapitres.map((c) => c.numero)));

/**
 * Données d'un chapitre (frontmatter). Les textes sont bruts : le gabarit
 * leur applique la typographie française à l'affichage.
 */
export const schemaChapitre = z
  .object({
    partie: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
    /** « partie.rang », par exemple « 1.3 » : doit exister dans PARCOURS. */
    numero: z.string().refine((n) => NUMEROS.has(n), {
      message: 'Ce numéro de chapitre n’existe pas dans le parcours (src/lib/parcours.ts).',
    }),
    titre: z.string().min(1),
    chapeau: z.string().min(1),
    /** Par exemple « 7 étapes, 4 paris, environ 15 minutes. » */
    programme: z.string().min(1),
    /**
     * Ce que le lecteur saura à la fin, dans l'ordre du chapitre. `ou` complète
     * « à gagner … », par exemple « à l'étape 3 ».
     */
    acquis: z.array(z.object({ cle: z.string().min(1), texte: z.string().min(1), ou: z.string().min(1) })),
  })
  .refine((c) => c.numero.split('.')[0] === String(c.partie), {
    message: 'Le numéro du chapitre ne correspond pas à sa partie.',
  });

export type DonneesChapitre = z.infer<typeof schemaChapitre>;

const chapitres = defineCollection({
  loader: glob({ pattern: '*.mdx', base: './src/content/chapitres' }),
  schema: schemaChapitre,
});

export const collections = { chapitres };
