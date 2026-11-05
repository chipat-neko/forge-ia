// Le jumeau du neurone à seuil : neurone.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (projets/0.5-reseau/tests/attendus.json) est écrit par
// `uv run --extra cpu python -m premier_reseau.attendus`. Pour chaque porte, le
// jumeau doit trouver le même meilleur réglage, et le même compte de points
// bien classés pour chacun des 729 réglages de la grille, au bit près
// (toStrictEqual). Les sections entrainement et graines ne sont pas refaites :
// le site les lit telles quelles.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { bienClasses, GRILLE, meilleurReglage, POINTS, PORTES, type Porte, type Reglage, sortieSeuil } from './neurone';

interface AttenduPorte {
  porte: Porte;
  sorties: number[];
  meilleur_reglage: Reglage;
  bien_classes: number[][][];
}

interface AttendusReseau {
  neurone: { points: number[][]; grille: number[]; portes: AttenduPorte[] };
  entrainement: { nb_poids: number };
}

// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/0.5-reseau/tests/attendus.json', 'utf8')) as AttendusReseau;

describe('jumeau du Python : le neurone à seuil de 0.5', () => {
  it('les points, la grille et les portes sont ceux du Python', () => {
    expect(POINTS).toStrictEqual(ATTENDUS.neurone.points);
    expect(GRILLE).toStrictEqual(ATTENDUS.neurone.grille);
    expect(Object.keys(PORTES)).toStrictEqual(ATTENDUS.neurone.portes.map((p) => p.porte));
    for (const p of ATTENDUS.neurone.portes) {
      expect(PORTES[p.porte], p.porte).toStrictEqual(p.sorties);
    }
  });

  it('le meilleur réglage de chaque porte', () => {
    expect(ATTENDUS.neurone.portes).toHaveLength(3);
    for (const p of ATTENDUS.neurone.portes) {
      expect(meilleurReglage(p.porte), p.porte).toStrictEqual(p.meilleur_reglage);
    }
    // ET et OU : les 4 points ; le OU exclusif : 3 au mieux.
    expect(ATTENDUS.neurone.portes.map((p) => p.meilleur_reglage[0])).toStrictEqual([4, 4, 3]);
  });

  it('le compte de chacun des 729 réglages de la grille', () => {
    let reglages = 0;
    for (const p of ATTENDUS.neurone.portes) {
      const comptes = GRILLE.map((w1) => GRILLE.map((w2) => GRILLE.map((b) => bienClasses([w1, w2], b, p.porte))));
      expect(comptes, p.porte).toStrictEqual(p.bien_classes);
      reglages += comptes.flat(2).length;
    }
    expect(reglages).toBe(3 * 729);
  });

  it('l’exemple de la porte ET, et des poids nuls', () => {
    // Le réglage de départ de l'atelier : w = (1, 1) et b = 0 classent 2 points sur 4, puis b = −1,5 les classe tous.
    expect(bienClasses([1, 1], 0, 'et')).toBe(2);
    expect(bienClasses([1, 1], -1.5, 'et')).toBe(4);
    expect(POINTS.map((x) => sortieSeuil([1, 1], -1.5, x))).toStrictEqual([0, 0, 0, 1]);
    // Tout à 0 : la somme vaut 0 partout, et 0 n'est pas plus grand que 0.
    expect(POINTS.map((x) => sortieSeuil([0, 0], 0, x))).toStrictEqual([0, 0, 0, 0]);
    expect(POINTS.map((x) => sortieSeuil([-0, -0], -0, x))).toStrictEqual([0, 0, 0, 0]);
  });

  it('le nombre de poids du réseau 2-2-1 vient des attendus', () => {
    // Compté par le Python sur le réseau lui-même (nb_poids) : le chapitre le lit ici, sans le taper.
    expect(ATTENDUS.entrainement.nb_poids).toBe(9);
  });
});
