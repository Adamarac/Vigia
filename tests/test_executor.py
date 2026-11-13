import threading
import time

from vigia.app import Executor


class MonitorContador:
    def __init__(self):
        self.ciclos = 0
        self.lock = threading.Lock()

    def ciclo(self):
        with self.lock:
            self.ciclos += 1
        return []


def esperar(condicao, timeout=2.0):
    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(0.01)
    return False


def test_executor_roda_ciclos_em_segundo_plano_e_para():
    monitor = MonitorContador()
    executor = Executor(monitor, intervalo_s=0.01)
    executor.iniciar()
    assert esperar(lambda: monitor.ciclos >= 3)
    executor.parar()
    assert not executor.rodando


def test_pausar_interrompe_e_retomar_volta():
    monitor = MonitorContador()
    executor = Executor(monitor, intervalo_s=0.01)
    executor.iniciar()
    assert esperar(lambda: monitor.ciclos >= 1)
    executor.pausar()
    contagem = monitor.ciclos
    time.sleep(0.05)
    assert monitor.ciclos == contagem
    assert executor.pausado
    executor.retomar()
    assert esperar(lambda: monitor.ciclos > contagem)
    executor.parar()


def test_ciclo_unico_funciona_pausado_e_engole_excecao():
    class MonitorQueFalha:
        def ciclo(self):
            raise RuntimeError("boom")

    executor = Executor(MonitorQueFalha(), intervalo_s=1)
    executor.pausar()
    executor.ciclo_unico()

    monitor = MonitorContador()
    executor = Executor(monitor, intervalo_s=1)
    executor.pausar()
    executor.ciclo_unico()
    assert monitor.ciclos == 1


def test_pausado_durante_restaura_o_estado_anterior():
    monitor = MonitorContador()
    executor = Executor(monitor, intervalo_s=1)
    with executor.pausado_durante():
        assert executor.pausado
    assert not executor.pausado
    executor.pausar()
    with executor.pausado_durante():
        pass
    assert executor.pausado
