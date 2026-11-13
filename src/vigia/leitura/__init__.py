"""Leitura de pixels da tela. Só os pontos das regiões configuradas, nunca o monitor inteiro."""

from vigia.leitura.base import ErroLeitura, LeitorDeTela
from vigia.leitura.fabrica import Leitores, leitores_padrao
from vigia.leitura.gdi import LeitorGDI
from vigia.leitura.retangulo import LeitorRetangulo

__all__ = [
    "ErroLeitura",
    "LeitorDeTela",
    "LeitorGDI",
    "LeitorRetangulo",
    "Leitores",
    "leitores_padrao",
]
