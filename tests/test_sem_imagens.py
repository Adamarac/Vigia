"""Guarda de arquitetura: o pacote não pode criar, gravar ou enviar imagens."""

from pathlib import Path

PACOTE = Path(__file__).resolve().parent.parent / "src" / "vigia"
PROIBIDOS = (
    "PIL",
    "cv2",
    "imageio",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    "imwrite",
    ".save(",
    "sendPhoto",
)


def test_pacote_nao_tem_rastro_de_imagem():
    arquivos = list(PACOTE.rglob("*.py"))
    assert arquivos, "pacote não encontrado"
    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        for termo in PROIBIDOS:
            assert termo not in texto, f"{arquivo.relative_to(PACOTE)} contém '{termo}'"


def test_dependencias_nao_incluem_bibliotecas_de_imagem():
    pyproject = (PACOTE.parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    for proibida in ("pillow", "opencv", "imageio", "numpy"):
        assert proibida not in pyproject.lower()
