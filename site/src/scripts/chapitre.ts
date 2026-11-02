// Le seul script client du gabarit de chapitre.
//
// Sur une page qui contient article[data-chapitre], il :
// 1. retire de la progression gardée les paris devenus obsolètes ;
// 2. restaure les paris déjà faits, les acquis, les étapes et les verrous ouverts ;
// 3. fait jouer les paris (verdict, acquis, verrou ouvert) ;
// 4. coche les étapes faites : toutes celles dont les paris sont joués, et
//    celles sans pari dont la fin passe au-dessus du milieu de l'écran ;
// 5. gagne les acquis annoncés par l'événement `forge:acquis` (îlots Svelte) ;
// 6. tient à jour la barre du haut et le récapitulatif ;
// 7. branche le bouton qui efface la progression du chapitre.
//
// Sans JavaScript, rien de tout cela : le HTML reste entièrement lisible, et
// aucune zone n'est verrouillée.
import { effacer, nettoyer, noterAcquis, noterEtape, noterPari } from '../lib/progression';
import { ouverture } from '../lib/canal';

/** Détail de l'événement `forge:acquis`, émis sur `window`. */
export interface DetailAcquis {
  cle: string;
}

const FINE = '\u202F';

function demarrer(article: HTMLElement): void {
  const numero = article.dataset.chapitre ?? '';
  if (!numero) return;

  // Vrai pendant la restauration : rien ne bouge, rien n'est réécrit.
  let restauration = true;
  // Vrai une fois la progression effacée : plus rien n'est noté avant le rechargement.
  let efface = false;

  const paris = [...article.querySelectorAll<HTMLElement>('.pari[data-pari]')];
  const boutonsDe = (pari: HTMLElement) => [...pari.querySelectorAll<HTMLButtonElement>('button[data-choix]')];

  // 1. Progression nettoyée des paris disparus ou dont le choix n'existe plus.
  const parisValides = Object.fromEntries(paris.map((p) => [p.dataset.pari!, boutonsDe(p).length]));
  const etat = nettoyer(numero, parisValides);
  const acquisGardes = new Set(etat.acquis);

  // ---------- Acquis : récapitulatif et pastilles de la barre ----------

  const lignes = new Map<string, HTMLElement>();
  for (const li of article.querySelectorAll<HTMLElement>('#recap li[data-acquis]')) {
    lignes.set(li.dataset.acquis!, li);
  }
  const total = article.querySelector<HTMLElement>('#recap [data-total]');
  const acquisMini = document.querySelector<HTMLElement>('[data-acquis-mini]');
  const pastilles = [...(acquisMini?.querySelectorAll<HTMLElement>('.pips i') ?? [])];

  function majAcquis(nouveau: boolean): void {
    const t = lignes.size;
    const n = [...lignes.values()].filter((li) => li.dataset.gagne === 'oui').length;
    if (total && t > 0) {
      total.textContent =
        n === 0
          ? `0 sur ${t}${FINE}: fais les paris pour remplir ta liste.`
          : n === t
            ? `${n} sur ${t}${FINE}: tout est acquis.`
            : `${n} sur ${t}`;
    }
    acquisMini?.setAttribute('aria-label', `Ce que tu sais${FINE}: ${n} sur ${t}`);
    pastilles.forEach((p, i) => {
      const plein = i < n;
      if (plein && nouveau && !p.classList.contains('plein')) p.classList.add('vient');
      p.classList.toggle('plein', plein);
    });
  }

  function gagner(cle: string): void {
    const li = lignes.get(cle);
    if (!li || li.dataset.gagne === 'oui') return;
    li.dataset.gagne = 'oui';
    if (!restauration) li.classList.add('vient');
    if (!acquisGardes.has(cle) && !efface) {
      acquisGardes.add(cle);
      noterAcquis(numero, cle);
    }
    majAcquis(!restauration);
  }

  // ---------- Paris ----------

  function ajouterMention(bouton: HTMLButtonElement, texte: string): void {
    const mention = document.createElement('span');
    mention.className = 'rep';
    mention.textContent = texte;
    // L'espace sépare la mention du choix dans le nom lu par les lecteurs d'écran.
    bouton.append(' ', mention);
  }

  function reveler(pari: HTMLElement, choix: number): void {
    if (pari.hasAttribute('data-repondu')) return;
    pari.setAttribute('data-repondu', '');
    const boutons = boutonsDe(pari);
    const choisi = boutons[choix];
    const juste = choisi.hasAttribute('data-juste');
    for (const bouton of boutons) {
      bouton.disabled = true;
      if (bouton.hasAttribute('data-juste')) {
        bouton.classList.add('juste');
        ajouterMention(bouton, bouton === choisi ? 'ton choix, juste' : 'bonne réponse');
      } else if (bouton === choisi) {
        bouton.classList.add('faux');
        ajouterMention(bouton, 'ton choix');
      } else {
        bouton.classList.add('attenue');
      }
    }
    const verdict = pari.querySelector<HTMLElement>('.verdict');
    if (!verdict) return;
    verdict.classList.add(juste ? 'ok' : 'ko');
    const titre = verdict.querySelector('.titre-v');
    if (titre) titre.textContent = juste ? 'Juste.' : 'Pas tout à fait.';
    verdict.hidden = false;
    if (!restauration) {
      verdict.classList.add('revele');
      // Le bouton choisi vient d'être désactivé : le focus passe au verdict,
      // que les lecteurs d'écran lisent aussitôt. S'il dépasse du bas de
      // l'écran, on le fait juste entrer (en douceur, sauf si le lecteur a
      // demandé moins de mouvement).
      verdict.focus({ preventScroll: true });
      const doux = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      verdict.scrollIntoView({ block: 'nearest', behavior: doux ? 'smooth' : 'auto' });
    }
  }

  function parier(pari: HTMLElement, choix: number): void {
    reveler(pari, choix);
    if (!efface && !restauration) noterPari(numero, pari.dataset.pari!, choix);
    if (pari.dataset.acquis) gagner(pari.dataset.acquis);
    if (pari.dataset.ouvre) ouverture(pari.dataset.ouvre).set(true);
  }

  for (const pari of paris) {
    const choix = etat.paris[pari.dataset.pari!];
    if (choix !== undefined) {
      parier(pari, choix);
    } else {
      // Firefox peut garder l'état « désactivé » d'un bouton au rechargement.
      for (const bouton of boutonsDe(pari)) bouton.disabled = false;
    }
    pari.addEventListener('click', (evenement) => {
      const bouton = (evenement.target as Element).closest<HTMLButtonElement>('button[data-choix]');
      if (!bouton || bouton.disabled || pari.hasAttribute('data-repondu')) return;
      parier(pari, Number(bouton.dataset.choix));
      majEtapes();
    });
  }

  // Acquis gardés qui ne viennent pas d'un pari (atelier, par exemple).
  for (const cle of etat.acquis) gagner(cle);

  // ---------- Verrous ----------

  function verrouiller(zone: HTMLElement): void {
    zone.inert = true;
    zone.classList.add('verrouille');
    if (zone.nextElementSibling?.classList.contains('verrou-msg')) return;
    const message = document.createElement('div');
    message.className = 'verrou-msg';
    const texte = document.createElement('p');
    texte.textContent = zone.dataset.message ?? '';
    message.append(texte);
    zone.after(message);
  }

  function deverrouiller(zone: HTMLElement): void {
    zone.inert = false;
    if (!restauration) zone.classList.add('anime');
    zone.classList.remove('verrouille');
    if (zone.nextElementSibling?.classList.contains('verrou-msg')) zone.nextElementSibling.remove();
  }

  for (const zone of article.querySelectorAll<HTMLElement>('[data-verrou]')) {
    const nom = zone.dataset.verrou!;
    ouverture(nom).subscribe((ouvert) => (ouvert ? deverrouiller(zone) : verrouiller(zone)));
  }

  // ---------- Étapes et barre du haut ----------

  const etapes = [...article.querySelectorAll<HTMLElement>('section.etape[id]')];
  // Étapes sans pari déjà faites (les autres se déduisent de leurs paris).
  const faites = new Set(etat.etapes);
  const barre = document.querySelector<HTMLElement>('[data-barre-etapes]');
  const liens = etapes.map((etape, i) => {
    const lien = document.createElement('a');
    lien.href = '#' + etape.id;
    barre?.append(lien);
    return { lien, titre: `Étape ${i + 1}${FINE}: ${etape.dataset.titre ?? ''}` };
  });

  const parisDe = (etape: HTMLElement) => [...etape.querySelectorAll<HTMLElement>('.pari[data-pari]')];

  function estFaite(etape: HTMLElement): boolean {
    const sesParis = parisDe(etape);
    if (sesParis.length === 0) return faites.has(etape.id);
    return sesParis.every((p) => p.hasAttribute('data-repondu'));
  }

  function majEtapes(): void {
    const etats = etapes.map(estFaite);
    const ici = etats.indexOf(false);
    etapes.forEach((etape, i) => {
      const faite = etats[i];
      if (faite && !efface && !restauration && !faites.has(etape.id)) {
        faites.add(etape.id);
        noterEtape(numero, etape.id);
      }
      etape.classList.toggle('faite', faite);
      etape.classList.toggle('ici', i === ici);
      const { lien, titre } = liens[i];
      lien.classList.toggle('faite', faite);
      lien.classList.toggle('ici', i === ici);
      lien.setAttribute('aria-label', faite ? `${titre}, faite` : titre);
      if (i === ici) lien.setAttribute('aria-current', 'step');
      else lien.removeAttribute('aria-current');
    });
  }

  // Une étape sans pari est faite quand sa fin passe au-dessus du milieu de l'écran.
  if ('IntersectionObserver' in window) {
    const observateur = new IntersectionObserver(
      (entrees) => {
        for (const entree of entrees) {
          if (!entree.isIntersecting) continue;
          const etape = entree.target.closest<HTMLElement>('section.etape');
          observateur.unobserve(entree.target);
          if (etape && !faites.has(etape.id) && !efface) {
            faites.add(etape.id);
            noterEtape(numero, etape.id);
            majEtapes();
          }
        }
      },
      { rootMargin: '0px 0px -50% 0px' },
    );
    for (const etape of etapes) {
      if (parisDe(etape).length > 0 || faites.has(etape.id)) continue;
      const fin = document.createElement('span');
      fin.className = 'fin-etape';
      fin.setAttribute('aria-hidden', 'true');
      etape.append(fin);
      observateur.observe(fin);
    }
  }

  // ---------- Acquis venus des îlots (atelier…) ----------

  window.addEventListener('forge:acquis', (evenement) => {
    const cle = (evenement as CustomEvent<Partial<DetailAcquis> | null>).detail?.cle;
    if (typeof cle === 'string') gagner(cle);
  });

  // ---------- Effacer la progression ----------

  const boutonEffacer = article.querySelector<HTMLButtonElement>('[data-effacer]');
  if (boutonEffacer) {
    boutonEffacer.hidden = false;
    boutonEffacer.addEventListener('click', () => {
      efface = true;
      effacer(numero);
      location.reload();
    });
  }

  majEtapes();
  majAcquis(false);
  restauration = false;
}

for (const article of document.querySelectorAll<HTMLElement>('article[data-chapitre]')) {
  demarrer(article);
}
