"""Notificadores simples: console (para testes manuais) e nulo (descarta)."""

from __future__ import annotations

from collections.abc import Callable


class NotificadorConsole:
    def __init__(self, saida: Callable[[str], None] = print) -> None:
        self._saida = saida

    def __str__(self) -> str:
        return "console (Telegram não configurado)"

    def enviar(self, texto: str) -> None:
        self._saida(f"[notificação] {texto}")


class NotificadorNulo:
    def __str__(self) -> str:
        return "nenhum"

    def enviar(self, texto: str) -> None:
        return None
