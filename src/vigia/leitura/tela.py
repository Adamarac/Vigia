"""Informações da tela: DPI e geometria da tela virtual (todos os monitores)."""

from __future__ import annotations

import logging
import sys

from vigia.dominio.geometria import Retangulo

log = logging.getLogger(__name__)

_SM_XVIRTUALSCREEN = 76
_SM_YVIRTUALSCREEN = 77
_SM_CXVIRTUALSCREEN = 78
_SM_CYVIRTUALSCREEN = 79
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def ativar_dpi_awareness() -> None:
    """Faz o processo trabalhar em pixels físicos.

    Precisa ser chamado antes de criar qualquer janela ou ler a tela; senão, com
    escala de 125 % ou 150 %, as coordenadas do overlay e da leitura divergem.
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        ):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError) as erro:
        log.warning("não foi possível ativar DPI awareness: %s", erro)


def tela_virtual() -> Retangulo:
    """Retângulo que cobre todos os monitores, em pixels físicos."""
    if sys.platform != "win32":
        raise RuntimeError("tela virtual só está disponível no Windows")
    import ctypes

    metrica = ctypes.windll.user32.GetSystemMetrics
    return Retangulo(
        metrica(_SM_XVIRTUALSCREEN),
        metrica(_SM_YVIRTUALSCREEN),
        metrica(_SM_CXVIRTUALSCREEN),
        metrica(_SM_CYVIRTUALSCREEN),
    )
