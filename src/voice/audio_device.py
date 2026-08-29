"""
Qual microfone o MILK deve abrir.

Selecionar_Microfone.py grava a escolha em config/local/audio_device.json.
Este modulo e o unico leitor desse arquivo: qualquer problema nele --
ausente, corrompido, com valor de outro tipo -- cai no dispositivo padrao
do sistema em vez de impedir o MILK de ouvir.

O arquivo guarda o *nome* do microfone e a host API, e o indice do
PortAudio e resolvido na hora de abrir. Guardar o indice nao funciona:
ele e a posicao na lista do PortAudio, e conectar ou desconectar um fone
insere ou remove entradas e renumera tudo o que vem depois. Observado
nesta maquina, na mesma sessao, com o headset saindo da lista entre uma
enumeracao e outra:

    antes:  15 | Windows WASAPI | Grupo de Microfones (Qualcomm) | 48000
    depois: 15 | Windows WDM-KS | Headset ()                     |  8000

O indice continuava valido, so tinha passado a apontar para outro
aparelho, entao nada reclamava: o MILK abria o microfone errado e o
Whisper transcrevia ruido. Por nome isso vira um aviso explicito.

A host API entra no casamento porque o mesmo aparelho aparece sob varias
delas e elas nao sao intercambiaveis -- o WDM-KS desta maquina nem abre
em modo bloqueante ("Blocking API not supported yet").

Arquivo no formato antigo, so com "input_device", continua valendo: quem
ja tem um nao fica sem microfone ate rodar o Selecionar_Microfone.py de
novo. O indice 0 conta como "nao configurado": e o valor que vem de
config/audio_device.example.json, e a mesma convencao que
installer/INSTALAR.ps1 usa para decidir se pergunta o microfone.
"""

import json

from core.config import config_path

ARQUIVO = "audio_device.json"


def listar_entradas():
    """Devolve (indice, nome, host_api) de cada dispositivo de entrada.

    Isolado numa funcao para o teste trocar a enumeracao sem depender de
    haver placa de audio na maquina que roda a suite. O import do
    sounddevice fica aqui dentro: quem so le o arquivo nao paga o
    PortAudio.
    """
    import sounddevice as sd

    entradas = []
    for indice, dispositivo in enumerate(sd.query_devices()):
        if int(dispositivo.get("max_input_channels", 0)) <= 0:
            continue
        host = sd.query_hostapis(dispositivo["hostapi"])["name"]
        entradas.append((indice, dispositivo.get("name", ""), host))
    return entradas


def _resolver_por_nome(nome, host_api):
    """Indice atual do microfone salvo, ou None para o padrao do sistema."""
    try:
        entradas = listar_entradas()
    except Exception as e:
        print(
            f"⚠️ não consegui listar os microfones ({type(e).__name__}: {e}); "
            "usando o microfone padrão."
        )
        return None

    for indice, nome_atual, host_atual in entradas:
        if nome_atual == nome and (host_api is None or host_atual == host_api):
            return indice

    alvo = nome if host_api is None else f"{nome} ({host_api})"
    print(
        f"⚠️ o microfone escolhido não está presente: {alvo}; "
        "usando o microfone padrão."
    )
    return None


def _texto(valor):
    """Devolve a string util, ou None se o campo nao for texto de verdade."""
    if isinstance(valor, str) and valor.strip():
        return valor
    return None


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

    if not isinstance(cfg, dict):
        return None

    nome = _texto(cfg.get("input_name"))
    if nome:
        return _resolver_por_nome(nome, _texto(cfg.get("input_hostapi")))

    # Formato antigo: so o indice, sem nada que permita conferir se ele
    # ainda aponta para o aparelho certo. Vale, mas e o caso que a
    # correcao existe para aposentar.
    valor = cfg.get("input_device")
    if valor is None:
        return None

    # bool e subclasse de int e passaria pelo isinstance sem isso.
    if isinstance(valor, bool) or not isinstance(valor, int):
        print(f"⚠️ input_device em {ARQUIVO} não é um índice inteiro; usando o microfone padrão.")
        return None

    if valor == 0:
        return None

    return valor
