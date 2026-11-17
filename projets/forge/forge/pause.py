"""La pause par Ctrl+C, commune à tous les travaux longs de la forge.

L'entraînement (`forge.entrainement.boucle`) et les travaux par fragments (téléchargement des
conversations, `forge.fragments`) s'y arrêtent de la même façon : un premier Ctrl+C lève un drapeau
que le travail regarde entre deux unités (un pas, une ligne), un second arrête tout de suite.
"""

import signal
import threading


class Pause:
    """Pendant l'entraînement, Ctrl+C (et Ctrl+Pause sous Windows) demande une pause.

    Le premier appui lève seulement un drapeau, que la boucle regarde à la fin de chaque pas.
    Un second appui arrête tout de suite (`KeyboardInterrupt`) : le pas en cours est perdu,
    mais la dernière sauvegarde complète reste bonne.

    SIGTERM, là où il existe, fait de même : c'est ce qu'envoient l'arrêt du système (Linux),
    `docker stop` ou `timeout`. Ils laissent en général le temps (90 s pour systemd, 10 s pour
    `docker stop`, réglable) de finir le pas et de sauvegarder, au lieu de perdre jusqu'à
    `sauvegarde_minutes` de calcul.

    `en_cours` et `sauvegarde` ne changent que les mots du message : les travaux par fragments
    (téléchargement, traduction…) y disent « le fragment en cours » et « je valide ce fragment ».
    Leurs valeurs par défaut sont celles de l'entraînement.
    """

    def __init__(self, en_cours: str = "le pas en cours", sauvegarde: str = "je sauvegarde") -> None:
        self.demandee = False
        self._en_cours = en_cours
        self._sauvegarde = sauvegarde
        self._anciens: dict[int, object] = {}

    def _signal_recu(self, numero, cadre) -> None:
        if self.demandee:
            raise KeyboardInterrupt
        self.demandee = True
        if numero == getattr(signal, "SIGTERM", None):
            message = (
                f"\nArrêt demandé par le système (SIGTERM) : je finis {self._en_cours}, {self._sauvegarde}, "
                "puis je m'arrête."
            )
        else:
            message = (
                f"\nPause demandée : je finis {self._en_cours}, {self._sauvegarde}, puis je m'arrête "
                "(Ctrl+C une seconde fois : arrêt immédiat, sans sauvegarder ce pas)."
            )
        try:
            print(message, flush=True)
        except (OSError, RuntimeError):
            pass  # l'écran était déjà occupé : le message de pause suivra quand même

    def __enter__(self) -> "Pause":
        # On ne peut poser un gestionnaire de signal que depuis le fil principal.
        if threading.current_thread() is threading.main_thread():
            for nom in ("SIGINT", "SIGBREAK", "SIGTERM"):
                numero = getattr(signal, nom, None)
                if numero is not None:
                    self._anciens[numero] = signal.signal(numero, self._signal_recu)
        return self

    def __exit__(self, *erreur) -> None:
        for numero, ancien in self._anciens.items():
            signal.signal(numero, ancien)
