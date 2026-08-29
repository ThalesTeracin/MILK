"""
Condicionamento do audio antes do Whisper.

O array de microfones desta maquina entrega a fala debaixo de ruido de
banda larga. Medido contra third_party/whisper.cpp/samples/jfk.wav, que o
mesmo binario e o mesmo modelo transcrevem sem errar uma palavra:

                  0-200   200-500  500-1k   1k-2k   2k-4k   4k-8k
    jfk            1.1%     7.0%    34.0%   40.6%   16.1%    1.2%
    microfone     14.8%    15.9%    12.3%   11.9%   18.6%   26.5%

A fala vive entre 500 Hz e 2 kHz: 75% da energia na referencia contra 24%
no microfone. O resto e ronco embaixo e chiado em cima, e com ele o
Whisper devolvia legenda de ruido ("[MUSICA DE FUNDO]", "[GRITOS DE
GOL]") em vez de palavras. Reduzir ruido pelo ffmpeg no mesmo audio
mudava a transcricao de "Nao te paixas de teus, fas" para "Nao precisa de
ter o que fazer" -- de nada para quase. Este modulo faz esse
condicionamento em numpy, sem depender do ffmpeg em tempo de execucao.

A reducao de taxa tambem mora aqui, com o filtro anti-alias que faltava:
o listener decimava 48 kHz para 16 kHz interpolando e mais nada, e tudo
acima de 8 kHz dobrava para dentro da faixa da fala.
"""

import numpy as np

TAXA_ALVO = 16000

# Ordem impar em todos os filtros: fase linear e atraso inteiro, entao a
# fala nao sai deslocada de meia amostra em relacao a si mesma.
_ORDEM = 127

# 7,5 kHz deixa a banda util inteira passar com folga ate o limite de
# Nyquist da taxa alvo (8 kHz), sem deixar a transicao do filtro chegar
# la e dobrar.
CORTE_ANTIALIAS = 7500.0

# 100 Hz fica abaixo da fundamental de qualquer voz e acima do ronco de
# ventoinha e mesa, que nesta maquina carrega 15% da energia.
CORTE_RONCO = 100.0


def _janela_sinc(corte_normalizado, ordem=_ORDEM):
    """Passa-baixa por sinc janelado. corte_normalizado = corte / taxa."""
    k = np.arange(ordem) - (ordem - 1) / 2
    h = 2 * corte_normalizado * np.sinc(2 * corte_normalizado * k) * np.hamming(ordem)
    return (h / h.sum()).astype(np.float32)


def passa_baixa(x, taxa, corte):
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == 0 or corte >= taxa / 2:
        return x
    return np.convolve(x, _janela_sinc(corte / taxa), mode="same").astype(np.float32)


def passa_alta(x, taxa, corte=CORTE_RONCO):
    """Tira o ronco: o sinal menos a sua propria parte grave."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == 0 or corte <= 0:
        return x
    return (x - passa_baixa(x, taxa, corte)).astype(np.float32)


def reduzir_taxa(x, taxa_origem, taxa_destino=TAXA_ALVO):
    """Reduz a taxa filtrando antes, para o agudo nao dobrar para dentro."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == 0:
        return np.array([], dtype=np.int16)
    if taxa_origem == taxa_destino:
        return np.clip(x, -32768, 32767).astype(np.int16)

    if taxa_origem > taxa_destino:
        corte = min(CORTE_ANTIALIAS, taxa_destino / 2 * 0.94)
        x = passa_baixa(x, taxa_origem, corte)

    tamanho = max(1, int(len(x) * taxa_destino / taxa_origem))
    y = np.interp(
        np.linspace(0, len(x) - 1, tamanho, dtype=np.float32),
        np.arange(len(x), dtype=np.float32),
        x,
    )
    return np.clip(y, -32768, 32767).astype(np.int16)


def subtrair_ruido(x, ruido, taxa, fator=1.5, piso=0.12):
    """
    Subtracao espectral: tira do sinal o perfil medio do ruido medido.

    `ruido` sai dos blocos que o listener grava antes de a fala comecar e
    ja descartava. O `piso` guarda uma fracao do original em cada faixa,
    porque zerar bin cria o chiado metalico que atrapalha mais do que o
    ruido original.
    """
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if ruido is None or len(x) == 0:
        return x

    ruido = np.asarray(ruido, dtype=np.float32).reshape(-1)
    janela = 512
    if len(ruido) < janela:
        return x

    perfil = np.zeros(janela // 2 + 1, dtype=np.float64)
    quadros = 0
    for inicio in range(0, len(ruido) - janela + 1, janela):
        perfil += np.abs(np.fft.rfft(ruido[inicio:inicio + janela] * np.hanning(janela)))
        quadros += 1
    if quadros == 0:
        return x
    perfil /= quadros

    salto = janela // 2
    janela_h = np.hanning(janela).astype(np.float32)
    saida = np.zeros(len(x) + janela, dtype=np.float32)
    peso = np.zeros(len(x) + janela, dtype=np.float32)

    for inicio in range(0, len(x), salto):
        quadro = np.zeros(janela, dtype=np.float32)
        pedaco = x[inicio:inicio + janela]
        quadro[:len(pedaco)] = pedaco
        espectro = np.fft.rfft(quadro * janela_h)

        magnitude = np.abs(espectro)
        limpa = np.maximum(magnitude - fator * perfil, piso * magnitude)
        fase = np.exp(1j * np.angle(espectro))

        recomposto = np.fft.irfft(limpa * fase, n=janela).astype(np.float32)
        saida[inicio:inicio + janela] += recomposto * janela_h
        peso[inicio:inicio + janela] += janela_h ** 2

    peso[peso < 1e-6] = 1.0
    return (saida[:len(x)] / peso[:len(x)]).astype(np.float32)


def normalizar(x, pico_alvo=26000.0):
    """Deixa o pico numa altura util, com folga para nao encostar no teto."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == 0:
        return x
    pico = float(np.abs(x).max())
    if pico < 1.0:
        return x
    return (x * (pico_alvo / pico)).astype(np.float32)


def condicionar(x, taxa_origem, ruido=None):
    """Cadeia inteira: ronco fora, ruido fora, taxa reduzida, nivel util."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == 0:
        return np.array([], dtype=np.int16)

    x = passa_alta(x, taxa_origem)
    if ruido is not None:
        x = subtrair_ruido(x, passa_alta(ruido, taxa_origem), taxa_origem)
    x = normalizar(x)
    return reduzir_taxa(x, taxa_origem)
