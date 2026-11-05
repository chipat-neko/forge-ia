// Parcours du chapitre 0.1, « Python pour l'IA » : un brouillon
// (src/brouillons/chapitres/0-1.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau du mot suivant (src/lib/partie-0/mot-suivant.ts)
// et des paris (paris-0-1.ts), appliqués au texte du projet lu sur le disque :
// un parcours, chargé par Node sans Vite, n'importe aucun module à ?raw (B1).
import { existsSync, readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { extraireRegion } from '../src/lib/regions';
import { trouverChapitre } from '../src/lib/parcours';
import { compterSuivants, decouperMots, generer, premiereReprise, suivantsTries } from '../src/lib/partie-0/mot-suivant';
import {
  choixBoucle,
  choixFlottants,
  choixMotSuivant,
  choixTranche,
  DEFI_REUSSI,
  LONGUEUR_DU_PARI,
  LONGUEUR_INITIALE,
  MOT_DU_PARI,
  motDuPari,
  ouvertureDuChapitre,
  SEUIL_DU_DEFI,
} from '../src/lib/partie-0/paris-0-1';
import type { Choix } from '../src/lib/choix';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-1/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const TEXTE = readFileSync('../projets/0.1-python/donnees/texte.txt', 'utf8');
const SUIVANTS = compterSuivants(decouperMots(TEXTE));
const DEPARTS = [...new Set(decouperMots(TEXTE))];
const MOT = motDuPari(TEXTE);
/** Un autre mot de départ que celui de l'atelier à l'arrivée. */
const AUTRE_MOT = DEPARTS.find((m) => m !== MOT_DU_PARI)!;

// Ce qui n'est pas du texte du chapitre mais des données brutes : le champ de
// l'atelier, ses mots (data-mot) et la liste des mots de départ.
const BRUT = 'textarea, select, [data-mot]';

/** Les mots d'une zone de l'atelier, dans l'ordre : leurs attributs data-mot. */
async function motsDe(page: Page, test: string): Promise<string[]> {
  return page.locator(`[data-test="${test}"] [data-mot]`).evaluateAll((li) => li.map((e) => e.getAttribute('data-mot') ?? ''));
}

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

/** Ouvre la page et fait le pari de l'étape 5, qui ouvre l'atelier. */
async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="suivant"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
}

/** Remplace le texte de l'atelier. */
async function ecrire(page: Page, texte: string): Promise<void> {
  await page.locator('[data-test="ms-texte"]').fill(texte);
}

test('chapitre 0.1 complet', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('0.1');
  await expect(page.locator('header')).toContainText(`Partie 0, chapitre 0.1 sur ${total}`);
  await page.locator('[data-pari="flottants"] [data-juste]').click();
  await page.locator('[data-pari="tranche"] [data-juste]').click();
  await page.locator('[data-pari="suivant"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // Changer le mot de départ fait gagner l'acquis de l'atelier.
  await page.locator('[data-test="ms-depart"]').selectOption(AUTRE_MOT);
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-pari="boucle"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
  // Le pied suit les fichiers : 0.2 est « à venir » tant qu'il n'a pas paru (S2).
  const suivant = page.locator('footer .voisin.suivant');
  if (existsSync('src/content/chapitres/0-2.mdx')) {
    await expect(suivant).toHaveAttribute('href', '/forge-ia/partie-0/0-2/');
  } else {
    await expect(suivant).toContainText('à venir');
    await expect(page.locator('footer a.voisin')).toHaveCount(0);
  }
  // Aucun lien vers un chapitre qui n'a pas paru (S3) : les renvois à 0.2, 0.3 ou 1.1 sont du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('les choix des paris viennent du jumeau', async ({ page }) => {
  await page.goto(PAGE);
  const paris: [string, Choix[]][] = [
    ['flottants', choixFlottants()],
    ['tranche', choixTranche()],
    ['suivant', choixMotSuivant(TEXTE)],
    ['boucle', choixBoucle(TEXTE)],
  ];
  for (const [id, choix] of paris) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(
      affiche(choix.find((c) => c.juste)!),
    );
  }
  // Les questions nomment le mot du pari, celui du jumeau.
  for (const id of ['suivant', 'boucle']) {
    expect(await texteExact(page, `[data-pari="${id}"] .q`)).toContain(`«${FINE}${MOT}${FINE}»`);
  }
  // L'ouverture : la première phrase du texte, en mots, et ce qui suit son mot.
  const o = ouvertureDuChapitre(TEXTE);
  expect(await motsDe(page, 'ouverture')).toEqual(o.mots);
  const phrase = await texteExact(page, '[data-test="ouverture"]');
  expect(phrase).toContain(typographier(`Après « ${o.mot} », ce texte met le plus souvent « ${o.suivant} »`));
  expect(phrase).not.toContain(`«${FINE}${MOT_DU_PARI}${FINE}»`);
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const regions: [string, string][] = [
    ['projets/0.1-python/mot_suivant/mots.py', 'decouper'],
    ['projets/0.1-python/mot_suivant/mots.py', 'compter'],
    ['projets/0.1-python/mot_suivant/mots.py', 'predire'],
    ['projets/0.1-python/mot_suivant/mots.py', 'generer'],
    ['projets/0.1-python/mot_suivant/mots.py', 'suivre'],
    ['projets/0.1-python/tests/test_mots.py', 'test-predire'],
  ];
  const blocs = page.locator('.code-explique');
  await expect(blocs).toHaveCount(regions.length);
  for (const [i, [fichier, region]] of regions.entries()) {
    const attendu = extraireRegion(readFileSync(`../${fichier}`, 'utf8'), region, fichier);
    expect(await blocs.nth(i).locator('pre').evaluate((pre) => pre.textContent), region).toBe(attendu);
    await expect(blocs.nth(i).locator('figcaption a')).toHaveAttribute(
      'href',
      `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`,
    );
  }
  // Le NamedTuple dont parle l'étape 7 est bien celui du code testé.
  await expect(blocs.nth(4).locator('pre')).toContainText('class Suite(NamedTuple):');
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/0.1-python',
  );
});

test('atelier : texte vide, mot sans suivant, 10 000 caractères, emoji', async ({ page }) => {
  await ouvrirAtelier(page);
  const message = '[data-test="ms-message"]';
  const atelier = page.locator('[data-atelier]');

  // Un texte vide : aucun mot, rien à compter.
  await ecrire(page, '');
  await expect(page.locator(message)).toBeVisible();
  expect(await texteExact(page, message)).toBe(`Écris quelques phrases${FINE}: le programme a besoin de mots à compter.`);
  await expect(page.locator('[data-test="ms-suite"] [data-mot]')).toHaveCount(0);
  await expect(page.locator('[data-test="ms-depart"] option')).toHaveCount(0);

  // Un seul mot : rien ne le suit.
  await ecrire(page, 'Forge');
  expect(await texteExact(page, message)).toBe(`Rien ne suit «${FINE}forge${FINE}» dans ce texte${FINE}: la suite s’arrête là.`);
  expect(await motsDe(page, 'ms-suite')).toEqual(['forge']);
  await expect(page.locator('[data-test="ms-suivants"] tbody tr')).toHaveCount(0);

  // Le dernier mot du texte, choisi comme départ.
  await ecrire(page, 'un deux trois');
  await page.locator('[data-test="ms-depart"]').selectOption('trois');
  expect(await texteExact(page, message)).toBe(`Rien ne suit «${FINE}trois${FINE}» dans ce texte${FINE}: la suite s’arrête là.`);
  // La suite qui s'arrête en route le dit aussi, pour son dernier mot.
  await page.locator('[data-test="ms-depart"]').selectOption('un');
  expect(await motsDe(page, 'ms-suite')).toEqual(['un', 'deux', 'trois']);
  expect(await texteExact(page, message)).toBe(`Rien ne suit «${FINE}trois${FINE}» dans ce texte${FINE}: la suite s’arrête là.`);

  // Des emoji : ils séparent les mots, et seuls, ils n'en font aucun.
  await ecrire(page, '🙂🔥 🙂');
  expect(await texteExact(page, message)).toBe(`Écris quelques phrases${FINE}: le programme a besoin de mots à compter.`);
  const avecEmoji = 'Le 🙂 forgeron frappe 🔥 le fer.';
  await ecrire(page, avecEmoji);
  // « un » n'est plus dans le texte : le départ revient au premier mot du texte.
  await expect(page.locator('[data-test="ms-depart"]')).toHaveValue('le');
  expect(await motsDe(page, 'ms-suite')).toEqual(generer(compterSuivants(decouperMots(avecEmoji)), 'le', LONGUEUR_INITIALE));

  // 10 000 caractères : le recalcul tient en moins de 200 ms, et la page ne déborde pas.
  const grand = TEXTE.repeat(Math.ceil(10_000 / TEXTE.length)).slice(0, 10_000);
  const duree = await page.evaluate(async (texte) => {
    const zone = document.querySelector<HTMLTextAreaElement>('[data-test="ms-texte"]')!;
    const debut = performance.now();
    zone.value = texte;
    zone.dispatchEvent(new Event('input', { bubbles: true }));
    // Svelte met la page à jour avant la prochaine image.
    await new Promise((fin) => requestAnimationFrame(() => fin(null)));
    return performance.now() - debut;
  }, grand);
  expect(duree, `recalcul en ${Math.round(duree)} ms`).toBeLessThan(200);
  expect(await motsDe(page, 'ms-suite')).toEqual(generer(compterSuivants(decouperMots(grand)), 'le', LONGUEUR_INITIALE));
  await verifierSansDebordement(page);

  // Un mot de 400 lettres passe à la ligne, sans élargir la page.
  await ecrire(page, `${'a'.repeat(400)} fin`);
  await expect(page.locator('[data-test="ms-suite"] [data-mot]')).toHaveCount(2);
  await verifierSansDebordement(page);

  // Jamais de valeur absurde dans l'atelier.
  expect(await atelier.innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('atelier : la suite et sa reprise suivent le jumeau', async ({ page }) => {
  await ouvrirAtelier(page);
  const depart = page.locator('[data-test="ms-depart"]');
  // Les mots de départ : chaque mot du texte une fois, dans l'ordre où il apparaît.
  expect(await depart.locator('option').evaluateAll((o) => o.map((e) => (e as HTMLOptionElement).value))).toEqual(DEPARTS);
  await expect(depart).toHaveValue(MOT_DU_PARI);
  await expect(page.locator('[data-test="ms-longueur"]')).toHaveAttribute('aria-valuenow', String(LONGUEUR_INITIALE));

  /** Vérifie le tableau, la suite et la reprise pour un départ et une longueur. */
  async function verifier(mot: string, longueur: number): Promise<void> {
    const tries = suivantsTries(SUIVANTS.get(mot) ?? new Map());
    const lignes = page.locator('[data-test="ms-suivants"] tbody tr');
    await expect(lignes).toHaveCount(Math.min(tries.length, 10));
    for (const [i, [suivant, n]] of tries.slice(0, 10).entries()) {
      await expect(lignes.nth(i).locator('[data-mot]')).toHaveAttribute('data-mot', suivant);
      await expect(lignes.nth(i).locator('td').last()).toHaveText(String(n));
    }
    if (tries.length > 0) {
      await expect(page.locator('[data-test="ms-suivants"] [data-prediction]')).toHaveCount(1);
      await expect(page.locator('[data-test="ms-suivants"] [data-prediction] [data-mot]')).toHaveAttribute('data-mot', tries[0][0]);
    }
    const suite = generer(SUIVANTS, mot, longueur);
    expect(await motsDe(page, 'ms-suite')).toEqual(suite);
    const reprise = premiereReprise(suite);
    const marque = page.locator('[data-test="ms-suite"] [data-reprise]');
    const ligne = page.locator('[data-test="ms-reprise"]');
    if (reprise === null) {
      await expect(marque).toHaveCount(0);
      await expect(ligne).toHaveCount(0);
    } else {
      await expect(marque).toHaveCount(1);
      await expect(page.locator('[data-test="ms-suite"] > li').nth(reprise)).toHaveAttribute('data-reprise', '');
      expect(await texteExact(page, '[data-test="ms-reprise"]')).toBe(
        `La suite revient sur «${FINE}${suite[reprise]}${FINE}» au mot ${reprise + 1}${FINE}: ` +
          'à partir de là, elle tourne en rond.',
      );
    }
  }

  // À l'arrivée, la suite qui part de « le » ne boucle pas encore : le lecteur parie avant de voir la boucle.
  expect(premiereReprise(generer(SUIVANTS, MOT_DU_PARI, LONGUEUR_INITIALE))).toBeNull();
  await verifier(MOT_DU_PARI, LONGUEUR_INITIALE);
  // Le nombre monté au clavier jusqu'à la longueur du pari : la boucle apparaît.
  const longueur = page.locator('[data-test="ms-longueur"]');
  await longueur.focus();
  for (let i = LONGUEUR_INITIALE; i < LONGUEUR_DU_PARI; i++) await page.keyboard.press('ArrowRight');
  await expect(longueur).toHaveAttribute('aria-valuenow', String(LONGUEUR_DU_PARI));
  expect(premiereReprise(generer(SUIVANTS, MOT_DU_PARI, LONGUEUR_DU_PARI))).not.toBeNull();
  await verifier(MOT_DU_PARI, LONGUEUR_DU_PARI);
  // Un autre départ : tout change.
  await depart.selectOption(AUTRE_MOT);
  await verifier(AUTRE_MOT, LONGUEUR_DU_PARI);
  // Une autre longueur, au clavier.
  await longueur.focus();
  for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowLeft');
  await expect(longueur).toHaveAttribute('aria-valuenow', String(LONGUEUR_DU_PARI - 6));
  await verifier(AUTRE_MOT, LONGUEUR_DU_PARI - 6);
  await page.keyboard.press('End');
  await verifier(AUTRE_MOT, Number(await longueur.getAttribute('aria-valuemax')));
  // Le point a plus de dix suivants : le tableau n'en montre que les dix premiers.
  await depart.selectOption('.');
  await verifier('.', Number(await longueur.getAttribute('aria-valuemax')));
  await verifierAxe(page);
});

test('défi réussi sur un texte sans boucle', async ({ page }) => {
  await ouvrirAtelier(page);
  const defi = page.locator('[data-test="ms-defi"]');
  // Au départ (« le », 12 mots), la suite est trop courte : le défi n'est pas réussi.
  await expect(defi).toHaveCount(0);
  await expect(page.locator('[data-defi]')).not.toHaveClass(/\breussi\b/);
  await expect(page.locator('[data-test="ms-defi-etat"]')).toContainText(`au moins ${SEUIL_DU_DEFI} mots`);
  // La longueur montée au maximum (15 ou plus) : depuis « le », la suite tourne en rond, toujours pas de défi.
  const longueur = page.locator('[data-test="ms-longueur"]');
  await longueur.focus();
  await page.keyboard.press('End');
  expect(Number(await longueur.getAttribute('aria-valuenow'))).toBeGreaterThanOrEqual(SEUIL_DU_DEFI);
  await expect(page.locator('[data-test="ms-defi-etat"]')).toContainText('tourne en rond');
  await expect(defi).toHaveCount(0);
  const nombres = ['un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze'];
  expect(nombres).toHaveLength(SEUIL_DU_DEFI);
  await ecrire(page, nombres.join(' '));
  // « le » a disparu du texte : le départ revient au premier mot, et c'est annoncé.
  await expect(page.locator('[data-test="ms-depart"]')).toHaveValue('un');
  expect(await texteExact(page, '[data-test="ms-annonce"]')).toBe(
    `«${FINE}le${FINE}» n’est plus dans le texte${FINE}: la suite part maintenant de «${FINE}un${FINE}».`,
  );
  expect(await motsDe(page, 'ms-suite')).toEqual(nombres);
  await expect(defi).toBeVisible();
  expect(await texteExact(page, '[data-test="ms-defi"]')).toBe(DEFI_REUSSI);
  await expect(page.locator('[data-defi]')).toHaveClass(/\breussi\b/);
  // La réussite est annoncée aux lecteurs d'écran.
  await expect(page.locator('[data-defi] [role="status"]')).toContainText('Défi réussi');
  // Une ligne de plus qui revient sur « un » : la boucle fait tomber le défi.
  await ecrire(page, `${nombres.join(' ')} un`);
  await expect(defi).toHaveCount(0);
  // « le » revient dans le texte : l'annonce qui le disait disparu s'efface, le départ reste « un ».
  await ecrire(page, `le ${nombres.join(' ')}`);
  await expect(page.locator('[data-test="ms-annonce"]')).toBeEmpty();
  await expect(page.locator('[data-test="ms-depart"]')).toHaveValue('un');
});

test('avant le pari, l’atelier est verrouillé ; sans JavaScript, tout se lit', async ({ page, browser, baseURL }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(page.locator('[data-verrou="atelier"]')).toHaveAttribute('inert', '');
  await expect(page.locator('.verrou-msg')).toContainText('Fais ton pari à l’étape 5');
  await expect(page.locator('[data-test="ms-longueur"]')).toHaveAttribute('aria-disabled', 'true');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);

  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const sansJs = await ctx.newPage();
  await sansJs.goto(PAGE);
  // Pas de verrou : l'atelier est là, net, avec ses valeurs de départ.
  await expect(sansJs.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(sansJs.locator('[data-test="ms-texte"]')).toHaveValue(TEXTE);
  const suite = generer(SUIVANTS, MOT_DU_PARI, LONGUEUR_INITIALE);
  expect(await motsDe(sansJs, 'ms-suite')).toEqual(suite);
  await expect(sansJs.locator('[data-test="ms-suivants"] [data-prediction] [data-mot]')).toHaveAttribute(
    'data-mot',
    suivantsTries(SUIVANTS.get(MOT_DU_PARI)!)[0][0],
  );
  // À l'arrivée, la suite ne boucle pas encore : pas de phrase de reprise.
  if (premiereReprise(suite) === null) await expect(sansJs.locator('[data-test="ms-reprise"]')).toHaveCount(0);
  else await expect(sansJs.locator('[data-test="ms-reprise"]')).toBeVisible();
  // Les explications des paris sont données d'emblée.
  for (const id of ['flottants', 'tranche', 'suivant', 'boucle']) {
    await expect(sansJs.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await expect(sansJs.locator('[data-test="ouverture"]')).toBeVisible();
  await ctx.close();
});
