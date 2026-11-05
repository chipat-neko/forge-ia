// Parcours du gabarit de chapitre, sur la page d'essai /forge-ia/essais/gabarit/
// (construite seulement avec FORGE_ESSAIS=1, voir src/essais/gabarit.mdx).
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { contraste, plusLongueLigne, verifierAxe, verifierSansDebordement } from './outils';

const PAGE = '/forge-ia/essais/gabarit/';
const CLE_PROGRESSION = 'forge-ia:progression:v1';

type FenetreMarquee = Window & { marque?: boolean };

// Une marque posée sur window disparaît quand la page est vraiment rechargée
// (nouveau document), et survit à un simple changement d'ancre.
async function marquer(page: Page): Promise<void> {
  await page.evaluate(() => {
    (window as FenetreMarquee).marque = true;
  });
}

async function estNouveauDocument(page: Page): Promise<boolean> {
  return page.evaluate(() => (window as FenetreMarquee).marque === undefined);
}

// Laisse passer les premières notifications des IntersectionObserver (elles
// arrivent après le script, au rendu suivant) avant de vérifier une absence.
async function laisserLaPageSeStabiliser(page: Page): Promise<void> {
  await page.evaluate(
    () =>
      new Promise<void>((fini) =>
        requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(fini, 150))),
      ),
  );
}

async function jouerLesDeuxParis(page: Page): Promise<void> {
  await page.locator('[data-pari="p1"] [data-juste]').click();
  await page.locator('[data-pari="p2"] [data-juste]').click();
}

// Après les deux paris : tout est restauré, verrou ouvert, étape 1 faite.
async function verifierRestauration(page: Page): Promise<void> {
  await expect(page.locator('[data-pari="p1"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-pari="p2"] .verdict')).toContainText('Juste.');
  await expect(page.locator('[data-pari="p1"] [data-juste]')).toBeDisabled();
  const zone = page.locator('[data-verrou="zone"]');
  await expect(zone).not.toHaveAttribute('inert', '');
  await expect(zone).not.toHaveClass(/\bverrouille\b/);
  await expect(page.locator('.verrou-msg')).toHaveCount(0);
  const liens = page.locator('header nav a');
  await expect(liens).toHaveCount(2);
  await expect(liens.first()).toHaveClass(/\bfaite\b/);
  await expect(liens.first()).toHaveAttribute('aria-label', /, faite$/);
  await expect(liens.first()).not.toHaveAttribute('aria-current', 'step');
  await expect(liens.nth(1)).toHaveAttribute('aria-current', 'step');
  await expect(page.locator('#etape-1')).toHaveClass(/\bfaite\b/);
  await expect(page.locator('#recap')).toContainText('2 sur 3');
}

// Les tests du brief de la tâche 5. Ceux du lien direct et d'« Effacer » ont
// été renforcés à la relecture : le premier ne rechargeait pas vraiment la
// page, le second ne vérifiait pas que la progression était vide.

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

test('lien direct vers #etape-2 : pari, verrou et barre restaurés', async ({ page }) => {
  await page.goto(PAGE);
  await jouerLesDeuxParis(page);
  // Passer par about:blank : sinon aller à #etape-2 depuis la même adresse
  // n'est qu'un changement d'ancre, sans nouveau document.
  await page.goto('about:blank');
  const reponse = await page.goto(PAGE + '#etape-2');
  expect(reponse, 'une vraie navigation renvoie une réponse').not.toBeNull();
  await verifierRestauration(page);
});

test('rechargement : pari, verrou et barre restaurés', async ({ page }) => {
  await page.goto(PAGE);
  await jouerLesDeuxParis(page);
  await marquer(page);
  await page.reload();
  expect(await estNouveauDocument(page)).toBe(true);
  await verifierRestauration(page);
});

test('effacer la progression : rien ne reste, même en effaçant depuis le bas de la page', async ({ page }) => {
  await page.goto(PAGE);
  await jouerLesDeuxParis(page);
  // En bas de page, la fin de l'étape 2 (sans pari) est passée au-dessus du milieu.
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect(page.locator('#etape-2')).toHaveClass(/\bfaite\b/);
  const bouton = page.getByRole('button', { name: 'Effacer ma progression pour ce chapitre' });
  await bouton.scrollIntoViewIfNeeded();
  await marquer(page);
  await Promise.all([page.waitForEvent('load'), bouton.click()]);
  expect(await estNouveauDocument(page)).toBe(true);
  await laisserLaPageSeStabiliser(page);
  await expect(page.locator('[data-pari="p1"] [data-juste]')).toBeEnabled();
  await expect(page.locator('[data-verrou="zone"]')).toHaveAttribute('inert', '');
  await expect(page.locator('#recap')).toContainText('0 sur 3');
  await expect(page.locator('section.etape.faite')).toHaveCount(0);
  await expect(page.locator('header nav a.faite')).toHaveCount(0);
  const brut = await page.evaluate((cle) => localStorage.getItem(cle), CLE_PROGRESSION);
  expect(brut === null ? {} : JSON.parse(brut)).not.toHaveProperty(['1.3']);
});

test('sans JavaScript : tout est lisible, rien de verrouillé', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
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

// axe ne compte pas un contraste de 1 pour 1 comme une faute (il le laisse
// « à revoir ») : le rapport se vérifie donc aussi à part.
test('encadré labo : le code en ligne se lit sur le fond indigo', async ({ page }) => {
  await page.goto(PAGE);
  const code = page.locator('.labo p code');
  await expect(code).toHaveText('paire_la_plus_frequente');
  const { texte, fond } = await code.evaluate((el) => {
    const style = getComputedStyle(el);
    return { texte: style.color, fond: style.backgroundColor };
  });
  expect(contraste(texte, fond)).toBeGreaterThanOrEqual(4.5);
  await verifierAxe(page);
});

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

test('typographie : apostrophes courbes partout, guillemets droits jamais anglais', async ({ page }) => {
  await page.goto('/forge-ia/essais/gabarit/');
  // Prose MDX : \u00AB qu'une \u00BB est \u00E9crit avec une apostrophe droite dans la source.
  const etape1 = (await page.locator('#etape-1').textContent()) ?? '';
  expect(etape1).toContain('qu\u2019une r\u00E9ponse');
  expect(etape1).not.toContain("qu'une");
  // Prop d'un composant : la question du pari p1 contient \u00AB l'\u00E9tape \u00BB.
  const question = (await page.locator('[data-pari="p1"] .q').textContent()) ?? '';
  expect(question).toContain('l\u2019\u00E9tape');
  expect(question).not.toContain("'");
  // Les guillemets droits doubles de la prose restent droits.
  const etape2 = (await page.locator('#etape-2').textContent()) ?? '';
  expect(etape2).toContain('"comme ceux-ci"');
  expect(etape2).not.toMatch(/[\u201C\u201D]/);
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

test('sans JavaScript : la réponse et l’explication des paris sont lisibles', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
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
  // La zone ouverte par p1 sort de son flou en 0,35 s : axe mesurerait le
  // contraste de l'atelier à mi-fondu (opacité 0,45), et non tel qu'on le lit.
  await expect(page.locator('[data-verrou="zone"]')).toHaveCSS('opacity', '1');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

// Les sorties de commande (SortieCommande.astro) : le contenu réel d'un fichier
// du dépôt, ou « à mesurer » quand il manque.
const SORTIE = 'projets/1.3-tokenizer/donnees/corpus.txt';

test('sortie de commande : le contenu du fichier, sans retour chariot, qui passe à la ligne', async ({ page }) => {
  await page.goto(PAGE);
  // Playwright tourne dans site/ : le dépôt est un dossier plus haut.
  const attendu = readFileSync(`../${SORTIE}`, 'utf8').replace(/\r/g, '').replace(/\n+$/, '');
  const sortie = page.locator(`[data-sortie="${SORTIE}"]`);
  await expect(sortie).toHaveCount(1);
  await expect(sortie.locator('.invite')).toHaveText('PS>');
  await expect(sortie.locator('.commande')).toHaveText(`Get-Content ${SORTIE}`);
  const contenu = await sortie.locator('[data-contenu]').evaluate((el) => el.textContent);
  expect(contenu).toBe(attendu);
  expect(contenu).not.toContain('\r');
  // Les lignes passent à la ligne (point mis de côté à la tâche 15) : la zone ne défile pas, et ne prend donc
  // pas le focus.
  const zone = sortie.locator('.zone-sortie');
  await expect(zone).toHaveCount(1);
  await expect(sortie.locator('.zone-defilable')).toHaveCount(0);
  await expect(zone).not.toHaveAttribute('tabindex', /.*/);
  await expect(zone.locator('pre')).toHaveCSS('white-space', 'pre-wrap');
  const { large, visible } = await zone.evaluate((z) => ({ large: z.scrollWidth, visible: z.clientWidth }));
  expect(large).toBeLessThanOrEqual(visible);
  // Sans ligne « # relevé le », la légende n'a pas de date.
  await expect(sortie.locator('figcaption')).not.toContainText('relevée le');
  await expect(sortie.locator('[data-a-mesurer]')).toHaveCount(0);
});

test('sortie de commande absente : son texte « à mesurer », marqué data-a-mesurer', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('[data-sortie="projets/inexistant/sortie.txt"]')).toHaveCount(0);
  const absente = page.locator('[data-a-mesurer]');
  await expect(absente).toHaveCount(1);
  expect(await absente.evaluate((el) => el.tagName)).toBe('P');
  // textContent : la typographie (espace fine avant « : », apostrophe courbe) compte.
  expect(await absente.textContent()).toBe('À mesurer\u202F: cette commande n\u2019a pas encore été lancée ici.');
  await expect(absente).toHaveCSS('font-style', 'italic');
});
