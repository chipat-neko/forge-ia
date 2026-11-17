"""Les versions publiées de ton IA : télécharger une Release `ton-ia-*` et la charger, comme le ferait un lecteur.

Une version publiée est un dossier de trois fichiers que `forge exporter` a écrits (voir
`forge.exporter`) : les poids en bf16 (`<étiquette>.safetensors`), `config.json` et le tokenizer figé
`tokenizer-ton-ia-v1.json`. Ce module sait :

- `telecharger_fichiers` : prendre des fichiers d'une Release GitHub du dépôt `DEPOT`, un par un,
  chacun d'abord sous un nom en `.partiel`, renommé quand il est complet (un fichier à moitié
  téléchargé n'a jamais son vrai nom, et un fichier complet ne se retélécharge pas) ;
- `telecharger_publication` : le cas des trois fichiers d'une version de ton IA ;
- `charger_publication` : rendre le modèle (float32, mode évaluation), son tokenizer, le nom de sa
  version et l'empreinte SHA-256 de ses poids.

La variable d'environnement `FORGE_IA_MODELES` désigne un dossier qui contient déjà un sous-dossier
par étiquette (`<dossier>/ton-ia-1.5/…`) : le réseau n'est alors jamais utilisé.
"""

import json
import os
import socket
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

import torch
from safetensors.torch import load_file

from forge.chemins import sous_forge_donnees
from forge.exporter import EMPREINTE_DU_TOKENIZER, NOM_DE_LA_CONFIG, PLONGEMENT, SORTIE, TOKENIZER, empreinte_sha256
from forge.fichiers import remplacer
from forge.modele import ConfigModele, Transformer
from forge.tokenizer.bpe_octets import TokenizerOctets

DEPOT = "chipat-neko/forge-ia"
ETIQUETTES = ("ton-ia-1.5", "ton-ia-1.7", "ton-ia-1.8", "ton-ia-1.9", "ton-ia-1.10")
VARIABLE_DES_VERSIONS = "FORGE_IA_MODELES"
NOM_DU_TOKENIZER = TOKENIZER.name  # « tokenizer-ton-ia-v1.json »
DELAI_DU_SOCKET = 60  # secondes : un serveur muet plus longtemps que ça coupe le téléchargement

CONSEIL_DE_TELECHARGEMENT = (
    "Télécharge la version avec `python -m forge publication --etiquette ton-ia-1.5` "
    f"(ou depuis la page des versions de {DEPOT}), puis donne le dossier qui contient ses fichiers."
)


def nom_des_poids(etiquette: str) -> str:
    """Le nom du fichier des poids d'une version : « ton-ia-1.5 » donne « ton-ia-1.5.safetensors »."""
    return f"{etiquette}.safetensors"


@dataclass
class Publication:
    """Une version publiée de ton IA, chargée.

    `version` est le nom du fichier des poids sans `.safetensors` (« ton-ia-1.5 ») ;
    `empreinte_des_poids` est le SHA-256 de ce fichier (64 caractères hexadécimaux).
    """

    modele: Transformer
    tokenizer: TokenizerOctets
    version: str
    empreinte_des_poids: str


def charger_publication(dossier: Path, appareil: str = "cpu") -> Publication:
    """Charge la version publiée de `dossier` sur `appareil` (« cpu » ou « cuda »), en float32.

    Le dossier doit contenir exactement un fichier `*.safetensors`, `config.json` et
    `tokenizer-ton-ia-v1.json` (dont l'empreinte SHA-256 est `EMPREINTE_DU_TOKENIZER`). Le lien
    entre la sortie et le plongement est rétabli, les poids bf16 passent en float32 (sans perte) et
    le modèle rendu est en mode évaluation.
    """
    dossier = Path(dossier)
    conseil = CONSEIL_DE_TELECHARGEMENT
    if not dossier.is_dir():
        raise FileNotFoundError(f"Le dossier {dossier} n'existe pas. {conseil}")
    fichiers_de_poids = sorted(dossier.glob("*.safetensors"))
    if len(fichiers_de_poids) > 1:
        trouves = ", ".join(chemin.name for chemin in fichiers_de_poids)
        raise ValueError(
            f"{dossier} contient {len(fichiers_de_poids)} fichiers de poids ({trouves}) : il en faut exactement un. "
            "Laisse seul le fichier de la version que tu veux charger, ou sépare les versions en deux dossiers."
        )
    if not fichiers_de_poids:
        raise FileNotFoundError(f"Il n'y a aucun fichier .safetensors dans {dossier}. {conseil}")
    poids_safetensors = fichiers_de_poids[0]
    config_json, tokenizer_json = dossier / NOM_DE_LA_CONFIG, dossier / NOM_DU_TOKENIZER
    manquants = [chemin.name for chemin in (config_json, tokenizer_json) if not chemin.is_file()]
    if manquants:
        raise FileNotFoundError(f"Il manque {', '.join(manquants)} dans {dossier}. {conseil}")

    try:
        config = ConfigModele(**json.loads(config_json.read_text(encoding="utf-8")))
    except (ValueError, TypeError) as erreur:  # JSON illisible, champ inconnu ou manquant, dimensions impossibles
        raise ValueError(f"{config_json} ne décrit pas un modèle de forge ({erreur}). {conseil}") from erreur

    empreinte_du_tokenizer = empreinte_sha256(tokenizer_json)
    if empreinte_du_tokenizer != EMPREINTE_DU_TOKENIZER:
        raise ValueError(
            f"{tokenizer_json} n'a pas l'empreinte SHA-256 du tokenizer de ton IA ({EMPREINTE_DU_TOKENIZER}, "
            f"lue : {empreinte_du_tokenizer}). Le fichier a changé (fins de ligne réécrites, téléchargement coupé ?). {conseil}"
        )
    tokenizer = TokenizerOctets.charger(tokenizer_json)

    try:
        poids = load_file(poids_safetensors)
    except Exception as erreur:  # fichier tronqué, ou qui n'est pas un safetensors
        raise ValueError(f"{poids_safetensors} ne se lit pas ({type(erreur).__name__} : {erreur}). {conseil}") from erreur
    if PLONGEMENT in poids:
        poids.setdefault(SORTIE, poids[PLONGEMENT])  # les poids liés : la sortie est le plongement
    modele = Transformer(config)
    try:
        modele.load_state_dict({nom: tenseur.float() for nom, tenseur in poids.items()})
    except RuntimeError as erreur:
        raise ValueError(
            f"Les poids de {poids_safetensors} ne correspondent pas au modèle que {config_json.name} décrit "
            f"({str(erreur).splitlines()[0]}). Les fichiers ne viennent pas de la même version. {conseil}"
        ) from erreur
    modele = modele.to(torch.device(appareil)).eval()
    return Publication(
        modele=modele,
        tokenizer=tokenizer,
        version=poids_safetensors.stem,
        empreinte_des_poids=empreinte_sha256(poids_safetensors),
    )


def _url(etiquette: str, nom: str) -> str:
    return f"https://github.com/{DEPOT}/releases/download/{etiquette}/{nom}"


def telecharger_fichiers(etiquette: str, noms: Sequence[str], dossier: Path | None = None) -> Path:
    """Rend le dossier qui contient les fichiers `noms` de la Release `etiquette`, en les téléchargeant au besoin.

    - Si `FORGE_IA_MODELES` est posée : rend `<FORGE_IA_MODELES>/<etiquette>`, sans réseau ;
      `FileNotFoundError` si ce dossier ou un des fichiers manque.
    - Sinon : télécharge chaque fichier depuis la Release du dépôt `DEPOT` dans `dossier` (par défaut
      `publications/<etiquette>` sous `FORGE_DONNEES`). Un fichier se télécharge sous le nom
      `<nom>.partiel`, renommé quand il est complet : un fichier déjà complet n'est pas retéléchargé,
      et relancer après une coupure ne reprend que ce qui manque. Délai du socket : 60 s.
    """
    imposee = os.environ.get(VARIABLE_DES_VERSIONS)
    if imposee:
        local = Path(imposee) / etiquette
        manquants = [nom for nom in noms if not (local / nom).is_file()]
        if not local.is_dir() or manquants:
            quoi = f"le dossier {local} n'existe pas" if not local.is_dir() else f"il manque {', '.join(manquants)} dans {local}"
            raise FileNotFoundError(
                f"{VARIABLE_DES_VERSIONS} est posée ({imposee}) et {quoi}. Mets-y les fichiers de la version "
                f"{etiquette}, ou retire la variable pour les télécharger depuis {DEPOT}."
            )
        return local

    cible = Path(dossier) if dossier is not None else sous_forge_donnees(etiquette, "publications")
    cible.mkdir(parents=True, exist_ok=True)
    ancien_delai = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DELAI_DU_SOCKET)
    try:
        for nom in noms:
            final = cible / nom
            if final.is_file():
                continue
            partiel = cible / f"{nom}.partiel"
            adresse = _url(etiquette, nom)
            try:
                urlretrieve(adresse, partiel)
                remplacer(partiel, final)
            except (URLError, OSError) as erreur:  # réseau coupé, 404, disque plein, délai dépassé
                partiel.unlink(missing_ok=True)
                raise ConnectionError(
                    f"Le téléchargement de {adresse} a échoué ({type(erreur).__name__} : {erreur}). "
                    "Relance la même commande : les fichiers déjà complets ne sont pas retéléchargés."
                ) from erreur
            except BaseException:  # Ctrl+C : pas de demi-fichier
                partiel.unlink(missing_ok=True)
                raise
    finally:
        socket.setdefaulttimeout(ancien_delai)
    return cible


def telecharger_publication(etiquette: str, dossier: Path | None = None) -> Path:
    """Télécharge les trois fichiers d'une version de ton IA (poids, `config.json`, tokenizer) ; rend leur dossier."""
    return telecharger_fichiers(etiquette, (nom_des_poids(etiquette), NOM_DE_LA_CONFIG, NOM_DU_TOKENIZER), dossier)
