"""Contrato dos leitores de tela."""

from __future__ import annotations

from typing import Protocol

from vigia.dominio.amostra import Amostra
from vigia.dominio.geometria import Retangulo


class ErroLeitura(RuntimeError):
    """A região não pôde ser lida (fora da tela, sem contexto gráfico, etc.)."""


class LeitorDeTela(Protocol):
    def ler(self, rect: Retangulo) -> Amostra:
        """Devolve as cores lidas dentro do retângulo. Levanta ErroLeitura se não conseguir."""
        ...
