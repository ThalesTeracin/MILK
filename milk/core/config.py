# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Configurações da Milk.

Constantes de caminho, voz e microfone usadas por todos os módulos.
"""

import os
import sys
import json

from pathlib import Path


def _descobrir_base():
    """A pasta da Milk.

    Rodando pelo Python, e a pasta do projeto (dois niveis acima deste
    arquivo). Rodando pelo Milk.exe, e a pasta onde o executavel esta.
    Assim o programa funciona onde quer que ele seja colocado, sem
    caminho fixo no codigo."""

    if getattr(sys, "frozen", False):
        return os.path.dirname(
            os.path.abspath(sys.executable)
        )

    return str(
        Path(__file__).resolve().parents[2]
    )


BASE_DIR = _descobrir_base()

AVATAR_FILE = os.path.join(
    BASE_DIR,
    "milk_avatar.png"
)

# Quadros da Milk caminhando, quando existirem. Enquanto a pasta estiver
# vazia ela continua sendo o PNG parado com o balanco procedural.
# Aceita GIF/WEBP animado, folha de sprites ou quadros numerados.
ANDANDO_DIR = Path(BASE_DIR) / "assets" / "avatar"

# Efeito sonoro do latido. Este e o unico lugar do projeto que sabe
# onde o arquivo mora.
BARK_FILE = Path(BASE_DIR) / "assets" / "sounds" / "latido.wav"

VOICE_FILE = os.path.join(
    BASE_DIR,
    "milk_voice.mp3"
)

MIC_FILE = os.path.join(
    BASE_DIR,
    "milk_microfone.wav"
)

MIC_CONVERTED_FILE = os.path.join(
    BASE_DIR,
    "milk_microfone_convertido.wav"
)

VOICE_NAME = "pt-BR-FranciscaNeural"

VOICE_RATE = "-6%"
VOICE_PITCH = "+8Hz"

MIC_SECONDS = 7

PESSOA_FILE = os.path.join(
    BASE_DIR,
    "milk_pessoa.json"
)

TASKS_FILE = os.path.join(
    BASE_DIR,
    "milk_tarefas.json"
)

MEMORIA_FILE = os.path.join(
    BASE_DIR,
    "milk_memoria.json"
)

CONVERSA_FILE = os.path.join(
    BASE_DIR,
    "milk_conversa.json"
)

LOGS_DIR = Path(BASE_DIR) / "logs"

SETTINGS_FILE = os.path.join(
    BASE_DIR,
    "config",
    "settings.json"
)

DONO_NOME = "Thales"

BARK_TEXT = "Au au!"

# Ajustes aplicados só na sessão que a Milk abre, sem tocar na
# configuração global nem nas sessões que você usa nesta pasta.
# O plugin caveman impõe respostas telegráficas; a Milk fala inteiro.
CLAUDE_SETTINGS = json.dumps({
    "enabledPlugins": {
        "caveman@caveman": False,
    }
})
