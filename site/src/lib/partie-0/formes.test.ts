// Le jumeau des formes : formes.ts refait exactement les attendus du Python.
//
// Le fichier d'attendus (projets/0.4-tenseurs/tests/attendus-formes.json) est
// écrit par `uv run --extra cpu python -m tenseurs.attendus`. Ses formes ne
// viennent pas des règles du projet, mais de PyTorch lui-même
// (torch.broadcast_shapes et torch.matmul) : sur les 1 521 paires de formes de
// 1 à 3 dimensions de tailles 1 à 3, le jumeau doit trouver les mêmes formes
// que PyTorch, ou null là où PyTorch refuse (toStrictEqual).

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { ecrireForme, formeDiffusee, formeProduit, memoireOctets } from './formes';

interface AttendusFormes {
  formes: { forme: number[]; texte: string }[];
  paires: { a: number[]; b: number[]; diffusion: number[] | null; produit: number[] | null }[];
  memoire: { forme: number[]; dtype: string; octets_par_nombre: number; octets: number }[];
  exemples: Record<string, unknown>;
}

// Vitest tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(
  readFileSync('../projets/0.4-tenseurs/tests/attendus-formes.json', 'utf8'),
) as AttendusFormes;

describe('jumeau du Python : les formes de 0.4, contre PyTorch', () => {
  it('les 1 521 paires : la diffusion (a + b) et le produit matriciel (a @ b)', () => {
    expect(ATTENDUS.paires).toHaveLength(1521);
    for (const p of ATTENDUS.paires) {
      const nom = `${ecrireForme(p.a)} et ${ecrireForme(p.b)}`;
      expect(formeDiffusee(p.a, p.b), `diffusion, ${nom}`).toStrictEqual(p.diffusion);
      expect(formeProduit(p.a, p.b), `produit, ${nom}`).toStrictEqual(p.produit);
    }
  });

  it('les paires des quatre sortes sont là : les deux règles, l’une seulement, aucune', () => {
    const sortes = new Set(ATTENDUS.paires.map((p) => `${p.diffusion === null}-${p.produit === null}`));
    expect([...sortes].sort()).toStrictEqual(['false-false', 'false-true', 'true-false', 'true-true']);
  });

  it('les 39 formes s’écrivent comme en Python : (4,) pour une dimension', () => {
    expect(ATTENDUS.formes).toHaveLength(39);
    for (const f of ATTENDUS.formes) {
      expect(ecrireForme(f.forme), f.texte).toBe(f.texte);
    }
    expect(ecrireForme([4])).toBe('(4,)');
    expect(ecrireForme([])).toBe('()');
    expect(ecrireForme([2, 1, 3])).toBe('(2, 1, 3)');
  });

  it('la mémoire : le nombre de nombres, fois la taille d’un nombre', () => {
    expect(memoireOctets([4096, 4096], 4)).toBe(67_108_864);
    expect(memoireOctets([4096, 4096], 2)).toBe(33_554_432);
    expect(ATTENDUS.memoire.length).toBeGreaterThan(0);
    for (const c of ATTENDUS.memoire) {
      expect(memoireOctets(c.forme, c.octets_par_nombre), `${ecrireForme(c.forme)} en ${c.dtype}`).toBe(c.octets);
    }
  });
});

describe('formes.ts : les exemples du chapitre et les cas hors du tableau', () => {
  it('la diffusion aligne les formes par la droite', () => {
    expect(formeDiffusee([3, 1], [4])).toStrictEqual([3, 4]);
    expect(formeDiffusee([2, 3], [3, 2])).toBeNull();
    // L'exercice du notebook : (2, 1, 3) + (4, 1).
    expect(formeDiffusee([2, 1, 3], [4, 1])).toStrictEqual([2, 4, 3]);
    expect(formeDiffusee([], [2, 3])).toStrictEqual([2, 3]);
    expect(formeDiffusee([], [])).toStrictEqual([]);
    expect(formeDiffusee([0], [1])).toStrictEqual([0]);
    expect(formeDiffusee([0], [3])).toBeNull();
  });

  it('le produit matriciel suit torch.matmul', () => {
    expect(formeProduit([2, 3], [3, 4])).toStrictEqual([2, 4]);
    expect(formeProduit([3], [3])).toStrictEqual([]);
    expect(formeProduit([5, 2, 3], [3, 4])).toStrictEqual([5, 2, 4]);
    expect(formeProduit([2, 3], [2, 3])).toBeNull();
    expect(formeProduit([2, 3], [3])).toStrictEqual([2]);
    expect(formeProduit([3], [3, 4])).toStrictEqual([4]);
    expect(formeProduit([2, 1, 3, 4], [5, 4, 2])).toStrictEqual([2, 5, 3, 2]);
    expect(formeProduit([6, 1, 5], [7, 1, 1, 5, 2])).toStrictEqual([7, 1, 6, 1, 2]);
    expect(formeProduit([2, 1], [3, 4])).toBeNull();
    expect(formeProduit([], [3])).toBeNull();
    expect(formeProduit([3], [])).toBeNull();
  });

  it('ne touche pas aux formes reçues', () => {
    const a = Object.freeze([3]);
    const b = Object.freeze([2, 3, 4]);
    expect(formeDiffusee(a, [1, 1, 1, 3])).toStrictEqual([1, 1, 1, 3]);
    expect(formeProduit(a, b)).toStrictEqual([2, 4]);
    expect(formeProduit(b, a)).toBeNull();
    expect(a).toStrictEqual([3]);
    expect(b).toStrictEqual([2, 3, 4]);
  });

  it('des formes pleines de 1, ou de 3 dimensions de taille 3 : rien ne plante', () => {
    expect(formeDiffusee([1, 1, 1], [1, 1, 1])).toStrictEqual([1, 1, 1]);
    expect(formeProduit([1, 1, 1], [1, 1, 1])).toStrictEqual([1, 1, 1]);
    expect(formeProduit([3, 3, 3], [3, 3, 3])).toStrictEqual([3, 3, 3]);
    expect(memoireOctets([], 4)).toBe(4);
    expect(memoireOctets([5, 0], 4)).toBe(0);
  });
});
