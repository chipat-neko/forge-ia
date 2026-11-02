import { describe, expect, it } from 'vitest';
import { typographier } from './typo';

const FINE = '\u202F';
const APOSTROPHE = '\u2019';

describe('typographier', () => {
  it('met une espace fine insécable avant ? ! ; :', () => {
    expect(typographier('Pourquoi découper ?')).toBe(`Pourquoi découper${FINE}?`);
    expect(typographier('Attention !')).toBe(`Attention${FINE}!`);
    expect(typographier('un ; deux')).toBe(`un${FINE}; deux`);
    expect(typographier('Les données : où les trouver')).toBe(`Les données${FINE}: où les trouver`);
  });

  it("remplace aussi l'espace insécable ordinaire (U+00A0)", () => {
    expect(typographier('Pourquoi\u00A0?')).toBe(`Pourquoi${FINE}?`);
    expect(typographier('Voici\u00A0: la suite')).toBe(`Voici${FINE}: la suite`);
  });

  it("met une espace fine insécable à l'intérieur des guillemets", () => {
    expect(typographier('« les forgerons »')).toBe(`«${FINE}les forgerons${FINE}»`);
    expect(typographier('«forge»')).toBe(`«${FINE}forge${FINE}»`);
    expect(typographier('« forge»')).toBe(`«${FINE}forge${FINE}»`);
    expect(typographier('«forge »')).toBe(`«${FINE}forge${FINE}»`);
    expect(typographier('«\u00A0forge\u00A0»')).toBe(`«${FINE}forge${FINE}»`);
  });

  it('traite les guillemets collés à un chiffre ou à une ponctuation', () => {
    expect(typographier('«2024»')).toBe(`«${FINE}2024${FINE}»`);
    expect(typographier('«Pourquoi?»')).toBe(`«${FINE}Pourquoi?${FINE}»`);
  });

  it('combine guillemets et ponctuation', () => {
    expect(typographier('Il dit : « Pourquoi ? »')).toBe(
      `Il dit${FINE}: «${FINE}Pourquoi${FINE}?${FINE}»`,
    );
  });

  it("n'ajoute rien devant ; : ! ? quand il n'y avait pas d'espace", () => {
    expect(typographier('https://exemple.fr et 16:9')).toBe('https://exemple.fr et 16:9');
    expect(typographier('Quoi?')).toBe('Quoi?');
    expect(typographier('a;b')).toBe('a;b');
    expect(typographier('Stop!')).toBe('Stop!');
    expect(typographier('http://exemple.fr/page?x=1&y=2')).toBe('http://exemple.fr/page?x=1&y=2');
  });

  it("ne touche pas aux guillemets vides, aux espaces simples et au reste du texte", () => {
    expect(typographier('«»')).toBe('«»');
    expect(typographier('Un texte simple, sans rien de spécial.')).toBe(
      'Un texte simple, sans rien de spécial.',
    );
    expect(typographier('')).toBe('');
  });

  it('garde les retours à la ligne et les espaces multiples', () => {
    expect(typographier('Une ligne\nPourquoi ?\n  Retrait')).toBe(
      `Une ligne\nPourquoi${FINE}?\n  Retrait`,
    );
  });

  it('est idempotent', () => {
    const textes = [
      'Pourquoi découper ?',
      'Il dit : « Pourquoi ? »',
      '«forge»',
      'https://exemple.fr et 16:9',
      'Attention !',
    ];
    for (const texte of textes) {
      const une = typographier(texte);
      expect(typographier(une)).toBe(une);
    }
  });

  it("courbe l'apostrophe droite placée entre deux lettres", () => {
    expect(typographier("l'atelier")).toBe(`l${APOSTROPHE}atelier`);
    expect(typographier("aujourd'hui")).toBe(`aujourd${APOSTROPHE}hui`);
    expect(typographier("Qu'il est l'heure d'apprendre")).toBe(
      `Qu${APOSTROPHE}il est l${APOSTROPHE}heure d${APOSTROPHE}apprendre`,
    );
    // Lettres accentuées et capitales.
    expect(typographier("à l'été, L'IA")).toBe(`à l${APOSTROPHE}été, L${APOSTROPHE}IA`);
    // Lettre accentuée écrite en deux caractères (e + accent combinant).
    expect(typographier("cafe\u0301'e")).toBe(`cafe\u0301${APOSTROPHE}e`);
  });

  it("laisse l'apostrophe droite qui n'est pas entre deux lettres", () => {
    expect(typographier("'a'")).toBe("'a'");
    expect(typographier("x = 'abc' + 'd'")).toBe("x = 'abc' + 'd'");
    expect(typographier("l' atelier")).toBe("l' atelier");
    expect(typographier("4'33")).toBe("4'33");
    expect(typographier("'")).toBe("'");
  });

  it('ne touche ni aux guillemets droits doubles ni aux apostrophes déjà courbes', () => {
    expect(typographier('un mot "brut"')).toBe('un mot "brut"');
    expect(typographier(`l${APOSTROPHE}atelier`)).toBe(`l${APOSTROPHE}atelier`);
  });

  it('reste idempotent avec les apostrophes', () => {
    const une = typographier("Qu'est-ce qu'un jeton ? « l'atelier »");
    expect(une).toBe(
      `Qu${APOSTROPHE}est-ce qu${APOSTROPHE}un jeton${FINE}? «${FINE}l${APOSTROPHE}atelier${FINE}»`,
    );
    expect(typographier(une)).toBe(une);
  });

  it('laisse intacte une espace fine déjà en place', () => {
    expect(typographier(`«${FINE}forge${FINE}»`)).toBe(`«${FINE}forge${FINE}»`);
    expect(typographier(`Quoi${FINE}?`)).toBe(`Quoi${FINE}?`);
  });
});
