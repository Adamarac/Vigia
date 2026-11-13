import math

import pytest

from vigia.dominio import Cor


def test_de_hex_aceita_com_e_sem_cerquilha_e_minusculas():
    assert Cor.de_hex("#FF8000") == Cor(255, 128, 0)
    assert Cor.de_hex("ff8000") == Cor(255, 128, 0)


@pytest.mark.parametrize("texto", ["#FFF", "#GG0000", "", "#1234567"])
def test_de_hex_rejeita_formato_invalido(texto):
    with pytest.raises(ValueError):
        Cor.de_hex(texto)


def test_hex_sai_em_maiusculas_com_cerquilha():
    assert Cor(255, 128, 0).hex == "#FF8000"
    assert str(Cor(0, 0, 0)) == "#000000"


def test_de_colorref_inverte_a_ordem_bgr():
    assert Cor.de_colorref(0x0000FF) == Cor(255, 0, 0)
    assert Cor.de_colorref(0xFF0000) == Cor(0, 0, 255)
    assert Cor.de_colorref(0x00FF00) == Cor(0, 255, 0)


@pytest.mark.parametrize("componentes", [(256, 0, 0), (0, -1, 0), (0, 0, 300)])
def test_componente_fora_da_faixa_e_erro(componentes):
    with pytest.raises(ValueError):
        Cor(*componentes)


def test_distancia_euclidiana():
    assert Cor(0, 0, 0).distancia(Cor(0, 0, 0)) == 0
    assert math.isclose(Cor(0, 0, 0).distancia(Cor(255, 255, 255)), 441.67, abs_tol=0.01)
    assert Cor(10, 0, 0).distancia(Cor(13, 4, 0)) == 5


def test_quantizada_agrupa_cores_parecidas():
    assert Cor(200, 30, 30).quantizada(32) == Cor(192, 0, 0)
    assert Cor(210, 20, 10).quantizada(32) == Cor(192, 0, 0)
    assert Cor(255, 255, 255).quantizada(32) == Cor(224, 224, 224)


def test_media():
    assert Cor.media([Cor(0, 0, 0), Cor(200, 100, 50)]) == Cor(100, 50, 25)
    with pytest.raises(ValueError):
        Cor.media([])


def test_eh_preta():
    assert Cor(0, 0, 0).eh_preta
    assert not Cor(0, 0, 1).eh_preta
