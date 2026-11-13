import pytest
import requests

from vigia.notificacao import ErroNotificacao, NotificadorTelegram

TOKEN = "123:ABC-segredo"


class RespostaFalsa:
    def __init__(self, status, corpo=None, texto=""):
        self.status_code = status
        self._corpo = corpo if corpo is not None else {"ok": status == 200}
        self.text = texto or str(self._corpo)

    def json(self):
        return self._corpo


class SessaoFalsa:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def post(self, url, *, json, timeout):
        self.chamadas.append((url, json, timeout))
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def notificador(sessao, tentativas=3):
    esperas = []
    n = NotificadorTelegram(
        TOKEN, "999", sessao=sessao, tentativas=tentativas, dormir=esperas.append
    )
    return n, esperas


def test_envia_para_a_url_do_bot_com_chat_e_texto():
    sessao = SessaoFalsa(RespostaFalsa(200))
    n, esperas = notificador(sessao)
    n.enviar("olá")
    (url, corpo, timeout) = sessao.chamadas[0]
    assert url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert corpo == {"chat_id": "999", "text": "olá"}
    assert timeout == 10.0
    assert esperas == []


def test_repete_em_erro_de_servidor_e_em_limite_de_taxa():
    sessao = SessaoFalsa(RespostaFalsa(500), RespostaFalsa(429), RespostaFalsa(200))
    n, esperas = notificador(sessao)
    n.enviar("x")
    assert len(sessao.chamadas) == 3
    assert esperas == [2.0, 4.0]


def test_nao_repete_em_erro_de_configuracao():
    sessao = SessaoFalsa(RespostaFalsa(401, {"ok": False, "description": "Unauthorized"}))
    n, esperas = notificador(sessao)
    with pytest.raises(ErroNotificacao, match="401"):
        n.enviar("x")
    assert len(sessao.chamadas) == 1
    assert esperas == []


def test_esgota_tentativas_em_falha_de_rede_e_esconde_o_token():
    erro = requests.ConnectionError(f"falhou em https://api.telegram.org/bot{TOKEN}/sendMessage")
    sessao = SessaoFalsa(erro, erro, erro)
    n, _ = notificador(sessao)
    with pytest.raises(ErroNotificacao) as info:
        n.enviar("x")
    assert TOKEN not in str(info.value)
    assert "***" in str(info.value)
    assert len(sessao.chamadas) == 3


def test_resposta_200_sem_ok_e_falha():
    sessao = SessaoFalsa(RespostaFalsa(200, {"ok": False}))
    n, _ = notificador(sessao, tentativas=1)
    with pytest.raises(ErroNotificacao):
        n.enviar("x")


@pytest.mark.parametrize("argumentos", [("", "1"), ("t", " "), ("t", "1", 0)])
def test_parametros_invalidos(argumentos):
    with pytest.raises(ValueError):
        NotificadorTelegram(
            *argumentos[:2],
            sessao=SessaoFalsa(),
            tentativas=argumentos[2] if len(argumentos) > 2 else 3,
        )


def test_descricao_nao_mostra_o_token():
    n, _ = notificador(SessaoFalsa())
    assert str(n) == "Telegram (chat 999)"
