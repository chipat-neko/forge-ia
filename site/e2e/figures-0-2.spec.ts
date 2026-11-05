// Parcours des trois figures du chapitre 0.2, « Les maths utiles » : un
// brouillon (src/brouillons/chapitres/0-2.mdx) tant qu'il n'a pas paru,
// construit à son adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau des maths utiles (src/lib/partie-0/maths.ts)
// et des textes des figures (paris-0-2.ts) : deux modules purs, qu'un parcours
// chargé par Node sans Vite peut importer (B1). Les phrases clés de la tâche
// (« Pas 1 : x = 3,000 », le message de l'explosion…) sont aussi écrites ici en
// toutes lettres, pour ne pas seulement comparer le module à lui-même.
import { test, expect, type Locator, type Page } from '@playwright/test';
import { descendre, EXEMPLE_COMPTES, GRAINE_TIRAGE, probabilites, tirages } from '../src/lib/partie-0/maths';
import { ecrireNombre, NOMBRES_DE_TIRAGES } from '../src/lib/partie-0/paris-0-2';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierSansDebordement,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-2/';
const FINE = '\u202F';
const MOINS = '\u2212';
/** Ce qu'une figure ne doit jamais écrire : un calcul qui a mal tourné. */
const ABSURDE = /NaN|Infinity|undefined|\de\+/;

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(page: Page, test: string): Promise<string> {
  return (await page.locator(`[data-test="${test}"]`).textContent()) ?? '';
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Ouvre la page et fait les paris qui ouvrent les figures des vecteurs et de la descente. */
async function ouvrirFigures(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="scalaire"] [data-juste]').click();
  await page.locator('[data-pari="pente"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="vecteurs"]')).toHaveCSS('opacity', '1');
  await expect(page.locator('[data-verrou="descente"]')).toHaveCSS('opacity', '1');
}

/** Règle un nombre jaune au clavier sur une valeur (aria-valuenow), par les flèches. */
async function regler(nombre: Locator, valeur: number, pas = 1): Promise<void> {
  await nombre.focus();
  const actuelle = Number(await nombre.getAttribute('aria-valuenow'));
  const crans = Math.round((valeur - actuelle) / pas);
  for (let i = 0; i < Math.abs(crans); i++) await nombre.press(crans > 0 ? 'ArrowRight' : 'ArrowLeft');
  await expect(nombre).toHaveAttribute('aria-valuenow', String(valeur));
}

/** Tous les attributs de dessin d'un SVG : aucun ne doit contenir NaN ni Infinity. */
async function attributsDuDessin(dessin: Locator): Promise<string> {
  return dessin.evaluate((svg) =>
    [svg, ...svg.querySelectorAll('*')]
      .flatMap((e) => [...e.attributes].map((a) => `${a.name}=${a.value}`))
      .join(' '),
  );
}

/** Une position de la descente, comme la liste des pas l'écrit : trois décimales, signe moins U+2212. */
function position(x: number): string {
  return ecrireNombre(x, 3);
}

test('vecteurs : le produit scalaire et le cosinus suivent les réglages', async ({ page }) => {
  await ouvrirFigures(page);
  // Au départ : (3, 1) et (1, 2).
  expect(await texteExact(page, 'vec-scalaire')).toBe('a · b = 3 × 1 + 1 × 2 = 5');
  expect(await texteExact(page, 'vec-cosinus')).toBe(`cos = 5 ÷ (3,16 × 2,24) = 0,71${FINE}: à peu près la même direction`);
  await expect(page.locator('[data-test="vec-dessin"]')).toHaveAttribute('aria-label', /a = \(3,\s1\).*b = \(1,\s2\)/);

  // (2, 1) et (−1, 2) : perpendiculaires, le défi est réussi et l'acquis gagné.
  await regler(page.locator('[data-test="vec-ax"]'), 2);
  await regler(page.locator('[data-test="vec-bx"]'), -1);
  expect(await texteExact(page, 'vec-scalaire')).toBe(`a · b = 2 × (${MOINS}1) + 1 × 2 = 0`);
  // Le cas exact se décide sur les entiers : « perpendiculaires », pas « presque ».
  expect(await texteExact(page, 'vec-cosinus')).toBe(`cos = 0 ÷ (2,24 × 2,24) = 0${FINE}: perpendiculaires`);
  await expect(page.locator('[data-test="vec-defi"]')).toBeVisible();
  await expect(page.locator('#recap [data-acquis="perpendiculaires"]')).toHaveAttribute('data-gagne', 'oui');
  await expect(page.locator('[data-test="vec-dessin"]')).toHaveAttribute('aria-label', new RegExp(`b = \\(${MOINS}1,\\s2\\)`));

  // Opposés : (−4, −4) et (4, 4).
  for (const [test, v] of [['vec-ax', -4], ['vec-ay', -4], ['vec-bx', 4], ['vec-by', 4]] as const) {
    await regler(page.locator(`[data-test="${test}"]`), v);
  }
  // Sur une même droite, en sens contraires : cos = −1 exactement, décidé sur les entiers.
  expect(await texteExact(page, 'vec-cosinus')).toBe(
    `cos = ${MOINS}32 ÷ (5,66 × 5,66) = ${MOINS}1${FINE}: des directions opposées`,
  );
  // Les bornes : −4 et 4.
  await page.locator('[data-test="vec-by"]').press('End');
  await expect(page.locator('[data-test="vec-by"]')).toHaveAttribute('aria-valuenow', '4');
  await page.locator('[data-test="vec-by"]').press('Home');
  await expect(page.locator('[data-test="vec-by"]')).toHaveAttribute('aria-valuenow', '-4');
  // a + b = (0, −8) sort du quadrillage : c'est dit, sans valeur absurde.
  await expect(page.locator('[data-test="vec-somme"]')).toContainText('hors du dessin');
  expect(await attributsDuDessin(page.locator('[data-test="vec-dessin"]'))).not.toMatch(/NaN|Infinity/);
});

test('vecteurs : un vecteur nul ne casse rien', async ({ page }) => {
  await ouvrirFigures(page);
  await regler(page.locator('[data-test="vec-ax"]'), 0);
  await regler(page.locator('[data-test="vec-ay"]'), 0);
  expect(await texteExact(page, 'vec-cosinus')).toBe(`a est nul${FINE}: il n’a pas de direction, le cosinus n’existe pas.`);
  expect(await texteExact(page, 'vec-scalaire')).toBe('a · b = 0 × 1 + 0 × 2 = 0');
  // a · b = 0, mais a est nul : le défi n'est pas réussi.
  await expect(page.locator('[data-test="vec-defi"]')).toHaveCount(0);
  // Les deux nuls.
  await regler(page.locator('[data-test="vec-bx"]'), 0);
  await regler(page.locator('[data-test="vec-by"]'), 0);
  expect(await texteExact(page, 'vec-cosinus')).toBe(
    `a et b sont nuls${FINE}: ils n’ont pas de direction, le cosinus n’existe pas.`,
  );
  const figure = page.locator('[data-figure="vecteurs"]');
  expect(await figure.innerText()).not.toMatch(ABSURDE);
  expect(await page.locator('[data-test="vec-dessin"]').getAttribute('aria-label')).not.toMatch(ABSURDE);
  expect(await attributsDuDessin(page.locator('[data-test="vec-dessin"]'))).not.toMatch(/NaN|Infinity/);
  await expect(page.locator('#recap [data-acquis="perpendiculaires"]')).not.toHaveAttribute('data-gagne', 'oui');
});

test('descente : au taux 0,5, un pas suffit', async ({ page }) => {
  await ouvrirFigures(page);
  // Au pas 0, la phrase de la pente.
  expect(await texteExact(page, 'desc-etat')).toBe(
    `En x = 0, la pente vaut 2 × (0 ${MOINS} 3) = ${MOINS}6${FINE}: la courbe descend vers la droite.`,
  );
  const taux = page.locator('[data-test="desc-taux"]');
  await expect(taux).toHaveAttribute('aria-valuetext', '0,1');
  await taux.focus();
  for (let i = 0; i < 3; i++) await taux.press('ArrowRight');
  await expect(taux).toHaveAttribute('aria-valuetext', '0,5');
  await page.locator('[data-test="desc-pas"]').click();
  expect(await texteExact(page, 'desc-etat')).toBe(`Pas 1${FINE}: x = 3,000, erreur = 1,000, pente = 0,000.`);
  // L'état est annoncé après le clic.
  await expect(page.locator('[data-test="desc-annonce"]')).toContainText('Pas 1');
  // Changer le taux repart du pas 0, sans rien annoncer.
  await taux.press('ArrowLeft');
  await expect(page.locator('[data-test="desc-liste"] li')).toHaveCount(1);
  expect(await texteExact(page, 'desc-etat')).toContain('En x = 0');
  await expect(page.locator('[data-test="desc-annonce"]')).toBeEmpty();
  // Revenir au taux d'avant ne ressuscite pas l'ancienne descente, et ne l'annonce pas.
  await taux.press('ArrowRight');
  await expect(taux).toHaveAttribute('aria-valuetext', '0,5');
  await expect(page.locator('[data-test="desc-liste"] li')).toHaveCount(1);
  expect(await texteExact(page, 'desc-etat')).toContain('En x = 0');
  await expect(page.locator('[data-test="desc-annonce"]')).toBeEmpty();
});

test('descente : au taux 1,2, la descente explose proprement', async ({ page }) => {
  await ouvrirFigures(page);
  const taux = page.locator('[data-test="desc-taux"]');
  await taux.focus();
  await taux.press('End');
  await expect(taux).toHaveAttribute('aria-valuetext', '1,2');
  const dix = page.locator('[data-test="desc-dix"]');
  await dix.click();
  await dix.click();
  expect(await texteExact(page, 'desc-etat')).toBe(
    `x est parti à plus de 1${FINE}000 du fond${FINE}: ce taux fait exploser la descente.`,
  );
  // La descente s'arrête au pas où elle explose : 18, d'après le jumeau.
  await expect(page.locator('[data-test="desc-liste"] li')).toHaveCount(19);
  await expect(page.locator('[data-test="desc-pas"]')).toHaveAttribute('aria-disabled', 'true');
  await expect(dix).toHaveAttribute('aria-disabled', 'true');
  // Un clic de plus ne fait rien (force : Playwright n'essaie pas de cliquer un bouton aria-disabled).
  await dix.click({ force: true });
  await expect(page.locator('[data-test="desc-liste"] li')).toHaveCount(19);
  // Le point est sorti du dessin : c'est dit.
  await expect(page.locator('[data-test="desc-hors"]')).toBeVisible();
  const figure = page.locator('[data-figure="descente"]');
  expect(await figure.innerText()).not.toMatch(ABSURDE);
  expect(await page.locator('[data-test="desc-dessin"]').getAttribute('aria-label')).not.toMatch(ABSURDE);
  expect(await attributsDuDessin(page.locator('[data-test="desc-dessin"]'))).not.toMatch(/NaN|Infinity/);
  await verifierSansDebordement(page);
  // Recommencer : retour au pas 0, les boutons repartent.
  await page.locator('[data-test="desc-recommencer"]').click();
  await expect(page.locator('[data-test="desc-liste"] li')).toHaveCount(1);
  await expect(page.locator('[data-test="desc-pas"]')).not.toHaveAttribute('aria-disabled', 'true');
});

test('descente : les positions suivent le jumeau', async ({ page }) => {
  await ouvrirFigures(page);
  await page.locator('[data-test="desc-dix"]').click();
  const attendu = descendre(0, 0.1, 10).map(position);
  expect(await page.locator('[data-test="desc-liste"] li [data-x]').allTextContents()).toEqual(attendu);
  expect(attendu[3]).toBe('1,464');
  // Trois pas de plus, un par un, depuis un autre départ : x = −1,5.
  await regler(page.locator('[data-test="desc-x0"]'), -1.5, 0.5);
  await expect(page.locator('[data-test="desc-x0"]')).toHaveAttribute('aria-valuetext', `${MOINS}1,5`);
  for (let i = 0; i < 3; i++) await page.locator('[data-test="desc-pas"]').click();
  expect(await page.locator('[data-test="desc-liste"] li [data-x]').allTextContents()).toEqual(
    descendre(-1.5, 0.1, 3).map(position),
  );
  const x3 = descendre(-1.5, 0.1, 3)[3];
  expect(await texteExact(page, 'desc-etat')).toBe(
    `Pas 3${FINE}: x = ${position(x3)}, erreur = ${ecrireNombre((x3 - 3) * (x3 - 3) + 1, 3)}, ` +
      `pente = ${ecrireNombre(2 * (x3 - 3), 3)}.`,
  );
});

test('descente : la pastille du départ garde sa largeur, de 0,5 en 0,5', async ({ page }) => {
  // NombreManipulable mesure sa largeur de pas en pas : « −1,5 » compte, pas seulement « −2 » et « 8 ».
  await ouvrirFigures(page);
  const x0 = page.locator('[data-test="desc-x0"]');
  const largeurs: number[] = [];
  await x0.focus();
  for (const touche of ['Home', 'ArrowRight', 'ArrowRight', 'End', 'ArrowLeft']) {
    await x0.press(touche);
    largeurs.push((await x0.boundingBox())!.width);
  }
  await expect(x0).toHaveAttribute('aria-valuetext', '7,5');
  for (const largeur of largeurs) expect(Math.abs(largeur - largeurs[0]), `largeurs ${largeurs.join(', ')}`).toBeLessThan(0.5);
});

test('tirage : les comptes suivent le jumeau, même à 100 000', async ({ page }) => {
  await ouvrirFigures(page);
  const probas = probabilites(EXEMPLE_COMPTES);
  const n = page.locator('[data-test="tir-n"]');

  /** Les lignes du tableau : « fer », puis « 60 % attendu, 58 sur 100 tirés (58 %) ». */
  async function verifier(nombre: number, graine: number): Promise<void> {
    const comptes = tirages(probas, nombre, graine);
    const lignes = page.locator('[data-test="tir-resultats"] tbody tr');
    await expect(lignes).toHaveCount(EXEMPLE_COMPTES.length);
    // La fréquence tirée, exacte : autant de décimales qu'il en faut (aucune sur 100 tirages, trois sur 100 000).
    const decimales = String(nombre).length - 3;
    for (const [i, [nom]] of EXEMPLE_COMPTES.entries()) {
      const cases = await lignes.nth(i).locator('th, td').evaluateAll((c) => c.map((e) => e.textContent ?? ''));
      const pour = ((100 * comptes[i]) / nombre).toFixed(Math.max(0, decimales)).replace('.', ',');
      expect(cases).toEqual([
        nom,
        `${ecrireNombre(probas[i] * 100)}${FINE}% attendu, ` +
          `${ecrireNombre(comptes[i])} sur ${ecrireNombre(nombre)} tirés (${pour}${FINE}%)`,
      ]);
    }
    expect(await page.locator('[data-figure="tirage"]').textContent()).toContain(`graine ${ecrireNombre(graine)}`);
  }

  // Au départ, 100 tirages, avec la graine de départ.
  await expect(n).toHaveAttribute('aria-valuetext', '100');
  await verifier(100, GRAINE_TIRAGE);
  // Les réglages de 10 à 10 000, au clavier.
  await n.focus();
  await n.press('Home');
  for (const [i, nombre] of NOMBRES_DE_TIRAGES.slice(0, -1).entries()) {
    if (i > 0) await n.press('ArrowRight');
    await expect(n).toHaveAttribute('aria-valuetext', ecrireNombre(nombre));
    await verifier(nombre, GRAINE_TIRAGE);
  }
  // Le dernier cran, 100 000 tirages : le recalcul tient en moins de 200 ms.
  const duree = await n.evaluate(async (element) => {
    const debut = performance.now();
    element.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    // Svelte met la page à jour avant la prochaine image.
    await new Promise((fin) => requestAnimationFrame(() => fin(null)));
    return performance.now() - debut;
  });
  expect(duree, `recalcul en ${Math.round(duree)} ms`).toBeLessThan(200);
  await expect(n).toHaveAttribute('aria-valuetext', ecrireNombre(100000));
  await verifier(100000, GRAINE_TIRAGE);
  // Autre graine : la graine suivante, affichée, et ses tirages.
  await page.locator('[data-test="tir-graine"]').click();
  await verifier(100000, GRAINE_TIRAGE + 1);
  expect(await page.locator('[data-figure="tirage"]').textContent()).toContain(`graine 1${FINE}235`);
  await expect(page.locator('[data-test="tir-annonce"]')).toContainText(`graine 1${FINE}235`);
  expect(await page.locator('[data-figure="tirage"]').innerText()).not.toMatch(ABSURDE);
  await verifierSansDebordement(page);
});

test('verrous, clavier, sans JavaScript, axe, débordement, typographie', async ({ page, browser, baseURL }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  // Avant les paris, les figures des vecteurs et de la descente sont verrouillées ; celle des tirages, non.
  await expect(page.locator('[data-verrou="vecteurs"]')).toHaveAttribute('inert', '');
  await expect(page.locator('[data-verrou="descente"]')).toHaveAttribute('inert', '');
  for (const test of ['vec-ax', 'vec-ay', 'vec-bx', 'vec-by', 'desc-x0', 'desc-taux']) {
    await expect(page.locator(`[data-test="${test}"]`)).toHaveAttribute('aria-disabled', 'true');
  }
  await expect(page.locator('[data-test="tir-n"]')).not.toHaveAttribute('aria-disabled', 'true');
  await expect(page.locator('.verrou-msg')).toHaveCount(2);
  await verifierAxe(page);

  // Le pari du produit scalaire ouvre la figure des vecteurs, celui de la pente, celle de la descente.
  await page.locator('[data-pari="scalaire"] [data-juste]').click();
  await expect(page.locator('[data-verrou="vecteurs"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-verrou="descente"]')).toHaveAttribute('inert', '');
  await page.locator('[data-pari="pente"] [data-juste]').click();
  await expect(page.locator('[data-verrou="descente"]')).not.toHaveAttribute('inert', '');

  // Au clavier : Tab atteint les nombres et les boutons, Entrée et Espace font un pas.
  await page.locator('[data-test="vec-ax"]').focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.locator('[data-test="vec-ax"]')).toHaveAttribute('aria-valuenow', '2');
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-test="vec-ay"]')).toBeFocused();
  await page.locator('[data-test="desc-taux"]').focus();
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-test="desc-pas"]')).toBeFocused();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Space');
  expect(await texteExact(page, 'desc-etat')).toMatch(/^Pas 2/);
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-test="desc-dix"]')).toBeFocused();
  await page.locator('[data-test="tir-graine"]').focus();
  await page.keyboard.press('Enter');
  expect(await page.locator('[data-figure="tirage"]').textContent()).toContain(`graine 1${FINE}235`);

  // Les autres paris de ces étapes : leurs explications entrent dans les contrôles de lecture.
  for (const id of ['taux-moitie', 'taux-grand', 'tirage']) await page.locator(`[data-pari="${id}"] [data-juste]`).click();

  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);

  // Sans JavaScript : pas de verrou, les figures sont là avec leurs valeurs de départ.
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const sansJs = await ctx.newPage();
  await sansJs.goto(PAGE);
  await expect(sansJs.locator('[data-verrou="vecteurs"]')).not.toHaveAttribute('inert', '');
  expect(await texteExact(sansJs, 'vec-scalaire')).toBe('a · b = 3 × 1 + 1 × 2 = 5');
  await expect(sansJs.locator('[data-test="vec-dessin"]')).toBeVisible();
  expect(await texteExact(sansJs, 'desc-etat')).toContain('En x = 0, la pente vaut');
  await expect(sansJs.locator('[data-test="desc-dessin"]')).toBeVisible();
  await expect(sansJs.locator('[data-test="desc-liste"] li')).toHaveCount(1);
  const comptes = tirages(probabilites(EXEMPLE_COMPTES), 100, GRAINE_TIRAGE);
  await expect(sansJs.locator('[data-test="tir-resultats"] tbody tr').first()).toContainText(`${comptes[0]} sur 100 tirés`);
  for (const id of ['scalaire', 'pente', 'taux-moitie', 'taux-grand', 'tirage']) {
    await expect(sansJs.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await verifierSansDebordement(sansJs);
  await ctx.close();
});
