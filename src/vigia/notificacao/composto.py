"""Entrega a mesma mensagem a vários notificadores."""

from __future__ import annotations

from collections.abc import Sequence

from vigia.notificacao.base import ErroNotificacao, Notificador


class NotificadorComposto:
    def __init__(self, notificadores: Sequence[Notificador]) -> None:
        if not notificadores:
            raise ValueError("lista de notificadores vazia")
        self._notificadores = tuple(notificadores)

    def __str__(self) -> str:
        return " + ".join(str(n) for n in self._notificadores)

    def enviar(self, texto: str) -> None:
        falhas: list[str] = []
        for notificador in self._notificadores:
            try:
                notificador.enviar(texto)
            except ErroNotificacao as erro:
                falhas.append(f"{type(notificador).__name__}: {erro}")
        if falhas:
            raise ErroNotificacao("; ".join(falhas))
