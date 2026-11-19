"""Ce que la DPO pousse : la réponse choisie vers le haut, ou la rejetée vers le bas ?

La perte DPO ne regarde que l'écart entre les deux gains : elle baisse autant si la choisie monte que si la
rejetée descend. Rien ne dit lequel arrive. Ce module le fait voir sur une seule paire et un modèle minuscule :
`pousser` fait quelques pas de DPO avec le vrai code de forge (`logps_des_rangees`, `perte_dpo`) et relève, à
chaque pas, la log-probabilité moyenne par jeton de chaque réponse.

La paire vient de `mesures/paires-exemples.json` quand ce fichier existe (une vraie paire de ton IA), sinon
elle est fabriquée (`PAIRE_FABRIQUEE`), et `paire_du_notebook` le dit.
"""

import json
from pathlib import Path

import forge
import torch

from forge.affinage.dpo import logps_des_rangees, perte_dpo
from forge.affinage.jeu import IGNORE, LotAffinage
from forge.conversation.format import Tour, invite_de_reponse
from forge.entrainement.boucle import ReglagesDPO
from forge.modele import ConfigModele, Transformer
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"

# Une paire fabriquée à la main : la choisie respecte la consigne de longueur et finit son tour, la rejetée bavarde.
PAIRE_FABRIQUEE = {
    "invite": [{"role": "utilisateur", "texte": "Quelle est la capitale de la France ? Réponds en une phrase."}],
    "choisie": {"texte": "La capitale de la France est Paris.", "terminee": True},
    "rejetee": {"texte": "Alors, la France, c'est un grand pays, avec beaucoup de villes, et parmi elles", "terminee": False},
    "contraintes": [["phrases_max", {"n": 1}]],
    "attendu": None,
}


# region: poussee
def paire_du_notebook(chemin_des_exemples: Path) -> tuple[dict, bool]:
    """(la paire, est-elle réelle ?) : la première de `paires-exemples.json` s'il existe, sinon la paire fabriquée."""
    chemin = Path(chemin_des_exemples)
    if chemin.is_file():
        paires = json.loads(chemin.read_text(encoding="utf-8"))
        if paires:
            p = paires[0]
            return (
                {
                    "invite": p["invite"],
                    "choisie": {"texte": p["choisie"]["texte"], "terminee": p["choisie"]["terminee"]},
                    "rejetee": {"texte": p["rejetee"]["texte"], "terminee": p["rejetee"]["terminee"]},
                    "contraintes": p["contraintes"],
                    "attendu": p["attendu"],
                },
                True,
            )
    return PAIRE_FABRIQUEE, False


def lot_de_la_paire(tok: TokenizerOctets, paire: dict) -> LotAffinage:
    """Deux rangées, la choisie puis la rejetée : l'invite, la réponse (et son `<|fin_tour|>` si elle a fini), du bourrage.

    Comme `forge preferences` les écrit : la perte ne porte que sur la réponse.
    """
    tours = [Tour(t["role"], t["texte"]) for t in paire["invite"]]
    invite = invite_de_reponse(tok, tours)
    fin_tour, bourrage = tok.id_special("<|fin_tour|>"), tok.id_special("<|bourrage|>")
    rangees = []
    for cle in ("choisie", "rejetee"):
        reponse = tok.encoder(paire[cle]["texte"]) + ([fin_tour] if paire[cle]["terminee"] else [])
        rangees.append((invite + reponse, len(invite)))
    largeur = max(len(ids) for ids, _ in rangees)
    ids = torch.full((2, largeur), bourrage, dtype=torch.int64)
    appris = torch.zeros((2, largeur), dtype=torch.bool)
    documents = torch.full((2, largeur), -1, dtype=torch.int64)
    for i, (suite, debut) in enumerate(rangees):
        ids[i, : len(suite)] = torch.tensor(suite)
        appris[i, debut : len(suite)] = True
        documents[i, : len(suite)] = 0
    suivant_appris = appris[:, 1:] & (documents[:, 1:] == documents[:, :-1])
    cibles = torch.where(suivant_appris, ids[:, 1:], torch.tensor(IGNORE))
    return LotAffinage(ids=ids[:, :-1], cibles=cibles, documents=documents[:, :-1])


def modele_minuscule(longueur_contexte: int, graine: int = 0) -> Transformer:
    """Un transformer minuscule (2 couches, des vecteurs de 32 nombres), aux poids tirés de `graine`."""
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        return Transformer(ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=longueur_contexte))


def pousser(modele: Transformer, lot: LotAffinage, reglages: ReglagesDPO, pas: int, taux: float) -> list[dict]:
    """`pas` pas de DPO sur une seule paire ; un relevé avant le premier pas (`pas` 0), puis un après chaque pas.

    La référence est le modèle de départ, ses log-probabilités calculées une fois. Chaque relevé : `pas`,
    `logps_choisie` et `logps_rejetee` (par jeton appris), `marge` (β fois l'écart des deux gains) et `perte`.
    """
    appareil = torch.device("cpu")
    modele.train()
    with torch.no_grad():
        somme, appris = logps_des_rangees(modele, lot, appareil)
    qc, qr = somme[0:1].double(), somme[1:2].double()
    lc, lr = appris[0:1], appris[1:2]
    optimiseur = torch.optim.AdamW(modele.parameters(), lr=taux, weight_decay=0.0)
    releves = []
    for numero in range(pas + 1):
        somme, _ = logps_des_rangees(modele, lot, appareil)
        perte, mesures = perte_dpo(somme[0:1], somme[1:2], qc, qr, lc, lr, reglages)
        releves.append(
            {
                "pas": numero,
                "logps_choisie": mesures["logps_choisie"].item(),
                "logps_rejetee": mesures["logps_rejetee"].item(),
                "marge": mesures["marge"].item(),
                "perte": perte.item(),
            }
        )
        if numero < pas:
            optimiseur.zero_grad(set_to_none=True)
            perte.backward()
            optimiseur.step()
    return releves
# fin: poussee
