import { defineConfig } from '@playwright/test';

// Parcours de test du site, sur le site construit (avec les pages d'essai)
// et servi par `astro preview` sur le port 8531, réservé à Playwright
// (8530 reste au serveur du développeur). En local, on utilise le Chrome
// installé ; en intégration continue, le Chromium de Playwright.
//
// Pour rejouer des parcours contre un site déjà en ligne, on fixe
// PLAYWRIGHT_BASE_URL (par exemple https://chipat-neko.github.io) : Playwright
// ne construit ni ne sert alors rien. Seuls les parcours qui ne lisent que la
// page s'y prêtent ; ceux qui visent 127.0.0.1:8531 ou lisent dist/ non.
const adressePublique = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: adressePublique || 'http://127.0.0.1:8531',
    channel: process.env.CI ? undefined : 'chrome',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'ordinateur', use: { viewport: { width: 1440, height: 900 } } },
    {
      name: 'mobile',
      use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
    },
  ],
  webServer: adressePublique
    ? undefined
    : {
        command: 'npm run build:essais && npm run preview -- --port 8531',
        url: 'http://127.0.0.1:8531/forge-ia/',
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
      },
});
