// Parcours des trois annexes construites : le glossaire, l'annuaire des données et le
// calculateur de coût (src/pages/annexes/). Les termes, les fiches et les adresses
// viennent des modules du site (glossaire.ts, annuaire.ts, parcours.ts), importés tels
// quels : aucune valeur n'est recopiée. Les chapitres parus sont ceux qui ont un fichier
// dans src/content/chapitres (Playwright tourne dans site/), comme chapitresParus().
import { readdirSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { ANNUAIRE } from '../src/lib/annexes/annuaire';
import { GLOSSAIRE } from '../src/lib/annexes/glossaire';
import { ANNEXES } from '../src/lib/parcours';
import { typographier } from '../src/lib/typo';
import { attendreHydratation, plusLongueLigne, verifierAxe, verifierSansDebordement, verifierTypographieHorsCode } from './outils';

const FINE = '\u202F';
const CONSTRUITES = ANNEXES.filter((a) => a.href !== undefined);
const GLOSSAIRE_HREF = CONSTRUITES[0].href!;
const ANNUAIRE_HREF = CONSTRUITES[1].href!;
const CALCULATEUR_HREF = CONSTRUITES[2].href!;
const PARUS = new Set(
  readdirSync('src/content/chapitres')
    .filter((f) => f.endsWith('.mdx'))
    .map((f) => f.replace(/\.mdx$/, '').replace('-', '.')),
);
const adresseDuChapitre = (numero: string) => `/forge-ia/partie-${numero.split('.')[0]}/${numero.replace('.', '-')}/`;

/**
 * La prose des pages d'annexe : colonne de lecture, notes de marge et notes de bas de tableau.
 * Le calculateur n'y est pas : c'est le composant du plan 3, mesuré sur sa page d'essai, et
 * ses sources, en petit texte, y font déjà des lignes plus longues.
 */
const PROSE = [
  '.annexe .texte p:not(.calculateur p)',
  '.annexe .large p',
  '.annexe .note p',
  '.annexe .note dd',
  '.annexe .notes-groupe li',
].join(', ');

async function ouvrir(page: Page, adresse: string): Promise<void> {
  const reponse = await page.goto(adresse);
  expect(reponse?.status(), adresse).toBe(200);
}

test('les trois annexes répondent 200, avec leur titre, sans violation axe ni débordement', async ({ page }) => {
  expect(CONSTRUITES.map((a) => a.titre)).toEqual(['Glossaire', 'Annuaire des données', 'Calculateur de coût']);
  for (const annexe of CONSTRUITES) {
    await ouvrir(page, annexe.href!);
    if (annexe.href === CALCULATEUR_HREF) await attendreHydratation(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(typographier(annexe.titrePage));
    // La barre des annexes signale la page où l'on est.
    const barre = page.getByRole('navigation', { name: 'Les annexes' });
    await expect(barre.locator('a[aria-current="page"]')).toHaveAttribute('href', annexe.href!);
    await expect(barre.locator('a')).toHaveCount(CONSTRUITES.length);
    await verifierTypographieHorsCode(page.locator('main'));
    await verifierAxe(page);
    await verifierSansDebordement(page);
  }
});

test('les lignes de prose des annexes ont 80 caractères au plus, à cette largeur et à 720 px', async ({ page }) => {
  for (const largeur of [undefined, 720]) {
    if (largeur !== undefined) await page.setViewportSize({ width: largeur, height: 900 });
    for (const annexe of CONSTRUITES) {
      await ouvrir(page, annexe.href!);
      await page.evaluate(() => document.fonts.ready.then(() => undefined));
      const { longueur, ligne } = await plusLongueLigne(page, PROSE);
      expect(longueur, `${annexe.href} (${largeur ?? 'largeur du projet'}) : « ${ligne} »`).toBeLessThanOrEqual(80);
    }
  }
});

test('le pied mène aux annexes voisines, et le matériel est à venir', async ({ page }) => {
  await ouvrir(page, GLOSSAIRE_HREF);
  const voisins = page.getByRole('navigation', { name: 'Annexes voisines' });
  await expect(voisins.getByRole('link', { name: /Toutes les annexes/ })).toHaveAttribute('href', '/forge-ia/#annexes');
  await expect(voisins.getByRole('link', { name: /annuaire des données/ })).toHaveAttribute('href', ANNUAIRE_HREF);
  await ouvrir(page, CALCULATEUR_HREF);
  await expect(page.getByRole('navigation', { name: 'Annexes voisines' })).toContainText('Annexe suivante, à venir');
  await expect(page.getByRole('navigation', { name: 'Annexes voisines' }).getByRole('link')).toHaveCount(1);
});

test('l’accueil mène aux trois annexes construites', async ({ page }) => {
  for (const annexe of CONSTRUITES) {
    await ouvrir(page, '/forge-ia/');
    await page.locator(`#annexes a[href="${annexe.href}"]`).click();
    await page.waitForURL(`**${annexe.href}`);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(typographier(annexe.titrePage));
  }
});

test('glossaire : chaque terme a son ancre, et l’adresse #<id> mène à son terme', async ({ page }) => {
  await ouvrir(page, GLOSSAIRE_HREF);
  await expect(page.locator('[data-terme]')).toHaveCount(GLOSSAIRE.length);
  const ids = await page.locator('[data-terme] h3').evaluateAll((titres) => titres.map((t) => t.id));
  expect(ids).toEqual(GLOSSAIRE.map((t) => t.id));
  // Chaque « voir aussi » vise une ancre de la page.
  const cibles = await page.locator('[data-voir-aussi]').evaluateAll((liens) => liens.map((l) => l.getAttribute('href')));
  for (const cible of new Set(cibles)) expect(ids, cible ?? '').toContain((cible ?? '').slice(1));
  // Depuis une autre page : l'adresse avec son ancre est un vrai chargement.
  await ouvrir(page, ANNUAIRE_HREF);
  await ouvrir(page, `${GLOSSAIRE_HREF}#perplexite`);
  await expect(page.locator('#perplexite')).toBeInViewport();
  await expect(page.locator('#perplexite')).toHaveText('perplexité');
  // Les renvois sont de la navigation : hors de l'index de la recherche.
  for (const renvois of await page.locator('.renvois').all()) {
    expect(await renvois.evaluate((e) => e.closest('[data-pagefind-ignore]') !== null)).toBe(true);
  }
});

test('glossaire : le filtre réduit la liste, garde les termes d’un chapitre, et dit quand rien ne reste', async ({ page }) => {
  await ouvrir(page, GLOSSAIRE_HREF);
  const champ = page.getByRole('searchbox', { name: 'Filtrer les termes' });
  const visibles = page.locator('[data-terme]:visible');
  const compte = page.locator('[data-compte]');
  await expect(compte).toHaveText(`${GLOSSAIRE.length} termes.`);

  await champ.fill('gradient');
  const attendus = GLOSSAIRE.filter((t) =>
    `${t.terme} ${t.aussi ?? ''} ${t.anglais ?? ''} ${t.enFrancais ?? ''} ${t.definition}`.toLowerCase().includes('gradient'),
  );
  expect(attendus.length).toBeGreaterThan(1);
  expect(attendus.length).toBeLessThan(GLOSSAIRE.length);
  await expect(visibles).toHaveCount(attendus.length);
  await expect(page.locator('[data-terme] mark').first()).toHaveText(/gradient/i);
  await expect(compte).toHaveText(`${attendus.length} termes sur ${GLOSSAIRE.length} pour «${FINE}gradient${FINE}».`);

  // Un numéro de chapitre garde les termes dont ce chapitre parle (expliqués, cités ou appliqués).
  await champ.fill('1.3');
  const du13 = GLOSSAIRE.filter((t) => t.renvois.some((r) => r.chapitre === '1.3'));
  await expect(visibles).toHaveCount(du13.length);

  // Rien ne reste : le message le dit, et propose la recherche du site.
  await champ.fill('xylophone');
  await expect(visibles).toHaveCount(0);
  const vide = page.locator('[data-vide]');
  await expect(vide).toBeVisible();
  await expect(vide).toContainText(`Aucun terme ne contient «${FINE}xylophone${FINE}».`);
  await expect(vide.getByRole('link', { name: 'cherche-le partout' })).toHaveAttribute('href', '/forge-ia/recherche/?q=xylophone');
  await verifierAxe(page);
  await verifierSansDebordement(page);

  // « effacer » remontre tout.
  await page.getByRole('button', { name: 'effacer' }).click();
  await expect(visibles).toHaveCount(GLOSSAIRE.length);
  await expect(vide).toBeHidden();
  await expect(champ).toBeFocused();
});

test('glossaire : un renvoi vers un chapitre paru est un lien, les autres disent « à venir »', async ({ page, request }) => {
  await ouvrir(page, GLOSSAIRE_HREF);
  const aVenir = new Set<string>();
  for (const t of GLOSSAIRE) {
    const renvois = page.locator(`[data-terme="${t.id}"] .renvois`);
    for (const r of t.renvois) {
      if (PARUS.has(r.chapitre)) {
        await expect(renvois.locator(`a[href="${adresseDuChapitre(r.chapitre)}"]`), `${t.id} → ${r.chapitre}`).toHaveCount(1);
      } else {
        aVenir.add(r.chapitre);
        await expect(renvois.locator('.chapitre-a-venir', { hasText: r.chapitre }), `${t.id} → ${r.chapitre}`).toHaveCount(1);
        await expect(renvois, t.id).toContainText('à venir');
      }
    }
  }
  // Aucun lien vers un chapitre qui n'a pas paru (1.5 et 1.6 au moins, aujourd'hui).
  expect(aVenir.size).toBeGreaterThan(0);
  for (const numero of aVenir) await expect(page.locator(`main a[href="${adresseDuChapitre(numero)}"]`)).toHaveCount(0);
  // Les liens des chapitres parus répondent.
  const liens = await page.locator('.renvois a[href^="/forge-ia/partie-"]').evaluateAll((a) => a.map((l) => l.getAttribute('href')));
  for (const lien of new Set(liens)) expect((await request.get(lien!)).status(), lien!).toBe(200);
});

test('glossaire : sans JavaScript, toute la liste se lit et le filtre reste caché', async ({ browser, baseURL }) => {
  const contexte = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await contexte.newPage();
  await ouvrir(page, GLOSSAIRE_HREF);
  await expect(page.locator('[data-terme]:visible')).toHaveCount(GLOSSAIRE.length);
  await expect(page.locator('[data-filtre]')).toBeHidden();
  await contexte.close();
});

test('la recherche du site trouve « perplexité » dans le glossaire', async ({ page }) => {
  await ouvrir(page, '/forge-ia/recherche/?q=perplexité');
  // Pagefind peut être lent pendant l'entraînement (disque D: occupé) : on vérifie les résultats, pas la vitesse.
  const glossaire = page.locator('[data-resultat]', { hasText: 'Le glossaire' });
  await expect(glossaire.first()).toBeVisible({ timeout: 15_000 });
  await expect(glossaire.first().locator(`a[href="${GLOSSAIRE_HREF}#perplexite"]`)).toHaveCount(1);
});

test('annuaire : une ligne par fiche, les jeux de ton IA marqués, les dates hors de la recherche', async ({ page }) => {
  await ouvrir(page, ANNUAIRE_HREF);
  await expect(page.locator('tr[data-fiche]')).toHaveCount(ANNUAIRE.length);
  await expect(page.locator('tr.ton-ia')).toHaveCount(ANNUAIRE.filter((f) => f.tonIA !== null).length);
  for (const f of ANNUAIRE) {
    const ligne = page.locator(`tr[data-fiche="${f.id}"]`);
    await expect(ligne.getByRole('link', { name: f.nom, exact: true })).toHaveAttribute('href', f.url);
    if (f.licence === null) await expect(ligne.locator('.licence')).toContainText('non indiquée');
    await expect(ligne.locator('[data-test="releve-le"] time')).toHaveAttribute('datetime', f.releveLe);
    // On remonte au relevé : la fiche (réponse de l'API), et la source de la taille quand il y en a une.
    const sources = ligne.locator('[data-test="sources-fiche"]');
    await expect(sources.getByRole('link', { name: 'fiche' })).toHaveAttribute('href', f.source);
    if (f.sourceTaille !== undefined) await expect(sources.getByRole('link', { name: 'taille' })).toHaveAttribute('href', f.sourceTaille);
    else await expect(sources.getByRole('link', { name: 'taille' })).toHaveCount(0);
  }
  // Les colonnes de dates restent hors de l'index de la recherche ; le reste du tableau y entre.
  const dates = page.locator('[data-test="releve-le"], thead th:last-child');
  expect(await dates.count()).toBeGreaterThan(ANNUAIRE.length);
  for (const date of await dates.all()) {
    expect(await date.evaluate((e) => e.closest('[data-pagefind-ignore]') !== null)).toBe(true);
  }
  expect(await page.locator('table.annuaire').first().evaluate((e) => e.closest('[data-pagefind-body]') !== null)).toBe(true);
  // Chaque appel de note mène à sa note.
  const appels = await page.locator('.appel a').evaluateAll((a) => a.map((l) => l.getAttribute('href')));
  expect(appels.length).toBeGreaterThan(0);
  for (const appel of new Set(appels)) await expect(page.locator(appel!)).toHaveCount(1);
});

test('calculateur : ouvert d’office, il se règle sans pari', async ({ page }) => {
  await ouvrir(page, CALCULATEUR_HREF);
  await attendreHydratation(page);
  const modele = page.locator('[data-test="calc-modele"]');
  await expect(modele).toBeEnabled();
  const avant = await page.locator('[data-test="calc-calcul"]').textContent();
  await modele.selectOption({ index: 0 });
  await expect(page.locator('[data-test="calc-calcul"]')).not.toHaveText(avant ?? '');
  await expect(page.locator('[data-pari]')).toHaveCount(0);
});
