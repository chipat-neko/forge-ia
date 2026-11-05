// Les données du calculateur : chaque chiffre de matériel, de prix ou de
// modèle a sa source primaire, son adresse et sa date de relevé.

import { describe, expect, it } from 'vitest';
import {
  EFFICACITE_PAR_DEFAUT,
  ELECTRICITE,
  fourchettePrix,
  MATERIELS,
  materiel,
  MODELES_PUBLICS,
  modelePublic,
  PRIX_LOCATION,
  REPERES_EFFICACITE,
  SOURCES_FORMULES,
  TAUX_DE_CHANGE,
  type Source,
} from './donnees';
import { operationsEntrainement } from './formules';

/** Toutes les sources des données, avec l'endroit où elles servent. */
function toutesLesSources(): [string, Source][] {
  return [
    ...MATERIELS.flatMap((m): [string, Source][] => [
      [m.id, m.source],
      ...(m.autresSources ?? []).map((s): [string, Source] => [m.id, s]),
    ]),
    ...PRIX_LOCATION.map((p): [string, Source] => [`${p.fournisseur} ${p.materiel}`, p.source]),
    ...MODELES_PUBLICS.flatMap((m): [string, Source][] => [
      [m.id, m.source],
      ...(m.autresSources ?? []).map((s): [string, Source] => [m.id, s]),
    ]),
    ...REPERES_EFFICACITE.map((r): [string, Source] => [r.modele, r.source]),
    ...Object.entries(SOURCES_FORMULES).flatMap(([nom, sources]) => sources.map((s): [string, Source] => [nom, s])),
    ['taux de change', TAUX_DE_CHANGE.source],
    ['électricité', ELECTRICITE.source],
  ];
}

/** Tous les textes que la page peut montrer, avec l'endroit d'où ils viennent. */
function textesVisibles(): [string, string][] {
  const textes: [string, string][] = [];
  for (const m of MATERIELS) {
    textes.push([m.id, m.nom]);
    if (m.note) textes.push([m.id, m.note]);
  }
  for (const p of PRIX_LOCATION) textes.push([p.materiel, p.fournisseur], [p.materiel, p.offre]);
  for (const m of MODELES_PUBLICS) {
    textes.push([m.id, m.nom]);
    if (m.note) textes.push([m.id, m.note]);
  }
  for (const r of REPERES_EFFICACITE) textes.push([r.modele, r.modele], [r.modele, r.materiel], [r.modele, r.definition], [r.modele, r.noteCourte ?? '']);
  textes.push(['électricité', ELECTRICITE.libelle]);
  for (const [lieu, s] of toutesLesSources()) textes.push([lieu, s.titre]);
  return textes;
}

describe('les sources', () => {
  it('chaque matériel a une adresse https', () => {
    for (const m of MATERIELS) expect(m.source.url).toMatch(/^https:\/\//);
  });

  it('chaque prix vient d’une source primaire, pour un matériel de la liste', () => {
    for (const p of PRIX_LOCATION) {
      expect(p.source.statut).toBe('primaire');
      expect(MATERIELS.some((m) => m.id === p.materiel)).toBe(true);
    }
  });

  it('toutes les sources sont primaires, en https, avec un titre et une vraie date de relevé', () => {
    const sources = toutesLesSources();
    expect(sources.length).toBeGreaterThan(30);
    for (const [lieu, s] of sources) {
      expect(s.statut, lieu).toBe('primaire');
      expect(s.url, lieu).toMatch(/^https:\/\/[^\s]+$/);
      expect(s.titre.length, lieu).toBeGreaterThan(5);
      expect(s.releveLe, lieu).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      const date = new Date(`${s.releveLe}T00:00:00Z`);
      expect(date.toISOString().slice(0, 10), `${lieu} : ${s.releveLe} n'est pas une date du calendrier`).toBe(s.releveLe);
      // Les relevés de ce plan : le 3 novembre 2026 (recherche) et le 4 (formes des modèles publics).
      expect(['2026-11-03', '2026-11-04'], lieu).toContain(s.releveLe);
    }
  });

  it('les relevés de matériel et de prix datent du 3 novembre 2026, ceux des modèles publics du 4', () => {
    for (const m of MATERIELS) expect(m.source.releveLe, m.id).toBe('2026-11-03');
    for (const p of PRIX_LOCATION) expect(p.source.releveLe, `${p.fournisseur} ${p.materiel}`).toBe('2026-11-03');
    for (const m of MODELES_PUBLICS) expect(m.source.releveLe, m.id).toBe('2026-11-04');
    expect(TAUX_DE_CHANGE.source.releveLe).toBe('2026-11-03');
    expect(ELECTRICITE.source.releveLe).toBe('2026-11-03');
  });
});

describe('le matériel', () => {
  it('les identifiants du plan, dans l’ordre (le plan 5 s’en sert)', () => {
    expect(MATERIELS.map((m) => m.id)).toEqual([
      'rtx-5070-ti',
      'rtx-5080',
      'rtx-5090',
      'rtx-4090',
      't4',
      'l4',
      'a100-80',
      'h100-sxm',
      'h200',
      'b200',
    ]);
  });

  it('crête bf16 dense, mémoire, bande passante et puissance relevées', () => {
    const resume = MATERIELS.map((m) => [m.id, m.categorie, m.creteTflops, m.memoireGo, m.bandePassanteGoS, m.puissanceW]);
    expect(resume).toEqual([
      ['rtx-5070-ti', 'grand-public', 87.9, 16, 896, 300],
      ['rtx-5080', 'grand-public', 112.6, 16, 960, 360],
      ['rtx-5090', 'grand-public', 209.5, 32, 1792, 575],
      ['rtx-4090', 'grand-public', 165.2, 24, 1008, 450],
      ['t4', 'colab', 65, 16, 320, 70],
      ['l4', 'colab', 121, 24, 300, 72],
      ['a100-80', 'centre-de-donnees', 312, 80, 2039, 400],
      ['h100-sxm', 'centre-de-donnees', 989, 80, 3350, 700],
      ['h200', 'centre-de-donnees', 989, 141, 4800, 700],
      ['b200', 'centre-de-donnees', 2250, 180, 8000, null],
    ]);
  });

  it('les cartes grand public viennent du livre blanc RTX Blackwell, les autres des pages de NVIDIA', () => {
    const livreBlanc = 'https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf';
    for (const m of MATERIELS.filter((x) => x.categorie === 'grand-public')) expect(m.source.url, m.id).toBe(livreBlanc);
    for (const m of MATERIELS.filter((x) => x.categorie !== 'grand-public')) {
      expect(m.source.url, m.id).toMatch(/^https:\/\/www\.nvidia\.com\/en-us\/data-center\//);
    }
    expect(materiel('rtx-5070-ti').source.titre).toMatch(/tableau 5/);
    expect(materiel('rtx-5080').source.titre).toMatch(/tableau 4/);
    expect(materiel('rtx-5090').source.titre).toMatch(/tableau 3/);
    expect(materiel('rtx-4090').source.titre).toMatch(/tableau 3/);
  });

  it('les chiffres « avec sparsité » ou sans bf16 sont expliqués dans la note', () => {
    expect(materiel('rtx-5070-ti').note).toMatch(/FP32 Accumulate/);
    expect(materiel('rtx-5070-ti').note).toMatch(/175,8/);
    expect(materiel('t4').note).toMatch(/bf16/);
    expect(materiel('h100-sxm').note).toMatch(/1\u202F979/);
    expect(materiel('h200').note).toMatch(/1\u202F979/);
    expect(materiel('l4').note).toMatch(/242/);
    expect(materiel('b200').note).toMatch(/36 PFLOPS/);
    expect(materiel('b200').autresSources?.[0].url).toBe('https://www.nvidia.com/en-us/data-center/dgx-b200/');
  });

  it('la bande passante de la B200 : « 64 TB/s » pour les 8 cartes du DGX B200, soit 8 000 Go/s par carte, chiffre dérivé', () => {
    const b200 = materiel('b200');
    expect(b200.bandePassanteGoS).toBe(64_000 / 8);
    expect(b200.note).toMatch(/64 TB\/s/);
    expect(b200.note).toMatch(/8\u202F000 Go\/s par carte/);
    expect(b200.note).toMatch(/dérivé/);
    const dgx = b200.autresSources?.[0];
    expect(dgx?.titre).toMatch(/bande passante/);
    expect(dgx?.releveLe).toBe('2026-11-04');
  });

  it('materiel() trouve une carte, ou dit quoi faire', () => {
    expect(materiel('h100-sxm').nom).toBe('H100 SXM');
    expect(() => materiel('rtx-9090')).toThrow(/rtx-9090/);
  });
});

describe('les prix de location', () => {
  it('RunPod (Community et Secure), Lambda et Azure, par carte et par heure, hors taxes', () => {
    const resume = PRIX_LOCATION.map((p) => [p.fournisseur, p.materiel, p.usdParHeure]);
    expect(resume).toEqual([
      ['RunPod', 'rtx-4090', 0.34],
      ['RunPod', 'rtx-4090', 0.89],
      ['RunPod', 'rtx-5090', 0.69],
      ['RunPod', 'rtx-5090', 1.19],
      ['RunPod', 'a100-80', 1.39],
      ['RunPod', 'a100-80', 1.79],
      ['RunPod', 'h100-sxm', 2.69],
      ['RunPod', 'h100-sxm', 3.99],
      ['RunPod', 'h200', 3.59],
      ['RunPod', 'h200', 5.29],
      ['RunPod', 'b200', 5.98],
      ['RunPod', 'b200', 7.99],
      ['Lambda', 'b200', 6.69],
      ['Lambda', 'b200', 6.99],
      ['Lambda', 'h100-sxm', 3.99],
      ['Lambda', 'h100-sxm', 4.29],
      ['Lambda', 'a100-80', 2.79],
      ['Azure', 'h100-sxm', 12.29],
    ]);
    for (const p of PRIX_LOCATION.filter((x) => x.fournisseur === 'RunPod')) expect(p.source.url).toBe('https://www.runpod.io/pricing');
    for (const p of PRIX_LOCATION.filter((x) => x.fournisseur === 'Lambda')) expect(p.source.url).toBe('https://lambda.ai/pricing');
    for (const p of PRIX_LOCATION.filter((x) => x.fournisseur === 'Azure')) {
      expect(p.source.url).toMatch(/^https:\/\/prices\.azure\.com\/api\/retail\/prices/);
    }
  });

  it('Azure : 98,32 $ de l’heure pour les 8 cartes du ND96isr H100 v5, soit 12,29 $ par carte', () => {
    const azure = PRIX_LOCATION.find((p) => p.fournisseur === 'Azure');
    expect(azure?.usdParHeure).toBe(98.32 / 8);
    expect(azure?.offre).toMatch(/98,32/);
  });

  it('la fourchette d’une carte : du prix le plus bas au plus haut, ou rien', () => {
    const h100 = fourchettePrix('h100-sxm');
    expect(h100?.min).toBe(2.69);
    expect(h100?.max).toBe(12.29);
    expect(h100?.prix).toHaveLength(5);
    // Les prix eux-mêmes sont rangés du plus bas au plus haut (à égalité, dans l'ordre du relevé).
    expect(h100?.prix.map((p) => [p.fournisseur, p.usdParHeure])).toEqual([
      ['RunPod', 2.69],
      ['RunPod', 3.99],
      ['Lambda', 3.99],
      ['Lambda', 4.29],
      ['Azure', 98.32 / 8],
    ]);
    const b200 = fourchettePrix('b200');
    expect(b200?.prix.map((p) => p.usdParHeure)).toEqual([5.98, 6.69, 6.99, 7.99]);
    expect([b200?.min, b200?.max]).toEqual([5.98, 7.99]);
    expect(fourchettePrix('rtx-5070-ti')).toBeNull();
    expect(fourchettePrix('t4')).toBeNull();
  });
});

describe('le taux de change, l’électricité et les efficacités', () => {
  it('BCE du 3 novembre 2026 et Tarif Bleu d’EDF au 1er août 2026', () => {
    expect(TAUX_DE_CHANGE.usdPourUnEur).toBe(1.1179);
    expect(TAUX_DE_CHANGE.source.url).toBe('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml');
    expect(ELECTRICITE.eurParKwh).toBe(0.2001);
    expect(ELECTRICITE.libelle).toBe('EDF, Tarif Bleu, option Base, 6 kVA, TTC, applicable au 1er août 2026');
    expect(ELECTRICITE.source.url).toBe('https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille_prix_Tarif_Bleu.pdf');
  });

  it('les efficacités par défaut et les repères publiés', () => {
    expect(EFFICACITE_PAR_DEFAUT).toEqual({ 'grand-public': 0.5, colab: 0.4, 'centre-de-donnees': 0.4 });
    expect(REPERES_EFFICACITE.map((r) => [r.modele, r.min, r.max])).toEqual([
      ['PaLM 540B', 0.462, 0.462],
      ['Llama 3 405B', 0.38, 0.43],
    ]);
    expect(REPERES_EFFICACITE[0].source.url).toBe('https://arxiv.org/abs/2204.02311');
    expect(REPERES_EFFICACITE[1].source.url).toBe('https://arxiv.org/abs/2407.21783');
  });

  it('chaque repère dit s’il compte l’attention : PaLM oui (annexe B), Llama 3 par renvoi à la définition de PaLM', () => {
    expect(REPERES_EFFICACITE.map((r) => [r.modele, r.compteAttention])).toEqual([
      ['PaLM 540B', true],
      ['Llama 3 405B', true],
    ]);
    expect(REPERES_EFFICACITE[0].definition).toMatch(/^Annexe B/);
    expect(REPERES_EFFICACITE[0].definition).toMatch(/12·L·H·Q·T/);
    expect(REPERES_EFFICACITE[1].definition).toMatch(/^Section 3\.3\.2/);
    expect(REPERES_EFFICACITE[1].definition).toMatch(/Chowdhery/);
    // Llama 3 ne compte l'attention que par renvoi à PaLM : la phrase de comparaison le dit.
    expect(REPERES_EFFICACITE.map((r) => r.noteCourte)).toEqual([null, 'avec la définition de PaLM']);
  });

  it('chaque formule a ses sources (article et section ou équation)', () => {
    expect(Object.keys(SOURCES_FORMULES).sort()).toEqual(
      ['activations', 'attention', 'cacheKv', 'efficacite', 'etats', 'generation', 'operations'].sort(),
    );
    for (const [nom, sources] of Object.entries(SOURCES_FORMULES)) {
      expect(sources.length, nom).toBeGreaterThan(0);
      for (const s of sources) expect(s.titre, nom).toMatch(/section|équation|tableau|annexe|estimate_mfu/);
    }
  });
});

describe('les modèles publics', () => {
  it('les identifiants que le plan 5 utilise', () => {
    expect(MODELES_PUBLICS.map((m) => m.id)).toEqual(['gpt-3-175b', 'llama-3-8b', 'llama-3-70b', 'llama-3-405b']);
  });

  it('les formes vérifiées dans les articles (GPT-3, tableau 2.1 ; Llama 3, tableau 3)', () => {
    const resume = MODELES_PUBLICS.map((m) => [
      m.id,
      m.parametres,
      m.couches,
      m.dim,
      m.tetes,
      m.tetesKv,
      m.contexte,
      m.vocabulaire,
      m.jetonsOrigine,
    ]);
    expect(resume).toEqual([
      ['gpt-3-175b', 175e9, 96, 12_288, 96, 96, 2048, 50_257, 300e9],
      ['llama-3-8b', 8e9, 32, 4096, 32, 8, 8192, 128_000, 15e12],
      ['llama-3-70b', 70e9, 80, 8192, 64, 8, 8192, 128_000, 15e12],
      ['llama-3-405b', 405e9, 126, 16_384, 128, 8, 8192, 128_000, 15.6e12],
    ]);
    expect(modelePublic('gpt-3-175b').source.url).toBe('https://arxiv.org/abs/2005.14165');
    for (const id of ['llama-3-8b', 'llama-3-70b', 'llama-3-405b']) {
      expect(modelePublic(id).source.url).toBe('https://arxiv.org/abs/2407.21783');
    }
    expect(() => modelePublic('gpt-5')).toThrow(/gpt-5/);
  });

  it('des formes possibles : têtes de même taille, têtes KV qui divisent les têtes', () => {
    for (const m of MODELES_PUBLICS) {
      expect(m.dim % m.tetes, m.id).toBe(0);
      expect(m.tetes % m.tetesKv, m.id).toBe(0);
    }
  });

  it('6·N·D retrouve le calcul publié : 3,14e23 pour GPT-3 (tableau D.1), 3,8e25 pour Llama 3 405B', () => {
    const calcul = (id: string) => operationsEntrainement(modelePublic(id).parametres, modelePublic(id).jetonsOrigine);
    expect(Math.abs(calcul('gpt-3-175b') / 3.14e23 - 1)).toBeLessThan(0.01);
    expect(Math.abs(calcul('llama-3-405b') / 3.8e25 - 1)).toBeLessThan(0.01);
    // Le chiffre que Meta annonce est rangé avec le modèle (le chapitre 0.2 le lit là).
    expect(modelePublic('llama-3-405b').operationsPubliees).toBe(3.8e25);
  });

  it('les écarts avec le plan sont dits : le vocabulaire de GPT-3 vient de GPT-2, les jetons des petits Llama 3 sont « environ 15 000 milliards »', () => {
    expect(modelePublic('gpt-3-175b').note).toMatch(/GPT-2/);
    expect(modelePublic('gpt-3-175b').autresSources?.[0].url).toBe(
      'https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf',
    );
    for (const id of ['llama-3-8b', 'llama-3-70b']) {
      // « billion » est un faux ami (10¹² en français) : on écrit les milliards.
      expect(modelePublic(id).note).toMatch(/^Environ 15\u202F000 milliards de jetons/);
      expect(modelePublic(id).note).not.toMatch(/billion/);
    }
  });
});

describe('la typographie des textes montrés', () => {
  it('espaces fines, guillemets, milliers et apostrophes courbes', () => {
    for (const [lieu, t] of textesVisibles()) {
      expect(t.match(/.{0,30}[ \u00A0][;:!?%].{0,10}/g) ?? [], lieu).toEqual([]);
      expect(t.match(/.{0,10}«(?!\u202F).{0,30}|.{0,30}(?<!\u202F)».{0,10}/g) ?? [], lieu).toEqual([]);
      expect(t.match(/.{0,20}\d[ \u00A0]\d{3}\b.{0,20}/g) ?? [], lieu).toEqual([]);
      expect(t.match(/.{0,20}\p{L}'\p{L}.{0,20}/gu) ?? [], lieu).toEqual([]);
    }
  });
});
