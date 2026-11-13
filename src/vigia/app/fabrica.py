"""Raiz de composição: monta o monitor e o notificador a partir da configuração."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from vigia.app.monitor import Monitor, Relogio
from vigia.config.modelos import Config
from vigia.dominio.classificacao import ClassificadorPorCobertura
from vigia.dominio.mensagem import PoliticaDeNotificacao
from vigia.leitura.fabrica import Leitores, leitores_padrao
from vigia.notificacao.base import Notificador
from vigia.notificacao.console import NotificadorConsole
from vigia.notificacao.telegram import NotificadorTelegram

log = logging.getLogger(__name__)


def construir_notificador(config: Config, ambiente: Mapping[str, str] | None = None) -> Notificador:
    """Telegram quando há seção e token; senão console, avisando o motivo."""
    ambiente = os.environ if ambiente is None else ambiente
    if config.telegram is None:
        log.warning("sem [notificador.telegram] no config: mensagens vão só para o console")
        return NotificadorConsole()
    token = ambiente.get(config.telegram.token_env, "").strip()
    if not token:
        log.warning("variável %s vazia: mensagens vão só para o console", config.telegram.token_env)
        return NotificadorConsole()
    return NotificadorTelegram(token, config.telegram.chat_id)


def construir_monitor(
    config: Config,
    notificador: Notificador,
    leitores: Leitores | None = None,
    relogio: Relogio | None = None,
) -> Monitor:
    politica = PoliticaDeNotificacao(
        config.mensagem_padrao, config.geral.estado_desconhecido_notifica
    )
    argumentos = {} if relogio is None else {"relogio": relogio}
    return Monitor(
        regioes=config.regioes,
        leitores=leitores or leitores_padrao(config.leitura.modo, config.leitura.grade),
        classificador=ClassificadorPorCobertura(),
        notificador=notificador,
        politica=politica,
        debounce_amostras=config.geral.debounce_amostras,
        cooldown_s=config.geral.cooldown_s,
        **argumentos,
    )
