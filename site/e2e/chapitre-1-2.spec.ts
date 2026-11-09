// Parcours du chapitre 1.2, « Les données » : un brouillon
// (src/brouillons/chapitres/1-2.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau du nettoyage (src/lib/partie-1/nettoyeur.ts)
// et des paris (paris-1-2.ts), appliqués aux exemples et à l'aperçu du projet
// 1.2, lus sur le disque : un parcours, chargé par Node sans Vite, n'importe ni
// ?raw, ni .json, ni astro:* (P8).
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import type { Choix } from '../src/lib/choix';
import { ANNEXES, trouverChapitre } from '../src/lib/parcours';
import { MESURES_PARTIE_1 } from '../src/lib/partie-1/mesures';
import { empreinte, longueurPointsDeCode, normaliser } from '../src/lib/partie-1/nettoyeur';
import {
  choixCourt,
  choixDoublon,
  choixLicence,
  choixPartGardee,
  choixValidation,
  coteDuTexte,
  CONTROLE_RETIRE,
  etatDuNettoyage,
  lireJsonl,
  messageDoublon,
  phraseLongueur,
  RETOUR_CHARIOT,
  verdictDuTexte,
  versWindows,
  type Apercu,
} from '../src/lib/partie-1/paris-1-2';
import { extraireRegion } from '../src/lib/regions';
import { extraireSymbole } from '../src/lib/symboles';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation,
  plusLongueLigne,
  texteHorsCode,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
  verifierVoisin,
} from './outils';

const PAGE = '/forge-ia/partie-1/1-2/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const PROJET = '../projets/1.2-donnees';
const WEB = lireJsonl(readFileSync(`${PROJET}/exemples/web.jsonl`, 'utf8'));
const CODE = lireJsonl(readFileSync(`${PROJET}/exemples/code.jsonl`, 'utf8'));
const APERCU = JSON.parse(readFileSync(`../${MESURES_PARTIE_1.apercu}`, 'utf8')) as Apercu;
const texteDe = (i: number): string => WEB[i].text as string;
/** Le texte écrit dans l'atelier à l'arrivée : le deuxième exemple du web. */
const INITIAL = texteDe(1);

// Ce qui n'est pas du texte du chapitre mais des données brutes : les champs de
// l'atelier, le texte nettoyé (les exemples gardent leurs apostrophes droites),
// et les citations d'exemples dans les paris.
const BRUT = 'textarea, [data-test="nt-nettoye"], [data-brut]';

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(page: Page, selecteur: string): Promise<string> {
  return (await page.locator(selecteur).textContent()) ?? '';
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Le texte d'un choix tel qu'un bouton l'affiche : le code tel quel, le reste typographié. */
function affiche(choix: Choix): string {
  return choix.texte
    .split('`')
    .map((morceau, i) => (i % 2 === 1 ? morceau : typographier(morceau)))
    .join('');
}

/** Ouvre la page et fait le pari de l'étape 4, qui ouvre l'atelier. */
async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="court"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
}

/** Ce que montre le texte nettoyé de l'atelier : les morceaux gardés, et les retraits à part. */
async function nettoyeAffiche(page: Page): Promise<{ gardes: string; retraits: string }> {
  return page.locator('[data-test="nt-nettoye"]').evaluate((pre) => {
    let gardes = '';
    let retraits = '';
    // Les nœuds de texte sont le texte gardé, les éléments marqués data-retrait les retraits ;
    // les commentaires que Svelte pose pour l'hydratation ne comptent pas.
    for (const n of pre.childNodes) {
      if (n.nodeType === Node.TEXT_NODE) gardes += n.textContent ?? '';
      else if (n instanceof HTMLElement && n.dataset.retrait !== undefined) retraits += n.textContent ?? '';
    }
    return { gardes, retraits };
  });
}

/** Vérifie tout ce que l'atelier dit du premier texte, face au jumeau (le brut tient compte des fins de ligne). */
async function verifierTexte(page: Page, brut: string): Promise<void> {
  const etat = etatDuNettoyage(brut);
  const e = await empreinte(brut);
  const nom = JSON.stringify(brut.slice(0, 40));
  await expect(page.locator('[data-test="nt-empreinte"]'), nom).toHaveText(e.slice(0, 8));
  await expect(page.locator('[data-test="nt-empreinte"]'), nom).not.toHaveAttribute('data-en-cours', 'oui');
  expect(await texteExact(page, '[data-test="nt-longueur"]'), nom).toBe(`${phraseLongueur(longueurPointsDeCode(normaliser(brut)))}.`);
  expect(await texteExact(page, '[data-test="nt-verdict"]'), nom).toBe(verdictDuTexte(etat));
  expect(await texteExact(page, '[data-test="nt-cote"]'), nom).toBe(coteDuTexte(etat, e));
  expect((await nettoyeAffiche(page)).gardes, nom).toBe(normaliser(brut));
}

test('chapitre 1.2 complet', async ({ page }, info) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('1.2');
  expect(total).toBe(21);
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.2 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  await expect(page.locator('.pari[data-pari]')).toHaveCount(5);
  await page.locator('[data-pari="licence"] [data-juste]').click();
  await page.locator('[data-pari="court"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // Modifier le texte de l'atelier fait gagner son acquis.
  await page.locator('[data-test="nt-texte"]').fill(`${INITIAL} Fin.`);
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-pari="doublon"] [data-juste]').click();
  await page.locator('[data-pari="validation"] [data-juste]').click();
  await page.locator('[data-pari="part"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('6 sur 6');
  // Le pied suit les fichiers : 1.1 et 1.3 ont paru.
  await verifierVoisin(page, 'precedent', '1-1.mdx', '/forge-ia/partie-1/1-1/');
  await verifierVoisin(page, 'suivant', '1-3.mdx', '/forge-ia/partie-1/1-3/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  // Aucune expression du MDX restée en texte (une accolade tombée dans un passage de code, par exemple).
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/[{}]/);
  expect(await page.locator('main code').allTextContents()).not.toContainEqual(expect.stringMatching(/[{}]/));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('les choix des paris viennent du jumeau', async ({ page }) => {
  await page.goto(PAGE);
  const paris: [string, Choix[]][] = [
    ['licence', choixLicence(CODE[1])],
    ['court', choixCourt(texteDe(0))],
    ['doublon', await choixDoublon(texteDe(1), texteDe(2))],
    ['validation', await choixValidation(WEB)],
    ['part', choixPartGardee(APERCU)],
  ];
  for (const [id, choix] of paris) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(affiche(choix.find((c) => c.juste)!));
  }
  // Le fichier GPL-3.0 des exemples : écarté, et la bonne réponse le dit.
  expect(CODE[1].license).toBe('gpl-3.0');
  await expect(page.locator('[data-pari="licence"] [data-juste]')).toContainText('n’est pas dans la liste');
  // L'ouverture : les trois sources, dans l'ordre du mélange, avec leur part.
  await expect(page.locator('[data-test="ouverture"] [data-source]')).toHaveCount(3);
  // Le tableau des sources : une ligne par source, et aucun lien vers l'annuaire tant qu'il n'a pas paru.
  await expect(page.locator('[data-test="sources"] tbody tr')).toHaveCount(3);
  const annuaire = ANNEXES.find((a) => a.titre.startsWith('Annuaire'));
  expect(annuaire).toBeDefined();
  if (annuaire!.href === undefined) await expect(page.locator('[data-test="sources"] a[data-annuaire]')).toHaveCount(0);
  else await expect(page.locator('[data-test="sources"] a[data-annuaire]').first()).toHaveAttribute('href', annuaire!.href);
});

test('le code affiché est celui des symboles et des régions testés', async ({ page }) => {
  await page.goto(PAGE);
  const forge = 'projets/forge/forge/donnees';
  const blocs: [string, 'symbole' | 'region', string][] = [
    [`${forge}/sources.py`, 'symbole', '_garder_python_permissif'],
    [`${forge}/nettoyage.py`, 'symbole', '_normaliser'],
    [`${forge}/nettoyage.py`, 'symbole', 'nettoyer'],
    [`${forge}/nettoyage.py`, 'symbole', 'empreinte_du_texte_nettoye'],
    ['projets/1.2-donnees/donnees_pas_a_pas/trier.py', 'region', 'doublons'],
    [`${forge}/melange.py`, 'symbole', 'est_validation'],
  ];
  const codes = page.locator('.code-explique');
  await expect(codes).toHaveCount(blocs.length);
  for (const [i, [fichier, sorte, nom]] of blocs.entries()) {
    const source = readFileSync(`../${fichier}`, 'utf8');
    const attendu = sorte === 'region' ? extraireRegion(source, nom, fichier) : extraireSymbole(source, nom, fichier, { docstring: false });
    expect(await codes.nth(i).locator('pre').evaluate((pre) => pre.textContent), nom).toBe(attendu);
    await expect(codes.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.2-donnees',
  );
});

test('atelier : 199 puis 200 caractères, \\r\\n contre \\n, contrôles, emoji', async ({ page }) => {
  await ouvrirAtelier(page);
  const champ = page.locator('[data-test="nt-texte"]');
  const windows = page.locator('[data-test="nt-fins-windows"]');
  const unix = page.locator('[data-test="nt-fins-unix"]');

  // À l'arrivée : le deuxième exemple, écrit sous Windows. Chaque \r retiré se voit (␍).
  await expect(champ).toHaveValue(INITIAL);
  await expect(windows).toHaveAttribute('aria-pressed', 'true');
  await verifierTexte(page, versWindows(INITIAL));
  const retours = (INITIAL.match(/\n/g) ?? []).length;
  expect(retours).toBeGreaterThan(0);
  expect((await nettoyeAffiche(page)).retraits).toBe(RETOUR_CHARIOT.repeat(retours));
  const avecWindows = await texteExact(page, '[data-test="nt-empreinte"]');

  // Les mêmes lignes, finies par \n : plus de retrait, et la même empreinte.
  await unix.click();
  await expect(unix).toHaveAttribute('aria-pressed', 'true');
  await verifierTexte(page, INITIAL);
  expect((await nettoyeAffiche(page)).retraits).toBe('');
  expect(await texteExact(page, '[data-test="nt-empreinte"]')).toBe(avecWindows);
  await windows.click();

  // 199 caractères : écarté ; 200 : gardé (les lignes 10 et 9 des exemples).
  await champ.fill(texteDe(9));
  await verifierTexte(page, versWindows(texteDe(9)));
  expect(await texteExact(page, '[data-test="nt-longueur"]')).toBe(`199 caractères sur les 200 qu’il faut.`);
  expect(await texteExact(page, '[data-test="nt-verdict"]')).toBe(`Écarté${FINE}: trop court, il manque 1 caractère.`);
  await champ.fill(texteDe(8));
  await verifierTexte(page, versWindows(texteDe(8)));
  expect(await texteExact(page, '[data-test="nt-verdict"]')).toBe(`Gardé${FINE}: il a au moins 200 caractères.`);
  await expect.poll(() => texteExact(page, '[data-test="nt-annonce"]')).toBe(`Gardé${FINE}: il a au moins 200 caractères.`);

  // Des contrôles collés dans le texte, et des blancs en fin : chacun devient un · en encre douce.
  const sale = `Un bip\u0007 et un nul\u0000 au milieu.\tFin.  `;
  await champ.fill(sale);
  await verifierTexte(page, versWindows(sale));
  expect((await nettoyeAffiche(page)).retraits).toBe(CONTROLE_RETIRE.repeat(4));
  const retrait = page.locator('[data-test="nt-nettoye"] [data-retrait]').first();
  const couleurs = await retrait.evaluate((e) => [getComputedStyle(e).color, getComputedStyle(e.parentElement!).color]);
  expect(couleurs[0]).not.toBe(couleurs[1]);

  // Un emoji : un seul caractère, rien d'anormal.
  const emoji = `Bravo 😀 ${'à toi '.repeat(40)}`;
  await champ.fill(emoji);
  await verifierTexte(page, emoji);
  expect((await nettoyeAffiche(page)).gardes).toContain('😀');
  expect(await page.locator('[data-atelier-nettoyeur]').innerText()).not.toMatch(/NaN|Infinity|undefined|�/);

  // Un texte collé de 400 caractères sans espace passe à la ligne, sans élargir la page.
  await champ.fill('a'.repeat(400));
  await verifierSansDebordement(page);
});

test('atelier : le doublon et le défi', async ({ page }) => {
  await ouvrirAtelier(page);
  const autre = page.locator('[data-test="nt-autre"]');
  const defi = page.locator('[data-defi]');
  await expect.poll(() => texteExact(page, '[data-test="nt-doublon"]')).toBe('Écris un autre texte pour comparer les empreintes.');

  // Le même texte, fini par \n : même empreinte que le texte de Windows. Doublon, mais pas de défi : ils sont pareils à l'écran.
  await autre.fill(INITIAL);
  const e1 = await empreinte(versWindows(INITIAL));
  const e2 = await empreinte(INITIAL);
  await expect(page.locator('[data-test="nt-autre-empreinte"]')).toHaveText(e2.slice(0, 8));
  await expect.poll(() => texteExact(page, '[data-test="nt-doublon"]')).toBe(messageDoublon(etatDuNettoyage(INITIAL), INITIAL, e1, e2));
  expect(await texteExact(page, '[data-test="nt-doublon"]')).toBe(`Même empreinte${FINE}: c’est un doublon.`);
  await expect(defi).not.toHaveClass(/\breussi\b/);

  // Un autre exemple : empreinte différente.
  await autre.fill(texteDe(13));
  await expect.poll(() => texteExact(page, '[data-test="nt-doublon"]')).toBe(`Empreinte différente${FINE}: ce n’est pas un doublon.`);

  // Le défi : des blancs en fin, invisibles une fois nettoyés.
  await autre.fill(`${INITIAL}   `);
  await expect(defi).toHaveClass(/\breussi\b/);
  expect(await texteExact(page, '[data-test="nt-defi"]')).toBe(
    `Défi réussi${FINE}: deux textes différents, une seule empreinte. Une fois nettoyés, ils sont identiques.`,
  );
  await expect(defi.locator('[role="status"]')).toContainText('Défi réussi');
  await verifierAxe(page);
});

test('atelier : 100 000 caractères en moins de 200 ms, et le verdict avant l’empreinte', async ({ page }) => {
  // L'empreinte passe par crypto.subtle : on peut la retenir, pour voir ce que l'atelier montre en attendant.
  await page.addInitScript(() => {
    const w = window as unknown as { __retenir: boolean; __enAttente: (() => void)[] };
    w.__retenir = false;
    w.__enAttente = [];
    const digest = SubtleCrypto.prototype.digest;
    SubtleCrypto.prototype.digest = function (this: SubtleCrypto, ...args: Parameters<SubtleCrypto['digest']>) {
      const resultat = digest.apply(this, args);
      if (!w.__retenir) return resultat;
      return new Promise<ArrayBuffer>((ok, ko) => w.__enAttente.push(() => void resultat.then(ok, ko)));
    } as SubtleCrypto['digest'];
  });
  await ouvrirAtelier(page);
  const avant = await texteExact(page, '[data-test="nt-empreinte"]');

  // Empreinte retenue : le verdict change tout de suite, l'empreinte attend, sans disparaître.
  await page.evaluate(() => {
    (window as unknown as { __retenir: boolean }).__retenir = true;
  });
  await page.locator('[data-test="nt-texte"]').fill(texteDe(9));
  await expect.poll(() => texteExact(page, '[data-test="nt-verdict"]')).toBe(`Écarté${FINE}: trop court, il manque 1 caractère.`);
  await expect.poll(() => texteExact(page, '[data-test="nt-annonce"]')).toBe(`Écarté${FINE}: trop court, il manque 1 caractère.`);
  await expect(page.locator('[data-test="nt-empreinte"]')).toHaveAttribute('data-en-cours', 'oui');
  expect(await texteExact(page, '[data-test="nt-empreinte"]')).toBe(avant);
  await page.evaluate(() => {
    const w = window as unknown as { __retenir: boolean; __enAttente: (() => void)[] };
    w.__retenir = false;
    for (const lacher of w.__enAttente.splice(0)) lacher();
  });
  await verifierTexte(page, versWindows(texteDe(9)));

  // Un aller-retour pendant que l'empreinte attend : celle du texte intermédiaire ne s'affiche jamais.
  await page.evaluate(() => {
    (window as unknown as { __retenir: boolean }).__retenir = true;
  });
  await page.locator('[data-test="nt-texte"]').fill(texteDe(8));
  await page.locator('[data-test="nt-texte"]').fill(texteDe(9));
  await page.evaluate(() => {
    const w = window as unknown as { __retenir: boolean; __enAttente: (() => void)[] };
    w.__retenir = false;
    for (const lacher of w.__enAttente.splice(0)) lacher();
  });
  await page.waitForTimeout(100);
  await verifierTexte(page, versWindows(texteDe(9)));

  // 100 000 caractères : le verdict suit la frappe en moins de 200 ms (médiane de 5 essais).
  const ligne = `${'Le forgeron frappe le fer. '.repeat(3)}\n`;
  const long = ligne.repeat(Math.ceil(100_000 / ligne.length)).slice(0, 100_000);
  const durees: number[] = [];
  for (let essai = 0; essai < 5; essai++) {
    durees.push(
      await page.evaluate(async (texte) => {
        const champ = document.querySelector<HTMLTextAreaElement>('[data-test="nt-texte"]')!;
        const debut = performance.now();
        champ.value = texte;
        champ.dispatchEvent(new Event('input', { bubbles: true }));
        // Svelte met la page à jour avant la prochaine image.
        await new Promise((fin) => requestAnimationFrame(() => fin(null)));
        return performance.now() - debut;
      }, `${long.slice(0, 100_000 - 1)}${'abcde'[essai]}`),
    );
  }
  durees.sort((a, b) => a - b);
  expect(durees[2], `durées en ms : ${durees.map((d) => d.toFixed(1)).join(', ')}`).toBeLessThan(200);
  await verifierTexte(page, versWindows(`${long.slice(0, 100_000 - 1)}e`));
  await verifierSansDebordement(page);
});

test('avant le pari, l’atelier est verrouillé ; sans JavaScript, tout se lit', async ({ page, browser, baseURL }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(page.locator('[data-verrou="atelier"]')).toHaveAttribute('inert', '');
  await expect(page.locator('.verrou-msg')).toContainText('Fais ton pari à l’étape 4');
  await expect(page.locator('[data-test="nt-texte"]')).toHaveAttribute('readonly', '');
  await expect(page.locator('[data-test="nt-fins-windows"]')).toHaveAttribute('aria-disabled', 'true');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);

  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const sansJs = await ctx.newPage();
  await sansJs.goto(PAGE);
  // Pas de verrou : l'atelier est là, net, avec ses valeurs de départ, empreinte comprise.
  await expect(sansJs.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(sansJs.locator('[data-test="nt-texte"]')).toHaveValue(INITIAL);
  await verifierTexte(sansJs, versWindows(INITIAL));
  // Les explications des paris sont données d'emblée.
  for (const id of ['licence', 'court', 'doublon', 'validation', 'part']) {
    await expect(sansJs.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await expect(sansJs.locator('[data-test="ouverture"]')).toBeVisible();
  await expect(sansJs.locator('[data-test="sources"]')).toBeVisible();
  await ctx.close();
});
