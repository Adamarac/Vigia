"""Região vigiada e as regras que dão significado às cores lidas nela."""

from __future__ import annotations

from dataclasses import dataclass, replace

from vigia.dominio.amostra import Amostra
from vigia.dominio.cor import Cor
from vigia.dominio.geometria import Retangulo

MODOS = ("amostragem", "retangulo")


@dataclass(frozen=True, slots=True)
class Regra:
    """Uma cor esperada na região e o que ela significa."""

    cor: Cor
    significado: str
    tolerancia: float = 40.0
    cobertura_min: float = 0.5
    mensagem: str | None = None
    notificar: bool = True

    def __post_init__(self) -> None:
        if not self.significado.strip():
            raise ValueError("regra sem significado")
        if self.tolerancia < 0:
            raise ValueError("tolerância não pode ser negativa")
        if not 0 < self.cobertura_min <= 1:
            raise ValueError("cobertura_min deve estar entre 0 (exclusivo) e 1")

    def cobertura(self, amostra: Amostra) -> float:
        """Fração dos pontos da amostra que estão dentro da tolerância desta cor."""
        dentro = sum(1 for cor in amostra.cores if cor.distancia(self.cor) <= self.tolerancia)
        return dentro / len(amostra)


@dataclass(frozen=True, slots=True)
class Regiao:
    nome: str
    rect: Retangulo
    regras: tuple[Regra, ...] = ()
    modo: str | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ValueError("região sem nome")
        if self.modo is not None and self.modo not in MODOS:
            raise ValueError(f"modo '{self.modo}' inválido; use um de {MODOS}")
        significados = [regra.significado for regra in self.regras]
        if len(set(significados)) != len(significados):
            raise ValueError(f"região '{self.nome}' tem significados repetidos")

    def regra_por_significado(self, significado: str) -> Regra | None:
        return next((r for r in self.regras if r.significado == significado), None)

    def com_regra(self, regra: Regra) -> Regiao:
        return replace(self, regras=(*self.regras, regra))

    def sem_regra(self, significado: str) -> Regiao:
        return replace(self, regras=tuple(r for r in self.regras if r.significado != significado))
