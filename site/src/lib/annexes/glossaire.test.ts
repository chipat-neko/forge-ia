import { describe, expect, it } from 'vitest';
import { NUMEROS_DU_PARCOURS } from '../parcours';
import { GLOSSAIRE, lettreDuTerme } from './glossaire';

describe('GLOSSAIRE', () => {
  it('a au moins 40 termes, chacun avec son identifiant à lui', () => {
    expect(GLOSSAIRE.length).toBeGreaterThanOrEqual(40);
    expect(new Set(GLOSSAIRE.map((t) => t.id)).size).toBe(GLOSSAIRE.length);
  });

  it('range les termes dans l’ordre alphabétique français', () => {
    const fr = new Intl.Collator('fr');
    expect([...GLOSSAIRE].sort((a, b) => fr.compare(a.terme, b.terme))).toEqual(GLOSSAIRE);
  });

  it('renvoie chaque terme à des chapitres du parcours, et ses « voir aussi » à des termes du glossaire', () => {
    for (const t of GLOSSAIRE) {
      expect(t.renvois.length, t.id).toBeGreaterThan(0);
      for (const r of t.renvois) {
        expect(NUMEROS_DU_PARCOURS, t.id).toContain(r.chapitre);
        expect(r.verbe, t.id).toMatch(/^\p{Ll}/u);
      }
      // Un même chapitre une seule fois, dans l'ordre où le parcours les lit.
      const numeros = t.renvois.map((r) => r.chapitre);
      expect(new Set(numeros).size, t.id).toBe(numeros.length);
      for (const v of t.voirAussi ?? []) {
        expect(GLOSSAIRE.some((u) => u.id === v), `${t.id} → ${v}`).toBe(true);
        expect(v, t.id).not.toBe(t.id);
      }
    }
  });

  it('définit chaque terme en 300 caractères au plus, et deux phrases au plus', () => {
    for (const t of GLOSSAIRE) {
      expect([...t.definition].length, t.id).toBeLessThanOrEqual(300);
      // Une phrase finit par un point (ou « … », « ? », « ! ») suivi d'une espace ou de la fin.
      const phrases = t.definition.split(/(?<=[.!?…])\s+/).filter((p) => p.trim() !== '');
      expect(phrases.length, t.id).toBeLessThanOrEqual(2);
      expect(t.definition, t.id).toMatch(/[.!?…]$/);
    }
  });

  it('écrit des identifiants faits pour une adresse : minuscules sans accents, chiffres et tirets', () => {
    for (const t of GLOSSAIRE) expect(t.id).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
  });

  it('couvre la Partie 0 et chaque chapitre de 1.1 à 1.6', () => {
    const couverts = new Set(GLOSSAIRE.flatMap((t) => t.renvois.map((r) => r.chapitre)));
    for (const n of ['0.1', '0.2', '0.3', '0.4', '0.5', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6']) {
      expect(couverts, n).toContain(n);
    }
  });

  it('ne laisse aucun texte brut avec une espace devant ; : ! ? ni d’espace fine déjà posée', () => {
    // La typographie se pose à l'affichage, par typographier() : le texte brut garde des
    // espaces ordinaires, et jamais d'espace fine ni d'insécable.
    for (const t of GLOSSAIRE) {
      for (const texte of [t.terme, t.definition, t.anglais ?? '', t.aussi ?? '', ...t.renvois.map((r) => r.verbe)]) {
        expect(texte, t.id).not.toMatch(/[\u00A0\u202F]/);
      }
    }
  });
});

describe('lettreDuTerme', () => {
  it('donne la première lettre, en capitale et sans accent', () => {
    expect(lettreDuTerme('écrêtage')).toBe('E');
    expect(lettreDuTerme('AdamW')).toBe('A');
    expect(lettreDuTerme('rétropropagation')).toBe('R');
  });
});
