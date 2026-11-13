import pytest

from tests.dubles import LeitorFalso
from vigia.dominio import Cor, Regiao, Retangulo
from vigia.leitura import ErroLeitura, Leitores, LeitorGDI, LeitorRetangulo
from vigia.leitura.gdi import CLR_INVALID

VERMELHO_COLORREF = 0x0000FF
VERDE_COLORREF = 0x00FF00


class ApiGdiFalsa:
    def __init__(self, pixels=None, padrao=VERMELHO_COLORREF, hdc=42):
        self.pixels = pixels or {}
        self.padrao = padrao
        self.hdc = hdc
        self.liberados = []

    def get_dc(self):
        return self.hdc

    def release_dc(self, hdc):
        self.liberados.append(hdc)

    def get_pixel(self, hdc, x, y):
        return self.pixels.get((x, y), self.padrao)


def test_gdi_le_a_grade_e_converte_colorref():
    api = ApiGdiFalsa()
    amostra = LeitorGDI(grade=(3, 2), api=api).ler(Retangulo(10, 10, 30, 20))
    assert len(amostra) == 6
    assert set(amostra.cores) == {Cor(255, 0, 0)}
    assert api.liberados == [42]


def test_gdi_mistura_de_pontos():
    rect = Retangulo(0, 0, 10, 10)
    (centro,) = rect.pontos_grade(1, 1)
    api = ApiGdiFalsa(pixels={centro: VERDE_COLORREF})
    assert LeitorGDI(grade=(1, 1), api=api).ler(rect).cores == (Cor(0, 255, 0),)


def test_gdi_ponto_fora_da_tela_e_erro_e_libera_o_dc():
    api = ApiGdiFalsa(padrao=CLR_INVALID)
    with pytest.raises(ErroLeitura, match="fora da tela"):
        LeitorGDI(api=api).ler(Retangulo(5000, 5000, 10, 10))
    assert api.liberados == [42]


def test_gdi_sem_dc_e_erro():
    with pytest.raises(ErroLeitura, match="GetDC"):
        LeitorGDI(api=ApiGdiFalsa(hdc=0)).ler(Retangulo(0, 0, 10, 10))


def test_gdi_grade_invalida():
    with pytest.raises(ValueError):
        LeitorGDI(grade=(0, 1), api=ApiGdiFalsa())


class CapturadorFalso:
    def __init__(self, largura, altura, cor_bgra=(0, 0, 255, 255), truncar=0, erro=None):
        self.largura, self.altura = largura, altura
        self.pixels = bytes(cor_bgra) * (largura * altura)
        if truncar:
            self.pixels = self.pixels[:-truncar]
        self.erro = erro

    def capturar(self, rect):
        if self.erro:
            raise self.erro
        return self.largura, self.altura, self.pixels


def test_retangulo_le_todos_os_pixels_quando_cabem():
    amostra = LeitorRetangulo(max_pontos=200, capturador=CapturadorFalso(10, 10)).ler(
        Retangulo(0, 0, 10, 10)
    )
    assert len(amostra) == 100
    assert set(amostra.cores) == {Cor(255, 0, 0)}


def test_retangulo_espalha_quando_excede_max_pontos():
    amostra = LeitorRetangulo(max_pontos=10, capturador=CapturadorFalso(10, 10)).ler(
        Retangulo(0, 0, 10, 10)
    )
    assert len(amostra) == 9


def test_retangulo_truncado_ou_com_falha_e_erro():
    with pytest.raises(ErroLeitura, match="truncado"):
        LeitorRetangulo(capturador=CapturadorFalso(4, 4, truncar=4)).ler(Retangulo(0, 0, 4, 4))
    with pytest.raises(ErroLeitura, match="boom"):
        LeitorRetangulo(capturador=CapturadorFalso(4, 4, erro=RuntimeError("boom"))).ler(
            Retangulo(0, 0, 4, 4)
        )


def test_leitores_escolhe_pelo_modo_da_regiao_ou_padrao():
    amostragem, retangulo = LeitorFalso(), LeitorFalso()
    leitores = Leitores("amostragem", {"amostragem": amostragem, "retangulo": retangulo})
    assert leitores.para(Regiao("a", Retangulo(0, 0, 1, 1))) is amostragem
    assert leitores.para(Regiao("b", Retangulo(0, 0, 1, 1), modo="retangulo")) is retangulo
    with pytest.raises(ValueError):
        Leitores("foto", {"amostragem": amostragem})
