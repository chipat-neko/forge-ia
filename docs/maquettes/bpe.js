// Moteur BPE partagé par toutes les maquettes de La Forge IA.
// Expose window.ForgeBPE : apprentissage des fusions sur un petit corpus français,
// puis découpage d'un texte avec les k premières fusions apprises.
(function () {
  const CORPUS = `Avant de lire une phrase, une intelligence artificielle la découpe en morceaux.
Ces morceaux sont appelés des jetons. Chaque jeton est ensuite remplacé par un nombre,
parce qu'un réseau de neurones ne sait manipuler que des nombres.
Le forgeron chauffe le métal, puis il le frappe sur l'enclume. Les forgerons forgent des outils,
des lames et des fers. Le métal forgé refroidit dans l'eau. On reforge les pièces abîmées.
Les données sont la matière première de l'apprentissage. On les collecte, on les nettoie,
on les trie, puis on les découpe en jetons. Plus les données sont propres, plus le modèle apprend vite.
Un modèle de langage prédit le jeton suivant. Il regarde les jetons précédents et calcule
la probabilité de chaque jeton possible. Puis il choisit, écrit, et recommence.
Les mots qui reviennent souvent deviennent des jetons entiers. Les mots rares restent découpés
en plusieurs morceaux. Ainsi, le vocabulaire reste petit, et aucun mot n'est impossible à écrire.
Les enfants apprennent à lire en reconnaissant des syllabes, puis des mots entiers.
Le tokenizer fait un peu la même chose : il part des lettres et apprend les assemblages fréquents.
Nous allons construire ce découpeur nous-mêmes, ligne par ligne, et le tester sur nos propres phrases.`;

  // Découpe en pré-jetons : un mot garde l'espace qui le précède, comme dans GPT.
  const PRE = /\s?[\p{L}\p{M}]+|\s?\p{N}+|\s?[^\s\p{L}\p{N}]+|\s+/gu;

  function preDecouper(texte) {
    return texte.match(PRE) || [];
  }

  function apprendre(corpus, nbFusions) {
    const freq = new Map();
    for (const m of preDecouper(corpus)) freq.set(m, (freq.get(m) || 0) + 1);
    let mots = [...freq.entries()].map(([m, f]) => ({ symboles: [...m], f }));
    const fusions = [];
    for (let i = 0; i < nbFusions; i++) {
      const compte = new Map();
      for (const { symboles, f } of mots) {
        for (let j = 0; j < symboles.length - 1; j++) {
          const cle = symboles[j] + '\u0000' + symboles[j + 1];
          compte.set(cle, (compte.get(cle) || 0) + f);
        }
      }
      let meilleure = null, max = 1;
      for (const [cle, n] of compte) {
        if (n > max || (n === max && meilleure !== null && cle < meilleure)) { meilleure = cle; max = n; }
      }
      if (meilleure === null) break;
      const [a, b] = meilleure.split('\u0000');
      fusions.push({ a, b, ab: a + b, n: max });
      mots = mots.map(({ symboles, f }) => ({ symboles: fusionner(symboles, a, b), f }));
    }
    return fusions;
  }

  function fusionner(symboles, a, b) {
    const out = [];
    for (let j = 0; j < symboles.length; j++) {
      if (j < symboles.length - 1 && symboles[j] === a && symboles[j + 1] === b) {
        out.push(a + b); j++;
      } else out.push(symboles[j]);
    }
    return out;
  }

  const FUSIONS = apprendre(CORPUS, 200);
  const LETTRES = [...new Set([...CORPUS])].sort();

  // Identifiant d'un jeton : les lettres d'abord, puis une case par fusion apprise.
  function identifiant(morceau, k) {
    const i = LETTRES.indexOf(morceau);
    if (i >= 0) return i;
    for (let j = 0; j < k; j++) if (FUSIONS[j].ab === morceau) return LETTRES.length + j;
    return LETTRES.length + FUSIONS.length + (morceau.codePointAt(0) % 97);
  }

  // Découpe un texte avec les k premières fusions. Renvoie [{ texte, id, mot }].
  function decouper(texte, k) {
    k = Math.max(0, Math.min(k, FUSIONS.length));
    const jetons = [];
    preDecouper(texte).forEach((mot, iMot) => {
      let symboles = [...mot];
      for (let j = 0; j < k; j++) symboles = fusionner(symboles, FUSIONS[j].a, FUSIONS[j].b);
      for (const s of symboles) jetons.push({ texte: s, id: identifiant(s, k), mot: iMot });
    });
    return jetons;
  }

  // Affichage lisible d'un jeton : l'espace devient ␣, le retour à la ligne ↵.
  function visible(s) {
    return s.replace(/ /g, '␣').replace(/\n/g, '↵');
  }

  window.ForgeBPE = {
    corpus: CORPUS,
    fusions: FUSIONS,
    maxFusions: FUSIONS.length,
    tailleBase: LETTRES.length,
    decouper,
    visible,
    preDecouper,
  };
})();
