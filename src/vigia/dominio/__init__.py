"""Modelo de domínio: cor, geometria, amostra, regras, classificação, estado e mensagens.

Nada aqui depende de tela, rede, disco ou interface gráfica.
"""

from vigia.dominio.amostra import Amostra
from vigia.dominio.classificacao import (
    DESCONHECIDO,
    Classificacao,
    Classificador,
    ClassificadorPorCobertura,
)
from vigia.dominio.cor import Cor
from vigia.dominio.estado import MaquinaEstados, Transicao
from vigia.dominio.geometria import Ponto, Retangulo
from vigia.dominio.mensagem import (
    MENSAGEM_PADRAO,
    PoliticaDeNotificacao,
    RenderizadorMensagem,
    contexto_de,
)
from vigia.dominio.regiao import MODOS, Regiao, Regra

__all__ = [
    "DESCONHECIDO",
    "MENSAGEM_PADRAO",
    "MODOS",
    "Amostra",
    "Classificacao",
    "Classificador",
    "ClassificadorPorCobertura",
    "Cor",
    "MaquinaEstados",
    "PoliticaDeNotificacao",
    "Ponto",
    "Regiao",
    "Regra",
    "RenderizadorMensagem",
    "Retangulo",
    "Transicao",
    "contexto_de",
]
