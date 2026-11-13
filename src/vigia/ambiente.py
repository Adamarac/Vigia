"""Preparação do processo: variáveis de ambiente e logging."""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def forcar_utf8() -> None:
    """Garante acentos e emojis corretos no console do Windows, que por padrão usa cp1252."""
    for fluxo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if reconfigurar is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigurar(encoding="utf-8")


def carregar_dotenv(caminho: Path) -> None:
    """Lê linhas CHAVE=valor de um .env sem sobrescrever variáveis já definidas."""
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        chave = chave.strip()
        valor = valor.strip().strip("\"'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def configurar_logging(verboso: bool, arquivo: Path | None = None) -> None:
    """Log textual: região, cor, cobertura, estado. Nunca imagens."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if arquivo is not None:
        handlers.append(
            RotatingFileHandler(arquivo, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        )
    logging.basicConfig(
        level=logging.DEBUG if verboso else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
