"""Exécuter du code Python généré par ton IA dans un sous-processus limité, et dire s'il a réussi.

`executer` lance un programme et rend un `ResultatExecution` ; `executer_tous` en lance plusieurs à la fois, sur
les fils du processeur. Ce qui est limité (le délai, la mémoire, le nombre de processus, le dossier) et ce qui ne
l'est pas (le réseau, les fichiers de l'utilisateur) est détaillé dans la docstring de `executer`.
"""

import math
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from forge.processeur import fils_disponibles

Raison = Literal["reussi", "echec", "delai", "memoire", "erreur_systeme"]


@dataclass(frozen=True)
class ResultatExecution:
    """Ce qu'a donné un programme.

    - `reussi` : vrai seulement si le programme a fini sans erreur, dans le délai (code de sortie 0) ;
    - `raison` : `reussi` ; `echec` (une erreur, un `assert` faux, un code de sortie non nul) ; `delai` (arrêté
      au délai) ; `memoire` (le programme a levé `MemoryError`, par exemple en dépassant la limite) ;
      `erreur_systeme` (le programme n'a pas pu être lancé, ou pas dans ses limites : il n'a pas tourné) ;
    - `sortie` : la sortie standard et les erreurs réunies, au plus `sortie_max` caractères (le début) ;
    - `secondes` : la durée du programme, du signal de départ à sa fin.
    """

    reussi: bool
    raison: Raison
    sortie: str
    secondes: float


class DossierJetableNonEfface(UserWarning):
    """Le dossier jetable d'un programme n'a pas pu être effacé : il reste sous `TEMP`, à effacer à la main."""



# Les codes de sortie propres à l'amorce (des codes qu'un programme de test n'a pas de raison de choisir) : le
# programme a levé MemoryError ; l'amorce n'a pas reçu son départ, et le programme n'a pas tourné.
_CODE_MEMOIRE = 197
_CODE_SANS_DEPART = 198

# L'octet de départ. L'amorce n'exécute le programme qu'après l'avoir reçu : sous Windows, le processus est rangé
# dans son objet Job avant son envoi. La fin du tube n'est pas un départ : elle arrive quand la forge meurt entre
# le lancement et le rangement (noyau de notebook redémarré, terminal fermé…), et le programme tournerait alors
# hors du Job. L'amorce sort donc sans rien exécuter.
_DEPART = b"\n"

# L'amorce, lancée par `python -I -X utf8 -c`. Elle attend l'octet de départ sur l'entrée standard. Ailleurs que
# sous Windows, elle pose elle-même les limites de mémoire et de temps de calcul (`resource`), puis exécute le
# fichier du programme comme `__main__`. Ses arguments : le fichier, la mémoire en octets, les secondes de calcul.
_AMORCE = f"""
import sys
if sys.stdin.buffer.read(1) != {_DEPART!r}:
    sys.exit({_CODE_SANS_DEPART})
programme, memoire, calcul = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
if sys.platform != "win32":
    import resource
    for limite, souple, dure in ((resource.RLIMIT_AS, memoire, memoire), (resource.RLIMIT_CPU, calcul, calcul + 1)):
        plafond = resource.getrlimit(limite)[1]
        if plafond != resource.RLIM_INFINITY:
            souple, dure = min(souple, plafond), min(dure, plafond)
        resource.setrlimit(limite, (souple, dure))
sys.argv = [programme]
import runpy
try:
    runpy.run_path(programme, run_name="__main__")
except MemoryError:
    try:
        import traceback
        traceback.print_exc()
    finally:
        sys.exit({_CODE_MEMOIRE})
"""

# La lecture de la sortie garde au plus ce nombre d'octets par caractère demandé (un caractère UTF-8 en prend
# au plus 4), et jette le reste sans arrêter le programme : un programme qui écrit sans fin ne remplit pas la
# mémoire de la forge.
_OCTETS_PAR_CARACTERE = 4

# L'attente, en secondes, de la fin d'un programme qu'on vient d'arrêter (elle ne dure qu'un instant d'habitude).
_ATTENTE_APRES_ARRET = 10.0

# Les pauses, en secondes, entre deux essais d'effacement du dossier jetable (0,75 s en tout au pire).
_PAUSES_D_EFFACEMENT = (0.05, 0.1, 0.2, 0.4)


def executer(programme: str, delai: float = 5.0, memoire_mo: int = 512, sortie_max: int = 10_000) -> ResultatExecution:
    """Exécute `programme` (du code Python) dans un sous-processus limité, et dit s'il a réussi.

    Ce qui est fait :

    - le programme est écrit dans un dossier jetable sous `TEMP` (`forge-code-…`), qui devient son dossier
      courant et son `TEMP`, et qui est effacé à la fin, même après une erreur ou un délai dépassé ;
    - il tourne dans l'interpréteur Python de base (pas celui de l'environnement virtuel : seulement la
      bibliothèque standard), en mode isolé (`-I` : il ignore les variables `PYTHON*`, les paquets de
      l'utilisateur et le dossier courant), en UTF-8 (`-X utf8`), avec un environnement réduit à
      `PATH` (le dossier de l'interpréteur), `TEMP`, `TMP`, `PYTHONIOENCODING` et, sous Windows, `SYSTEMROOT` ;
    - **sous Windows**, il est rangé dans un objet Job avant sa première ligne (l'amorce attend un octet de
      départ, envoyé après le rangement, et ne fait rien sans lui) : au plus `memoire_mo` Mio de mémoire, un seul
      processus (créer un processus lui-même échoue), et le Job tue ce qu'il contient quand il est fermé, y
      compris quand la forge meurt. Au délai, `TerminateJobObject` l'arrête ;
    - **ailleurs** (Linux), il ouvre sa propre session : sa mémoire est limitée à `memoire_mo` Mio
      (`RLIMIT_AS`, l'espace d'adressage) et son temps de calcul à délai + 1 s (`RLIMIT_CPU`). Au délai, et
      aussi quand il a fini, tout son groupe de processus est tué (`os.killpg`) ;
    - la sortie standard et les erreurs sont réunies et tronquées à `sortie_max` caractères.

    Ce qui n'est **pas** empêché, sous Windows comme ailleurs. Ce n'est pas un vrai bac à sable :

    - **le réseau** : le programme peut ouvrir des connexions, télécharger ou envoyer des données ;
    - **l'écriture dans les dossiers de l'utilisateur** : il peut écrire, modifier ou effacer tout fichier que
      l'utilisateur qui lance la forge a le droit de toucher, hors de son dossier jetable ;
    - **la lecture des fichiers de l'utilisateur** : documents, clés, jetons de connexion, données de la forge ;
    - **sous Windows**, un processus créé pour lui par un service (WMI `Win32_Process.Create`, le planificateur
      de tâches, un serveur COM) naît hors du Job, sans ses limites, et lui survit ;
    - **sous Linux**, un processus qu'il lance peut quitter son groupe (`setsid`) et échapper à `os.killpg`, le
      nombre de processus n'est pas limité (`RLIMIT_NPROC` compterait tous ceux de l'utilisateur), et si la forge
      est tuée net (`kill -9`, noyau du notebook redémarré), le programme en cours lui survit jusqu'à sa fin :
      `RLIMIT_CPU` arrête une boucle de calcul, pas une attente (`time.sleep`).

    C'est fait pour le code de ton IA aux problèmes de HumanEval, sur ton PC : du code qui peut boucler, prendre
    trop de mémoire ou écrire des mégaoctets, mais qu'on ne soupçonne pas de nuire. Du code venu d'ailleurs, ou
    écrit pour nuire, doit tourner dans une machine virtuelle ou un conteneur sans réseau.

    `ValueError` si `delai` n'est pas un nombre fini plus grand que 0, si `memoire_mo` n'est pas positif, ou si
    `sortie_max` est négatif. `RuntimeError` si l'interpréteur de base est introuvable (voir `_interpreteur`).
    Un dossier jetable qui ne s'efface pas ne lève rien : un avertissement `DossierJetableNonEfface` le nomme.
    """
    if not (math.isfinite(delai) and delai > 0):
        raise ValueError(
            f"delai = {delai} : le délai est une durée finie en secondes, plus grande que 0. "
            "Donne par exemple delai=5."
        )
    if memoire_mo < 1:
        raise ValueError(
            f"memoire_mo = {memoire_mo} : la mémoire permise se compte en Mio, au moins 1. "
            "Donne par exemple memoire_mo=512."
        )
    if sortie_max < 0:
        raise ValueError(
            f"sortie_max = {sortie_max} : le nombre de caractères gardés ne peut pas être négatif "
            "(0 n'en garde aucun)."
        )
    interpreteur = _interpreteur()
    dossier = Path(tempfile.mkdtemp(prefix="forge-code-"))
    try:
        fichier = dossier / "programme.py"
        fichier.write_text(programme, encoding="utf-8")
        return _lancer(interpreteur, fichier, dossier, delai, memoire_mo, sortie_max)
    finally:
        _effacer(dossier)


def executer_tous(programmes: Sequence[str], processus: int | None = None, **reglages) -> list[ResultatExecution]:
    """Exécute chaque programme par `executer` (avec les mêmes `reglages`), plusieurs à la fois ; ordre gardé.

    `processus` programmes tournent en même temps, chacun suivi par un fil ; par défaut, autant que de fils de
    calcul disponibles (`fils_disponibles()`).
    """
    if processus is not None and processus < 1:
        raise ValueError(
            f"processus = {processus} : il faut au moins 1 programme à la fois. "
            "Laisse None pour en lancer autant que de fils de calcul disponibles."
        )
    with ThreadPoolExecutor(max_workers=processus or fils_disponibles()) as fils:
        return list(fils.map(lambda programme: executer(programme, **reglages), programmes))


def _interpreteur() -> str:
    """L'interpréteur Python de base, celui qui exécute les programmes.

    Sous Windows, le `python.exe` d'un environnement virtuel (`.venv/Scripts/python.exe`, celui de `uv run`) n'est
    qu'un lanceur : il démarre le vrai interpréteur dans un processus enfant, dès sa création, donc avant que le
    lanceur soit rangé dans l'objet Job. Le programme tournerait alors hors du Job, sans ses limites. On lance
    donc l'interpréteur de base (`sys._base_executable`), partout, pour que le programme voie la même chose sous
    Windows et sous Linux : la bibliothèque standard, sans les paquets de l'environnement virtuel.

    Hors d'un environnement virtuel, `sys.executable` est l'interpréteur lui-même. Dans un environnement virtuel
    dont l'interpréteur de base est introuvable, `RuntimeError` : se replier sur le lanceur ferait tourner les
    programmes hors du Job, ou les ferait tous échouer sans le dire.
    """
    base = getattr(sys, "_base_executable", None)
    if base and os.path.isfile(base):
        return base
    if sys.prefix == sys.base_prefix:
        return sys.executable
    raise RuntimeError(
        f"L'interpréteur Python de base de cet environnement virtuel est introuvable ({base!r}) : les programmes "
        f"ne peuvent pas être exécutés dans leurs limites, et {sys.executable} n'est qu'un lanceur. Recrée "
        "l'environnement (uv sync), ou réinstalle le Python qu'il utilise (uv python install)."
    )


def _environnement(dossier: Path, interpreteur: str) -> dict[str, str]:
    """L'environnement réduit du programme : rien de l'environnement de la forge, sauf `SYSTEMROOT` sous Windows.

    `PYTHONIOENCODING` ne sert pas à l'amorce (`-I` ignore les variables `PYTHON*`, d'où `-X utf8`), mais aux
    interpréteurs que le programme lancerait sans `-I` (sous Linux : sous Windows, il ne peut pas en lancer).
    """
    environnement = {
        "PATH": os.path.dirname(interpreteur),
        "TEMP": str(dossier),
        "TMP": str(dossier),
        "PYTHONIOENCODING": "utf-8",
    }
    racine = os.environ.get("SYSTEMROOT")
    if racine:  # sans elle, Python ne démarre pas sous Windows
        environnement["SYSTEMROOT"] = racine
    return environnement


def _lancer(
    interpreteur: str, fichier: Path, dossier: Path, delai: float, memoire_mo: int, sortie_max: int
) -> ResultatExecution:
    """Lance l'amorce sur `fichier`, la range dans ses limites, donne le départ, attend la fin ou le délai."""
    commande = [
        interpreteur, "-I", "-X", "utf8", "-c", _AMORCE,
        str(fichier), str(memoire_mo * 1024 * 1024), str(math.ceil(delai) + 1),
    ]
    if sys.platform == "win32":
        options = {"creationflags": subprocess.CREATE_NO_WINDOW}
    else:
        options = {"start_new_session": True}
    debut = time.monotonic()
    try:
        processus = subprocess.Popen(
            commande,
            cwd=dossier,
            env=_environnement(dossier, interpreteur),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **options,
        )
    except OSError as erreur:
        return ResultatExecution(
            False,
            "erreur_systeme",
            f"Le programme n'a pas pu être lancé ({interpreteur}) : {erreur}. "
            "Vérifie que l'interpréteur Python existe.",
            time.monotonic() - debut,
        )

    job = None
    lecteur = None
    trop_long = False
    try:
        if sys.platform == "win32":
            try:
                job = _JobWindows(processus.pid, memoire_mo)
            except OSError as erreur:
                return ResultatExecution(
                    False,
                    "erreur_systeme",
                    f"Le programme n'a pas pu être rangé dans un objet Job ({erreur}) : il n'a pas été lancé. "
                    "Un programme qui limite déjà ses processus (un autre Job sans imbrication) peut l'empêcher.",
                    time.monotonic() - debut,
                )
        morceaux: list[bytes] = []
        lecteur = threading.Thread(
            target=_lire, args=(processus.stdout, _OCTETS_PAR_CARACTERE * sortie_max + 4, morceaux), daemon=True
        )
        lecteur.start()
        _donner_le_depart(processus)
        depart = time.monotonic()
        if job is not None:
            try:
                processus.wait(timeout=delai)
            except subprocess.TimeoutExpired:
                trop_long = True
                _arreter(processus, job)
        else:
            trop_long = _attendre(processus, delai)
            _tuer_le_groupe(processus.pid)  # au délai, et les processus qu'il a laissés derrière lui
            _attendre_la_fin(processus)
        secondes = time.monotonic() - depart
    finally:
        if processus.poll() is None:  # une exception (Ctrl+C…) pendant l'attente : rien ne reste derrière
            _arreter(processus, job)
        if job is not None:
            job.fermer()
        if lecteur is None:  # le programme n'a pas reçu son départ
            processus.stdin.close()
            processus.stdout.close()

    # Le tuyau se ferme quand le dernier processus qui l'avait meurt. Sous Linux, un processus sorti du groupe
    # peut le garder ouvert : on n'attend pas plus d'une seconde, et on garde ce qui a été lu.
    lecteur.join(timeout=1.0)
    texte = b"".join(morceaux).decode("utf-8", errors="replace").replace("\r\n", "\n")[:sortie_max]
    code = processus.returncode
    if trop_long or (sys.platform != "win32" and code == -signal.SIGXCPU):
        raison: Raison = "delai"
    elif code == 0:
        raison = "reussi"
    elif code == _CODE_MEMOIRE:
        raison = "memoire"
    elif code == _CODE_SANS_DEPART:
        raison = "erreur_systeme"
        texte = "L'amorce n'a pas reçu son octet de départ : le programme n'a pas été exécuté."[:sortie_max]
    else:
        raison = "echec"
    return ResultatExecution(raison == "reussi", raison, texte, secondes)


def _donner_le_depart(processus: subprocess.Popen) -> None:
    """Envoie l'octet de départ à l'amorce, puis ferme son entrée standard."""
    try:
        processus.stdin.write(_DEPART)
        processus.stdin.close()
    except OSError:
        pass  # l'amorce est déjà morte : son code de sortie le dira


def _arreter(processus: subprocess.Popen, job: "_JobWindows | None") -> None:
    """Arrête le programme et ce qu'il a lancé (le Job sous Windows, le groupe ailleurs), puis attend sa fin."""
    if job is not None:
        if not job.terminer():
            processus.kill()  # TerminateJobObject a échoué : au moins le programme lui-même
    elif sys.platform != "win32":
        _tuer_le_groupe(processus.pid)
    else:
        processus.kill()
    _attendre_la_fin(processus)


def _attendre_la_fin(processus: subprocess.Popen) -> None:
    """Attend la fin d'un programme arrêté (ou déjà fini), au plus `_ATTENTE_APRES_ARRET` secondes.

    L'attente est bornée : un programme qui ne mourrait pas ne bloque pas la forge (son code reste alors `None`,
    compté comme un échec, ou comme un délai s'il a été arrêté au délai).
    """
    try:
        processus.wait(timeout=_ATTENTE_APRES_ARRET)
    except subprocess.TimeoutExpired:
        pass


def _lire(flux, octets_max: int, morceaux: list[bytes]) -> None:
    """Lit `flux` jusqu'à sa fin, en garde les `octets_max` premiers octets dans `morceaux`, et jette le reste."""
    gardes = 0
    try:
        while morceau := flux.read1(65536):
            if gardes < octets_max:
                morceau = morceau[: octets_max - gardes]
                morceaux.append(morceau)
                gardes += len(morceau)
    finally:
        flux.close()


def _attendre(processus: subprocess.Popen, delai: float) -> bool:
    """Attend la fin du programme (hors Windows), au plus `delai` secondes ; vrai si le délai est dépassé.

    Sous Linux, sans le ramasser (`os.waitid` avec `WNOWAIT`) : un processus fini mais pas encore ramassé garde son
    numéro, et `os.killpg` vise alors à coup certain son groupe, jamais celui d'un autre programme qui aurait reçu
    le même numéro. CPython n'a pas `os.waitid` sous macOS : on y attend par `wait`, qui ramasse le processus, et
    le groupe est tué juste après (un autre programme pourrait, en théorie, avoir reçu son numéro entre-temps).
    """
    if not hasattr(os, "waitid"):
        try:
            processus.wait(timeout=delai)
        except subprocess.TimeoutExpired:
            return True
        return False
    fin = time.monotonic() + delai
    while os.waitid(os.P_PID, processus.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is None:
        if time.monotonic() >= fin:
            return True
        time.sleep(0.01)
    return False


def _tuer_le_groupe(pid: int) -> None:
    """Tue tout le groupe de processus du programme (Linux et autres Unix), s'il en reste."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _effacer(dossier: Path) -> None:
    """Efface le dossier jetable. Ne lève jamais d'`OSError` : le résultat du programme passe avant.

    Ce que le programme a mis en lecture seule est rendu inscriptible, et aussi le dossier qui le contient : sous
    Linux, c'est un dossier sans droit d'écriture qui empêche d'effacer ce qu'il contient. Un fichier tenu ouvert
    un instant par un autre programme (un antivirus, un indexeur, sous Windows) : on réessaie après une courte
    pause, `len(_PAUSES_D_EFFACEMENT) + 1` passes en tout ; chaque passe efface tout ce qu'elle peut. Si le dossier
    reste, un avertissement `DossierJetableNonEfface` le nomme : un `executer_tous` ne s'arrête pas pour autant.
    """
    # La première erreur d'une passe : celle qui bloque (les suivantes, « dossier non vide », en découlent).
    cause: OSError | None = None

    def rendre_inscriptible(fonction, chemin, erreur):
        nonlocal cause
        for cible in (os.path.dirname(chemin), chemin):
            try:
                os.chmod(cible, stat.S_IRWXU)
            except OSError:
                pass
        # Un effacement refusé est retenté tout de suite ; un dossier qu'on n'a pas pu ouvrir le sera à la passe
        # suivante. Une erreur qui reste n'arrête pas la passe : elle efface tout le reste.
        if fonction in (os.unlink, os.remove, os.rmdir):
            try:
                fonction(chemin)
                return
            except OSError as encore:
                erreur = encore
        if cause is None:
            cause = erreur

    for pause in (*_PAUSES_D_EFFACEMENT, None):
        cause = None
        try:
            shutil.rmtree(dossier, onexc=rendre_inscriptible)
        except OSError as erreur:
            cause = cause or erreur
        if not os.path.lexists(dossier):
            return
        if pause is not None:
            time.sleep(pause)
    warnings.warn(
        f"Le dossier jetable {dossier} n'a pas pu être effacé ({cause}) : il reste sous TEMP. "
        "Efface-le à la main quand plus aucun programme ne s'en sert.",
        DossierJetableNonEfface,
        stacklevel=3,
    )


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    _JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9  # la classe d'information de SetInformationJobObject
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_SET_QUOTA = 0x0100

    class _LimitesDeBase(ctypes.Structure):
        """JOBOBJECT_BASIC_LIMIT_INFORMATION."""

        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _CompteursEntreesSorties(ctypes.Structure):
        """IO_COUNTERS."""

        _fields_ = [
            (nom, ctypes.c_uint64)
            for nom in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )
        ]

    class _LimitesEtendues(ctypes.Structure):
        """JOBOBJECT_EXTENDED_LIMIT_INFORMATION."""

        _fields_ = [
            ("BasicLimitInformation", _LimitesDeBase),
            ("IoInfo", _CompteursEntreesSorties),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    # Une instance à part de kernel32 : ses prototypes ne touchent pas `ctypes.windll.kernel32`, partagé.
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL

    def _erreur_windows(fonction: str) -> OSError:
        code = ctypes.get_last_error()
        return OSError(code, f"{fonction} a échoué : {ctypes.FormatError(code).strip()}")

    class _JobWindows:
        """Un objet Job qui contient le processus `pid` : mémoire bornée, un seul processus, tué à la fermeture."""

        def __init__(self, pid: int, memoire_mo: int):
            self._poignee = _kernel32.CreateJobObjectW(None, None)
            if not self._poignee:
                raise _erreur_windows("CreateJobObjectW")
            try:
                limites = _LimitesEtendues()
                limites.BasicLimitInformation.LimitFlags = (
                    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    | _JOB_OBJECT_LIMIT_PROCESS_MEMORY
                    | _JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                )
                limites.BasicLimitInformation.ActiveProcessLimit = 1
                limites.ProcessMemoryLimit = memoire_mo * 1024 * 1024
                if not _kernel32.SetInformationJobObject(
                    self._poignee, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limites), ctypes.sizeof(limites)
                ):
                    raise _erreur_windows("SetInformationJobObject")
                # Le processus attend son octet de départ, et `Popen` garde une poignée sur lui : son numéro ne
                # peut pas avoir été redonné à un autre.
                processus = _kernel32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
                if not processus:
                    raise _erreur_windows("OpenProcess")
                try:
                    if not _kernel32.AssignProcessToJobObject(self._poignee, processus):
                        raise _erreur_windows("AssignProcessToJobObject")
                finally:
                    _kernel32.CloseHandle(processus)
            except BaseException:  # une erreur, ou Ctrl+C pendant la création : la poignée ne fuit pas
                self.fermer()
                raise

        def terminer(self) -> bool:
            """Tue tous les processus du Job (au délai) ; faux si Windows a refusé."""
            return bool(self._poignee) and bool(_kernel32.TerminateJobObject(self._poignee, 1))

        def fermer(self) -> None:
            """Ferme le Job : ce qui y tourne encore est tué (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`)."""
            if self._poignee:
                _kernel32.CloseHandle(self._poignee)
                self._poignee = None
