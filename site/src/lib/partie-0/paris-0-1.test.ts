// Les paris du chapitre 0.1 : leurs bonnes réponses sont calculées par le
// jumeau du mot suivant (mot-suivant.ts), jamais écrites à la main.
//
// Les derniers tests prouvent, par le calcul sur le texte de l'atelier, ce que
// la page enseigne : la suite du pari tourne en rond, le défi n'est pas réussi
// au départ, un autre mot de départ le réussit, et « le » ne le peut pas.

import { describe, expect, it } from 'vitest';
import { compterSuivants, decouperMots, generer, predire, premiereReprise, suivantsTries } from './mot-suivant';
import {
  boucleDuPari,
  choixBoucle,
  choixFlottants,
  choixMotSuivant,
  choixSelonLaSuite,
  choixTranche,
  DEFI_REUSSI,
  defiReussi,
  faitsDuPariSuivant,
  LISTE_DU_PARI,
  LONGUEUR_DU_PARI,
  LONGUEUR_INITIALE,
  LONGUEUR_MAX,
  MOT_D_OUVERTURE,
  MOT_DU_PARI,
  motDuPari,
  ouvertureDuChapitre,
  reprListePython,
  SEUIL_DU_DEFI,
  SOMME_DES_FLOTTANTS,
  suiteDeDepart,
} from './paris-0-1';
import { TEXTE_DE_DEPART } from './texte-0-1';

const FINE = '\u202F';

describe('les bonnes réponses viennent du calcul', () => {
  it('flottants : 0.1 + 0.2 == 0.3 répond False, comme en Python', () => {
    expect(choixFlottants().find((c) => c.juste)?.texte).toBe('`False`');
    expect(choixFlottants().map((c) => c.texte)).toEqual(['`True`', '`False`', 'Une erreur']);
    // Python affiche la même somme que JavaScript : le plus court texte qui redonne ce flottant.
    expect(SOMME_DES_FLOTTANTS).toBe('0.30000000000000004');
  });

  it('tranche : mots[1:] sur la liste du pari', () => {
    expect(choixTranche().find((c) => c.juste)?.texte).toBe("`['forgeron', 'frappe']`");
    expect(choixTranche().map((c) => c.texte)).toEqual([
      "`['le', 'forgeron']`",
      "`['forgeron', 'frappe']`",
      "`['forgeron']`",
    ]);
    expect(reprListePython(LISTE_DU_PARI)).toBe("['le', 'forgeron', 'frappe']");
  });

  it('mot suivant : le mot que prédit le jumeau, sur le texte de l’atelier', () => {
    const s = compterSuivants(decouperMots(TEXTE_DE_DEPART));
    expect(choixMotSuivant(TEXTE_DE_DEPART).find((c) => c.juste)?.texte).toBe(`« ${predire(s, MOT_DU_PARI)} »`);
    // Le deuxième suivant, et le mot le plus fréquent du texte qui ne suit jamais « le ».
    const tries = suivantsTries(s.get(MOT_DU_PARI)!);
    const textes = choixMotSuivant(TEXTE_DE_DEPART).map((c) => c.texte);
    expect(textes).toContain(`« ${tries[1][0]} »`);
    const { troisieme } = faitsDuPariSuivant(TEXTE_DE_DEPART);
    expect(textes).toContain(`« ${troisieme.mot} »`);
    expect(s.get(MOT_DU_PARI)!.has(troisieme.mot)).toBe(false);
    expect(troisieme.mot).toMatch(/\p{L}/u);
    // Les choix sont rangés par point de code : la bonne réponse n'est pas toujours à la même place.
    expect([...textes].sort()).toEqual(textes);
  });

  it('boucle : la suite du pari tourne en rond, par le calcul', () => {
    expect(choixBoucle(TEXTE_DE_DEPART).find((c) => c.juste)?.texte).toBe('Une boucle : les mêmes mots reviennent');
    expect(choixBoucle(TEXTE_DE_DEPART)[2].texte).toBe(`Elle s'arrête avant ${LONGUEUR_DU_PARI} mots`);
  });

  it('chaque pari a exactement un choix juste', () => {
    for (const f of [choixFlottants, choixTranche, () => choixMotSuivant(TEXTE_DE_DEPART), () => choixBoucle(TEXTE_DE_DEPART)]) {
      expect(f().filter((c) => c.juste)).toHaveLength(1);
    }
  });
});

describe('les règles des paris', () => {
  it('reprListePython écrit une liste comme Python', () => {
    expect(reprListePython([])).toBe('[]');
    expect(reprListePython(['un'])).toBe("['un']");
    // Une apostrophe dans le mot : Python passe aux guillemets doubles.
    expect(reprListePython(["l'eau", 'fer'])).toBe(`["l'eau", 'fer']`);
    expect(reprListePython(['a\\b'])).toBe("['a\\\\b']");
  });

  it('le mot du pari est « le » sur le texte de l’atelier', () => {
    expect(motDuPari(TEXTE_DE_DEPART)).toBe(MOT_DU_PARI);
  });

  it('si « le » ne passe plus les gardes, le premier mot du texte qui les passe prend sa place', () => {
    // « le » n'a qu'un suivant ; « la » en a deux, dont « forge » seul en tête, et « mine » ne la suit jamais.
    const texte = 'Le feu. La forge. La forge. La mine. Mine mine mine.';
    expect(motDuPari(texte)).toBe('la');
    expect(choixMotSuivant(texte).find((c) => c.juste)?.texte).toBe('« forge »');
    expect(choixMotSuivant(texte).map((c) => c.texte)).toContain('« mine »');
  });

  it('sans aucun mot qui passe les gardes, l’exemple est devenu faux', () => {
    expect(() => motDuPari('un deux trois')).toThrow(/Exemple devenu faux/);
  });

  it('choixSelonLaSuite : un seul choix juste, quelle que soit la suite', () => {
    const juste = (suite: string[]) => choixSelonLaSuite(suite, 5).find((c) => c.juste)?.texte;
    expect(juste(['a', 'b', 'a', 'b', 'a'])).toBe('Une boucle : les mêmes mots reviennent');
    expect(juste(['a', 'b', 'c', 'd', 'e'])).toBe('Une suite de mots qui ne se répète jamais');
    expect(juste(['a', 'b', 'c'])).toBe("Elle s'arrête avant 5 mots");
  });

  it('la boucle du pari : où elle reprend, et les mots qui tournent en rond', () => {
    const { mot, suite, reprise, cycle } = boucleDuPari(TEXTE_DE_DEPART);
    expect(mot).toBe(MOT_DU_PARI);
    expect(suite).toEqual(generer(compterSuivants(decouperMots(TEXTE_DE_DEPART)), MOT_DU_PARI, LONGUEUR_DU_PARI));
    expect(reprise).toBe(premiereReprise(suite));
    expect(cycle[0]).toBe(suite[reprise]);
    expect(suite.slice(reprise, reprise + cycle.length)).toEqual(cycle);
  });

  it('l’ouverture ne donne pas la réponse du pari de l’étape 5', () => {
    const o = ouvertureDuChapitre(TEXTE_DE_DEPART);
    expect(o.mot).toBe(MOT_D_OUVERTURE);
    expect(o.mot).not.toBe(MOT_DU_PARI);
    const s = compterSuivants(decouperMots(TEXTE_DE_DEPART));
    expect(o.suivant).toBe(predire(s, MOT_D_OUVERTURE));
    expect(o.fois).toBe(s.get(MOT_D_OUVERTURE)!.get(o.suivant));
    expect(o.fois).toBeLessThan(o.total);
    expect(TEXTE_DE_DEPART.startsWith(o.phrase)).toBe(true);
    expect(o.mots).toEqual(decouperMots(o.phrase));
    expect(o.mots.at(-1)).toBe('.');
  });
});

describe('ce que la page enseigne, prouvé sur le texte de l’atelier', () => {
  const suivants = compterSuivants(decouperMots(TEXTE_DE_DEPART));
  const departs = [...new Set(decouperMots(TEXTE_DE_DEPART))];

  it('la suite du pari, depuis « le », revient sur un mot', () => {
    expect(premiereReprise(generer(suivants, MOT_DU_PARI, LONGUEUR_DU_PARI))).not.toBeNull();
  });

  it('à l’arrivée (« le », 12 mots), l’atelier ne montre pas encore la boucle du pari', () => {
    expect(LONGUEUR_INITIALE).toBeLessThan(LONGUEUR_DU_PARI);
    expect(premiereReprise(generer(suivants, MOT_DU_PARI, LONGUEUR_INITIALE))).toBeNull();
    expect(suiteDeDepart(TEXTE_DE_DEPART)).toEqual({
      mot: MOT_DU_PARI,
      longueur: LONGUEUR_INITIALE,
      suite: generer(suivants, MOT_DU_PARI, LONGUEUR_INITIALE),
    });
  });

  it('le défi n’est pas réussi dans l’état de départ de l’atelier', () => {
    expect(defiReussi(generer(suivants, MOT_DU_PARI, LONGUEUR_INITIALE))).toBe(false);
  });

  it('au moins un mot de départ du texte atteint 15 mots sans reprise, la longueur réglée à 15 ou plus', () => {
    const reussis = departs.filter((mot) => {
      for (let longueur = SEUIL_DU_DEFI; longueur <= LONGUEUR_MAX; longueur++) {
        if (defiReussi(generer(suivants, mot, longueur))) return true;
      }
      return false;
    });
    expect(reussis.length).toBeGreaterThan(0);
    expect(reussis).not.toContain(MOT_DU_PARI);
  });

  it('« le » ne peut pas réussir le défi, quelle que soit la longueur', () => {
    for (let longueur = 1; longueur <= LONGUEUR_MAX; longueur++) {
      expect(defiReussi(generer(suivants, MOT_DU_PARI, longueur)), `longueur ${longueur}`).toBe(false);
    }
  });

  it('le défi : au moins SEUIL_DU_DEFI mots, sans reprise', () => {
    const quinze = 'un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze'.split(' ');
    expect(quinze).toHaveLength(SEUIL_DU_DEFI);
    expect(defiReussi(quinze)).toBe(true);
    expect(defiReussi(quinze.slice(1))).toBe(false);
    expect(defiReussi([...quinze, 'un'])).toBe(false);
    expect(DEFI_REUSSI).toBe(`Défi réussi${FINE}: ${SEUIL_DU_DEFI} mots ou plus, sans boucle.`);
    expect(SEUIL_DU_DEFI).toBeLessThanOrEqual(LONGUEUR_MAX);
  });
});
