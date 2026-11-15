"""Le processeur : combien de fils de calcul ce processus a le droit d'utiliser."""

import os


def fils_disponibles() -> int:
    """Le nombre de fils de calcul que ce processus peut utiliser (au moins 1).

    `os.cpu_count()` compte tous les cœurs logiques de la machine, même ceux que ce processus n'a
    pas le droit d'utiliser : son affinité (`taskset`, un conteneur réglé sur quelques cœurs…) en
    laisse parfois moins. En demander plus ferait se disputer les mêmes cœurs à plusieurs fils, et
    tout irait plus lentement. On prend donc, dans l'ordre :

    - `os.process_cpu_count()` (Python 3.13 et plus), qui tient compte de l'affinité ;
    - sinon `len(os.sched_getaffinity(0))`, là où il existe (Linux) ;
    - sinon `os.cpu_count()` (Windows avec Python 3.12).
    """
    compter = getattr(os, "process_cpu_count", None)
    if compter is not None:
        return compter() or 1
    affinite = getattr(os, "sched_getaffinity", None)
    if affinite is not None:
        try:
            return len(affinite(0)) or 1
        except OSError:
            pass
    return os.cpu_count() or 1
