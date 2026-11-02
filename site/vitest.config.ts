/// <reference types="vitest/config" />
import { getViteConfig } from 'astro/config';
import astroConfig from './astro.config.mjs';

// getViteConfig reprend la configuration d'Astro (plugins, alias), mais
// Vitest impose la base « / » à Vite et masque la définition d'Astro :
// sans le réglage ci-dessous, import.meta.env.BASE_URL vaut « / » dans les
// tests. On la reprend de astro.config.mjs, avec la barre oblique finale
// qu'Astro ajoute avec trailingSlash: 'always', pour que la valeur soit la
// même dans les tests et dans le site construit (« /forge-ia/ »).
const base = (astroConfig.base ?? '/').replace(/\/?$/, '/');

export default getViteConfig({
  test: {
    include: ['src/**/*.test.ts'],
    env: { BASE_URL: base },
  },
});
