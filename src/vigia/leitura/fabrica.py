"""Escolha do leitor conforme o modo de cada região."""

from __future__ import annotations

from collections.abc import Mapping

from vigia.dominio.regiao import MODOS, Regiao
from vigia.leitura.base import LeitorDeTela
from vigia.leitura.gdi import LeitorGDI
from vigia.leitura.retangulo import LeitorRetangulo


class Leitores:
    def __init__(self, modo_padrao: str, por_modo: Mapping[str, LeitorDeTela]) -> None:
        if modo_padrao not in por_modo:
            raise ValueError(f"não há leitor para o modo padrão '{modo_padrao}'")
        self._modo_padrao = modo_padrao
        self._por_modo = dict(por_modo)

    def para(self, regiao: Regiao) -> LeitorDeTela:
        modo = regiao.modo or self._modo_padrao
        try:
            return self._por_modo[modo]
        except KeyError as erro:
            raise ValueError(f"região '{regiao.nome}': modo '{modo}' sem leitor") from erro


def leitores_padrao(modo_padrao: str, grade: tuple[int, int]) -> Leitores:
    if modo_padrao not in MODOS:
        raise ValueError(f"modo '{modo_padrao}' inválido; use um de {MODOS}")
    return Leitores(
        modo_padrao,
        {"amostragem": LeitorGDI(grade), "retangulo": LeitorRetangulo()},
    )
