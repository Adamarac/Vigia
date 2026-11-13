"""Modelos de configuração, imutáveis e validados na construção."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from vigia.dominio.mensagem import MENSAGEM_PADRAO
from vigia.dominio.regiao import MODOS, Regiao


@dataclass(frozen=True, slots=True)
class ConfigGeral:
    intervalo_s: float = 5.0
    debounce_amostras: int = 3
    cooldown_s: float = 300.0
    estado_desconhecido_notifica: bool = False

    def __post_init__(self) -> None:
        if self.intervalo_s <= 0:
            raise ValueError("intervalo_s deve ser positivo")
        if self.debounce_amostras < 1:
            raise ValueError("debounce_amostras deve ser pelo menos 1")
        if self.cooldown_s < 0:
            raise ValueError("cooldown_s não pode ser negativo")


@dataclass(frozen=True, slots=True)
class ConfigLeitura:
    modo: str = "amostragem"
    grade: tuple[int, int] = (5, 5)

    def __post_init__(self) -> None:
        if self.modo not in MODOS:
            raise ValueError(f"modo '{self.modo}' inválido; use um de {MODOS}")
        if len(self.grade) != 2 or any(v < 1 for v in self.grade):
            raise ValueError("grade deve ser [colunas, linhas], ambos pelo menos 1")


@dataclass(frozen=True, slots=True)
class ConfigTelegram:
    chat_id: str
    mensagem_padrao: str = MENSAGEM_PADRAO
    token_env: str = "TELEGRAM_BOT_TOKEN"

    def __post_init__(self) -> None:
        if not self.chat_id.strip():
            raise ValueError("chat_id vazio")
        if not self.token_env.strip():
            raise ValueError("token_env vazio")


@dataclass(frozen=True, slots=True)
class Config:
    geral: ConfigGeral = field(default_factory=ConfigGeral)
    leitura: ConfigLeitura = field(default_factory=ConfigLeitura)
    telegram: ConfigTelegram | None = None
    regioes: tuple[Regiao, ...] = ()

    def __post_init__(self) -> None:
        nomes = [r.nome for r in self.regioes]
        repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
        if repetidos:
            raise ValueError(f"nomes de região repetidos: {', '.join(repetidos)}")

    @property
    def mensagem_padrao(self) -> str:
        return self.telegram.mensagem_padrao if self.telegram else MENSAGEM_PADRAO

    def regiao(self, nome: str) -> Regiao | None:
        return next((r for r in self.regioes if r.nome == nome), None)

    def com_regioes(self, regioes: Iterable[Regiao]) -> Config:
        return replace(self, regioes=tuple(regioes))

    def com_regiao(self, regiao: Regiao) -> Config:
        """Acrescenta a região, ou substitui a de mesmo nome mantendo a posição."""
        if self.regiao(regiao.nome) is None:
            return self.com_regioes((*self.regioes, regiao))
        return self.com_regioes(regiao if r.nome == regiao.nome else r for r in self.regioes)

    def sem_regiao(self, nome: str) -> Config:
        return self.com_regioes(r for r in self.regioes if r.nome != nome)
