import pytest

from tests.dubles import RelogioFalso, classificacao
from vigia.dominio import MaquinaEstados


@pytest.fixture
def relogio():
    return RelogioFalso()


def alimentar(maquina, relogio, significado, vezes):
    transicoes = []
    for _ in range(vezes):
        transicoes.append(maquina.receber(classificacao(significado), relogio()))
        relogio.avancar(5)
    return transicoes


def test_estado_so_confirma_apos_debounce(relogio):
    maquina = MaquinaEstados("r", debounce=3, cooldown_s=0)
    assert alimentar(maquina, relogio, "FALHA", 2) == [None, None]
    assert maquina.estado is None
    assert maquina.candidato == "FALHA"
    assert maquina.contagem == 2
    alimentar(maquina, relogio, "FALHA", 1)
    assert maquina.estado == "FALHA"


def test_ruido_curto_nao_muda_o_estado(relogio):
    maquina = MaquinaEstados("r", debounce=3, cooldown_s=0)
    alimentar(maquina, relogio, "NORMAL", 3)
    alimentar(maquina, relogio, "FALHA", 2)
    assert maquina.estado == "NORMAL"
    assert alimentar(maquina, relogio, "NORMAL", 3) == [None, None, None]
    assert maquina.estado == "NORMAL"


def test_primeira_confirmacao_nao_gera_transicao(relogio):
    maquina = MaquinaEstados("r", debounce=1, cooldown_s=0)
    assert maquina.receber(classificacao("NORMAL"), relogio()) is None
    assert maquina.estado == "NORMAL"


def test_mudanca_confirmada_gera_transicao(relogio):
    maquina = MaquinaEstados("Bomba", debounce=2, cooldown_s=0)
    alimentar(maquina, relogio, "NORMAL", 2)
    transicoes = alimentar(maquina, relogio, "FALHA", 2)
    assert transicoes[0] is None
    transicao = transicoes[1]
    assert transicao is not None
    assert (transicao.regiao, transicao.de, transicao.para) == ("Bomba", "NORMAL", "FALHA")
    assert transicao.classificacao.significado == "FALHA"


def test_cooldown_segura_a_mesma_transicao_mas_nao_outra(relogio):
    maquina = MaquinaEstados("r", debounce=1, cooldown_s=300)
    alimentar(maquina, relogio, "NORMAL", 1)
    assert alimentar(maquina, relogio, "FALHA", 1)[0] is not None
    assert alimentar(maquina, relogio, "NORMAL", 1)[0] is not None
    assert alimentar(maquina, relogio, "FALHA", 1)[0] is None
    assert maquina.estado == "FALHA"
    relogio.avancar(300)
    alimentar(maquina, relogio, "NORMAL", 1)
    assert alimentar(maquina, relogio, "FALHA", 1)[0] is not None


@pytest.mark.parametrize("argumentos", [(0, 0), (1, -1)])
def test_parametros_invalidos(argumentos):
    with pytest.raises(ValueError):
        MaquinaEstados("r", *argumentos)
