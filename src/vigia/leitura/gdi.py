"""Leitor por amostragem: lê uma grade de pontos com GetPixel do GDI.

Não existe bitmap em nenhum momento. Cada chamada devolve um único valor de cor.
"""

from __future__ import annotations

from typing import Protocol

from vigia.dominio.amostra import Amostra
from vigia.dominio.cor import Cor
from vigia.dominio.geometria import Retangulo
from vigia.leitura.base import ErroLeitura

CLR_INVALID = 0xFFFFFFFF


class ApiGdi(Protocol):
    """Fatia mínima do GDI usada pelo leitor; injetável para testes."""

    def get_dc(self) -> int: ...
    def release_dc(self, hdc: int) -> None: ...
    def get_pixel(self, hdc: int, x: int, y: int) -> int: ...


class LeitorGDI:
    def __init__(self, grade: tuple[int, int] = (5, 5), api: ApiGdi | None = None) -> None:
        colunas, linhas = grade
        if colunas < 1 or linhas < 1:
            raise ValueError("grade precisa de pelo menos 1×1")
        self._colunas = colunas
        self._linhas = linhas
        self._api: ApiGdi = api if api is not None else _ApiGdiWindows()

    def ler(self, rect: Retangulo) -> Amostra:
        hdc = self._api.get_dc()
        if not hdc:
            raise ErroLeitura("GetDC falhou: sem contexto gráfico da tela")
        try:
            cores = tuple(
                self._ler_ponto(hdc, x, y)
                for x, y in rect.pontos_grade(self._colunas, self._linhas)
            )
        finally:
            self._api.release_dc(hdc)
        return Amostra(cores)

    def _ler_ponto(self, hdc: int, x: int, y: int) -> Cor:
        valor = self._api.get_pixel(hdc, x, y)
        if valor == CLR_INVALID:
            raise ErroLeitura(f"ponto ({x},{y}) fora da tela")
        return Cor.de_colorref(valor)


class _ApiGdiWindows:
    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32
        self._user32.GetDC.argtypes = [wintypes.HWND]
        self._user32.GetDC.restype = wintypes.HDC
        self._user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        self._user32.ReleaseDC.restype = ctypes.c_int
        self._gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        self._gdi32.GetPixel.restype = ctypes.c_uint32

    def get_dc(self) -> int:
        return self._user32.GetDC(None) or 0

    def release_dc(self, hdc: int) -> None:
        self._user32.ReleaseDC(None, hdc)

    def get_pixel(self, hdc: int, x: int, y: int) -> int:
        return self._gdi32.GetPixel(hdc, x, y)
