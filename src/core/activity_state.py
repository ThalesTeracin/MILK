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
import os
import threading
import time
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[2] / "data" / "milk_runtime_state.json"

ATIVIDADES = ("idle", "listening", "thinking", "speaking")
PADRAO = "idle"

# Cinco segundos: o UnifiedApp chama pulsar() de segundo em segundo, entao
# cinco pulsos podem se perder antes de o mini declarar a MILK morta.
LIMITE_DE_FRESCOR = 5.0

# Escrita e leitura do mesmo arquivo, de processos diferentes, colidem no
# Windows durante a troca de nome. Tres tentativas com pausa curta cobrem a
# janela sem segurar ninguem: o pior caso soma 10 ms.
TENTATIVAS_DE_ACESSO = 3
PAUSA_ENTRE_TENTATIVAS = 0.005

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

    Tenta mais de uma vez porque a troca de nome do escritor e o Windows
    nao convivem bem: durante o `os.replace` o caminho fica indisponivel
    por instantes, e uma leitura unica traduziria isso em "DESLIGADA" com
    a MILK viva.
    """
    dados = None
    for tentativa in range(TENTATIVAS_DE_ACESSO):
        try:
            dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
            break
        except Exception:
            if tentativa + 1 < TENTATIVAS_DE_ACESSO:
                time.sleep(PAUSA_ENTRE_TENTATIVAS)
    if dados is None:
        return (PADRAO, False)

    try:
        nome = dados["activity"]
        carimbo = float(dados["at"])
    except Exception:
        return (PADRAO, False)

    if nome not in ATIVIDADES:
        return (PADRAO, False)

    agora = time.time() if agora is None else agora
    return (nome, (agora - carimbo) <= LIMITE_DE_FRESCOR)


def _gravar(nome):
    """Publica no arquivo. Falhar aqui nunca pode derrubar a MILK.

    Grava num arquivo ao lado e renomeia por cima. `write_text` trunca o
    arquivo antes de escrever, e o mini overlay le de outro processo a cada
    150 ms: medido, metade das leituras concorrentes pegava o arquivo pela
    metade, caia no `except` de `ler_do_arquivo` e virava "DESLIGADA" com a
    MILK viva. `os.replace` troca o nome de uma vez, entao o leitor ve o
    conteudo antigo ou o novo, nunca um meio.
    """
    temporario = None
    try:
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        temporario = ARQUIVO.with_name(f"{ARQUIVO.name}.{os.getpid()}.tmp")
        temporario.write_text(
            json.dumps({"activity": nome, "at": time.time()}),
            encoding="utf-8",
        )
        # O Windows recusa a troca enquanto o leitor tem o arquivo aberto.
        # Sao microssegundos; tentar de novo custa menos que perder o pulso.
        for tentativa in range(TENTATIVAS_DE_ACESSO):
            try:
                os.replace(temporario, ARQUIVO)
                break
            except PermissionError:
                if tentativa + 1 == TENTATIVAS_DE_ACESSO:
                    raise
                time.sleep(PAUSA_ENTRE_TENTATIVAS)
    except Exception as e:
        # Sem isto, cada troca recusada deixaria um .tmp para tras em data/.
        try:
            if temporario is not None:
                temporario.unlink(missing_ok=True)
        except Exception:
            pass
        print(
            f"⚠️ MILK: não consegui publicar o estado em {ARQUIVO} "
            f"({type(e).__name__}: {e}); o mini overlay pode ficar parado."
        )
