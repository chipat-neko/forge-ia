// Parcours des pages hors chapitre : l'accueil (pari d'ouverture et plan du
// parcours), les pages de partie, la recherche (Pagefind) et la page 404.
import { test, expect } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { ANNEXES, PARCOURS } from '../src/lib/parcours';
import { typographier } from '../src/lib/typo';
import { terminerChapitre13, verifierAxe, verifierSansDebordement } from './outils';

const CLE_PROGRESSION = 'forge-ia:progression:v1';
const FINE = '\u202F';

// Les cinq tests du brief de la tâche 12, chacun terminé par axe et le
// contrôle du débordement.

test('accueil : 34 chapitres, 1.3 disponible', async ({ page }) => {
  await page.goto('/forge-ia/');
  await expect(page.locator('[data-chapitre-carte]')).toHaveCount(34);
  // Le compte annoncé en tête du plan vient du parcours, pas d'un texte écrit à la main.
  const total = PARCOURS.reduce((n, p) => n + p.chapitres.length, 0);
  await expect(page.locator('.parcours-tete p').first()).toContainText(`Quatre parties, ${total} chapitres.`);
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'disponible');
  // Le premier chapitre de la Partie 1 sans fichier parmi les chapitres parus est « à venir »
  // (un brouillon n'est pas paru). Calculé, pour tenir à chaque parution. Playwright tourne dans site/.
  const premierAVenir = PARCOURS.find((p) => p.numero === 1)!.chapitres.find(
    (c) => !existsSync(`src/content/chapitres/${c.numero.replace('.', '-')}.mdx`),
  )!;
  await expect(page.locator(`[data-chapitre-carte="${premierAVenir.numero}"]`)).toHaveAttribute('data-etat', 'a-venir');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await page.locator('[data-chapitre-carte="1.3"] a').click();
  // Attendre la page chargée (waitForURL attend « load »), pas seulement la nouvelle
  // adresse : sinon axe et le contrôle du débordement lisent un document à moitié
  // analysé, sans ses CSS, que le navigateur ne peint jamais.
  await page.waitForURL(/\/forge-ia\/partie-1\/1-3\/$/);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('accueil : les annexes construites sont des liens, « Matériel » reste à venir', async ({ page }) => {
  await page.goto('/forge-ia/');
  const annexes = page.locator('#annexes li');
  await expect(annexes).toHaveCount(ANNEXES.length);
  for (const [i, annexe] of ANNEXES.entries()) {
    const carte = annexes.nth(i);
    if (annexe.href === undefined) {
      await expect(carte.getByRole('link')).toHaveCount(0);
      await expect(carte).toContainText('à venir');
    } else {
      await expect(carte.getByRole('link', { name: typographier(annexe.titre) })).toHaveAttribute('href', annexe.href);
      await expect(carte).not.toContainText('à venir');
    }
  }
  expect(ANNEXES.filter((a) => a.href === undefined).map((a) => a.titre)).toEqual(['Matériel']);
});

test('page de partie', async ({ page }) => {
  await page.goto('/forge-ia/partie-1/');
  await expect(page.locator('[data-chapitre-carte]')).toHaveCount(21);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Créer son IA de zéro');
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'disponible');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('recherche', async ({ page }) => {
  await page.goto('/forge-ia/recherche/');
  await page.getByRole('searchbox').fill('fusions');
  await expect(page.locator('[data-resultat]').first()).toContainText('tokenizer');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('404', async ({ page }) => {
  const r = await page.goto('/forge-ia/nimporte-quoi/');
  expect(r?.status()).toBe(404);
  await expect(page.getByRole('link', { name: /accueil/i })).toBeVisible();
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('progression visible sur l’accueil', async ({ page }) => {
  await terminerChapitre13(page);
  await page.goto('/forge-ia/');
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'fait');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

// Parcours ajoutés : les maquettes validées en demandent davantage.

test('accueil : le pari d’ouverture se joue une fois et reste répondu au rechargement', async ({ page }) => {
  await page.goto('/forge-ia/');
  const pari = page.locator('[data-pari="phrase"]');
  // Les choix sont calculés par le moteur du chapitre 1.3 (mots, jetons, caractères).
  await expect(pari.locator('button[data-choix]')).toHaveText([/^5\s*jetons/, /^17\s*jetons/, /^25\s*jetons/]);
  await expect(pari.locator('.verdict')).toBeHidden();
  await pari.locator('[data-juste]').click();
  await expect(pari.locator('.verdict')).toContainText('Juste.');
  await expect(pari.locator('[data-juste]')).toContainText('ton choix, juste');
  await expect(page.locator('[data-phrase]')).toHaveClass(/\bdecoupee\b/);
  // Le bouton jaune ne garde que les nombres, puis remontre les morceaux.
  const bascule = page.getByRole('button', { name: 'Ne garder que les nombres' });
  await bascule.click();
  await expect(page.locator('[data-phrase]')).toHaveClass(/\bnumeros\b/);
  // Le nom du bouton dit ce qu'il fera : pas d'aria-pressed en plus (il se contredirait).
  await expect(page.getByRole('button', { name: 'Remontrer les morceaux' })).toBeVisible();
  await page.reload();
  await expect(pari.locator('.verdict')).toBeVisible();
  await expect(pari.locator('.verdict')).toContainText('Juste.');
  await expect(pari.locator('[data-juste]')).toBeDisabled();
  await expect(page.locator('[data-phrase]')).toHaveClass(/\bdecoupee\b/);
  const garde = await page.evaluate((cle) => localStorage.getItem(cle), CLE_PROGRESSION);
  expect(JSON.parse(garde ?? '{}')).toMatchObject({ accueil: { paris: { phrase: 1 } } });
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('accueil : le bouton de lecture suit la progression du chapitre 1.3', async ({ page }) => {
  await page.goto('/forge-ia/');
  const bouton = page.locator('[data-suite] a');
  // Sans progression, le bouton ouvre le premier chapitre paru du parcours : 0.1 depuis sa parution.
  await expect(bouton).toHaveText(/Ouvrir le chapitre 0\.1/);
  await page.goto('/forge-ia/partie-1/1-3/');
  await page.locator('[data-pari="nombres"] [data-juste]').click();
  await page.goto('/forge-ia/');
  await expect(bouton).toHaveText(/Reprendre le chapitre 1\.3/);
  await expect(page.locator('[data-suite]')).toContainText('1 sur 5');
  // « Commencé » garde l'état disponible, avec les acquis dans les infos.
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'disponible');
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toContainText('1 acquis sur 5');
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('progression visible sur la page de partie, puis effacée depuis le pied de page', async ({ page }) => {
  await terminerChapitre13(page);
  await page.goto('/forge-ia/partie-1/');
  const carte = page.locator('[data-chapitre-carte="1.3"]');
  await expect(carte).toHaveAttribute('data-etat', 'fait');
  await expect(page.locator('header')).toContainText('1 fait sur 21');
  await expect(page.locator('[data-savoir="1.3"]')).toHaveClass(/\bacquis\b/);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await page.getByRole('button', { name: 'Effacer ma progression' }).click();
  await expect(carte).toHaveAttribute('data-etat', 'disponible');
  expect(await page.evaluate((cle) => localStorage.getItem(cle), CLE_PROGRESSION)).toBeNull();
  await page.goto('/forge-ia/');
  await expect(page.locator('[data-chapitre-carte="1.3"]')).toHaveAttribute('data-etat', 'disponible');
});

test('les quatre pages de partie', async ({ page }) => {
  const attendus: [string, number, string][] = [
    ['/forge-ia/partie-0/', 5, 'Les bases'],
    ['/forge-ia/partie-1/', 21, 'Créer son IA de zéro'],
    ['/forge-ia/partie-2/', 4, 'Hybride'],
    ['/forge-ia/partie-3/', 4, 'Assemblage'],
  ];
  for (const [adresse, nombre, titre] of attendus) {
    await page.goto(adresse);
    await expect(page.locator('[data-chapitre-carte]')).toHaveCount(nombre);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(titre);
    await verifierAxe(page);
    await verifierSansDebordement(page);
  }
  // L'accueil mène aux pages de partie.
  await page.goto('/forge-ia/');
  await page.getByRole('link', { name: /Hybride/ }).click();
  await expect(page).toHaveURL(/\/forge-ia\/partie-2\/$/);
});

test('recherche : les titres du parcours, un numéro, et rien de la page d’essai', async ({ page }) => {
  await page.goto('/forge-ia/recherche/');
  const champ = page.getByRole('searchbox');
  await champ.fill('images');
  // Le sommaire trouve les titres à venir qui en parlent ; le texte de 0.3 dit « image »
  // (même racine pour Pagefind), mais ce compte ne porte que sur les titres du sommaire.
  // Pendant un entraînement, le disque D: est occupé et astro preview sert Pagefind en plus
  // d'une seconde (mesuré le 06/11/2026) ; ce test vérifie les résultats, pas la vitesse.
  await expect(page.locator('.sommaire-trouve [data-resultat]')).toHaveCount(6, { timeout: 15_000 });
  await champ.fill('1.3');
  await expect(page.locator('[data-resultat]').first()).toContainText('Le tokenizer');
  // La page d'essai du gabarit (construite pour les tests) n'est jamais cherchée :
  // « gabarit » n'est que dans son texte à elle.
  await champ.fill('gabarit');
  await expect(page.getByRole('heading', { level: 2, name: /Rien sur «\s?gabarit\s?»/ })).toBeVisible();
  await expect(page.locator('[data-resultat]')).toHaveCount(0);
  await champ.fill('Parier avant de voir');
  await expect(page.locator('[role="status"]')).toContainText('avant');
  await expect(page.locator('main a[href*="/essais/"]')).toHaveCount(0);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('recherche : « jeux » et « mots » trouvent « jeu » et « mot », comme Pagefind', async ({ page }) => {
  await page.goto('/forge-ia/recherche/?q=jeux');
  // Depuis la parution de 1.2 (« jeux de données »), « jeux » est dans l'index :
  // Pagefind ne le cherche plus en morceaux, et le « jeu de société » de 1.3
  // n'en sort plus. Les mots surlignés commencent toujours par « jeu ». Le
  // pluriel ramené au singulier reste vérifié par « mots » ci-dessous.
  await expect(page.locator('[data-resultat]')).not.toHaveCount(0);
  await expect(page.locator('[data-resultat] mark').first()).toHaveText(/^jeu/);
  await page.getByRole('searchbox').fill('mots');
  await expect(page.locator('[role="status"]')).toContainText('mots');
  await expect(page.locator('[data-resultat] .passages li')).not.toHaveCount(0);
  await expect(page.locator('[data-resultat] mark', { hasText: /^mot$/ }).first()).toBeVisible();
});

test('recherche : la requête de l’adresse est cherchée d’emblée', async ({ page }) => {
  await page.goto('/forge-ia/recherche/?q=jetons');
  await expect(page.getByRole('searchbox')).toHaveValue('jetons');
  // Depuis la parution de 1.4, plusieurs chapitres parlent surtout de jetons : l'ordre des
  // résultats n'est plus celui d'un seul chapitre. 1.3 (le tokenizer) doit en être.
  await expect(page.locator('[data-resultat]', { hasText: 'tokenizer' }).first()).toBeVisible();
  await expect(page.locator('[data-resultat] a[href*="#etape-"]').first()).toBeVisible();
});

test('404 : un chapitre à venir est reconnu, et le pari se joue', async ({ page }) => {
  // Le premier chapitre de la Partie 1 qui n'est ni paru ni en brouillon : un brouillon est
  // construit à son adresse pour les parcours (FORGE_ESSAIS=1), il n'y donne donc pas de 404.
  // Playwright tourne dans site/.
  const aVenir = PARCOURS.find((p) => p.numero === 1)!.chapitres.find((c) => {
    const fichier = `${c.numero.replace('.', '-')}.mdx`;
    return !existsSync(`src/content/chapitres/${fichier}`) && !existsSync(`src/brouillons/chapitres/${fichier}`);
  });
  expect(aVenir, 'aucun chapitre de la Partie 1 n’est à venir').toBeDefined();
  const r = await page.goto(`/forge-ia/partie-1/${aVenir!.numero.replace('.', '-')}/`);
  expect(r?.status()).toBe(404);
  await expect(page.locator('main')).toContainText(typographier(`${aVenir!.numero}, ${aVenir!.titre}`));
  await expect(page.locator('main')).toContainText('pas encore paru');
  const pari = page.locator('[data-pari="introuvable"]');
  await expect(pari.locator('button[data-choix]')).toHaveText([/^1\s*jeton/, /^8\s*jetons/, /^11\s*jetons/]);
  await pari.locator('button:not([data-juste])').first().click();
  await expect(pari.locator('.verdict')).toContainText('Pas tout à fait.');
  const g = (mot: string) => `«${FINE}${mot}${FINE}»`;
  await expect(pari.locator('.verdict')).toContainText(`${g('ou')}, ${g('ab')} et ${g('le')}`);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

// GitHub Pages sert 404.html pour toute adresse inconnue, même mal encodée
// (vieux lien en Latin-1, « % » isolé). astro preview répond 500 à ces
// adresses : on sert donc 404.html nous-mêmes, comme le ferait GitHub Pages.
test('404 : une adresse mal encodée ne casse ni l’adresse affichée ni le pari', async ({ page }) => {
  const page404 = readFileSync('dist/404.html', 'utf8');
  const erreurs: string[] = [];
  page.on('pageerror', (erreur) => erreurs.push(erreur.message));
  for (const abimee of ['/forge-ia/caf%E9/', '/forge-ia/100%zz/']) {
    await page.route(
      (url) => url.pathname === abimee,
      (route) => route.fulfill({ status: 404, contentType: 'text/html; charset=utf-8', body: page404 }),
    );
    const r = await page.goto(abimee);
    expect(r?.status()).toBe(404);
    await expect(page.locator('[data-adresse]')).toBeVisible();
    await expect(page.locator('[data-adresse]')).toHaveText(abimee);
    const pari = page.locator('[data-pari="introuvable"]');
    await pari.locator('[data-juste]').click();
    await expect(pari.locator('.verdict')).toBeVisible();
    await expect(pari.locator('.verdict')).toContainText('Juste.');
  }
  expect(erreurs).toEqual([]);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('accueil : les phrases d’embranchement restent lues par les lecteurs d’écran', async ({ page }, info) => {
  await page.goto('/forge-ia/');
  if (info.project.name === 'ordinateur') {
    // Sur grand écran, le script place les embranchements à droite du plan :
    // la phrase « Elle part de… » n'a plus à se voir, mais doit rester lue.
    await expect(page.locator('[data-carte]')).toHaveClass(/\bplacee\b/);
  }
  const depuis = page.locator('.depuis');
  await expect(depuis).toHaveCount(2);
  for (const phrase of await depuis.all()) {
    await expect(phrase).not.toHaveCSS('display', 'none');
    if (info.project.name === 'ordinateur') expect((await phrase.boundingBox())?.width).toBeLessThanOrEqual(1);
  }
  const arbre = await page.locator('[data-carte]').ariaSnapshot();
  expect(arbre).toContain('Elle part de la Partie 1 après 1.7,');
  expect(arbre).toContain('Elle part de la Partie 1 après 1.16,');
  await verifierSansDebordement(page);
});

test('favicon : une icône SVG sous la base du site, et aucune requête en 404', async ({ page, request }) => {
  const manquantes: string[] = [];
  page.on('response', (reponse) => {
    if (reponse.status() === 404) manquantes.push(reponse.url());
  });
  for (const adresse of ['/forge-ia/', '/forge-ia/partie-1/', '/forge-ia/partie-1/1-3/', '/forge-ia/recherche/']) {
    await page.goto(adresse);
    await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', '/forge-ia/favicon.svg');
  }
  const icone = await request.get('/forge-ia/favicon.svg');
  expect(icone.status()).toBe(200);
  expect(icone.headers()['content-type']).toContain('image/svg+xml');
  expect(manquantes).toEqual([]);
});
