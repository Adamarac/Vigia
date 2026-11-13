from tests.dubles import VERMELHO
from vigia.app import construir_monitor, construir_notificador
from vigia.config import Config, ConfigTelegram
from vigia.dominio import Regiao, Regra, Retangulo
from vigia.notificacao import NotificadorConsole, NotificadorTelegram


def test_sem_secao_telegram_cai_no_console():
    assert isinstance(construir_notificador(Config(), ambiente={}), NotificadorConsole)


def test_sem_token_no_ambiente_cai_no_console():
    config = Config(telegram=ConfigTelegram(chat_id="1", token_env="TOKEN_X"))
    assert isinstance(construir_notificador(config, ambiente={"TOKEN_X": "  "}), NotificadorConsole)


def test_com_token_usa_telegram():
    config = Config(telegram=ConfigTelegram(chat_id="1", token_env="TOKEN_X"))
    notificador = construir_notificador(config, ambiente={"TOKEN_X": "abc"})
    assert isinstance(notificador, NotificadorTelegram)
    assert str(notificador) == "Telegram (chat 1)"


def test_construir_monitor_carrega_as_regioes():
    regiao = Regiao("A", Retangulo(0, 0, 5, 5), (Regra(VERMELHO, "FALHA"),))
    monitor = construir_monitor(Config(regioes=(regiao,)), NotificadorConsole())
    assert monitor.regioes == (regiao,)
