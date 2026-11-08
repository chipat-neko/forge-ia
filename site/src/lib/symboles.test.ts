// Les extraits par symbole : sur une source écrite ici, puis sur le vrai
// code de forge (lu sans jamais être modifié).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { extraireSymbole } from './symboles';

const src =
  'import x\n\n@decorateur\ndef f(a):\n    """Doc."""\n    return a\n\n\nclass C:\n    """Doc de C."""\n\n    def m(self):\n        """Doc\n        sur deux lignes."""\n        if self:\n\n            return 1\n        return 2\n\n# commentaire après\nY = 1\n';

describe('extraireSymbole', () => {
  it('une fonction décorée, sans sa docstring ou avec', () => {
    expect(extraireSymbole(src, 'f')).toBe('@decorateur\ndef f(a):\n    return a');
    expect(extraireSymbole(src, 'f', '?', { docstring: true })).toContain('"""Doc."""');
  });

  it('une méthode : indentation enlevée, docstring sur deux lignes retirée, ligne vide gardée', () => {
    expect(extraireSymbole(src, 'C.m')).toBe('def m(self):\n    if self:\n\n        return 1\n    return 2');
    expect(extraireSymbole(src, 'C.m', '?', { docstring: true })).toContain('sur deux lignes."""');
  });

  it('une classe entière, sans le commentaire qui suit au même niveau', () => {
    const c = extraireSymbole(src, 'C');
    expect(c.startsWith('class C:\n    def m(self):')).toBe(true);
    expect(c.endsWith('        return 2')).toBe(true);
  });

  it('async def, fins de ligne Windows et docstring avec guillemets simples', () => {
    const s = "async def g(x):\r\n    '''Doc.'''\r\n    return x\r\n";
    expect(extraireSymbole(s, 'g')).toBe('async def g(x):\n    return x');
  });

  it('un symbole manquant dit quoi faire', () => {
    expect(() => extraireSymbole(src, 'g', 'a.py')).toThrow('Symbole introuvable : g dans a.py');
    expect(() => extraireSymbole(src, 'C.absente', 'a.py')).toThrow('Symbole introuvable : C.absente dans a.py');
    expect(() => extraireSymbole(src, 'm', 'a.py')).toThrow('Symbole introuvable');
  });

  it('une méthode ne se confond pas avec celle d’une autre classe', () => {
    const s = 'class A:\n    def forward(self):\n        return 1\n\n\nclass B:\n    def forward(self):\n        return 2\n';
    expect(extraireSymbole(s, 'B.forward')).toBe('def forward(self):\n    return 2');
  });

  it('une signature sur plusieurs lignes n’arrête pas l’extrait', () => {
    const s = 'def h(\n    a: int,\n    b: dict[str, int] = {},\n) -> int:\n    return a\n\nZ = 1\n';
    expect(extraireSymbole(s, 'h')).toBe('def h(\n    a: int,\n    b: dict[str, int] = {},\n) -> int:\n    return a');
  });

  describe('sur le vrai code de forge', () => {
    const t = readFileSync('../projets/forge/forge/modele/transformer.py', 'utf8');

    it('Attention.forward et MLP.forward', () => {
      expect(extraireSymbole(t, 'Attention.forward').split('\n')[0]).toBe(
        'def forward(self, x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:',
      );
      expect(extraireSymbole(t, 'MLP.forward')).toBe(
        'def forward(self, x: Tensor) -> Tensor:\n    return self.proj_basse(F.silu(self.proj_porte(x)) * self.proj_haute(x))',
      );
    });

    it('Bloc.forward tient en 3 lignes', () => {
      expect(extraireSymbole(t, 'Bloc.forward').split('\n')).toHaveLength(3);
    });

    it('rope_cos_sin : signature sur plusieurs lignes, docstring retirée', () => {
      const r = extraireSymbole(t, 'rope_cos_sin').split('\n');
      expect(r[0]).toBe('def rope_cos_sin(');
      expect(r.join('\n')).toContain(') -> tuple[Tensor, Tensor]:');
      expect(r.join('\n')).not.toContain('Cosinus et sinus');
    });

    it('_pas_d_optimisation : signature sur plusieurs lignes, corps entier', () => {
      const b = readFileSync('../projets/forge/forge/entrainement/boucle.py', 'utf8');
      const e = extraireSymbole(b, '_pas_d_optimisation').split('\n');
      expect(e[0]).toBe('def _pas_d_optimisation(');
      expect(e[1]).toBe('    modele: nn.Module,');
      const finSig = e.findIndex((l) => /^\).*:$/.test(l));
      expect(finSig).toBeGreaterThan(5);
      expect(e.length).toBeGreaterThan(finSig + 3);
      expect(e.slice(finSig + 1).every((l) => l === '' || l.startsWith('    '))).toBe(true);
    });
  });
});
