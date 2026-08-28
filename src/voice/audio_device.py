"""
Qual microfone o MILK deve abrir.

Selecionar_Microfone.py grava o indice escolhido em
config/local/audio_device.json. Este modulo e o unico leitor desse
arquivo: qualquer problema nele -- ausente, corrompido, com valor de
outro tipo -- cai no dispositivo padrao do sistema em vez de impedir o
MILK de ouvir.

O indice 0 conta como "nao configurado": e o valor que vem de
config/audio_device.example.json, e a mesma convencao que
installer/INSTALAR.ps1 usa para decidir se pergunta o microfone.
"""

import json

from core.config import config_path

ARQUIVO = "audio_device.json"


def indice_de_entrada():
    """Devolve o indice do microfone, ou None para o padrao do sistema."""
    caminho = config_path(ARQUIVO)
    if not caminho.exists():
        return None

    try:
        # utf-8-sig: o mesmo que listener.py usa, porque editores do
        # Windows acrescentam BOM ao salvar.
        cfg = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"⚠️ {ARQUIVO} ilegível ({type(e).__name__}: {e}); usando o microfone padrão.")
        return None

    valor = cfg.get("input_device") if isinstance(cfg, dict) else None
    if valor is None:
        return None

    # bool e subclasse de int e passaria pelo isinstance sem isso.
    if isinstance(valor, bool) or not isinstance(valor, int):
        print(f"⚠️ input_device em {ARQUIVO} não é um índice inteiro; usando o microfone padrão.")
        return None

    if valor == 0:
        return None

    return valor
