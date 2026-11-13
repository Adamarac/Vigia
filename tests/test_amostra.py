import pytest

from tests.dubles import BRANCO, PRETO, VERMELHO, amostra_mista, amostra_uniforme
from vigia.dominio import Amostra, Cor


def test_amostra_vazia_e_erro():
    with pytest.raises(ValueError):
        Amostra(())


def test_toda_preta():
    assert amostra_uniforme(PRETO).toda_preta
    assert not amostra_mista((PRETO, 24), (Cor(0, 0, 1), 1)).toda_preta


def test_cores_dominantes_ordena_por_frequencia_com_fracao():
    amostra = amostra_mista((VERMELHO, 20), (BRANCO, 5))
    dominantes = amostra.cores_dominantes()
    assert dominantes[0] == (VERMELHO, 0.8)
    assert dominantes[1] == (BRANCO, 0.2)


def test_cores_dominantes_agrupa_tons_parecidos_e_devolve_a_media():
    amostra = amostra_mista((Cor(200, 30, 30), 10), (Cor(210, 20, 10), 10), (BRANCO, 5))
    cor, fracao = amostra.cores_dominantes()[0]
    assert cor == Cor(205, 25, 20)
    assert fracao == 0.8


def test_cor_dominante_e_limite_n():
    amostra = amostra_mista((VERMELHO, 3), (BRANCO, 2), (PRETO, 1))
    assert amostra.cor_dominante == VERMELHO
    assert len(amostra.cores_dominantes(n=2)) == 2
    with pytest.raises(ValueError):
        amostra.cores_dominantes(n=0)
