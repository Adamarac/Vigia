import pytest

from tests.dubles import (
    CINZA,
    PRETO,
    VERDE,
    VERMELHO,
    LeitorFalso,
    NotificadorFalso,
    RelogioFalso,
    amostra_uniforme,
)
from vigia.app import Monitor
from vigia.dominio import ClassificadorPorCobertura, PoliticaDeNotificacao, Regiao, Regra, Retangulo
from vigia.leitura import ErroLeitura, Leitores

RECT = Retangulo(10, 10, 20, 10)
BOMBA = Regiao(
    "Bomba",
    RECT,
    (
        Regra(VERMELHO, "FALHA", mensagem="🔴 {regiao} falhou"),
        Regra(VERDE, "NORMAL", mensagem="🟢 {regiao} voltou ao normal"),
    ),
)


class Cenario:
    def __init__(self, regioes=(BOMBA,), notificador=None, debounce=2, cooldown=60):
        self.leitor = LeitorFalso()
        self.notificador = notificador or NotificadorFalso()
        self.relogio = RelogioFalso()
        self.monitor = Monitor(
            regioes=regioes,
            leitores=Leitores("amostragem", {"amostragem": self.leitor}),
            classificador=ClassificadorPorCobertura(),
            notificador=self.notificador,
            politica=PoliticaDeNotificacao(),
            debounce_amostras=debounce,
            cooldown_s=cooldown,
            relogio=self.relogio,
        )

    def ciclos(self, cor, vezes, rect=RECT):
        resultados = []
        for _ in range(vezes):
            self.leitor.definir(rect, amostra_uniforme(cor))
            resultados.append(self.monitor.ciclo()[0])
            self.relogio.avancar(5)
        return resultados


def test_estado_inicial_nao_notifica_e_transicao_notifica_com_a_mensagem_da_regra():
    cenario = Cenario()
    primeiro, segundo = cenario.ciclos(VERMELHO, 2)
    assert primeiro.estado is None and primeiro.candidato == "FALHA" and primeiro.contagem == 1
    assert segundo.estado == "FALHA"
    assert cenario.notificador.enviadas == []

    _, confirmado = cenario.ciclos(VERDE, 2)
    assert confirmado.estado == "NORMAL"
    assert confirmado.transicao is not None and confirmado.transicao.de == "FALHA"
    assert confirmado.mensagem == "🟢 Bomba voltou ao normal"
    assert cenario.notificador.enviadas == ["🟢 Bomba voltou ao normal"]
    assert "mensagem enviada" in confirmado.observacao


def test_leitura_com_erro_nao_derruba_o_ciclo_nem_o_estado():
    cenario = Cenario()
    cenario.ciclos(VERMELHO, 2)
    cenario.leitor.definir(RECT, ErroLeitura("fora da tela"))
    (resultado,) = cenario.monitor.ciclo()
    assert resultado.erro == "fora da tela"
    assert resultado.classificacao is None
    assert resultado.estado == "FALHA"
    assert resultado.observacao == "erro: fora da tela"


def test_falha_inesperada_na_leitura_vira_erro_no_resultado():
    cenario = Cenario()
    cenario.leitor.definir(RECT, RuntimeError("explodiu"))
    (resultado,) = cenario.monitor.ciclo()
    assert resultado.erro is not None and "explodiu" in resultado.erro


def test_falha_ao_notificar_e_registrada_mas_o_estado_avanca():
    cenario = Cenario(notificador=NotificadorFalso(falhar=True))
    cenario.ciclos(VERMELHO, 2)
    _, resultado = cenario.ciclos(VERDE, 2)
    assert resultado.estado == "NORMAL"
    assert resultado.mensagem == "🟢 Bomba voltou ao normal"
    assert resultado.erro is not None and "falha ao notificar" in resultado.erro


def test_observacao_diagnostica_regiao_mal_posicionada():
    cenario = Cenario()
    (preto,) = cenario.ciclos(PRETO, 1)
    assert "tudo preto" in preto.observacao
    (cinza,) = cenario.ciclos(CINZA, 1)
    assert cinza.observacao == "nenhuma cor configurada bate"

    sem_regras = Cenario(regioes=(Regiao("Vazia", RECT),))
    (resultado,) = sem_regras.ciclos(VERDE, 1)
    assert resultado.observacao == "sem regras: adicione uma cor"


def test_observadores_recebem_cada_leitura_e_um_que_falha_nao_atrapalha():
    cenario = Cenario()
    recebidas = []
    cenario.monitor.adicionar_observador(lambda _leitura: 1 / 0)
    cenario.monitor.adicionar_observador(recebidas.append)
    cenario.ciclos(VERMELHO, 3)
    assert [r.regiao.nome for r in recebidas] == ["Bomba"] * 3


def test_substituir_regioes_mantem_o_estado_das_que_continuam():
    cenario = Cenario()
    cenario.ciclos(VERMELHO, 2)
    outra = Regiao("Outra", Retangulo(50, 50, 5, 5), (Regra(VERDE, "OK"),))
    cenario.monitor.substituir_regioes((BOMBA, outra))
    cenario.leitor.definir(outra.rect, amostra_uniforme(VERDE))
    bomba, nova = cenario.monitor.ciclo()
    assert bomba.estado == "FALHA"
    assert nova.estado is None and nova.candidato == "OK"
    assert cenario.monitor.regioes == (BOMBA, outra)


def test_regiao_sem_resposta_do_leitor_e_erro_de_leitura():
    cenario = Cenario()
    (resultado,) = cenario.monitor.ciclo()
    assert resultado.erro is not None
    assert pytest.approx(0) == resultado.contagem
