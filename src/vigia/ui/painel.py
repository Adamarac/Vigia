"""Painel mínimo: mostra o que cada região está lendo e permite criar regiões e regras.

Cada linha da tabela é uma região: um quadrado com a cor lida agora, o hex, o estado
confirmado (e o candidato em debounce), a cobertura de cada regra e um diagnóstico.
O botão "Mostrar regiões na tela" desenha o contorno numerado de cada uma por cima
da tela, para conferir se o retângulo está no lugar certo.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

from vigia.app.executor import Executor
from vigia.app.monitor import LeituraRegiao, Monitor
from vigia.config.modelos import Config
from vigia.config.repositorio_toml import ErroConfig, RepositorioConfig
from vigia.dominio.regiao import Regiao
from vigia.notificacao.base import ErroNotificacao, Notificador
from vigia.ui.destaque import DestaqueDeRegioes
from vigia.ui.dialogo_regra import DialogoRegra
from vigia.ui.seletor import SeletorDeRegiao

COLUNAS = ("#", "Região", "Retângulo", "Cor", "Hex", "Estado", "Coberturas", "Hora", "Observação")


class Painel:
    INTERVALO_FILA_MS = 250

    def __init__(
        self,
        repositorio: RepositorioConfig,
        config: Config,
        monitor: Monitor,
        executor: Executor,
        notificador: Notificador,
    ) -> None:
        self._repositorio = repositorio
        self._config = config
        self._monitor = monitor
        self._executor = executor
        self._notificador = notificador
        self._leituras: queue.SimpleQueue[LeituraRegiao] = queue.SimpleQueue()
        self._avisos: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._linhas: dict[str, _LinhaRegiao] = {}
        self._dica: ttk.Label | None = None

        self._raiz = tk.Tk()
        self._raiz.title("Vigia")
        self._raiz.minsize(960, 240)
        self._montar()
        self._reconstruir_linhas()
        self._monitor.adicionar_observador(self._leituras.put)

    def executar(self) -> None:
        self._executor.iniciar()
        self._raiz.protocol("WM_DELETE_WINDOW", self._fechar)
        self._raiz.after(self.INTERVALO_FILA_MS, self._drenar_filas)
        self._raiz.mainloop()

    # --- montagem -----------------------------------------------------------

    def _montar(self) -> None:
        barra = ttk.Frame(self._raiz, padding=(8, 8, 8, 4))
        barra.pack(fill="x")
        self._botao_pausa = ttk.Button(barra, text="Pausar", command=self._alternar_pausa)
        self._botao_pausa.pack(side="left")
        for texto, comando in (
            ("Ler agora", self._ler_agora),
            ("Mostrar regiões na tela", self._mostrar_na_tela),
            ("Nova região", self._nova_regiao),
            ("Testar notificação", self._testar_notificacao),
        ):
            ttk.Button(barra, text=texto, command=comando).pack(side="left", padx=(6, 0))
        ttk.Label(barra, text=f"notificador: {self._notificador}").pack(side="right")

        self._tabela = ttk.Frame(self._raiz, padding=8)
        self._tabela.pack(fill="both", expand=True)
        for coluna, titulo in enumerate(COLUNAS):
            ttk.Label(self._tabela, text=titulo, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=coluna, sticky="w", padx=4, pady=(0, 4)
            )

        self._status = ttk.Label(self._raiz, anchor="w", padding=(8, 4))
        self._status.pack(fill="x", side="bottom")
        self._avisar("Aguardando o primeiro ciclo…")

    def _reconstruir_linhas(self) -> None:
        for linha in self._linhas.values():
            linha.destruir()
        self._linhas = {}
        if self._dica is not None:
            self._dica.destroy()
            self._dica = None
        for indice, regiao in enumerate(self._config.regioes, 1):
            self._linhas[regiao.nome] = _LinhaRegiao(
                self._tabela, indice, regiao, self._nova_regra, self._remover_regiao
            )
        if not self._config.regioes:
            self._dica = ttk.Label(
                self._tabela,
                text="Nenhuma região configurada. Clique em “Nova região” e arraste sobre a tela.",
            )
            self._dica.grid(row=1, column=0, columnspan=len(COLUNAS), sticky="w", pady=8)

    # --- ações --------------------------------------------------------------

    def _alternar_pausa(self) -> None:
        if self._executor.pausado:
            self._executor.retomar()
            self._botao_pausa.config(text="Pausar")
            self._avisar("Monitoramento retomado.")
        else:
            self._executor.pausar()
            self._botao_pausa.config(text="Retomar")
            self._avisar("Monitoramento pausado.")

    def _ler_agora(self) -> None:
        threading.Thread(
            target=self._executor.ciclo_unico, name="vigia-ler-agora", daemon=True
        ).start()

    def _mostrar_na_tela(self) -> None:
        if not self._config.regioes:
            self._avisar("Nenhuma região para mostrar.")
            return
        with self._executor.pausado_durante():
            DestaqueDeRegioes(self._raiz).mostrar(self._config.regioes)

    def _nova_regiao(self) -> None:
        with self._executor.pausado_durante():
            rect = SeletorDeRegiao(self._raiz).selecionar()
            if rect is None:
                return
            nome = simpledialog.askstring(
                "Nova região", f"Nome da região ({rect}):", parent=self._raiz
            )
        if not nome or not nome.strip():
            return
        nome = nome.strip()
        if self._config.regiao(nome) is not None:
            messagebox.showerror(
                "Vigia", f"Já existe uma região chamada '{nome}'.", parent=self._raiz
            )
            return
        self._aplicar(
            self._config.com_regiao(Regiao(nome, rect)), f"Região '{nome}' criada em {rect}."
        )

    def _nova_regra(self, nome: str) -> None:
        regiao = self._config.regiao(nome)
        if regiao is None:
            return
        ultima = self._linhas[nome].ultima
        cores = (
            ultima.classificacao.cores_dominantes
            if ultima is not None and ultima.classificacao is not None
            else ()
        )
        dialogo = DialogoRegra(self._raiz, regiao, cores)
        if dialogo.resultado is None:
            return
        self._aplicar(
            self._config.com_regiao(regiao.com_regra(dialogo.resultado)),
            f"Regra '{dialogo.resultado.significado}' adicionada a '{nome}'.",
        )

    def _remover_regiao(self, nome: str) -> None:
        if not messagebox.askyesno("Vigia", f"Remover a região '{nome}'?", parent=self._raiz):
            return
        self._aplicar(self._config.sem_regiao(nome), f"Região '{nome}' removida.")

    def _aplicar(self, config: Config, aviso: str) -> None:
        try:
            self._repositorio.salvar(config)
        except ErroConfig as erro:
            messagebox.showerror("Vigia", str(erro), parent=self._raiz)
            return
        self._config = config
        self._monitor.substituir_regioes(config.regioes)
        self._reconstruir_linhas()
        self._avisar(aviso)
        self._ler_agora()

    def _testar_notificacao(self) -> None:
        texto = f"Teste do Vigia às {datetime.now():%H:%M:%S}"

        def enviar() -> None:
            try:
                self._notificador.enviar(texto)
            except ErroNotificacao as erro:
                self._avisos.put(f"Falha no teste: {erro}")
            else:
                self._avisos.put(f"Mensagem de teste enviada via {self._notificador}.")

        threading.Thread(target=enviar, name="vigia-teste-notificacao", daemon=True).start()

    # --- atualização --------------------------------------------------------

    def _drenar_filas(self) -> None:
        ultima: LeituraRegiao | None = None
        while True:
            try:
                leitura = self._leituras.get_nowait()
            except queue.Empty:
                break
            linha = self._linhas.get(leitura.regiao.nome)
            if linha is not None:
                linha.atualizar(leitura)
                ultima = leitura
        if ultima is not None:
            situacao = "pausado" if self._executor.pausado else "monitorando"
            self._avisar(
                f"Última leitura às {ultima.instante:%H:%M:%S} · {situacao} · "
                f"{len(self._config.regioes)} região(ões)"
            )
        while True:
            try:
                self._avisar(self._avisos.get_nowait())
            except queue.Empty:
                break
        self._raiz.after(self.INTERVALO_FILA_MS, self._drenar_filas)

    def _avisar(self, texto: str) -> None:
        self._status.config(text=texto)

    def _fechar(self) -> None:
        self._executor.parar()
        self._raiz.destroy()


class _LinhaRegiao:
    """Uma linha da tabela: widgets de uma região e a última leitura dela."""

    def __init__(
        self,
        tabela: ttk.Frame,
        indice: int,
        regiao: Regiao,
        ao_criar_regra: Callable[[str], None],
        ao_remover: Callable[[str], None],
    ) -> None:
        self.regiao = regiao
        self.ultima: LeituraRegiao | None = None
        self._widgets: list[tk.Widget] = []
        linha = indice
        self._rotulo(tabela, linha, 0, str(indice))
        self._rotulo(tabela, linha, 1, regiao.nome)
        self._rotulo(tabela, linha, 2, str(regiao.rect))
        self._amostra = tk.Label(tabela, width=3, bg="#DDDDDD", relief="solid", bd=1)
        self._amostra.grid(row=linha, column=3, padx=4, pady=2)
        self._widgets.append(self._amostra)
        self._hex = self._rotulo(tabela, linha, 4, "—")
        self._estado = self._rotulo(tabela, linha, 5, "—")
        self._coberturas = self._rotulo(tabela, linha, 6, self._texto_regras(regiao))
        self._hora = self._rotulo(tabela, linha, 7, "—")
        self._obs = self._rotulo(tabela, linha, 8, "", foreground="#B00020")
        for coluna, (texto, acao) in enumerate(
            (("Regra…", ao_criar_regra), ("Remover", ao_remover)), start=len(COLUNAS)
        ):
            botao = ttk.Button(tabela, text=texto, command=lambda acao=acao: acao(regiao.nome))
            botao.grid(row=linha, column=coluna, padx=2)
            self._widgets.append(botao)

    def _rotulo(
        self, tabela: ttk.Frame, linha: int, coluna: int, texto: str, **opcoes: object
    ) -> ttk.Label:
        rotulo = ttk.Label(tabela, text=texto, **opcoes)  # type: ignore[arg-type]
        rotulo.grid(row=linha, column=coluna, sticky="w", padx=4, pady=2)
        self._widgets.append(rotulo)
        return rotulo

    @staticmethod
    def _texto_regras(regiao: Regiao) -> str:
        return " · ".join(f"{r.significado} {r.cor.hex}" for r in regiao.regras) or "sem regras"

    def atualizar(self, leitura: LeituraRegiao) -> None:
        self.ultima = leitura
        self._hora.config(text=f"{leitura.instante:%H:%M:%S}")
        classificacao = leitura.classificacao
        if classificacao is not None:
            self._amostra.config(bg=classificacao.cor_dominante.hex)
            self._hex.config(text=classificacao.cor_dominante.hex)
            self._coberturas.config(
                text=" · ".join(f"{s} {v:.0%}" for s, v in classificacao.coberturas.items())
                or "sem regras"
            )
        estado = leitura.estado or "—"
        if leitura.candidato is not None and leitura.candidato != leitura.estado:
            estado += f" → {leitura.candidato} ({leitura.contagem}/{leitura.debounce})"
        self._estado.config(text=estado)
        self._obs.config(text=leitura.observacao)

    def destruir(self) -> None:
        for widget in self._widgets:
            widget.destroy()
