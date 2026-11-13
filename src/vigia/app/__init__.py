"""Orquestração: ciclo de leitura, execução periódica e montagem das dependências."""

from vigia.app.executor import Executor
from vigia.app.fabrica import construir_monitor, construir_notificador
from vigia.app.monitor import LeituraRegiao, Monitor

__all__ = [
    "Executor",
    "LeituraRegiao",
    "Monitor",
    "construir_monitor",
    "construir_notificador",
]
