"""Mostra na tela onde está cada região configurada, com número e nome."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence

from vigia.dominio.geometria import Retangulo
from vigia.dominio.regiao import Regiao
from vigia.leitura.tela import tela_virtual


class DestaqueDeRegioes:
    """Desenha o contorno e o rótulo de cada região por cima da tela, por alguns segundos.

    Usa cor-chave transparente: só as linhas e os rótulos ficam visíveis. Quem chama
    deve pausar o executor enquanto o destaque está aberto, porque o contorno fica
    a 2 px da borda da região e o rótulo pode cobrir regiões vizinhas.
    """

    COR_CHAVE = "#FF00FE"
    COR_CONTORNO = "#FF3B30"
    COR_ROTULO = "#FFD60A"

    def __init__(self, mestre: tk.Misc, tela: Retangulo | None = None) -> None:
        self._mestre = mestre
        self._tela = tela or tela_virtual()

    def mostrar(self, regioes: Sequence[Regiao], duracao_s: float = 5.0) -> None:
        janela = tk.Toplevel(self._mestre)
        janela.overrideredirect(True)
        janela.attributes("-topmost", True)
        janela.geometry(f"{self._tela.largura}x{self._tela.altura}+{self._tela.x}+{self._tela.y}")
        janela.configure(bg=self.COR_CHAVE)
        janela.attributes("-transparentcolor", self.COR_CHAVE)

        canvas = tk.Canvas(janela, bg=self.COR_CHAVE, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        for indice, regiao in enumerate(regioes, 1):
            self._desenhar(canvas, indice, regiao)
        self._rotulo(
            canvas,
            24,
            24,
            "nw",
            f"{len(regioes)} região(ões) configurada(s) · fecha em {duracao_s:.0f} s · Esc fecha",
        )

        def fechar(*_argumentos: object) -> None:
            if janela.winfo_exists():
                janela.destroy()

        janela.bind("<Escape>", fechar)
        canvas.bind("<Button-1>", fechar)
        janela.after(int(duracao_s * 1000), fechar)
        janela.focus_force()
        self._mestre.wait_window(janela)

    def _desenhar(self, canvas: tk.Canvas, indice: int, regiao: Regiao) -> None:
        rect = regiao.rect
        x1 = rect.x - self._tela.x - 2
        y1 = rect.y - self._tela.y - 2
        x2 = rect.direita - self._tela.x + 1
        y2 = rect.inferior - self._tela.y + 1
        canvas.create_rectangle(x1, y1, x2, y2, outline=self.COR_CONTORNO, width=2)
        texto = f"{indice}. {regiao.nome}"
        if y1 >= 24:
            self._rotulo(canvas, x1, y1 - 3, "sw", texto)
        else:
            self._rotulo(canvas, x1, y2 + 3, "nw", texto)

    def _rotulo(self, canvas: tk.Canvas, x: int, y: int, ancora: str, texto: str) -> None:
        id_texto = canvas.create_text(
            x, y, anchor=ancora, text=texto, font=("Segoe UI", 10, "bold"), fill="black"
        )
        bx1, by1, bx2, by2 = canvas.bbox(id_texto)
        id_fundo = canvas.create_rectangle(
            bx1 - 3, by1 - 1, bx2 + 3, by2 + 1, fill=self.COR_ROTULO, outline=""
        )
        canvas.tag_lower(id_fundo, id_texto)
