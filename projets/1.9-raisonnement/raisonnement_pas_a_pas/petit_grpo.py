"""Un tout petit GRPO : un modèle minuscule apprend à répéter un chiffre, puis 20 pas de GRPO de forge.

Le chapitre 1.9 explique que le GRPO ne peut amplifier qu'un comportement déjà présent. Cet essai le fait voir de bout
en bout, sur le processeur, avec le vrai code de forge et sans réécrire la boucle :

1. un modèle minuscule (2 couches, des vecteurs de 32 nombres) est d'abord **affiné à répéter un chiffre** :
   « Répète : 7 » → « 7 », sur dix chiffres, quelques pas de perte masquée, comme le SFT du chapitre 1.7. Il le fait à
   peu près, pas toujours : de quoi donner un signal au RL ;
2. il fait ensuite **`pas` pas de GRPO**, avec `forge.entrainement.methodes.pas_grpo` : pour chaque chiffre d'un lot,
   huit réponses, la récompense 1 si la réponse est juste (`forge.raisonnement.verification.est_juste`), l'avantage
   `r − moyenne` du groupe (`forge.raisonnement.grpo.avantages`), puis un pas de `forge.raisonnement.grpo.apprendre`.

Rien n'est réécrit ici que ce que forge n'a pas pour cette tâche : le petit affinage de départ, le lot de problèmes
(`ChargeurDeChiffres`, qui rend des `Probleme` de forge, comme `ChargeurInvites` le fait d'un dossier de
`forge problemes`) et la réunion des mesures.
"""

import time
from types import SimpleNamespace

import torch
import torch.nn.functional as F
from forge.affinage.jeu import IGNORE
from forge.conversation.format import Tour, encoder_conversation
from forge.entrainement.boucle import ReglagesGRPO
from forge.entrainement.methodes import pas_grpo
from forge.modele import ConfigModele, Transformer
from forge.raisonnement import grpo
from forge.raisonnement.problemes import Probleme
from forge.tokenizer import TokenizerOctets

from raisonnement_pas_a_pas.problemes import TOKENIZER

CHIFFRES = tuple(range(10))
CONTEXTE = 32  # l'invite fait une douzaine de jetons, la réponse en a quatre au plus
PAS_D_AFFINAGE = 220  # le modèle apprend à copier le chiffre d'un coup, entre 150 et 300 pas : 220 le laisse à mi-chemin
TAUX_D_AFFINAGE = 3e-3
TAUX_DU_GRPO = 3e-3
REGLAGES = dict(
    invites_par_pas=8,
    reponses_par_invite=8,
    jetons_max_reponse=4,
    temperature=1.0,
    top_k=50,
    lot_de_generation=64,
    controle_invites=10,
    controle_reponses=8,
    evaluation_invites=10,
)


# region: pas-grpo
def probleme_de_chiffre(chiffre: int) -> Probleme:
    """« Répète : 7 », dont la réponse est 7 : un problème de forge, que sa récompense sait vérifier."""
    return Probleme(f"repeter-1-{chiffre}", "repeter", 1, f"Répète : {chiffre}", (), chiffre)


class ChargeurDeChiffres:
    """Des lots de `taille_lot` problèmes, les chiffres de 0 à 9 pris à la suite, en boucle (comme `ChargeurInvites`)."""

    def __init__(self, taille_lot: int) -> None:
        self.taille_lot = taille_lot
        self.position = 0

    def lot(self) -> list[Probleme]:
        pris = [probleme_de_chiffre(CHIFFRES[(self.position + k) % len(CHIFFRES)]) for k in range(self.taille_lot)]
        self.position = (self.position + self.taille_lot) % len(CHIFFRES)
        return pris


def modele_minuscule(graine: int = 0) -> Transformer:
    """Un transformer minuscule (2 couches, des vecteurs de 32 nombres), aux poids tirés de `graine`."""
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        return Transformer(ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=CONTEXTE))


def affiner_a_repeter(modele: Transformer, tok: TokenizerOctets, pas: int = PAS_D_AFFINAGE, taux: float = TAUX_D_AFFINAGE) -> list[float]:
    """`pas` pas de perte masquée sur les dix conversations « Répète : d » → « d » ; rend la perte de chaque pas.

    Chaque conversation est encodée par `encoder_conversation` : la perte ne porte que sur la réponse (« d » et
    `<|fin_tour|>`), jamais sur l'énoncé. Le lot de chaque pas est les dix conversations.
    """
    exemples = [encoder_conversation(tok, [Tour("utilisateur", f"Répète : {c}"), Tour("assistant", str(c))]) for c in CHIFFRES]
    largeur = max(len(e.ids) for e in exemples) - 1
    bourrage = tok.id_special("<|bourrage|>")
    appareil = next(modele.parameters()).device
    ids = torch.full((len(exemples), largeur), bourrage, dtype=torch.long)
    cibles = torch.full((len(exemples), largeur), IGNORE, dtype=torch.long)
    for k, e in enumerate(exemples):
        n = len(e.ids) - 1
        ids[k, :n] = torch.tensor(e.ids[:-1])
        cibles[k, :n] = torch.tensor([i if appris else IGNORE for i, appris in zip(e.ids[1:], e.appris[1:], strict=True)])
    ids, cibles = ids.to(appareil), cibles.to(appareil)
    optimiseur = torch.optim.AdamW(modele.parameters(), lr=taux, weight_decay=0.0)
    modele.train()
    pertes = []
    for _ in range(pas):
        logits, _ = modele(ids)
        perte = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), cibles.reshape(-1), ignore_index=IGNORE)
        optimiseur.zero_grad(set_to_none=True)
        perte.backward()
        optimiseur.step()
        pertes.append(perte.item())
    return pertes


def essai_grpo(appareil: str, pas: int = 20) -> dict:
    """Un modèle minuscule affiné à répéter un chiffre, puis `pas` pas de GRPO de forge sur cette tâche.

    Rend `recompense_moyenne` et `groupes_sans_signal` (une valeur par pas : la récompense moyenne des réponses du pas,
    et la part des chiffres dont les huit réponses ont la même récompense, donc sans aucun avantage), `reussite_avant` et
    `reussite_apres` (la part des dix chiffres que le modèle répète bien, en glouton, avant et après le GRPO), la
    perte de l'affinage de départ (`perte_affinage`), les `reglages` de l'essai (la taille du modèle, les réponses par
    chiffre : le carnet les imprime au lieu de les retaper) et `secondes`. La récompense ne monte pas forcément : vingt pas
    sur un modèle minuscule ne le garantissent pas, et rien ici ne triche pour qu'elle monte.
    """
    tok = TokenizerOctets.charger(TOKENIZER)
    cible = torch.device(appareil)
    if cible.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError('La carte graphique est demandée, mais PyTorch ne la voit pas : demande "cpu".')
    modele = modele_minuscule().to(cible)
    pertes = affiner_a_repeter(modele, tok)
    problemes = [probleme_de_chiffre(c) for c in CHIFFRES]
    reglages = ReglagesGRPO(pas=pas, **REGLAGES)
    reussite_avant = grpo.reussite(modele, tok, problemes, reglages)
    config = SimpleNamespace(grpo=reglages, graine=0, micro_lot=16, ecretage=1.0)
    optimiseur = torch.optim.AdamW(modele.parameters(), lr=TAUX_DU_GRPO, weight_decay=0.0)
    chargeur = ChargeurDeChiffres(reglages.invites_par_pas)
    recompenses, sans_signal = [], []
    debut = time.perf_counter()
    for numero in range(1, pas + 1):
        mesures = pas_grpo(modele, optimiseur, chargeur, config, TAUX_DU_GRPO, cible, {"tokenizer": tok}, numero=numero)
        recompenses.append(mesures["recompense_moyenne"])
        sans_signal.append(mesures["groupes_sans_signal"])
    return {
        "appareil": str(cible),
        "pas": pas,
        "reglages": {
            "couches": modele.config.couches,
            "dim": modele.config.dim,
            "pas_d_affinage": PAS_D_AFFINAGE,
            "invites_par_pas": reglages.invites_par_pas,
            "reponses_par_invite": reglages.reponses_par_invite,
            "jetons_max_reponse": reglages.jetons_max_reponse,
            "taux": TAUX_DU_GRPO,
        },
        "perte_affinage": pertes,
        "reussite_avant": reussite_avant,
        "recompense_moyenne": recompenses,
        "groupes_sans_signal": sans_signal,
        "reussite_apres": grpo.reussite(modele, tok, problemes, reglages),
        "secondes": round(time.perf_counter() - debut, 1),
    }
# fin: pas-grpo
