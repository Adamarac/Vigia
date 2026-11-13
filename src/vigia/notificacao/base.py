"""Contrato dos notificadores."""

from __future__ import annotations

from typing import Protocol


class ErroNotificacao(RuntimeError):
    """A mensagem não pôde ser entregue."""


class Notificador(Protocol):
    def enviar(self, texto: str) -> None:
        """Entrega o texto. Levanta ErroNotificacao se não conseguir."""
        ...
