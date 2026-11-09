// Les paris du chapitre 1.1, son ouverture et son atelier : leurs bonnes
// réponses viennent du jumeau du Python (ngrammes.ts), appliqué au texte du site.

import { describe, expect, it } from 'vitest';
import { visible as visibleDe13 } from '../bpe';
import {
  alphabet,
  compter,
  compterParOrdre,
  couper,
  distribution,
  generer,
  partJamaisVue,
  tirage,
  tourneEnRond,
} from './ngrammes';
import {
  choixContexte,
  choixPerplexite,
  choixSuivant,
  choixTemperature,
  CONTEXTE_DU_PARI,
  CONTEXTE_INITIAL,
  etatDeLAtelier,
  etatDuDefi,
  faitsDuPariContexte,
  faitsDuPariSuivant,
  GRAINE_INITIALE,
  LONGUEUR_SUITE,
  messageBoucle,
  messageCourt,
  messageRecul,
  minimumDesPerplexites,
  N_DU_PARI,
  N_DU_PARI_CONTEXTE,
  N_INITIAL,
  N_OUVERTURE,
  nomDuBlanc,
  NS_DU_PARI_PERPLEXITE,
  ouvertureDuChapitre,
  suiteDuPariTemperature,
  trancheDeLaPart,
  visible,
} from './paris-1-1';
import { PERPLEXITES } from './perplexites-1-1';
import { ALPHABET, TEXTE_DU_SITE } from './texte-1-1';

const FINE = '\u202F';

describe('le pari « suivant »', () => {
  it('la bonne réponse est « environ une fois sur N », N calculé sur la distribution du jumeau', () => {
    const c = compter(couper(TEXTE_DU_SITE)[0], N_DU_PARI);
    const n = Math.round(1 / distribution(c, ALPHABET, CONTEXTE_DU_PARI, N_DU_PARI)[0][1]);
    expect(choixSuivant(TEXTE_DU_SITE).find((x) => x.juste)?.texte).toBe(`Environ une fois sur ${n}`);
    expect(choixSuivant(TEXTE_DU_SITE).map((x) => x.texte)).toStrictEqual([
      `À chaque fois${FINE}: 100${FINE}%`,
      'Environ une fois sur deux',
      `Environ une fois sur ${n}`,
    ]);
  });

  it('« ton I » passe les gardes : un seul suivant vu, « A », et N ≥ 3', () => {
    const f = faitsDuPariSuivant(TEXTE_DU_SITE);
    expect(f.contexte).toBe(CONTEXTE_DU_PARI);
    expect(f.caractere).toBe('A');
    expect(f.fois).toBeGreaterThan(0);
    // Le lissage : (compte + 1) ÷ (total + V), et 1 ÷ (total + V) pour chacun des autres.
    expect(f.p).toBe((f.fois + 1) / (f.fois + f.v));
    expect(f.pAutre).toBe(1 / (f.fois + f.v));
    expect(f.uneSur).toBe(Math.round(1 / f.p));
    expect(f.uneSur).toBeGreaterThanOrEqual(3);
  });

  it('une garde qui tombe arrête la construction', () => {
    // « ton I » suivi de deux caractères différents.
    expect(() => faitsDuPariSuivant('ton IA, ton IB. '.repeat(20))).toThrow(/Exemple devenu faux/);
    // « ton I » toujours suivi de « A », sur un alphabet si petit que A gagne plus d'une fois sur trois.
    expect(() => faitsDuPariSuivant('ton IA '.repeat(40))).toThrow(/Exemple devenu faux/);
    // Pas de « ton I » du tout.
    expect(() => faitsDuPariSuivant('abcdefghij'.repeat(10))).toThrow(/Exemple devenu faux/);
  });

  it('visible écrit les blancs comme le chapitre 1.3, et nomDuBlanc les nomme', () => {
    for (const s of ['a b', '\n', ' \n ', 'ton IA']) expect(visible(s)).toBe(visibleDe13(s));
    expect(nomDuBlanc(' ')).toBe('espace');
    expect(nomDuBlanc('\n')).toBe('retour à la ligne');
    expect(nomDuBlanc('\u202F')).toBe('espace fine');
    expect(nomDuBlanc('A')).toBeNull();
  });
});

describe('le pari « temperature »', () => {
  it('juste si la suite à température 0 tourne en rond', () => {
    const [entrainement] = couper(TEXTE_DU_SITE);
    const suite = generer(compterParOrdre(entrainement, N_INITIAL), ALPHABET, N_INITIAL, CONTEXTE_INITIAL, LONGUEUR_SUITE, 0, GRAINE_INITIALE);
    expect(suiteDuPariTemperature(TEXTE_DU_SITE)).toBe(suite);
    const juste = choixTemperature(TEXTE_DU_SITE).find((x) => x.juste)!.texte;
    expect(juste).toBe(tourneEnRond(suite) ? `Il tourne en rond${FINE}: les mêmes morceaux reviennent` : 'Il invente sans fin des mots nouveaux');
    expect(tourneEnRond(suite)).toBe(true);
  });
});

describe('le pari « contexte »', () => {
  it('la tranche juste est celle de la part des contextes jamais vus, à n = 6', () => {
    const [entrainement, validation] = couper(TEXTE_DU_SITE);
    const [absents, total] = partJamaisVue(compter(entrainement, N_DU_PARI_CONTEXTE), validation, N_DU_PARI_CONTEXTE);
    const f = faitsDuPariContexte(TEXTE_DU_SITE);
    expect([f.absents, f.total]).toStrictEqual([absents, total]);
    const choix = choixContexte(TEXTE_DU_SITE);
    expect(choix.findIndex((x) => x.juste)).toBe(trancheDeLaPart(absents / total));
  });

  it('les bornes des tranches : un sur dix et la moitié comptent dans la tranche du milieu', () => {
    expect(trancheDeLaPart(0)).toBe(0);
    expect(trancheDeLaPart(0.0999)).toBe(0);
    expect(trancheDeLaPart(0.1)).toBe(1);
    expect(trancheDeLaPart(0.5)).toBe(1);
    expect(trancheDeLaPart(0.5001)).toBe(2);
    expect(trancheDeLaPart(1)).toBe(2);
  });
});

describe('le pari « perplexite »', () => {
  it('la bonne réponse est le n de la plus petite perplexité de validation, parmi 1, 3 et 6', () => {
    const parmi = PERPLEXITES.filter((p) => NS_DU_PARI_PERPLEXITE.includes(p.n));
    const meilleur = parmi.reduce((a, b) => (b.validation < a.validation ? b : a));
    const juste = choixPerplexite(PERPLEXITES).find((x) => x.juste)!;
    expect(juste.texte).toBe(`${meilleur.n} ${meilleur.n > 1 ? 'caractères' : 'caractère'}`);
  });

  it('un minimum partagé arrête la construction', () => {
    const egalite = PERPLEXITES.map((p) => ({ ...p, validation: 10 }));
    expect(() => choixPerplexite(egalite)).toThrow(/Exemple devenu faux/);
  });

  it('le minimum de toute la courbe de validation, unique', () => {
    const { n, valeur } = minimumDesPerplexites(PERPLEXITES);
    for (const p of PERPLEXITES) if (p.n !== n) expect(p.validation).toBeGreaterThan(valeur);
  });
});

describe('chaque pari a exactement un choix juste', () => {
  it('suivant, temperature, contexte, perplexite', () => {
    for (const f of [
      () => choixSuivant(TEXTE_DU_SITE),
      () => choixTemperature(TEXTE_DU_SITE),
      () => choixContexte(TEXTE_DU_SITE),
      () => choixPerplexite(PERPLEXITES),
    ]) {
      expect(f().filter((x) => x.juste)).toHaveLength(1);
    }
  });
});

describe('l’ouverture', () => {
  it('les cinq caractères les plus probables après « Le forgeron frappe », tous déjà vus', () => {
    const o = ouvertureDuChapitre(TEXTE_DU_SITE);
    const [entrainement] = couper(TEXTE_DU_SITE);
    const d = distribution(compter(entrainement, N_OUVERTURE), ALPHABET, CONTEXTE_INITIAL, N_OUVERTURE);
    expect(o.suites).toStrictEqual(d.slice(0, 5));
    expect(o.autres).toBe(ALPHABET.length - 5);
    let somme = 0;
    for (const [, p] of d.slice(5)) somme += p;
    expect(o.reste).toBeCloseTo(somme, 12);
  });
});

describe('l’atelier', () => {
  const [entrainement] = couper(TEXTE_DU_SITE);
  const comptes = compterParOrdre(entrainement, 6);
  const lettres = alphabet(TEXTE_DU_SITE);

  it('à l’arrivée : le tirage et la suite du jumeau, sans message', () => {
    const e = etatDeLAtelier(comptes, lettres, CONTEXTE_INITIAL, N_INITIAL, 1, GRAINE_INITIALE);
    const [ordre, chances] = tirage(comptes, lettres, CONTEXTE_INITIAL, N_INITIAL, 1);
    expect(e.court).toBe(false);
    expect(e.ordre).toBe(ordre);
    expect(e.chances).toStrictEqual(chances);
    expect(e.suite).toBe(generer(comptes, lettres, N_INITIAL, CONTEXTE_INITIAL, LONGUEUR_SUITE, 1, GRAINE_INITIALE));
    expect(e.messages).toStrictEqual([]);
  });

  it('les messages exacts : contexte trop court, contexte jamais vu, boucle à température 0', () => {
    expect(messageCourt(4)).toBe(`Il faut au moins 4 caractères de contexte${FINE}: écris-en un peu plus.`);
    expect(messageCourt(1)).toBe(`Il faut au moins 1 caractère de contexte${FINE}: écris-en un peu plus.`);
    expect(messageRecul(2)).toBe(
      `Ce contexte n’apparaît jamais dans le texte${FINE}: le modèle raccourcit son contexte à 2 caractères, le plus long qu’il connaît.`,
    );
    expect(messageRecul(0)).toContain('à 0 caractère, le plus long');
    expect(messageBoucle()).toBe(`La suite revient sur ses pas${FINE}: à température 0, elle tourne en rond.`);
    expect(etatDeLAtelier(comptes, lettres, 'abc', 4, 1, 0).messages).toStrictEqual([messageCourt(4)]);
    expect(etatDeLAtelier(comptes, lettres, '', 0, 1, 0).messages).toStrictEqual([]);
    const emoji = etatDeLAtelier(comptes, lettres, 'Le 😀', 4, 1, 0);
    expect(emoji.ordre).toBe(0);
    expect(emoji.messages).toStrictEqual([messageRecul(0)]);
    expect(etatDeLAtelier(comptes, lettres, CONTEXTE_INITIAL, N_INITIAL, 0, 0).messages).toStrictEqual([messageBoucle()]);
  });

  it('le défi : 4 caractères connus, dont le suivant le plus probable est une espace', () => {
    const reussi = etatDeLAtelier(comptes, lettres, 'les questions', 4, 1, 0);
    expect(reussi.defi).toBe(true);
    expect(etatDuDefi(reussi, 4)).toBe(`Défi réussi${FINE}: après «${FINE}ions${FINE}», le caractère le plus probable est une espace.`);
    expect(etatDuDefi(reussi, 3)).toBe(`Pas encore${FINE}: règle le nombre jaune sur 4.`);
    expect(etatDuDefi(etatDeLAtelier(comptes, lettres, 'abc', 4, 1, 0), 4)).toBe(`Pas encore${FINE}: écris au moins 4 caractères.`);
    expect(etatDuDefi(etatDeLAtelier(comptes, lettres, 'zzzz', 4, 1, 0), 4)).toBe(
      `Pas encore${FINE}: ces 4 derniers caractères n’apparaissent jamais dans le texte.`,
    );
    expect(etatDuDefi(etatDeLAtelier(comptes, lettres, CONTEXTE_INITIAL, 4, 1, 0), 4)).toBe(
      `Pas encore${FINE}: après «${FINE}appe${FINE}», le plus probable est «${FINE}l${FINE}».`,
    );
    expect(etatDeLAtelier(comptes, lettres, 'les questions', 4, 1, 0).defi).toBe(true);
    expect(etatDeLAtelier(comptes, lettres, 'les questions', 3, 1, 0).defi).toBe(false);
    expect(etatDeLAtelier(comptes, lettres, CONTEXTE_INITIAL, 4, 1, 0).defi).toBe(false);
    expect(etatDeLAtelier(comptes, lettres, 'zzzz', 4, 1, 0).defi).toBe(false);
  });
});
