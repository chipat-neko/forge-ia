// @ts-check
import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';
import mdx from '@astrojs/mdx';
import svelte from '@astrojs/svelte';
import { remarkTypoFr } from './src/lib/remark-typo-fr.ts';

// Site statique publié sur GitHub Pages : https://chipat-neko.github.io/forge-ia/
export default defineConfig({
  site: 'https://chipat-neko.github.io',
  base: '/forge-ia',
  trailingSlash: 'always',
  output: 'static',
  // Port réservé à ce projet (dev et aperçu). 8531 est pour Playwright.
  server: { port: 8530, host: '127.0.0.1' },
  integrations: [mdx(), svelte()],
  // Typographie française (espaces fines) sur tous les textes Markdown et MDX.
  // Astro 7 traite le Markdown avec Sätteri par défaut, qui n'exécute pas les
  // plugins remark : on passe donc par le processeur unified, qui les exécute
  // (et que l'intégration MDX reprend, car elle étend la config Markdown).
  // La clé markdown.remarkPlugins est dépréciée et inopérante avec Sätteri.
  markdown: {
    processor: unified({ remarkPlugins: [remarkTypoFr] }),
  },
  vite: {
    server: {
      // Pour pouvoir importer le code des projets pédagogiques (../projets/**).
      fs: { allow: ['..'] },
    },
  },
});
