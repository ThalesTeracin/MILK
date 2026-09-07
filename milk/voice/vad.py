# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Detecção de fala por energia.

O microfone entrega blocos de som o tempo todo. Quase todos são só o
barulho da sala. Este módulo decide quando começou uma fala e quando
ela terminou, para a Milk transcrever **só o trecho falado** — em vez
de gravar 7 segundos fixos e mandar tudo, inclusive o silêncio.

Como funciona: os primeiros blocos servem para medir o silêncio do
ambiente. A partir daí, bloco com energia bem acima desse piso é fala;
uma sequência de blocos de volta ao piso fecha a fala.

É proposital que seja simples. Não há modelo, não há rede e não há
dependência nova: roda em qualquer máquina, inclusive Windows ARM64,
e gasta quase nada de processador.
"""

import numpy as np


# Quantos blocos medem o silêncio da sala antes de começar a valer.
BLOCOS_DE_CALIBRACAO = 8

# A fala precisa ser este tanto de vezes mais forte que o silêncio.
FATOR_DE_FALA = 3.5

# Piso absoluto: sala muito silenciosa não vira gatilho de qualquer coisa.
PISO_MINIMO = 90.0

# Silêncio em segundos que fecha a fala. Cada décimo aqui é um décimo
# a mais de espera antes de ela começar a responder.
SILENCIO_PARA_FECHAR = 0.6

# Fala mais curta que isto é ruído (porta batendo, clique de mouse).
FALA_MINIMA = 0.35

# Ninguém fala um pedido de 30 segundos sem pausa.
FALA_MAXIMA = 15.0


class Detector:
    """Recebe blocos de áudio e diz quando uma fala começou e terminou.

    `alimentar()` devolve:

        None              nada mudou
        "comecou"         a fala começou neste bloco
        "falando"         segue falando
        numpy array       a fala terminou; é o trecho falado inteiro
    """

    def __init__(
        self,
        taxa,
        tamanho_do_bloco,
        fator=FATOR_DE_FALA,
        silencio_para_fechar=SILENCIO_PARA_FECHAR,
        fala_minima=FALA_MINIMA,
        fala_maxima=FALA_MAXIMA,
        piso_minimo=PISO_MINIMO,
    ):
        self.taxa = taxa
        self.tamanho_do_bloco = tamanho_do_bloco

        self.fator = fator
        self.piso_minimo = piso_minimo

        self.segundos_por_bloco = tamanho_do_bloco / float(taxa)

        self.blocos_de_silencio_para_fechar = max(
            1,
            int(silencio_para_fechar / self.segundos_por_bloco)
        )

        self.blocos_minimos = max(
            1,
            int(fala_minima / self.segundos_por_bloco)
        )

        self.blocos_maximos = max(
            2,
            int(fala_maxima / self.segundos_por_bloco)
        )

        self.piso = None
        self.medidas = []

        self.falando = False
        self.silencio_seguido = 0

        self.trecho = []

        # So os blocos com voz contam para o tamanho minimo. O silencio
        # do fim entra no audio, mas nao pode fazer um clique curto
        # parecer uma frase.
        self.blocos_com_fala = 0

    # --------------------------------------------------------

    def energia(self, bloco):
        """Volume médio do bloco (RMS)."""

        amostras = np.asarray(bloco, dtype=np.float32).reshape(-1)

        if amostras.size == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(amostras ** 2)
            )
        )

    def calibrando(self):
        return self.piso is None

    def limite(self):
        """A partir de que energia o bloco conta como fala."""

        if self.piso is None:
            return self.piso_minimo

        return max(
            self.piso * self.fator,
            self.piso_minimo,
        )

    def recalibrar(self):
        self.piso = None
        self.medidas = []

    def esquecer(self):
        """Joga fora o trecho em andamento, mantendo o piso da sala.

        É o que a escuta chama enquanto a Milk late ou fala: o áudio
        dela mesma não pode virar uma fala para transcrever."""

        self.trecho = []
        self.blocos_com_fala = 0
        self.falando = False
        self.silencio_seguido = 0

    # --------------------------------------------------------

    def alimentar(self, bloco):
        forca = self.energia(bloco)

        # Fase 1: medir o silêncio da sala.
        if self.piso is None:
            self.medidas.append(forca)

            if len(self.medidas) >= BLOCOS_DE_CALIBRACAO:
                # Mediana, para uma tossida no meio não estragar a medida.
                self.piso = float(
                    np.median(self.medidas)
                )

            return None

        # Fase 2: ouvir.
        if forca >= self.limite():
            self.silencio_seguido = 0

            self.trecho.append(
                np.asarray(bloco, dtype=np.int16).reshape(-1)
            )

            self.blocos_com_fala += 1

            if not self.falando:
                self.falando = True

                return "comecou"

            # Fala longa demais: fecha aqui mesmo.
            if len(self.trecho) >= self.blocos_maximos:
                return self.fechar()

            return "falando"

        if not self.falando:
            # Silêncio com silêncio: o piso vai se ajustando devagar.
            self.piso = (self.piso * 0.95) + (forca * 0.05)

            return None

        # Estava falando e agora não está.
        self.silencio_seguido += 1

        # O rabinho do silêncio entra no trecho: corta menos a última sílaba.
        self.trecho.append(
            np.asarray(bloco, dtype=np.int16).reshape(-1)
        )

        if self.silencio_seguido >= self.blocos_de_silencio_para_fechar:
            return self.fechar()

        return "falando"

    def fechar(self):
        """Fecha a fala e devolve o trecho, ou None se foi ruído curto."""

        blocos = self.trecho
        com_fala = self.blocos_com_fala

        self.trecho = []
        self.blocos_com_fala = 0
        self.falando = False
        self.silencio_seguido = 0

        if com_fala < self.blocos_minimos:
            return None

        return np.concatenate(blocos)
