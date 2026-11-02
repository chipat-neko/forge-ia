// Le script de l'accueil, hors pari (voir components/accueil/PariAccueil.astro) :
// 1. passe les chapitres faits à l'état « fait » et montre les acquis des
//    chapitres commencés, sur le plan ;
// 2. tient à jour le relevé des chapitres faits ;
// 3. change le bouton de lecture : ouvrir, reprendre ou revoir ;
// 4. sur grand écran, place les embranchements à la hauteur de leur départ.
//
// Sans JavaScript, le plan reste lisible tel quel : chapitres parus
// disponibles, embranchements à la suite de la ligne principale.
import { typographier } from '../lib/typo';
import { avancementDe, pastilles } from './etats';
import type { Avancement } from '../lib/avancement';

interface Paru {
  element: HTMLElement;
  numero: string;
  court: string;
  href: string;
  avancement: Avancement;
}

const carte = document.querySelector<HTMLElement>('[data-carte]');
const stations = [...document.querySelectorAll<HTMLElement>('[data-chapitre-carte]')];

// ---------- 1. États des chapitres parus ----------

const parus: Paru[] = [];
for (const element of stations) {
  const avancement = avancementDe(element);
  if (!avancement) continue;
  parus.push({
    element,
    numero: element.dataset.chapitreCarte ?? '',
    court: element.dataset.titreCourt ?? '',
    href: element.querySelector('a')?.getAttribute('href') ?? '',
    avancement,
  });
  const { gagnes, total, etat } = avancement;
  const infos = element.querySelector<HTMLElement>('[data-infos]');
  if (etat === 'fait') {
    element.dataset.etat = 'fait';
    if (infos) {
      const fait = document.createElement('span');
      fait.className = 'fait-txt';
      fait.textContent = 'fait';
      infos.replaceChildren(fait, `, ${total} acquis sur ${total}`);
    }
  } else if (etat === 'commence' && infos) {
    // « Commencé » garde l'état disponible : on y montre les acquis gagnés.
    infos.replaceChildren(pastilles(gagnes, total), typographier(`commencé : ${gagnes} acquis sur ${total}`));
  }
}

// ---------- 2. Le relevé ----------

const faits = parus.filter((p) => p.avancement.etat === 'fait');
for (const { numero } of faits) {
  document.querySelector(`[data-barre="${numero}"]`)?.classList.add('fait');
}
const compte = document.querySelector('[data-compte-faits] strong');
if (compte) compte.textContent = `${faits.length} sur ${stations.length}`;

// ---------- 3. Le bouton de lecture ----------

const suite = document.querySelector<HTMLElement>('[data-suite]');
const bouton = suite?.querySelector<HTMLAnchorElement>('a');
const apres = suite?.querySelector<HTMLElement>('.apres');
const commence = parus.find((p) => p.avancement.etat === 'commence');
const aFaire = parus.find((p) => p.avancement.etat === 'disponible');
if (suite && bouton && apres) {
  if (commence) {
    const { gagnes, total } = commence.avancement;
    bouton.href = commence.href;
    bouton.textContent = `Reprendre le chapitre ${commence.numero}`;
    apres.replaceChildren(pastilles(gagnes, total), typographier(`Ce que tu sais : ${gagnes} sur ${total}`));
  } else if (faits.length > 0 && aFaire) {
    bouton.href = aFaire.href;
    bouton.textContent = `Ouvrir le chapitre ${aFaire.numero}, ${aFaire.court}`;
    apres.textContent = suite.dataset.vagues ?? '';
  } else if (faits.length > 0) {
    const dernier = faits[faits.length - 1];
    bouton.href = dernier.href;
    bouton.textContent = `Revoir le chapitre ${dernier.numero}`;
    apres.textContent = suite.dataset.fini ?? '';
  }
}

// ---------- 4. Les embranchements, sur grand écran ----------

// Mesures du plan, les mêmes que dans CarteParcours.astro : la gouttière des
// noms de groupes (230 px), la position du trait (22 px), la largeur d'un
// embranchement (380 px), le centre et le rayon de sa pastille (32 et 24 px).
const GOUTTIERE = 230;
const RAIL = 22;
const LARGEUR_BRANCHE = 380;
const CENTRE_PASTILLE = 32;
const RAYON_PASTILLE = 24;

function placer(): void {
  if (!carte) return;
  const large = window.matchMedia('(min-width: 1220px)').matches;
  carte.classList.toggle('placee', large);
  carte.style.minHeight = '';
  const branches = [...carte.querySelectorAll<HTMLElement>('.branche')];
  for (const branche of branches) branche.style.top = '';
  if (!large) return;
  const cadre = carte.getBoundingClientRect();
  const xLigne = GOUTTIERE + RAIL;
  let bas = 0;
  for (const branche of branches) {
    const depart = carte.querySelector(`.l1 [data-chapitre-carte="${branche.dataset.depart}"]`);
    const raccord = carte.querySelector<HTMLElement>(`[data-raccord="${branche.dataset.ligne}"]`);
    if (!depart || !raccord) continue;
    // Le raccord passe dans l'écart laissé sous le chapitre de départ.
    const yRaccord = depart.getBoundingClientRect().bottom - cadre.top + 19;
    branche.style.top = `${yRaccord - CENTRE_PASTILLE}px`;
    const xPastille = cadre.width - LARGEUR_BRANCHE + RAIL - RAYON_PASTILLE;
    raccord.style.left = `${xLigne - 3}px`;
    raccord.style.top = `${yRaccord - 60}px`;
    raccord.style.width = `${xPastille - xLigne + 3}px`;
    raccord.style.height = '63px';
    bas = Math.max(bas, branche.offsetTop + branche.offsetHeight);
  }
  carte.style.minHeight = `${bas}px`;
}

placer();
window.addEventListener('resize', placer);
document.fonts?.ready.then(placer);
