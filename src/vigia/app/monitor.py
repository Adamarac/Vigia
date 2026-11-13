"""Monitor: um ciclo = ler cada região, classificar, atualizar estado e notificar transições."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from vigia.dominio.classificacao import Classificacao, Classificador
from vigia.dominio.estado import MaquinaEstados, Transicao
from vigia.dominio.mensagem import PoliticaDeNotificacao
from vigia.dominio.regiao import Regiao
from vigia.leitura.base import ErroLeitura
from vigia.leitura.fabrica import Leitores
from vigia.notificacao.base import ErroNotificacao, Notificador

log = logging.getLogger(__name__)

Relogio = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class LeituraRegiao:
    """O que aconteceu com uma região num ciclo. É o que o painel e o terminal mostram."""

    regiao: Regiao
    instante: datetime
    classificacao: Classificacao | None = None
    estado: str | None = None
    candidato: str | None = None
    contagem: int = 0
    debounce: int = 1
    erro: str | None = None
    transicao: Transicao | None = None
    mensagem: str | None = None

    @property
    def observacao(self) -> str:
        """Diagnóstico curto: diz se a região está sendo lida direito."""
        if self.erro:
            return f"erro: {self.erro}"
        if self.classificacao is None:
            return ""
        avisos: list[str] = []
        if self.classificacao.toda_preta:
            avisos.append("tudo preto: janela protegida, minimizada ou fora da tela?")
        if not self.regiao.regras:
            avisos.append("sem regras: adicione uma cor")
        elif self.classificacao.desconhecido:
            avisos.append("nenhuma cor configurada bate")
        if self.mensagem:
            avisos.append("mensagem enviada")
        return " · ".join(avisos)


Observador = Callable[[LeituraRegiao], None]


class Monitor:
    def __init__(
        self,
        regioes: Iterable[Regiao],
        leitores: Leitores,
        classificador: Classificador,
        notificador: Notificador,
        politica: PoliticaDeNotificacao,
        debounce_amostras: int,
        cooldown_s: float,
        relogio: Relogio = datetime.now,
    ) -> None:
        self._leitores = leitores
        self._classificador = classificador
        self._notificador = notificador
        self._politica = politica
        self._debounce = debounce_amostras
        self._cooldown_s = cooldown_s
        self._relogio = relogio
        self._lock = threading.RLock()
        self._observadores: list[Observador] = []
        self._maquinas: dict[str, MaquinaEstados] = {}
        self._regioes: tuple[Regiao, ...] = ()
        self.substituir_regioes(regioes)

    @property
    def regioes(self) -> tuple[Regiao, ...]:
        with self._lock:
            return self._regioes

    def substituir_regioes(self, regioes: Iterable[Regiao]) -> None:
        """Troca a lista de regiões mantendo o estado das que continuam existindo."""
        with self._lock:
            novas = tuple(regioes)
            self._maquinas = {
                r.nome: self._maquinas.get(r.nome)
                or MaquinaEstados(r.nome, self._debounce, self._cooldown_s)
                for r in novas
            }
            self._regioes = novas

    def adicionar_observador(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def ciclo(self) -> list[LeituraRegiao]:
        with self._lock:
            resultados = [self._processar(r, self._maquinas[r.nome]) for r in self._regioes]
        for resultado in resultados:
            self._avisar(resultado)
        return resultados

    def _processar(self, regiao: Regiao, maquina: MaquinaEstados) -> LeituraRegiao:
        agora = self._relogio()
        try:
            amostra = self._leitores.para(regiao).ler(regiao.rect)
        except ErroLeitura as erro:
            log.warning("região '%s': %s", regiao.nome, erro)
            return self._resultado(regiao, maquina, agora, erro=str(erro))
        except Exception as erro:
            log.exception("região '%s': falha inesperada na leitura", regiao.nome)
            return self._resultado(regiao, maquina, agora, erro=f"falha inesperada: {erro}")

        classificacao = self._classificador.classificar(amostra, regiao.regras)
        transicao = maquina.receber(classificacao, agora)
        if transicao is None:
            return self._resultado(regiao, maquina, agora, classificacao=classificacao)

        log.info("região '%s': %s -> %s", regiao.nome, transicao.de, transicao.para)
        mensagem = self._politica.mensagem_para(regiao, transicao)
        erro_envio = self._enviar(mensagem) if mensagem is not None else None
        return self._resultado(
            regiao,
            maquina,
            agora,
            classificacao=classificacao,
            transicao=transicao,
            mensagem=mensagem,
            erro=erro_envio,
        )

    def _enviar(self, texto: str) -> str | None:
        try:
            self._notificador.enviar(texto)
        except ErroNotificacao as erro:
            log.error("falha ao notificar: %s", erro)
            return f"falha ao notificar: {erro}"
        return None

    @staticmethod
    def _resultado(
        regiao: Regiao,
        maquina: MaquinaEstados,
        agora: datetime,
        classificacao: Classificacao | None = None,
        transicao: Transicao | None = None,
        mensagem: str | None = None,
        erro: str | None = None,
    ) -> LeituraRegiao:
        return LeituraRegiao(
            regiao=regiao,
            instante=agora,
            classificacao=classificacao,
            estado=maquina.estado,
            candidato=maquina.candidato,
            contagem=maquina.contagem,
            debounce=maquina.debounce,
            erro=erro,
            transicao=transicao,
            mensagem=mensagem,
        )

    def _avisar(self, resultado: LeituraRegiao) -> None:
        for observador in self._observadores:
            try:
                observador(resultado)
            except Exception:
                log.exception("observador falhou; o ciclo continua")
