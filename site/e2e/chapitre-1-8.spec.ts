// Parcours du chapitre 1.8, « L'aligner : préférences et récompenses », en brouillon
// (src/brouillons/chapitres/1-8.mdx), construit avec FORGE_ESSAIS=1.
//
// Les attendus viennent des fichiers du projet 1.8 (ses attendus, lus sur le disque), de ce que l'atelier calcule
// (atelier-1-8.ts, et le jumeau des notes), de paris-1-8.ts, des rapports d'étape (etapes.ts), des commandes
// (commandes.ts), des sources (sources-1-8.ts) et du code montré, relu dans les fichiers tels qu'ils sont
// aujourd'hui. Un parcours, chargé par Node sans Vite, n'importe ni ?raw, ni .json, ni astro:*.
//
// Ton IA 1.8 n'existe pas encore : ses paires, son balayage, ses courbes et ses rapports viennent avec sa Release
// (tâche 12 du plan 8). Jusque-là, ce qui la mesure est « à mesurer » (data-a-mesurer), et l'ouverture et l'atelier
// s'appuient sur une paire écrite pour l'exemple, dite comme telle.
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { test, expect, type Page } from '@playwright/test';
import { formaterDate } from '../src/lib/calculateur/formats';
import { nombre } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { CLONER_DEPOT, METTRE_A_JOUR_DEPOT } from '../src/lib/partie-0/commandes';
import * as commandes from '../src/lib/partie-1/commandes';
import {
  betaDeLIndice,
  ECART_MAX,
  ECART_MIN,
  estLaPlusHaute,
  expliquerNote,
  INDICE_BETA_MAX,
  INDICE_BETA_MIN,
  noteEnTexte,
  phraseDeLaPerteDpo,
} from '../src/lib/partie-1/atelier-1-8';
import { celluleDeMesure, lireRapportEtape } from '../src/lib/partie-1/etapes';
import { FICHIERS_PARTIE_1 } from '../src/lib/partie-1/fichiers';
import { mots, noteSansJustesse, VERIFICATEURS_CONTRAINTES, type ReglagesConsigne } from '../src/lib/partie-1/notes';
import {
  choixLongueur,
  choixNote,
  choixOrdreDesCriteres,
  choixPaires,
  choixVictoire,
  choixVraisemblance,
  essaisDuBalayage,
  exigerSensDeLaChoisie,
  faitsDeLaVraisemblance,
  FICHIERS_1_8,
  lireConsignesDeReference,
  paireDeLOuverture,
  phraseDeLaVraisemblance,
  sensDeLaChoisie,
} from '../src/lib/partie-1/paris-1-8';
import { INSTRUCTGPT_RM, LLAMA_2_RLHF, LU_LE_1_8, QWEN_25, SOURCES_DONNEES_1_8, SOURCES_DPO_1_8, SOURCES_LABO_1_8, TULU_3_DPO } from '../src/lib/partie-1/sources-1-8';
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

const PAGE = '/forge-ia/partie-1/1-8/';

// Playwright tourne dans site/ : paris-1-8.ts et etapes.ts lisent le dépôt, un dossier plus haut.
const PAIRE = paireDeLOuverture();
const TON_IA_18 = lireRapportEtape('1.8@1.8');
const COURBES = faitsDeLaVraisemblance();
const BALAYAGE = essaisDuBalayage();
const CONSIGNES_DE_REFERENCE = lireConsignesDeReference();

interface TexteAttendu {
  nom: string;
  texte: string;
  terminee: boolean;
  mots: number;
  langue: string;
  verdicts: Record<string, boolean>;
  note: { terminee: number; consignes: number; francais: number; longueur: number };
}
const TEXTES = (JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.notes}`, 'utf8')) as { textes: TexteAttendu[] }).textes;

// Ce qui n'est pas du texte du chapitre mais des données brutes : l'invite et les réponses telles quelles, le texte
// du lecteur, les consignes telles que forge les écrit.
const BRUT =
  '[data-test="ouverture-preferences"] [data-pagefind-ignore], [data-atelier-note] [data-pagefind-ignore], ' +
  '[data-echantillons-conversation] [data-pagefind-ignore], [data-pari] code';

const PROJET = 'projets/1.8-alignement';

/** Ouvre la page, hydratée (deux îlots : l'atelier et la phrase de la DPO). */
async function ouvrir(page: Page): Promise<void> {
  const reponse = await page.goto(PAGE);
  expect(reponse?.status()).toBe(200);
  await attendreHydratation(page, 20_000);
}

/** Ouvre l'atelier par le pari de l'étape 3. */
async function ouvrirLAtelier(page: Page): Promise<void> {
  await ouvrir(page);
  await page.locator('[data-pari="notes"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-atelier-note]')).toHaveAttribute('data-pret', 'oui');
}

/** Écrit un texte dans l'atelier d'un seul geste (comme un collage), et rend le temps du recalcul, mesuré dans la page. */
async function ecrire(page: Page, texte: string): Promise<number> {
  return page.evaluate(async (t) => {
    const zone = document.querySelector('[data-test="an-texte"]') as HTMLTextAreaElement;
    const debut = performance.now();
    zone.value = t;
    zone.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => requestAnimationFrame(() => r(null)));
    return performance.now() - debut;
  }, texte);
}

/** Met la bascule « elle a fini son tour » dans l'état voulu. */
async function finie(page: Page, voulu: boolean): Promise<void> {
  const bascule = page.locator('[data-test="an-terminee"]');
  if ((await bascule.getAttribute('aria-pressed')) !== String(voulu)) await bascule.click();
  await expect(bascule).toHaveAttribute('aria-pressed', String(voulu));
}

async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

test('chapitre 1.8 complet, en brouillon : paris, atelier, phrase de la DPO, récapitulatif', async ({ page }, info) => {
  test.setTimeout(90_000);
  await ouvrir(page);
  const { total } = trouverChapitre('1.8');
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.8 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  const etapes = await page.locator('.etape h2').count();
  const nParis = await page.locator('.pari[data-pari]').count();
  expect(etapes).toBe(10);
  expect(await page.locator('.programme').textContent()).toContain(`${etapes} étapes, ${nParis} paris`);
  // Ton IA 1.8 n'est pas encore mesurée : au moins une valeur « à mesurer ».
  expect(await page.locator('[data-a-mesurer]').count()).toBeGreaterThanOrEqual(1);
  const mesures = { vraisemblance: choixVraisemblance(), longueur: choixLongueur(), victoire: choixVictoire() };
  const parisPresents = ['note', 'notes', 'paires', ...Object.entries(mesures).filter(([, c]) => c !== null).map(([id]) => id)];
  await expect(page.locator('.pari[data-pari]')).toHaveCount(parisPresents.length);
  for (const id of parisPresents) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  // L'atelier s'ouvre au pari « notes » ; son acquis se gagne à la première frappe.
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'non');
  await page.locator('[data-test="an-texte"]').fill('Paris est la capitale de la France.');
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  // La phrase de la DPO : son acquis se gagne au premier réglage.
  await expect(page.locator('#recap [data-acquis="dpo"]')).toHaveAttribute('data-gagne', 'non');
  await page.locator('[data-test="dpo-choisie"]').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#recap [data-acquis="dpo"]')).toHaveAttribute('data-gagne', 'oui');
  const acquis = await page.locator('#recap li[data-acquis]').count();
  expect(acquis).toBe(5 + (mesures.vraisemblance ? 1 : 0) + (mesures.longueur ? 1 : 0));
  await expect(page.locator('#recap [data-total]')).toContainText(`${acquis} sur ${acquis}`);
  // Le pied : 1.7 et 1.9 sont « à venir » tant qu'ils n'ont pas paru.
  await verifierVoisin(page, 'precedent', '1-7.mdx', '/forge-ia/partie-1/1-7/');
  await verifierVoisin(page, 'suivant', '1-9.mdx', '/forge-ia/partie-1/1-9/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/[{}]/);
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('l’ouverture : deux réponses côte à côte, sans dire laquelle est choisie avant le pari', async ({ page }) => {
  await ouvrir(page);
  const ouverture = page.locator('[data-test="ouverture-preferences"]');
  await expect(ouverture.locator('[data-test="op-invite"]')).toHaveText(PAIRE.invite);
  for (const r of PAIRE.reponses) await expect(ouverture.locator(`[data-reponse="${r.lettre}"] [data-test="op-texte"]`)).toHaveText(r.texte);
  // Rien, dans l'ouverture, ne dit laquelle est choisie : le verdict n'est que dans l'explication du pari.
  expect(await ouverture.innerText()).not.toMatch(/choisie|rejetée|préfère/);
  if (!PAIRE.reelle) {
    await expect(ouverture).toContainText('écrites pour l’exemple');
    await expect(page.locator('[data-paire-a-mesurer][data-a-mesurer]')).toHaveCount(1);
  }
  await expect(page.locator('[data-pari="note"] [data-juste]')).toHaveText(choixNote().find((c) => c.juste)!.texte);
});

test('l’atelier : sur les quarante textes de référence, mêmes verdicts que le Python, chaque recalcul en moins de 200 ms', async ({ page }) => {
  test.setTimeout(120_000);
  await ouvrirLAtelier(page);
  const atelier = page.locator('[data-atelier-note]');
  // Les consignes de l'invite ont-elles les réglages de référence des attendus ? Alors les verdicts du Python s'appliquent tels quels.
  const deReference = PAIRE.consignes.every(([id, kwargs]) => JSON.stringify(CONSIGNES_DE_REFERENCE.find((c) => c.id === id)?.kwargs) === JSON.stringify(kwargs));
  if (!PAIRE.reelle) expect(deReference).toBe(true);
  for (const t of TEXTES) {
    await finie(page, t.terminee);
    const ms = await ecrire(page, t.texte);
    expect(ms, `${t.nom} : ${ms.toFixed(1)} ms`).toBeLessThan(200);
    const lu = await page.locator('[data-test="an-texte"]').inputValue();
    // Un champ de saisie ramène \r\n et \r à \n : le texte lu peut différer de celui des attendus.
    const intact = lu === t.texte;
    const attendu = expliquerNote(lu, t.terminee, PAIRE.consignes);
    const consignes = atelier.locator('[data-test="an-consigne"]');
    await expect(consignes, t.nom).toHaveCount(PAIRE.consignes.length);
    for (const [i, [id, kwargs]] of PAIRE.consignes.entries()) {
      const verdict = intact && deReference ? t.verdicts[id] : VERIFICATEURS_CONTRAINTES[id](lu, kwargs as ReglagesConsigne);
      await expect(consignes.nth(i), `${t.nom}, ${id}`).toHaveAttribute('data-respectee', verdict ? 'oui' : 'non');
    }
    const valeurs = intact
      ? { terminee: t.note.terminee, juste: 1, consignes: attendu.note.consignes, francais: t.note.francais, longueur: t.note.longueur }
      : attendu.note;
    if (intact) expect(mots(lu).length, t.nom).toBe(t.mots);
    for (const [nom, valeur] of Object.entries(valeurs)) {
      await expect(atelier.locator(`[data-test="an-critere"][data-nom="${nom}"]`), `${t.nom}, ${nom}`).toHaveAttribute('data-valeur', String(valeur));
    }
    expect(noteSansJustesse(lu, t.terminee, PAIRE.consignes)).toStrictEqual({ terminee: valeurs.terminee, consignes: valeurs.consignes, francais: valeurs.francais, longueur: valeurs.longueur });
    await expect(atelier.locator('[data-test="an-note"]'), t.nom).toContainText(noteEnTexte(attendu.note));
    expect(await atelier.innerText()).not.toMatch(/NaN|Infinity|undefined/);
  }
});

test('l’atelier : le défi, la bascule de fin de tour, et la comparaison', async ({ page }) => {
  await ouvrirLAtelier(page);
  const atelier = page.locator('[data-atelier-note]');
  const defi = atelier.locator('[data-test="an-defi"]');
  // À l'arrivée, le texte du champ n'a pas la note la plus haute.
  await expect(defi).toContainText('Pas encore');
  // Recopier la réponse de la paire qui a la note la plus haute ne réussit pas le défi : il veut la tienne.
  const auMaximum = PAIRE.reponses.find((r) => estLaPlusHaute(expliquerNote(r.texte, true, PAIRE.consignes)));
  if (auMaximum !== undefined) {
    await ecrire(page, auMaximum.texte);
    await expect(defi).toContainText(`c’est la réponse ${auMaximum.lettre} de la paire`);
  }
  if (!PAIRE.reelle) {
    // Une réponse à soi, finie, sous 20 mots et sans virgule : le défi est réussi.
    const tienne = 'La capitale de la France est Paris.';
    expect(estLaPlusHaute(expliquerNote(tienne, true, PAIRE.consignes))).toBe(true);
    await ecrire(page, tienne);
    await expect(defi).toContainText('Défi réussi');
    // Coupée par la limite, la même réponse perd : la fin du tour passe avant tout le reste.
    await finie(page, false);
    await expect(defi).toContainText('Pas encore');
    await expect(atelier.locator('[data-test="an-critere"][data-nom="terminee"]')).toHaveAttribute('data-verdict', 'non');
    await finie(page, true);
  }
  // La comparaison : les deux réponses de la paire et leurs notes, ou, sans vraie paire, celles de l'exemple.
  await atelier.locator('[data-test="an-comparer"]').click();
  const comparees = atelier.locator('[data-test="an-reponse-comparee"]');
  await expect(comparees).toHaveCount(2);
  for (const [i, r] of PAIRE.reponses.entries()) await expect(comparees.nth(i).locator('[data-pagefind-ignore]').first()).toHaveText(r.texte);
  if (!PAIRE.reelle) await expect(atelier.locator('[data-comparaison-a-mesurer][data-a-mesurer]')).toHaveCount(1);
  await verifierAxe(page);
});

test('la phrase de la DPO : aux bornes de ses trois nombres, la perte de dpo.ts, jamais NaN ni « e+ »', async ({ page }) => {
  await ouvrir(page);
  const figure = page.locator('[data-figure="phrase-dpo"]');
  const regler = async (test_: string, fin: 'Home' | 'End') => {
    await figure.locator(`[data-test="${test_}"]`).focus();
    await page.keyboard.press(fin);
  };
  for (const b of ['Home', 'End'] as const) {
    for (const c of ['Home', 'End'] as const) {
      for (const r of ['Home', 'End'] as const) {
        await regler('dpo-beta', b);
        await regler('dpo-choisie', c);
        await regler('dpo-rejetee', r);
        const beta = betaDeLIndice(b === 'Home' ? INDICE_BETA_MIN : INDICE_BETA_MAX);
        const ec = c === 'Home' ? ECART_MIN : ECART_MAX;
        const er = r === 'Home' ? ECART_MIN : ECART_MAX;
        const attendu = phraseDeLaPerteDpo(beta, ec, er);
        await expect(figure.locator('[data-test="dpo-perte"]'), `${beta} ${ec} ${er}`).toHaveText(attendu.perte);
        await expect(figure.locator('[data-test="dpo-suite"]'), `${beta} ${ec} ${er}`).toHaveText(attendu.suite);
        expect(await figure.innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
      }
    }
  }
  await verifierAxe(page);
});

test('les choix des paris viennent des fichiers du projet, de forge et des rapports', async ({ page }) => {
  await ouvrir(page);
  const lus = async (id: string) => page.locator(`[data-pari="${id}"] [data-choix]`).allTextContents();
  const juste = async (id: string) => page.locator(`[data-pari="${id}"] [data-juste]`).textContent();
  const attendus = { note: choixNote(), notes: choixOrdreDesCriteres(), paires: choixPaires() };
  for (const [id, choix] of Object.entries(attendus)) {
    expect((await lus(id)).map((t) => t.replace(/\s+/g, ' ').trim()), id).toStrictEqual(choix.map((c) => c.texte));
    expect(await juste(id), id).toBe(choix.find((c) => c.juste)!.texte);
  }
  // Les paris de ton IA 1.8 : null sans leur fichier, et la page pose « à mesurer » à leur place.
  for (const [id, choix] of [['vraisemblance', choixVraisemblance()], ['longueur', choixLongueur()], ['victoire', choixVictoire()]] as const) {
    if (choix === null) {
      await expect(page.locator(`[data-pari="${id}"]`)).toHaveCount(0);
      await expect(page.locator(`[data-pari-a-mesurer="${id}"][data-a-mesurer]`)).toHaveCount(1);
    } else {
      expect(await juste(id)).toBe(choix.find((c) => c.juste)!.texte);
    }
  }
});

test('ton IA 1.8 est « à mesurer » tant que ses relevés n’existent pas : courbes, balayage, tableau, échantillons', async ({ page }) => {
  await ouvrir(page);
  if (COURBES === null) await expect(page.locator('[data-courbe-dpo-absente][data-a-mesurer]')).toHaveCount(1);
  else await expect(page.locator('[data-courbe-dpo] [data-test="courbe-dpo-tableau"] tbody tr')).not.toHaveCount(0);
  if (BALAYAGE === null) await expect(page.locator('[data-balayage-absent][data-a-mesurer]')).toHaveCount(1);
  else await expect(page.locator('[data-tableau-balayage] tbody tr')).toHaveCount(BALAYAGE.essais.length);
  const tableau = page.locator('[data-tableau-etape]').first();
  for (const version of ['1.7@1.8', '1.8@1.8', '1.8-court@1.8'] as const) {
    const rapport = lireRapportEtape(version);
    for (const mesure of ['ifeval_fr', 'tenue', 'victoire', 'oubli']) {
      const cellule = tableau.locator(`td[data-version="${version}"][data-mesure="${mesure}"]`);
      const attendu = celluleDeMesure(rapport, mesure);
      if (attendu === null) await expect(cellule.locator('[data-a-mesurer]')).toHaveText('à mesurer');
      else await expect(cellule.locator('.valeur')).toHaveText(attendu.valeur);
    }
  }
  if (TON_IA_18 === null) {
    await expect(page.locator('[data-echantillons-conversation="1.8@1.8"][data-a-mesurer]')).toHaveCount(1);
    await expect(page.locator('[data-construction-absente][data-a-mesurer]')).toHaveCount(1);
  }
});

test('la vraisemblance : avec deux jeux de mesures fabriqués, la phrase de l’étape 6 change de sens, et exiger refuse le faux', () => {
  // Deux dépôts fabriqués : la choisie monte dans le premier, baisse dans le second (point à surveiller 5).
  const dossiers: string[] = [];
  const depot = (choisie: [number, number], rejetee: [number, number]) => {
    const racine = mkdtempSync(join(tmpdir(), 'chapitre-1-8-'));
    dossiers.push(racine);
    mkdirSync(join(racine, 'projets/1.5-pre-entrainement'), { recursive: true });
    const fichier = join(racine, FICHIERS_1_8.courbes);
    mkdirSync(dirname(fichier), { recursive: true });
    const serie = ([a, b]: [number, number]) => [[10, a], [20, b]];
    writeFileSync(fichier, JSON.stringify({ logps_choisie: serie(choisie), logps_rejetee: serie(rejetee), exactitude: [[10, 0.5], [20, 0.7]] }));
    return racine;
  };
  try {
    const monte = depot([-1.3, -1.2], [-1.35, -1.7]);
    const baisse = depot([-1.3, -1.6], [-1.35, -2.4]);
    expect(sensDeLaChoisie(monte)).toBe('monte');
    expect(sensDeLaChoisie(baisse)).toBe('baisse');
    expect(phraseDeLaVraisemblance(monte)).toMatch(/choisie monte/);
    expect(phraseDeLaVraisemblance(baisse)).toMatch(/choisie baisse/);
    expect(choixVraisemblance(monte)!.find((c) => c.juste)!.texte).not.toBe(choixVraisemblance(baisse)!.find((c) => c.juste)!.texte);
    // Une phrase qui dirait « monte » sur des courbes où la choisie baisse arrête la construction.
    expect(() => exigerSensDeLaChoisie('monte', baisse)).toThrow(/Exemple devenu faux/);
    expect(() => exigerSensDeLaChoisie('baisse', monte)).toThrow(/Exemple devenu faux/);
  } finally {
    for (const d of dossiers) rmSync(d, { recursive: true, force: true });
  }
});

test('le code affiché est celui des régions et des symboles testés, tels qu’ils sont aujourd’hui', async ({ page }) => {
  await page.goto(PAGE);
  const blocs: [string, 'symbole' | 'region', string][] = [
    [`${PROJET}/alignement_pas_a_pas/noter.py`, 'region', 'noter'],
    ['projets/forge/forge/preferences/noter.py', 'symbole', 'sans_paire'],
    ['projets/forge/forge/preferences/construction.py', 'symbole', 'construire_paires'],
    [`${PROJET}/alignement_pas_a_pas/perte_dpo.py`, 'region', 'perte-dpo'],
    [`${PROJET}/tests/test_perte_dpo.py`, 'region', 'test-dpo'],
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

test('les commandes affichées sont celles de commandes.ts', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page.locator('.bloc-commande pre code').evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual([
    [commandes.PREFERENCES_1_8],
    [METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_1_8],
    [CLONER_DEPOT, commandes.ALLER_AU_PROJET_1_8],
    [commandes.ALIGNEMENT_TESTS],
    [commandes.ALIGNEMENT_NOTER, commandes.ALIGNEMENT_DPO, commandes.ALIGNEMENT_POUSSER],
  ]);
});

test('l’encadré du labo et les notes : les chiffres de sources-1-8, et leurs sources', async ({ page }) => {
  await page.goto(PAGE);
  const labo = page.locator('#etape-9 .labo');
  for (const n of [
    nombre(INSTRUCTGPT_RM.invitesRm.valeur),
    nombre(INSTRUCTGPT_RM.petaflopsPpo.valeur),
    nombre(LLAMA_2_RLHF.comparaisonsMeta.valeur),
    nombre(QWEN_25.paires.valeur),
    nombre(TULU_3_DPO.paires8B.valeur),
    nombre(TULU_3_DPO.pairesTotal.valeur),
    nombre(TULU_3_DPO.invitesTableau7.valeur),
  ]) {
    await expect(labo).toContainText(n);
  }
  for (const s of SOURCES_LABO_1_8) await expect(labo.locator(`a[href="${s.url}"]`)).toHaveCount(1);
  // Les étapes 2, 5 et 6 citent leurs sources dans leurs notes, avec leur date de lecture.
  for (const [etape, sources] of [[2, SOURCES_DONNEES_1_8], [6, SOURCES_DPO_1_8]] as const) {
    const note = page.locator(`#etape-${etape} .note`);
    await expect(note).toContainText(`lues le ${formaterDate(LU_LE_1_8)}`);
    for (const s of sources) await expect(note.locator(`a[href="${s.url}"]`)).toHaveCount(1);
  }
});

test('sans JavaScript, tout se lit : les explications des paris, l’atelier et la phrase à l’arrivée', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  for (const id of ['note', 'notes', 'paires']) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="an-critere"]')).toHaveCount(5);
  const depart = phraseDeLaPerteDpo(betaDeLIndice(2), 1, -1);
  await expect(page.locator('[data-test="dpo-perte"]')).toHaveText(depart.perte);
  await verifierSansDebordement(page);
  await ctx.close();
});
