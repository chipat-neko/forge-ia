// Ce que l'atelier des notes et la phrase de la DPO du chapitre 1.8 calculent dans le navigateur (atelier-1-8.ts) :
// la note d'une réponse critère par critère, avec la raison de chacun, égale aux attendus du Python sur les quarante
// textes de référence (dont les pièges du point à surveiller 3) ; les phrases des consignes, celles de forge ; l'ordre
// des notes ; le défi ; la phrase de la perte DPO, jamais NaN ni « e+ », aux bornes de ses trois nombres.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { nombre } from '../nombres';
import {
  avecConsignes,
  betaDeLIndice,
  comparerNotes,
  CRITERES,
  defiReussi,
  ECART_MAX,
  ECART_MIN,
  estLaPlusHaute,
  expliquerNote,
  INDICE_BETA_MAX,
  INDICE_BETA_MIN,
  noteEnTexte,
  noteMaximale,
  PAS_D_ECART,
  phraseDeConsigne,
  phraseDeLaPerteDpo,
  SEPARATEUR_DES_CONSIGNES,
  texteDuDefi,
  type Note,
} from './atelier-1-8';
import { deriveeDpo, perteDpo } from './dpo';
import { noteSansJustesse } from './notes';
import { FICHIERS_PARTIE_1 } from './fichiers';
import type { ConsigneDInvite, ReglagesConsigne } from './notes';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const FINE = '\u202F';

interface TexteAttendu {
  nom: string;
  texte: string;
  terminee: boolean;
  invite: [string, ReglagesConsigne][];
  mots: number;
  langue: string;
  verdicts: Record<string, boolean>;
  longueur: boolean;
  note: { terminee: number; consignes: number; francais: number; longueur: number };
}

const ATTENDUS = JSON.parse(readFileSync(`../${FICHIERS_PARTIE_1.notes}`, 'utf8')) as {
  consignes: { id: string; kwargs: ReglagesConsigne; consigne: string }[];
  textes: TexteAttendu[];
};

describe('les consignes, telles que forge les écrit', () => {
  it('la phrase de chacune des huit consignes est celle de forge (attendus du Python)', () => {
    expect(ATTENDUS.consignes).toHaveLength(8);
    for (const c of ATTENDUS.consignes) expect(phraseDeConsigne(c.id, c.kwargs), c.id).toBe(c.consigne);
  });

  it('une consigne inconnue est refusée, avec la liste des huit', () => {
    expect(() => phraseDeConsigne('rimes', {})).toThrow(/rimes.*mots_max/);
  });

  it('une invite : la question, une ligne vide, puis les consignes, séparées d’une espace (avec_consignes de forge)', () => {
    expect(SEPARATEUR_DES_CONSIGNES).toBe('\n\n');
    const consignes: ConsigneDInvite[] = [['mots_max', { n: 20 }], ['sans_virgule', {}]];
    expect(avecConsignes('Quelle est la capitale de la France ?', consignes)).toBe(
      "Quelle est la capitale de la France ?\n\nRéponds en 20 mots au plus. N'utilise aucune virgule.",
    );
    expect(avecConsignes('Bonjour.', [])).toBe('Bonjour.');
  });
});

describe('la note d’une réponse, critère par critère', () => {
  it('les cinq critères de forge, du plus important au moins important', () => {
    expect([...CRITERES]).toStrictEqual(['terminee', 'juste', 'consignes', 'francais', 'longueur']);
  });

  it('sur les quarante textes de référence (pièges compris) : la note, les verdicts, les mots et la langue du Python', () => {
    expect(ATTENDUS.textes.length).toBeGreaterThanOrEqual(40);
    for (const t of ATTENDUS.textes) {
      const e = expliquerNote(t.texte, t.terminee, t.invite);
      // Une question n'a pas de réponse à vérifier : « juste » est acquis, comme dans forge.
      expect(e.note, t.nom).toStrictEqual({ terminee: t.note.terminee, juste: 1, consignes: t.note.consignes, francais: t.note.francais, longueur: t.note.longueur });
      // Les valeurs sont celles du jumeau, noteSansJustesse, et « juste » est acquis.
      expect(e.note, t.nom).toStrictEqual({ ...noteSansJustesse(t.texte, t.terminee, t.invite), juste: 1 });
      expect(e.mots, t.nom).toBe(t.mots);
      expect(e.langue, t.nom).toBe(t.langue);
      expect(e.consignes.map((c) => [c.id, c.respectee]), t.nom).toStrictEqual(t.invite.map(([id]) => [id, t.verdicts[id]]));
      expect(e.criteres.map((c) => c.nom), t.nom).toStrictEqual([...CRITERES]);
      for (const c of e.criteres) {
        expect(c.verdict, `${t.nom}, ${c.nom}`).toBe(c.valeur === c.maximum);
        expect(c.raison.length, `${t.nom}, ${c.nom}`).toBeGreaterThan(3);
        expect(c.raison, `${t.nom}, ${c.nom}`).not.toMatch(/NaN|undefined|Infinity/);
      }
    }
  });

  it('chaque raison dit le pourquoi, comme expliquer_note du projet', () => {
    const invite: ConsigneDInvite[] = [['mots_max', { n: 20 }], ['sans_virgule', {}]];
    const e = expliquerNote('Paris, la capitale.', true, invite);
    const raison = (nom: string) => e.criteres.find((c) => c.nom === nom)!.raison;
    expect(raison('terminee')).toBe('elle a fini son tour');
    expect(raison('juste')).toBe(`une question n’a pas de réponse à vérifier${FINE}: le critère est acquis`);
    expect(raison('consignes')).toBe('1 consigne sur 2');
    expect(raison('francais')).toBe(`moins de 3 mots outils${FINE}: la langue ne se juge pas, et le critère passe`);
    expect(raison('longueur')).toBe('3 mots');
    expect(e.consignes.map((c) => c.consigne)).toStrictEqual(['Réponds en 20 mots au plus.', "N'utilise aucune virgule."]);
    const coupee = expliquerNote('The capital of France is Paris and it is beautiful.', false, invite);
    expect(coupee.criteres.find((c) => c.nom === 'terminee')!.raison).toBe('elle est coupée par la limite de jetons');
    expect(coupee.criteres.find((c) => c.nom === 'francais')!.raison).toBe('dans une autre langue que le français');
    expect(expliquerNote('Oui', true, []).criteres.find((c) => c.nom === 'longueur')!.raison).toBe('1 mot, moins de 3');
    expect(expliquerNote('Paris est belle, Lyon aussi.', true, invite).criteres.find((c) => c.nom === 'consignes')!.raison).toBe('1 consigne sur 2');
    expect(expliquerNote('Paris est belle et Lyon aussi.', true, invite).criteres.find((c) => c.nom === 'consignes')!.raison).toBe('2 consignes sur 2');
    expect(expliquerNote('mot '.repeat(301), true, []).criteres.find((c) => c.nom === 'longueur')!.raison).toBe('301 mots, plus de 300');
  });

  it('le texte vide, les chiffres seuls et dix mille caractères : une note, jamais NaN, en moins de 200 ms', () => {
    for (const nom of ['vide', 'chiffres-seuls', 'dix-mille-caracteres']) {
      const t = ATTENDUS.textes.find((x) => x.nom === nom)!;
      const debut = performance.now();
      const e = expliquerNote(t.texte, t.terminee, t.invite);
      expect(performance.now() - debut, nom).toBeLessThan(200);
      expect(Object.values(e.note).every(Number.isInteger), nom).toBe(true);
      expect(noteEnTexte(e.note), nom).not.toMatch(/NaN/);
    }
  });
});

describe('l’ordre des notes', () => {
  const note = (terminee: number, consignes: number, francais = 1, longueur = 1): Note => ({ terminee, juste: 1, consignes, francais, longueur });

  it('le premier critère qui diffère décide, comme un NamedTuple de Python', () => {
    expect(comparerNotes(note(1, 0), note(0, 2))).toBeGreaterThan(0); // finie bat coupée, même sans consigne
    expect(comparerNotes(note(1, 1), note(1, 2))).toBeLessThan(0);
    expect(comparerNotes(note(1, 2, 0), note(1, 1, 1))).toBeGreaterThan(0); // les consignes passent avant le français
    expect(comparerNotes(note(1, 2), note(1, 2))).toBe(0);
  });

  it('la note la plus haute : tout au maximum, toutes les consignes respectées', () => {
    expect(noteMaximale(2)).toStrictEqual({ terminee: 1, juste: 1, consignes: 2, francais: 1, longueur: 1 });
    expect(noteEnTexte(noteMaximale(2))).toBe('(1, 1, 2, 1, 1)');
    const invite: ConsigneDInvite[] = [['mots_max', { n: 20 }], ['sans_virgule', {}]];
    expect(estLaPlusHaute(expliquerNote('Paris est la capitale de la France.', true, invite))).toBe(true);
    expect(estLaPlusHaute(expliquerNote('Paris est la capitale de la France.', false, invite))).toBe(false);
    expect(estLaPlusHaute(expliquerNote('Paris, la capitale de la France.', true, invite))).toBe(false);
  });
});

describe('le défi : écrire sa propre réponse qui obtient la note la plus haute', () => {
  const invite: ConsigneDInvite[] = [['mots_max', { n: 20 }], ['sans_virgule', {}]];
  const paire = [
    { lettre: 'A', texte: 'La capitale de la France est Paris, une grande ville au bord de la Seine.' },
    { lettre: 'B', texte: 'Paris est la capitale de la France.' },
  ];
  const defi = (texte: string, finie = true) => {
    const e = expliquerNote(texte, finie, invite);
    return { reussi: defiReussi(e, texte, paire), texte: texteDuDefi(e, texte, paire) };
  };

  it('réussi seulement à la note la plus haute, et le texte le dit', () => {
    expect(defi('La capitale de la France est Paris.')).toStrictEqual({ reussi: true, texte: `Défi réussi${FINE}: ta réponse a la note la plus haute, (1, 1, 2, 1, 1).` });
    expect(defi('La capitale de la France est Paris, au bord de la Seine.')).toStrictEqual({ reussi: false, texte: `Pas encore${FINE}: 1 consigne sur 2.` });
    expect(defi('Paris', false).texte).toBe(`Pas encore${FINE}: elle est coupée par la limite de jetons${FINE}; 1 mot, moins de 3.`);
  });

  it('refuse une copie d’une réponse de la paire, même à une espace près', () => {
    for (const copie of ['Paris est la capitale de la France.', '  Paris est la   capitale de la France.\n']) {
      expect(estLaPlusHaute(expliquerNote(copie, true, invite))).toBe(true);
      expect(defi(copie)).toStrictEqual({ reussi: false, texte: `Pas encore${FINE}: c’est la réponse B de la paire. Écris la tienne.` });
    }
  });
});

describe('la phrase de la perte DPO', () => {
  const coins: [number, number, number][] = [];
  for (const i of [INDICE_BETA_MIN, INDICE_BETA_MAX]) for (const ec of [ECART_MIN, ECART_MAX]) for (const er of [ECART_MIN, ECART_MAX]) coins.push([i, ec, er]);

  it('ses bornes : β de 0,05 à 0,5, des écarts de −3 à +3 nats par pas de 0,5', () => {
    expect(betaDeLIndice(INDICE_BETA_MIN)).toBe(0.05);
    expect(betaDeLIndice(INDICE_BETA_MAX)).toBe(0.5);
    expect(betaDeLIndice(3)).toBe(0.15); // i ÷ 20, sans la poussière de 3 × 0,05
    expect([ECART_MIN, ECART_MAX, PAS_D_ECART]).toStrictEqual([-3, 3, 0.5]);
  });

  it('aux huit coins : la perte de dpo.ts, jamais NaN ni « e+ »', () => {
    for (const [i, ec, er] of coins) {
      const beta = betaDeLIndice(i);
      const p = phraseDeLaPerteDpo(beta, ec, er);
      expect(p.perte, `${beta} ${ec} ${er}`).toBe(nombre(perteDpo(beta, ec, er), 3));
      expect(p.force).toBe(nombre(-deriveeDpo(beta, ec, er), 3));
      expect(`${p.perte} ${p.force} ${p.suite}`).not.toMatch(/NaN|Infinity|undefined|e\+|\de-\d/);
    }
  });

  it('dit le sens du gradient d’après la dérivée : la choisie vers le haut et la rejetée vers le bas, avec la même force', () => {
    // La dérivée selon la choisie est négative (la monter fait baisser la perte), celle selon la rejetée est l'opposée.
    const p = phraseDeLaPerteDpo(0.1, 1, -1);
    expect(deriveeDpo(0.1, 1, -1)).toBeLessThan(0);
    expect(p.suite).toMatch(/la descente de gradient pousse la choisie vers le haut et la rejetée vers le bas/);
    // L'ordre de la paire décide de la force : à l'envers (z < 0), plus de la moitié de β ; dans l'ordre, moins.
    expect(phraseDeLaPerteDpo(0.1, -1, 1).suite).toMatch(/à l’envers/);
    expect(phraseDeLaPerteDpo(0.1, 1, -1).suite).toMatch(/déjà dans le bon ordre/);
    expect(phraseDeLaPerteDpo(0.1, 2, 2).suite).toMatch(/à égalité/);
    // Sans écart entre les deux, la perte vaut ln 2, quelle que soit leur hauteur.
    expect(phraseDeLaPerteDpo(0.3, 2, 2).perte).toBe(nombre(Math.LN2, 3));
    expect(phraseDeLaPerteDpo(0.3, -3, -3).perte).toBe(nombre(Math.LN2, 3));
  });
});
