# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Qual microfone a Milk usa.

O padrão do Windows nem sempre é o que está ouvindo. Nesta máquina, por
exemplo, o microfone interno entrega silêncio e o fone entrega som — e
o Windows continua apontando para o interno.

Por isso a Milk escolhe o dela, em vez de aceitar o padrão do sistema:

    config/settings.json -> microfone.dispositivo   pedaço do nome
                            microfone.api           API preferida

Com `"auto"` (o padrão), ela procura sozinha uma entrada que esteja
captando de verdade, testando cada uma por meio segundo.

O nome é guardado como texto, não como número: o índice muda quando um
aparelho é conectado ou desconectado, o nome não.
"""

import numpy as np
import sounddevice as sd

from milk.core.log import logger, registrar_erro
from milk.core.settings import obter


# Quando duas entradas servem, esta é a ordem de preferência.
ORDEM_DAS_APIS = (
    "Windows WASAPI",
    "MME",
    "Windows DirectSound",
    "Windows WDM-KS",
)

# Abaixo disso, o que chega é silêncio de sala, não voz.
PICO_MINIMO = 200

SEGUNDOS_DE_TESTE = 0.5


class Entrada:
    """Um microfone utilizável, com o que a gravação precisa saber."""

    def __init__(self, indice, nome, api, taxa, canais):
        self.indice = indice
        self.nome = nome
        self.api = api
        self.taxa = taxa
        self.canais = canais

    def __repr__(self):
        return f"<Entrada {self.indice} {self.nome} ({self.api})>"


def listar_entradas():
    """Todos os microfones que o sistema oferece."""

    entradas = []

    try:
        dispositivos = sd.query_devices()

    except Exception as erro:
        registrar_erro("voice", "não consegui listar os microfones", erro)

        return entradas

    for indice, aparelho in enumerate(dispositivos):
        if aparelho.get("max_input_channels", 0) < 1:
            continue

        try:
            api = sd.query_hostapis(aparelho["hostapi"])["name"]

        except Exception:
            api = ""

        entradas.append(
            Entrada(
                indice,
                str(aparelho.get("name", "")),
                api,
                int(aparelho.get("default_samplerate") or 44100),
                min(int(aparelho.get("max_input_channels", 1)), 2),
            )
        )

    return entradas


def peso_da_api(entrada):
    try:
        return ORDEM_DAS_APIS.index(entrada.api)

    except ValueError:
        return len(ORDEM_DAS_APIS)


def combinam(entrada, pedaco):
    return pedaco.lower() in entrada.nome.lower()


def entrada_padrao_do_sistema():
    """A entrada que o Windows considera padrão, se houver."""

    try:
        indice = sd.default.device[0]

        if indice is None or indice < 0:
            return None

        aparelho = sd.query_devices(indice)

        api = sd.query_hostapis(aparelho["hostapi"])["name"]

        return Entrada(
            indice,
            str(aparelho.get("name", "")),
            api,
            int(aparelho.get("default_samplerate") or 44100),
            min(int(aparelho.get("max_input_channels", 1)), 2),
        )

    except Exception:
        return None


def medir(entrada, segundos=SEGUNDOS_DE_TESTE):
    """Grava um pouco e devolve (pico, rms). (-1, -1) se nem abriu."""

    try:
        audio = sd.rec(
            int(segundos * entrada.taxa),
            samplerate=entrada.taxa,
            channels=entrada.canais,
            dtype="int16",
            device=entrada.indice,
        )

        sd.wait()

    except Exception:
        return -1, -1.0

    amostras = np.asarray(audio, dtype=np.int16).reshape(-1)

    if amostras.size == 0:
        return 0, 0.0

    pico = int(np.max(np.abs(amostras)))

    rms = float(
        np.sqrt(
            np.mean(amostras.astype(np.float32) ** 2)
        )
    )

    return pico, rms


def procurar_quem_ouve(entradas=None, segundos=SEGUNDOS_DE_TESTE):
    """Testa as entradas e devolve a que está captando de forma mais confiável.

    Cada dispositivo é testado em até 3 tentativas rápidas; a Milk escolhe
    aquele que deu o pico mais alto em alguma das tentativas (em vez de
    confiar na primeira medição, que às vezes dá silêncio por puro azar).
    Quando nada capta, devolve None — o código then tenta o padrão do sistema.
    """

    entradas = entradas if entradas is not None else listar_entradas()

    if not entradas:
        return None

    # Dispositivos com nomes mais específicos (ex: "Grupo de Microfones
    # Qualcomm") são preferidos por cair antes no sort por peso da API.
    candidatas = sorted(entradas, key=peso_da_api)

    melhor = None           # Entrada com o melhor pico encontrado
    melhor_pico = 0

    for entrada in candidatas:
        # Testa em até 3 tentativas rápidas
        pico_max = 0
        for _tentativa in range(3):
            pico, _ = medir(entrada, segundos)
            if pico > pico_max:
                pico_max = pico
            if pico_max >= 2000:
                # Já achou um pico longe de silêncio — não precisa testar
                # mais de uma vez neste dispositivo: ele é bom o suficiente.
                break

        if pico_max > melhor_pico:
            melhor_pico = pico_max
            melhor = entrada

        # Se achou um pico bom o suficiente, para de procurar.
        if pico_max >= 2000:
            return entrada

    # Nada com pico ≥ 2000, mas pode haver algo com pico moderado
    # (ex: sussurro). Se o melhor pico foi ≥ 50, usa ele.
    if melhor_pico >= 50:
        return melhor

    return None


def dispositivo_pedido():
    """O nome pedido no settings.json, ou "" quando está em automático."""

    pedido = str(
        obter("microfone", "dispositivo", "auto") or ""
    ).strip()

    return "" if pedido.lower() in ("", "auto") else pedido


def escolher(entradas=None, procurar=procurar_quem_ouve):
    """O microfone que a Milk vai usar agora.

    1. o nome pedido no settings.json, na API preferida;
    2. com `auto`, o primeiro que estiver captando de verdade;
    3. se nada disso der, o padrão do Windows."""

    entradas = entradas if entradas is not None else listar_entradas()

    pedido = str(
        obter("microfone", "dispositivo", "auto") or "auto"
    ).strip()

    api_pedida = str(
        obter("microfone", "api", "") or ""
    ).strip()

    if pedido and pedido.lower() != "auto":
        combinando = [
            entrada
            for entrada in entradas
            if combinam(entrada, pedido)
        ]

        if api_pedida:
            preferidas = [
                entrada
                for entrada in combinando
                if entrada.api.lower() == api_pedida.lower()
            ]

            if preferidas:
                return preferidas[0]

        if combinando:
            return sorted(combinando, key=peso_da_api)[0]

        logger("voice").warning(
            f"não achei o microfone '{pedido}'; procurando outro"
        )

    achada = procurar(entradas)

    if achada is not None:
        return achada

    return entrada_padrao_do_sistema()


def descrever(entrada):
    if entrada is None:
        return "nenhum microfone"

    return f"{entrada.nome} ({entrada.api})"
