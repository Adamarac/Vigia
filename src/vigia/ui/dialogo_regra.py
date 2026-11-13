"""Diálogo para criar uma regra a partir das cores lidas agora na região."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import messagebox, simpledialog, ttk

from vigia.dominio.cor import Cor
from vigia.dominio.regiao import Regiao, Regra

PLACEHOLDERS = "{regiao} {significado} {significado_anterior} {cor_hex} {cobertura} {hora} {data}"


class DialogoRegra(simpledialog.Dialog):
    def __init__(self, mestre: tk.Misc, regiao: Regiao, cores: Sequence[tuple[Cor, float]]) -> None:
        self._regiao = regiao
        self._cores = tuple(cores)
        self._regra: Regra | None = None
        self.resultado: Regra | None = None
        super().__init__(mestre, title=f"Nova regra · {regiao.nome}")

    def body(self, master: tk.Frame) -> tk.Widget:
        linha = 0
        ttk.Label(master, text="Cores lidas agora nesta região:").grid(
            row=linha, column=0, columnspan=3, sticky="w"
        )
        linha += 1
        self._cor_var = tk.StringVar(value=self._cores[0][0].hex if self._cores else "")
        for cor, fracao in self._cores:
            tk.Label(master, bg=cor.hex, width=3, relief="solid", bd=1).grid(
                row=linha, column=0, padx=(0, 6), pady=1, sticky="w"
            )
            ttk.Radiobutton(
                master,
                text=f"{cor.hex}  ({fracao:.0%} dos pontos)",
                value=cor.hex,
                variable=self._cor_var,
            ).grid(row=linha, column=1, columnspan=2, sticky="w")
            linha += 1
        if not self._cores:
            ttk.Label(master, text="(nenhuma leitura ainda: digite a cor em hex)").grid(
                row=linha, column=0, columnspan=3, sticky="w"
            )
            linha += 1

        self._campo(master, linha, "Cor (hex):", variavel=self._cor_var)
        self._significado = self._campo(master, linha + 1, "Significado:")
        self._mensagem = self._campo(master, linha + 2, "Mensagem (opcional):", largura=48)
        self._tolerancia = self._campo(master, linha + 3, "Tolerância (0 a 441):", valor="40")
        self._cobertura = self._campo(master, linha + 4, "Cobertura mínima (%):", valor="50")
        linha += 5

        self._notificar = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            master, text="Notificar quando este estado for confirmado", variable=self._notificar
        ).grid(row=linha, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(master, text=f"Placeholders: {PLACEHOLDERS}", foreground="#666666").grid(
            row=linha + 1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )
        return self._significado

    @staticmethod
    def _campo(
        master: tk.Frame,
        linha: int,
        rotulo: str,
        valor: str = "",
        largura: int = 24,
        variavel: tk.StringVar | None = None,
    ) -> ttk.Entry:
        ttk.Label(master, text=rotulo).grid(
            row=linha, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        entrada = ttk.Entry(master, width=largura, textvariable=variavel)
        if valor and variavel is None:
            entrada.insert(0, valor)
        entrada.grid(row=linha, column=2, sticky="we", pady=(6, 0))
        return entrada

    def validate(self) -> bool:
        try:
            regra = self._montar()
        except ValueError as erro:
            messagebox.showerror("Regra inválida", str(erro), parent=self)
            return False
        if self._regiao.regra_por_significado(regra.significado) is not None:
            messagebox.showerror(
                "Regra inválida",
                f"Já existe a regra '{regra.significado}' nesta região.",
                parent=self,
            )
            return False
        self._regra = regra
        return True

    def _montar(self) -> Regra:
        try:
            tolerancia = float(self._tolerancia.get().replace(",", "."))
            cobertura = float(self._cobertura.get().replace(",", ".")) / 100
        except ValueError as erro:
            raise ValueError("tolerância e cobertura mínima devem ser números") from erro
        return Regra(
            cor=Cor.de_hex(self._cor_var.get()),
            significado=self._significado.get().strip(),
            tolerancia=tolerancia,
            cobertura_min=cobertura,
            mensagem=self._mensagem.get().strip() or None,
            notificar=self._notificar.get(),
        )

    def apply(self) -> None:
        self.resultado = self._regra
