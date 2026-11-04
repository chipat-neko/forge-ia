// Les paris de l'animation de l'attention.
//
// Leurs bonnes réponses sont calculées par le moteur (detaillerExemple), sur
// l'exemple écrit à la main : rien n'est recopié. Ce que les paris et leurs
// explications affirment (« il » regarde surtout « forgeron », « forgeron » ne
// voit pas « il ») est vérifié aussi : si l'exemple change et qu'une phrase
// devient fausse, la construction s'arrête (« Exemple devenu faux : … »).
//
// Les têtes et les mots sont numérotés à partir de 0, comme dans l'exemple :
//  - la tête 0 est « qui agit », que la page appelle « Tête 1 : qui agit » ;
//  - la tête 1 est « de qui on parle », la « Tête 2 : de qui on parle » de la page ;
//  - les mots : 0 « Le », 1 « forgeron », 2 « chauffe », 3 « le », 4 « fer »,
//    5 « puis », 6 « il », 7 « le », 8 « tord ».

import type { Choix } from '../choix';
import { detaillerExemple, exempleAttention, type DetailTete, type ExempleAttention } from './exemple-attention';

/** La tête « qui agit » (la « Tête 1 » de la page). */
export const TETE_QUI_AGIT = 0;
/** La tête « de qui on parle » (la « Tête 2 » de la page). */
export const TETE_DE_QUI_ON_PARLE = 1;
/** « forgeron », le sujet de la phrase. */
export const MOT_FORGERON = 1;
/** « puis », le mot juste avant « il ». */
export const MOT_PUIS = 5;
/** « il », le pronom qui pose la question du pari. */
export const MOT_IL = 6;

function exiger(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(
      `Exemple devenu faux : ${message}. Revoir projets/mini-modele/donnees/exemple-attention.json ` +
        'et src/lib/mini-modele/paris-attention.ts.',
    );
  }
}

// Le détail de chaque exemple, calculé une fois et rangé sous l'objet exemple
// lui-même. Ne modifie donc jamais un exemple après l'avoir passé à l'une de
// ces fonctions : elles rendraient le détail de son ancien contenu. Pour en
// essayer une variante, fais-en une copie (structuredClone), comme les tests.
// L'exemple par défaut est figé, il ne peut pas changer.
const detailsCalcules = new WeakMap<ExempleAttention, DetailTete[]>();

function details(exemple: ExempleAttention): DetailTete[] {
  let d = detailsCalcules.get(exemple);
  if (d === undefined) {
    d = detaillerExemple(exemple);
    detailsCalcules.set(exemple, d);
  }
  return d;
}

/**
 * Les deux têtes dont parlent les paris et leurs explications sont toujours là,
 * à leur place : avant d'indexer TETE_DE_QUI_ON_PARLE, pour qu'un exemple
 * changé dise « Exemple devenu faux » plutôt qu'une TypeError.
 */
function verifierTetes(exemple: ExempleAttention): void {
  const noms = exemple.tetes.map((t) => t.nom);
  exiger(noms.length === 2, `il faut 2 têtes, « qui agit » et « de qui on parle » (il y en a ${noms.length})`);
  for (const [indice, nom] of [
    [TETE_QUI_AGIT, 'qui agit'],
    [TETE_DE_QUI_ON_PARLE, 'de qui on parle'],
  ] as const) {
    exiger(noms[indice] === nom, `la tête ${indice} n'est plus « ${nom} » (c'est « ${noms[indice]} »)`);
  }
}

/** Les mots dont parlent les paris sont toujours à leur place dans la phrase. */
function verifierMots(exemple: ExempleAttention): void {
  for (const [indice, mot] of [
    [MOT_FORGERON, 'forgeron'],
    [MOT_PUIS, 'puis'],
    [MOT_IL, 'il'],
  ] as const) {
    exiger(exemple.jetons[indice] === mot, `le mot ${indice} n'est plus « ${mot} » (c'est « ${exemple.jetons[indice]} »)`);
  }
}

/**
 * Le mot que la requête regarde le plus dans la tête donnée : le mot visible
 * (de 0 à requete) de plus grand poids, le premier à égalité. Têtes et mots
 * comptés à partir de 0 (la tête 1 est « de qui on parle »).
 */
export function motLePlusRegarde(tete: number, requete: number, exemple: ExempleAttention = exempleAttention): number {
  const d = details(exemple);
  if (!Number.isInteger(tete) || tete < 0 || tete >= d.length) {
    throw new RangeError(`motLePlusRegarde : la tête va de 0 à ${d.length - 1} (reçu ${tete}).`);
  }
  const n = exemple.jetons.length;
  if (!Number.isInteger(requete) || requete < 0 || requete >= n) {
    throw new RangeError(`motLePlusRegarde : le mot qui pose la question va de 0 à ${n - 1} (reçu ${requete}).`);
  }
  const poids = d[tete].poids[requete];
  let meilleur = 0;
  for (let j = 1; j <= requete; j++) {
    if (poids[j] > poids[meilleur]) meilleur = j;
  }
  return meilleur;
}

/**
 * Le pari « Dans la tête « de qui on parle », vers quel mot « il » regarde-t-il le plus ? ».
 *
 * La bonne réponse est le mot de plus grand poids (« forgeron », sinon
 * l'exemple est devenu faux). Les leurres : « puis », le mot juste avant
 * « il », et le mot visible de deuxième plus grand poids (du troisième si le
 * deuxième est « puis »). Les choix sont dans l'ordre de la phrase.
 */
export function choixRegardDeIl(exemple: ExempleAttention = exempleAttention): Choix[] {
  verifierTetes(exemple);
  verifierMots(exemple);
  const poids = details(exemple)[TETE_DE_QUI_ON_PARLE].poids[MOT_IL];
  const juste = motLePlusRegarde(TETE_DE_QUI_ON_PARLE, MOT_IL, exemple);
  exiger(
    juste === MOT_FORGERON,
    `dans la tête « de qui on parle », « il » regarde surtout « ${exemple.jetons[juste]} », et non plus « forgeron »`,
  );
  for (let j = 0; j <= MOT_IL; j++) {
    exiger(
      j === juste || poids[j] < poids[juste],
      `« ${exemple.jetons[j]} » reçoit autant d'attention de « il » que « forgeron » : le pari n'a plus une seule réponse`,
    );
  }
  // Le leurre calculé : le mot visible de plus grand poids après « forgeron », hors « puis » (déjà un leurre).
  let leurre = -1;
  for (let j = 0; j <= MOT_IL; j++) {
    if (j === juste || j === MOT_PUIS) continue;
    if (leurre < 0 || poids[j] > poids[leurre]) leurre = j;
  }
  const indices = [juste, MOT_PUIS, leurre].sort((a, b) => a - b);
  const choix = indices.map((j) => ({ texte: exemple.jetons[j], juste: j === juste }));
  exiger(new Set(choix.map((c) => c.texte)).size === 3, 'deux choix du pari sur « il » ont le même texte');
  return choix;
}

/**
 * Le pari « Combien vaut le poids de « forgeron » vers « il » ? ».
 *
 * « 0 » est juste : « forgeron » (mot 1) ne voit pas « il » (mot 6), qui vient
 * après lui. Si ce poids ne vaut pas exactement 0 dans une tête, l'exemple
 * est devenu faux.
 */
export function choixMasque(exemple: ExempleAttention = exempleAttention): Choix[] {
  verifierTetes(exemple);
  verifierMots(exemple);
  details(exemple).forEach((d, t) => {
    const p = d.poids[MOT_FORGERON][MOT_IL];
    exiger(p === 0, `dans la tête « ${exemple.tetes[t].nom} », le poids de « forgeron » vers « il » vaut ${p}, et pas 0`);
  });
  return [
    { texte: '0', juste: true },
    { texte: 'environ la moitié', juste: false },
    { texte: 'presque tout', juste: false },
  ];
}
