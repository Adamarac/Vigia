"""Leitor por retângulo: lê os pixels do retângulo exato da região, em memória.

Usado só quando a amostragem por pontos não basta. O buffer vive dentro de `ler`
e é descartado ao sair; devolve no máximo `max_pontos` cores espalhadas pela área.
"""

from __future__ import annotations

import math
from typing import Protocol

from vigia.dominio.amostra import Amostra
from vigia.dominio.cor import Cor
from vigia.dominio.geometria import Retangulo
from vigia.leitura.base import ErroLeitura


class CapturadorDeRetangulo(Protocol):
    def capturar(self, rect: Retangulo) -> tuple[int, int, bytes]:
        """Devolve (largura, altura, pixels BGRA) do retângulo pedido."""
        ...


class LeitorRetangulo:
    def __init__(
        self, max_pontos: int = 2000, capturador: CapturadorDeRetangulo | None = None
    ) -> None:
        if max_pontos < 1:
            raise ValueError("max_pontos deve ser pelo menos 1")
        self._max_pontos = max_pontos
        self._capturador: CapturadorDeRetangulo = (
            capturador if capturador is not None else _CapturadorMss()
        )

    def ler(self, rect: Retangulo) -> Amostra:
        try:
            largura, altura, pixels = self._capturador.capturar(rect)
        except Exception as erro:
            raise ErroLeitura(f"falha ao ler o retângulo {rect}: {erro}") from erro
        if largura < 1 or altura < 1 or len(pixels) < largura * altura * 4:
            raise ErroLeitura(f"retângulo {rect} veio vazio ou truncado")
        passo = max(1, math.ceil(math.sqrt(largura * altura / self._max_pontos)))
        cores = []
        for y in range(0, altura, passo):
            base_linha = y * largura * 4
            for x in range(0, largura, passo):
                i = base_linha + x * 4
                cores.append(Cor(pixels[i + 2], pixels[i + 1], pixels[i]))
        return Amostra(tuple(cores))


class _CapturadorMss:
    def capturar(self, rect: Retangulo) -> tuple[int, int, bytes]:
        import mss

        with mss.mss() as tela:
            recorte = tela.grab(
                {"left": rect.x, "top": rect.y, "width": rect.largura, "height": rect.altura}
            )
            return recorte.width, recorte.height, bytes(recorte.raw)
