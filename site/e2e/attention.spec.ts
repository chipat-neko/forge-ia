// Parcours de l'animation de l'attention, sur la page d'essai
// /forge-ia/essais/attention/ (construite seulement avec FORGE_ESSAIS=1, voir
// src/essais/attention.mdx). L'animation est derrière le verrou « attention »,
// ouvert par le pari « regard ».
//
// Les nombres attendus viennent du jumeau Python : tests/attendus-attention.json,
// écrit par « python -m mini_modele.attendus », chaque flottant en 16 chiffres
// hexadécimaux (le moteur TypeScript donne les mêmes bits, voir
// exemple-attention.test.ts). Aucun pourcentage n'est recopié. Têtes et mots
// comptés à partir de 0 : la tête 1 est « de qui on parle » (la « Tête 2 » de
// la page), le mot 6 « il ».
import { readFileSync } from 'node:fs';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { pourcent } from '../src/lib/nombres';
import { depuisHex } from '../src/lib/mini-modele/calcul';
import { attendreHydratation, verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/attention/';
const F = '\u202F';

interface TeteAttendue {
  nom: string;
  requetes: number[][];
  poids: number[][];
}

// Playwright tourne dans site/.
const ATTENDUS = JSON.parse(readFileSync('../projets/mini-modele/tests/attendus-attention.json', 'utf8')) as {
  jetons: string[];
  tetes: { nom: string; requetes: string[][]; poids: string[][] }[];
};
const versNombres = (m: string[][]) => m.map((ligne) => ligne.map(depuisHex));
const D: TeteAttendue[] = ATTENDUS.tetes.map((t) => ({ nom: t.nom, requetes: versNombres(t.requetes), poids: versNombres(t.poids) }));
const JETONS = ATTENDUS.jetons;
const N = JETONS.length;
const NB_TRAITS = 8;
const QUI_AGIT = 0;
const DE_QUI = 1;
const FORGERON = 1;
const CHAUFFE = 2;
const IL = 6;

const ETAPES = [
  'Les mots et leurs traits',
  'Requête, clé, valeur',
  `Les scores${F}: requête · clé`,
  'Divisés par √4 = 2',
  `Le masque${F}: pas de regard vers la suite`,
  `Softmax${F}: des poids qui font 1`,
  'Le mélange des valeurs',
];
// La légende du brief, en deux parties : la seconde ne s'affiche qu'avec la carte.
const LEGENDE_VECTEURS =
  'Ces vecteurs sont écrits à la main, comme si les couches précédentes avaient déjà reconnu le rôle de chaque mot. ' +
  'Dans un vrai modèle, ils sont appris, et les têtes sont rarement aussi nettes.';
const LEGENDE_CARTE =
  'La carte montre où le calcul lit, pas pourquoi le modèle répond. ' +
  `Une ligne par mot qui demande, une colonne par mot regardé${F}; score = requête · clé.`;
/** En dessous de cette largeur de fenêtre, la carte est plus large que la colonne de texte. */
const LARGEUR_CARTE_DEFILE = 480;
const COURTS = ['les traits', 'requête, clé, valeur', 'les scores', 'divisés par 2', 'le masque', 'softmax', 'le mélange'];

/** Un mot entre guillemets, avec les espaces fines. */
const g = (mot: string) => `«${F}${mot}${F}»`;
/** Un poids tel que la page l'écrit : le pourcentage de sa barre (2 décimales), arrondi à l'entier. */
const pourcentDe = (p: number) => pourcent(Number((p * 100).toFixed(2)) / 100);

const anim = (p: Page) => p.locator('[data-attention]');
const etat = (p: Page) => anim(p).getByRole('status');
const suivante = (p: Page) => anim(p).locator('[data-test="att-suivante"]');
const precedente = (p: Page) => anim(p).locator('[data-test="att-precedente"]');
const mot = (p: Page, i: number) => anim(p).locator(`[data-test="att-mot"][data-mot="${i}"]`);
const tete = (p: Page, t: number) => anim(p).locator(`[data-test="att-tete"][data-tete="${t}"]`);
const barre = (p: Page, i: number) => anim(p).locator(`[data-test="att-barre"][data-mot="${i}"]`);
const nombreDe = (p: Page, i: number) => anim(p).locator(`[data-test="att-nombre"][data-mot="${i}"]`);
const carte = (p: Page) => anim(p).locator('[data-test="att-carte"]');
const regionCarte = (p: Page) => anim(p).getByRole('region', { name: 'Carte complète de la tête, défilable' });
const legende = (p: Page) => anim(p).locator('[data-test="att-legende"]');

/** Les mesures de défilement d'une zone. */
const defilement = (zone: Locator) =>
  zone.evaluate((el) => ({ total: el.scrollWidth, visible: el.clientWidth, gauche: el.scrollLeft }));

/** Vérifie qu'une zone qui défile est focalisable et contient son tableau. */
async function verifierZone(zone: Locator, tableau: string): Promise<void> {
  await expect(zone).toHaveAttribute('tabindex', '0');
  await expect(zone).toHaveCSS('overflow-x', 'auto');
  await expect(zone.locator(`[data-test="${tableau}"]`)).toHaveCount(1);
}

/** Le texte brut (textContent : Playwright ramène U+202F à une espace dans toHaveText). */
const brut = async (zone: Locator) => ((await zone.textContent()) ?? '').trim();

/** Ouvre la page et joue le pari « regard » (la bonne réponse), qui ouvre l'animation. */
async function ouvrir(p: Page): Promise<void> {
  await p.goto(PAGE);
  await attendreHydratation(p);
  await p.locator('[data-pari="regard"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(p.locator('[data-verrou="attention"]')).toHaveCSS('opacity', '1');
}

/** Avance (ou recule) jusqu'à l'étape n, en cliquant. */
async function allerA(p: Page, n: number): Promise<void> {
  let actuelle = Number(await anim(p).getAttribute('data-etape'));
  while (actuelle !== n) {
    await (actuelle < n ? suivante(p) : precedente(p)).click();
    actuelle += actuelle < n ? 1 : -1;
    await expect(anim(p)).toHaveAttribute('data-etape', String(actuelle));
  }
}

/** La cible et la largeur posée de chaque barre. */
async function barres(p: Page): Promise<{ cible: string; largeur: string }[]> {
  return anim(p)
    .locator('[data-test="att-barre"]')
    .evaluateAll((bs) => bs.map((b) => ({ cible: (b as HTMLElement).dataset.cible ?? '', largeur: (b as HTMLElement).style.width })));
}

test('au clavier seul, jusqu’à la dernière étape', async ({ page }) => {
  await ouvrir(page);
  await expect(page.locator('#recap [data-acquis="attention"]')).toHaveAttribute('data-gagne', 'non');
  await expect(precedente(page)).toBeDisabled();
  const bouton = suivante(page);
  await bouton.focus();
  for (let i = 0; i < 5; i++) await page.keyboard.press('Enter');
  await expect(etat(page).filter({ hasText: 'Étape 6 sur 7' })).toBeVisible();
  // Pas d'acquis avant la septième étape.
  await expect(page.locator('#recap [data-acquis="attention"]')).toHaveAttribute('data-gagne', 'non');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status').filter({ hasText: 'Étape 7 sur 7' })).toBeVisible();
  await expect(bouton).toBeDisabled();
  // Le bouton désactivé garde le focus : le clavier ne se perd pas.
  await expect(bouton).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(anim(page)).toHaveAttribute('data-etape', '7');
  await expect(page.locator('#recap [data-acquis="attention"]')).toHaveAttribute('data-gagne', 'oui');
  // Et retour, au clavier aussi.
  await page.keyboard.press('Shift+Tab');
  await expect(precedente(page)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(anim(page)).toHaveAttribute('data-etape', '6');
});

test('au clavier, le mot et la tête se choisissent, avec un focus visible', async ({ page }) => {
  await ouvrir(page);
  // Les mots qui reviennent disent leur place aux lecteurs d'écran.
  await expect(mot(page, 3)).toHaveAccessibleName('le (mot 4)');
  await expect(mot(page, FORGERON)).toHaveAccessibleName('forgeron');
  await mot(page, 0).focus();
  await page.keyboard.press('Tab');
  await expect(mot(page, FORGERON)).toBeFocused();
  const contour = await mot(page, FORGERON).evaluate((el) => {
    const s = getComputedStyle(el);
    return { style: s.outlineStyle, largeur: parseFloat(s.outlineWidth) };
  });
  expect(contour.style).toBe('solid');
  expect(contour.largeur).toBeGreaterThanOrEqual(2);
  await page.keyboard.press('Space');
  await expect(mot(page, FORGERON)).toHaveAttribute('aria-pressed', 'true');
  await expect(mot(page, IL)).toHaveAttribute('aria-pressed', 'false');
  await expect(anim(page)).toHaveAttribute('data-requete', String(FORGERON));
  // Des mots à la première tête.
  for (let i = FORGERON + 1; i < N; i++) await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await expect(tete(page, QUI_AGIT)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(tete(page, QUI_AGIT)).toHaveAttribute('aria-pressed', 'true');
  await expect(tete(page, DE_QUI)).toHaveAttribute('aria-pressed', 'false');
  await expect(anim(page)).toHaveAttribute('data-tete', String(QUI_AGIT));
  // Puis les étapes : « Étape précédente » reste focalisable au début, mais ne fait rien.
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await expect(precedente(page)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(anim(page)).toHaveAttribute('data-etape', '1');
  await page.keyboard.press('Tab');
  await expect(suivante(page)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(anim(page)).toHaveAttribute('data-etape', '2');
  expect(await brut(etat(page))).toBe(
    `Étape 2 sur 7${F}: requête, clé, valeur. La requête de ${g('forgeron')} est nulle${F}: (0${F}; 0${F}; 0${F}; 0).`,
  );
  expect(D[QUI_AGIT].requetes[FORGERON]).toEqual([0, 0, 0, 0]);
});

test('les sept étapes, dans l’ordre, avec leur compteur et leur ligne d’état', async ({ page }) => {
  await ouvrir(page);
  for (let n = 1; n <= 7; n++) {
    await allerA(page, n);
    expect(await brut(anim(page).locator('[data-test="att-titre"]'))).toBe(ETAPES[n - 1]);
    expect(await brut(anim(page).locator('[data-test="att-compteur"]'))).toBe(`Étape ${n} sur 7`);
    expect(await brut(etat(page))).toMatch(new RegExp(`^Étape ${n} sur 7${F}: ${COURTS[n - 1]}[.] `));
    if (n === 1) await expect(precedente(page)).toBeDisabled();
    else await expect(precedente(page)).toBeEnabled();
    if (n === 7) await expect(suivante(page)).toBeDisabled();
    else await expect(suivante(page)).toBeEnabled();
  }
  // Étape 1 : le tableau des traits ; étape 2 : les vecteurs de « il » et la clé de chaque mot,
  // chaque tableau dans une zone nommée qui défile.
  await allerA(page, 1);
  await expect(anim(page).locator('[data-test="att-traits"] tbody tr')).toHaveCount(N);
  await expect(anim(page).locator('[data-test="att-traits"] tbody tr').first().locator('td')).toHaveCount(NB_TRAITS);
  await verifierZone(anim(page).getByRole('region', { name: 'Traits de chaque mot, défilable' }), 'att-traits');
  // La légende ne parle de la carte qu'avec la carte.
  expect((await legende(page).innerText()).trim()).toBe(LEGENDE_VECTEURS);
  await allerA(page, 2);
  await expect(anim(page).locator('[data-test="att-cles"] tbody tr')).toHaveCount(N);
  await verifierZone(anim(page).getByRole('region', { name: 'Clés de chaque mot, défilable' }), 'att-cles');
  await expect(anim(page).getByRole('table', { name: 'La clé k de chaque mot' })).toHaveCount(1);
  expect(await brut(anim(page).locator('.vecteurs dd').first())).toBe(`(${D[DE_QUI].requetes[IL].join(`${F}; `)})`);
  await allerA(page, 5);
  expect((await legende(page).innerText()).trim()).toBe(LEGENDE_VECTEURS);
  await allerA(page, 6);
  expect((await legende(page).innerText()).trim()).toBe(`${LEGENDE_VECTEURS} ${LEGENDE_CARTE}`);
});

test('« il » regarde « forgeron » dans la tête 2', async ({ page }) => {
  await ouvrir(page);
  const p = D[DE_QUI].poids[IL][FORGERON];
  // L'explication du pari donne le même pourcentage, calculé.
  await expect(page.locator('[data-pari="regard"] .explication')).toContainText(`il${F}» lui donne ${pourcentDe(p)} de son attention`);
  await expect(tete(page, DE_QUI)).toHaveAttribute('aria-pressed', 'true');
  await expect(mot(page, IL)).toHaveAttribute('aria-pressed', 'true');
  await allerA(page, 6);
  const b = barre(page, FORGERON);
  const cible = Number(await b.getAttribute('data-cible'));
  expect(cible).toBeGreaterThanOrEqual(60);
  expect(cible).toBe(Number((p * 100).toFixed(2)));
  expect(await brut(nombreDe(page, FORGERON))).toBe(pourcent(cible / 100));
  // C'est la plus longue barre.
  for (const { cible: autre } of (await barres(page)).filter((_, j) => j !== FORGERON)) expect(Number(autre)).toBeLessThan(cible);
  expect(await brut(etat(page))).toBe(`Étape 6 sur 7${F}: softmax. ${g('il')} donne ${pourcentDe(p)} de son attention à ${g('forgeron')}.`);
  // La barre finit de glisser à sa place.
  await expect(anim(page)).toHaveAttribute('data-mouvement', 'normal');
  await expect.poll(() => b.evaluate((el) => (el as HTMLElement).style.width)).toBe(`${cible}%`);
  // Étape 7 : la sortie (4 nombres) et la phrase calculée.
  await allerA(page, 7);
  expect(await brut(anim(page).locator('[data-test="att-phrase"]'))).toBe(
    `Sa nouvelle valeur vient surtout de ${g('forgeron')} (${pourcentDe(p)}).`,
  );
  const sortie = await brut(anim(page).locator('[data-test="att-sortie"] dd').first());
  expect(sortie.match(/-?\d+(,\d+)?/g)).toHaveLength(4);
});

test('le masque : à l’étape 5, les mots après « forgeron » sont masqués', async ({ page }) => {
  await ouvrir(page);
  await mot(page, FORGERON).click();
  await allerA(page, 4);
  for (let j = 0; j < N; j++) expect(await brut(nombreDe(page, j))).not.toBe('masqué');
  await allerA(page, 5);
  for (let j = 0; j < N; j++) {
    if (j > FORGERON) {
      expect(await brut(nombreDe(page, j))).toBe('masqué');
      await expect(barre(page, j)).toHaveAttribute('data-cible', '0');
    } else {
      expect(await brut(nombreDe(page, j))).toMatch(/^-?\d+(,\d+)?$/);
    }
  }
  await expect.poll(async () => (await barres(page)).slice(FORGERON + 1).every((b) => b.largeur === '0%')).toBe(true);
  expect(await brut(etat(page))).toBe(
    `Étape 5 sur 7${F}: le masque. ${g('forgeron')} voit les 2 premiers mots, lui compris${F}: les 7 suivants sont masqués.`,
  );
  // Dans l'autre tête aussi.
  await tete(page, QUI_AGIT).click();
  for (let j = FORGERON + 1; j < N; j++) expect(await brut(nombreDe(page, j))).toBe('masqué');
});

test('la carte complète : 9 lignes, 9 cases, cases masquées au-dessus de la diagonale', async ({ page }) => {
  await ouvrir(page);
  await expect(carte(page)).toBeHidden();
  await allerA(page, 5);
  await expect(carte(page)).toBeHidden();
  await allerA(page, 6);
  await expect(carte(page)).toBeVisible();
  const region = anim(page).getByRole('region', { name: 'Carte complète de la tête, défilable' });
  await expect(region).toHaveAttribute('tabindex', '0');
  await expect(region).toHaveCSS('overflow-x', 'auto');
  await expect(region.locator('[data-test="att-carte"]')).toHaveCount(1);
  expect(await brut(anim(page).locator('[data-test="att-carte-titre"]'))).toBe(`Tête 2${F}: de qui on parle. Les poids après le softmax, en pourcentage.`);
  await expect(carte(page).locator('thead th')).toHaveCount(N);
  // Le titre, hors de la zone qui défile, nomme le tableau.
  await expect(anim(page).getByRole('table', { name: /^Tête 2.*de qui on parle\. Les poids après le softmax/ })).toHaveCount(1);

  /** Le texte de chaque case, ligne par ligne. */
  const cases = () =>
    carte(page)
      .locator('tbody tr')
      .evaluateAll((lignes) => lignes.map((l) => [...l.querySelectorAll('td')].map((c) => (c.textContent ?? '').trim())));
  const verifierCases = async (t: number) => {
    const texte = await cases();
    expect(texte).toHaveLength(N);
    texte.forEach((ligne, i) => {
      expect(ligne).toHaveLength(N);
      ligne.forEach((c, j) => {
        if (j > i) expect(c).toBe('—masqué');
        else expect(c).toBe(pourcentDe(D[t].poids[i][j]));
      });
    });
  };
  await verifierCases(DE_QUI);
  // « il » → « forgeron » : fond foncé, texte papier ; une case au poids nul ou presque : texte indigo.
  const caseIlForgeron = carte(page).locator('tbody tr').nth(IL).locator('td').nth(FORGERON);
  await expect(caseIlForgeron).toHaveClass(/claire/);
  await expect(carte(page).locator('tbody tr').nth(IL).locator('td').nth(0)).not.toHaveClass(/claire/);

  // L'autre tête : « chauffe » regarde « forgeron ».
  await tete(page, QUI_AGIT).click();
  expect(await brut(anim(page).locator('[data-test="att-carte-titre"]'))).toBe(`Tête 1${F}: qui agit. Les poids après le softmax, en pourcentage.`);
  await verifierCases(QUI_AGIT);
  expect(D[QUI_AGIT].poids[CHAUFFE][FORGERON]).toBeGreaterThan(0.5);
  // À l'étape 7 aussi, puis plus avant l'étape 6.
  await allerA(page, 7);
  await expect(carte(page)).toBeVisible();
  await allerA(page, 5);
  await expect(carte(page)).toBeHidden();
});

test('mouvement réduit : les barres prennent leur valeur tout de suite', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await ouvrir(page);
  await expect(page.locator('[data-mouvement]')).toHaveAttribute('data-mouvement', 'reduit');
  // Aller à l'étape 6, puis, sans attendre :
  for (let i = 0; i < 5; i++) await suivante(page).click();
  const b = barre(page, FORGERON);
  const { cible, largeur } = await b.evaluate((el) => ({ cible: (el as HTMLElement).dataset.cible, largeur: (el as HTMLElement).style.width }));
  expect(largeur).toBe(`${cible}%`);
  // Toutes les barres, après chaque geste : changer de tête, de mot, d'étape.
  for (const geste of [() => tete(page, QUI_AGIT).click(), () => mot(page, CHAUFFE).click(), () => precedente(page).click()]) {
    await geste();
    for (const { cible: c, largeur: l } of await barres(page)) expect(l).toBe(`${c}%`);
  }
});

test('sans JavaScript : la carte est lisible', async ({ browser, baseURL }, info) => {
  // Le contexte reprend la fenêtre du projet (390 px sur mobile) : la carte y défile.
  const { viewport, deviceScaleFactor, isMobile } = info.project.use;
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL, viewport, deviceScaleFactor, isMobile });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  const a = anim(page);
  // Pas de commandes, une phrase à leur place.
  await expect(a.locator('[data-test="att-suivante"]')).toBeHidden();
  await expect(a.locator('[data-test="att-mot"]').first()).toBeHidden();
  await expect(a.getByText('Sans JavaScript, l’animation reste à sa première étape')).toBeVisible();
  // L'étape 1, avec le tableau des traits.
  expect(await brut(a.locator('[data-test="att-titre"]'))).toBe(ETAPES[0]);
  await expect(a.locator('[data-test="att-traits"]')).toBeVisible();
  expect(await brut(a.getByRole('status'))).toBe(
    `Étape 1 sur 7${F}: les traits. ${g('il')} a 3 traits sur 8${F}: pronom, sujet et personne.`,
  );
  // La carte complète de la tête 2, lisible.
  await expect(carte(page)).toBeVisible();
  expect(await brut(anim(page).locator('[data-test="att-carte-titre"]'))).toBe(`Tête 2${F}: de qui on parle. Les poids après le softmax, en pourcentage.`);
  await expect(carte(page).locator('tbody tr')).toHaveCount(N);
  const caseIl = carte(page).locator('tbody tr').nth(IL).locator('td').nth(FORGERON);
  await expect(caseIl).toBeVisible();
  expect(await brut(caseIl)).toBe(pourcentDe(D[DE_QUI].poids[IL][FORGERON]));
  expect((await legende(page).innerText()).trim()).toBe(`${LEGENDE_VECTEURS} ${LEGENDE_CARTE}`);
  // Sur un téléphone, la phrase qui invite à faire défiler la carte est là aussi, et rien ne déborde.
  const indice = a.locator('[data-test="att-indice-defile"]');
  if (viewport!.width <= LARGEUR_CARTE_DEFILE) {
    await expect(indice).toBeVisible();
    const m = await defilement(regionCarte(page));
    expect(m.total).toBeGreaterThan(m.visible);
  } else {
    await expect(indice).toBeHidden();
  }
  await verifierSansDebordement(page);
  // Les réponses des paris aussi.
  await expect(page.locator('[data-pari="regard"] .verdict')).toBeVisible();
  await ctx.close();
});

test('accessibilité, largeur, typographie aux étapes 6 et 7', async ({ page }) => {
  await ouvrir(page);
  // Au départ, et à l'étape 2 (vecteurs et tableau des clés).
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(anim(page));
  await allerA(page, 2);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographie(anim(page));
  // Aucun débordement aux étapes des barres non plus.
  for (const n of [3, 4, 5]) {
    await allerA(page, n);
    await verifierSansDebordement(page);
  }
  for (const n of [6, 7]) {
    await allerA(page, n);
    await verifierAxe(page);
    await verifierSansDebordement(page);
    await verifierTypographie(anim(page));
  }
  // Une requête nulle, et l'autre tête.
  await mot(page, 5).click();
  await tete(page, QUI_AGIT).click();
  await verifierAxe(page);
  await verifierTypographie(anim(page));
  await verifierTypographie(page.locator('main'));
  // Des cibles d'au moins 24 px sur 24 px.
  for (const bouton of await anim(page).locator('button').all()) {
    const boite = (await bouton.boundingBox())!;
    expect(boite.height, await bouton.innerText()).toBeGreaterThanOrEqual(24);
    expect(boite.width, await bouton.innerText()).toBeGreaterThanOrEqual(24);
  }
  // La ligne d'état n'a jamais pris le focus.
  await expect(etat(page)).not.toBeFocused();
});

test('la carte défile au clavier, sans faire déborder la page', async ({ page }) => {
  await ouvrir(page);
  await allerA(page, 6);
  const region = regionCarte(page);
  await verifierZone(region, 'att-carte');
  const indice = anim(page).locator('[data-test="att-indice-defile"]');
  const avant = await defilement(region);
  if (page.viewportSize()!.width > LARGEUR_CARTE_DEFILE) {
    // Sur ordinateur, la carte tient dans la colonne : rien à faire défiler, pas de phrase.
    expect(avant.total).toBeLessThanOrEqual(avant.visible);
    await expect(indice).toBeHidden();
    return;
  }
  // Sur un téléphone, elle est plus large que sa zone…
  expect(avant.total).toBeGreaterThan(avant.visible);
  expect(avant.gauche).toBe(0);
  await expect(indice).toBeVisible();
  expect(await brut(indice)).toBe('Fais défiler la carte vers la droite pour voir les autres colonnes.');
  // … et une colonne est coupée au bord droit : on en voit le début, pas la fin.
  const bord = (await region.boundingBox())!;
  const droite = bord.x + bord.width;
  const colonnes = await carte(page)
    .locator('thead th')
    .evaluateAll((ths) => ths.map((th) => ({ gauche: th.getBoundingClientRect().left, fin: th.getBoundingClientRect().right })));
  const coupee = colonnes.find((c) => c.gauche < droite && c.fin > droite);
  expect(coupee, 'une colonne à cheval sur le bord droit').toBeDefined();
  expect(droite - coupee!.gauche, 'partie visible de la colonne coupée').toBeGreaterThanOrEqual(10);
  expect(coupee!.fin - droite, 'partie cachée de la colonne coupée').toBeGreaterThanOrEqual(5);
  // Au clavier : la flèche droite fait défiler la zone, et la page ne déborde toujours pas.
  await region.focus();
  await expect(region).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect.poll(async () => (await defilement(region)).gauche).toBeGreaterThan(0);
  await verifierSansDebordement(page);
  // La colonne des mots reste en place pendant le défilement.
  const premierMot = (await carte(page).locator('tbody th').first().boundingBox())!;
  expect(Math.abs(premierMot.x - bord.x)).toBeLessThanOrEqual(1);
  // Jusqu'au bout, toujours à la flèche droite : la dernière colonne devient visible.
  const auBout = async () => {
    const m = await defilement(region);
    return m.gauche + m.visible >= m.total - 1;
  };
  for (let i = 0; i < 30 && !(await auBout()); i++) await page.keyboard.press('ArrowRight');
  await expect.poll(auBout).toBe(true);
  const derniere = (await carte(page).locator('thead th').last().boundingBox())!;
  expect(derniere.x + derniere.width).toBeLessThanOrEqual(droite + 1);
  await verifierSansDebordement(page);
});
