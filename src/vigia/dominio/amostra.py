"""Amostra: o conjunto de cores lidas de uma região num instante.

É só uma lista de valores RGB. Nunca um bitmap, nunca uma imagem.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigia.dominio.cor import Cor


@dataclass(frozen=True, slots=True)
class Amostra:
    cores: tuple[Cor, ...]

    def __post_init__(self) -> None:
        if not self.cores:
            raise ValueError("amostra vazia")

    def __len__(self) -> int:
        return len(self.cores)

    @property
    def toda_preta(self) -> bool:
        """Verdadeiro quando todos os pontos são (0,0,0): janela protegida ou fora da tela."""
        return all(cor.eh_preta for cor in self.cores)

    def cores_dominantes(self, n: int = 5, passo: int = 32) -> tuple[tuple[Cor, float], ...]:
        """As `n` cores mais frequentes e a fração de pontos de cada uma.

        Cores parecidas são agrupadas por quantização; a cor devolvida é a média do grupo,
        para ficar fiel ao que está na tela e não ao início da faixa.
        """
        if n < 1:
            raise ValueError("n deve ser pelo menos 1")
        grupos: dict[Cor, list[Cor]] = {}
        for cor in self.cores:
            grupos.setdefault(cor.quantizada(passo), []).append(cor)
        maiores = sorted(grupos.values(), key=len, reverse=True)[:n]
        total = len(self.cores)
        return tuple((Cor.media(grupo), len(grupo) / total) for grupo in maiores)

    @property
    def cor_dominante(self) -> Cor:
        return self.cores_dominantes(1)[0][0]
