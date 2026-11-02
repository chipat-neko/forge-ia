// Parcours du gabarit de chapitre, sur la page d'essai /forge-ia/essais/gabarit/
// (construite seulement avec FORGE_ESSAIS=1, voir src/essais/gabarit.mdx).
import { test, expect } from '@playwright/test';
import { plusLongueLigne, verifierAxe, verifierSansDebordement } from './outils';

// Les tests du brief de la tâche 5, tels quels.

test('pari juste : verdict, boutons figés, acquis, verrou ouvert', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await expect(page.locator('[data-verrou="zone"]')).toHaveAttribute('inert', '');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await expect(page.locator('[data-pari="p1"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-pari="p1"] button').first()).toBeDisabled();
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#recap')).toContainText('1 sur 3');
  await expect(page.locator('#recap [data-acquis="a1"]')).toHaveAttribute('data-gagne', 'oui');
});

test('pari faux : « Pas tout à fait. » et bonne réponse signalée', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p2"] button:not([data-juste])').click();
  await expect(page.locator('[data-pari="p2"] .verdict')).toContainText('Pas tout à fait.');
  await expect(page.locator('[data-pari="p2"] [data-juste]')).toContainText('bonne réponse');
});

test('rechargement et lien direct : pari et verrou restaurés', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.goto('/forge-ia/essais/gabarit/#etape-2');
  await expect(page.locator('[data-pari="p1"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
});

test('effacer la progression', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.getByRole('button', { name: 'Effacer ma progression pour ce chapitre' }).click();
  await expect(page.locator('[data-pari="p1"] [data-juste]')).toBeEnabled();
});

test('sans JavaScript : tout est lisible, rien de verrouillé', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8531/forge-ia/essais/gabarit/');
  await expect(page.locator('[data-verrou="zone"]')).not.toHaveAttribute('inert', '');
  await expect(page.getByText('Dedans')).toBeVisible();
  await ctx.close();
});

test('accessibilité et largeur', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

// Compléments.

test('typographie : espace fine avant « ? » dans la prose MDX et dans les props', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  // textContent, et non toContainText : Playwright ramène toutes les espaces
  // (U+202F comprise) à une espace ordinaire avant de comparer.
  const etape1 = (await page.locator('#etape-1').textContent()) ?? '';
  expect(etape1).toContain('Pourquoi parier avant de voir\u202F?');
  expect(etape1).not.toContain('voir ?');
  // La question du pari est une prop : c'est le composant qui la typographie.
  const question = (await page.locator('[data-pari="p1"] .q').textContent()) ?? '';
  expect(question).toContain('\u202F?');
  expect(question).not.toMatch(/ \?/);
});

test('barre du haut : position, étapes faites et rechargement', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  const barre = page.locator('header');
  await expect(barre).toContainText('Partie 1, chapitre 1.3 sur 21');
  const liens = barre.locator('nav a');
  await expect(liens).toHaveCount(2);
  await expect(liens.first()).toHaveAttribute('aria-current', 'step');
  // L'étape 1 est faite quand ses deux paris sont joués.
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await expect(page.locator('#etape-1')).not.toHaveClass(/\bfaite\b/);
  await page.locator('[data-pari="p2"] [data-juste]').click();
  await expect(page.locator('#etape-1')).toHaveClass(/\bfaite\b/);
  await expect(liens.first()).toHaveClass(/\bfaite\b/);
  await expect(liens.nth(1)).toHaveAttribute('aria-current', 'step');
  // Après rechargement, la barre montre toujours l'étape 1 faite.
  await page.reload();
  await expect(liens.first()).toHaveClass(/\bfaite\b/);
  await expect(page.locator('#etape-1')).toHaveClass(/\bfaite\b/);
  await expect(page.locator('[data-pari="p2"] .verdict')).toContainText('Juste.');
  // L'étape 2, sans pari, est faite quand sa fin passe au-dessus du milieu de l'écran.
  await expect(page.locator('#etape-2')).not.toHaveClass(/\bfaite\b/);
  await page.locator('#recap').scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect(page.locator('#etape-2')).toHaveClass(/\bfaite\b/);
  await expect(liens.nth(1)).toHaveClass(/\bfaite\b/);
});

test('acquis gagné par l’événement forge:acquis, gardé au rechargement', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  const fusions = page.locator('#recap [data-acquis="fusions"]');
  await expect(fusions).toHaveAttribute('data-gagne', 'non');
  await expect(fusions).toContainText('à gagner');
  await page.evaluate(() =>
    window.dispatchEvent(new CustomEvent('forge:acquis', { detail: { cle: 'fusions' } })),
  );
  await expect(fusions).toHaveAttribute('data-gagne', 'oui');
  await expect(page.locator('#recap')).toContainText('1 sur 3');
  await page.reload();
  await expect(fusions).toHaveAttribute('data-gagne', 'oui');
});

test('progression obsolète : pari inconnu et choix hors limites ignorés', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.evaluate(() =>
    localStorage.setItem(
      'forge-ia:progression:v1',
      JSON.stringify({ '1.3': { paris: { p1: 7, disparu: 0, p2: 0 }, acquis: [], etapes: [] } }),
    ),
  );
  await page.reload();
  await expect(page.locator('[data-pari="p1"] [data-juste]')).toBeEnabled();
  await expect(page.locator('[data-verrou="zone"]')).toHaveAttribute('inert', '');
  await expect(page.locator('[data-pari="p2"] .verdict')).toContainText('Juste.');
});

test('sans JavaScript : la réponse et l’explication des paris sont lisibles', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8531/forge-ia/essais/gabarit/');
  const verdict = page.locator('[data-pari="p1"] .verdict');
  await expect(verdict).toBeVisible();
  await expect(verdict).toContainText('Réponse');
  await expect(verdict).toContainText('est B. Ce pari ouvre la zone');
  // Effacer n'a de sens qu'avec le script : le bouton reste caché.
  await expect(page.getByRole('button', { name: 'Effacer ma progression pour ce chapitre' })).toBeHidden();
  await ctx.close();
});

test('mesure : lignes de texte de 80 caractères au plus', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('accessibilité après les paris (verdicts, choix marqués)', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.locator('[data-pari="p2"] button:not([data-juste])').click();
  await expect(page.locator('[data-pari="p2"] .verdict')).toBeVisible();
  await verifierAxe(page);
  await verifierSansDebordement(page);
});
