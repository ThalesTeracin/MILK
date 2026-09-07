# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Escuta contínua com a palavra "Milk" (Fases 4 e 5).

O botão "🎤 Falar" grava 7 segundos fixos. Isto aqui é outra coisa: a
Milk fica ouvindo a sala, percebe quando alguém falou, transcreve só
aquele trecho e, **se o nome dela aparecer na fala**, atende.

O nome vale em qualquer lugar da frase. Em português a gente chama pelo
nome no fim tanto quanto no começo — "fecha o navegador para mim, Milk"
—, e exigir o nome na frente era o que fazia parecer que ela não
atendia. Sem o nome, a fala é descartada e nada aparece na conversa — a
não ser nos segundos seguintes a um atendimento, quando ela continua
ouvindo você sem exigir o nome de novo. É o mesmo que acontece com uma
pessoa: você chama uma vez e continua a conversa.

Enquanto ela late ou fala, o ouvido fica fechado (`surdear()`). Sem
isso a própria voz dela entra pelo microfone e, como a janela de
conversa está aberta, ela responderia a si mesma.

Duas escolhas importantes:

- **Nada de modelo local de wake word.** Esta máquina é Windows ARM64,
  onde `torch`, `vosk` e afins não têm roda. O gatilho é o próprio
  reconhecimento que já funciona, aplicado só aos trechos com fala.
- **Só sai da máquina o que tem fala.** O detector de energia
  (`milk/voice/vad.py`) segura o silêncio aqui dentro, então a sala
  não fica sendo enviada para lugar nenhum.

O microfone e a transcrição entram por argumento, então dá para testar
esta classe inteira sem microfone e sem internet.
"""

import re

import numpy as np

from PySide6.QtCore import QThread, Signal

from milk.core.log import logger, registrar_erro
from milk.voice import transcricao as transcricao_padrao
from milk.voice.vad import Detector


# "Milk" como o reconhecimento costuma ouvir, **em qualquer lugar da
# frase**. Chamar pelo nome no fim é o normal em português — "fecha o
# navegador para mim, Milk" — e o reconhecimento ainda gruda o nome na
# palavra anterior ("jamilk"). Daí o `\w*` dos dois lados: em português
# não existe palavra com "milk" dentro, então isto não pega fala que
# não era com ela.
NOME_FORTE = re.compile(
    r"\w*m[ie]l[kqc]\w*"

    # O reconhecimento tambem troca a consoante do comeco: a chamada
    # de 06/09, as 17h18, virou 'Silk' e ela ficou calada. Nenhuma
    # palavra comum do portugues termina em -ilk, -ilq ou -ilc, entao
    # aceitar a troca nao transforma conversa em chamado.
    r"|\b[bcdfgjlnpqrstvxz]il[kqc]\w*"

    r"|\bmeek\b|\bmick\b",
    re.IGNORECASE
)


# Formas curtas que também são palavra comum ("mil", "link", "mio").
# Estas só valem no começo da fala, senão qualquer conversa viraria
# chamado.
NOME_FRACO = re.compile(
    r"^\s*(?:oi|ei|ô|o|ol[áa]|al[ôo]|hey|e a[íi])?[\s,]*"
    r"(?:mil|miu|mio|nick|link|leek|mike)\b"
    r"[\s,;:.!?-]*",
    re.IGNORECASE
)


# Sobra do vocativo: " ," vira ",".
ESPACO_ANTES_DA_PONTUACAO = re.compile(r"\s+([,;:.!?])")

# O nome tirado do meio da frase deixa a pontuacao dele para tras:
# fecha o navegador, Milk, por favor virava fecha o navegador,, por
# favor. Fica so a ultima, que e a que separa o resto da frase.
PONTUACAO_REPETIDA = re.compile(r"([,;:])[ ]*(?=[,;:.!?])")


PONTUACAO_SOLTA = re.compile(r"^[\s,;:.!?-]+|[\s,;:-]+$")

ESPACOS_SEGUIDOS = re.compile(r"\s{2,}")


# Depois de atender, ela segue ouvindo por este tempo sem exigir o nome.
JANELA_DE_CONVERSA = 12.0

TAMANHO_DO_BLOCO = 2048


def tem_o_nome(texto):
    """Ela foi chamada nesta fala? O nome pode estar em qualquer lugar."""

    texto = str(texto or "")

    return bool(
        NOME_FORTE.search(texto)
        or
        NOME_FRACO.match(texto)
    )


def tirar_o_nome(texto):
    """'Milk, que horas são' e 'que horas são, Milk' viram a mesma coisa."""

    texto = str(texto or "")

    texto = NOME_FRACO.sub("", texto, count=1)

    texto = NOME_FORTE.sub(" ", texto)

    texto = ESPACOS_SEGUIDOS.sub(" ", texto)

    texto = ESPACO_ANTES_DA_PONTUACAO.sub(r"\1", texto)

    texto = PONTUACAO_REPETIDA.sub("", texto)

    return PONTUACAO_SOLTA.sub("", texto).strip()


class EscutaWorker(QThread):
    """Fica ouvindo até mandarem parar.

    Sinais:
        ouviu(str)     fala dirigida à Milk, já sem o nome na frente
        acordou()      ela foi chamada agora
        status(str)    para a barra de status e o log
        erro(str)      falha que o usuário precisa saber
    """

    ouviu = Signal(str)
    acordou = Signal()
    so_o_nome = Signal()
    status = Signal(str)
    erro = Signal(str)

    # Tempo de ouvido fechado depois do latido, para o próprio som não
    # virar pedido.
    SURDEZ_DO_LATIDO = 1.5

    # Tempo de ouvido fechado enquanto ela fala. É generoso de
    # propósito: quem encurta é o fim da fala, avisando de volta.
    SURDEZ_DA_FALA = 120.0

    # Depois que ela cala, o eco ainda passeia pela sala.
    RABO_DA_FALA = 0.5

    def __init__(
        self,
        *,
        abrir_microfone=None,
        transcritor=None,
        taxa=None,
        tamanho_do_bloco=TAMANHO_DO_BLOCO,
        janela_de_conversa=JANELA_DE_CONVERSA,
        relogio=None,
    ):
        super().__init__()

        self._abrir_microfone = abrir_microfone
        self._transcrever = transcritor
        self._taxa = taxa
        self._tamanho_do_bloco = tamanho_do_bloco
        self._janela = janela_de_conversa

        import time

        self._relogio = relogio or time.monotonic

        self.rodando = False

        # Enquanto isto for maior que agora, ela não exige o nome.
        self.conversa_ate = 0.0

        # Enquanto isto for maior que agora, ela não escuta nada. É o
        # que impede o latido e a própria voz dela de virarem pedido.
        self.surda_ate = 0.0

        self.ultimo_texto = ""

    # --------------------------------------------------------

    def surdear(self, segundos):
        """Fecha o ouvido por um tempo. Só estende, nunca encurta."""

        alvo = self._relogio() + max(0.0, float(segundos))

        if alvo > self.surda_ate:
            self.surda_ate = alvo

    def voltar_a_ouvir(self, atraso=0.0):
        """Reabre o ouvido, com um rabinho de atraso para o eco passar."""

        self.surda_ate = self._relogio() + max(0.0, float(atraso))

    def surda(self):
        return self._relogio() < self.surda_ate

    def parar(self):
        """Pede para o laço terminar. O `run()` sai no próximo bloco."""

        self.rodando = False

    def esperando_continuacao(self):
        return self._relogio() < self.conversa_ate

    def abrir(self):
        """Abre o microfone. Sem `sounddevice`, devolve None e avisa."""

        if self._abrir_microfone is not None:
            return self._abrir_microfone()

        import sounddevice as sd

        from milk.voice import dispositivos

        # O microfone é o escolhido no settings.json, não o padrão do
        # Windows: nesta máquina o padrão está mudo.
        entrada = dispositivos.escolher()

        if entrada is None:
            return None

        taxa = self._taxa or entrada.taxa

        fluxo = sd.InputStream(
            samplerate=taxa,
            channels=1,
            dtype="int16",
            blocksize=self._tamanho_do_bloco,
            device=entrada.indice,
        )

        fluxo.start()

        return fluxo, taxa, entrada.nome

    def transcrever(self, amostras, taxa):
        if self._transcrever is not None:
            return self._transcrever(amostras, taxa)

        return transcricao_padrao.transcrever_amostras(amostras, taxa)

    # --------------------------------------------------------

    def run(self):
        try:
            aberto = self.abrir()

        except Exception as erro:
            registrar_erro("voice", "não consegui abrir o microfone", erro)

            self.erro.emit(
                "Não consegui abrir o microfone para escutar."
            )

            return

        if not aberto:
            self.erro.emit(
                "Não consegui abrir o microfone para escutar."
            )

            return

        fluxo, taxa, nome = aberto

        detector = Detector(
            taxa,
            self._tamanho_do_bloco
        )

        self.rodando = True

        self.status.emit(
            f"👂 Ouvindo pelo {nome}. Diga o meu nome."
        )

        logger("voice").info(f"escuta contínua ligada ({nome}, {taxa} Hz)")

        try:
            while self.rodando:
                bloco = self.ler(fluxo)

                if bloco is None:
                    break

                # Ela está latindo ou falando: o microfone continua
                # aberto (fechar e abrir a cada fala trava o áudio),
                # mas o que entra é jogado fora. Sem isto, a própria
                # voz dela cai na janela de conversa e vira pedido.
                if self.surda():
                    detector.esquecer()

                    continue

                resposta = detector.alimentar(bloco)

                if resposta is None or isinstance(resposta, str):
                    continue

                # Veio um trecho de fala inteiro.
                self.tratar_fala(resposta, taxa)

        except Exception as erro:
            registrar_erro("voice", "a escuta contínua parou sozinha", erro)

            self.erro.emit(
                "A escuta parou sozinha. Pode ligar de novo."
            )

        finally:
            self.rodando = False

            self.fechar(fluxo)

            logger("voice").info("escuta contínua desligada")

    def ler(self, fluxo):
        """Um bloco do microfone. None quando o fluxo acabou."""

        try:
            dados, estourou = fluxo.read(self._tamanho_do_bloco)

        except Exception:
            return None

        if dados is None:
            return None

        amostras = np.asarray(dados, dtype=np.int16).reshape(-1)

        if amostras.size == 0:
            return None

        return amostras

    def tratar_fala(self, amostras, taxa):
        """Transcreve o trecho e decide se era com ela."""

        try:
            texto = self.transcrever(amostras, taxa)

        except transcricao_padrao.SemFala:
            # Barulho que parecia fala. Silêncio é a resposta certa.
            return

        except transcricao_padrao.ServicoIndisponivel as erro:
            registrar_erro("voice", "reconhecimento indisponível", erro)

            self.status.emit(
                "👂 Ouvindo (o reconhecimento falhou agora)"
            )

            return

        except Exception as erro:
            registrar_erro("voice", "falha ao transcrever", erro)

            return

        self.ultimo_texto = texto

        chamada = tem_o_nome(texto)

        if not (chamada or self.esperando_continuacao()):
            logger("voice").info(f"ignorou (sem o nome): {texto[:40]}")

            return

        pedido = tirar_o_nome(texto) if chamada else texto.strip()

        # Renova a janela: a conversa continua sem repetir o nome.
        self.conversa_ate = self._relogio() + self._janela

        if chamada:
            # O latido sai daqui, antes de qualquer rede: é a resposta
            # imediata que mostra que ela ouviu.
            # Quem fecha o ouvido durante o latido e a fala e o
            # mascote, que e quem toca o som: se ela estiver no modo
            # silencioso nao ha latido nenhum para ignorar.
            self.acordou.emit()

        if not pedido:
            # Chamaram só o nome. Antes isto virava um texto na barra de
            # status e mais nada — parecia que ela não tinha atendido.
            # Agora ela responde de viva voz, na hora.
            self.status.emit("👂 Oi! Estou ouvindo.")

            self.so_o_nome.emit()

            return

        logger("voice").info(f"atendeu: {pedido[:60]}")

        self.ouviu.emit(pedido)

    def fechar(self, fluxo):
        for metodo in ("stop", "close"):
            try:
                getattr(fluxo, metodo)()

            except Exception:
                pass
