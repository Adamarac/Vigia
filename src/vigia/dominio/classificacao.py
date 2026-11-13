"""Classificação de uma amostra: qual significado a região está mostrando."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from vigia.dominio.amostra import Amostra
from vigia.dominio.cor import Cor
from vigia.dominio.regiao import Regra

DESCONHECIDO = "DESCONHECIDO"


@dataclass(frozen=True, slots=True)
class Classificacao:
    significado: str
    cobertura: float
    cor_dominante: Cor
    coberturas: Mapping[str, float]
    cores_dominantes: tuple[tuple[Cor, float], ...]
    toda_preta: bool

    @property
    def desconhecido(self) -> bool:
        return self.significado == DESCONHECIDO


class Classificador(Protocol):
    def classificar(self, amostra: Amostra, regras: Sequence[Regra]) -> Classificacao: ...


class ClassificadorPorCobertura:
    """Vence a regra com maior fração de pontos dentro da sua tolerância.

    Cobertura em vez de cor média: texto escrito por cima do fundo, bordas e
    anti-aliasing não arrastam a decisão.
    """

    def classificar(self, amostra: Amostra, regras: Sequence[Regra]) -> Classificacao:
        coberturas = {regra.significado: regra.cobertura(amostra) for regra in regras}
        vencedora = max(regras, key=lambda r: coberturas[r.significado], default=None)
        if vencedora is not None and coberturas[vencedora.significado] >= vencedora.cobertura_min:
            significado = vencedora.significado
            cobertura = coberturas[vencedora.significado]
        else:
            significado = DESCONHECIDO
            cobertura = 0.0
        dominantes = amostra.cores_dominantes()
        return Classificacao(
            significado=significado,
            cobertura=cobertura,
            cor_dominante=dominantes[0][0],
            coberturas=coberturas,
            cores_dominantes=dominantes,
            toda_preta=amostra.toda_preta,
        )
