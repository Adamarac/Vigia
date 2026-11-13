"""Linha de comando do Vigia.

vigia ui                 painel (padrão)
vigia run                monitora no terminal, sem janela
vigia ler                um ciclo: imprime cor, leitura e diagnóstico de cada região
vigia selecionar         marca regiões com o mouse e grava no config
vigia mostrar            desenha as regiões configuradas por cima da tela
vigia testar-telegram    envia uma mensagem de teste
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from vigia import __version__
from vigia.ambiente import carregar_dotenv, configurar_logging, forcar_utf8
from vigia.app.executor import Executor
from vigia.app.fabrica import construir_monitor, construir_notificador
from vigia.app.monitor import LeituraRegiao
from vigia.config.modelos import Config
from vigia.config.repositorio_toml import ErroConfig, RepositorioConfig, RepositorioToml
from vigia.dominio.regiao import Regiao
from vigia.leitura.tela import ativar_dpi_awareness
from vigia.notificacao.base import ErroNotificacao
from vigia.notificacao.console import NotificadorNulo
from vigia.notificacao.telegram import NotificadorTelegram

log = logging.getLogger("vigia")

Comando = Callable[[argparse.Namespace, RepositorioConfig, Config], int]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    forcar_utf8()
    ativar_dpi_awareness()
    carregar_dotenv(Path(".env"))
    configurar_logging(args.verboso, args.log)
    repositorio = RepositorioToml(Path(args.config))
    try:
        config = repositorio.carregar()
        return COMANDOS[args.comando or "ui"](args, repositorio, config)
    except ErroConfig as erro:
        print(f"erro no config: {erro}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vigia", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config", default="config.toml", help="arquivo TOML (padrão: config.toml)"
    )
    parser.add_argument("--log", type=Path, default=None, help="também grava o log neste arquivo")
    parser.add_argument("--verboso", action="store_true", help="log em nível DEBUG")
    parser.add_argument("--versao", action="version", version=f"vigia {__version__}")
    sub = parser.add_subparsers(dest="comando")
    sub.add_parser("ui", help="abre o painel")
    sub.add_parser("run", help="monitora no terminal")
    sub.add_parser("ler", help="um ciclo de leitura, só texto")
    sub.add_parser("selecionar", help="marca regiões com o mouse")
    mostrar = sub.add_parser("mostrar", help="desenha as regiões por cima da tela")
    mostrar.add_argument("--segundos", type=float, default=5.0)
    sub.add_parser("testar-telegram", help="envia uma mensagem de teste")
    return parser


def _cmd_ui(args: argparse.Namespace, repositorio: RepositorioConfig, config: Config) -> int:
    from vigia.ui.painel import Painel

    notificador = construir_notificador(config)
    monitor = construir_monitor(config, notificador)
    executor = Executor(monitor, config.geral.intervalo_s)
    Painel(repositorio, config, monitor, executor, notificador).executar()
    return 0


def _cmd_run(args: argparse.Namespace, repositorio: RepositorioConfig, config: Config) -> int:
    if not config.regioes:
        print("Nenhuma região configurada. Use 'vigia selecionar' ou o painel.")
        return 1
    notificador = construir_notificador(config)
    monitor = construir_monitor(config, notificador)
    monitor.adicionar_observador(_registrar)
    executor = Executor(monitor, config.geral.intervalo_s)
    print(
        f"Monitorando {len(config.regioes)} região(ões) a cada {config.geral.intervalo_s:g} s "
        f"via {notificador}. Ctrl+C para parar."
    )
    executor.iniciar()
    try:
        while executor.rodando:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nParando…")
    finally:
        executor.parar()
    return 0


def _registrar(leitura: LeituraRegiao) -> None:
    classificacao = leitura.classificacao
    cor = classificacao.cor_dominante.hex if classificacao else "—"
    lido = classificacao.significado if classificacao else "—"
    log.debug(
        "%s: cor %s, leitura %s, estado %s %s",
        leitura.regiao.nome,
        cor,
        lido,
        leitura.estado,
        leitura.observacao,
    )


def _cmd_ler(args: argparse.Namespace, repositorio: RepositorioConfig, config: Config) -> int:
    if not config.regioes:
        print("Nenhuma região configurada. Use 'vigia selecionar' ou o painel.")
        return 1
    resultados = construir_monitor(config, NotificadorNulo()).ciclo()
    _imprimir_tabela(resultados)
    return 0 if all(r.erro is None for r in resultados) else 1


def _imprimir_tabela(resultados: Sequence[LeituraRegiao]) -> None:
    linhas = [("#", "Região", "Retângulo", "Cor", "Leitura", "Coberturas", "Observação")]
    for indice, r in enumerate(resultados, 1):
        c = r.classificacao
        linhas.append(
            (
                str(indice),
                r.regiao.nome,
                str(r.regiao.rect),
                c.cor_dominante.hex if c else "—",
                f"{c.significado} ({c.cobertura:.0%})" if c else "—",
                " · ".join(f"{s} {v:.0%}" for s, v in c.coberturas.items())
                if c and c.coberturas
                else "—",
                r.observacao,
            )
        )
    larguras = [max(len(linha[i]) for linha in linhas) for i in range(len(linhas[0]))]
    for linha in linhas:
        print("  ".join(campo.ljust(larguras[i]) for i, campo in enumerate(linha)).rstrip())


def _cmd_selecionar(
    args: argparse.Namespace, repositorio: RepositorioConfig, config: Config
) -> int:
    import tkinter as tk
    from tkinter import messagebox, simpledialog

    from vigia.ui.seletor import SeletorDeRegiao

    raiz = tk.Tk()
    raiz.withdraw()
    try:
        while True:
            rect = SeletorDeRegiao(raiz).selecionar()
            if rect is None:
                break
            nome = simpledialog.askstring("Nova região", f"Nome da região ({rect}):", parent=raiz)
            if nome and nome.strip():
                nome = nome.strip()
                if config.regiao(nome) is not None:
                    messagebox.showerror(
                        "Vigia", f"Já existe uma região chamada '{nome}'.", parent=raiz
                    )
                else:
                    config = config.com_regiao(Regiao(nome, rect))
                    repositorio.salvar(config)
                    print(f"Região '{nome}' gravada em {rect}.")
            if not messagebox.askyesno("Vigia", "Marcar outra região?", parent=raiz):
                break
    finally:
        raiz.destroy()
    return 0


def _cmd_mostrar(args: argparse.Namespace, repositorio: RepositorioConfig, config: Config) -> int:
    import tkinter as tk

    from vigia.ui.destaque import DestaqueDeRegioes

    if not config.regioes:
        print("Nenhuma região configurada.")
        return 1
    raiz = tk.Tk()
    raiz.withdraw()
    try:
        DestaqueDeRegioes(raiz).mostrar(config.regioes, args.segundos)
    finally:
        raiz.destroy()
    return 0


def _cmd_testar_telegram(
    args: argparse.Namespace, repositorio: RepositorioConfig, config: Config
) -> int:
    notificador = construir_notificador(config)
    if not isinstance(notificador, NotificadorTelegram):
        print(
            "Telegram não configurado: confira [notificador.telegram] no config "
            "e a variável do token."
        )
        return 1
    try:
        notificador.enviar(f"Teste do Vigia às {datetime.now():%H:%M:%S}")
    except ErroNotificacao as erro:
        print(f"Falha: {erro}")
        return 1
    print("Mensagem de teste enviada.")
    return 0


COMANDOS: dict[str, Comando] = {
    "ui": _cmd_ui,
    "run": _cmd_run,
    "ler": _cmd_ler,
    "selecionar": _cmd_selecionar,
    "mostrar": _cmd_mostrar,
    "testar-telegram": _cmd_testar_telegram,
}


if __name__ == "__main__":
    sys.exit(main())
