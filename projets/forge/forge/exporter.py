"""L'export de « ton IA » : les fichiers à publier, tirés d'une sauvegarde de l'entraînement.

Une sauvegarde de l'entraînement (`meilleur.pt`, `etape-*.pt`) sert à reprendre l'entraînement :
des poids en 32 bits, au format de PyTorch, avec les réglages de l'entraînement. Pour publier le
modèle, `exporter` écrit trois fichiers dans un dossier :

- `ton-ia-1.5.safetensors` (le nom peut changer) : les poids, en bf16 (16 bits par nombre : deux
  fois moins lourds, et la précision des calculs sur la carte graphique). Le format safetensors
  ne contient que des tableaux de nombres, sans code : l'ouvrir ne peut rien exécuter. Il refuse
  deux noms pour une même matrice ; or la sortie du modèle EST le plongement (« poids liés »,
  voir `forge.modele.transformer`). Seul `plongement.weight` est donc écrit, `sortie.weight`
  manque ;
- `config.json` : les dimensions du modèle, c'est-à-dire les champs de `ConfigModele`, de sorte
  que `ConfigModele(**config)` le reconstruit ;
- `tokenizer-ton-ia-v1.json` : la copie, à l'octet près, du tokenizer du dépôt, vérifiée par son
  empreinte SHA-256.

Pour recharger le modèle :

    config = ConfigModele(**json.loads(Path("config.json").read_text(encoding="utf-8")))
    poids = safetensors.torch.load_file("ton-ia-1.5.safetensors")
    poids.setdefault("sortie.weight", poids["plongement.weight"])  # le lien, rétabli
    modele = Transformer(config)
    modele.load_state_dict(poids)

Chaque fichier est d'abord écrit sous un nom en `.tmp`, puis renommé d'un coup : un fichier à
moitié écrit n'existe jamais sous son vrai nom.
"""

import dataclasses
import hashlib
import json
import shutil
import struct
import warnings
from pathlib import Path

import torch
from safetensors.torch import save_file

from forge.chemins import sous_forge_donnees, verifier_place
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement.chargeur import empreinte_du_tokenizer_des_jetons
from forge.entrainement.sauvegarde import lire_sauvegarde
from forge.fichiers import ecrire_atomique_vers, ecrire_texte
from forge.modele import ConfigModele, Transformer
from forge.tokenizer.bpe_octets import TokenizerOctets

NOM_DES_POIDS = "ton-ia-1.5.safetensors"
NOM_DE_LA_CONFIG = "config.json"
TOKENIZER = Path(__file__).parent / "ressources" / "tokenizer-ton-ia-v1.json"
# L'empreinte SHA-256 du fichier du tokenizer figé de ton IA, tel qu'il est dans le dépôt depuis la
# vague 1 (celle que publient le README et le LISEZMOI). À ne pas confondre avec
# `empreinte_du_tokenizer()`, le SHA-1 de ses fusions, que portent `index.json` et les sauvegardes.
EMPREINTE_DU_TOKENIZER = "3001e7ab40630739c4dec807c7a92c0d4fb469cc0fc4afa368704395391f21ba"


class TokenizerNonVerifie(UserWarning):
    """L'export a lieu, mais rien ne dit que la sauvegarde vient du tokenizer figé de ton IA."""


# `torch.compile` range le modèle d'origine sous `_orig_mod` : ses poids prennent ce préfixe.
PREFIXE_DE_LA_COMPILATION = "_orig_mod."
PLONGEMENT = "plongement.weight"
SORTIE = "sortie.weight"

# Marge pour l'en-tête du fichier safetensors et le fichier de configuration.
_MARGE_OCTETS = 1024**2


def empreinte_sha256(chemin: Path) -> str:
    """L'empreinte SHA-256 d'un fichier, en hexadécimal (64 caractères), lue par blocs de 1 Mo."""
    empreinte = hashlib.sha256()
    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024**2), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


# L'ordre des champs d'un tenseur dans l'en-tête, celui que `safetensors` écrit toujours.
_CHAMPS_D_UN_TENSEUR = ("dtype", "shape", "data_offsets")


def _en_tete_dans_l_ordre(en_tete: dict) -> dict:
    """L'en-tête avec un seul ordre possible : noms triés, métadonnées triées, champs des tenseurs dans l'ordre de `safetensors`."""
    resultat = {}
    for nom in sorted(en_tete):
        valeur = en_tete[nom]
        if nom == "__metadata__":
            valeur = {cle: valeur[cle] for cle in sorted(valeur)}
        elif isinstance(valeur, dict):
            connus = [cle for cle in _CHAMPS_D_UN_TENSEUR if cle in valeur]
            valeur = {cle: valeur[cle] for cle in (*connus, *sorted(set(valeur) - set(connus)))}
        resultat[nom] = valeur
    return resultat


def trier_l_en_tete(chemin: Path) -> None:
    """Réécrit l'en-tête JSON d'un fichier safetensors dans un ordre fixe, sans bouger d'un octet le reste.

    `safetensors` écrit les métadonnées de l'en-tête (`__metadata__` : `format`, `pas`) dans un ordre
    qui change d'un lancement à l'autre : deux exports du même modèle n'avaient donc pas la même
    empreinte. Les noms de tenseurs et les clés des métadonnées sont ici triés ; les champs d'un
    tenseur restent dans l'ordre fixe de la bibliothèque (`dtype`, `shape`, `data_offsets`).
    Le format (https://github.com/huggingface/safetensors) : 8 octets (un entier, petit-boutiste)
    qui donnent la taille N de l'en-tête, puis N octets de JSON en UTF-8, complétés à droite par des
    espaces, puis les nombres. L'en-tête réécrit, sans espace, n'est jamais plus long que l'ancien ;
    on le complète d'espaces jusqu'à N. La partie « nombres » et les `data_offsets` ne bougent pas.
    """
    with open(chemin, "r+b") as fichier:
        debut = fichier.read(8)
        if len(debut) < 8:
            raise ValueError(f"{chemin} n'est pas un fichier safetensors : l'en-tête est tronqué.")
        taille = struct.unpack("<Q", debut)[0]
        brut = fichier.read(taille)
        if len(brut) != taille:
            raise ValueError(f"{chemin} n'est pas un fichier safetensors : en-tête de {taille} octets annoncé, il est tronqué.")
        try:
            en_tete = json.loads(brut)
        except ValueError as erreur:
            raise ValueError(f"{chemin} n'est pas un fichier safetensors : l'en-tête n'est pas du JSON ({erreur}).") from erreur
        trie = json.dumps(_en_tete_dans_l_ordre(en_tete), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(trie) > taille:
            raise ValueError(f"L'en-tête réécrit de {chemin} ({len(trie)} octets) est plus long que l'original ({taille}).")
        fichier.seek(8)
        fichier.write(trie.ljust(taille, b" "))


def _meme_matrice(a: torch.Tensor, b: torch.Tensor) -> bool:
    """Deux poids liés : la même mémoire, ou du moins les mêmes nombres (après une copie)."""
    return a.shape == b.shape and (a.data_ptr() == b.data_ptr() or torch.equal(a, b))


def poids_a_publier(etat_du_modele: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Les poids d'une sauvegarde, prêts pour safetensors.

    - le préfixe `_orig_mod.` d'un modèle compilé par `torch.compile` est retiré ;
    - si la sortie est la même matrice que le plongement (poids liés), elle n'est pas gardée :
      safetensors refuse les tenseurs partagés, et le plongement suffit à la rétablir ;
    - chaque tenseur passe en bf16, sur le processeur, rangé d'un seul tenant en mémoire.
    """
    poids = {nom.removeprefix(PREFIXE_DE_LA_COMPILATION): tenseur for nom, tenseur in etat_du_modele.items()}
    if SORTIE in poids and PLONGEMENT in poids and _meme_matrice(poids[SORTIE], poids[PLONGEMENT]):
        del poids[SORTIE]
    return {nom: tenseur.detach().to("cpu", torch.bfloat16).contiguous() for nom, tenseur in poids.items()}


def _verifier_les_poids(poids: dict[str, torch.Tensor], config: ConfigModele, fichier: str) -> None:
    """Refuse des poids qui ne vont pas avec la configuration : le fichier publié ne se rechargerait pas."""
    with torch.device("meta"):  # un modèle sans mémoire : seulement les noms et les formes
        attendus = {nom: tuple(tenseur.shape) for nom, tenseur in Transformer(config).state_dict().items()}
    if SORTIE not in poids:
        del attendus[SORTIE]  # liée au plongement : elle se rétablit au chargement
    trouves = {nom: tuple(tenseur.shape) for nom, tenseur in poids.items()}
    if trouves != attendus:
        manquants = sorted(set(attendus) - set(trouves))
        en_trop = sorted(set(trouves) - set(attendus))
        mal_formes = sorted(nom for nom in set(trouves) & set(attendus) if trouves[nom] != attendus[nom])
        details = "; ".join(
            f"{titre} : {', '.join(noms[:3])}{'…' if len(noms) > 3 else ''}"
            for titre, noms in (("manquants", manquants), ("en trop", en_trop), ("de mauvaise forme", mal_formes))
            if noms
        )
        raise ValueError(
            f"Les poids de {fichier} ne correspondent pas au modèle que sa configuration décrit ({details}). "
            "La sauvegarde est abîmée, ou d'une autre version de la forge."
        )


def _verifier_nom_des_poids(nom: str) -> None:
    if not nom or Path(nom).name != nom or Path(nom).suffix != ".safetensors":
        raise ValueError(
            f"Nom de fichier des poids invalide : {nom!r}. Donne un simple nom de fichier qui finit par "
            f".safetensors, par exemple {NOM_DES_POIDS} : il est écrit dans le dossier de sortie."
        )


def _copier_le_tokenizer(temporaire: Path) -> None:
    shutil.copyfile(TOKENIZER, temporaire)
    if empreinte_sha256(temporaire) != EMPREINTE_DU_TOKENIZER:
        raise ValueError(
            f"La copie du tokenizer n'a pas l'empreinte SHA-256 attendue ({EMPREINTE_DU_TOKENIZER}) : "
            "le disque a mal écrit le fichier. Relance la même commande."
        )


def _verifier_le_tokenizer_de_la_sauvegarde(etat: dict, fichier: str) -> None:
    """Refuse une sauvegarde entraînée avec un autre tokenizer que le tokenizer figé de ton IA.

    L'empreinte comparée est celle des fusions (le SHA-1 d'`empreinte_du_tokenizer`, celle
    d'`index.json`), pas le SHA-256 du fichier (`EMPREINTE_DU_TOKENIZER`). Elle vient de la
    sauvegarde ; une ancienne sauvegarde ne l'a pas, on la lit alors dans l'`index.json` de ses
    données (`config["donnees"]`). Si on ne la trouve nulle part, l'export a lieu, avec un
    avertissement (`TokenizerNonVerifie`) qui dit ce qui n'a pas été vérifié.
    """
    attendue = empreinte_du_tokenizer(TokenizerOctets.charger(TOKENIZER))
    trouvee, origine = etat.get("empreinte_du_tokenizer"), "la sauvegarde"
    if trouvee is None:
        donnees = (etat.get("config") or {}).get("donnees")
        if donnees:
            index = sous_forge_donnees(donnees, "jetons") / "index.json"
            trouvee, origine = empreinte_du_tokenizer_des_jetons(index.parent), str(index)
    if trouvee is None:
        warnings.warn(
            f"Le tokenizer de {fichier} n'a pas pu être vérifié : la sauvegarde ne retient pas son "
            "empreinte, et l'index.json de ses données est introuvable. Rien ne dit qu'elle a été "
            "entraînée avec le tokenizer figé de ton IA ; vérifie-le avant de publier.",
            TokenizerNonVerifie,
            stacklevel=3,
        )
    elif trouvee != attendue:
        raise ValueError(
            f"{fichier} a été entraînée avec un autre tokenizer que le tokenizer figé de ton IA : "
            f"l'empreinte de ses fusions (SHA-1, celle d'index.json) lue dans {origine} est {trouvee}, "
            f"celle de {TOKENIZER.name} est {attendue}. Les jetons ne se liraient pas pareil : l'export "
            "est refusé."
        )


def exporter(sauvegarde: Path, dossier: Path, nom_des_poids: str = NOM_DES_POIDS) -> list[Path]:
    """Écrit les poids, la configuration et le tokenizer de `sauvegarde` dans `dossier` ; renvoie leurs chemins.

    - `sauvegarde` : un fichier `.pt` de l'entraînement (`meilleur.pt`, `etape-*.pt`), ou le
      dossier `sauvegardes/` (sa dernière étape) ;
    - `dossier` : où écrire (créé au besoin) ; un fichier du même nom est remplacé ;
    - `nom_des_poids` : le nom du fichier des poids, qui finit par `.safetensors`.

    Tout est vérifié avant d'écrire : le nom des poids, l'empreinte du tokenizer du dépôt (s'il a
    changé, ce n'est plus celui de ton IA : `ValueError`), la sauvegarde, son tokenizer (l'empreinte
    qu'elle retient, ou à défaut celle de l'`index.json` de ses données : un autre tokenizer est
    refusé, un tokenizer introuvable avertit), l'accord entre ses poids et sa configuration, puis la place sur le disque (`PlaceInsuffisante`).
    """
    _verifier_nom_des_poids(nom_des_poids)
    if empreinte_sha256(TOKENIZER) != EMPREINTE_DU_TOKENIZER:
        raise ValueError(
            f"Le tokenizer {TOKENIZER} n'a plus l'empreinte SHA-256 du tokenizer figé de ton IA "
            f"({EMPREINTE_DU_TOKENIZER}) : il a été modifié (fins de ligne changées par git ou un "
            "éditeur ?). Remets-le comme dans le dépôt (git checkout -- sur ce fichier), puis relance."
        )
    etat, fichier_lu = lire_sauvegarde(Path(sauvegarde))
    _verifier_le_tokenizer_de_la_sauvegarde(etat, fichier_lu)
    config = ConfigModele(**etat["config_modele"])
    poids = poids_a_publier(etat["modele"])
    pas = etat.get("pas")
    del etat  # la copie des poids en 32 bits ne sert plus
    _verifier_les_poids(poids, config, fichier_lu)

    dossier = Path(dossier)
    octets = sum(t.numel() * t.element_size() for t in poids.values()) + TOKENIZER.stat().st_size + _MARGE_OCTETS
    verifier_place(octets, dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = [dossier / nom_des_poids, dossier / NOM_DE_LA_CONFIG, dossier / TOKENIZER.name]
    informations = {"format": "pt"}  # « pt » : des tenseurs de PyTorch
    if pas is not None:  # une sauvegarde sans pas n'en écrit pas (jamais « None »)
        informations["pas"] = str(pas)

    def ecrire_les_poids(chemin: Path) -> None:
        save_file(poids, chemin, metadata=informations)
        trier_l_en_tete(chemin)  # le même modèle donne le même fichier, à l'octet près

    ecrire_atomique_vers(chemins[0], ecrire_les_poids)
    texte = json.dumps(dataclasses.asdict(config), ensure_ascii=False, indent=2) + "\n"
    ecrire_texte(chemins[1], texte)
    ecrire_atomique_vers(chemins[2], _copier_le_tokenizer)
    return chemins
