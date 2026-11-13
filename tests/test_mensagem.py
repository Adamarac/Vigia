from datetime import datetime

from tests.dubles import VERDE, VERMELHO, classificacao
from vigia.dominio import (
    DESCONHECIDO,
    MENSAGEM_PADRAO,
    PoliticaDeNotificacao,
    Regiao,
    Regra,
    RenderizadorMensagem,
    Retangulo,
    Transicao,
    contexto_de,
)

INSTANTE = datetime(2026, 3, 4, 17, 32, 10)


def transicao(para="FALHA", de="NORMAL"):
    return Transicao("Bomba", de, para, classificacao(para, VERMELHO, 0.92), INSTANTE)


def test_contexto_tem_todos_os_placeholders():
    contexto = contexto_de(transicao())
    assert contexto == {
        "regiao": "Bomba",
        "significado": "FALHA",
        "significado_anterior": "NORMAL",
        "cor_hex": "#DC1E1E",
        "cobertura": "92%",
        "hora": "17:32:10",
        "data": "04/03/2026",
        "texto": "",
    }


def test_render_preenche_e_mantem_placeholder_desconhecido():
    texto = RenderizadorMensagem().render(
        "{regiao}: {significado} {inexistente}", contexto_de(transicao())
    )
    assert texto == "Bomba: FALHA {inexistente}"


def test_render_com_template_quebrado_nao_derruba_o_ciclo():
    texto = RenderizadorMensagem().render("{cobertura:.0%} {", contexto_de(transicao()))
    assert texto == "Bomba: FALHA"


def regiao(**regra_extra):
    return Regiao(
        "Bomba",
        Retangulo(0, 0, 10, 10),
        (
            Regra(VERMELHO, "FALHA", mensagem="🔴 {regiao} em FALHA às {hora}", **regra_extra),
            Regra(VERDE, "NORMAL"),
        ),
    )


def test_politica_usa_a_mensagem_da_regra():
    assert (
        PoliticaDeNotificacao().mensagem_para(regiao(), transicao())
        == "🔴 Bomba em FALHA às 17:32:10"
    )


def test_politica_cai_no_padrao_quando_a_regra_nao_tem_mensagem():
    texto = PoliticaDeNotificacao().mensagem_para(regiao(), transicao(para="NORMAL", de="FALHA"))
    assert texto == MENSAGEM_PADRAO.format(
        regiao="Bomba", significado="NORMAL", cor_hex="#DC1E1E", hora="17:32:10"
    )


def test_politica_respeita_notificar_false():
    assert PoliticaDeNotificacao().mensagem_para(regiao(notificar=False), transicao()) is None


def test_politica_e_desconhecido():
    for_desconhecido = transicao(para=DESCONHECIDO)
    assert PoliticaDeNotificacao().mensagem_para(regiao(), for_desconhecido) is None
    texto = PoliticaDeNotificacao(desconhecido_notifica=True).mensagem_para(
        regiao(), for_desconhecido
    )
    assert texto is not None and DESCONHECIDO in texto


def test_politica_ignora_significado_sem_regra():
    assert PoliticaDeNotificacao().mensagem_para(regiao(), transicao(para="OUTRO")) is None
