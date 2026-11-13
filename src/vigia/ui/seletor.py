"""Overlay para marcar uma região com o mouse."""

from __future__ import annotations

import tkinter as tk

from vigia.dominio.geometria import Ponto, Retangulo
from vigia.leitura.tela import tela_virtual


class SeletorDeRegiao:
    """Overlay translúcido sobre toda a tela virtual.

    Arraste com o mouse para marcar o retângulo; soltar o botão confirma; Esc cancela.
    Devolve o retângulo em pixels físicos absolutos, ou None se cancelado.
    """

    TAMANHO_MINIMO = 3

    def __init__(self, mestre: tk.Misc, tela: Retangulo | None = None, alpha: float = 0.35) -> None:
        self._mestre = mestre
        self._tela = tela or tela_virtual()
        self._alpha = alpha
        self._inicio: Ponto | None = None
        self._marca: int | None = None
        self._resultado: Retangulo | None = None

    def selecionar(self) -> Retangulo | None:
        self._inicio = None
        self._marca = None
        self._resultado = None

        janela = tk.Toplevel(self._mestre)
        janela.overrideredirect(True)
        janela.attributes("-topmost", True)
        janela.attributes("-alpha", self._alpha)
        janela.geometry(f"{self._tela.largura}x{self._tela.altura}+{self._tela.x}+{self._tela.y}")
        janela.configure(bg="black")

        canvas = tk.Canvas(janela, bg="black", cursor="crosshair", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            24,
            24,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 14),
            text="Arraste para marcar a região · solte para confirmar · Esc cancela",
        )
        canvas.bind("<ButtonPress-1>", lambda evento: self._comecar(canvas, evento))
        canvas.bind("<B1-Motion>", lambda evento: self._arrastar(canvas, evento))
        canvas.bind("<ButtonRelease-1>", lambda evento: self._terminar(janela, evento))
        janela.bind("<Escape>", lambda _evento: janela.destroy())
        janela.focus_force()

        self._mestre.wait_window(janela)
        return self._resultado

    def _comecar(self, canvas: tk.Canvas, evento: tk.Event) -> None:
        self._inicio = (evento.x, evento.y)
        if self._marca is not None:
            canvas.delete(self._marca)
        self._marca = canvas.create_rectangle(
            evento.x, evento.y, evento.x, evento.y, outline="#FFD60A", width=2
        )

    def _arrastar(self, canvas: tk.Canvas, evento: tk.Event) -> None:
        if self._inicio is None or self._marca is None:
            return
        canvas.coords(self._marca, self._inicio[0], self._inicio[1], evento.x, evento.y)

    def _terminar(self, janela: tk.Toplevel, evento: tk.Event) -> None:
        if self._inicio is None:
            return
        x1, y1 = self._inicio
        if abs(evento.x - x1) < self.TAMANHO_MINIMO or abs(evento.y - y1) < self.TAMANHO_MINIMO:
            self._inicio = None
            return
        self._resultado = Retangulo.de_cantos(
            x1 + self._tela.x, y1 + self._tela.y, evento.x + self._tela.x, evento.y + self._tela.y
        )
        janela.destroy()
