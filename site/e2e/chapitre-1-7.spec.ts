// Parcours du chapitre 1.7, « Apprendre à converser », en brouillon (src/brouillons/chapitres/1-7.mdx),
// construit avec FORGE_ESSAIS=1.
//
// Les attendus viennent des fichiers du projet 1.7, lus sur le disque (paris-1-7.ts), de ce que l'atelier
// calcule (atelier-1-7.ts, et le jumeau d'encoder_conversation), des rapports d'étape (etapes.ts), des
// commandes (commandes.ts), des sources (sources-1-7.ts) et du code montré, relu dans les fichiers tels
// qu'ils sont aujourd'hui. Un parcours, chargé par Node sans Vite, n'importe ni ?raw, ni .json, ni astro:*.
//
// Ton IA 1.7 est publiée (Release ton-ia-1.7) : ses relevés sont dans le projet 1.7 (rapports d'étape des versions
// 1.5 et 1.7, et des versions courtes et à 3e-4 ; balayage du taux ; courbes des affinages). La page n'a plus aucune
// valeur « à mesurer » (data-a-mesurer).
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { test, expect, type Page } from '@playwright/test';
import { formaterDate } from '../src/lib/calculateur/formats';
import { formaterPerte, nombre, pourcent } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { CLONER_DEPOT, METTRE_A_JOUR_DEPOT } from '../src/lib/partie-0/commandes';
import * as commandes from '../src/lib/partie-1/commandes';
import { assemblerConversation } from '../src/lib/partie-1/conversation';
import {
  enToursEncodes,
  etatDeLAtelier,
  LONGUEURS_DE_RANGEE,
  NOMS_DE_L_ATELIER,
  phraseDeLEmpaquetage,
  reglageDeReference,
  texteDuCompte,
  toursDeLAtelier,
} from '../src/lib/partie-1/atelier-1-7';
import { celluleDeMesure, FICHIERS_ETAPES, lireRapportEtape, type NomRapportEtape } from '../src/lib/partie-1/etapes';
import { lireEntrainement } from '../src/lib/partie-1/journal';
import { MESURES_PARTIE_1 } from '../src/lib/partie-1/mesures';
import {
  choixConsignes,
  choixFinDeTour,
  choixFuite,
  choixGabarit,
  choixMasque,
  choixOubli,
  empaquetagesDeLaFigure,
  exigerSensDeLOubli,
  lireBalayage,
  lireConversationsDeReference,
  phraseDeLOubli,
  retenuDuBalayage,
  sensDeLOubli,
} from '../src/lib/partie-1/paris-1-7';
import { INSTRUCTGPT, LLAMA_2, LU_LE_1_7, SMOLLM3, SOURCES_DONNEES_1_7, SOURCES_LABO_1_7, TULU_3 } from '../src/lib/partie-1/sources-1-7';
import { extraireRegion } from '../src/lib/regions';
import { extraireSymbole } from '../src/lib/symboles';
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

const PAGE = '/forge-ia/partie-1/1-7/';

// Playwright tourne dans site/ : paris-1-7.ts et etapes.ts lisent le dépôt, un dossier plus haut.
const CONVERSATIONS = lireConversationsDeReference();
const TON_IA_15 = lireRapportEtape('1.5@1.7');
const TON_IA_17 = lireRapportEtape('1.7@1.7');
const FIGURE = empaquetagesDeLaFigure();

// Ce qui n'est pas du texte du chapitre mais des données brutes : les jetons de l'atelier, les longueurs de la
// figure, les réponses de ton IA telles quelles.
const BRUT =
  '[data-test="cv-jetons"], [data-test="cv-erreur"], [data-test="cv-appris-en-mots"], [data-figure="empaquetage"] [data-pagefind-ignore], ' +
  '[data-test="ouverture"] [data-pagefind-ignore], [data-echantillons-conversation] [data-pagefind-ignore]';

const GABARIT = 'projets/1.7-conversation/conversation_pas_a_pas/gabarit.py';
const FORMAT = 'projets/forge/forge/conversation/format.py';

/** Ouvre la page, hydratée (deux îlots : l'atelier et la figure). */
async function ouvrir(page: Page): Promise<void> {
  const reponse = await page.goto(PAGE);
  expect(reponse?.status()).toBe(200);
  await attendreHydratation(page, 20_000);
}

/** Ouvre l'atelier par le pari de l'étape 3. */
async function ouvrirLAtelier(page: Page): Promise<void> {
  await ouvrir(page);
  await page.locator('[data-pari="masque"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-atelier-conversation]')).toHaveAttribute('data-pret', 'oui');
}

/** Règle l'atelier : la conversation, puis chaque bascule, d'un clic seulement si elle n'est pas déjà dans l'état voulu. */
async function regler(page: Page, nom: string, systeme: boolean, deuxieme: boolean): Promise<void> {
  const atelier = page.locator('[data-atelier-conversation]');
  await atelier.locator(`[data-test="cv-conversation"][data-nom="${nom}"]`).click();
  for (const [test, voulu] of [['cv-systeme', systeme], ['cv-deuxieme', deuxieme]] as const) {
    const bascule = atelier.locator(`[data-test="${test}"]`);
    if ((await bascule.getAttribute('aria-pressed')) !== String(voulu)) await bascule.click();
    await expect(bascule).toHaveAttribute('aria-pressed', String(voulu));
  }
}

/** Attend la fin des animations en cours (fondu des verrous, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

test('chapitre 1.7 complet, en brouillon : paris, atelier, récapitulatif', async ({ page }, info) => {
  test.setTimeout(90_000);
  await ouvrir(page);
  const { total } = trouverChapitre('1.7');
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.7 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  // Le programme compte les étapes et les paris de la page.
  const etapes = await page.locator('.etape h2').count();
  const nParis = await page.locator('.pari[data-pari]').count();
  expect(etapes).toBe(10);
  expect(await page.locator('.programme').textContent()).toContain(`${etapes} étapes, ${nParis} paris`);
  // Ton IA 1.7 est mesurée : plus aucune valeur « à mesurer ».
  await expect(page.locator('[data-a-mesurer]')).toHaveCount(0);
  // Les six paris, dont ceux de ton IA 1.7.
  const parisPresents = ['fin', 'gabarit', 'masque', 'fuite', 'oubli', 'consignes'];
  expect(await page.locator('.pari[data-pari]').evaluateAll((p) => p.map((x) => x.getAttribute('data-pari')))).toStrictEqual(parisPresents);
  for (const id of parisPresents) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  // L'atelier s'ouvre au pari « masque » ; son acquis se gagne au premier réglage.
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'non');
  await regler(page, 'pensee', false, false);
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  const acquis = await page.locator('#recap li[data-acquis]').count();
  expect(acquis).toBe(7);
  await expect(page.locator('#recap [data-total]')).toContainText(`${acquis} sur ${acquis}`);
  // Le pied : 1.6 a paru, 1.8 est « à venir » tant qu'il n'a pas paru.
  await verifierVoisin(page, 'precedent', '1-6.mdx', '/forge-ia/partie-1/1-6/');
  await verifierVoisin(page, 'suivant', '1-8.mdx', '/forge-ia/partie-1/1-8/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  // Des accolades oubliées du MDX, hors des réponses de ton IA, montrées telles quelles (BRUT) : celle de 1.7 en écrit.
  expect(await texteHorsCode(page.locator('main'), BRUT)).not.toMatch(/[{}]/);
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('l’atelier : le compte égale celui du jumeau, pour les six conversations et les quatre combinaisons des bascules', async ({ page }) => {
  test.setTimeout(120_000);
  await ouvrirLAtelier(page);
  const atelier = page.locator('[data-atelier-conversation]');
  // À l'arrivée : la première conversation, telle que forge l'a assemblée.
  const depart = etatDeLAtelier(CONVERSATIONS, reglageDeReference(CONVERSATIONS, 'avec-systeme'));
  await expect(atelier.locator('[data-test="cv-compte"]')).toHaveText(texteDuCompte(depart.jetons, depart.appris));
  await expect(atelier.locator('[data-test="cv-jetons"]')).toHaveAttribute('data-pagefind-ignore', '');
  for (const nom of NOMS_DE_L_ATELIER) {
    for (const systeme of [false, true]) {
      for (const deuxieme of [false, true]) {
        await regler(page, nom, systeme, deuxieme);
        const tours = toursDeLAtelier(CONVERSATIONS, { nom, systeme, deuxieme });
        const ici = `${nom}, système ${systeme}, deuxième tour ${deuxieme}`;
        if (nom === 'reponse-vide') {
          // Forge refuse la réponse vide : la page dit son erreur, mot pour mot, et ne montre aucun jeton.
          expect(() => assemblerConversation(enToursEncodes(tours))).toThrow();
          await expect(atelier.locator('[data-test="cv-erreur"]'), ici).toHaveText(etatDeLAtelier(CONVERSATIONS, { nom, systeme, deuxieme }).erreur!);
          await expect(atelier.locator('[data-jeton]')).toHaveCount(0);
          continue;
        }
        const jumeau = assemblerConversation(enToursEncodes(tours));
        const appris = jumeau.appris.filter(Boolean).length;
        await expect(atelier.locator('[data-test="cv-compte"]'), ici).toHaveText(texteDuCompte(jumeau.ids.length, appris));
        const jetons = await atelier.locator('[data-jeton]').evaluateAll((j) => j.map((e) => [Number(e.getAttribute('data-id')), e.getAttribute('data-appris') === 'oui']));
        expect(jetons, ici).toStrictEqual(jumeau.ids.map((id, i) => [id, jumeau.appris[i]]));
      }
    }
  }
});

test('l’atelier : appris en indigo plein, non appris en lavande, spéciaux en chasse fixe ; et le défi', async ({ page }) => {
  await ouvrirLAtelier(page);
  const atelier = page.locator('[data-atelier-conversation]');
  const appris = atelier.locator('[data-jeton][data-appris="oui"]').first();
  const nonAppris = atelier.locator('[data-jeton][data-appris="non"]').first();
  await expect(appris).toHaveCSS('background-color', 'rgb(35, 32, 87)');
  await expect(nonAppris).toHaveCSS('border-top-color', 'rgb(143, 140, 184)');
  await expect(nonAppris).not.toHaveCSS('background-color', 'rgb(35, 32, 87)');
  const special = atelier.locator('[data-jeton][data-special]').first();
  expect(await special.evaluate((e) => getComputedStyle(e).fontFamily)).toMatch(/JetBrains Mono/);
  // Le défi : avec un message système et un deuxième tour, plus de la moitié des jetons appris. À l'arrivée, il
  // manque le deuxième tour ; un bonjour seul dépasse la moitié, mais sans les deux ajouts, le défi n'est pas réussi.
  await expect(atelier.locator('[data-test="cv-defi"]')).toContainText('le défi veut aussi les deux ajouts');
  await regler(page, 'sans-systeme', false, false);
  const bonjour = etatDeLAtelier(CONVERSATIONS, { nom: 'sans-systeme', systeme: false, deuxieme: false });
  expect(2 * bonjour.appris).toBeGreaterThan(bonjour.jetons);
  await expect(atelier.locator('[data-test="cv-defi"]')).toContainText('le défi veut aussi les deux ajouts');
  await regler(page, 'sans-systeme', true, true);
  await expect(atelier.locator('[data-test="cv-defi"]')).toContainText('pas encore la moitié');
  await regler(page, 'pensee', true, true);
  const pensee = etatDeLAtelier(CONVERSATIONS, { nom: 'pensee', systeme: true, deuxieme: true });
  expect(2 * pensee.appris).toBeGreaterThan(pensee.jetons);
  await expect(atelier.locator('[data-test="cv-defi"]')).toContainText('Défi réussi');
  await verifierAxe(page);
});

test('la figure de l’empaquetage : quatre longueurs, jamais NaN, chaque recalcul en moins de 200 ms', async ({ page }) => {
  await ouvrir(page);
  const figure = page.locator('[data-figure="empaquetage"]');
  const nombreJaune = figure.locator('[data-test="emp-longueur"]');
  const phrase = figure.locator('[data-test="emp-phrase"]');
  // À l'arrivée : la longueur des rangées de ton IA.
  const rang = (longueur: number) => LONGUEURS_DE_RANGEE.indexOf(longueur);
  await expect(nombreJaune).toHaveText(nombre(2048));
  await expect(phrase).toHaveText(phraseDeLEmpaquetage(FIGURE.resultats[rang(2048)]));
  // Les longueurs rangées sont celles du jeu de ton IA, relevées par le projet.
  expect(FIGURE.source).toBe('jeu');
  await expect(figure).not.toContainText('liste de référence');
  await nombreJaune.focus();
  await page.keyboard.press('Home');
  for (const [i, resultat] of FIGURE.resultats.entries()) {
    if (i > 0) {
      const debut = Date.now();
      await page.keyboard.press('ArrowRight');
      await expect(phrase).toHaveText(phraseDeLEmpaquetage(resultat), { timeout: 2_000 });
      expect(Date.now() - debut, `rangées de ${resultat.longueur}`).toBeLessThan(200);
    }
    await expect(nombreJaune).toHaveText(nombre(resultat.longueur));
    await expect(phrase).toHaveText(phraseDeLEmpaquetage(resultat));
    await expect(figure.locator('[data-test="emp-rangee"]')).toHaveCount(resultat.premieres.length);
    expect(await figure.innerText()).not.toMatch(/NaN|Infinity|undefined/);
  }
  expect(FIGURE.resultats.map((r) => r.longueur)).toStrictEqual([...LONGUEURS_DE_RANGEE]);
  await verifierAxe(page);
});

test('les choix des paris viennent des fichiers du projet et des rapports', async ({ page }) => {
  await ouvrir(page);
  const lus = async (id: string) => page.locator(`[data-pari="${id}"] [data-choix]`).allTextContents();
  const juste = async (id: string) => page.locator(`[data-pari="${id}"] [data-juste]`).textContent();
  const attendus = {
    fin: choixFinDeTour()!,
    gabarit: choixGabarit(),
    masque: choixMasque(),
    fuite: choixFuite(),
    oubli: choixOubli()!,
    consignes: choixConsignes()!,
  };
  for (const [id, choix] of Object.entries(attendus)) {
    expect((await lus(id)).map((t) => t.replace(/\s+/g, ' ').trim()), id).toStrictEqual(choix.map((c) => c.texte.replace(/\s+/g, ' ')));
    expect((await juste(id))?.replace(/\s+/g, ' '), id).toBe(choix.find((c) => c.juste)!.texte.replace(/\s+/g, ' '));
  }
  // Ton IA 1.7, publiée : sa perte sur le texte du web monte, et elle respecte moins de consignes que ton IA 1.5.
  expect(sensDeLOubli()).toBe('monte');
  expect(choixConsignes()!.find((c) => c.juste)!.texte).toMatch(/^Moins/);
  const phrase = page.locator('[data-pari="oubli"] [data-test="phrase-oubli"]');
  await expect(phrase).toContainText('monte');
  for (const r of [TON_IA_15!, TON_IA_17!]) await expect(phrase).toContainText(formaterPerte((r.mesures.oubli as { perte: number }).perte));
  expect(phraseDeLOubli()).toMatch(/monte/);
});

test('ton IA 1.5 et ton IA 1.7 : les réponses et les tableaux viennent des relevés du projet', async ({ page }) => {
  await ouvrir(page);
  expect(TON_IA_15).not.toBeNull();
  expect(TON_IA_17).not.toBeNull();
  // L'ouverture : la question, et les réponses de ton IA 1.5 et de ton IA 1.7, telles quelles.
  const ouverture = page.locator('[data-test="ouverture"]');
  for (const [nom, r] of [['1.5@1.7', TON_IA_15!], ['1.7@1.7', TON_IA_17!]] as const) {
    await expect(ouverture.locator(`[data-reponse="${nom}"]`)).toHaveText(r.echantillons.find((e) => e.invite === 'Qui es-tu ?')!.texte);
  }
  // Les deux tableaux d'étape : celui des versions courtes (étape 7), puis ton IA 1.5 face à ton IA 1.7 (étape 8).
  const tableaux: [string, NomRapportEtape[], string[]][] = [
    ['#etape-7', ['1.5@1.7', '1.7-court-3e-4@1.7', '1.7-court@1.7'], ['oubli', 'perte_conversation', 'tenue', 'ifeval_fr']],
    ['#etape-8', ['1.5@1.7', '1.7@1.7'], ['ifeval_fr', 'tenue', 'perte_conversation', 'oubli']],
  ];
  for (const [etape, versions, mesures] of tableaux) {
    const tableau = page.locator(`${etape} [data-tableau-etape]`);
    await expect(tableau).toHaveCount(1);
    for (const version of versions) {
      const rapport = lireRapportEtape(version);
      expect(rapport, version).not.toBeNull();
      for (const mesure of mesures) {
        await expect(tableau.locator(`td[data-version="${version}"][data-mesure="${mesure}"] .valeur`)).toHaveText(celluleDeMesure(rapport, mesure)!.valeur);
      }
    }
  }
  // Deux versions courtes : leurs colonnes disent leur taux.
  await expect(page.locator('#etape-7 [data-tableau-etape] th[data-version="1.7-court-3e-4@1.7"]')).toContainText('0,0003');
  await expect(page.locator('#etape-7 [data-tableau-etape] th[data-version="1.7-court@1.7"]')).toContainText('0,0001');
  // Le balayage : un essai par ligne, ses pertes de validation, et le trait sur celui que retient la règle.
  const balayage = lireBalayage()!;
  const lignes = page.locator('[data-tableau-balayage="1.7"] tbody tr');
  await expect(lignes).toHaveCount(balayage.essais.length);
  for (const [i, e] of balayage.essais.entries()) {
    expect(await lignes.nth(i).locator('td').allTextContents()).toStrictEqual(e.validations.map(([, v]) => formaterPerte(v)));
  }
  await expect(page.locator('[data-tableau-balayage="1.7"] tr[data-retenu="oui"]')).toHaveAttribute('data-essai', balayage.essais[retenuDuBalayage(balayage.essais)].essai);
  // La courbe de l'affinage publié : à son échelle, sans le hasard, que la légende dit hors du cadre.
  const courbe = page.locator('[data-courbe="sft-1.7"]');
  await expect(courbe.locator('line.hasard')).toHaveCount(0);
  await expect(courbe.locator('[data-test="hasard-hors-cadre"]')).toHaveCount(1);
  await expect(courbe.locator('[data-test="courbe-tableau"] tbody tr')).not.toHaveCount(0);
  // Les sessions de l'affinage à 3e-4 : ses deux pauses.
  const sessions = lireEntrainement('sft-1.7-3e-4')!;
  await expect(page.locator('[data-sessions="sft-1.7-3e-4"] tbody tr')).toHaveCount(sessions.sessions.length);
  // Les dix réponses de ton IA 1.7, puis celles de ton IA 1.5, telles quelles, dans l'ordre du rapport.
  for (const [nom, r] of [['1.7@1.7', TON_IA_17!], ['1.5@1.7', TON_IA_15!]] as const) {
    const echantillons = page.locator(`[data-echantillons-conversation="${nom}"] [data-reponse-texte]`);
    expect(await echantillons.allTextContents()).toStrictEqual(r.echantillons.map((e) => e.texte));
  }
});

test('l’oubli : avec deux jeux de rapports fabriqués, la phrase de l’étape 8 change de sens, et exiger refuse le faux', () => {
  // Deux dépôts fabriqués : l'oubli monte dans le premier, baisse dans le second (point à surveiller 5).
  const dossiers: string[] = [];
  const depot = (perte15: number, perte17: number) => {
    const racine = mkdtempSync(join(tmpdir(), 'chapitre-1-7-'));
    dossiers.push(racine);
    mkdirSync(join(racine, 'projets/1.5-pre-entrainement'), { recursive: true });
    for (const [nom, version, perte] of [['1.5@1.7', 'ton-ia-1.5', perte15], ['1.7@1.7', 'ton-ia-1.7', perte17]] as const) {
      const fichier = join(racine, FICHIERS_ETAPES[nom]);
      mkdirSync(dirname(fichier), { recursive: true });
      const mesures = {
        perte_conversation: { perte: 1.2, n: 64 },
        ifeval_fr: { invite_stricte: 0.3, consigne_stricte: 0.4, n: 235 },
        tenue: { terminee: 0.9, fr: 0.9, autre: 0.05, indetermine: 0.05, mots_moyens: 60, n: 335 },
        oubli: { perte, bits_par_octet: 0.8, n: 64 },
      };
      writeFileSync(fichier, JSON.stringify({ version, etape: '1.7', releve_le: '2026-11-20', mesures, echantillons: [] }));
    }
    return racine;
  };
  try {
    const monte = depot(2.35, 2.52);
    const baisse = depot(2.35, 2.21);
    expect(sensDeLOubli(monte)).toBe('monte');
    expect(sensDeLOubli(baisse)).toBe('baisse');
    expect(phraseDeLOubli(monte)).toMatch(/monte/);
    expect(phraseDeLOubli(baisse)).toMatch(/baisse/);
    expect(choixOubli(monte)!.find((c) => c.juste)!.texte).not.toBe(choixOubli(baisse)!.find((c) => c.juste)!.texte);
    // Une phrase qui dirait « monte » sur des rapports où l'oubli baisse arrête la construction.
    expect(() => exigerSensDeLOubli('monte', baisse)).toThrow(/Exemple devenu faux/);
    expect(() => exigerSensDeLOubli('baisse', monte)).toThrow(/Exemple devenu faux/);
  } finally {
    for (const d of dossiers) rmSync(d, { recursive: true, force: true });
  }
});

test('le code affiché est celui des régions et des symboles testés, tels qu’ils sont aujourd’hui', async ({ page }) => {
  await page.goto(PAGE);
  const blocs: [string, 'symbole' | 'region', string][] = [
    [FORMAT, 'symbole', '_jetons_du_tour'],
    [FORMAT, 'symbole', 'encoder_conversation'],
    [GABARIT, 'region', 'masque'],
    ['projets/forge/forge/affinage/empaquetage.py', 'symbole', 'empaqueter'],
    ['projets/forge/forge/modele/transformer.py', 'symbole', 'masque_des_documents'],
    ['projets/1.7-conversation/conversation_pas_a_pas/petit_affinage.py', 'region', 'essai'],
    ['projets/1.7-conversation/tests/test_gabarit.py', 'region', 'test-perte'],
  ];
  const codes = page.locator('.code-explique');
  await expect(codes).toHaveCount(blocs.length);
  for (const [i, [fichier, sorte, nom]] of blocs.entries()) {
    const source = readFileSync(`../${fichier}`, 'utf8');
    const attendu = sorte === 'region' ? extraireRegion(source, nom, fichier) : extraireSymbole(source, nom, fichier, { docstring: false });
    expect(await codes.nth(i).locator('pre').evaluate((pre) => pre.textContent), nom).toBe(attendu);
    await expect(codes.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
});

test('les commandes affichées sont celles de commandes.ts, et les sorties celles du projet', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page.locator('.bloc-commande pre code').evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual([
    [commandes.AFFINER_1_7, commandes.AFFINER_1_7_COURT],
    [METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_1_7],
    [CLONER_DEPOT, commandes.ALLER_AU_PROJET_1_7],
    [commandes.CONVERSATION_TESTS],
    [commandes.CONVERSATION_MONTRER],
    [commandes.DISCUTER_1_7],
  ]);
  // Les sorties montrées : la commande qui les a écrites, et le texte du fichier, sans sa ligne de date.
  for (const [fichier, commande] of [
    [MESURES_PARTIE_1.sortieFuiteConversation, commandes.CONVERSATION_FUITE],
    [MESURES_PARTIE_1.sortieEssaiAffinage, commandes.CONVERSATION_ESSAI],
  ] as const) {
    const sortie = page.locator(`[data-sortie="${fichier}"]`);
    await expect(sortie.locator('.commande')).toHaveText(commande);
    const texte = readFileSync(`../${fichier}`, 'utf8').replace(/\r\n?/g, '\n').split('\n').slice(1).join('\n').trimEnd();
    expect((await sortie.locator('[data-contenu]').textContent())?.trimEnd()).toBe(texte);
  }
});

test('l’encadré du labo : les chiffres de sources-1-7, et leurs sources', async ({ page }) => {
  await page.goto(PAGE);
  const labo = page.locator('#etape-9 .labo');
  for (const n of [
    nombre(INSTRUCTGPT.invitesSft.valeur),
    nombre(INSTRUCTGPT.petaflopsSft.valeur, 1),
    nombre(INSTRUCTGPT.petaflopsGpt3.valeur),
    nombre(LLAMA_2.annotationsSft.valeur),
    nombre(TULU_3.invitesSft.valeur),
    nombre(TULU_3.cartes8B.valeur),
    nombre(TULU_3.heuresDeCartes8B.valeur),
    `${nombre(SMOLLM3.jetonsSft.valeur / 1e9, 1)} milliard`,
  ]) {
    await expect(labo).toContainText(n);
  }
  await expect(labo).toContainText(pourcent(INSTRUCTGPT.petaflopsSft.valeur / INSTRUCTGPT.petaflopsGpt3.valeur, 2));
  for (const s of SOURCES_LABO_1_7) await expect(labo.locator(`a[href="${s.url}"]`)).toHaveCount(1);
  // L'étape des données cite ses sources dans sa note, avec leur date de lecture.
  const note = page.locator('#etape-5 .note');
  await expect(note).toContainText(`lues le ${formaterDate(LU_LE_1_7)}`);
  for (const s of SOURCES_DONNEES_1_7) await expect(note.locator(`a[href="${s.url}"]`)).toHaveCount(1);
});

test('sans JavaScript, tout se lit : les explications des paris, l’atelier à l’arrivée, la figure', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  for (const id of ['fin', 'gabarit', 'masque', 'fuite', 'oubli', 'consignes']) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  const depart = etatDeLAtelier(CONVERSATIONS, reglageDeReference(CONVERSATIONS, 'avec-systeme'));
  await expect(page.locator('[data-test="cv-compte"]')).toHaveText(texteDuCompte(depart.jetons, depart.appris));
  await expect(page.locator('[data-test="emp-phrase"]')).toHaveText(phraseDeLEmpaquetage(FIGURE.resultats[LONGUEURS_DE_RANGEE.indexOf(2048)]));
  await verifierSansDebordement(page);
  await ctx.close();
});
