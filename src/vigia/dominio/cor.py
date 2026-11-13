"""Cor RGB como objeto de valor: conversões, distância e agrupamento."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Cor:
    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for nome, valor in (("r", self.r), ("g", self.g), ("b", self.b)):
            if not 0 <= valor <= 255:
                raise ValueError(f"componente {nome}={valor} fora da faixa 0..255")

    @classmethod
    def de_hex(cls, texto: str) -> Cor:
        """Aceita '#RRGGBB' ou 'RRGGBB'."""
        limpo = texto.strip().lstrip("#")
        if len(limpo) != 6:
            raise ValueError(f"cor '{texto}' inválida; use o formato #RRGGBB")
        try:
            numero = int(limpo, 16)
        except ValueError as erro:
            raise ValueError(f"cor '{texto}' inválida; use o formato #RRGGBB") from erro
        return cls((numero >> 16) & 0xFF, (numero >> 8) & 0xFF, numero & 0xFF)

    @classmethod
    def de_colorref(cls, valor: int) -> Cor:
        """Converte um COLORREF do Windows, cujo layout é 0x00BBGGRR."""
        return cls(valor & 0xFF, (valor >> 8) & 0xFF, (valor >> 16) & 0xFF)

    @classmethod
    def media(cls, cores: Sequence[Cor]) -> Cor:
        if not cores:
            raise ValueError("não há cores para tirar a média")
        n = len(cores)
        return cls(
            round(sum(c.r for c in cores) / n),
            round(sum(c.g for c in cores) / n),
            round(sum(c.b for c in cores) / n),
        )

    @property
    def hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def eh_preta(self) -> bool:
        return self.r == 0 and self.g == 0 and self.b == 0

    def distancia(self, outra: Cor) -> float:
        """Distância euclidiana no espaço RGB, de 0 a aproximadamente 441."""
        return math.sqrt(
            (self.r - outra.r) ** 2 + (self.g - outra.g) ** 2 + (self.b - outra.b) ** 2
        )

    def quantizada(self, passo: int = 32) -> Cor:
        """Arredonda cada componente para o início da sua faixa, para agrupar cores parecidas."""
        if passo < 1:
            raise ValueError("passo de quantização deve ser pelo menos 1")
        return Cor(
            (self.r // passo) * passo,
            (self.g // passo) * passo,
            (self.b // passo) * passo,
        )

    def __str__(self) -> str:
        return self.hex
