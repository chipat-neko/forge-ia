import { defineConfig } from '@playwright/test';

// Parcours de test du site, sur le site construit (avec les pages d'essai)
// et servi par `astro preview` sur le port 8531, réservé à Playwright
// (8530 reste au serveur du développeur). En local, on utilise le Chrome
// installé ; en intégration continue, le Chromium de Playwright.
//
// Pour rejouer des parcours contre un site déjà en ligne, on fixe
// PLAYWRIGHT_BASE_URL (par exemple https://chipat-neko.github.io) : Playwright
// ne construit ni ne sert alors rien. Seuls les parcours qui ne lisent que la
// page s'y prêtent ; ceux qui lisent dist/ ou visent les pages d'essai non.
// Les parcours « sans JavaScript », qui ouvrent leur propre contexte, lui
// passent la baseURL de cette configuration : ils suivent la même adresse.
const adressePublique = process.env.PLAYWRIGHT_BASE_URL;

// Réglages des projets Chrome. La carte graphique reste éteinte (`--disable-gpu`) :
// l'entraînement de ton IA l'occupe sur le PC. Le canal est posé projet par projet,
// pas dans le `use` commun : un projet Firefox ou WebKit ne peut pas annuler un
// `channel: 'chrome'` hérité (Playwright ignore les valeurs `undefined`).
const chrome = {
  channel: process.env.CI ? undefined : 'chrome',
  launchOptions: { args: ['--disable-gpu'] },
};

// Firefox et WebKit, pour le seul parcours de parité (e2e/parite.spec.ts) : la
// page d'essai y refait tous les attendus du Python, pour voir si un moteur
// JavaScript s'écarte. Seulement avec FORGE_TOUS_NAVIGATEURS=1 : en
// intégration continue, et en local après `npx playwright install firefox webkit`.
// Ce sont les navigateurs de Playwright (sans canal), sans fenêtre : aucun de
// leurs processus n'apparaît dans nvidia-smi pendant le parcours (relevé du
// 04/11/2026). Firefox coupe en plus l'accélération graphique et WebGL.
//
// Garde-fou : en intégration continue, sans cette variable, les projets Firefox et
// WebKit disparaîtraient en silence et le parcours de parité ne tournerait plus que
// dans Chrome, tout en restant vert. On s'arrête donc avec un message qui dit quoi faire.
const tousLesNavigateurs = process.env.FORGE_TOUS_NAVIGATEURS === '1';
if (process.env.CI && !tousLesNavigateurs) {
  throw new Error(
    'En intégration continue, la variable FORGE_TOUS_NAVIGATEURS doit valoir 1 : sans elle, les projets ' +
      'parite-firefox et parite-webkit ne tournent pas, et la parité n’est vérifiée que dans Chrome. ' +
      'Ajoute FORGE_TOUS_NAVIGATEURS: 1 dans le bloc env de l’étape Playwright de .github/workflows/site.yml.',
  );
}
const autresNavigateurs = tousLesNavigateurs
  ? [
      {
        name: 'parite-firefox',
        testMatch: /parite\.spec\.ts/,
        use: {
          browserName: 'firefox' as const,
          launchOptions: { firefoxUserPrefs: { 'layers.acceleration.disabled': true, 'webgl.disabled': true } },
        },
      },
      { name: 'parite-webkit', testMatch: /parite\.spec\.ts/, use: { browserName: 'webkit' as const } },
    ]
  : [];

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: adressePublique || 'http://127.0.0.1:8531',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'ordinateur', use: { ...chrome, viewport: { width: 1440, height: 900 } } },
    {
      name: 'mobile',
      use: { ...chrome, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
    },
    ...autresNavigateurs,
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
