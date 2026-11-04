// Parcours du calculateur de coût, sur la page d'essai
// /forge-ia/essais/calculateur/ (construite seulement avec FORGE_ESSAIS=1,
// voir src/essais/calculateur.mdx). Le calculateur est derrière le verrou
// « calculateur », ouvert par le pari « operations ».
//
// Les valeurs attendues sont calculées ici par les modules de la tâche 10,
// importés directement (TypeScript pur, sans import propre à Vite) : aucun
// nombre n'est recopié.
import { test, expect, type Locator, type Page } from '@playwright/test';
import { nombre, pourcent } from '../src/lib/nombres';
import { fourchettePrix, materiel, REPERES_EFFICACITE } from '../src/lib/calculateur/donnees';
import { formaterDate, formaterDuree, formaterPrix, formaterPuissanceDeDix, formaterQuantite } from '../src/lib/calculateur/formats';
import { dureeSecondes, efficaciteMesuree, efficaciteMesureeAvecAttention, operationsEntrainement } from '../src/lib/calculateur/formules';
import { MESURES_TON_IA, PRESETS_FORGE } from '../src/lib/calculateur/ton-ia';
import { attendreHydratation, verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/calculateur/';
const F = '\u202F';
const N = PRESETS_FORGE.tres_grand.parametres;

const calc = (p: Page) => p.locator('.calculateur');
const t = (p: Page, id: string) => p.locator(`[data-test="${id}"]`);
const etat = (p: Page) => calc(p).getByRole('status');

/** Un texte, ses espaces insécables, fines et retours à la ligne ramenés à une espace ordinaire. */
const norm = (texte: string) => texte.replace(/[\u00A0\u202F\s]+/g, ' ').trim();
/** Le texte d'une zone (textContent), normalisé. */
const brut = async (zone: Locator) => norm((await zone.textContent()) ?? '');

/**
 * La phrase réglable telle qu'elle se lit : un sélecteur compte pour son
 * option choisie, et ce qui est caché (display: none) ne compte pas.
 */
async function phraseLue(p: Page): Promise<string> {
  const texte = await t(p, 'calc-phrase').evaluate((racine) => {
    const lire = (n: Node): string => {
      if (n.nodeType === Node.TEXT_NODE) return n.textContent ?? '';
      if (!(n instanceof HTMLElement)) return '';
      if (getComputedStyle(n).display === 'none') return '';
      if (n instanceof HTMLSelectElement) return n.selectedOptions[0]?.text ?? '';
      return Array.from(n.childNodes).map(lire).join('');
    };
    return lire(racine);
  });
  return norm(texte);
}

/** Ouvre la page et joue le pari « operations » (la bonne réponse), qui ouvre le calculateur. */
async function ouvrir(p: Page): Promise<void> {
  await p.goto(PAGE);
  await attendreHydratation(p);
  await p.locator('[data-pari="operations"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(p.locator('[data-verrou="calculateur"]')).toHaveCSS('opacity', '1');
}

test('avant le pari, rien ne se règle ; après, tout', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(t(page, 'calc-modele')).toBeDisabled();
  await expect(t(page, 'calc-materiel')).toBeDisabled();
  for (const id of ['calc-jetons', 'calc-cartes', 'calc-efficacite']) await expect(t(page, id)).toHaveAttribute('aria-disabled', 'true');
  await ouvrir(page);
  await expect(t(page, 'calc-modele')).toBeEnabled();
  await expect(t(page, 'calc-materiel')).toBeEnabled();
  for (const id of ['calc-jetons', 'calc-cartes', 'calc-efficacite']) await expect(t(page, id)).not.toHaveAttribute('aria-disabled', 'true');
});

test('réglage de départ : ton IA sur la RTX 5070 Ti', async ({ page }) => {
  await ouvrir(page);
  const s = dureeSecondes(operationsEntrainement(N, 20 * N), 87.9, 0.5, 1);
  await expect(t(page, 'calc-duree')).toContainText(formaterDuree(s));
  await expect(t(page, 'calc-memoire')).toContainText('ça tient sur une carte');
  await expect(t(page, 'calc-reperes')).toContainText(`${nombre(17_855)} jetons`);
  await expect(t(page, 'calc-reperes')).toContainText(pourcent(efficaciteMesuree(N, 17_855, 87.9), 1));
  // La phrase réglable, avec ses valeurs de départ.
  await expect(t(page, 'calc-modele')).toHaveValue('tres_grand');
  await expect(t(page, 'calc-materiel')).toHaveValue('rtx-5070-ti');
  await expect(t(page, 'calc-jetons')).toHaveAttribute('aria-valuetext', '20');
  await expect(t(page, 'calc-cartes')).toHaveAttribute('aria-valuetext', '1');
  await expect(t(page, 'calc-efficacite')).toHaveAttribute('aria-valuetext', `50${F}%`);
  expect(await phraseLue(page)).toBe(
    norm(
      `Entraîner ton IA « très grand » en lui faisant lire 20 jetons par paramètre, soit ${formaterQuantite(20 * N)} de jetons, ` +
        `avec 1 × RTX 5070 Ti, à 50 % d’efficacité.`,
    ),
  );
  // Le relevé : le calcul, l'électricité, la location.
  await expect(t(page, 'calc-calcul')).toContainText(`${formaterPuissanceDeDix(operationsEntrainement(N, 20 * N))} opérations`);
  await expect(t(page, 'calc-electricite')).toContainText('42,8 kWh, environ 8,56 €');
  await expect(t(page, 'calc-cout')).toContainText('pas de prix relevé pour cette carte');
  // Le calcul et la mesure, côte à côte.
  const heures = (20 * N) / 17_855 / 3600;
  expect(await brut(t(page, 'calc-repere-phrase'))).toBe(
    norm(
      `Calcul : ${formaterDuree(s)}. Mesuré : ${formaterDuree(heures * 3600)} (${nombre(heures)} h). ` +
        `L’écart vient de l’efficacité : ${pourcent(efficaciteMesuree(N, 17_855, 87.9), 1)} mesurés contre 50 % supposés.`,
    ),
  );
  // Ton IA à côté de PaLM, en comptant l'attention comme lui.
  const avecAttention = efficaciteMesureeAvecAttention(PRESETS_FORGE.tres_grand, 17_855, 87.9);
  await expect(t(page, 'calc-comme-les-grands')).toContainText(`fait alors ${pourcent(avecAttention, 1)} sur ce PC`);
  await expect(t(page, 'calc-comme-les-grands')).toContainText(`PaLM 540B (46,2${F}%)`);
  // Changer de taille de ton IA garde la comparaison ; deux cartes l'enlèvent.
  await t(page, 'calc-modele').selectOption('mini');
  await expect(t(page, 'calc-repere-phrase')).toContainText('Mesuré');
  await t(page, 'calc-cartes').focus();
  await page.keyboard.press('ArrowRight');
  await expect(t(page, 'calc-repere-phrase')).toHaveCount(0);
});

test('valeurs extrêmes : 405 milliards sur une seule carte, puis 16 384 H100', async ({ page }) => {
  await ouvrir(page);
  await t(page, 'calc-modele').selectOption('llama-3-405b');
  await expect(t(page, 'calc-duree')).toContainText('ans');
  await expect(t(page, 'calc-memoire')).toContainText('il faut au moins');
  await expect(t(page, 'calc-memoire')).toContainText(`cartes de 16 Go`);
  await t(page, 'calc-materiel').selectOption('h100-sxm');
  await t(page, 'calc-cartes').focus();
  await page.keyboard.press('End');
  await expect(t(page, 'calc-cartes')).toHaveAttribute('aria-valuetext', '16\u202F384');
  await expect(t(page, 'calc-cout')).toContainText('millions d’euros');
  // La mémoire parle de la carte choisie : 80 Go, jamais un « 16 Go » écrit en dur.
  await expect(t(page, 'calc-memoire')).toContainText(`cartes de ${materiel('h100-sxm').memoireGo} Go`);
  // Le pire réglage : 2 000 jetons par paramètre, 10 % d'efficacité, une seule carte grand public.
  const texte = await calc(page).innerText();
  expect(texte).not.toMatch(/NaN|Infinity|e\+/);
  await verifierSansDebordement(page);
  await t(page, 'calc-jetons').focus();
  await page.keyboard.press('End');
  await t(page, 'calc-efficacite').focus();
  await page.keyboard.press('Home');
  await t(page, 'calc-cartes').focus();
  await page.keyboard.press('Home');
  await t(page, 'calc-materiel').selectOption('rtx-5070-ti');
  await expect(t(page, 'calc-efficacite')).toHaveAttribute('aria-valuetext', `10${F}%`);
  await expect(t(page, 'calc-duree')).toContainText('ans');
  await expect(t(page, 'calc-electricite')).toContainText('TWh');
  await t(page, 'calc-voir').click();
  expect(await calc(page).innerText()).not.toMatch(/NaN|Infinity|undefined|e\+/);
  await verifierSansDebordement(page);
  await verifierTypographie(calc(page));
});

test('au clavier : tous les réglages', async ({ page }) => {
  await ouvrir(page);
  const modele = t(page, 'calc-modele');
  // Le sélecteur de modèle, au clavier : la flèche passe au modèle suivant (GPT-3, après « très grand »).
  await modele.focus();
  const contour = await modele.evaluate((el) => {
    const s = getComputedStyle(el);
    return { style: s.outlineStyle, largeur: parseFloat(s.outlineWidth) };
  });
  expect(contour.style).toBe('solid');
  expect(contour.largeur).toBeGreaterThanOrEqual(2);
  const avant = await brut(t(page, 'calc-duree'));
  await page.keyboard.press('ArrowDown');
  await expect(modele).toHaveValue('gpt-3-175b');
  await expect.poll(() => brut(t(page, 'calc-duree'))).not.toBe(avant);
  // Puis chaque réglage, à la tabulation, dans l'ordre de la phrase.
  await page.keyboard.press('Tab');
  await expect(t(page, 'calc-jetons')).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect(t(page, 'calc-jetons')).toHaveAttribute('aria-valuetext', '50');
  await expect(t(page, 'calc-phrase')).toContainText('50 jetons par paramètre');
  await page.keyboard.press('Home');
  await expect(t(page, 'calc-jetons')).toHaveAttribute('aria-valuetext', '1');
  await expect(t(page, 'calc-phrase')).toContainText('1 jeton par paramètre');
  await page.keyboard.press('Tab');
  await expect(t(page, 'calc-cartes')).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect(t(page, 'calc-cartes')).toHaveAttribute('aria-valuetext', '2');
  await page.keyboard.press('Tab');
  await expect(t(page, 'calc-materiel')).toBeFocused();
  await page.keyboard.press('ArrowDown');
  await expect(t(page, 'calc-materiel')).toHaveValue('rtx-5080');
  await page.keyboard.press('Tab');
  await expect(t(page, 'calc-efficacite')).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(t(page, 'calc-efficacite')).toHaveAttribute('aria-valuetext', `49${F}%`);
  await expect(t(page, 'calc-phrase')).toContainText('à 49 % d’efficacité');
  await page.keyboard.press('Tab');
  await expect(t(page, 'calc-voir')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(t(page, 'calc-voir')).toHaveAttribute('aria-expanded', 'true');
  // Le relevé suit : GPT-3 (175 milliards), 1 jeton par paramètre, sur 2 RTX 5080 à 49 %.
  const g = 175e9;
  const s = dureeSecondes(operationsEntrainement(g, g), materiel('rtx-5080').creteTflops, 0.49, 2);
  await expect(t(page, 'calc-duree')).toContainText(formaterDuree(s));
  // La ligne d'état l'a annoncé, sans prendre le focus.
  await expect(etat(page)).toContainText(`Durée${F}: ${formaterDuree(s)}`);
  await expect(etat(page)).not.toBeFocused();
});

test('l’efficacité suit la catégorie de la carte, tant qu’on ne l’a pas réglée, et la ligne d’état le dit', async ({ page }) => {
  await ouvrir(page);
  const efficacite = t(page, 'calc-efficacite');
  await t(page, 'calc-materiel').selectOption('h100-sxm');
  await expect(efficacite).toHaveAttribute('aria-valuetext', `40${F}%`);
  await expect(etat(page)).toContainText(`Efficacité${F}: 40${F}%, celle d’une carte de centre de données.`);
  await t(page, 'calc-materiel').selectOption('rtx-5090');
  await expect(efficacite).toHaveAttribute('aria-valuetext', `50${F}%`);
  await expect(etat(page)).toContainText(`Efficacité${F}: 50${F}%, celle d’une carte grand public.`);
  // Une carte de la même catégorie : l'efficacité ne bouge pas, l'annonce n'en parle pas.
  await t(page, 'calc-materiel').selectOption('rtx-4090');
  await expect(etat(page)).toContainText('Durée');
  await expect(etat(page)).not.toContainText('Efficacité');
  // Le lecteur la règle, puis revient à 50 % : elle reste à lui, même revenue à la valeur par défaut.
  await efficacite.focus();
  await page.keyboard.press('ArrowRight');
  await expect(efficacite).toHaveAttribute('aria-valuetext', `51${F}%`);
  await page.keyboard.press('ArrowLeft');
  await expect(efficacite).toHaveAttribute('aria-valuetext', `50${F}%`);
  await t(page, 'calc-materiel').selectOption('h100-sxm');
  await expect(efficacite).toHaveAttribute('aria-valuetext', `50${F}%`);
  const h100 = dureeSecondes(operationsEntrainement(N, 20 * N), materiel('h100-sxm').creteTflops, 0.5, 1);
  await expect(etat(page)).toContainText(`Durée${F}: ${formaterDuree(h100)}`);
  await expect(etat(page)).not.toContainText('Efficacité');
  // L'explication de la durée donne les valeurs par défaut et leur base.
  await t(page, 'calc-voir').click();
  await expect(t(page, 'calc-formules').locator('[data-formule="duree"]')).toContainText('Par défaut, le calculateur suppose 50');
});

test('chaque prix affiché a sa source et sa date', async ({ page }) => {
  await ouvrir(page);
  const sources = t(page, 'calc-sources');
  // La carte de départ : sa source et sa date, et pas de prix.
  const rtx = materiel('rtx-5070-ti');
  await expect(sources.locator('[data-source="materiel"] a')).toHaveAttribute('href', rtx.source.url);
  await expect(sources.locator('[data-source="materiel"]')).toContainText(`relevé le ${formaterDate(rtx.source.releveLe)}`);
  await expect(sources.locator('[data-prix]')).toHaveCount(0);
  await expect(t(page, 'calc-cout')).toContainText('pas de prix relevé pour cette carte');
  // L'électricité au tarif d'EDF, sourcée et datée.
  await expect(sources.locator('[data-source="electricite"]')).toContainText('relevé le 3 novembre 2026');
  for (const id of ['rtx-4090', 'rtx-5090', 'a100-80', 'h100-sxm', 'h200', 'b200']) {
    await t(page, 'calc-materiel').selectOption(id);
    const carte = materiel(id);
    await expect(sources.locator('[data-source="materiel"] a').first()).toHaveAttribute('href', carte.source.url);
    const prix = fourchettePrix(id)!.prix;
    const lignes = sources.locator('[data-prix]');
    await expect(lignes).toHaveCount(prix.length);
    for (let i = 0; i < prix.length; i++) {
      const ligne = lignes.nth(i);
      await expect(ligne).toContainText(prix[i].fournisseur);
      await expect(ligne).toContainText(formaterPrix(prix[i].usdParHeure));
      await expect(ligne.locator('a')).toHaveAttribute('href', prix[i].source.url);
      await expect(ligne).toContainText(`relevé le ${formaterDate(prix[i].source.releveLe)}`);
    }
    // Les prix changent : une phrase le dit, sans chiffre qu'aucune source ne donne ; le taux de change est sourcé.
    expect(((await sources.locator('[data-test="calc-avertissement-prix"]').textContent()) ?? '').trim()).toBe(
      'Les prix de location changent souvent\u202F: ceux-ci sont ceux du jour de leur relevé, hors taxes.',
    );
    await expect(sources.locator('[data-source="change"]')).toContainText('relevé le 3 novembre 2026');
  }
  // La B200 a deux sources (la crête, puis la mémoire et la bande passante), chacune datée.
  const b200 = materiel('b200');
  await expect(sources.locator('[data-source="materiel"] a')).toHaveCount(2);
  await expect(sources.locator('[data-source="materiel"]')).toContainText(`relevé le ${formaterDate(b200.autresSources![0].releveLe)}`);
  // Les repères publiés (PaLM, Llama 3) : chacun sa source, sa date et sa définition.
  const reperes = t(page, 'calc-sources-reperes').locator('[data-repere]');
  await expect(reperes).toHaveCount(REPERES_EFFICACITE.length);
  for (let i = 0; i < REPERES_EFFICACITE.length; i++) {
    const r = REPERES_EFFICACITE[i];
    await expect(reperes.nth(i)).toContainText(r.modele);
    await expect(reperes.nth(i).locator('a')).toHaveAttribute('href', r.source.url);
    await expect(reperes.nth(i)).toContainText(`relevé le ${formaterDate(r.source.releveLe)}`);
    await expect(reperes.nth(i)).toContainText(r.definition);
  }
  await expect(t(page, 'calc-comme-les-grands')).toContainText('avec la définition de PaLM');
  // Les mesures de ton IA : la date vient de leur source, pas d'un texte écrit à la main.
  const mesures = MESURES_TON_IA.tres_grand.source;
  expect(MESURES_TON_IA.mini.source.releveLe).toBe(mesures.releveLe); // une seule date pour les deux liens
  const sourceMesures = calc(page).locator('.source-mesures');
  expect(await brut(sourceMesures)).toMatch(new RegExp(`^Mesures du ${norm(formaterDate(mesures.releveLe))} : le rapport de mesure`));
  await expect(sourceMesures.getByRole('link', { name: 'le rapport de mesure' })).toHaveAttribute('href', mesures.url);
  // Un modèle public : sa source, datée elle aussi.
  await t(page, 'calc-modele').selectOption('llama-3-405b');
  await expect(sources.locator('[data-source="modele"] a').first()).toHaveAttribute('href', 'https://arxiv.org/abs/2407.21783');
  await expect(sources.locator('[data-source="modele"]')).toContainText('relevé le 4 novembre 2026');
});

test('« Voir le calcul » déplie les formules', async ({ page }) => {
  await ouvrir(page);
  const bouton = t(page, 'calc-voir');
  const formules = t(page, 'calc-formules');
  await expect(bouton).toHaveAttribute('aria-expanded', 'false');
  await expect(bouton).toHaveText('Voir le calcul');
  await expect(formules).toBeHidden();
  await bouton.click();
  await expect(bouton).toHaveAttribute('aria-expanded', 'true');
  await expect(bouton).toHaveText('Cacher le calcul');
  await expect(formules).toBeVisible();
  const ops = operationsEntrainement(N, 20 * N);
  expect(await brut(formules.locator('[data-formule="calcul"]'))).toContain(
    `6 × ${formaterQuantite(N)} × ${formaterQuantite(20 * N)} = ${formaterPuissanceDeDix(ops)} opérations`.replace(/\u202F/g, ' '),
  );
  expect(await brut(formules.locator('[data-formule="calcul"]'))).toContain('6 × 433,6 millions × 8,67 milliards = 2,26 × 10¹⁹ opérations');
  // Les deux efficacités de ton IA : 6N, et en comptant l'attention.
  const efficacites = formules.locator('[data-formule="efficacites"]');
  await expect(efficacites).toContainText(pourcent(efficaciteMesuree(N, 17_855, 87.9), 1));
  await expect(efficacites).toContainText(pourcent(efficaciteMesureeAvecAttention(PRESETS_FORGE.tres_grand, 17_855, 87.9), 1));
  // Les unités des octets sont dites, et la génération divise par la mémoire des poids affichée plus haut.
  await expect(formules.locator('[data-formule="memoire"]')).toContainText('Ici, 1 Go vaut 1 024³ octets, comme la mémoire des cartes');
  await expect(formules.locator('[data-formule="service"]')).toContainText('Ici, 1 Go vaut 1 024³ octets');
  await expect(formules.locator('[data-formule="generation"]')).toContainText('÷ 827 Mo =');
  // Chaque formule a au moins une source.
  for (const f of await formules.locator('[data-formule]').all()) await expect(f.locator('a[href^="https://"]').first()).toBeVisible();
  // Un modèle public : pas d'efficacité mesurée ; une carte louée : la location.
  await t(page, 'calc-modele').selectOption('gpt-3-175b');
  await expect(efficacites).toHaveCount(0);
  await t(page, 'calc-materiel').selectOption('h100-sxm');
  await expect(formules.locator('[data-formule="location"]')).toContainText('÷ 1,1179');
  await expect(formules.locator('[data-formule="electricite"]')).toHaveCount(0);
  await bouton.click();
  await expect(formules).toBeHidden();
  await expect(bouton).toHaveAttribute('aria-expanded', 'false');
});

test('acquis gagné au premier changement de carte', async ({ page }) => {
  await ouvrir(page);
  const acquis = page.locator('#recap [data-acquis="calcul"]');
  await expect(acquis).toHaveAttribute('data-gagne', 'non');
  // Régler un nombre ne suffit pas.
  await t(page, 'calc-cartes').focus();
  await page.keyboard.press('ArrowRight');
  await expect(t(page, 'calc-cartes')).toHaveAttribute('aria-valuetext', '2');
  await expect(acquis).toHaveAttribute('data-gagne', 'non');
  await t(page, 'calc-materiel').selectOption('h100-sxm');
  await expect(acquis).toHaveAttribute('data-gagne', 'oui');
});

test('sans JavaScript : le réglage de départ reste lisible', async ({ browser, baseURL }, info) => {
  const { viewport, deviceScaleFactor, isMobile } = info.project.use;
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL, viewport, deviceScaleFactor, isMobile });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(calc(page).getByText('Sans JavaScript, le calculateur garde son réglage de départ')).toBeVisible();
  // Les sélecteurs ne feraient rien : leur valeur s'écrit à leur place.
  await expect(t(page, 'calc-modele')).toBeHidden();
  await expect(t(page, 'calc-modele-fixe')).toBeVisible();
  expect(await phraseLue(page)).toContain('Entraîner ton IA « très grand » en lui faisant lire 20 jetons par paramètre');
  const s = dureeSecondes(operationsEntrainement(N, 20 * N), 87.9, 0.5, 1);
  await expect(t(page, 'calc-duree')).toContainText(formaterDuree(s));
  await expect(t(page, 'calc-reperes')).toContainText(`${nombre(17_855)} jetons`);
  // Les formules sont dépliées d'office, la bascule est cachée.
  await expect(t(page, 'calc-voir')).toBeHidden();
  await expect(t(page, 'calc-formules')).toBeVisible();
  await expect(t(page, 'calc-sources')).toBeVisible();
  await verifierSansDebordement(page);
  await expect(page.locator('[data-pari="operations"] .verdict')).toBeVisible();
  await ctx.close();
});

test('accessibilité, largeur, typographie', async ({ page }) => {
  await ouvrir(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(calc(page));
  await verifierTypographie(page.locator('main'));
  // Formules dépliées, sur une carte louée.
  await t(page, 'calc-voir').click();
  await t(page, 'calc-materiel').selectOption('b200');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(calc(page));
  // Les réglages extrêmes.
  await t(page, 'calc-modele').selectOption('llama-3-405b');
  await t(page, 'calc-cartes').focus();
  await page.keyboard.press('End');
  await t(page, 'calc-jetons').focus();
  await page.keyboard.press('End');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(calc(page));
  // Des cibles d'au moins 24 px sur 24 px (les nombres jaunes et les liens sont dans des phrases :
  // WCAG 2.5.8 les en dispense, comme ceux de l'atelier).
  for (const cible of await calc(page).locator('button, select').all()) {
    if (!(await cible.isVisible())) continue;
    const boite = (await cible.boundingBox())!;
    const nom = (await cible.textContent()) ?? '';
    expect(boite.height, nom).toBeGreaterThanOrEqual(24);
    expect(boite.width, nom).toBeGreaterThanOrEqual(24);
  }
  // Le tableau des repères défile dans sa zone, focalisable, sans faire déborder la page.
  // « Repère mesuré » et « Les sources » sont de vrais titres, sous celui de l'étape ; la zone qui défile a son propre nom.
  await expect(calc(page).getByRole('heading', { level: 3, name: /^Repère mesuré\s*: ton IA sur ce PC$/ })).toHaveCount(1);
  await expect(calc(page).getByRole('heading', { level: 3, name: 'Les sources' })).toHaveCount(1);
  const zone = calc(page).getByRole('region', { name: 'Débits mesurés, défilable' });
  await expect(zone).toHaveAttribute('tabindex', '0');
  await expect(zone).toHaveCSS('overflow-x', 'auto');
  // La ligne d'état n'a jamais pris le focus.
  await expect(etat(page)).not.toBeFocused();
});
