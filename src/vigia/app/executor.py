"""Executor: roda ciclos do monitor em intervalo fixo, com pausa, retomada e parada."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from vigia.app.monitor import Monitor

log = logging.getLogger(__name__)


class Executor:
    def __init__(self, monitor: Monitor, intervalo_s: float) -> None:
        if intervalo_s <= 0:
            raise ValueError("intervalo deve ser positivo")
        self._monitor = monitor
        self._intervalo_s = intervalo_s
        self._parar = threading.Event()
        self._acordar = threading.Event()
        self._pausado = threading.Event()
        self._ciclo_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    @property
    def pausado(self) -> bool:
        return self._pausado.is_set()

    @property
    def rodando(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self) -> None:
        """Começa a rodar em segundo plano."""
        if self.rodando:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self.executar, name="vigia-executor", daemon=True)
        self._thread.start()

    def executar(self) -> None:
        """Roda na thread atual até `parar()` ser chamado."""
        while not self._parar.is_set():
            if not self._pausado.is_set():
                self.ciclo_unico()
            self._acordar.wait(self._intervalo_s)
            self._acordar.clear()

    def ciclo_unico(self) -> None:
        """Um ciclo agora, mesmo pausado. Nunca roda dois ciclos ao mesmo tempo."""
        with self._ciclo_lock:
            try:
                self._monitor.ciclo()
            except Exception:
                log.exception("ciclo falhou; o executor continua")

    def pausar(self) -> None:
        """Pausa e só volta depois que um ciclo em andamento terminar."""
        self._pausado.set()
        with self._ciclo_lock:
            pass

    def retomar(self) -> None:
        self._pausado.clear()
        self._acordar.set()

    def parar(self) -> None:
        self._parar.set()
        self._acordar.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=self._intervalo_s + 5)

    @contextmanager
    def pausado_durante(self) -> Iterator[None]:
        """Pausa enquanto algo cobre a tela (overlay), para não ler pixels contaminados."""
        estava_pausado = self.pausado
        self.pausar()
        try:
            yield
        finally:
            if not estava_pausado:
                self.retomar()
