"""Máquina de estados de uma região: debounce e cooldown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from vigia.dominio.classificacao import Classificacao


@dataclass(frozen=True, slots=True)
class Transicao:
    regiao: str
    de: str
    para: str
    classificacao: Classificacao
    instante: datetime


class MaquinaEstados:
    """Confirma um estado só depois de `debounce` leituras iguais seguidas.

    Emite uma transição quando o estado confirmado muda, exceto na primeira
    confirmação (estado inicial) e quando a mesma transição já foi emitida
    há menos de `cooldown_s`.
    """

    def __init__(self, regiao: str, debounce: int, cooldown_s: float) -> None:
        if debounce < 1:
            raise ValueError("debounce deve ser pelo menos 1")
        if cooldown_s < 0:
            raise ValueError("cooldown não pode ser negativo")
        self._regiao = regiao
        self._debounce = debounce
        self._cooldown_s = cooldown_s
        self._confirmado: str | None = None
        self._candidato: str | None = None
        self._contagem = 0
        self._ultimo_envio: dict[tuple[str, str], datetime] = {}

    @property
    def estado(self) -> str | None:
        return self._confirmado

    @property
    def candidato(self) -> str | None:
        return self._candidato

    @property
    def contagem(self) -> int:
        return self._contagem

    @property
    def debounce(self) -> int:
        return self._debounce

    def receber(self, classificacao: Classificacao, agora: datetime) -> Transicao | None:
        significado = classificacao.significado
        if significado == self._candidato:
            self._contagem += 1
        else:
            self._candidato = significado
            self._contagem = 1

        if self._contagem < self._debounce or significado == self._confirmado:
            return None

        anterior = self._confirmado
        self._confirmado = significado
        if anterior is None:
            return None

        chave = (anterior, significado)
        ultimo = self._ultimo_envio.get(chave)
        if ultimo is not None and (agora - ultimo).total_seconds() < self._cooldown_s:
            return None
        self._ultimo_envio[chave] = agora
        return Transicao(self._regiao, anterior, significado, classificacao, agora)
