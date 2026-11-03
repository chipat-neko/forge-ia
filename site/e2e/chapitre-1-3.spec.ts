// Parcours du chapitre 1.3, « Le tokenizer » (src/content/chapitres/1-3.mdx) :
// le premier vrai chapitre, qui assemble tout le gabarit (paris, verrou,
// atelier, code expliqué, encadré labo, récapitulatif).
import { readFileSync } from 'node:fs';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { extraireRegion } from '../src/lib/regions';
import { plusLongueLigne, terminerChapitre13, verifierAxe, verifierSansDebordement } from './outils';

const PAGE = '/forge-ia/partie-1/1-3/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const FICHIER = 'projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py';
const SOURCE = readFileSync(`../${FICHIER}`, 'utf8');
const CORPUS = readFileSync('../projets/1.3-tokenizer/donnees/corpus.txt', 'utf8');
// Les caractères de base du tokenizer : ceux du corpus, sans doublon.
const TAILLE_BASE = new Set(CORPUS).size;
// Les fusions apprises, calculées par le Python.
const attendus = JSON.parse(readFileSync('../projets/1.3-tokenizer/tests/attendus.json', 'utf8')) as {
  fusions: [string, string, number][];
};
const NB_FUSIONS = attendus.fusions.length;

/** Une fusion telle que l'atelier la liste : « fusion 30 : é + c → éc ». */
function ligneFusion(n: number): string {
  const visible = (s: string) => s.replace(/ /g, '␣').replace(/\n/g, '↵');
  const [a, b] = attendus.fusions[n - 1];
  return `fusion ${n}${FINE}: ${visible(a)} + ${visible(b)} → ${visible(a + b)}`;
}

/**
 * Le texte qui se voit à l'écran dans un élément : sans ce qui est caché ni
 * ce qui est réservé aux lecteurs d'écran (une boîte d'un pixel).
 */
async function texteAffiche(element: Locator): Promise<string> {
  return element.evaluate((racine) => {
    let texte = '';
    const marcheur = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT);
    for (let n = marcheur.nextNode(); n; n = marcheur.nextNode()) {
      const boite = n.parentElement?.getBoundingClientRect();
      if (!boite || boite.width <= 1 || boite.height <= 1) continue;
      texte += n.textContent ?? '';
    }
    return texte.replace(/\s+/g, ' ').trim();
  });
}

// Les îlots Svelte (atelier, marge, labo) répondent au clavier une fois
// hydratés : Astro retire alors l'attribut ssr.
async function attendreHydratation(page: Page): Promise<void> {
  await expect(page.locator('astro-island[ssr]')).toHaveCount(0);
}

/** Ouvre la page et fait le pari de l'étape 3, qui ouvre l'atelier. */
async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="prediction"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
}

// Le test du brief de la tâche 9, avec deux retouches :
// - attendre l'hydratation des îlots avant de jouer, pour que les flèches
//   atteignent bien l'atelier ;
// - Playwright ramène toutes les espaces du nom accessible (U+202F comprise)
//   à une espace ordinaire : le titre se cherche avec \s, et l'espace fine se
//   vérifie à part, sur le texte du titre.
test('chapitre 1.3 complet', async ({ page }, info) => {
  await page.goto('/forge-ia/partie-1/1-3/');
  await attendreHydratation(page);
  await expect(page.locator('header')).toContainText('Partie 1, chapitre 1.3 sur 21');
  // La position se voit aussi sur téléphone, en forme courte (le texte
  // complet reste lu par les lecteurs d'écran) : toContainText ne suffit pas,
  // il lit aussi le texte caché.
  const position = page.locator('header .ou');
  await expect(position).toBeVisible();
  expect(await texteAffiche(position)).toBe(
    info.project.name === 'mobile' ? '1.3 sur 21' : 'Partie 1, chapitre 1.3 sur 21',
  );
  const titre = page.getByRole('heading', { level: 2, name: /Pourquoi découper\s\?/ });
  await expect(titre).toBeVisible();
  expect(await titre.textContent()).toBe('Pourquoi découper\u202F?');
  await expect(page.locator('[data-pari="prediction"] button')).toHaveText([/2 jetons/, /9 jetons/, /13 jetons/]);
  await page.locator('[data-pari="nombres"] [data-juste]').click();
  await page.locator('[data-pari="prediction"] [data-juste]').click();
  await page.locator('[data-test="fusions"]').focus();
  for (let i = 0; i < 60; i++) await page.keyboard.press('ArrowRight');
  await page.locator('[data-pari="rare"] [data-juste]').click();
  await page.locator('[data-pari="zip"] [data-juste]').click();
  await expect(page.locator('#recap')).toContainText('5 sur 5');
  await expect(page.locator('footer')).toContainText('à venir'); // 1.2 et 1.4 pas encore écrits
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('les réponses des paris viennent du tokenizer : 9 jetons, et « reforgeronnes » en 6 morceaux', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  // Le pari de l'étape 3 : la bonne réponse est le découpage de la démo.
  await expect(page.locator('[data-pari="prediction"] [data-juste]')).toHaveText(/9 jetons/);
  await page.locator('[data-pari="prediction"] button').first().click(); // un pari perdu
  const prediction = page.locator('[data-pari="prediction"] .verdict');
  await expect(prediction).toContainText('Pas tout à fait.');
  await expect(prediction.locator('[data-jeton]')).toHaveText(['l', 'es', '␣f', 'o', 'r', 'g', 'er', 'on', 's']);
  // Le mot rare : « Non » est juste, car il reste en 6 morceaux.
  await expect(page.locator('[data-pari="rare"] [data-juste]')).toHaveText(/^Non/);
  await page.locator('[data-pari="rare"] [data-juste]').click();
  const rare = page.locator('[data-pari="rare"] .verdict');
  await expect(rare).toContainText('Juste.');
  await expect(rare.locator('[data-jeton]')).toHaveText(['re', 'f', 'org', 'er', 'onn', 'es']);
});

test('le défi se vérifie en direct, avec toutes les fusions', async ({ page }) => {
  await ouvrirAtelier(page);
  const saisie = page.locator('[data-test="saisie"]');
  const defi = page.locator('[data-defi]');
  const etat = page.locator('[data-test="defi"]');
  // textContent : toHaveText ramènerait U+202F à une espace ordinaire.
  const texteEtat = async () => (await etat.textContent()) ?? '';
  // La phrase de départ de l'atelier ne réussit pas le défi.
  await expect(etat).toContainText(`Avec les ${NB_FUSIONS} fusions, ta phrase tient en 18 jetons, soit 6 de trop.`);
  await saisie.fill('Le modèle apprend les jetons.'); // 29 caractères
  await expect(etat).toContainText('Ta phrase fait 29 caractères');
  expect(await texteEtat()).toBe(`Ta phrase fait 29 caractères${FINE}: il en faut au moins 30.`);
  await saisie.fill('Les forgerons forgent des outils.'); // 33 caractères, mais 13 jetons
  await expect(etat).toContainText('ta phrase tient en 13 jetons, soit 1 de trop.');
  await expect(defi).not.toHaveClass(/\breussi\b/);
  await saisie.fill('Les enfants apprennent à lire.'); // 30 caractères, 11 jetons
  await expect(defi).toHaveClass(/\breussi\b/);
  expect(await texteEtat()).toBe(`Défi réussi${FINE}: 30 caractères en 11 jetons.`);
  // Le texte de l'atelier ne promet pas plus que ce tokenizer ne sait faire :
  // un caractère absent du corpus reste « inconnu ».
  await expect(page.locator('[data-atelier]')).toContainText('n’importe quel mot fait de caractères déjà vus');
  // Les 11 jetons sont ceux de la bande avec toutes les fusions…
  const nombre = page.locator('[data-test="fusions"]');
  await nombre.focus();
  await page.keyboard.press('End');
  await expect(page.locator('[data-test="jetons"] [data-jeton]')).toHaveCount(11);
  // … et le défi ne dépend pas du nombre jaune.
  await page.keyboard.press('Home');
  await expect(nombre).toHaveAttribute('aria-valuenow', '0');
  await expect(defi).toHaveClass(/\breussi\b/);
  // La réussite est annoncée aux lecteurs d'écran.
  await expect(defi.locator('[aria-live]')).toContainText('Défi réussi');
  await verifierAxe(page);
});

test('le code : régions « compter » et « choisir », tirées du fichier testé et lisibles seules', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = page.locator('.code-explique pre');
  await expect(blocs).toHaveCount(2);
  for (const [i, region] of ['compter', 'choisir'].entries()) {
    const attendu = extraireRegion(SOURCE, region, FICHIER);
    expect(await blocs.nth(i).evaluate((pre) => pre.textContent)).toBe(attendu);
    // L'extrait se lit seul : aucun alias de type défini ailleurs dans le fichier.
    expect(attendu).not.toMatch(/\b(Mot|Paire)\b/);
  }
  // L'explication du départage dit la règle du code (l'ordre des points de
  // code, où « é » vient après « z »), pas l'ordre alphabétique, et allume
  // la ligne du min().
  const choisir = page.locator('.code-explique').nth(1);
  const departage = choisir.locator('.explications li', { hasText: 'En cas d’égalité' });
  await expect(departage).toContainText('dans l’ordre des numéros des caractères');
  await expect(departage).toContainText('sauf que « é » passe après « z »');
  await departage.hover();
  const allumees = await choisir.locator('[data-l].allumee').allTextContents();
  expect(allumees.join('\n')).toContain('return min(compte, key=lambda paire: (-compte[paire], paire))');
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.3-tokenizer',
  );
});

test('marge et labo : les autres vues du nombre de fusions le suivent', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  // Un seul nombre porte data-test="fusions" : celui de l'atelier.
  await expect(page.locator('[data-test="fusions"]')).toHaveCount(1);
  const labo = page.locator('.labo');
  const nombreLabo = labo.getByRole('slider');
  // Deux curseurs, deux noms : le lecteur d'écran sait lequel il règle.
  await expect(nombreLabo).toHaveAccessibleName('Nombre de fusions apprises, échelle du labo');
  await expect(page.getByRole('slider', { name: 'Nombre de fusions apprises', exact: true })).toHaveCount(1);
  // Avant le pari, le nombre du labo est figé, comme celui de l'atelier.
  await expect(nombreLabo).toHaveAttribute('aria-disabled', 'true');
  await page.locator('[data-pari="prediction"] [data-juste]').click();
  await expect(nombreLabo).not.toHaveAttribute('aria-disabled', 'true');
  const marge = page.locator('#etape-4 .note [data-dernieres-fusions] li');
  await expect(marge).toHaveText([ligneFusion(20), ligneFusion(19), ligneFusion(18)]);
  await expect(labo).toContainText(`${TAILLE_BASE} caractères`);
  await expect(labo).toContainText(`soit ${TAILLE_BASE + 20} morceaux`);
  // L'atelier règle la marge et le labo…
  await page.locator('[data-test="fusions"]').focus();
  await page.keyboard.press('End');
  await expect(nombreLabo).toHaveText(String(NB_FUSIONS));
  await expect(labo).toContainText(`soit ${TAILLE_BASE + NB_FUSIONS} morceaux`);
  await expect(marge.first()).toHaveText(ligneFusion(NB_FUSIONS));
  // … et le labo règle l'atelier.
  await nombreLabo.focus();
  await page.keyboard.press('Home');
  await expect(page.locator('[data-test="fusions"]')).toHaveAttribute('aria-valuenow', '0');
  await expect(page.locator('#etape-4 .note [data-dernieres-fusions]')).toContainText('aucune pour l’instant');
  // Les chiffres du labo ne sont pas tous comptés de la même façon (jetons
  // spéciaux compris ou non) : celui de Llama 3 est donné en ordre de grandeur.
  await expect(labo).toContainText('environ 128 000 pour Llama 3');
  // Les sources du labo sont datées du jour de la vérification.
  expect(await labo.locator('.sources a').count()).toBeGreaterThanOrEqual(3);
  expect((await labo.locator('.sources').textContent()) ?? '').toContain('vérifiées le 2 novembre 2026');
});

test('lien d’évitement : Tab puis Entrée mène au contenu, après la barre du haut', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.keyboard.press('Tab');
  const lien = page.getByRole('link', { name: 'Aller au contenu' });
  await expect(lien).toBeFocused();
  await expect(lien).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#contenu$/);
  await expect(page.locator('main#contenu')).toHaveCount(1);
  // La touche Tab suivante part du contenu : la barre du haut est sautée.
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement?.closest('main')?.id)).toBe('contenu');
});

test('progression gardée : après rechargement, tout reste acquis et l’atelier ouvert', async ({ page }) => {
  await terminerChapitre13(page);
  await page.reload();
  await attendreHydratation(page);
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
  await expect(page.locator('[data-acquis-mini] .pips i.plein')).toHaveCount(5);
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="fusions"]')).toHaveAttribute('tabindex', '0');
  for (const id of ['nombres', 'prediction', 'rare', 'zip']) {
    await expect(page.locator(`[data-pari="${id}"] .verdict`)).toContainText('Juste.');
  }
});

test('avant tout pari : verrou posé, accessibilité, largeur et longueur des lignes', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(page.locator('[data-verrou="atelier"]')).toHaveAttribute('inert', '');
  await expect(page.locator('.verrou-msg')).toContainText('Fais ton pari à l’étape 3');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('après les paris : accessibilité, largeur et longueur des lignes', async ({ page }) => {
  await terminerChapitre13(page);
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('typographie française dans tout le texte (hors code)', async ({ page }) => {
  await terminerChapitre13(page);
  const textes = await page.locator('main').evaluate((main) => {
    // Le texte affiché, sans les scripts ni le code (où « a: b » et 'x' sont
    // du Python), ni les jetons (des morceaux de texte bruts).
    const morceaux: string[] = [];
    const marcheur = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
    for (let n = marcheur.nextNode(); n; n = marcheur.nextNode()) {
      if (n.parentElement?.closest('script, style, code, pre, [data-test="jetons"], .glose, [data-jeton]')) continue;
      morceaux.push(n.textContent ?? '');
    }
    return morceaux.join('');
  });
  expect(textes).toContain('Le tokenizer');
  // Une espace ordinaire (ou insécable) devant ; : ! ? ou à l'intérieur des guillemets.
  expect(textes.match(/.{0,30}[ \u00A0][;:!?].{0,10}/g) ?? []).toEqual([]);
  expect(textes.match(/.{0,10}«[ \u00A0].{0,30}|.{0,30}[ \u00A0]».{0,10}/g) ?? []).toEqual([]);
  // Apostrophes courbes, jamais droites entre deux lettres ; jamais de guillemets anglais.
  expect(textes.match(/.{0,20}\p{L}'\p{L}.{0,20}/gu) ?? []).toEqual([]);
  expect(textes).not.toMatch(/[\u201C\u201D]/);
});

test('sans JavaScript : tout le texte reste lisible', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  // Pas de verrou : l'atelier et son défi sont là, nets.
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="defi"]')).toBeVisible();
  // Les explications des paris sont données d'emblée.
  await expect(page.locator('[data-pari="rare"] .verdict')).toBeVisible();
  await expect(page.locator('[data-pari="prediction"] .verdict [data-jeton]')).toHaveCount(9);
  await expect(page.locator('.labo')).toContainText(`soit ${TAILLE_BASE + 20} morceaux`);
  await ctx.close();
});
