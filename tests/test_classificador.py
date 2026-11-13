import pytest

from tests.dubles import BRANCO, CINZA, PRETO, VERDE, VERMELHO, amostra_mista, amostra_uniforme
from vigia.dominio import DESCONHECIDO, ClassificadorPorCobertura, Cor, Regra

FALHA = Regra(cor=VERMELHO, significado="FALHA")
NORMAL = Regra(cor=VERDE, significado="NORMAL")


@pytest.fixture
def classificador():
    return ClassificadorPorCobertura()


def test_fundo_vermelho_com_texto_branco_e_falha(classificador):
    resultado = classificador.classificar(
        amostra_mista((VERMELHO, 20), (BRANCO, 5)), [FALHA, NORMAL]
    )
    assert resultado.significado == "FALHA"
    assert resultado.cobertura == 0.8
    assert resultado.coberturas == {"FALHA": 0.8, "NORMAL": 0.0}
    assert resultado.cor_dominante == VERMELHO
    assert not resultado.desconhecido


def test_cinza_nao_bate_com_nenhuma_regra(classificador):
    resultado = classificador.classificar(amostra_uniforme(CINZA), [FALHA, NORMAL])
    assert resultado.significado == DESCONHECIDO
    assert resultado.desconhecido
    assert resultado.cobertura == 0.0
    assert resultado.coberturas == {"FALHA": 0.0, "NORMAL": 0.0}


def test_sem_regras_e_desconhecido_mas_informa_a_cor(classificador):
    resultado = classificador.classificar(amostra_uniforme(VERDE), [])
    assert resultado.desconhecido
    assert resultado.coberturas == {}
    assert resultado.cor_dominante == VERDE
    assert resultado.cores_dominantes == ((VERDE, 1.0),)


def test_tolerancia_decide_se_um_tom_proximo_conta():
    lido = amostra_uniforme(Cor(220, 30, 30))
    regra_puro = Regra(cor=Cor(255, 0, 0), significado="FALHA", tolerancia=40)
    assert ClassificadorPorCobertura().classificar(lido, [regra_puro]).desconhecido
    regra_larga = Regra(cor=Cor(255, 0, 0), significado="FALHA", tolerancia=60)
    assert ClassificadorPorCobertura().classificar(lido, [regra_larga]).significado == "FALHA"


def test_cobertura_minima_decide_quando_o_fundo_e_minoria(classificador):
    amostra = amostra_mista((VERMELHO, 10), (BRANCO, 15))
    assert classificador.classificar(amostra, [FALHA]).desconhecido
    folgada = Regra(cor=VERMELHO, significado="FALHA", cobertura_min=0.3)
    assert classificador.classificar(amostra, [folgada]).significado == "FALHA"


def test_marca_amostra_toda_preta(classificador):
    assert classificador.classificar(amostra_uniforme(PRETO), [FALHA]).toda_preta
    assert not classificador.classificar(amostra_uniforme(VERMELHO), [FALHA]).toda_preta


def test_regra_invalida():
    with pytest.raises(ValueError):
        Regra(cor=VERMELHO, significado=" ")
    with pytest.raises(ValueError):
        Regra(cor=VERMELHO, significado="X", cobertura_min=0)
    with pytest.raises(ValueError):
        Regra(cor=VERMELHO, significado="X", tolerancia=-1)
