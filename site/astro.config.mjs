// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import svelte from '@astrojs/svelte';

// Site statique publié sur GitHub Pages : https://chipat-neko.github.io/forge-ia/
export default defineConfig({
  site: 'https://chipat-neko.github.io',
  base: '/forge-ia',
  trailingSlash: 'always',
  output: 'static',
  // Port réservé à ce projet (dev et aperçu). 8531 est pour Playwright.
  server: { port: 8530, host: '127.0.0.1' },
  integrations: [mdx(), svelte()],
  // Le plugin remark de typographie française (remarkTypoFr) est branché
  // ici par la tâche 4, dans markdown.remarkPlugins.
  markdown: {},
  vite: {
    server: {
      // Pour pouvoir importer le code des projets pédagogiques (../projets/**).
      fs: { allow: ['..'] },
    },
  },
});
