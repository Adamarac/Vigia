import pytest

from vigia.dominio import Retangulo


def test_grade_5x5_tem_25_pontos_todos_dentro():
    rect = Retangulo(100, 50, 60, 24)
    pontos = rect.pontos_grade(5, 5)
    assert len(pontos) == 25
    assert len(set(pontos)) == 25
    for x, y in pontos:
        assert rect.x <= x < rect.direita
        assert rect.y <= y < rect.inferior


def test_grade_1x1_cai_no_centro():
    assert Retangulo(0, 0, 10, 10).pontos_grade(1, 1) == ((5, 5),)


def test_grade_em_retangulo_minusculo_nao_sai_dele():
    pontos = Retangulo(7, 7, 1, 1).pontos_grade(5, 5)
    assert set(pontos) == {(7, 7)}


@pytest.mark.parametrize("grade", [(0, 5), (5, 0)])
def test_grade_invalida(grade):
    with pytest.raises(ValueError):
        Retangulo(0, 0, 10, 10).pontos_grade(*grade)


@pytest.mark.parametrize("tamanho", [(0, 10), (10, 0), (-5, 10)])
def test_retangulo_sem_area_e_erro(tamanho):
    with pytest.raises(ValueError):
        Retangulo(0, 0, *tamanho)


def test_de_lista_e_como_lista():
    rect = Retangulo.de_lista([1, 2, 3, 4])
    assert rect == Retangulo(1, 2, 3, 4)
    assert rect.como_lista() == [1, 2, 3, 4]
    with pytest.raises(ValueError):
        Retangulo.de_lista([1, 2, 3])


def test_de_cantos_normaliza_a_ordem():
    assert Retangulo.de_cantos(50, 40, 10, 20) == Retangulo(10, 20, 40, 20)


def test_texto_legivel():
    assert str(Retangulo(1240, 310, 60, 24)) == "1240,310 60×24"
