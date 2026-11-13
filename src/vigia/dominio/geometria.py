"""Retângulos em pixels físicos absolutos da tela virtual."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

Ponto = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Retangulo:
    x: int
    y: int
    largura: int
    altura: int

    def __post_init__(self) -> None:
        if self.largura <= 0 or self.altura <= 0:
            raise ValueError(
                "retângulo precisa de largura e altura positivas, "
                f"recebeu {self.largura}×{self.altura}"
            )

    @property
    def direita(self) -> int:
        """Primeira coluna fora do retângulo."""
        return self.x + self.largura

    @property
    def inferior(self) -> int:
        """Primeira linha fora do retângulo."""
        return self.y + self.altura

    def pontos_grade(self, colunas: int, linhas: int) -> tuple[Ponto, ...]:
        """Pontos distribuídos uniformemente dentro do retângulo, afastados das bordas."""
        if colunas < 1 or linhas < 1:
            raise ValueError("grade precisa de pelo menos 1 coluna e 1 linha")
        xs = [
            self.x + min(self.largura - 1, int((i + 0.5) * self.largura / colunas))
            for i in range(colunas)
        ]
        ys = [
            self.y + min(self.altura - 1, int((j + 0.5) * self.altura / linhas))
            for j in range(linhas)
        ]
        return tuple((x, y) for y in ys for x in xs)

    def como_lista(self) -> list[int]:
        return [self.x, self.y, self.largura, self.altura]

    @classmethod
    def de_lista(cls, valores: Sequence[int]) -> Retangulo:
        if len(valores) != 4:
            raise ValueError("rect precisa de 4 inteiros: x, y, largura, altura")
        return cls(*(int(v) for v in valores))

    @classmethod
    def de_cantos(cls, x1: int, y1: int, x2: int, y2: int) -> Retangulo:
        """Constrói a partir de dois cantos opostos, em qualquer ordem."""
        return cls(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def __str__(self) -> str:
        return f"{self.x},{self.y} {self.largura}×{self.altura}"
