import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ANNEXES,
  PARCOURS,
  chapitresDuGroupe,
  hrefChapitre,
  hrefPartie,
  titreCourt,
  trouverChapitre,
  voisins,
} from './parcours';

describe('PARCOURS', () => {
  it('compte 5, 21, 4 et 4 chapitres par partie', () => {
    expect(PARCOURS.map((p) => p.chapitres.length)).toEqual([5, 21, 4, 4]);
  });

  it('numérote les parties de 0 à 3 avec les titres de la spécification', () => {
    expect(PARCOURS.map((p) => p.numero)).toEqual([0, 1, 2, 3]);
    expect(PARCOURS.map((p) => p.titre)).toEqual([
      'Les bases',
      'Créer son IA de zéro',
      'Hybride',
      'Assemblage',
    ]);
  });

  it('numérote les chapitres de 0.1 à 3.4, sans trou ni doublon', () => {
    const attendus = [
      ...[1, 2, 3, 4, 5].map((n) => `0.${n}`),
      ...Array.from({ length: 21 }, (_, i) => `1.${i + 1}`),
      ...[1, 2, 3, 4].map((n) => `2.${n}`),
      ...[1, 2, 3, 4].map((n) => `3.${n}`),
    ];
    expect(PARCOURS.flatMap((p) => p.chapitres.map((c) => c.numero))).toEqual(attendus);
  });

  it('range chaque chapitre dans la partie de son numéro', () => {
    for (const partie of PARCOURS) {
      for (const chapitre of partie.chapitres) {
        expect(chapitre.numero.startsWith(`${partie.numero}.`)).toBe(true);
      }
    }
  });

  it('reprend les titres exacts de la spécification', () => {
    const titre = (numero: string) => trouverChapitre(numero).chapitre.titre;
    expect(titre('0.1')).toBe("Python pour l'IA");
    expect(titre('0.2')).toBe('Les maths utiles (vecteurs, matrices, dérivées, probabilités)');
    expect(titre('0.5')).toBe('Premier réseau de neurones, à la main puis avec PyTorch');
    expect(titre('1.1')).toBe("Ce qu'est vraiment un modèle de langage");
    expect(titre('1.2')).toBe('Les données : où les trouver, les nettoyer, les licences');
    expect(titre('1.3')).toBe('Le tokenizer (BPE)');
    expect(titre('1.6')).toBe('Évaluer son modèle');
    expect(titre('1.7')).toBe('Apprendre à converser (instructions, format chat)');
    expect(titre('1.19')).toBe('Gérer un projet de A à Z en autonomie');
    expect(titre('1.21')).toBe('Sécurité et garde-fous');
    expect(titre('2.2')).toBe("L'affiner sur 16 Go (LoRA, QLoRA)");
    expect(titre('3.3')).toBe('Agents et outils (MCP…)');
    expect(titre('3.4')).toBe('Un système qui mène des projets seul');
  });

  it('groupe les chapitres de la Partie 1 en cinq groupes', () => {
    const groupes = new Map<string, string[]>();
    for (const c of PARCOURS[1].chapitres) {
      groupes.set(c.groupe ?? '(aucun)', [...(groupes.get(c.groupe ?? '(aucun)') ?? []), c.numero]);
    }
    expect([...groupes.keys()]).toEqual([
      'Le cœur : un modèle de langage',
      'Le rendre utile',
      'Voir et créer des images',
      'Agir seul',
      'Le mettre en service',
    ]);
    expect([...groupes.values()].map((l) => [l[0], l[l.length - 1], l.length])).toEqual([
      ['1.1', '1.6', 6],
      ['1.7', '1.10', 4],
      ['1.11', '1.15', 5],
      ['1.16', '1.19', 4],
      ['1.20', '1.21', 2],
    ]);
  });

  it("n'a pas de groupe hors de la Partie 1", () => {
    for (const partie of [PARCOURS[0], PARCOURS[2], PARCOURS[3]]) {
      for (const chapitre of partie.chapitres) {
        expect(chapitre.groupe).toBeUndefined();
      }
    }
  });
});

describe('trouverChapitre', () => {
  it('donne le rang dans la partie et le nombre de chapitres de la partie', () => {
    expect(trouverChapitre('1.3')).toMatchObject({ rang: 3, total: 21 });
    expect(trouverChapitre('0.1')).toMatchObject({ rang: 1, total: 5 });
    expect(trouverChapitre('3.4')).toMatchObject({ rang: 4, total: 4 });
  });

  it('renvoie la partie et le chapitre', () => {
    const trouve = trouverChapitre('1.3');
    expect(trouve.partie.numero).toBe(1);
    expect(trouve.chapitre.numero).toBe('1.3');
  });

  it('lève une erreur si le numéro est inconnu', () => {
    expect(() => trouverChapitre('9.9')).toThrow();
    expect(() => trouverChapitre('1.22')).toThrow();
    expect(() => trouverChapitre('')).toThrow();
    expect(() => trouverChapitre('1-3')).toThrow();
  });
});

describe('voisins', () => {
  it('donne le chapitre précédent et le suivant', () => {
    expect(voisins('1.3').precedent?.titre).toBe(
      'Les données : où les trouver, les nettoyer, les licences',
    );
    expect(voisins('1.3').suivant?.numero).toBe('1.4');
  });

  it('suit tout le parcours, au-delà des frontières des parties', () => {
    expect(voisins('0.5').suivant?.numero).toBe('1.1');
    expect(voisins('1.1').precedent?.numero).toBe('0.5');
    expect(voisins('1.21').suivant?.numero).toBe('2.1');
    expect(voisins('2.4').suivant?.numero).toBe('3.1');
  });

  it('ne donne rien avant le premier chapitre ni après le dernier', () => {
    expect(voisins('0.1').precedent).toBeUndefined();
    expect(voisins('3.4').suivant).toBeUndefined();
  });

  it('lève une erreur si le numéro est inconnu', () => {
    expect(() => voisins('9.9')).toThrow();
  });
});

describe('hrefChapitre', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('construit le lien à partir de la base du site', () => {
    expect(hrefChapitre('1.3')).toBe('/forge-ia/partie-1/1-3/');
    expect(hrefChapitre('0.1')).toBe('/forge-ia/partie-0/0-1/');
    expect(hrefChapitre('1.21')).toBe('/forge-ia/partie-1/1-21/');
    expect(hrefChapitre('3.4')).toBe('/forge-ia/partie-3/3-4/');
  });

  it('met une seule barre oblique entre la base et le reste, avec ou sans barre finale', () => {
    vi.stubEnv('BASE_URL', '/forge-ia');
    expect(hrefChapitre('1.3')).toBe('/forge-ia/partie-1/1-3/');
    vi.stubEnv('BASE_URL', '/forge-ia/');
    expect(hrefChapitre('1.3')).toBe('/forge-ia/partie-1/1-3/');
    vi.stubEnv('BASE_URL', '/');
    expect(hrefChapitre('1.3')).toBe('/partie-1/1-3/');
    vi.stubEnv('BASE_URL', '');
    expect(hrefChapitre('1.3')).toBe('/partie-1/1-3/');
  });
});

describe('textes des maquettes validées (accueil C et page de partie)', () => {
  it('donne un résumé à chacun des 21 chapitres de la Partie 1, et à eux seuls', () => {
    for (const partie of PARCOURS) {
      for (const chapitre of partie.chapitres) {
        if (partie.numero === 1) expect(chapitre.resume, chapitre.numero).toMatch(/\S/);
        else expect(chapitre.resume).toBeUndefined();
      }
    }
    expect(trouverChapitre('1.3').chapitre.resume).toBe(
      "Une IA ne lit pas des lettres : elle lit des nombres. Tu construis l'outil qui découpe le texte en morceaux numérotés.",
    );
  });

  it('place les quatre jalons de « ton IA » en 1.5, 1.7, 1.15 et 1.19', () => {
    const jalons = PARCOURS.flatMap((p) => p.chapitres)
      .filter((c) => c.jalon)
      .map((c) => [c.numero, c.jalon]);
    expect(jalons).toEqual([
      ['1.5', 'Ici, ton IA naît.'],
      ['1.7', 'Elle apprend à te répondre.'],
      ['1.15', 'Elle voit les images.'],
      ['1.19', 'Elle mène seule une tâche simple.'],
    ]);
  });

  it("décrit les cinq groupes de la Partie 1, dans l'ordre de ses chapitres", () => {
    const partie = PARCOURS[1];
    const noms = [...new Set(partie.chapitres.map((c) => c.groupe))];
    expect(partie.groupes?.map((g) => g.nom)).toEqual(noms);
    expect(partie.groupes?.map((g) => chapitresDuGroupe(partie, g).length)).toEqual([6, 4, 5, 4, 2]);
    for (const g of partie.groupes ?? []) {
      expect(g.resume).toMatch(/\S/);
      expect(g.gain).toMatch(/\S/);
      expect(g.note).toMatch(/\S/);
    }
  });

  it('fait partir la Partie 2 après 1.7 et la Partie 3 après 1.16', () => {
    expect(PARCOURS.map((p) => p.depart)).toEqual([undefined, undefined, '1.7', '1.16']);
  });

  it('donne à chaque partie un résumé, et des savoirs tirés de ses chapitres', () => {
    for (const partie of PARCOURS) expect(partie.resume).toMatch(/\S/);
    const savoirs = PARCOURS[1].savoirs ?? [];
    expect(savoirs.map((s) => s.chapitre)).toEqual(['1.3', '1.5', '1.7', '1.8', '1.9', '1.10', '1.15', '1.16', '1.19']);
    for (const s of savoirs) expect(trouverChapitre(s.chapitre).partie.numero).toBe(1);
  });

  it('annonce les quatre annexes de la spécification', () => {
    expect(ANNEXES.map((a) => a.titre)).toEqual([
      'Glossaire',
      'Annuaire des données, modèles et outils',
      'Calculateur de coût',
      'Matériel',
    ]);
  });
});

describe('hrefPartie', () => {
  it('construit le lien de la page de partie', () => {
    expect(hrefPartie(0)).toBe('/forge-ia/partie-0/');
    expect(hrefPartie(3)).toBe('/forge-ia/partie-3/');
  });
});

describe('titreCourt', () => {
  it('coupe au deux-points ou à la parenthèse', () => {
    expect(titreCourt('Le tokenizer (BPE)')).toBe('Le tokenizer');
    expect(titreCourt('Les données : où les trouver, les nettoyer, les licences')).toBe('Les données');
    expect(titreCourt('Le faire coder')).toBe('Le faire coder');
  });
});
