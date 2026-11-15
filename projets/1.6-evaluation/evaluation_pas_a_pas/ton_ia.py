"""Charger « ton IA » publiée : les fichiers de la version GitHub `ton-ia-1.5`.

La version publiée n'est pas une sauvegarde de l'entraînement : `python -m forge exporter` en a tiré
trois fichiers, rangés dans un même dossier (voir `forge.exporter`) :

- `config.json` : les dimensions du modèle, les champs de `ConfigModele` ;
- `ton-ia-1.5.safetensors` : les poids, en bf16 (16 bits par nombre). La sortie du modèle est la même
  matrice que le plongement (« poids liés ») : seul `plongement.weight` est rangé, `sortie.weight`
  manque ;
- `tokenizer-ton-ia-v1.json` : le tokenizer figé de ton IA, reconnu à son empreinte SHA-256.

`charger_ton_ia` rétablit le lien et passe les poids en float32, sur le processeur comme sur la carte.
Le passage de bf16 à float32 est exact (un nombre bf16, ce sont les 16 premiers bits d'un float32) :
le modèle rendu calcule avec les poids publiés, tels quels, en float32 comme le reste du projet.
"""

import json
from pathlib import Path

import torch
from forge.exporter import EMPREINTE_DU_TOKENIZER, NOM_DE_LA_CONFIG, NOM_DES_POIDS, PLONGEMENT, SORTIE, empreinte_sha256
from forge.modele import ConfigModele, Transformer
from forge.tokenizer.bpe_octets import TokenizerOctets
from safetensors.torch import load_file

NOM_DU_TOKENIZER = "tokenizer-ton-ia-v1.json"
NOM_DE_LA_VERSION = Path(NOM_DES_POIDS).stem  # « ton-ia-1.5 » : le nom des relevés faits avec ces poids
TELECHARGER = (
    "Télécharge les fichiers de la version publiée dans un dossier, par exemple avec "
    "`gh release download ton-ia-1.5 --dir ton-ia-1.5` (ou depuis la page des versions du dépôt "
    "chipat-neko/forge-ia), puis donne ce dossier."
)


def charger_ton_ia(dossier: Path, appareil: str = "cpu") -> tuple[Transformer, TokenizerOctets]:
    """Le modèle publié de `dossier`, prêt à calculer sur `appareil` (« cpu » ou « cuda ») en float32, et son tokenizer.

    Lit `config.json` (`ConfigModele(**config)`), les poids `ton-ia-1.5.safetensors` (`sortie.weight`
    reprend `plongement.weight`) et `tokenizer-ton-ia-v1.json`, dont l'empreinte SHA-256 doit être celle
    du tokenizer figé de forge. Le modèle rendu est en mode évaluation.
    """
    dossier = Path(dossier)
    if not dossier.is_dir():
        raise FileNotFoundError(f"Le dossier de ton IA {dossier} n'existe pas. {TELECHARGER}")
    config_json, poids_safetensors, tokenizer_json = (dossier / nom for nom in (NOM_DE_LA_CONFIG, NOM_DES_POIDS, NOM_DU_TOKENIZER))
    manquants = [chemin.name for chemin in (config_json, poids_safetensors, tokenizer_json) if not chemin.is_file()]
    if manquants:
        raise FileNotFoundError(f"Il manque {', '.join(manquants)} dans {dossier}. {TELECHARGER}")

    try:
        config = ConfigModele(**json.loads(config_json.read_text(encoding="utf-8")))
    except (ValueError, TypeError) as erreur:  # JSON illisible, champ inconnu ou manquant, dimensions impossibles
        raise ValueError(f"{config_json} ne décrit pas un modèle de forge ({erreur}). {TELECHARGER}") from erreur

    empreinte = empreinte_sha256(tokenizer_json)
    if empreinte != EMPREINTE_DU_TOKENIZER:
        raise ValueError(
            f"{tokenizer_json} n'a pas l'empreinte SHA-256 du tokenizer de ton IA ({EMPREINTE_DU_TOKENIZER}, "
            f"lue\u202f: {empreinte}). Le fichier a changé (fins de ligne réécrites, téléchargement coupé\u202f?). {TELECHARGER}"
        )
    tokenizer = TokenizerOctets.charger(tokenizer_json)

    try:
        poids = load_file(poids_safetensors)
    except Exception as erreur:  # fichier tronqué, ou qui n'est pas un safetensors
        raise ValueError(f"{poids_safetensors} ne se lit pas ({type(erreur).__name__}\u202f: {erreur}). {TELECHARGER}") from erreur
    if PLONGEMENT in poids:
        poids.setdefault(SORTIE, poids[PLONGEMENT])  # les poids liés : la sortie est le plongement
    modele = Transformer(config)
    try:
        modele.load_state_dict({nom: tenseur.float() for nom, tenseur in poids.items()})
    except RuntimeError as erreur:
        raise ValueError(
            f"Les poids de {poids_safetensors} ne correspondent pas au modèle que {config_json.name} décrit "
            f"({str(erreur).splitlines()[0]}). Les fichiers ne viennent pas de la même version. {TELECHARGER}"
        ) from erreur
    return modele.to(torch.device(appareil)).eval(), tokenizer
