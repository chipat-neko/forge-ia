// Les paris du chapitre 1.7 et ce qu'il lit du projet 1.7 (paris-1-7.ts) : un seul juste par pari, calculé
// sur les fichiers du dépôt ; null pour les paris dont le rapport d'étape manque (la page pose alors
// data-a-mesurer) ; la phrase de l'oubli qui change de sens avec les rapports, gardée par exiger ; la figure
// de l'empaquetage calculée par le jumeau de BFD.

import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { assemblerConversation, PREMIER_SPECIAL, SPECIAUX_TON_IA } from './conversation';
import { empaqueterLongueurs } from './bfd';
import { enToursEncodes, LONGUEURS_DE_RANGEE } from './atelier-1-7';
import { FICHIERS_ETAPES, lireRapportEtape } from './etapes';
import { MESURES_PARTIE_1 } from './mesures';
import {
  choixConsignes,
  choixFinDeTour,
  choixFuite,
  choixGabarit,
  choixMasque,
  choixOubli,
  decoderLesIds,
  empaquetagesDeLaFigure,
  exigerSensDeLOubli,
  faitsDuPariFin,
  faitsDuPariGabarit,
  faitsDuPariMasque,
  FICHIER_LONGUEURS_SFT_17,
  INVITE_DE_L_OUVERTURE,
  lireConversationsDeReference,
  lireEssaiAffinage,
  lireFuite,
  lireLongueurs,
  lireReglagesSft,
  phraseDeLOubli,
  reponseALInvite,
  sensDeLOubli,
  SEUIL_DE_FUITE,
  textesDesJetons,
  TOLERANCE_OUBLI,
  TRANCHES_CONSIGNES,
  TRANCHES_FIN,
} from './paris-1-7';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const RACINE = '..';
const FINE = '\u202F';

const dossiers: string[] = [];
afterAll(() => dossiers.forEach((d) => rmSync(d, { recursive: true, force: true })));

/** Un dépôt fabriqué, avec ses fichiers (chemin depuis la racine vers contenu). */
function depot(fichiers: Record<string, unknown> = {}): string {
  const racine = mkdtempSync(join(tmpdir(), 'paris-1-7-'));
  dossiers.push(racine);
  mkdirSync(join(racine, 'projets/1.5-pre-entrainement'), { recursive: true });
  for (const [chemin, contenu] of Object.entries(fichiers)) {
    mkdirSync(dirname(join(racine, chemin)), { recursive: true });
    writeFileSync(join(racine, chemin), typeof contenu === 'string' ? contenu : JSON.stringify(contenu));
  }
  return racine;
}

/** Le résumé d'un rapport d'étape 1.7 fabriqué, avec les nombres qu'on lui donne. */
function rapport17(version: string, n: { terminee?: number; invite?: number; oubli?: number }) {
  return {
    version,
    etape: '1.7',
    releve_le: '2026-11-20',
    mesures: {
      perte_conversation: { perte: 1.2, n: 64 },
      ifeval_fr: { invite_stricte: n.invite ?? 0.3, consigne_stricte: 0.4, n: 235 },
      tenue: { terminee: n.terminee ?? 0.9, fr: 0.95, autre: 0.01, indetermine: 0.04, mots_moyens: 80, n: 335 },
      oubli: { perte: n.oubli ?? 2.35, bits_par_octet: 0.78, n: 64 },
    },
    echantillons: [{ invite: 'Qui es-tu ?', texte: 'Je suis ton IA.', pensee: null, terminee: true }],
  };
}

/** Deux rapports, ton IA 1.5 puis ton IA 1.7, dans un dépôt fabriqué. */
function avantApres(avant: Parameters<typeof rapport17>[1], apres: Parameters<typeof rapport17>[1]): string {
  return depot({
    [FICHIERS_ETAPES['1.5@1.7']]: rapport17('ton-ia-1.5', avant),
    [FICHIERS_ETAPES['1.7@1.7']]: rapport17('ton-ia-1.7', apres),
  });
}

const juste = (choix: { texte: string; juste?: boolean }[] | null) => choix?.filter((c) => c.juste).map((c) => c.texte);

describe('les fichiers du projet 1.7', () => {
  it('les six conversations de référence, et leurs textes retrouvés jeton par jeton depuis le tokenizer', () => {
    const conversations = lireConversationsDeReference(RACINE);
    expect(conversations.map((c) => c.nom)).toStrictEqual(['avec-systeme', 'sans-systeme', 'deux-tours', 'faux-special', 'pensee', 'reponse-vide']);
    for (const c of conversations) {
      for (const t of c.tours) {
        // Les octets des jetons, mis bout à bout, redonnent le texte encodé par le Python.
        expect(decoderLesIds(t.ids, RACINE), `${c.nom}, ${t.role}`).toBe(t.texte);
        if (t.pensee_ids !== undefined) expect(decoderLesIds(t.pensee_ids, RACINE)).toBe(t.pensee);
      }
      // Le jumeau redonne l'assemblage de forge.
      if (c.erreur === null) expect(assemblerConversation(enToursEncodes(c.tours))).toStrictEqual({ ids: c.ids, appris: c.appris });
    }
  });

  it('le texte de chaque jeton : son nom pour un spécial, « ␊ » pour un saut de ligne', () => {
    const textes = textesDesJetons([SPECIAUX_TON_IA['<|fin_tour|>'], SPECIAUX_TON_IA['<|assistant|>'], 10, 32], RACINE);
    expect(textes[SPECIAUX_TON_IA['<|fin_tour|>']]).toBe('<|fin_tour|>');
    expect(textes[SPECIAUX_TON_IA['<|assistant|>']]).toBe('<|assistant|>');
    expect(textes[10]).toBe('␊');
    expect(textes[32]).toBe(' ');
    expect(() => textesDesJetons([32768], RACINE)).toThrow(/32768/);
  });

  it('la fuite et le petit affinage, relevés sur le processeur', () => {
    const f = lireFuite(RACINE);
    expect(f.avec_masque).toBeLessThanOrEqual(1e-5);
    expect(f.sans_masque).toBeGreaterThan(SEUIL_DE_FUITE);
    const e = lireEssaiAffinage(RACINE);
    expect(e.appareil).toBe('cpu');
    expect(e.pertes).toHaveLength(e.pas);
    expect(e.reponses_avant).toHaveLength(e.reponses_apres.length);
    expect(MESURES_PARTIE_1.fuiteConversation).toBe('projets/1.7-conversation/mesures/fuite.json');
    expect(MESURES_PARTIE_1.sortieEssaiAffinage).toBe('projets/1.7-conversation/sorties/essai-processeur.txt');
  });

  it('un fichier de mesures faux est refusé, en disant quelle commande le refait', () => {
    expect(() => lireFuite(depot({ [MESURES_PARTIE_1.fuiteConversation]: { avec_masque: 'x' } }))).toThrow(/fuite\.json.*conversation_pas_a_pas fuite/s);
    expect(() => lireEssaiAffinage(depot({ [MESURES_PARTIE_1.essaiAffinage]: '{' }))).toThrow(/essai-processeur\.json.*conversation_pas_a_pas essai/s);
  });

  it('les longueurs du jeu d’affinage : null tant qu’elles ne sont pas relevées', () => {
    expect(lireLongueurs(depot())).toBeNull();
    const racine = depot({
      [FICHIER_LONGUEURS_SFT_17]: { jeu: 'sft-1.7', releve_le: '2026-11-20', longueur_des_rangees: 2048, histogramme: [[3, 2], [700, 1]] },
    });
    expect(lireLongueurs(racine)?.longueurs).toStrictEqual([3, 3, 700]);
  });

  it('les réglages des deux affinages, lus dans les configurations de forge', () => {
    const complet = lireReglagesSft('sft-1.7', RACINE);
    const court = lireReglagesSft('sft-1.7-court', RACINE);
    expect(complet.methode).toBe('sft');
    expect(complet.depart).toBe('ton-ia-1.5');
    expect(complet.longueur).toBe(2048);
    expect(court.taux_max).toBe(complet.taux_max);
    expect(court.jetons_total).toBeLessThan(complet.jetons_total);
    expect(Number.isInteger(complet.jetons_total / complet.taille_lot_jetons)).toBe(true);
  });
});

describe('les paris du chapitre 1.7', () => {
  it('« fin » : trois tranches de la part terminée de ton IA 1.5, un seul juste', () => {
    const choix = choixFinDeTour(RACINE);
    expect(choix).not.toBeNull();
    expect(choix!.map((c) => c.texte)).toStrictEqual(TRANCHES_FIN.map((t) => t.texte));
    expect(juste(choix)).toHaveLength(1);
    // Ton IA 1.5 ne finit aucune réponse : la première tranche.
    expect(faitsDuPariFin(RACINE)!.terminee).toBe(0);
    expect(juste(choix)).toStrictEqual([TRANCHES_FIN[0].texte]);
    // Une autre part, une autre tranche.
    expect(juste(choixFinDeTour(avantApres({ terminee: 0.5 }, {})))).toStrictEqual([TRANCHES_FIN[1].texte]);
    expect(juste(choixFinDeTour(avantApres({ terminee: 0.95 }, {})))).toStrictEqual([TRANCHES_FIN[2].texte]);
    // Sans le rapport de ton IA 1.5 : pas de pari.
    expect(choixFinDeTour(depot())).toBeNull();
    expect(faitsDuPariFin(depot())).toBeNull();
  });

  it('« gabarit » : un texte qui imite un jeton spécial reste fait de jetons ordinaires', () => {
    const choix = choixGabarit(RACINE);
    expect(juste(choix)).toHaveLength(1);
    expect(juste(choix)![0]).toMatch(/ordinaires/);
    const f = faitsDuPariGabarit(RACINE);
    expect(f.question).toContain('<|fin_tour|>');
    expect(f.ids.every((id) => id < PREMIER_SPECIAL)).toBe(true);
    expect(f.jetons).toBe(f.ids.length);
    // Dans la conversation assemblée, deux <|fin_tour|> seulement : un par tour, posés par forge.
    expect(f.finsDeTour).toBe(2);
  });

  it('« masque » : seules les réponses de l’assistant sont apprises, fin de tour comprise', () => {
    const choix = choixMasque(RACINE);
    expect(choix.map((c) => c.texte)).toStrictEqual(['Tous', 'Ceux des réponses de l’assistant, fin de tour comprise', 'Seulement le dernier jeton']);
    expect(juste(choix)).toStrictEqual(['Ceux des réponses de l’assistant, fin de tour comprise']);
    const f = faitsDuPariMasque(RACINE);
    expect(f.appris).toBe(f.reponse + 1); // la réponse et son <|fin_tour|>
    expect(f.appris).toBeLessThan(f.jetons);
  });

  it('« fuite » : sans masque par document, la deuxième conversation voit la première', () => {
    expect(juste(choixFuite(RACINE))).toStrictEqual(['voit la première']);
    const sansFuite = depot({
      [MESURES_PARTIE_1.fuiteConversation]: { releve_le: '2026-11-18', graine: 0, jetons_a: 14, jetons_b: 15, avec_masque: 1e-7, sans_masque: 1e-6 },
    });
    expect(juste(choixFuite(sansFuite))).toStrictEqual(['est calculée comme si elle était seule']);
  });

  it('« consignes » : trois tranches de la part des invites respectées par ton IA 1.7, null sans son rapport', () => {
    expect(choixConsignes(depot())).toBeNull();
    for (const [part, rang] of [[0.2, 0], [0.3, 1], [0.45, 2]] as const) {
      const choix = choixConsignes(avantApres({}, { invite: part }));
      expect(choix!.map((c) => c.texte)).toStrictEqual(TRANCHES_CONSIGNES.map((t) => t.texte));
      expect(juste(choix), String(part)).toStrictEqual([TRANCHES_CONSIGNES[rang].texte]);
    }
    expect(TRANCHES_CONSIGNES[0].texte).toBe(`Moins de 25${FINE}%`);
  });

  it('« oubli » : monte, baisse ou ne bouge pas, à 0,01 près ; null sans les deux rapports', () => {
    expect(choixOubli(depot())).toBeNull();
    expect(choixOubli(depot({ [FICHIERS_ETAPES['1.5@1.7']]: rapport17('ton-ia-1.5', {}) }))).toBeNull();
    expect(TOLERANCE_OUBLI).toBe(0.01);
    const cas = [
      [2.35, 2.5, 'monte'],
      [2.35, 2.2, 'baisse'],
      [2.35, 2.355, 'stable'],
    ] as const;
    for (const [avant, apres, sens] of cas) {
      const racine = avantApres({ oubli: avant }, { oubli: apres });
      expect(sensDeLOubli(racine), `${avant} puis ${apres}`).toBe(sens);
      expect(juste(choixOubli(racine))).toHaveLength(1);
    }
  });

  it('la phrase de l’oubli change de sens avec les rapports, et exiger refuse un sens annoncé à tort', () => {
    const monte = avantApres({ oubli: 2.35 }, { oubli: 2.5 });
    const baisse = avantApres({ oubli: 2.35 }, { oubli: 2.2 });
    expect(phraseDeLOubli(monte)).toMatch(/monte/);
    expect(phraseDeLOubli(baisse)).toMatch(/baisse/);
    expect(phraseDeLOubli(monte)).not.toBe(phraseDeLOubli(baisse));
    expect(() => exigerSensDeLOubli('monte', monte)).not.toThrow();
    expect(() => exigerSensDeLOubli('monte', baisse)).toThrow(/Exemple devenu faux/);
    expect(phraseDeLOubli(depot())).toBeNull();
  });

  it('l’ouverture : la réponse de ton IA 1.5 à « Qui es-tu ? », telle quelle', () => {
    const r15 = lireRapportEtape('1.5@1.7', RACINE)!;
    const reponse = reponseALInvite(r15, INVITE_DE_L_OUVERTURE);
    expect(reponse.invite).toBe('Qui es-tu ?');
    expect(reponse.terminee).toBe(false);
    expect(() => reponseALInvite({ ...r15, echantillons: [] }, INVITE_DE_L_OUVERTURE)).toThrow(/Qui es-tu/);
  });
});

describe('la figure de l’empaquetage', () => {
  it('quatre longueurs de rangée, calculées par le jumeau de BFD, sans NaN', () => {
    const figure = empaquetagesDeLaFigure(RACINE);
    expect(figure.resultats.map((r) => r.longueur)).toStrictEqual([...LONGUEURS_DE_RANGEE]);
    const longueurs = figure.longueurs;
    for (const r of figure.resultats) {
      const bfd = empaqueterLongueurs(longueurs, r.longueur + 1);
      expect(r.places).toBe(r.longueur + 1);
      expect(r.rangees).toBe(bfd.rangees.length);
      expect(r.ecartes).toBe(bfd.ecartes);
      expect(r.occupees).toBe(bfd.rangees.flat().reduce((s, i) => s + longueurs[i], 0));
      expect(r.premieres).toStrictEqual(bfd.rangees.slice(0, r.premieres.length).map((rangee) => rangee.map((i) => longueurs[i])));
      expect(Number.isFinite(r.occupees / (r.rangees * r.places))).toBe(true);
    }
  });

  it('avant le relevé du jeu, la liste de référence des attendus ; après, les longueurs du jeu', () => {
    if (lireLongueurs(RACINE) === null) {
      const figure = empaquetagesDeLaFigure(RACINE);
      expect(figure.source).toBe('reference');
      expect(figure.longueurs.length).toBeGreaterThan(0);
    }
    const racine = depot({
      [FICHIER_LONGUEURS_SFT_17]: { jeu: 'sft-1.7', releve_le: '2026-11-20', longueur_des_rangees: 2048, histogramme: [[10, 3], [900, 2]] },
      'projets/1.7-conversation/tests/attendus.json': { speciaux: [], conversations: [], empaquetages: [] },
    });
    const figure = empaquetagesDeLaFigure(racine);
    expect(figure.source).toBe('jeu');
    expect(figure.longueurs).toStrictEqual([10, 10, 10, 900, 900]);
    expect(figure.resultats[0].ecartes).toBe(2); // 900 dépasse 513
  });
});
