// Parcours de l'atelier du tokenizer (chapitre 1.3) et du nombre manipulable,
// sur la page d'essai /forge-ia/essais/gabarit/ (construite seulement avec
// FORGE_ESSAIS=1, voir src/essais/gabarit.mdx). L'atelier y est posé derrière
// le verrou « zone », ouvert par le pari p1 ; la phrase découpée d'ouverture
// est en tête de la page.
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { attendreHydratation, plusLongueLigne, verifierAxe, verifierSansDebordement } from './outils';

const PAGE = '/forge-ia/essais/gabarit/';
const PHRASE = 'Les forgerons découpent le texte en jetons.';
// La phrase de départ de l'atelier, qui est aussi la phrase découpée en tête de la page.
const PHRASE_INITIALE = "Le forgeron frappe le métal sur l'enclume.";
const FINE = '\u202F';

// Les attendus calculés par le Python (le TypeScript donne les mêmes, voir
// src/lib/bpe.test.ts) : les fusions apprises et des découpages de référence.
// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
interface Attendus {
  fusions: [string, string, number][];
  cas: { texte: string; k: number; jetons: [string, number | null, number][] }[];
}
const attendus = JSON.parse(readFileSync('../projets/1.3-tokenizer/tests/attendus.json', 'utf8')) as Attendus;
const NB_FUSIONS = attendus.fusions.length;

/** Affichage d'un morceau : l'espace devient « ␣ », le retour à la ligne « ↵ ». */
const visible = (s: string) => s.replace(/ /g, '␣').replace(/\n/g, '↵');

/** Le découpage de référence d'un texte avec k fusions, tel que l'atelier l'affiche. */
function reference(texte: string, k: number): { morceaux: string[]; numeros: string[] } {
  const cas = attendus.cas.find((c) => c.texte === texte && c.k === k);
  if (!cas) throw new Error(`pas de cas de référence pour « ${texte} » avec ${k} fusions`);
  return {
    morceaux: cas.jetons.map(([t]) => visible(t)),
    numeros: cas.jetons.map(([, id]) => (id === null ? 'inconnu' : String(id))),
  };
}

/** Une fusion telle que l'atelier la liste : « fusion 30 : é + c → éc ». */
function ligneFusion(n: number): string {
  const [a, b] = attendus.fusions[n - 1];
  return `fusion ${n}${FINE}: ${visible(a)} + ${visible(b)} → ${visible(a + b)}`;
}

async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="p1"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="zone"]')).toHaveCSS('opacity', '1');
}

const jetons = (page: Page) => page.locator('[data-test="jetons"] [data-jeton]');
const nombre = (page: Page) => page.locator('[data-test="fusions"]');
const saisie = (page: Page) => page.locator('[data-test="saisie"]');

/** Règle le nombre de fusions au clavier : Home, puis k fois la flèche droite. */
async function reglerAuClavier(page: Page, k: number): Promise<void> {
  await nombre(page).focus();
  await page.keyboard.press('Home');
  for (let i = 0; i < k; i++) await page.keyboard.press('ArrowRight');
  await expect(nombre(page)).toHaveAttribute('aria-valuenow', String(k));
}

// Le test du brief de la tâche 8, à peine renforcé : l'acquis n'est pas
// gagné à 59 fusions, il l'est à 60.
test('atelier : saisie, fusions au clavier, jetons, acquis à 60, emoji et champ vide', async ({ page }) => {
  await ouvrirAtelier(page);
  await saisie(page).fill(PHRASE);
  const f = nombre(page);
  await f.focus();
  await page.keyboard.press('Home');
  await expect(jetons(page)).toHaveCount(43);
  const acquis = page.locator('#recap [data-acquis="fusions"]');
  for (let i = 0; i < 59; i++) await page.keyboard.press('ArrowRight');
  await expect(f).toHaveAttribute('aria-valuenow', '59');
  await expect(acquis).toHaveAttribute('data-gagne', 'non');
  await page.keyboard.press('ArrowRight');
  await expect(jetons(page)).toHaveCount(18);
  await expect(acquis).toHaveAttribute('data-gagne', 'oui'); // gagné à 60
  await saisie(page).fill('Salut 🙂');
  await expect(page.locator('[data-test="jetons"]')).toContainText('inconnu');
  await saisie(page).fill('');
  await expect(page.getByText('Tape une phrase pour la voir découpée.')).toBeVisible();
});

test('avant le pari, le nombre est désactivé ; le pari l’active', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const f = nombre(page);
  await expect(f).toHaveAttribute('aria-disabled', 'true');
  await expect(f).toHaveAttribute('tabindex', '-1');
  // Même une touche envoyée directement au nombre ne le fait pas bouger.
  await f.dispatchEvent('keydown', { key: 'End' });
  await expect(f).toHaveAttribute('aria-valuenow', '20');
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await expect(f).not.toHaveAttribute('aria-disabled', 'true');
  await expect(f).toHaveAttribute('tabindex', '0');
});

test('les jetons affichés et leurs numéros sont ceux du Python', async ({ page }) => {
  await ouvrirAtelier(page);
  await saisie(page).fill(PHRASE);
  for (const k of [0, 30, 60]) {
    await reglerAuClavier(page, k);
    const { morceaux, numeros } = reference(PHRASE, k);
    await expect(page.locator('[data-test="jetons"] [data-jeton] .morceau')).toHaveText(morceaux);
    await expect(page.locator('[data-test="jetons"] [data-jeton] .num')).toHaveText(numeros);
  }
  // Les teintes alternent d'un jeton au suivant.
  const fonds = await page
    .locator('[data-test="jetons"] [data-jeton] .morceau')
    .evaluateAll((els) => els.slice(0, 4).map((e) => getComputedStyle(e).backgroundColor));
  expect(fonds[0]).toBe(fonds[2]);
  expect(fonds[1]).toBe(fonds[3]);
  expect(fonds[0]).not.toBe(fonds[1]);
  // Les caractères absents du corpus : « inconnu » sous le morceau.
  await saisie(page).fill('Salut 🙂');
  const salut = reference('Salut 🙂', 60);
  await expect(page.locator('[data-test="jetons"] [data-jeton] .num')).toHaveText(salut.numeros);
});

test('la phrase des fusions, la comparaison et les trois dernières fusions', async ({ page }) => {
  await ouvrirAtelier(page);
  await saisie(page).fill(PHRASE);
  await reglerAuClavier(page, 60);
  const atelier = page.locator('[data-atelier]');
  await expect(atelier).toContainText('Avec 60 fusions apprises, ses 43 caractères tiennent en 18 jetons');
  // textContent : Playwright ramène U+202F à une espace ordinaire dans toContainText.
  // Les retours à la ligne du gabarit Svelte s'affichent comme une espace.
  const texte = ((await atelier.textContent()) ?? '').replace(/[ \n]+/g, ' ');
  expect(texte).toContain(`lettre par lettre${FINE}: 43${FINE}; mot par mot${FINE}: 7`);
  await expect(page.locator('[data-dernieres-fusions] li')).toHaveText([
    ligneFusion(60),
    ligneFusion(59),
    ligneFusion(58),
  ]);
  // L'exemple du brief : la fusion 30 colle « é » et « c ».
  await reglerAuClavier(page, 30);
  await expect(page.locator('[data-dernieres-fusions] li').first()).toHaveText(`fusion 30${FINE}: é + c → éc`);
  // Accords : une seule fusion, un seul caractère.
  await reglerAuClavier(page, 1);
  await expect(atelier).toContainText('Avec 1 fusion apprise,');
  await expect(page.locator('[data-dernieres-fusions] li')).toHaveText([ligneFusion(1)]);
  await reglerAuClavier(page, 0);
  await expect(atelier).toContainText('Avec 0 fusion apprise,');
  await expect(page.locator('[data-dernieres-fusions]')).toContainText('aucune pour l’instant');
});

test('nombre manipulable : tout le clavier et les valeurs ARIA', async ({ page }) => {
  await ouvrirAtelier(page);
  const f = nombre(page);
  await expect(f).toHaveAttribute('role', 'slider');
  await expect(f).toHaveAttribute('aria-label', 'Nombre de fusions apprises');
  await expect(f).toHaveAttribute('aria-valuemin', '0');
  await expect(f).toHaveAttribute('aria-valuemax', String(NB_FUSIONS));
  await expect(f).toHaveAttribute('aria-valuenow', '20');
  await expect(f).toHaveText('20');
  await f.focus();
  const essais: [string, number][] = [
    ['End', NB_FUSIONS],
    ['PageDown', NB_FUSIONS - 10],
    ['ArrowLeft', NB_FUSIONS - 11],
    ['ArrowDown', NB_FUSIONS - 12],
    ['ArrowUp', NB_FUSIONS - 11],
    ['ArrowRight', NB_FUSIONS - 10],
    ['PageUp', NB_FUSIONS],
    ['PageUp', NB_FUSIONS], // bloqué au maximum
    ['Home', 0],
    ['ArrowLeft', 0], // bloqué au minimum
    ['PageDown', 0],
    ['PageUp', 10],
  ];
  for (const [touche, valeur] of essais) {
    await page.keyboard.press(touche);
    await expect(f, `après ${touche}`).toHaveAttribute('aria-valuenow', String(valeur));
    await expect(f).toHaveText(String(valeur));
  }
});

test('nombre manipulable : glisser à la souris, une unité tous les 6 px', async ({ page }) => {
  await ouvrirAtelier(page);
  const f = nombre(page);
  await f.scrollIntoViewIfNeeded();
  const boite = (await f.boundingBox())!;
  const x = boite.x + boite.width / 2;
  const y = boite.y + boite.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 60, y, { steps: 6 });
  await expect(f).toHaveAttribute('aria-valuenow', '30');
  await expect(f).toHaveClass(/\bglisse\b/);
  // Le geste continue hors du nombre, et revient en arrière.
  await page.mouse.move(x - 30, y + 40, { steps: 6 });
  await expect(f).toHaveAttribute('aria-valuenow', '15');
  await page.mouse.up();
  await expect(f).not.toHaveClass(/\bglisse\b/);
  // Le glissé a donné le focus au nombre : le clavier prend le relais.
  await page.keyboard.press('ArrowRight');
  await expect(f).toHaveAttribute('aria-valuenow', '16');
});

test('nombre manipulable : glisser au doigt', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'le toucher se teste sur le projet mobile');
  await ouvrirAtelier(page);
  const f = nombre(page);
  await f.scrollIntoViewIfNeeded();
  const boite = (await f.boundingBox())!;
  const x = Math.round(boite.x + boite.width / 2);
  const y = Math.round(boite.y + boite.height / 2);
  // Playwright n'a pas de geste de glissé au doigt : on passe par Chrome directement.
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  for (let i = 1; i <= 10; i++) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + i * 6, y }] });
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await expect(f).toHaveAttribute('aria-valuenow', '30');
});

test('bascule : cacher les morceaux, puis les revoir, sans perdre le focus', async ({ page }) => {
  await ouvrirAtelier(page);
  const morceau = page.locator('[data-test="jetons"] [data-jeton] .morceau').first();
  const numero = page.locator('[data-test="jetons"] [data-jeton] .num').first();
  await expect(morceau).toBeVisible();
  await page.getByRole('button', { name: 'cacher les morceaux' }).click();
  await expect(morceau).toBeHidden();
  await expect(numero).toBeVisible();
  const revoir = page.getByRole('button', { name: 'voir les morceaux' });
  await expect(revoir).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(morceau).toBeVisible();
  await expect(page.getByRole('button', { name: 'cacher les morceaux' })).toBeFocused();
});

test('l’acquis « fusions » est annoncé une seule fois', async ({ page }) => {
  await ouvrirAtelier(page);
  await page.evaluate(() => {
    const w = window as Window & { annonces?: unknown[] };
    w.annonces = [];
    window.addEventListener('forge:acquis', (e) => w.annonces!.push((e as CustomEvent).detail));
  });
  const annonces = () => page.evaluate(() => (window as Window & { annonces?: unknown[] }).annonces);
  await reglerAuClavier(page, 59);
  expect(await annonces()).toEqual([]);
  await page.keyboard.press('End');
  await page.keyboard.press('Home');
  await page.keyboard.press('End');
  await expect(nombre(page)).toHaveAttribute('aria-valuenow', String(NB_FUSIONS));
  expect(await annonces()).toEqual([{ cle: 'fusions' }]);
});

test('saisie inhabituelle : rien ne plante, rien ne déborde', async ({ page }) => {
  const erreurs: Error[] = [];
  page.on('pageerror', (e) => erreurs.push(e));
  await ouvrirAtelier(page);
  const atelier = page.locator('[data-atelier]');
  // Espaces multiples : chaque espace reste visible, un jeton par espace.
  await saisie(page).fill('le   métal');
  await expect(page.locator('[data-test="jetons"] [data-jeton] .morceau')).toHaveText([
    'l', 'e', '␣', '␣', '␣', 'm', 'é', 't', 'a', 'l',
  ]);
  // Un champ d'une ligne ne garde pas les retours à la ligne (Chrome en fait des espaces).
  await saisie(page).fill('le\nmétal');
  await expect(saisie(page)).not.toHaveValue(/\n/);
  await expect(page.locator('[data-atelier]')).toContainText('ses 8 caractères tiennent en');
  // Un caractère absent du corpus.
  await saisie(page).fill('Ωmega');
  await expect(page.locator('[data-test="jetons"] [data-jeton]').first()).toContainText('inconnu');
  // 10 000 caractères : découpés, affichés, sans débordement.
  const long = 'Le forgeron frappe le métal. '.repeat(400).slice(0, 10_000);
  await saisie(page).fill(long);
  await expect(atelier).toContainText('ses 10 000 caractères tiennent en');
  await verifierSansDebordement(page);
  // Le nombre répond encore.
  await nombre(page).focus();
  await page.keyboard.press('End');
  await expect(atelier).toContainText(`Avec ${NB_FUSIONS} fusions apprises, ses 10 000 caractères`);
  expect(erreurs).toEqual([]);
});

test('accessibilité, largeur et mesure : atelier ouvert, à 0 et à 60 fusions, morceaux cachés', async ({ page }) => {
  await ouvrirAtelier(page);
  await saisie(page).fill('Une phrase un peu plus longue que les autres, pour voir la bande passer à la ligne sans déborder.');
  await reglerAuClavier(page, 0);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await reglerAuClavier(page, 60);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
  await page.getByRole('button', { name: 'cacher les morceaux' }).click();
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('le mouvement suit le lecteur : rien sans action, rien si on le demande', async ({ browser }) => {
  for (const reducedMotion of ['no-preference', 'reduce'] as const) {
    const ctx = await browser.newContext({ reducedMotion });
    const page = await ctx.newPage();
    await ouvrirAtelier(page);
    // Au chargement, aucun jeton n'est animé.
    await expect(page.locator('[data-test="jetons"] .nouveau')).toHaveCount(0);
    await nombre(page).focus();
    await page.keyboard.press('End');
    const nouveaux = page.locator('[data-test="jetons"] .nouveau .morceau');
    await expect(nouveaux.first()).toBeAttached();
    const animation = await nouveaux.first().evaluate((e) => getComputedStyle(e).animationName);
    if (reducedMotion === 'reduce') expect(animation).toBe('none');
    else expect(animation).not.toBe('none');
    await ctx.close();
  }
});

test('sans JavaScript : l’atelier reste lisible, découpé au départ', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(saisie(page)).toHaveValue(PHRASE_INITIALE);
  // Rendu au départ, à 20 fusions : entre les 18 jetons de 165 fusions et les 42 de 0 fusion.
  const n = await jetons(page).count();
  expect(n).toBeGreaterThan(18);
  expect(n).toBeLessThan(42);
  await expect(jetons(page).first()).toBeVisible();
  await expect(nombre(page)).toHaveText('20');
  await expect(page.locator('[data-atelier]')).toContainText(`ses 42 caractères tiennent en ${n} jetons`);
  await ctx.close();
});

test('phrase découpée d’ouverture : calculée à la construction, fidèle au Python', async ({ browser, baseURL }) => {
  // Sans JavaScript : la preuve que le découpage est fait à la construction.
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  const { morceaux, numeros } = reference(PHRASE_INITIALE, NB_FUSIONS);
  const figure = page.locator('figure.phrase-decoupee');
  await expect(figure.locator('[data-jeton] .morceau')).toHaveText(morceaux);
  await expect(figure.locator('[data-jeton] .num')).toHaveText(numeros);
  const legende = (await figure.locator('figcaption').textContent()) ?? '';
  expect(legende).toBe(
    `«${FINE}Le forgeron frappe le métal sur l’enclume.${FINE}», tel que le modèle le reçoit${FINE}: ` +
      `${morceaux.length} morceaux, donc ${morceaux.length} nombres.`,
  );
  await ctx.close();
});
