"""Carrega e grava a configuração em TOML.

Chaves desconhecidas são erro, para que um nome digitado errado não passe em silêncio.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import tomli_w

from vigia.config.modelos import Config, ConfigGeral, ConfigLeitura, ConfigTelegram
from vigia.dominio.cor import Cor
from vigia.dominio.geometria import Retangulo
from vigia.dominio.regiao import Regiao, Regra


class ErroConfig(ValueError):
    """Configuração ausente, malformada ou com valores inválidos."""


class RepositorioConfig(Protocol):
    def carregar(self) -> Config: ...
    def salvar(self, config: Config) -> None: ...


class RepositorioToml:
    def __init__(self, caminho: Path) -> None:
        self._caminho = caminho

    @property
    def caminho(self) -> Path:
        return self._caminho

    def carregar(self) -> Config:
        """Arquivo inexistente vale como configuração vazia: o painel permite criar tudo."""
        if not self._caminho.is_file():
            return Config()
        try:
            dados = tomllib.loads(self._caminho.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as erro:
            raise ErroConfig(f"não foi possível ler {self._caminho}: {erro}") from erro
        return _config_de(dados)

    def salvar(self, config: Config) -> None:
        texto = tomli_w.dumps(_dict_de(config))
        temporario = self._caminho.with_name(self._caminho.name + ".tmp")
        try:
            temporario.write_text(texto, encoding="utf-8")
            os.replace(temporario, self._caminho)
        except OSError as erro:
            raise ErroConfig(f"não foi possível gravar {self._caminho}: {erro}") from erro


# --- TOML -> modelos -------------------------------------------------------


def _config_de(dados: Mapping[str, Any]) -> Config:
    _somente_chaves(dados, {"geral", "leitura", "notificador", "regiao"}, "raiz")
    notificador = _secao(dados, "notificador")
    _somente_chaves(notificador, {"telegram"}, "[notificador]")
    try:
        return Config(
            geral=_geral_de(_secao(dados, "geral")),
            leitura=_leitura_de(_secao(dados, "leitura")),
            telegram=_telegram_de(notificador.get("telegram")),
            regioes=tuple(_regiao_de(r) for r in _lista(dados, "regiao")),
        )
    except ValueError as erro:
        raise ErroConfig(str(erro)) from erro


def _geral_de(d: Mapping[str, Any]) -> ConfigGeral:
    _somente_chaves(
        d,
        {"intervalo_s", "debounce_amostras", "cooldown_s", "estado_desconhecido_notifica"},
        "[geral]",
    )
    padrao = ConfigGeral()
    return ConfigGeral(
        intervalo_s=float(d.get("intervalo_s", padrao.intervalo_s)),
        debounce_amostras=int(d.get("debounce_amostras", padrao.debounce_amostras)),
        cooldown_s=float(d.get("cooldown_s", padrao.cooldown_s)),
        estado_desconhecido_notifica=bool(
            d.get("estado_desconhecido_notifica", padrao.estado_desconhecido_notifica)
        ),
    )


def _leitura_de(d: Mapping[str, Any]) -> ConfigLeitura:
    _somente_chaves(d, {"modo", "grade"}, "[leitura]")
    padrao = ConfigLeitura()
    grade = d.get("grade", list(padrao.grade))
    if not isinstance(grade, list) or len(grade) != 2:
        raise ErroConfig("[leitura].grade deve ser uma lista [colunas, linhas]")
    return ConfigLeitura(modo=str(d.get("modo", padrao.modo)), grade=(int(grade[0]), int(grade[1])))


def _telegram_de(d: Mapping[str, Any] | None) -> ConfigTelegram | None:
    if d is None:
        return None
    _somente_chaves(d, {"chat_id", "mensagem_padrao", "token_env"}, "[notificador.telegram]")
    if "chat_id" not in d:
        raise ErroConfig("[notificador.telegram] precisa de chat_id")
    padrao_args: dict[str, Any] = {}
    if "mensagem_padrao" in d:
        padrao_args["mensagem_padrao"] = str(d["mensagem_padrao"])
    if "token_env" in d:
        padrao_args["token_env"] = str(d["token_env"])
    return ConfigTelegram(chat_id=str(d["chat_id"]), **padrao_args)


def _regiao_de(d: Mapping[str, Any]) -> Regiao:
    nome = str(d.get("nome", "")).strip()
    rotulo = f"[[regiao]] '{nome or '?'}'"
    _somente_chaves(d, {"nome", "rect", "modo", "regra"}, rotulo)
    if "rect" not in d:
        raise ErroConfig(f"{rotulo}: falta rect = [x, y, largura, altura]")
    try:
        return Regiao(
            nome=nome,
            rect=Retangulo.de_lista(d["rect"]),
            regras=tuple(_regra_de(r, rotulo) for r in _lista(d, "regra")),
            modo=str(d["modo"]) if "modo" in d else None,
        )
    except (ValueError, TypeError) as erro:
        raise ErroConfig(f"{rotulo}: {erro}") from erro


def _regra_de(d: Mapping[str, Any], rotulo_regiao: str) -> Regra:
    rotulo = f"{rotulo_regiao} regra '{d.get('significado', '?')}'"
    _somente_chaves(
        d,
        {"cor", "significado", "tolerancia", "cobertura_min", "mensagem", "notificar"},
        rotulo,
    )
    for obrigatoria in ("cor", "significado"):
        if obrigatoria not in d:
            raise ErroConfig(f"{rotulo}: falta '{obrigatoria}'")
    padrao = Regra(cor=Cor(0, 0, 0), significado="_")
    try:
        return Regra(
            cor=Cor.de_hex(str(d["cor"])),
            significado=str(d["significado"]),
            tolerancia=float(d.get("tolerancia", padrao.tolerancia)),
            cobertura_min=float(d.get("cobertura_min", padrao.cobertura_min)),
            mensagem=str(d["mensagem"]) if "mensagem" in d else None,
            notificar=bool(d.get("notificar", padrao.notificar)),
        )
    except (ValueError, TypeError) as erro:
        raise ErroConfig(f"{rotulo}: {erro}") from erro


def _secao(dados: Mapping[str, Any], chave: str) -> Mapping[str, Any]:
    valor = dados.get(chave, {})
    if not isinstance(valor, Mapping):
        raise ErroConfig(f"[{chave}] deve ser uma tabela")
    return valor


def _lista(dados: Mapping[str, Any], chave: str) -> list[Mapping[str, Any]]:
    valor = dados.get(chave, [])
    if not isinstance(valor, list) or not all(isinstance(v, Mapping) for v in valor):
        raise ErroConfig(f"[[{chave}]] deve ser uma lista de tabelas")
    return valor


def _somente_chaves(d: Mapping[str, Any], permitidas: set[str], rotulo: str) -> None:
    desconhecidas = sorted(set(d) - permitidas)
    if desconhecidas:
        raise ErroConfig(f"{rotulo}: chave(s) desconhecida(s): {', '.join(desconhecidas)}")


# --- modelos -> TOML -------------------------------------------------------


def _dict_de(config: Config) -> dict[str, Any]:
    saida: dict[str, Any] = {
        "geral": {
            "intervalo_s": config.geral.intervalo_s,
            "debounce_amostras": config.geral.debounce_amostras,
            "cooldown_s": config.geral.cooldown_s,
            "estado_desconhecido_notifica": config.geral.estado_desconhecido_notifica,
        },
        "leitura": {"modo": config.leitura.modo, "grade": list(config.leitura.grade)},
    }
    if config.telegram is not None:
        saida["notificador"] = {
            "telegram": {
                "chat_id": config.telegram.chat_id,
                "mensagem_padrao": config.telegram.mensagem_padrao,
                "token_env": config.telegram.token_env,
            }
        }
    saida["regiao"] = [_dict_de_regiao(r) for r in config.regioes]
    return saida


def _dict_de_regiao(regiao: Regiao) -> dict[str, Any]:
    d: dict[str, Any] = {"nome": regiao.nome, "rect": regiao.rect.como_lista()}
    if regiao.modo is not None:
        d["modo"] = regiao.modo
    d["regra"] = [_dict_de_regra(r) for r in regiao.regras]
    return d


def _dict_de_regra(regra: Regra) -> dict[str, Any]:
    d: dict[str, Any] = {
        "cor": regra.cor.hex,
        "significado": regra.significado,
        "tolerancia": regra.tolerancia,
        "cobertura_min": regra.cobertura_min,
        "notificar": regra.notificar,
    }
    if regra.mensagem is not None:
        d["mensagem"] = regra.mensagem
    return d
