# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Gera o Milk.exe.

    .venv\\Scripts\\python.exe construir_exe.py

O resultado fica em `dist\\Milk\\`, com o executável e tudo de que ele
precisa ao lado. Essa pasta é o que se copia para usar em outro lugar.

Três coisas acontecem aqui além de chamar o PyInstaller:

- o ícone é gerado a partir do PNG da Milk;
- as informações de versão (com o direito autoral de Thales Teracin) entram no
  executável e aparecem nas Propriedades do arquivo no Windows;
- assets, config, licença e manual são copiados para o lado do .exe,
  porque o programa usa a pasta onde ele está como base.
"""

import shutil
import subprocess
import sys

from pathlib import Path

BASE = Path(__file__).resolve().parent

DESTINO = BASE / "dist" / "Milk"

NOME = "Milk"

AUTOR = "Thales Teracin"

VERSAO = "1.0.0.0"


ICONE = BASE / "assets" / "milk.ico"

ARQUIVO_DE_VERSAO = BASE / "versao_exe.txt"


# O que precisa estar ao lado do executável.
#
# `.claude` entra porque é ele que desliga o plugin que deixa a fala da
# Milk telegráfica. Ela já passa a mesma configuração em `--settings`,
# mas sem o arquivo na pasta o Milk Doctor acusa a falta — e qualquer
# sessão aberta ali dentro voltaria a carregar o plugin.
JUNTO = (
    "assets",
    "config",
    ".claude",
    "LICENSE.txt",
    "README.md",
    "Manual da Milk.pdf",
    "milk_avatar.png",
)


def gerar_icone():
    """Um .ico com vários tamanhos, a partir do PNG da Milk."""

    from PIL import Image

    origem = BASE / "milk_avatar.png"

    if not origem.is_file():
        return None

    imagem = Image.open(origem).convert("RGBA")

    caixa = imagem.getbbox()

    if caixa:
        imagem = imagem.crop(caixa)

    lado = max(imagem.size)

    quadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))

    quadrado.paste(
        imagem,
        (
            (lado - imagem.width) // 2,
            (lado - imagem.height) // 2,
        ),
    )

    ICONE.parent.mkdir(parents=True, exist_ok=True)

    quadrado.save(
        ICONE,
        sizes=[
            (16, 16),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )

    return ICONE


def construir():
    comando = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        NOME,
        "--collect-submodules",
        "milk",
        "--hidden-import",
        "sounddevice",
        "--hidden-import",
        "speech_recognition",
        "--hidden-import",
        "edge_tts",
        "--hidden-import",
        "imageio_ffmpeg",
        str(BASE / "milk.py"),
    ]

    if ICONE.is_file():
        comando[6:6] = ["--icon", str(ICONE)]

    if ARQUIVO_DE_VERSAO.is_file():
        comando[6:6] = ["--version-file", str(ARQUIVO_DE_VERSAO)]

    return subprocess.run(comando, cwd=str(BASE)).returncode


def copiar_o_que_vai_junto():
    copiados = []

    for nome in JUNTO:
        origem = BASE / nome

        if not origem.exists():
            continue

        destino = DESTINO / nome

        if origem.is_dir():
            shutil.copytree(origem, destino, dirs_exist_ok=True)

        else:
            shutil.copy2(origem, destino)

        copiados.append(nome)

    return copiados


def main():
    print("gerando o ícone...")

    gerar_icone()

    print("empacotando (isso leva alguns minutos)...")

    codigo = construir()

    if codigo != 0:
        print("o PyInstaller terminou com erro.")

        return codigo

    print("copiando o que vai junto...")

    for nome in copiar_o_que_vai_junto():
        print("  +", nome)

    print()
    print("pronto:", DESTINO / f"{NOME}.exe")

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
