"""Envio de notificações. Só texto sai daqui."""

from vigia.notificacao.base import ErroNotificacao, Notificador
from vigia.notificacao.composto import NotificadorComposto
from vigia.notificacao.console import NotificadorConsole, NotificadorNulo
from vigia.notificacao.telegram import NotificadorTelegram

__all__ = [
    "ErroNotificacao",
    "Notificador",
    "NotificadorComposto",
    "NotificadorConsole",
    "NotificadorNulo",
    "NotificadorTelegram",
]
