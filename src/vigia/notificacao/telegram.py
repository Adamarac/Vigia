"""Envio pela Bot API do Telegram, com repetição em falhas transitórias."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

import requests

from vigia.notificacao.base import ErroNotificacao


class Resposta(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class SessaoHttp(Protocol):
    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> Resposta: ...


class NotificadorTelegram:
    URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(
        self,
        token: str,
        chat_id: str,
        sessao: SessaoHttp | None = None,
        tentativas: int = 3,
        timeout_s: float = 10.0,
        espera_s: float = 2.0,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token.strip():
            raise ValueError("token do bot vazio")
        if not str(chat_id).strip():
            raise ValueError("chat_id vazio")
        if tentativas < 1:
            raise ValueError("tentativas deve ser pelo menos 1")
        self._token = token.strip()
        self._chat_id = str(chat_id).strip()
        self._sessao: SessaoHttp = sessao if sessao is not None else requests.Session()
        self._tentativas = tentativas
        self._timeout_s = timeout_s
        self._espera_s = espera_s
        self._dormir = dormir

    def __str__(self) -> str:
        return f"Telegram (chat {self._chat_id})"

    def enviar(self, texto: str) -> None:
        url = self.URL.format(token=self._token)
        corpo = {"chat_id": self._chat_id, "text": texto}
        ultimo_erro: ErroNotificacao | None = None
        for tentativa in range(1, self._tentativas + 1):
            try:
                resposta = self._sessao.post(url, json=corpo, timeout=self._timeout_s)
            except requests.RequestException as erro:
                ultimo_erro = ErroNotificacao(f"rede: {self._sem_token(str(erro))}")
            else:
                if self._aceita(resposta):
                    return
                ultimo_erro = ErroNotificacao(
                    f"Telegram respondeu {resposta.status_code}: {self._sem_token(resposta.text)}"
                )
                if self._erro_definitivo(resposta.status_code):
                    break
            if tentativa < self._tentativas:
                self._dormir(self._espera_s * tentativa)
        assert ultimo_erro is not None
        raise ultimo_erro

    @staticmethod
    def _aceita(resposta: Resposta) -> bool:
        if resposta.status_code != 200:
            return False
        try:
            return bool(resposta.json().get("ok"))
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _erro_definitivo(status: int) -> bool:
        """4xx é erro de configuração (token, chat_id), exceto 429 que é limite de taxa."""
        return 400 <= status < 500 and status != 429

    def _sem_token(self, texto: str) -> str:
        return texto.replace(self._token, "***")
