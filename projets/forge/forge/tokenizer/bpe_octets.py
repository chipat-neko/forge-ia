"""Le tokenizer de « ton IA » : un BPE sur les octets, avec 64 jetons spéciaux.

BPE veut dire « Byte Pair Encoding » (codage par paires). On part des octets du
texte en UTF-8 : 256 symboles de base suffisent donc pour écrire n'importe quel
texte, émojis et caractères chinois compris, et aucun texte n'est jamais
« inconnu ». L'apprentissage colle ensuite, encore et encore, la paire de
symboles voisins la plus fréquente en un nouveau symbole : c'est une fusion.

Identifiants des jetons, pour une taille de vocabulaire `T` :

- 0 à 255 : les octets ;
- 256, 257… : les fusions, dans l'ordre où elles ont été apprises (la fusion de
  rang `r` donne le jeton `256 + r`) ;
- `T − 64` à `T − 1` : les 64 jetons spéciaux (voir `speciaux.py`).

Pour encoder un texte, on le pré-découpe en pré-mots (voir `predecoupage.py`),
puis, dans chaque pré-mot, on rejoue les fusions : tant que c'est possible, on
applique celle qui a été apprise en premier (la méthode de GPT-2).

Le tokenizer est figé à la fin de la vague 1 : à textes égaux, l'apprentissage
donne exactement les mêmes fusions, et le fichier enregistré est le même, octet
pour octet.
"""

from __future__ import annotations

import heapq
import json
import operator
import os
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from itertools import chain
from pathlib import Path

from forge.tokenizer.predecoupage import MOTIF_COMPILE, MOTIF_TON_IA
from forge.tokenizer.speciaux import NOMBRE_SPECIAUX, SPECIAUX, TAILLE_VOCABULAIRE

VERSION_DU_FORMAT = 1
NOMBRE_OCTETS = 256
# Les jetons sont rangés sur 16 bits (uint16) dans les fichiers de données :
# un vocabulaire ne peut donc pas dépasser 65 536 jetons.
TAILLE_MAXIMALE = 2**16

# Une paire de jetons (a, b) est rangée dans un seul entier, `(a << 16) | b` :
# les 16 bits du haut pour `a`, ceux du bas pour `b`. Un entier se range et se
# retrouve plus vite qu'un tuple dans un dictionnaire, ce qui compte quand on
# manipule des dizaines de millions de paires.
_DECALAGE = 16
_MASQUE = (1 << _DECALAGE) - 1

# Nombre de pré-mots gardés en mémoire par l'encodeur (voir `_CacheDesMots`).
_TAILLE_DU_CACHE = 2**18

# Plus grand que n'importe quel rang : « cette paire n'est pas une fusion ».
_AUCUN_RANG = 1 << 62


class _CacheDesMots(dict):
    """Pré-mot → ses jetons, calculés une seule fois puis gardés.

    Les mêmes pré-mots reviennent sans cesse (« ␣de », « ␣la », « ␣self »…) :
    on ne refait les fusions que la première fois. Quand le cache est plein, on
    le vide d'un coup ; les pré-mots fréquents y reviennent aussitôt.
    """

    def __init__(self, calculer: Callable[[str], tuple[int, ...]], taille_max: int):
        super().__init__()
        self._calculer = calculer
        self._taille_max = taille_max

    def __missing__(self, mot: str) -> tuple[int, ...]:
        # Appelée par `cache[mot]` quand `mot` n'y est pas encore.
        if len(self) >= self._taille_max:
            self.clear()
        jetons = self._calculer(mot)
        self[mot] = jetons
        return jetons


def _octets_utf8(mot: str) -> bytes:
    """Les octets UTF-8 d'un pré-mot, avec un message clair si c'est impossible."""
    try:
        return mot.encode("utf-8")
    except UnicodeEncodeError as erreur:
        raise ValueError(
            f"Le texte contient un caractère qui ne s'écrit pas en UTF-8 "
            f"({erreur.object[erreur.start:erreur.end]!r}, une moitié de paire de "
            "substitution U+D800 à U+DFFF, souvent laissée par un texte mal décodé). "
            "Nettoie le texte, par exemple avec "
            "texte.encode('utf-8', 'replace').decode('utf-8'), puis recommence."
        ) from None


def _verifier_taille(taille_vocabulaire: int, nombre_fusions: int = 0) -> None:
    """Vérifie qu'il y a de la place pour les octets, les fusions et les spéciaux."""
    minimum = NOMBRE_OCTETS + nombre_fusions + NOMBRE_SPECIAUX
    if taille_vocabulaire > TAILLE_MAXIMALE:
        raise ValueError(
            f"Taille de vocabulaire trop grande : {taille_vocabulaire}. Elle ne peut pas "
            "dépasser 65 536, car les jetons sont rangés sur 16 bits (uint16)."
        )
    if taille_vocabulaire < minimum:
        raise ValueError(
            f"Taille de vocabulaire trop petite : {taille_vocabulaire}. Il en faut au "
            f"moins {minimum} : {NOMBRE_OCTETS} octets, {nombre_fusions} fusions et "
            f"{NOMBRE_SPECIAUX} jetons spéciaux (au moins 320 sans aucune fusion)."
        )


class TokenizerOctets:
    """Encode un texte en identifiants de jetons, et les décode en texte.

    Attributs :

    - `fusions` : les paires `(a, b)` fusionnées, dans l'ordre d'apprentissage ;
    - `speciaux` : nom de chaque jeton spécial → son identifiant ;
    - `taille_vocabulaire` : nombre total d'identifiants ;
    - `premier_special` : identifiant du premier jeton spécial ;
    - `nom` : nom du tokenizer, par exemple « ton-ia-v1 ».

    Si l'apprentissage s'est arrêté faute de paires, les identifiants entre la
    dernière fusion et `premier_special` restent libres : ils ne désignent
    aucun jeton.
    """

    def __init__(
        self,
        fusions: Sequence[tuple[int, int]],
        taille_vocabulaire: int = TAILLE_VOCABULAIRE,
        nom: str = "sans-nom",
    ):
        _verifier_taille(taille_vocabulaire, len(fusions))
        self.nom = nom
        self.taille_vocabulaire = taille_vocabulaire
        self.premier_special = taille_vocabulaire - NOMBRE_SPECIAUX
        self.speciaux: dict[str, int] = {
            nom_special: self.premier_special + place for place, nom_special in enumerate(SPECIAUX)
        }
        self.fusions: list[tuple[int, int]] = []
        # Les octets de chaque jeton ordinaire, rangés par identifiant.
        octets = [bytes([i]) for i in range(NOMBRE_OCTETS)]
        # Paire (rangée dans un entier) → rang de sa fusion.
        self._rangs: dict[int, int] = {}
        for rang, (a, b) in enumerate(fusions):
            nouveau = NOMBRE_OCTETS + rang
            try:
                a, b = operator.index(a), operator.index(b)
            except TypeError:
                raise ValueError(
                    f"La fusion de rang {rang}, ({a!r}, {b!r}), ne contient pas deux entiers. "
                    "Le fichier du tokenizer est abîmé : récupère-le depuis git, ou réapprends "
                    "le tokenizer."
                ) from None
            if not (0 <= a < nouveau and 0 <= b < nouveau):
                raise ValueError(
                    f"La fusion de rang {rang}, ({a!r}, {b!r}), utilise un jeton qui "
                    f"n'existe pas encore : à ce rang, seuls les identifiants 0 à "
                    f"{nouveau - 1} sont définis. Le fichier du tokenizer est abîmé : "
                    "récupère-le depuis git, ou réapprends le tokenizer."
                )
            cle = (a << _DECALAGE) | b
            if cle in self._rangs:
                raise ValueError(
                    f"La paire ({a}, {b}) est fusionnée deux fois (rangs "
                    f"{self._rangs[cle]} et {rang}). Le fichier du tokenizer est abîmé : "
                    "récupère-le depuis git, ou réapprends le tokenizer."
                )
            self._rangs[cle] = rang
            self.fusions.append((a, b))
            octets.append(octets[a] + octets[b])
        # Identifiant → octets, pour décoder ; un jeton spécial se décode en son nom.
        self._octets_par_id: dict[int, bytes] = dict(enumerate(octets))
        for nom_special, identifiant in self.speciaux.items():
            self._octets_par_id[identifiant] = nom_special.encode("utf-8")
        self._cache = _CacheDesMots(self._fusionner_mot, _TAILLE_DU_CACHE)

    # --- Encoder et décoder ---------------------------------------------------

    def encoder(self, texte: str) -> list[int]:
        """Encode un texte en identifiants. N'émet jamais de jeton spécial.

        Un texte qui contient la chaîne « <|fin_texte|> » est encodé comme
        n'importe quel texte, octet par octet : pour ajouter un vrai jeton
        spécial, on utilise `id_special`.
        """
        # Pour chaque pré-mot, `cache[mot]` donne ses jetons (calculés au besoin),
        # puis `chain` met toutes ces listes bout à bout.
        return list(chain.from_iterable(map(self._cache.__getitem__, MOTIF_COMPILE.findall(texte))))

    def _fusionner_mot(self, mot: str) -> tuple[int, ...]:
        """Applique les fusions à un pré-mot, en commençant par celle de plus petit rang."""
        symboles = list(_octets_utf8(mot))
        rangs = self._rangs
        while len(symboles) > 1:
            # Le plus petit rang parmi les paires de voisins du mot.
            meilleur = min(
                rangs.get((gauche << _DECALAGE) | droite, _AUCUN_RANG)
                for gauche, droite in zip(symboles, symboles[1:])
            )
            if meilleur == _AUCUN_RANG:
                break  # plus aucune paire du mot n'est une fusion
            a, b = self.fusions[meilleur]
            nouveau = NOMBRE_OCTETS + meilleur
            # On colle toutes les occurrences de la paire, de gauche à droite et
            # sans chevauchement : avec la paire (a, a), « aaa » donne (aa, a).
            fusionnes: list[int] = []
            i = 0
            longueur = len(symboles)
            while i < longueur:
                if i + 1 < longueur and symboles[i] == a and symboles[i + 1] == b:
                    fusionnes.append(nouveau)
                    i += 2
                else:
                    fusionnes.append(symboles[i])
                    i += 1
            symboles = fusionnes
        return tuple(symboles)

    def decoder(self, ids: Sequence[int]) -> str:
        """Décode des identifiants en texte.

        Le décodage est exact pour une suite complète. Si la suite s'arrête au
        milieu d'un caractère de plusieurs octets (par exemple quand le modèle
        n'a pas fini de l'écrire), ce morceau devient « � » (U+FFFD). Un jeton
        spécial se décode en son nom, par exemple « <|fin_texte|> ».
        """
        table = self._octets_par_id
        try:
            octets = b"".join(map(table.__getitem__, ids))
        except KeyError:
            # Peut-être des entiers d'un autre type (un tenseur PyTorch, par
            # exemple) : on les convertit, et on cherche le mauvais identifiant.
            entiers = [operator.index(i) for i in ids]
            for identifiant in entiers:
                if identifiant not in table:
                    raise ValueError(self._message_identifiant_inconnu(identifiant)) from None
            octets = b"".join(map(table.__getitem__, entiers))
        # « replace » ne change rien à une suite d'octets UTF-8 complète et valide.
        return octets.decode("utf-8", errors="replace")

    def id_special(self, nom: str) -> int:
        """Identifiant d'un jeton spécial : `id_special("<|fin_texte|>")`."""
        try:
            return self.speciaux[nom]
        except KeyError:
            raise KeyError(
                f"Jeton spécial inconnu : {nom!r}. Les noms possibles sont dans "
                "forge.tokenizer.SPECIAUX, par exemple « <|fin_texte|> »."
            ) from None

    def octets_du_jeton(self, i: int) -> bytes:
        """Les octets d'un jeton (pour un jeton spécial : son nom en UTF-8)."""
        identifiant = operator.index(i)
        try:
            return self._octets_par_id[identifiant]
        except KeyError:
            raise ValueError(self._message_identifiant_inconnu(identifiant)) from None

    def _message_identifiant_inconnu(self, identifiant: int) -> str:
        if 0 <= identifiant < self.premier_special:
            raison = (
                f"il est libre : l'apprentissage s'est arrêté après {len(self.fusions)} "
                f"fusions, donc les jetons ordinaires vont de 0 à "
                f"{NOMBRE_OCTETS + len(self.fusions) - 1}"
            )
        else:
            raison = f"les identifiants de ce tokenizer vont de 0 à {self.taille_vocabulaire - 1}"
        return (
            f"L'identifiant {identifiant} ne désigne aucun jeton de « {self.nom} » : {raison}. "
            "Vérifie que ces identifiants viennent bien de ce tokenizer."
        )

    # --- Fichier --------------------------------------------------------------

    def enregistrer(self, chemin: Path) -> None:
        """Enregistre le tokenizer en JSON (UTF-8, fins de ligne `\\n`).

        Une fusion par ligne, pour que les différences restent lisibles dans
        git. L'écriture passe par un fichier `.tmp` renommé à la fin : on ne
        laisse jamais un fichier à moitié écrit sous le nom définitif.
        """
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)

        def liste(lignes: list[str], ouvrant: str, fermant: str) -> str:
            if not lignes:
                return ouvrant + fermant
            return ouvrant + "\n" + ",\n".join(lignes) + "\n  " + fermant

        speciaux = liste(
            [f"    {json.dumps(n, ensure_ascii=False)}: {i}" for n, i in self.speciaux.items()], "{", "}"
        )
        fusions = liste([f"    [{a}, {b}]" for a, b in self.fusions], "[", "]")
        texte = (
            "{\n"
            f'  "version": {VERSION_DU_FORMAT},\n'
            f'  "nom": {json.dumps(self.nom, ensure_ascii=False)},\n'
            f'  "motif": {json.dumps(MOTIF_TON_IA, ensure_ascii=False)},\n'
            f'  "taille_vocabulaire": {self.taille_vocabulaire},\n'
            f'  "speciaux": {speciaux},\n'
            f'  "fusions": {fusions}\n'
            "}\n"
        )
        temporaire = chemin.with_name(chemin.name + ".tmp")
        with open(temporaire, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(texte)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)

    @classmethod
    def charger(cls, chemin: Path) -> TokenizerOctets:
        """Relit un tokenizer enregistré par `enregistrer`, en vérifiant tout."""
        chemin = Path(chemin)
        reapprendre = "Récupère le fichier depuis git, ou réapprends le tokenizer (python -m forge tokenizer)."
        try:
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise FileNotFoundError(f"Fichier du tokenizer introuvable : {chemin}. {reapprendre}") from None
        except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
            raise ValueError(f"Le fichier {chemin} n'est pas un JSON lisible ({erreur}). {reapprendre}") from None
        if not isinstance(contenu, dict):
            raise ValueError(f"Le fichier {chemin} ne décrit pas un tokenizer. {reapprendre}")
        if contenu.get("version") != VERSION_DU_FORMAT:
            raise ValueError(
                f"Le fichier {chemin} est au format de version {contenu.get('version')!r}, "
                f"or ce code ne lit que la version {VERSION_DU_FORMAT}. Mets le code à jour, "
                "ou utilise un fichier de la bonne version."
            )
        if contenu.get("motif") != MOTIF_TON_IA:
            raise ValueError(
                f"Le motif de pré-découpage du fichier {chemin} n'est pas celui de ce code : "
                "ce tokenizer découperait les textes autrement qu'à son apprentissage. "
                f"{reapprendre}"
            )
        taille = contenu.get("taille_vocabulaire")
        fusions = contenu.get("fusions")
        if type(taille) is not int or not isinstance(fusions, list):
            raise ValueError(f"Le fichier {chemin} n'a pas de taille ou de fusions lisibles. {reapprendre}")
        paires: list[tuple[int, int]] = []
        for rang, paire in enumerate(fusions):
            if not (isinstance(paire, list) and len(paire) == 2):
                raise ValueError(
                    f"La fusion de rang {rang} du fichier {chemin} n'est pas une paire "
                    f"d'identifiants : {paire!r}. {reapprendre}"
                )
            paires.append((paire[0], paire[1]))
        tokenizer = cls(paires, taille, str(contenu.get("nom", "sans-nom")))
        if contenu.get("speciaux") != tokenizer.speciaux:
            raise ValueError(
                f"Les jetons spéciaux du fichier {chemin} ne correspondent pas à ceux du code "
                "(mêmes noms, dans le même ordre, sur les 64 derniers identifiants). "
                f"{reapprendre}"
            )
        return tokenizer


# --- Apprentissage ----------------------------------------------------------------


def entrainer_tokenizer(
    textes: Iterable[str],
    taille_vocabulaire: int = TAILLE_VOCABULAIRE,
    journal: Callable[[str], None] | None = None,
) -> TokenizerOctets:
    """Apprend `taille_vocabulaire − 320` fusions sur des textes.

    À chaque pas, on fusionne la paire de jetons voisins la plus fréquente. En
    cas d'égalité, on prend la plus petite `(octets(a), octets(b))` dans
    l'ordre lexicographique : le résultat ne dépend ni de l'ordre des textes,
    ni du hasard. On s'arrête plus tôt s'il ne reste plus aucune paire.

    `journal`, s'il est donné, reçoit des messages de progression (toutes les
    1 000 fusions). Une chaîne passée seule compte pour un seul texte.

    Pour aller vite sur des centaines de Mo, on ne recompte jamais tout :

    - les textes sont réduits à leurs pré-mots distincts, avec leur nombre
      d'apparitions ;
    - on tient à jour le nombre d'apparitions de chaque paire, et un index
      « paire → pré-mots qui la contiennent » : une fusion ne touche que les
      pré-mots où la paire apparaît, et seulement les paires voisines ;
    - un tas (file de priorité) donne la paire la plus fréquente. Quand un
      compte baisse, on ne retire pas l'ancienne entrée du tas (« suppression
      paresseuse ») : à la sortie, une entrée dont le compte n'est plus à jour
      est remise à sa vraie place.
    """
    if isinstance(textes, str):
        textes = [textes]
    _verifier_taille(taille_vocabulaire)
    nombre_fusions = taille_vocabulaire - NOMBRE_OCTETS - NOMBRE_SPECIAUX
    ecrire = journal if journal is not None else (lambda _message: None)
    debut = time.perf_counter()

    # 1. Les pré-mots distincts et leur nombre d'apparitions.
    compteur: Counter[str] = Counter()
    nombre_textes = 0
    for texte in textes:
        compteur.update(MOTIF_COMPILE.findall(texte))
        nombre_textes += 1
    # Chaque pré-mot devient la liste de ses octets. Un pré-mot d'un seul octet
    # ne contient aucune paire : il ne compte pas pour l'apprentissage.
    mots: list[list[int]] = []
    frequences: list[int] = []
    for morceau, frequence in compteur.items():
        octets = _octets_utf8(morceau)
        if len(octets) > 1:
            mots.append(list(octets))
            frequences.append(frequence)
    nombre_pre_mots = len(compteur)
    del compteur
    ecrire(
        f"Pré-découpage : {nombre_textes} textes, {nombre_pre_mots} pré-mots distincts "
        f"({time.perf_counter() - debut:.1f} s)."
    )

    # 2. Le compte de chaque paire, et l'index paire → pré-mots qui la contiennent.
    #    L'index peut garder un pré-mot qui ne contient plus la paire : on le
    #    vérifie au moment de fusionner, c'est moins cher que de le retirer.
    comptes: dict[int, int] = defaultdict(int)
    index: defaultdict[int, set[int]] = defaultdict(set)
    for numero, mot in enumerate(mots):
        frequence = frequences[numero]
        for gauche, droite in zip(mot, mot[1:]):
            cle = (gauche << _DECALAGE) | droite
            comptes[cle] += frequence
            index[cle].add(numero)
    comptes = dict(comptes)

    # 3. Le tas : (−compte, octets de a, octets de b, paire). Le plus petit sort
    #    en premier : le plus grand compte, puis, à égalité, les plus petits
    #    octets. La paire elle-même départage deux jetons aux octets identiques.
    octets_des_jetons = [bytes([i]) for i in range(NOMBRE_OCTETS)]
    tas = [
        (-compte, octets_des_jetons[cle >> _DECALAGE], octets_des_jetons[cle & _MASQUE], cle)
        for cle, compte in comptes.items()
    ]
    heapq.heapify(tas)
    ecrire(f"Comptage : {len(comptes)} paires distinctes ({time.perf_counter() - debut:.1f} s).")

    fusions: list[tuple[int, int]] = []
    while len(fusions) < nombre_fusions:
        # 4. La paire la plus fréquente, en sautant les entrées périmées du tas.
        meilleure = None
        while tas:
            moins_compte, octets_a, octets_b, cle = heapq.heappop(tas)
            compte = comptes.get(cle, 0)
            if compte == 0:
                continue  # la paire a disparu
            if compte != -moins_compte:
                # Le compte a baissé depuis : on remet la paire à sa vraie place.
                heapq.heappush(tas, (-compte, octets_a, octets_b, cle))
                continue
            meilleure = cle
            break
        if meilleure is None:
            ecrire(
                f"Arrêt après {len(fusions)} fusions : plus aucune paire à fusionner dans "
                f"ces textes. Les identifiants {NOMBRE_OCTETS + len(fusions)} à "
                f"{taille_vocabulaire - NOMBRE_SPECIAUX - 1} resteront libres."
            )
            break
        a = meilleure >> _DECALAGE
        b = meilleure & _MASQUE
        nouveau = NOMBRE_OCTETS + len(fusions)
        fusions.append((a, b))
        octets_des_jetons.append(octets_des_jetons[a] + octets_des_jetons[b])

        # 5. On fusionne la paire dans chaque pré-mot qui la contient, en notant
        #    comment changent les comptes des paires voisines. Pour une
        #    occurrence de (a, b) entre un voisin gauche g et un voisin droit d :
        #    (g, a) et (b, d) disparaissent, (g, nouveau) et (nouveau, d)
        #    apparaissent. Le voisin gauche est lu dans le mot déjà fusionné :
        #    dans « a b a b », la deuxième occurrence a pour voisin `nouveau`.
        variations: defaultdict[int, int] = defaultdict(int)
        for numero in index.pop(meilleure):
            mot = mots[numero]
            longueur = len(mot)
            frequence = frequences[numero]
            resultat: list[int] = []
            i = 0
            trouve = False
            while i < longueur:
                symbole = mot[i]
                if symbole == a and i + 1 < longueur and mot[i + 1] == b:
                    trouve = True
                    if resultat:
                        gauche = resultat[-1]
                        variations[(gauche << _DECALAGE) | a] -= frequence
                        cle = (gauche << _DECALAGE) | nouveau
                        variations[cle] += frequence
                        index[cle].add(numero)
                    if i + 2 < longueur:
                        droite = mot[i + 2]
                        variations[(b << _DECALAGE) | droite] -= frequence
                        cle = (nouveau << _DECALAGE) | droite
                        variations[cle] += frequence
                        index[cle].add(numero)
                    resultat.append(nouveau)
                    i += 2
                else:
                    resultat.append(symbole)
                    i += 1
            if trouve:
                mots[numero] = resultat

        # 6. On reporte les variations. La paire fusionnée n'existe plus nulle
        #    part. Seules les paires qui contiennent `nouveau` gagnent des
        #    apparitions : elles seules entrent dans le tas. Les autres ne font
        #    que baisser, et leur ancienne entrée sera corrigée à sa sortie.
        del comptes[meilleure]
        for cle, variation in variations.items():
            if variation == 0 or cle == meilleure:
                continue
            compte = comptes.get(cle, 0) + variation
            if compte > 0:
                comptes[cle] = compte
                if variation > 0:
                    heapq.heappush(
                        tas,
                        (-compte, octets_des_jetons[cle >> _DECALAGE], octets_des_jetons[cle & _MASQUE], cle),
                    )
            else:
                comptes.pop(cle, None)
                index.pop(cle, None)

        if len(fusions) % 1000 == 0:
            ecrire(
                f"{len(fusions)} fusions sur {nombre_fusions} "
                f"({time.perf_counter() - debut:.0f} s) ; dernière : "
                f"{octets_des_jetons[nouveau]!r}"
            )

    ecrire(f"Apprentissage terminé : {len(fusions)} fusions en {time.perf_counter() - debut:.1f} s.")
    return TokenizerOctets(fusions, taille_vocabulaire)
