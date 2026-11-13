"""Texto da notificação: qual template usar e como preenchê-lo."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from vigia.dominio.classificacao import DESCONHECIDO
from vigia.dominio.estado import Transicao
from vigia.dominio.regiao import Regiao

log = logging.getLogger(__name__)

MENSAGEM_PADRAO = "[{regiao}] {significado} ({cor_hex}) às {hora}"


class _Contexto(dict):
    """Placeholder desconhecido fica como está em vez de derrubar o ciclo."""

    def __missing__(self, chave: str) -> str:
        return "{" + chave + "}"


def contexto_de(transicao: Transicao) -> dict[str, str]:
    classificacao = transicao.classificacao
    return {
        "regiao": transicao.regiao,
        "significado": transicao.para,
        "significado_anterior": transicao.de,
        "cor_hex": classificacao.cor_dominante.hex,
        "cobertura": f"{classificacao.cobertura:.0%}",
        "hora": transicao.instante.strftime("%H:%M:%S"),
        "data": transicao.instante.strftime("%d/%m/%Y"),
        "texto": "",
    }


class RenderizadorMensagem:
    def render(self, template: str, contexto: Mapping[str, str]) -> str:
        try:
            return template.format_map(_Contexto(contexto))
        except (ValueError, IndexError, AttributeError) as erro:
            log.warning("template inválido (%s): %r", erro, template)
            return f"{contexto.get('regiao', '?')}: {contexto.get('significado', '?')}"


class PoliticaDeNotificacao:
    """Decide se uma transição vira mensagem e com qual texto."""

    def __init__(
        self,
        mensagem_padrao: str = MENSAGEM_PADRAO,
        desconhecido_notifica: bool = False,
        renderizador: RenderizadorMensagem | None = None,
    ) -> None:
        self._padrao = mensagem_padrao
        self._desconhecido_notifica = desconhecido_notifica
        self._renderizador = renderizador or RenderizadorMensagem()

    def mensagem_para(self, regiao: Regiao, transicao: Transicao) -> str | None:
        if transicao.para == DESCONHECIDO:
            if not self._desconhecido_notifica:
                return None
            template = self._padrao
        else:
            regra = regiao.regra_por_significado(transicao.para)
            if regra is None or not regra.notificar:
                return None
            template = regra.mensagem or self._padrao
        return self._renderizador.render(template, contexto_de(transicao))
