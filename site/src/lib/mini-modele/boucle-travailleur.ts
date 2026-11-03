// La boucle d'entraînement du Worker, sans le Worker : elle reçoit les
// messages de la page, fait des tranches de pas, et envoie ses progrès.
//
// travailleur.ts la branche sur self.onmessage et enchaîne les tranches par
// setTimeout. Ici, l'horloge et l'entraîneur sont passés au constructeur :
// les tests les remplacent par des faux, sans Worker ni minuterie.
//
// Le rythme :
//  - une tranche enchaîne des pas entiers, pendant 50 ms au plus, puis rend
//    la main (le Worker reste à l'écoute des messages entre deux tranches) ;
//  - en vitesse normale, elle s'arrête aussi dès que les pas faits depuis le
//    début de la fenêtre atteignent 150 × (maintenant − début) / 1 000 : au
//    plus 150 pas par seconde, pour voir la courbe se dessiner ;
//  - pas de rattrapage : la fenêtre repart à zéro à chaque lancement, reprise
//    ou changement de vitesse. Un trou de plus de 100 ms entre deux tranches
//    (machine en veille, minuteries bridées) est oublié comme une pause : il
//    ne compte ni pour le rythme, ni pour la durée, ni pour la mesure des pas
//    par seconde.
//
// Les messages : un progres part au plus toutes les 100 ms, avec les pertes
// des pas faits depuis le précédent ; tout de suite à chaque validation (aux
// multiples de validationTous, et au dernier pas), avec l'erreur de
// validation et les prénoms inventés. La page numérote chaque essai (la
// génération) : un message pause ou vitesse d'un autre essai est ignoré, et
// tout ce que la boucle envoie porte le numéro de son essai.
//
// La page n'importe de ce module que des types (import type) : la valeur
// Entraineur, et avec elle la liste des prénoms, n'entre que dans le Worker.

import { Entraineur } from './entrainement';
import { PRESETS_MINI, type NomPreset, type ReglagesMini } from './reglages';

/** Le plafond de la vitesse normale. */
export const PAS_PAR_SECONDE_NORMAL = 150;
/** La durée d'une tranche de pas, au plus. */
export const DUREE_TRANCHE_MS = 50;
/** L'intervalle minimal entre deux messages progres (sauf validation). */
export const INTERVALLE_MESSAGES_MS = 100;

export type Vitesse = 'normale' | 'rapide';

/** Ce que la page envoie au lancement : le préréglage, le taux choisi et la vitesse. */
export interface ReglagesLancement {
  preset: NomPreset;
  tauxMax: number;
  vitesse: Vitesse;
}

/** Les messages de la page vers le Worker. */
export type MessageVersTravailleur =
  /** Nouvelle génération : repart de zéro. Même génération : reprend. */
  | { type: 'lancer'; generation: number; reglages: ReglagesLancement }
  | { type: 'pause'; generation: number }
  | { type: 'vitesse'; generation: number; vitesse: Vitesse };

/** Un prénom inventé, et s'il est déjà dans la liste. Il peut être vide ('') : le modèle a tiré la fin tout de suite. */
export interface Prenom {
  texte: string;
  existe: boolean;
}

/** Les messages du Worker vers la page. */
export type MessageDuTravailleur =
  | {
      type: 'progres';
      generation: number;
      /** Le numéro du dernier pas fait. */
      pas: number;
      pasTotal: number;
      /** Les pertes des pas faits depuis le message précédent, dans l'ordre. */
      pertes: number[];
      /** La durée de l'entraînement, pauses non comprises. */
      dureeMs: number;
      /** Mesuré depuis le dernier lancement, reprise ou changement de vitesse. */
      pasParSeconde: number;
      validation?: { pas: number; perte: number };
      echantillons?: { pas: number; prenoms: Prenom[] };
    }
  | { type: 'etat'; generation: number; etat: 'en-pause' | 'termine' | 'diverge' }
  | { type: 'erreur'; generation: number; message: string };

/** Ce que la boucle demande à l'entraîneur : Entraineur le fait, un faux aussi. */
export interface EntraineurPilote {
  readonly pas: number;
  readonly diverge: boolean;
  readonly reglages: Pick<ReglagesMini, 'pasTotal' | 'validationTous'>;
  readonly donnees: { readonly connus: ReadonlySet<string> };
  faireUnPas(): number;
  perteValidation(): number;
  echantillons(): string[];
}

type Progres = Extract<MessageDuTravailleur, { type: 'progres' }>;

/** La boucle d'un Worker : un seul essai à la fois, celui de la dernière génération lancée. */
export class BoucleTravailleur {
  private generation: number | null = null;
  private entraineur: EntraineurPilote | null = null;
  private vitesse: Vitesse = 'normale';
  /** Vrai entre un lancement (ou une reprise) et une pause ou la fin. */
  private enCours = false;
  /** Vrai une fois l'essai terminé, divergé ou en erreur : il faut une nouvelle génération. */
  private fini = false;
  // La fenêtre du rythme, et celle de la mesure des pas par seconde.
  private debutFenetre = 0;
  private pasFenetre = 0;
  private debutMesure = 0;
  private pasMesure = 0;
  // La durée : celle des courses d'avant, et le début de la course actuelle.
  private dureeAvant = 0;
  private debutCourse = 0;
  private finTranche = 0;
  private dernierEnvoi = 0;
  private pertes: number[] = [];

  constructor(
    private readonly envoyer: (m: MessageDuTravailleur) => void,
    private readonly horloge: () => number,
    private readonly creerEntraineur: (r: ReglagesMini) => EntraineurPilote = (r) => new Entraineur(r),
  ) {}

  /** Un message de la page. */
  recevoir(m: MessageVersTravailleur): void {
    if (m.type === 'lancer') {
      this.lancer(m.generation, m.reglages);
    } else if (m.generation === this.generation) {
      if (m.type === 'pause') this.pause();
      else this.changerVitesse(m.vitesse);
    }
  }

  /**
   * Une tranche de pas, de 50 ms au plus. Renvoie vrai s'il faut une autre
   * tranche (l'essai est en cours), faux sinon (en pause, fini, ou rien de lancé).
   */
  tranche(): boolean {
    const e = this.entraineur;
    if (!this.enCours || this.fini || e === null) return false;
    const debut = this.horloge();
    this.oublierTrou(debut);
    let maintenant = debut;
    try {
      while (maintenant - debut < DUREE_TRANCHE_MS && !this.assezPourLeRythme(maintenant)) {
        const perte = e.faireUnPas();
        this.pertes.push(perte);
        this.pasFenetre += 1;
        this.pasMesure += 1;
        maintenant = this.horloge();
        if (e.diverge) {
          this.envoyerProgres(maintenant);
          this.terminer('diverge', maintenant);
          return false;
        }
        const dernier = e.pas >= e.reglages.pasTotal;
        if (dernier || e.pas % e.reglages.validationTous === 0) {
          const validation = { pas: e.pas, perte: e.perteValidation() };
          const prenoms = e.echantillons().map((texte) => ({ texte, existe: e.donnees.connus.has(texte) }));
          maintenant = this.horloge();
          this.envoyerProgres(maintenant, { validation, echantillons: { pas: e.pas, prenoms } });
          if (dernier) {
            this.terminer('termine', maintenant);
            return false;
          }
        }
      }
    } catch (erreur) {
      this.echouer(erreur);
      return false;
    }
    if (this.pertes.length > 0 && maintenant - this.dernierEnvoi >= INTERVALLE_MESSAGES_MS) {
      this.envoyerProgres(maintenant);
    }
    this.finTranche = maintenant;
    return true;
  }

  private lancer(generation: number, reglages: ReglagesLancement): void {
    const maintenant = this.horloge();
    if (generation !== this.generation) {
      // Un nouvel essai : on oublie tout de l'ancien.
      this.generation = generation;
      this.entraineur = null;
      this.enCours = false;
      this.fini = false;
      this.dureeAvant = 0;
      this.pertes = [];
      try {
        if (!Object.hasOwn(PRESETS_MINI, reglages.preset)) {
          throw new RangeError(
            `Préréglage inconnu : « ${String(reglages.preset)} ». Choisis « complet » ou « avant-gout ».`,
          );
        }
        this.entraineur = this.creerEntraineur({ ...PRESETS_MINI[reglages.preset], tauxMax: reglages.tauxMax });
      } catch (erreur) {
        this.echouer(erreur);
        return;
      }
    }
    if (this.fini || this.entraineur === null) return; // fini : il faut une nouvelle génération
    this.vitesse = reglages.vitesse;
    if (!this.enCours) {
      this.enCours = true;
      this.debutCourse = maintenant;
      this.dernierEnvoi = maintenant;
    }
    this.ouvrirFenetre(maintenant);
  }

  private pause(): void {
    if (!this.enCours || this.fini) return;
    const maintenant = this.horloge();
    if (this.pertes.length > 0) this.envoyerProgres(maintenant);
    this.dureeAvant += maintenant - this.debutCourse;
    this.enCours = false;
    this.envoyer({ type: 'etat', generation: this.numero(), etat: 'en-pause' });
  }

  private changerVitesse(vitesse: Vitesse): void {
    if (this.fini) return;
    this.vitesse = vitesse;
    if (this.enCours) this.ouvrirFenetre(this.horloge());
  }

  /** Une fenêtre neuve : le rythme et la mesure repartent de zéro, sans rattrapage. */
  private ouvrirFenetre(maintenant: number): void {
    this.debutFenetre = maintenant;
    this.pasFenetre = 0;
    this.debutMesure = maintenant;
    this.pasMesure = 0;
    this.finTranche = maintenant;
  }

  /** Un trou de plus de 100 ms depuis la tranche d'avant compte comme une pause : on le retire de tout. */
  private oublierTrou(maintenant: number): void {
    const trou = maintenant - this.finTranche;
    if (trou > INTERVALLE_MESSAGES_MS) {
      this.debutFenetre += trou;
      this.debutMesure += trou;
      this.debutCourse += trou;
      this.dernierEnvoi += trou;
    }
  }

  /** En vitesse normale : vrai quand la fenêtre a déjà ses 150 pas par seconde. */
  private assezPourLeRythme(maintenant: number): boolean {
    if (this.vitesse !== 'normale') return false;
    return this.pasFenetre >= (PAS_PAR_SECONDE_NORMAL * (maintenant - this.debutFenetre)) / 1000;
  }

  private envoyerProgres(maintenant: number, extra: Pick<Progres, 'validation' | 'echantillons'> = {}): void {
    const e = this.entraineur;
    if (e === null) return;
    const ecoule = maintenant - this.debutMesure;
    const message: Progres = {
      type: 'progres',
      generation: this.numero(),
      pas: e.pas,
      pasTotal: e.reglages.pasTotal,
      pertes: this.pertes,
      dureeMs: this.dureeAvant + (this.enCours ? maintenant - this.debutCourse : 0),
      pasParSeconde: ecoule > 0 ? (this.pasMesure * 1000) / ecoule : 0,
      ...extra,
    };
    this.pertes = []; // un tableau neuf : celui du message ne bouge plus
    this.dernierEnvoi = maintenant;
    this.envoyer(message);
  }

  private terminer(etat: 'termine' | 'diverge', maintenant: number): void {
    this.dureeAvant += maintenant - this.debutCourse;
    this.enCours = false;
    this.fini = true;
    this.envoyer({ type: 'etat', generation: this.numero(), etat });
  }

  /** Une erreur du moteur : les pertes déjà calculées partent d'abord, puis le message d'erreur. */
  private echouer(erreur: unknown): void {
    if (this.pertes.length > 0) this.envoyerProgres(this.horloge());
    this.enCours = false;
    this.fini = true;
    const message = erreur instanceof Error ? erreur.message : String(erreur);
    this.envoyer({ type: 'erreur', generation: this.numero(), message });
  }

  private numero(): number {
    if (this.generation === null) throw new Error("BoucleTravailleur : aucun essai lancé (envoie d'abord « lancer »).");
    return this.generation;
  }
}
