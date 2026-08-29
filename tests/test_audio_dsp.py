"""
Testes de src/voice/audio_dsp.py.

O condicionamento existe porque o array de microfones desta maquina
entrega a fala debaixo de ruido de banda larga. Medido contra o
samples/jfk.wav, que o mesmo Whisper transcreve perfeito:

                  0-200   200-500  500-1k   1k-2k   2k-4k   4k-8k
    jfk            1.1%     7.0%    34.0%   40.6%   16.1%    1.2%
    microfone     14.8%    15.9%    12.3%   11.9%   18.6%   26.5%

A fala vive entre 500 Hz e 2 kHz: 75% da energia na referencia, 24% no
microfone. O resto e ronco embaixo e chiado em cima.
"""
import numpy as np
import pytest

from voice.audio_dsp import condicionar, passa_alta, reduzir_taxa, subtrair_ruido


def tom(hz, segundos, taxa, amplitude=8000.0):
    t = np.arange(int(segundos * taxa), dtype=np.float32) / taxa
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def energia_em(x, taxa, lo, hi):
    X = np.abs(np.fft.rfft(x.astype(np.float64) * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / taxa)
    return float(X[(f >= lo) & (f < hi)].sum())


# ------------------------------------------------- reducao de taxa

def test_reduzir_taxa_devolve_o_numero_certo_de_amostras():
    x = tom(1000, 1.0, 48000)

    y = reduzir_taxa(x, 48000)

    assert abs(len(y) - 16000) <= 1


def test_reduzir_taxa_preserva_tom_dentro_da_banda():
    y = reduzir_taxa(tom(1000, 0.5, 48000), 48000)

    dentro = energia_em(y, 16000, 800, 1200)
    fora = energia_em(y, 16000, 2000, 8000)
    assert dentro > fora * 10


def test_reduzir_taxa_nao_dobra_o_agudo_para_dentro_da_banda():
    """
    O defeito que este modulo tira do listener: decimar 48 kHz para
    16 kHz sem passa-baixa dobra tudo acima de 8 kHz para dentro da faixa
    da fala. Um tom de 12 kHz vira 4 kHz -- ruido no meio das consoantes,
    e nenhum aviso.

    A medida e a imagem contra a fala que tem de sobreviver, nao contra o
    total: com entrada de tom puro tudo o que resta depois do filtro e a
    propria imagem, e a razao daria 1 por construcao.
    """
    x = tom(1000, 0.5, 48000) + tom(12000, 0.5, 48000)

    y = reduzir_taxa(x, 48000)

    fala = energia_em(y, 16000, 800, 1200)
    imagem = energia_em(y, 16000, 3500, 4500)
    assert imagem < fala * 0.02


def test_reduzir_taxa_dobra_menos_que_a_interpolacao_crua():
    """A comparacao direta com o que o listener fazia antes."""
    x = tom(1000, 0.5, 48000) + tom(12000, 0.5, 48000)

    tamanho = int(len(x) * 16000 / 48000)
    cru = np.interp(
        np.linspace(0, len(x) - 1, tamanho, dtype=np.float32),
        np.arange(len(x), dtype=np.float32),
        x,
    )

    imagem_crua = energia_em(cru, 16000, 3500, 4500)
    imagem_filtrada = energia_em(reduzir_taxa(x, 48000), 16000, 3500, 4500)
    assert imagem_filtrada < imagem_crua * 0.05


def test_reduzir_taxa_de_16k_nao_mexe_no_sinal():
    x = tom(1000, 0.2, 16000)

    assert np.array_equal(reduzir_taxa(x, 16000), x.astype(np.int16))


def test_reduzir_taxa_aceita_audio_vazio():
    assert len(reduzir_taxa(np.array([], dtype=np.float32), 48000)) == 0


# ------------------------------------------------- passa-alta

def test_passa_alta_tira_o_ronco_e_mantem_a_fala():
    x = tom(50, 0.5, 16000) + tom(1000, 0.5, 16000)

    y = passa_alta(x, 16000, 100)

    assert energia_em(y, 16000, 30, 80) < energia_em(x, 16000, 30, 80) * 0.2
    assert energia_em(y, 16000, 900, 1100) > energia_em(x, 16000, 900, 1100) * 0.7


# ------------------------------------------------- subtracao de ruido

def test_subtrair_ruido_derruba_o_chiado_e_preserva_o_tom():
    rng = np.random.default_rng(7)
    ruido = (rng.normal(0, 600, 16000)).astype(np.float32)
    fala = tom(1000, 1.0, 16000) + (rng.normal(0, 600, 16000)).astype(np.float32)

    y = subtrair_ruido(fala, ruido, 16000)

    assert energia_em(y, 16000, 3000, 8000) < energia_em(fala, 16000, 3000, 8000) * 0.6
    assert energia_em(y, 16000, 900, 1100) > energia_em(fala, 16000, 900, 1100) * 0.5


def test_subtrair_ruido_sem_referencia_devolve_o_sinal():
    x = tom(1000, 0.2, 16000)

    assert np.allclose(subtrair_ruido(x, None, 16000), x)


def test_subtrair_ruido_com_referencia_curta_demais_nao_explode():
    x = tom(1000, 0.2, 16000)

    y = subtrair_ruido(x, np.zeros(8, dtype=np.float32), 16000)

    assert len(y) == len(x)


# ------------------------------------------------- cadeia inteira

def test_condicionar_devolve_int16_a_16k():
    x = tom(1000, 1.0, 48000)

    y = condicionar(x, 48000)

    assert y.dtype == np.int16
    assert abs(len(y) - 16000) <= 1


def test_condicionar_nao_satura():
    """
    Saturar foi o que quebrou o reconhecimento antes de a fase existir:
    picos no teto do int16 viram distorcao e o Whisper devolve legenda de
    ruido em vez de palavras.
    """
    x = tom(1000, 0.5, 48000, amplitude=32000.0)

    y = condicionar(x, 48000)

    assert int(np.abs(y).max()) < 32767


def test_condicionar_aceita_audio_vazio():
    y = condicionar(np.array([], dtype=np.float32), 48000)

    assert y.dtype == np.int16
    assert len(y) == 0
