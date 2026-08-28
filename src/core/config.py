"""
Resolve qual arquivo de configuração usar.

config/ é versionado e vem com a atualização. config/local/ é ignorado
pelo git e guarda o que pertence a ESTA máquina: índice do microfone,
caminhos absolutos do whisper. Sem essa separação, um git pull
sobrescreve a escolha de dispositivo do usuário.

Quem escreve configuração de máquina deve escrever sempre em
config/local/, nunca em config/.
"""

from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
LOCAL_DIR = CONFIG_DIR / "local"


def config_path(nome):
    """
    Devolve config/local/<nome> se existir, senão config/<nome>.

    O caminho devolvido pode não existir; cabe a quem chama tratar isso.
    """
    local = LOCAL_DIR / nome
    if local.exists():
        return local
    return CONFIG_DIR / nome
