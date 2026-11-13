"""Dublês de teste: leitor, notificador e relógio controláveis; amostras sintéticas.

Nenhuma imagem real da tela entra no repositório. As amostras são geradas em código.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from vigia.dominio import DESCONHECIDO, Amostra, Classificacao, Cor, Retangulo
from vigia.leitura.base import ErroLeitura
from vigia.notificacao.base import ErroNotificacao

VERMELHO = Cor(220, 30, 30)
VERDE = Cor(30, 160, 60)
CINZA = Cor(128, 128, 128)
BRANCO = Cor(255, 255, 255)
PRETO = Cor(0, 0, 0)


def amostra_uniforme(cor: Cor, n: int = 25) -> Amostra:
    return Amostra((cor,) * n)


def amostra_mista(*partes: tuple[Cor, int]) -> Amostra:
    """Ex.: amostra_mista((VERMELHO, 20), (BRANCO, 5)) = fundo vermelho com texto branco."""
    cores: list[Cor] = []
    for cor, quantidade in partes:
        cores.extend([cor] * quantidade)
    return Amostra(tuple(cores))


def classificacao(significado: str, cor: Cor = VERMELHO, cobertura: float = 1.0) -> Classificacao:
    coberturas = {} if significado == DESCONHECIDO else {significado: cobertura}
    return Classificacao(
        significado=significado,
        cobertura=0.0 if significado == DESCONHECIDO else cobertura,
        cor_dominante=cor,
        coberturas=coberturas,
        cores_dominantes=((cor, 1.0),),
        toda_preta=cor.eh_preta,
    )


class LeitorFalso:
    def __init__(self) -> None:
        self._respostas: dict[Retangulo, Amostra | Exception] = {}
        self.leituras: list[Retangulo] = []

    def definir(self, rect: Retangulo, resposta: Amostra | Exception) -> None:
        self._respostas[rect] = resposta

    def ler(self, rect: Retangulo) -> Amostra:
        self.leituras.append(rect)
        resposta = self._respostas.get(rect)
        if resposta is None:
            raise ErroLeitura(f"sem resposta definida para {rect}")
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class NotificadorFalso:
    def __init__(self, falhar: bool = False) -> None:
        self.enviadas: list[str] = []
        self.falhar = falhar

    def enviar(self, texto: str) -> None:
        if self.falhar:
            raise ErroNotificacao("falha simulada")
        self.enviadas.append(texto)


class RelogioFalso:
    def __init__(self, inicio: datetime | None = None) -> None:
        self.agora = inicio or datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)
