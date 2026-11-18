// L'atelier du masque et la phrase de l'empaquetage (atelier-1-7.ts) : les conversations composées par les
// bascules, leur compte calculé par le jumeau, le défi, et la règle des textes vides de Python, refaite par la
// page avant le jumeau (qui ne refait pas strip()).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { assemblerConversation, SPECIAUX_TON_IA } from './conversation';
import {
  DEUXIEMES_TOURS,
  defiReussi,
  enToursEncodes,
  etatDeLAtelier,
  LIBELLES_DE_L_ATELIER,
  morceauxDuJeton,
  NOMS_DE_L_ATELIER,
  phraseDeLEmpaquetage,
  refuserLesTextesBlancs,
  reglageDeReference,
  texteDuCompte,
  texteDuDefi,
  texteFaitDeBlancs,
  toursDeLAtelier,
  type ConversationDeReference,
} from './atelier-1-7';
import { BLANCS_PYTHON } from './nettoyeur';

// Vitest est lancé depuis site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/1.7-conversation/tests/attendus.json', 'utf8')) as {
  conversations: ConversationDeReference[];
};
const CONVERSATIONS = ATTENDUS.conversations;
const FINE = '\u202F';
const MESSAGE_VIDE = (rang: number, role: string) => `Le texte du tour ${rang} (${role}) est vide. Écris un texte ou retire ce tour.`;

describe('les conversations de l’atelier', () => {
  it('les six conversations des attendus, chacune avec son nom dans la phrase', () => {
    expect(CONVERSATIONS.map((c) => c.nom)).toStrictEqual([...NOMS_DE_L_ATELIER]);
    expect(Object.keys(LIBELLES_DE_L_ATELIER)).toStrictEqual([...NOMS_DE_L_ATELIER]);
    expect(Object.keys(DEUXIEMES_TOURS)).toStrictEqual([...NOMS_DE_L_ATELIER]);
  });

  it('le réglage de référence redonne chaque conversation telle que forge l’a assemblée, ou son erreur', () => {
    for (const c of CONVERSATIONS) {
      const nom = c.nom as (typeof NOMS_DE_L_ATELIER)[number];
      const reglage = reglageDeReference(CONVERSATIONS, nom);
      expect(toursDeLAtelier(CONVERSATIONS, reglage), nom).toStrictEqual(c.tours);
      const etat = etatDeLAtelier(CONVERSATIONS, reglage);
      if (c.erreur === null) {
        expect(etat.erreur, nom).toBeNull();
        expect(etat.lignes.flatMap((l) => l.jetons.map((j) => j.id))).toStrictEqual(c.ids);
        expect(etat.lignes.flatMap((l) => l.jetons.map((j) => j.appris))).toStrictEqual(c.appris);
        expect(etat.jetons).toBe(c.ids!.length);
        expect(etat.appris).toBe(c.appris!.filter(Boolean).length);
      } else {
        expect(etat.erreur, nom).toBe(c.erreur);
      }
    }
  });

  it('chaque combinaison des bascules : le compte est celui du jumeau, une ligne par tour', () => {
    for (const nom of NOMS_DE_L_ATELIER) {
      for (const systeme of [false, true]) {
        for (const deuxieme of [false, true]) {
          const tours = toursDeLAtelier(CONVERSATIONS, { nom, systeme, deuxieme });
          expect(tours.filter((t) => t.role === 'systeme')).toHaveLength(systeme ? 1 : 0);
          expect(tours.filter((t) => t.role === 'utilisateur')).toHaveLength(deuxieme ? 2 : 1);
          const etat = etatDeLAtelier(CONVERSATIONS, { nom, systeme, deuxieme });
          if (nom === 'reponse-vide') {
            expect(etat.erreur).toBe(MESSAGE_VIDE(systeme ? 3 : 2, 'assistant'));
            continue;
          }
          const jumeau = assemblerConversation(enToursEncodes(tours));
          expect(etat.jetons).toBe(jumeau.ids.length);
          expect(etat.appris).toBe(jumeau.appris.filter(Boolean).length);
          // Le premier jeton seul, puis une ligne par tour, ouverte par son jeton de rôle.
          expect(etat.lignes).toHaveLength(tours.length + 1);
          expect(etat.lignes[0].jetons.map((j) => j.id)).toStrictEqual([SPECIAUX_TON_IA['<|fin_texte|>']]);
          etat.lignes.slice(1).forEach((l, i) => expect(l.role).toBe(tours[i].role));
        }
      }
    }
  });

  it('le compte et le défi : plus de la moitié des jetons appris', () => {
    expect(texteDuCompte(30, 9)).toBe('30 jetons, dont 9 appris.');
    const bonjour = etatDeLAtelier(CONVERSATIONS, { nom: 'sans-systeme', systeme: false, deuxieme: false });
    const capitale = etatDeLAtelier(CONVERSATIONS, reglageDeReference(CONVERSATIONS, 'avec-systeme'));
    expect(defiReussi(bonjour)).toBe(2 * bonjour.appris > bonjour.jetons);
    expect(defiReussi(capitale)).toBe(false);
    expect(texteDuDefi(capitale)).toMatch(new RegExp(`pas encore la moitié`));
    // Au moins un réglage réussit le défi : il est faisable.
    const reussis = NOMS_DE_L_ATELIER.flatMap((nom) =>
      [false, true].flatMap((systeme) => [false, true].filter((deuxieme) => defiReussi(etatDeLAtelier(CONVERSATIONS, { nom, systeme, deuxieme })))),
    );
    expect(reussis.length).toBeGreaterThan(0);
    const vide = etatDeLAtelier(CONVERSATIONS, reglageDeReference(CONVERSATIONS, 'reponse-vide'));
    expect(defiReussi(vide)).toBe(false);
    expect(texteDuDefi(vide)).toBe(`Cette conversation n’a aucun jeton${FINE}: forge la refuse.`);
  });

  it('les espaces d’un jeton se voient', () => {
    expect(morceauxDuJeton(' capitale')).toStrictEqual([
      { texte: '␣', blanc: true },
      { texte: 'capitale', blanc: false },
    ]);
    expect(morceauxDuJeton('<|fin_tour|>')).toStrictEqual([{ texte: '<|fin_tour|>', blanc: false }]);
  });
});

describe('la règle des textes vides de Python, refaite par la page', () => {
  it('un texte fait de blancs, au sens de str.isspace(), est vide ; une lettre ou un caractère invisible non blanc ne l’est pas', () => {
    expect(texteFaitDeBlancs('')).toBe(true);
    expect(texteFaitDeBlancs(' \t\n\r\u00A0\u202F　 \u0085\u001C')).toBe(true);
    expect(texteFaitDeBlancs(String.fromCodePoint(...BLANCS_PYTHON))).toBe(true);
    // U+200B (espace sans chasse) et U+FEFF ne sont pas des blancs pour Python : strip() les garde.
    expect(texteFaitDeBlancs('\u200B')).toBe(false);
    expect(texteFaitDeBlancs('\uFEFF')).toBe(false);
    expect(texteFaitDeBlancs('  a ')).toBe(false);
    expect(texteFaitDeBlancs('🙂')).toBe(false);
  });

  it('un texte de blancs passerait le jumeau, qui ne voit que des ids : la page le refuse elle-même, avec le message de Python', () => {
    // Des blancs encodés donnent des jetons : assemblerConversation les accepte.
    const blancs = [{ role: 'utilisateur' as const, ids: [32], texte: ' ' }, { role: 'assistant' as const, ids: [32, 32], texte: '\u00A0\u202F' }];
    expect(() => assemblerConversation(blancs)).not.toThrow();
    // La page, non : le premier tour vide est nommé, comme verifier_conversation.
    expect(() => refuserLesTextesBlancs(blancs)).toThrow(MESSAGE_VIDE(1, 'utilisateur'));
    expect(() => refuserLesTextesBlancs([{ role: 'utilisateur', texte: 'Bonjour' }, { role: 'assistant', texte: '\t' }])).toThrow(MESSAGE_VIDE(2, 'assistant'));
    expect(() => refuserLesTextesBlancs([{ role: 'utilisateur', texte: 'Bonjour' }, { role: 'assistant', texte: 'Salut' }])).not.toThrow();
  });

  it('la réponse vide des attendus : la page dit l’erreur de forge, mot pour mot', () => {
    const vide = CONVERSATIONS.find((c) => c.nom === 'reponse-vide')!;
    expect(() => refuserLesTextesBlancs(vide.tours)).toThrow(vide.erreur!);
  });
});

describe('la phrase de l’empaquetage', () => {
  it('le remplissage en pourcentage, et les écartés accordés', () => {
    const base = { longueur: 512, places: 513, premieres: [] };
    expect(phraseDeLEmpaquetage({ ...base, rangees: 2, occupees: 513, ecartes: 0 })).toBe(
      `jetons, BFD remplit 50,0${FINE}% des places, et n’écarte aucun exemple.`,
    );
    expect(phraseDeLEmpaquetage({ ...base, rangees: 1, occupees: 400, ecartes: 1 })).toMatch(/et écarte 1 exemple trop long\.$/);
    expect(phraseDeLEmpaquetage({ ...base, rangees: 1, occupees: 400, ecartes: 1234 })).toMatch(new RegExp(`écarte 1${FINE}234 exemples trop longs\\.$`));
    expect(phraseDeLEmpaquetage({ ...base, rangees: 0, occupees: 0, ecartes: 3 })).not.toMatch(/NaN/);
  });
});
