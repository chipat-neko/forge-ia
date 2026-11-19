// Les paris du chapitre 1.8 et ce qu'il lit du projet 1.8, de forge et des rapports d'étape (paris-1-8.ts) : un seul
// juste par pari, calculé ; null pour les paris dont le fichier manque (la page pose alors data-a-mesurer) ; la paire
// d'exemple tant que les vraies paires de ton IA n'existent pas, et la vraie paire dès qu'elle existe ; la phrase de
// la vraisemblance qui change de sens avec les courbes, gardée par exiger (point à surveiller 5) ; le balayage et son
// essai retenu.

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { avecConsignes, comparerNotes, expliquerNote, phraseDeConsigne } from './atelier-1-8';
import { FICHIERS_ETAPES } from './etapes';
import { FICHIERS_PARTIE_1 } from './fichiers';
import { MOTS_MAXIMUM, MOTS_MINIMUM } from './notes';
import {
  CONFIG_DPO_18,
  CONSIGNES_D_EXEMPLE,
  DEFAUTS_DPO,
  choixLongueur,
  choixNote,
  choixOrdreDesCriteres,
  choixPaires,
  choixVictoire,
  choixVraisemblance,
  dessinDesCourbes,
  essaisDuBalayage,
  exigerSensDeLaChoisie,
  faitsDeForge18,
  faitsDeLaLongueur,
  faitsDeLaVraisemblance,
  faitsDuPariNotes,
  faitsDuProjet18,
  FICHIERS_1_8,
  lignesDuCode,
  lireConsignesDeReference,
  lirePairesExemples,
  lireReglagesDpo18,
  paireDeLOuverture,
  phraseDeLaLongueur,
  phraseDeLaNote,
  phraseDeLaVraisemblance,
  QUESTION_D_EXEMPLE,
  REPONSES_D_EXEMPLE,
  sensDeLaChoisie,
  SEUIL_IFEVAL_EN_INVITES,
  sensDeLaLongueur,
  textesDuPariNotes,
  TOLERANCE_LONGUEUR,
  TOLERANCE_VRAISEMBLANCE,
  TRANCHES_VICTOIRE,
} from './paris-1-8';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const ATTENDUS_18 = readFileSync(`${RACINE}/${FICHIERS_PARTIE_1.notes}`, 'utf8');

const dossiers: string[] = [];
afterAll(() => dossiers.forEach((d) => rmSync(d, { recursive: true, force: true })));

/** Un dépôt fabriqué, avec les attendus du projet 1.8 (les phrases des consignes) et les fichiers qu'on lui donne. */
function depot(fichiers: Record<string, unknown> = {}): string {
  const racine = mkdtempSync(join(tmpdir(), 'paris-1-8-'));
  dossiers.push(racine);
  mkdirSync(join(racine, 'projets/1.5-pre-entrainement'), { recursive: true });
  const tout: Record<string, unknown> = { [FICHIERS_PARTIE_1.notes]: ATTENDUS_18, ...fichiers };
  for (const [chemin, contenu] of Object.entries(tout)) {
    mkdirSync(dirname(join(racine, chemin)), { recursive: true });
    writeFileSync(join(racine, chemin), typeof contenu === 'string' ? contenu : JSON.stringify(contenu));
  }
  return racine;
}

const juste = (choix: { texte: string; juste?: boolean }[] | null) => choix?.filter((c) => c.juste).map((c) => c.texte);

const note = (terminee: number, consignes: number, francais = 1, longueur = 1) => ({ terminee, juste: 1, consignes, francais, longueur });

/** Une vraie paire fabriquée, comme `paires` du projet l'écrit (resumer.py). */
function paireQuestion(n: { choisie?: Record<string, number> } = {}) {
  return {
    id: 'luth2_conversation:0042',
    source: { nom: 'luth2_conversation', licence: 'CC BY 4.0', lien: 'https://huggingface.co/datasets/kurakurai/Luth-2-Post-Training-SFT' },
    invite: [{ role: 'utilisateur', texte: 'Cite une ville de France.\n\nRéponds en 20 mots au plus.' }],
    contraintes: [['mots_max', { n: 20 }]],
    attendu: null,
    choisie: { texte: 'Lyon est une ville de France.', terminee: true, note: n.choisie ?? note(1, 1), jetons: 9, logp_reference: -14.2 },
    rejetee: { texte: 'Lyon est une ville de', terminee: false, note: note(0, 1), jetons: 7, logp_reference: -12.0 },
    raison: 'terminee',
  };
}

/** Une paire d'un problème : l'ouverture et l'atelier la sautent (la page ne refait pas le critère « juste »). */
function paireProbleme() {
  return {
    ...paireQuestion(),
    id: 'probleme:7',
    source: { nom: 'problemes', licence: 'MIT', lien: 'https://github.com/chipat-neko/forge-ia' },
    invite: [{ role: 'utilisateur', texte: 'Combien font 2 et 3 ?' }],
    contraintes: [],
    attendu: 5,
    choisie: { texte: 'Cela fait 5.', terminee: true, note: note(1, 0), jetons: 5, logp_reference: -6.0 },
    rejetee: { texte: 'Cela fait 6.', terminee: true, note: { ...note(1, 0), juste: 0 }, jetons: 5, logp_reference: -6.5 },
    raison: 'juste',
  };
}

/** Le résumé d'un rapport d'étape 1.8 fabriqué. */
function rapport18(version: string, n: { taux?: number; motsModele?: number; motsReference?: number; invite?: number }) {
  return {
    version,
    etape: '1.8',
    releve_le: '2026-12-01',
    mesures: {
      perte_conversation: { perte: 1.1, n: 64 },
      ifeval_fr: { invite_stricte: n.invite ?? 0.3, consigne_stricte: 0.4, n: 235 },
      tenue: { terminee: 0.95, fr: 0.95, autre: 0.01, indetermine: 0.04, mots_moyens: 70, n: 335 },
      oubli: { perte: 2.4, bits_par_octet: 0.8, n: 64 },
      victoire: { victoires: 120, egalites: 40, defaites: 40, taux: n.taux ?? 0.7, mots_modele: n.motsModele ?? 60, mots_reference: n.motsReference ?? 60, n: 200 },
    },
    echantillons: [{ invite: 'Qui es-tu ?', texte: 'Je suis ton IA.', pensee: null, terminee: true }],
  };
}

/** Les courbes d'une DPO fabriquées : la choisie et la rejetée, de leur début à leur fin. */
function courbes(choisie: [number, number], rejetee: [number, number]) {
  const serie = ([a, b]: [number, number]) => [[10, a], [20, (a + b) / 2], [30, b]];
  return { logps_choisie: serie(choisie), logps_rejetee: serie(rejetee), exactitude: [[10, 0.5], [20, 0.6], [30, 0.7]] };
}

describe('la paire de l’ouverture et de l’atelier', () => {
  it('les consignes de référence du projet : leurs phrases sont celles de forge', () => {
    const consignes = lireConsignesDeReference(RACINE);
    expect(consignes).toHaveLength(8);
    for (const c of consignes) expect(phraseDeConsigne(c.id, c.kwargs)).toBe(c.consigne);
  });

  it('sans paires-exemples.json : la paire écrite pour l’exemple, dite comme telle, et ses consignes de référence', () => {
    expect(lirePairesExemples(depot())).toBeNull();
    const p = paireDeLOuverture(depot());
    expect(p.reelle).toBe(false);
    expect(p.source).toBeNull();
    expect(p.invite).toBe(avecConsignes(QUESTION_D_EXEMPLE, CONSIGNES_D_EXEMPLE));
    expect(p.reponses.map((r) => r.texte)).toStrictEqual(REPONSES_D_EXEMPLE.map((r) => r.texte));
    expect(p.reponses.map((r) => r.lettre)).toStrictEqual(['A', 'B']);
    // Les consignes de l'exemple ont les réglages de référence des attendus : la page peut comparer ses verdicts à ceux du Python.
    const reference = lireConsignesDeReference(RACINE);
    for (const [id, kwargs] of CONSIGNES_D_EXEMPLE) expect(reference.find((c) => c.id === id)?.kwargs, id).toStrictEqual(kwargs);
  });

  it('le pari « note » : un seul juste, celui que les contrôles préfèrent (noteSansJustesse et la fin du tour)', () => {
    const p = paireDeLOuverture(depot());
    const choix = choixNote(depot());
    expect(choix.filter((c) => c.juste)).toHaveLength(1);
    const [a, b] = p.reponses.map((r) => expliquerNote(r.texte, r.terminee, p.consignes).note);
    const attendu = comparerNotes(a, b) > 0 ? 'La réponse A' : comparerNotes(a, b) < 0 ? 'La réponse B' : 'Aucune : elles ont la même note';
    expect(juste(choix)).toStrictEqual([attendu]);
    // L'exemple : B respecte les deux consignes, A en oublie une (sa virgule).
    expect(juste(choix)).toStrictEqual(['La réponse B']);
    expect(phraseDeLaNote(depot())).toMatch(/consignes/);
  });

  it('avec paires-exemples.json : la première vraie paire d’une question à consignes, sa source et sa licence', () => {
    const racine = depot({ [FICHIERS_1_8.pairesExemples]: [paireProbleme(), paireQuestion()] });
    expect(lirePairesExemples(racine)).toHaveLength(2);
    const p = paireDeLOuverture(racine);
    expect(p.reelle).toBe(true);
    expect(p.source).toStrictEqual(paireQuestion().source);
    expect(p.invite).toBe('Cite une ville de France.\n\nRéponds en 20 mots au plus.');
    expect(p.consignes).toStrictEqual([['mots_max', { n: 20 }]]);
    // Le juste est la lettre de la réponse que forge a choisie, quel que soit l'ordre d'affichage.
    const lettreChoisie = p.reponses.find((r) => r.texte === 'Lyon est une ville de France.')!.lettre;
    expect(juste(choixNote(racine))).toStrictEqual([`La réponse ${lettreChoisie}`]);
    expect(p.reponses.find((r) => r.lettre === p.choisie)!.texte).toBe('Lyon est une ville de France.');
  });

  it('une vraie paire dont la note ne serait pas celle du jumeau arrête la construction', () => {
    const racine = depot({ [FICHIERS_1_8.pairesExemples]: [paireQuestion({ choisie: note(1, 0) })] });
    expect(() => paireDeLOuverture(racine)).toThrow(/Exemple devenu faux/);
  });

  it('un fichier de paires abîmé est refusé, avec la commande du projet 1.8 qui le refait', () => {
    expect(() => lirePairesExemples(depot({ [FICHIERS_1_8.pairesExemples]: [{ id: 'x' }] }))).toThrow(/alignement_pas_a_pas paires/);
    expect(() => lirePairesExemples(depot({ [FICHIERS_1_8.pairesExemples]: '{' }))).toThrow(/JSON illisible.*alignement_pas_a_pas paires/s);
  });
});

describe('le pari « notes » : l’ordre des critères, sur la paire de l’ouverture', () => {
  it('sur l’exemple : la réponse B, préférée, imaginée coupée, perd contre la A, finie', () => {
    const choix = choixOrdreDesCriteres(depot());
    expect(choix.filter((c) => c.juste)).toHaveLength(1);
    expect(juste(choix)).toStrictEqual(['La réponse A, finie']);
    expect(choix.findIndex((c) => c.juste)).toBe(0);
    const t = textesDuPariNotes(depot());
    expect(t.question).toMatch(/forge y préfère la réponse B/);
    expect(t.explication).toMatch(/^La réponse A, finie/);
    // Deux réponses finies : la précision donne leurs notes telles que forge les a données.
    expect(t.precision).toBe('Telles que forge les a notées à l’ouverture, la réponse B a (1, 1, 2, 1, 1), la réponse A (1, 1, 1, 1, 1).');
  });

  it('la précision du pari « notes » est vraie sur une vraie paire, que la rejetée soit coupée ou finie', () => {
    // La rejetée coupée (paireQuestion) : sa note réelle a 0 pour la fin du tour, et la précision le dit tel quel.
    const coupee = textesDuPariNotes(depot({ [FICHIERS_1_8.pairesExemples]: [paireQuestion()] }));
    expect(coupee.precision).toBe('Telles que forge les a notées à l’ouverture, la réponse B a (1, 1, 1, 1, 1), la réponse A (0, 1, 1, 1, 1).');
    expect(coupee.precision).not.toMatch(/sans coupure/i);
    // Les deux finies : la rejetée, d'un seul mot, perd sur la longueur.
    const deuxFinies = {
      ...paireQuestion(),
      rejetee: { texte: 'Lyon', terminee: true, note: { ...note(1, 1), longueur: 0 }, jetons: 2, logp_reference: -5.0 },
      raison: 'longueur',
    };
    const finies = textesDuPariNotes(depot({ [FICHIERS_1_8.pairesExemples]: [deuxFinies] }));
    expect(finies.precision).toBe('Telles que forge les a notées à l’ouverture, la réponse B a (1, 1, 1, 1, 1), la réponse A (1, 1, 1, 1, 0).');
    expect(finies.explication).toMatch(/^La réponse A, finie/);
    expect(juste(choixOrdreDesCriteres(depot({ [FICHIERS_1_8.pairesExemples]: [deuxFinies] })))).toStrictEqual(['La réponse A, finie']);
  });

  it('avec un paires-exemples.json fabriqué : le pari, l’ouverture et l’atelier parlent de la même paire', () => {
    const racine = depot({ [FICHIERS_1_8.pairesExemples]: [paireProbleme(), paireQuestion()] });
    const p = paireDeLOuverture(racine);
    const f = faitsDuPariNotes(racine);
    // La préférée est la réponse que forge a choisie ; l'autre, la rejetée, est donnée finie.
    expect(f.preferee).toBe(p.choisie);
    const lettres = p.reponses.map((r) => r.lettre);
    expect(lettres).toContain(f.preferee);
    expect(lettres).toContain(f.autre);
    expect(f.coupee.note.terminee).toBe(0);
    expect(f.finie.note.terminee).toBe(1);
    const t = textesDuPariNotes(racine);
    expect(t.question).toContain(`forge y préfère la réponse ${p.choisie}`);
    expect(juste(choixOrdreDesCriteres(racine))).toStrictEqual([`La réponse ${f.autre}, finie`]);
    // Rien ne parle plus de l'exemple : ni ses réponses, ni sa virgule.
    for (const r of REPONSES_D_EXEMPLE) expect(`${t.question} ${t.precision} ${t.explication}`).not.toContain(r.texte);
    expect(`${t.question} ${t.precision} ${t.explication}`).not.toMatch(/virgule/);
  });
});

describe('ce que le chapitre lit dans forge', () => {
  it('les critères, le plancher, la recette des paires et les réglages de la DPO', () => {
    const f = faitsDeForge18(RACINE);
    expect(f.criteres).toStrictEqual(['terminee', 'juste', 'consignes', 'francais', 'longueur']);
    expect(f.plancherFinieEtJuste).toBe(true);
    expect(f.egaliteSansPaire).toBe(true);
    expect(f.modeleMotAMot).toBe(true);
    expect([f.motsMinimum, f.motsMaximum]).toStrictEqual([3, 300]);
    expect(f.recette).toStrictEqual({ reponsesParInvite: 2, temperature: 1, topK: 50, nNouveaux: 384, longueur: 768, partValidation: 0.05 });
    expect([f.invites, f.invitesCourt]).toStrictEqual([40_000, 8_000]);
    expect(f.seuilDuTauxDePaires).toBe(0.2);
    expect(f.partDesProblemes).toBe(0.3);
    expect([f.consignesMin, f.consignesMax]).toStrictEqual([1, 2]);
    expect(f.dpo).toStrictEqual({ beta: 0.1, normaliserLongueur: false, poidsSft: 1 });
    expect(f.referenceCalculeeUneFois).toBe(true);
    expect(f.balayageDepartageParLaVictoire).toBe(true);
    expect(f.victoirePasUnJuge).toBe(true);
    expect(f.egaliteUneDemie).toBe(true);
    expect(f.questionSansJustesse).toBe(true);
    expect(f.questionsNonApprises).toBe(true);
    expect(f.invitesParPaquet).toBe(512);
    expect(f.longueursDesPaires).toBe(true);
    expect(f.memeNoteCourteOuLongue).toBe(true);
    // Les valeurs par défaut de [dpo] que lireReglagesDpo18 prend sont celles de forge.
    expect(f.dpo).toStrictEqual({ beta: DEFAUTS_DPO.beta, normaliserLongueur: DEFAUTS_DPO.normaliser_longueur, poidsSft: DEFAUTS_DPO.poids_sft });
  });

  it('ce que le chapitre dit du projet 1.8, relu dans son README', () => {
    expect(faitsDuProjet18(RACINE)).toStrictEqual({ noterEgaleForge: true, perteA1e12: true, pousserSansPaire: true, pointsDuTestDpo: 27, reglagesDuBalayage: true });
  });

  it('les bornes de longueur du jumeau sont celles de forge', () => {
    const f = faitsDeForge18(RACINE);
    expect([MOTS_MINIMUM, MOTS_MAXIMUM]).toStrictEqual([f.motsMinimum, f.motsMaximum]);
  });

  it('le nombre de lignes d’un extrait montré, région ou symbole sans sa docstring', () => {
    const racine = depot({
      'projets/essai.py': 'def f(x):\n    """Une docstring."""\n    y = x\n    return y\n\n\n# region: r\na = 1\nb = 2\n# fin: r\n',
    });
    expect(lignesDuCode('projets/essai.py', 'symbole', 'f', racine)).toBe(3);
    expect(lignesDuCode('projets/essai.py', 'region', 'r', racine)).toBe(2);
  });

  it('le pari « paires » : la meilleure coupée, pas de paire (le plancher de forge)', () => {
    const choix = choixPaires(RACINE);
    expect(choix.filter((c) => c.juste)).toHaveLength(1);
    expect(juste(choix)).toStrictEqual(['N’en fait pas de paire']);
  });
});

describe('la vraisemblance de la réponse choisie (étape 6)', () => {
  it('null sans le relevé des courbes : la page pose « à mesurer »', () => {
    expect(faitsDeLaVraisemblance(depot())).toBeNull();
    expect(choixVraisemblance(depot())).toBeNull();
    expect(phraseDeLaVraisemblance(depot())).toBeNull();
  });

  it('deux jeux de mesures fabriqués, « la choisie monte » puis « la choisie baisse » : le pari et la phrase changent de sens', () => {
    const monte = depot({ [FICHIERS_1_8.courbes]: courbes([-1.3, -1.2], [-1.35, -1.7]) });
    const baisse = depot({ [FICHIERS_1_8.courbes]: courbes([-1.3, -1.6], [-1.35, -2.4]) });
    const stable = depot({ [FICHIERS_1_8.courbes]: courbes([-1.3, -1.305], [-1.35, -1.9]) });
    expect(sensDeLaChoisie(monte)).toBe('monte');
    expect(sensDeLaChoisie(baisse)).toBe('baisse');
    expect(sensDeLaChoisie(stable)).toBe('stable');
    expect(faitsDeLaVraisemblance(baisse)).toMatchObject({ debut: -1.3, fin: -1.6, rejeteeDebut: -1.35, rejeteeFin: -2.4 });
    expect(juste(choixVraisemblance(monte))).toStrictEqual(['Monte']);
    expect(juste(choixVraisemblance(baisse))).toStrictEqual(['Baisse']);
    expect(juste(choixVraisemblance(stable))).toStrictEqual([`Ne bouge pas, à 0,01 près`]);
    expect(TOLERANCE_VRAISEMBLANCE).toBe(0.01);
    expect(phraseDeLaVraisemblance(monte)).toMatch(/choisie monte/);
    expect(phraseDeLaVraisemblance(monte)).not.toMatch(/piège/);
    expect(phraseDeLaVraisemblance(baisse)).toMatch(/choisie baisse/);
    expect(phraseDeLaVraisemblance(baisse)).toMatch(/piège/);
    expect(phraseDeLaVraisemblance(stable)).toMatch(/ne bouge pas/);
    // Une phrase qui dirait « monte » sur des courbes où la choisie baisse arrête la construction.
    expect(() => exigerSensDeLaChoisie('monte', baisse)).toThrow(/Exemple devenu faux/);
    expect(() => exigerSensDeLaChoisie('baisse', monte)).toThrow(/Exemple devenu faux/);
    expect(() => exigerSensDeLaChoisie('monte', monte)).not.toThrow();
  });

  it('le dessin des deux courbes : deux tracés, jamais NaN, une échelle qui les contient', () => {
    const d = dessinDesCourbes({ logps_choisie: [[10, -1.3], [20, -1.6]], logps_rejetee: [[10, -1.35], [20, -2.4]] }, 640, 280);
    expect(d.choisie.startsWith('M')).toBe(true);
    expect(d.rejetee.startsWith('M')).toBe(true);
    expect(`${d.choisie}${d.rejetee}`).not.toMatch(/NaN|Infinity/);
    expect(d.yMin).toBeLessThanOrEqual(-2.4);
    expect(d.yMax).toBeGreaterThanOrEqual(-1.3);
    expect(d.xMax).toBe(20);
    expect(d.lignes).toStrictEqual([
      { pas: 10, choisie: -1.3, rejetee: -1.35 },
      { pas: 20, choisie: -1.6, rejetee: -2.4 },
    ]);
  });
});

describe('ce qui a changé (étape 8) : la longueur et la victoire', () => {
  const avec = (r17: Parameters<typeof rapport18>[1], r18: Parameters<typeof rapport18>[1]) =>
    depot({ [FICHIERS_ETAPES['1.7@1.8']]: rapport18('ton-ia-1.7', r17), [FICHIERS_ETAPES['1.8@1.8']]: rapport18('ton-ia-1.8', r18) });

  it('null sans les rapports de l’étape 1.8', () => {
    expect(choixLongueur(depot())).toBeNull();
    expect(choixVictoire(depot())).toBeNull();
    expect(phraseDeLaLongueur(depot())).toBeNull();
    expect(faitsDeLaLongueur(depot())).toBeNull();
  });

  it('« plus longues », « plus courtes », « de même longueur, à 5 % près » : par la mesure victoire de ton IA 1.8', () => {
    expect(TOLERANCE_LONGUEUR).toBe(0.05);
    expect(sensDeLaLongueur(avec({}, { motsModele: 80, motsReference: 60 }))).toBe('plus longues');
    expect(sensDeLaLongueur(avec({}, { motsModele: 40, motsReference: 60 }))).toBe('plus courtes');
    expect(sensDeLaLongueur(avec({}, { motsModele: 62, motsReference: 60 }))).toBe('de même longueur');
    expect(juste(choixLongueur(avec({}, { motsModele: 80, motsReference: 60 })))).toStrictEqual(['Plus longues']);
    expect(juste(choixLongueur(avec({}, { motsModele: 62, motsReference: 60 })))).toStrictEqual([`De même longueur, à 5${'\u202F'}% près`]);
  });

  it('la phrase de la longueur dit si elle grandit sans mieux suivre les consignes d’IFEval-FR', () => {
    const sansMieux = phraseDeLaLongueur(avec({ invite: 0.3 }, { motsModele: 80, motsReference: 60, invite: 0.3 }));
    expect(sansMieux).toMatch(/plus longues/);
    expect(sansMieux).toMatch(/sans respecter plus souvent les consignes d’IFEval-FR/);
    const mieux = phraseDeLaLongueur(avec({ invite: 0.3 }, { motsModele: 80, motsReference: 60, invite: 0.4 }));
    expect(mieux).toMatch(/respectent plus souvent toutes les consignes d’IFEval-FR/);
    // L'écart se compte en invites, sur les 235 : 94 contre 71 (arrondis de 0,4 et 0,3 × 235).
    expect(mieux).toMatch(/94 des 235 invites d’IFEval-FR respectées en entier, contre 71/);
    // Deux invites de plus ne suffisent pas à dire « plus souvent » ; trois, si.
    expect(SEUIL_IFEVAL_EN_INVITES).toBe(3);
    const deuxDePlus = phraseDeLaLongueur(avec({ invite: 70 / 235 }, { motsModele: 80, motsReference: 60, invite: 72 / 235 }));
    expect(deuxDePlus).toMatch(/sans respecter plus souvent/);
    const troisDePlus = phraseDeLaLongueur(avec({ invite: 70 / 235 }, { motsModele: 80, motsReference: 60, invite: 73 / 235 }));
    expect(troisDePlus).toMatch(/respectent plus souvent/);
    // Les consignes d'IFEval-FR et celles des paires sont vérifiées par le même module : rien sur des consignes « pas apprises ».
    expect(`${sansMieux} ${mieux}`).not.toMatch(/apprise/);
    expect(phraseDeLaLongueur(avec({}, { motsModele: 40, motsReference: 60 }))).toMatch(/plus courtes/);
  });

  it('sans la mesure d’IFEval-FR, la phrase s’arrête à la longueur, et le pari garde son explication', () => {
    const r17 = rapport18('ton-ia-1.7', {});
    const sansIfeval = { ...r17, mesures: { ...r17.mesures, ifeval_fr: { absente: 'IFEval-FR n’est pas téléchargé' } } };
    const racine = depot({ [FICHIERS_ETAPES['1.7@1.8']]: sansIfeval, [FICHIERS_ETAPES['1.8@1.8']]: rapport18('ton-ia-1.8', { motsModele: 80, motsReference: 60 }) });
    expect(choixLongueur(racine)).not.toBeNull();
    expect(phraseDeLaLongueur(racine)).toMatch(/^Ses réponses sont plus longues.*aux mêmes invites\.$/);
  });

  it('la victoire : trois tranches, un seul juste', () => {
    expect(TRANCHES_VICTOIRE.map((t) => t.jusqua)).toStrictEqual([0.5, 0.75, Infinity]);
    expect(juste(choixVictoire(avec({}, { taux: 0.42 })))).toStrictEqual([TRANCHES_VICTOIRE[0].texte]);
    expect(juste(choixVictoire(avec({}, { taux: 0.6 })))).toStrictEqual([TRANCHES_VICTOIRE[1].texte]);
    expect(juste(choixVictoire(avec({}, { taux: 0.9 })))).toStrictEqual([TRANCHES_VICTOIRE[2].texte]);
  });
});

describe('le balayage (étape 7)', () => {
  const essai = (nom: string, beta: number, taux: number | null) => ({
    essai: nom,
    reglages: { taux_max: 1e-6, beta, normaliser_longueur: false, poids_sft: 1.0 },
    victoire: taux === null ? { absente: 'pas de jeu de paires' } : { taux, victoires: 100, egalites: 20, defaites: 80, n: 200 },
    longueur: taux === null ? { absente: 'pas de jeu de paires' } : { mots_modele: 61.5, mots_reference: 58.25 },
    logps_choisie: { debut: -1.32, fin: -1.21 },
  });
  const CONFIG = 'methode = "dpo"\ndepart = "ton-ia-1.7"\ntaux_max = 1e-6  # le taux\n\n[dpo]\nbeta = 0.1\n';

  it('null sans le relevé : la page pose « à mesurer »', () => {
    expect(essaisDuBalayage(depot())).toBeNull();
    expect(lireReglagesDpo18(depot())).toBeNull();
  });

  it('l’essai retenu est celui qui a les réglages de configs/dpo-1.8.toml (les valeurs par défaut de forge pour les autres)', () => {
    const racine = depot({ [FICHIERS_1_8.balayage]: [essai('b0.05', 0.05, 0.6), essai('b0.1', 0.1, 0.7), essai('b0.3', 0.3, null)], [CONFIG_DPO_18]: CONFIG });
    expect(lireReglagesDpo18(racine)).toStrictEqual({ taux_max: 1e-6, beta: 0.1, normaliser_longueur: false, poids_sft: 1 });
    const b = essaisDuBalayage(racine)!;
    expect(b.essais.map((e) => e.essai)).toStrictEqual(['b0.05', 'b0.1', 'b0.3']);
    expect(b.retenu).toBe(1);
  });

  it('sans la configuration, aucun essai n’est marqué ; une configuration qu’aucun essai n’a est une erreur', () => {
    const sansConfig = depot({ [FICHIERS_1_8.balayage]: [essai('b0.1', 0.1, 0.7)] });
    expect(essaisDuBalayage(sansConfig)!.retenu).toBeNull();
    const aucun = depot({ [FICHIERS_1_8.balayage]: [essai('b0.3', 0.3, 0.7)], [CONFIG_DPO_18]: CONFIG });
    expect(() => essaisDuBalayage(aucun)).toThrow(/Exemple devenu faux/);
  });

  it('un relevé abîmé est refusé, avec la commande du projet 1.8 qui le refait', () => {
    expect(() => essaisDuBalayage(depot({ [FICHIERS_1_8.balayage]: [{ essai: 'x' }] }))).toThrow(/alignement_pas_a_pas balayage/);
  });
});

describe('le dépôt réel, aujourd’hui', () => {
  it('chaque pari est soit calculé, soit null ; jamais deux justes', () => {
    for (const [nom, choix] of [
      ['note', choixNote(RACINE)],
      ['paires', choixPaires(RACINE)],
      ['vraisemblance', choixVraisemblance(RACINE)],
      ['longueur', choixLongueur(RACINE)],
      ['victoire', choixVictoire(RACINE)],
    ] as const) {
      if (choix !== null) expect(choix.filter((c) => c.juste), nom).toHaveLength(1);
    }
  });
});
