import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { extraireRegion } from './regions';

const BPE = new URL('../../../projets/1.3-tokenizer/tokenizer_pedagogique/bpe.py', import.meta.url);

describe('extraireRegion', () => {
  const src = 'a\n    # region: r\n    def f():\n        return 1\n    # fin: r\nb';

  it('renvoie les lignes entre les marqueurs, sans leur indentation commune', () => {
    expect(extraireRegion(src, 'r')).toBe('def f():\n    return 1');
  });

  it('nomme la région et le fichier quand la région est introuvable', () => {
    expect(() => extraireRegion(src, 'absente', 'x.py')).toThrow('Région introuvable : absente dans x.py');
  });

  it('écrit « ? » quand le fichier n’est pas donné', () => {
    expect(() => extraireRegion(src, 'absente')).toThrow('Région introuvable : absente dans ?');
  });

  it('lève la même erreur quand la région n’est pas fermée', () => {
    const ouverte = 'a\n# region: r\ndef f():\n    pass\n';
    expect(() => extraireRegion(ouverte, 'r', 'y.py')).toThrow('Région introuvable : r dans y.py');
  });

  it('ignore une fermeture qui précède l’ouverture', () => {
    const inverse = '# fin: r\n# region: r\nx = 1\n';
    expect(() => extraireRegion(inverse, 'r', 'z.py')).toThrow('Région introuvable : r dans z.py');
  });

  it('accepte des marqueurs au début de la ligne', () => {
    const colonne0 = '# region: r\ndef f():\n    return 1\n# fin: r\n';
    expect(extraireRegion(colonne0, 'r')).toBe('def f():\n    return 1');
  });

  it('retire les marqueurs des régions imbriquées, mais garde leur code', () => {
    const imbriquees = [
      '# region: grande',
      'def f():',
      '    # region: petite',
      '    x = 1',
      '    # fin: petite',
      '    return x',
      '# fin: grande',
    ].join('\n');
    expect(extraireRegion(imbriquees, 'grande')).toBe('def f():\n    x = 1\n    return x');
    expect(extraireRegion(imbriquees, 'petite')).toBe('x = 1');
  });

  it('garde les lignes vides, et ne compte pas les vides pour l’indentation', () => {
    const avecVide = '    # region: r\n    a = 1\n\n    b = 2\n    # fin: r';
    expect(extraireRegion(avecVide, 'r')).toBe('a = 1\n\nb = 2');
  });

  it('ne confond pas deux régions dont le nom commence pareil', () => {
    const proches = '# region: compter_tout\nx\n# fin: compter_tout\n# region: compter\ny\n# fin: compter\n';
    expect(extraireRegion(proches, 'compter')).toBe('y');
  });

  it('prend le nom tel quel, sans l’interpréter comme un motif', () => {
    expect(() => extraireRegion('# region: a\nx\n# fin: a\n', '.', 'p.py')).toThrow(
      'Région introuvable : . dans p.py',
    );
  });

  it('accepte les fins de ligne Windows', () => {
    expect(extraireRegion('# region: r\r\nx = 1\r\n# fin: r\r\n', 'r')).toBe('x = 1');
  });

  it('extrait les régions du vrai fichier testé', () => {
    const source = readFileSync(BPE, 'utf8');
    const choisir = extraireRegion(source, 'choisir', 'bpe.py');
    expect(choisir.startsWith('def paire_la_plus_frequente(')).toBe(true);
    expect(choisir.endsWith('paire))')).toBe(true);
    expect(choisir).not.toMatch(/region:|fin:/);
    const compter = extraireRegion(source, 'compter', 'bpe.py');
    expect(compter.startsWith('def compter_paires(')).toBe(true);
    expect(compter).toContain('zip(symboles, symboles[1:])');
    expect(compter).not.toMatch(/region:|fin:/);
  });
});
