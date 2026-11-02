// Parcours du code expliqué et des liens vers le projet, sur la page d'essai
// /forge-ia/essais/gabarit/ (construite seulement avec FORGE_ESSAIS=1).
// Le code affiché doit être celui du fichier testé, pas une copie.
import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { extraireRegion } from '../src/lib/regions';
import { verifierAxe, verifierSansDebordement } from './outils';

const PAGE = '/forge-ia/essais/gabarit/';
const FICHIER = 'projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py';
// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const attendu = extraireRegion(readFileSync(`../${FICHIER}`, 'utf8'), 'choisir', FICHIER);
const NB_LIGNES = attendu.split('\n').length;

/** Numéros des lignes allumées, dans l'ordre. */
async function lignesAllumees(page: import('@playwright/test').Page): Promise<number[]> {
  return page.$$eval('.code-explique [data-l].allumee', (els) => els.map((e) => Number(e.getAttribute('data-l'))));
}

test('le code affiché est identique à la région du fichier testé', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('.code-explique pre')).toHaveText(attendu);
  // À l'octet près : les numéros de ligne et la coloration ne s'ajoutent pas au texte.
  const texte = await page.locator('.code-explique pre').evaluate((pre) => pre.textContent);
  expect(texte).toBe(attendu);
  // Aucun marqueur de région ne doit apparaître.
  expect(texte).not.toMatch(/# region|# fin/);
});

test('copier le code donne la région du fichier, lignes vides comprises', async ({ page }) => {
  await page.goto(PAGE);
  // Ce que le lecteur copie vers Colab : la sélection de tout le bloc, pas son textContent.
  const copie = await page.locator('.code-explique pre').evaluate((pre) => {
    const selection = getSelection()!;
    selection.removeAllRanges();
    selection.selectAllChildren(pre);
    return selection.toString();
  });
  expect(attendu).toContain('\n\n'); // la région de test a bien une ligne vide
  expect(copie).toBe(attendu);
});

test('chaque ligne porte son numéro, de 1 à N', async ({ page }) => {
  await page.goto(PAGE);
  const numeros = await page.$$eval('.code-explique pre [data-l]', (els) => els.map((e) => e.getAttribute('data-l')));
  expect(numeros).toEqual(Array.from({ length: NB_LIGNES }, (_, i) => String(i + 1)));
});

test('le chemin du fichier renvoie vers GitHub', async ({ page }) => {
  await page.goto(PAGE);
  const lien = page.locator('.code-explique').getByRole('link', { name: FICHIER });
  await expect(lien).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${FICHIER}`);
});

test('au repos, aucune ligne n’est allumée', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('.code-explique [data-l]').first()).toBeVisible();
  expect(await lignesAllumees(page)).toEqual([]);
});

test('survoler une explication allume ses lignes, la quitter les éteint', async ({ page }) => {
  await page.goto(PAGE);
  const premiere = page.locator('.code-explique li').first();
  await premiere.hover();
  await expect(page.locator('.code-explique [data-l].allumee')).not.toHaveCount(0);
  const voulues = (await premiere.getAttribute('data-lignes'))!;
  expect(voulues).toMatch(/^\d+(-\d+)?$/);
  const [debut, fin = debut] = voulues.split('-').map(Number);
  expect(await lignesAllumees(page)).toEqual(
    Array.from({ length: fin - debut + 1 }, (_, i) => debut + i),
  );
  await page.mouse.move(0, 0);
  await expect(page.locator('.code-explique [data-l].allumee')).toHaveCount(0);
});

test('une explication qui vise une plage allume toutes ses lignes', async ({ page }) => {
  await page.goto(PAGE);
  const plage = page.locator('.code-explique li[data-lignes*="-"]').first();
  const [debut, fin] = (await plage.getAttribute('data-lignes'))!.split('-').map(Number);
  expect(fin).toBeGreaterThan(debut);
  await plage.hover();
  expect(await lignesAllumees(page)).toEqual(Array.from({ length: fin - debut + 1 }, (_, i) => debut + i));
});

test('le focus clavier d’une explication allume ses lignes, le quitter les éteint', async ({ page }) => {
  await page.goto(PAGE);
  const explications = page.locator('.code-explique li');
  await explications.nth(1).focus();
  await expect(explications.nth(1)).toBeFocused();
  await expect(page.locator('.code-explique [data-l].allumee')).not.toHaveCount(0);
  await page.keyboard.press('Tab');
  await expect(explications.nth(2)).toBeFocused();
  await expect(page.locator('.code-explique [data-l].allumee')).not.toHaveCount(0);
  await explications.nth(2).blur();
  await expect(page.locator('.code-explique [data-l].allumee')).toHaveCount(0);
});

test('focus, puis souris qui passe et repart : les lignes restent allumées tant que le focus y est', async ({ page }) => {
  await page.goto(PAGE);
  const explication = page.locator('.code-explique li').nth(1);
  await explication.focus();
  await expect(explication).toBeFocused();
  const avant = await lignesAllumees(page);
  expect(avant.length).toBeGreaterThan(0);
  // La souris survole l'explication, puis s'en va : le focus, lui, reste.
  await explication.hover();
  await page.mouse.move(0, 0);
  await expect(explication).toBeFocused();
  expect(await lignesAllumees(page)).toEqual(avant);
  // Le focus parti, la lumière s'éteint.
  await explication.blur();
  await expect(page.locator('.code-explique [data-l].allumee')).toHaveCount(0);
});

test('un clic donne le focus à l’explication : la souris qui repart n’éteint rien', async ({ page }) => {
  await page.goto(PAGE);
  const explication = page.locator('.code-explique li').nth(1);
  await explication.click();
  await expect(explication).toBeFocused();
  const avant = await lignesAllumees(page);
  expect(avant.length).toBeGreaterThan(0);
  await page.mouse.move(0, 0);
  await expect(explication).toBeFocused();
  expect(await lignesAllumees(page)).toEqual(avant);
});

test('deux explications actives (focus sur l’une, souris sur l’autre) : les lignes des deux sont allumées', async ({ page }) => {
  await page.goto(PAGE);
  const explications = page.locator('.code-explique li');
  await explications.nth(1).focus(); // lignes 4 à 5
  await explications.nth(2).hover(); // ligne 7
  await expect.poll(() => lignesAllumees(page)).toEqual([4, 5, 7]);
  await page.mouse.move(0, 0);
  await expect.poll(() => lignesAllumees(page)).toEqual([4, 5]);
});

test('on atteint les explications au clavier, avec un focus visible', async ({ page }) => {
  await page.goto(PAGE);
  const premiere = page.locator('.code-explique li').first();
  await expect(premiere).toHaveAttribute('tabindex', '0');
  await premiere.focus();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Tab');
  await expect(premiere).toBeFocused();
  const contour = await premiere.evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(contour).not.toBe('none');
});

test('chaque explication dit aux lecteurs d’écran quelles lignes elle vise', async ({ page }) => {
  await page.goto(PAGE);
  const explications = page.locator('.code-explique li');
  await expect(explications.first()).toContainText('Ligne 1. La fonction');
  await expect(explications.nth(1)).toContainText('Lignes 4 à 5. En cas');
  // Ce texte n'est pas montré à l'écran : une boîte d'un pixel.
  const boite = await explications.nth(1).locator('.lignes-visees').boundingBox();
  expect(boite!.width).toBeLessThanOrEqual(1);
});

test('la lumière d’une ligne est le soleil pâle', async ({ page }) => {
  await page.goto(PAGE);
  await page.locator('.code-explique li').first().hover();
  // Le fond s'allume en un instant : on attend la fin de la transition.
  await expect(page.locator('.code-explique [data-l].allumee').first()).toHaveCSS(
    'background-color',
    'rgb(255, 244, 214)', // #FFF4D6
  );
});

test('le bloc a le fond brume claire et le texte indigo', async ({ page }) => {
  await page.goto(PAGE);
  const { fond, encre } = await page.locator('.code-explique pre').evaluate((pre) => {
    const s = getComputedStyle(pre);
    return { fond: s.backgroundColor, encre: s.color };
  });
  expect(fond).toBe('rgb(245, 244, 250)'); // #F5F4FA
  expect(encre).toBe('rgb(35, 32, 87)'); // #232057
});

test('le code est en JetBrains Mono', async ({ page }) => {
  await page.goto(PAGE);
  const famille = await page.locator('.code-explique pre').evaluate((pre) => getComputedStyle(pre).fontFamily);
  expect(famille).toContain('JetBrains Mono Variable');
});

test('les liens du projet : le dépôt et le notebook Colab', async ({ page }) => {
  await page.goto(PAGE);
  const complet = page.getByRole('link', { name: 'Le projet complet', exact: true });
  await expect(complet).toHaveAttribute('href', 'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.3-tokenizer');
  const colab = page.getByRole('link', { name: 'Ouvrir dans Colab', exact: true });
  await expect(colab).toHaveAttribute(
    'href',
    'https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/1.3-tokenizer.ipynb',
  );
});

test('les liens du projet sont du texte simple : ni flèche, ni point médian', async ({ page }) => {
  await page.goto(PAGE);
  const textes = await page.locator('.liens-projet li').allTextContents();
  expect(textes.map((t) => t.trim())).toEqual(['Le projet complet', 'Ouvrir dans Colab']);
  expect(textes.join('')).not.toMatch(/[→·•]/);
});

test('sans JavaScript : le code et les explications restent lisibles', async ({ browser }) => {
  const contexte = await browser.newContext({ javaScriptEnabled: false });
  const page = await contexte.newPage();
  await page.goto(`http://127.0.0.1:8531${PAGE}`);
  await expect(page.locator('.code-explique pre')).toHaveText(attendu);
  await expect(page.locator('.code-explique li').first()).toBeVisible();
  await contexte.close();
});

test('accessibilité et largeur : le code défile dans son bloc, pas dans la page', async ({ page }, info) => {
  await page.goto(PAGE);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const pre = page.locator('.code-explique pre');
  expect(await pre.evaluate((el) => getComputedStyle(el).overflowX)).toBe('auto');
  if (info.project.name === 'mobile') {
    // À 390 px, les lignes les plus longues ne tiennent pas : elles défilent dans le bloc.
    expect(await pre.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
  }
});

test('accessibilité pendant qu’une explication est allumée', async ({ page }) => {
  await page.goto(PAGE);
  await page.locator('.code-explique li').first().focus();
  await expect(page.locator('.code-explique [data-l].allumee')).not.toHaveCount(0);
  await verifierAxe(page);
});
