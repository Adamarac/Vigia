"""Configuração: modelos validados e persistência em TOML."""

from vigia.config.modelos import Config, ConfigGeral, ConfigLeitura, ConfigTelegram
from vigia.config.repositorio_toml import ErroConfig, RepositorioConfig, RepositorioToml

__all__ = [
    "Config",
    "ConfigGeral",
    "ConfigLeitura",
    "ConfigTelegram",
    "ErroConfig",
    "RepositorioConfig",
    "RepositorioToml",
]
