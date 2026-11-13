import pytest

from tests.dubles import VERDE, VERMELHO
from vigia.config import (
    Config,
    ConfigGeral,
    ConfigLeitura,
    ConfigTelegram,
    ErroConfig,
    RepositorioToml,
)
from vigia.dominio import Regiao, Regra, Retangulo


def config_completa() -> Config:
    return Config(
        geral=ConfigGeral(
            intervalo_s=2.5, debounce_amostras=2, cooldown_s=60, estado_desconhecido_notifica=True
        ),
        leitura=ConfigLeitura(modo="amostragem", grade=(4, 3)),
        telegram=ConfigTelegram(
            chat_id="123", mensagem_padrao="[{regiao}] {significado}", token_env="TOKEN_X"
        ),
        regioes=(
            Regiao(
                "Bomba P-101",
                Retangulo(1240, 310, 60, 24),
                (
                    Regra(
                        VERMELHO,
                        "FALHA",
                        tolerancia=50,
                        cobertura_min=0.6,
                        mensagem="🔴 {regiao}",
                        notificar=True,
                    ),
                    Regra(VERDE, "NORMAL", notificar=False),
                ),
            ),
            Regiao("Válvula", Retangulo(10, 20, 30, 40), (), modo="retangulo"),
        ),
    )


def test_salvar_e_carregar_preserva_tudo(tmp_path):
    repositorio = RepositorioToml(tmp_path / "config.toml")
    repositorio.salvar(config_completa())
    assert repositorio.carregar() == config_completa()
    assert not (tmp_path / "config.toml.tmp").exists()


def test_arquivo_inexistente_vale_config_vazia(tmp_path):
    config = RepositorioToml(tmp_path / "nao-existe.toml").carregar()
    assert config == Config()
    assert config.regioes == ()
    assert config.telegram is None


def escrever(tmp_path, texto: str) -> RepositorioToml:
    caminho = tmp_path / "config.toml"
    caminho.write_text(texto, encoding="utf-8")
    return RepositorioToml(caminho)


def test_chave_desconhecida_e_erro_com_nome(tmp_path):
    repositorio = escrever(tmp_path, "[geral]\nintervalo = 5\n")
    with pytest.raises(ErroConfig, match="intervalo"):
        repositorio.carregar()


def test_toml_malformado_e_erro(tmp_path):
    with pytest.raises(ErroConfig):
        escrever(tmp_path, "[geral\n").carregar()


def test_regiao_sem_rect_e_erro_apontando_a_regiao(tmp_path):
    repositorio = escrever(tmp_path, '[[regiao]]\nnome = "Bomba"\n')
    with pytest.raises(ErroConfig, match="Bomba"):
        repositorio.carregar()


def test_regra_com_cor_invalida_e_erro(tmp_path):
    repositorio = escrever(
        tmp_path,
        '[[regiao]]\nnome = "Bomba"\nrect = [0, 0, 10, 10]\n'
        '[[regiao.regra]]\ncor = "vermelho"\nsignificado = "FALHA"\n',
    )
    with pytest.raises(ErroConfig, match="FALHA"):
        repositorio.carregar()


def test_nomes_repetidos_sao_erro(tmp_path):
    repositorio = escrever(
        tmp_path,
        '[[regiao]]\nnome = "A"\nrect = [0, 0, 1, 1]\n'
        '[[regiao]]\nnome = "A"\nrect = [0, 0, 1, 1]\n',
    )
    with pytest.raises(ErroConfig, match="repetidos"):
        repositorio.carregar()


def test_valores_omitidos_recebem_padrao(tmp_path):
    config = escrever(tmp_path, '[[regiao]]\nnome = "A"\nrect = [0, 0, 1, 1]\n').carregar()
    assert config.geral == ConfigGeral()
    assert config.leitura == ConfigLeitura()
    assert config.regioes[0].modo is None
    assert config.regioes[0].regras == ()


def test_config_com_regiao_substitui_mantendo_a_posicao():
    config = config_completa()
    nova = Regiao("Bomba P-101", Retangulo(1, 1, 2, 2))
    atualizada = config.com_regiao(nova)
    assert atualizada.regioes[0] == nova
    assert atualizada.regioes[1].nome == "Válvula"
    acrescida = config.com_regiao(Regiao("Nova", Retangulo(0, 0, 1, 1)))
    assert [r.nome for r in acrescida.regioes] == ["Bomba P-101", "Válvula", "Nova"]


def test_config_sem_regiao_e_regiao():
    config = config_completa().sem_regiao("Válvula")
    assert [r.nome for r in config.regioes] == ["Bomba P-101"]
    assert config.regiao("Válvula") is None
    assert config.regiao("Bomba P-101") is not None


def test_mensagem_padrao_vem_do_telegram_ou_do_dominio():
    assert config_completa().mensagem_padrao == "[{regiao}] {significado}"
    assert "{regiao}" in Config().mensagem_padrao


@pytest.mark.parametrize(
    "fabrica",
    [
        lambda: ConfigGeral(intervalo_s=0),
        lambda: ConfigGeral(debounce_amostras=0),
        lambda: ConfigLeitura(modo="foto"),
        lambda: ConfigLeitura(grade=(0, 5)),
        lambda: ConfigTelegram(chat_id=" "),
    ],
)
def test_modelos_invalidos(fabrica):
    with pytest.raises(ValueError):
        fabrica()
