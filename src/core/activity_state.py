"""
Dono unico do estado de atividade da MILK.

Ate a fase 33 havia duas verdades sobre o que a MILK estava fazendo:
MilkCore.activity, em memoria, que movia o overlay grande; e
data/milk_runtime_state.json, lido pelo mini overlay -- que ninguem nunca
escrevia. O mini mostrava o estado padrao para sempre.

Agora ha um dono so. Ele guarda em memoria para quem esta no mesmo
processo (o overlay grande le a 120 ms e nao pode tocar disco nessa
frequencia) e publica no arquivo para o mini overlay, que roda em outro
processo.

O carimbo de tempo existe porque o arquivo sobrevive ao processo. Sem ele,
com a MILK fechada o mini mostraria "pensando" para sempre. Quem le decide
o que fazer com estado velho; este modulo so diz se e fresco.

Este modulo fica em core/ e nao em avatar/ porque quem escreve e o
MilkCore, e o cerebro nao deve importar de um pacote de interface.
"""

import json
import threading
import time
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[2] / "data" / "milk_runtime_state.json"

ATIVIDADES = ("idle", "listening", "thinking", "speaking")
PADRAO = "idle"

# Cinco segundos: o UnifiedApp chama pulsar() de segundo em segundo, entao
# cinco pulsos podem se perder antes de o mini declarar a MILK morta.
LIMITE_DE_FRESCOR = 5.0

# RLock permite que a mesma thread adquira o lock múltiplas vezes sem deadlock.
# Isso é crucial porque pulsar() chama atividade() (que entra no lock) e depois
# _gravar() (que também está sob lock). Com Lock comum seria deadlock. Com RLock,
# serializa corretamente sem complexidade adicional. A propriedade invariante é:
# o par (atividade, carimbo) publicado no arquivo nunca diverge da memória.
_LOCK = threading.RLock()
_atividade = PADRAO


def definir_atividade(nome):
    """Muda a atividade e publica. Recusa nome fora de ATIVIDADES."""
    global _atividade
    if nome not in ATIVIDADES:
        raise ValueError(f"atividade desconhecida: {nome!r}")
    with _LOCK:
        _atividade = nome
        _gravar(nome)


def atividade():
    """O valor em memoria. Para quem esta no mesmo processo."""
    with _LOCK:
        return _atividade


def pulsar():
    """Regrava o carimbo sem mudar a atividade.

    A atividade so e escrita quando muda. Com a MILK parada ouvindo, o
    carimbo envelheceria e o mini a declararia desligada enquanto ela esta
    viva.
    """
    with _LOCK:
        _gravar(_atividade)


def ler_do_arquivo(agora=None):
    """
    Devolve (atividade, fresco). Para quem esta em OUTRO processo.

    Devolve (PADRAO, False) quando o arquivo nao existe, esta corrompido,
    tem formato inesperado ou traz atividade que este modulo nao conhece.
    """
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        nome = dados["activity"]
        carimbo = float(dados["at"])
    except Exception:
        return (PADRAO, False)

    if nome not in ATIVIDADES:
        return (PADRAO, False)

    agora = time.time() if agora is None else agora
    return (nome, (agora - carimbo) <= LIMITE_DE_FRESCOR)


def _gravar(nome):
    """Publica no arquivo. Falhar aqui nunca pode derrubar a MILK."""
    try:
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO.write_text(
            json.dumps({"activity": nome, "at": time.time()}),
            encoding="utf-8",
        )
    except Exception as e:
        print(
            f"⚠️ MILK: não consegui publicar o estado em {ARQUIVO} "
            f"({type(e).__name__}: {e}); o mini overlay pode ficar parado."
        )
