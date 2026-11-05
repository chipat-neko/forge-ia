"""La mémoire d'un tenseur : combien d'octets il occupe, d'après sa forme et son type.

Un tenseur range ses nombres les uns à la suite des autres. Sa mémoire, c'est
donc le nombre de nombres (le produit des tailles de sa forme) fois la place
d'un nombre : 4 octets en float32, 2 en float16 et bfloat16, 8 en float64 et
int64, 1 en int8 et bool.
"""

import math

import torch


# region: memoire
def octets(forme: tuple[int, ...], dtype: torch.dtype) -> int:
    """Le nombre d'octets d'un tenseur de cette forme et de ce type."""
    nombres = math.prod(forme)  # (4096, 4096) : 16 777 216 nombres
    par_nombre = torch.empty((), dtype=dtype).element_size()  # float32 : 4 octets
    return nombres * par_nombre
# fin: memoire
