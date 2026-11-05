// Parcours du chapitre 0.3, « Installer son poste » : un brouillon
// (src/brouillons/chapitres/0-3.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1. Le chapitre n'a pas d'îlot : son
// atelier, c'est le terminal du lecteur et le script `python -m poste`.
//
// Les attendus viennent des fichiers du projet lus sur le disque (le
// diagnostic, tests/attendus.json, et la sortie enregistrée sur ce PC,
// sorties/processeur.txt), des commandes (commandes.ts), des données du
// calculateur et des faits sourcés du chapitre (sources-0-3.ts). Un parcours,
// chargé par Node sans Vite, n'importe aucun module à ?raw, .json ou astro:*
// (B1) : il n'importe ni poste.ts ni paris-0-3.ts, qui lisent le fichier
// d'attendus par un import. Les choix des paris sont donc écrits ici en toutes
// lettres, et rapprochés des attendus et des mesures.
import { existsSync, readFileSync } from 'node:fs';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { materiel } from '../src/lib/calculateur/donnees';
import { MESURES_TON_IA } from '../src/lib/calculateur/ton-ia';
import { nombre } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { extraireRegion } from '../src/lib/regions';
import { lireSortie } from '../src/lib/sorties';
import { typographier } from '../src/lib/typo';
import * as commandes from '../src/lib/partie-0/commandes';
import {
  ligneDuRapport,
  lignesDesSituations,
  NOMS_DES_SITUATIONS,
  texteDesMorceaux,
  trouverSituation,
  type AttendusPoste,
} from '../src/lib/partie-0/situations-0-3';
import { CARTES_LLAMA_3_405B, SOURCES_0_3 } from '../src/lib/partie-0/sources-0-3';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-3/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/0.3-poste/tests/attendus.json', 'utf8')) as AttendusPoste;
const FICHIER_PROCESSEUR = 'projets/0.3-poste/sorties/processeur.txt';
const FICHIER_CARTE = 'projets/0.3-poste/sorties/rtx-5070-ti.txt';
const SORTIE_PROCESSEUR = readFileSync(`../${FICHIER_PROCESSEUR}`, 'utf8');

/** Les titres des huit étapes, dans l'ordre. */
const TITRES = [
  'Pourquoi une carte graphique',
  'Le pilote, et rien d’autre',
  'Installer uv',
  'Le projet et sa version de PyTorch',
  'Vérifier',
  'Quand ça ne marche pas',
  'Le processeur, Colab, Linux et Mac',
  'À grande échelle',
];

/** Les paris, dans l'ordre de la page : leurs choix en toutes lettres, et le juste. */
const RAPPORT = Math.round(MESURES_TON_IA.tres_grand.carte.jetonsParSeconde / MESURES_TON_IA.tres_grand.processeur.jetonsParSeconde);
const PARIS: [string, string[], number][] = [
  ['vitesse', ['2 fois', '10 fois', `${RAPPORT} fois`], 2],
  ['pypi', ['Oui, la carte calcule', "Non : c'est la version pour processeur", "PyTorch refuse de s'importer"], 1],
  ['trop-recente', ['Tout marche', 'La carte est trop récente pour cette version', 'Le pilote est trop ancien'], 1],
];

/** Les commandes que les blocs « À taper » du chapitre montrent, dans l'ordre de la page. */
const COMMANDES_DES_BLOCS = [
  [commandes.NVIDIA_SMI],
  [commandes.INSTALLER_UV_WINDOWS, commandes.VERIFIER_UV],
  [commandes.INSTALLER_UV_LINUX_MAC],
  [commandes.CLONER_DEPOT, commandes.ALLER_AU_PROJET_0_3],
  [commandes.VERIFIER_POSTE_GPU],
  [commandes.VERIFIER_POSTE_CPU],
];

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(zone: Locator): Promise<string> {
  return (await zone.textContent()) ?? '';
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Le pied vers un voisin : un lien s'il a paru (son fichier est dans src/content/chapitres/), sinon « à venir » (S2). */
async function verifierVoisin(page: Page, sens: 'precedent' | 'suivant', fichier: string, href: string): Promise<void> {
  const voisin = page.locator(`footer .voisin.${sens}`);
  if (existsSync(`src/content/chapitres/${fichier}`)) {
    await expect(voisin).toHaveAttribute('href', href);
  } else {
    await expect(voisin).toContainText('à venir');
    await expect(page.locator(`footer a.voisin.${sens}`)).toHaveCount(0);
  }
}

test('chapitre 0.3 complet', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('0.3');
  await expect(page.locator('header')).toContainText(`Partie 0, chapitre 0.3 sur ${total}`);
  // Huit étapes, dans l'ordre, trois paris et trois acquis.
  const titres = page.locator('.etape h2');
  await expect(titres).toHaveCount(TITRES.length);
  expect(await titres.evaluateAll((h) => h.map((e) => e.textContent))).toEqual(TITRES.map(typographier));
  await expect(page.locator('[data-pari]')).toHaveCount(PARIS.length);
  await expect(page.locator('#recap [data-acquis]')).toHaveCount(3);

  // Avant le pari de l'étape 6, le tableau des situations est verrouillé.
  await expect(page.locator('[data-verrou="situations"]')).toHaveAttribute('inert', '');
  for (const [id] of PARIS) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  await expect(page.locator('[data-verrou="situations"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#recap [data-gagne="oui"]')).toHaveCount(3);
  await expect(page.locator('#recap [data-total]')).toContainText('3 sur 3');

  // Le pied suit les fichiers : 0.2 a paru, 0.4 est « à venir » tant qu'il n'a pas paru (S2).
  await verifierVoisin(page, 'precedent', '0-2.mdx', '/forge-ia/partie-0/0-2/');
  await verifierVoisin(page, 'suivant', '0-4.mdx', '/forge-ia/partie-0/0-4/');
  // Aucun lien vers un chapitre qui n'a pas paru (S3) : le renvoi à 0.4 est du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);

  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('les choix des paris viennent des mesures et des attendus', async ({ page }) => {
  await page.goto(PAGE);
  // Le rapport des débits mesurés de la plus grande taille : 17 855 contre 235 jetons par seconde.
  expect(RAPPORT).toBe(76);
  // Les paires du chapitre : PyPI donne la version pour processeur, l'ancienne version pour CUDA 12.6
  // ne connaît pas la RTX 5070 Ti.
  const cles = (nom: string) => trouverSituation(ATTENDUS, nom).constats.map((c) => c.cle);
  expect(cles('windows_pypi_rtx5070ti')).toEqual(['roue_processeur']);
  expect(cles('windows_cu126_rtx5070ti')).toEqual(['carte_trop_recente']);
  for (const [id, choix, rang] of PARIS) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(typographier));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(typographier(choix[rang]));
  }
  // La question du dernier pari nomme la version de l'ancien tutoriel, lue dans les attendus.
  const ancienne = trouverSituation(ATTENDUS, 'windows_cu126_rtx5070ti').faits.torch!;
  expect(await texteExact(page.locator('[data-pari="trop-recente"] .q'))).toContain(ancienne);
});

test('l’ouverture est la ligne du diagnostic quand la carte est prête', async ({ page }) => {
  await page.goto(PAGE);
  const prete = trouverSituation(ATTENDUS, 'windows_cu132_rtx5070ti').constats[0];
  expect(prete.cle).toBe('carte_prete');
  expect(await texteExact(page.locator('[data-test="ouverture-ligne"]'))).toBe(ligneDuRapport(prete).trim());
  await expect(page.locator('[data-test="ouverture"] .commande')).toHaveText(commandes.VERIFIER_POSTE_GPU);
  // Le jour où la sortie de la carte est relevée (tâche 16), elle doit contenir cette ligne.
  if (existsSync(`../${FICHIER_CARTE}`)) {
    expect(readFileSync(`../${FICHIER_CARTE}`, 'utf8').split('\n')).toContain(ligneDuRapport(prete));
  }
});

test('le tableau des situations est celui des attendus', async ({ page }) => {
  await page.goto(PAGE);
  // Une situation par groupe de lignes (tbody), une ligne par constat.
  const groupes = page.locator('[data-test="situations"] tbody');
  await expect(groupes).toHaveCount(NOMS_DES_SITUATIONS.length);
  const attendues = lignesDesSituations(ATTENDUS);
  for (const [i, [nom, s]] of ATTENDUS.situations.entries()) {
    const groupe = groupes.nth(i);
    await expect(groupe).toHaveAttribute('data-situation', nom);
    await expect(groupe.locator('tr'), nom).toHaveCount(s.constats.length);
    await expect(groupe.locator('th'), nom).toHaveAttribute('rowspan', String(s.constats.length));
    expect(await texteExact(groupe.locator('th')), nom).toBe(texteDesMorceaux(attendues[i].situation));
    const dit = await groupe.locator('[data-colonne="dit"] p').evaluateAll((p) => p.map((e) => e.textContent ?? ''));
    const faire = await groupe.locator('[data-colonne="faire"] p').evaluateAll((p) => p.map((e) => e.textContent ?? ''));
    // Les messages du Python, mot pour mot : seuls les accents graves deviennent du code.
    expect(dit, nom).toEqual(s.constats.map((c, j) => `${attendues[i].constats[j].niveau}${FINE}: ${c.message.replaceAll('`', '')}`));
    expect(faire, nom).toEqual(s.constats.map((c) => (c.a_faire === null ? 'Rien à faire.' : c.a_faire.replaceAll('`', ''))));
  }
  // Les commandes conseillées sont du code, qui ne se coupe qu'entre ses mots.
  const sync = page.locator('[data-situation="windows_pypi_rtx5070ti"] [data-colonne="faire"] code').first();
  await expect(sync).toHaveText(commandes.SYNC_GPU);
  await expect(sync.locator('.mot').first()).toHaveCSS('white-space', 'nowrap');
  // Colab : ni le pilote ni les fils d'exemple, qui ne sont pas sourcés.
  const colab = trouverSituation(ATTENDUS, 'colab_t4').faits;
  const ligneColab = await texteExact(page.locator('[data-situation="colab_t4"]'));
  expect(ligneColab).toContain(colab.torch!);
  expect(ligneColab).not.toContain(colab.pilote!);
  expect(ligneColab).not.toContain('fils');
});

test('les sorties : celle du processeur est le fichier, celle de la carte reste à mesurer', async ({ page }) => {
  await page.goto(PAGE);
  const sortie = page.locator(`[data-sortie="${FICHIER_PROCESSEUR}"]`);
  await expect(sortie).toHaveCount(1);
  const lue = lireSortie(SORTIE_PROCESSEUR, FICHIER_PROCESSEUR)!;
  // Le fichier sans sa première ligne « # relevé le … », caractère pour caractère.
  expect(SORTIE_PROCESSEUR.split('\n')[0]).toBe('# relevé le 2026-11-05');
  expect(await texteExact(sortie.locator('[data-contenu]'))).toBe(SORTIE_PROCESSEUR.replace(/^[^\n]*\n/, '').replace(/\n+$/, ''));
  expect(await texteExact(sortie.locator('[data-contenu]'))).toBe(lue.contenu);
  await expect(sortie.locator('figcaption')).toContainText('relevée le 5');
  await expect(sortie.locator('.commande')).toHaveText(commandes.VERIFIER_POSTE_CPU);
  // Une seule valeur à mesurer : la sortie de la carte, relevée à la porte (tâche 16).
  const aMesurer = page.locator('[data-a-mesurer]');
  if (existsSync(`../${FICHIER_CARTE}`)) {
    await expect(aMesurer).toHaveCount(0);
    await expect(page.locator(`[data-sortie="${FICHIER_CARTE}"]`)).toHaveCount(1);
  } else {
    await expect(aMesurer).toHaveCount(1);
    expect(await texteExact(aMesurer)).toBe(
      typographier('La sortie sur la RTX 5070 Ti s’affichera ici : on la relève quand la carte sera libre.'),
    );
  }
});

test('les commandes affichées sont celles de commandes.ts', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page
    .locator('.bloc-commande pre code')
    .evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual(COMMANDES_DES_BLOCS);
  // Les commandes après l'invite des sorties, et celles citées dans le texte, viennent aussi de commandes.ts.
  const connues = new Set(Object.values(commandes));
  for (const commande of await page.locator('.sortie .commande, [data-test="ouverture"] .commande').allTextContents()) {
    expect(connues, commande).toContain(commande);
  }
  for (const code of await page.locator('.etape .texte p code').allTextContents()) {
    if (/^(uv (sync|run) |pip |conda |winget |git clone |cd )/.test(code)) expect(connues, code).toContain(code);
  }
  await expect(page.locator('.etape .texte p code', { hasText: commandes.SYNC_CPU })).not.toHaveCount(0);
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const regions: [string, string][] = [
    ['projets/0.3-poste/pyproject.toml', 'pytorch'],
    ['projets/0.3-poste/poste/diagnostic.py', 'diagnostiquer'],
    ['projets/0.3-poste/poste/appareil.py', 'appareil'],
  ];
  const blocs = page.locator('.code-explique');
  await expect(blocs).toHaveCount(regions.length);
  // La région « diagnostiquer » finit par deux lignes vides (avant « # fin: diagnostiquer »), que la
  // coloration ne garde pas toutes : on compare sans les lignes vides de la fin.
  const sansLignesVidesALaFin = (code: string | null) => (code ?? '').replace(/\n+$/, '');
  for (const [i, [fichier, region]] of regions.entries()) {
    const attendu = extraireRegion(readFileSync(`../${fichier}`, 'utf8'), region, fichier);
    const affiche = await blocs.nth(i).locator('pre').evaluate((pre) => pre.textContent);
    expect(sansLignesVidesALaFin(affiche), region).toBe(sansLignesVidesALaFin(attendu));
    await expect(blocs.nth(i).locator('figcaption a')).toHaveAttribute(
      'href',
      `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`,
    );
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/0.3-poste',
  );
  await expect(page.getByRole('link', { name: 'Ouvrir dans Colab' })).toHaveAttribute(
    'href',
    'https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/0.3-poste.ipynb',
  );
});

test('les faits de la recherche portent leur source, et l’encadré vient des données', async ({ page }) => {
  await page.goto(PAGE);
  // Chaque source du chapitre a son lien sur la page, et une date de vérification à côté.
  const liens = await page.locator('main a').evaluateAll((a) => a.map((e) => e.getAttribute('href')));
  for (const source of Object.values(SOURCES_0_3).flat()) expect(liens, source.titre).toContain(source.url);
  for (const note of await page.locator('.sources-poste').allTextContents()) expect(note).toMatch(/vérifiées? le \d/);
  // La mesure de l'étape 1 renvoie au rapport de mesure du dépôt.
  expect(liens).toContain(MESURES_TON_IA.tres_grand.source.url);

  // L'encadré : jusqu'à 16 384 H100 pour Llama 3 405B, puis les cartes, mémoire et calcul, depuis MATERIELS.
  const labo = page.locator('#etape-8 .labo');
  expect(await texteExact(labo)).toContain(`${nombre(CARTES_LLAMA_3_405B)} cartes H100`);
  const cartes = labo.locator('[data-test="cartes"] tbody tr');
  const ids = ['t4', 'rtx-5070-ti', 'h100-sxm'];
  await expect(cartes).toHaveCount(ids.length);
  for (const [i, id] of ids.entries()) {
    const m = materiel(id);
    const cellules = await cartes.nth(i).locator('th, td').evaluateAll((c) => c.map((e) => e.textContent ?? ''));
    expect(cellules, id).toEqual([m.nom, `${nombre(m.memoireGo)} Go`, nombre(m.creteTflops, Number.isInteger(m.creteTflops) ? 0 : 1)]);
  }
});

test('les zones de terminal défilent dans leur zone, sans faire déborder la page', async ({ page }) => {
  await page.goto(PAGE);
  const zones = page.locator('.bloc-terminal .zone-defilable');
  expect(await zones.count()).toBeGreaterThanOrEqual(COMMANDES_DES_BLOCS.length + 1);
  for (const zone of await zones.all()) await expect(zone).toHaveCSS('overflow-x', 'auto');
  // La sortie du processeur a des lignes plus longues que la colonne : sa zone défile en largeur.
  const sortie = page.locator(`[data-sortie="${FICHIER_PROCESSEUR}"] .zone-defilable`);
  const { large, visible } = await sortie.evaluate((z) => ({ large: z.scrollWidth, visible: z.clientWidth }));
  expect(large).toBeGreaterThan(visible);
  await verifierSansDebordement(page);
});

test('sans JavaScript, tout le chapitre se lit', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(page.locator('[data-test="ouverture"]')).toBeVisible();
  // Pas de verrou : le tableau des situations est là, net.
  await expect(page.locator('[data-verrou="situations"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="situations"]')).toBeVisible();
  // Les explications des trois paris sont données d'emblée.
  for (const [id] of PARIS) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator(`[data-sortie="${FICHIER_PROCESSEUR}"]`)).toBeVisible();
  await expect(page.locator('#etape-8 .labo')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
