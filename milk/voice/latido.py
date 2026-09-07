# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Latido da Milk.

Efeito sonoro curto, separado da voz. O TTS continua sendo o
`TTSWorker`; aqui não passa nada de fala.

Usa `QSoundEffect`, que já vem no PySide6 instalado: ele carrega o WAV
uma vez e guarda em memória, então tocar de novo não lê o disco outra
vez. Tocar não bloqueia a interface e não abre janela nem console.

Se o arquivo não existir ou o formato não for aceito, `latir()` devolve
False e a Milk segue funcionando normalmente. Nada aqui derruba nada.
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

from milk.core.config import BARK_FILE
from milk.core.settings import obter


VOLUME_PADRAO = 0.8


# Um único efeito para a sessão inteira: o arquivo é lido uma vez só.
_efeito = None

# Reserva para WAV que o QSoundEffect não aceita (ele só toca PCM).
_reserva = None

# Pedido de tocar feito enquanto o arquivo ainda estava carregando.
_esperando = False


def caminho():
    """Onde o latido mora. O caminho vem de milk/core/config.py."""

    return Path(BARK_FILE)


def existe():
    try:
        return caminho().is_file()

    except OSError:
        return False


def volume():
    """Volume de 0.0 a 1.0, vindo do config/settings.json."""

    valor = obter(
        "latido",
        "volume",
        VOLUME_PADRAO
    )

    try:
        valor = float(valor)

    except (TypeError, ValueError):
        return VOLUME_PADRAO

    return min(
        max(valor, 0.0),
        1.0
    )


def _ao_mudar_status():
    """Toca o latido que foi pedido enquanto o arquivo carregava."""

    global _esperando

    if _efeito is None or not _esperando:
        return

    if _efeito.status() == QSoundEffect.Status.Ready:
        _esperando = False
        _efeito.play()

    elif _efeito.status() == QSoundEffect.Status.Error:
        _esperando = False
        _tocar_reserva()


def preparar():
    """Cria o efeito uma única vez. Devolve None se não houver arquivo.

    Precisa de um QApplication já criado, por isso a criação é aqui e
    não na importação do módulo."""

    global _efeito

    if _efeito is not None:
        return _efeito

    if not existe():
        return None

    try:
        efeito = QSoundEffect()

        efeito.setSource(
            QUrl.fromLocalFile(
                str(caminho())
            )
        )

        efeito.setVolume(
            volume()
        )

        efeito.statusChanged.connect(
            _ao_mudar_status
        )

        _efeito = efeito

    except Exception:
        return None

    return _efeito


def _tocar_reserva():
    """Alguns WAV não são PCM puro e o QSoundEffect recusa.

    Aí entra um QMediaPlayer só do latido, separado do player da voz,
    para não atrapalhar o TTS."""

    global _reserva

    try:
        if _reserva is None:
            player = QMediaPlayer()
            saida = QAudioOutput()

            player.setAudioOutput(saida)

            player.setSource(
                QUrl.fromLocalFile(
                    str(caminho())
                )
            )

            _reserva = (player, saida)

        player, saida = _reserva

        saida.setVolume(
            volume()
        )

        player.setPosition(0)
        player.play()

        return True

    except Exception:
        return False


def latir():
    """Toca o latido. Devolve True se conseguiu, False se não.

    Pode ser chamada quantas vezes quiser na mesma sessão."""

    global _esperando

    try:
        efeito = preparar()

        if efeito is None:
            return False

        efeito.setVolume(
            volume()
        )

        status = efeito.status()

        if status == QSoundEffect.Status.Ready:
            efeito.play()

            return True

        if status == QSoundEffect.Status.Loading:
            # Toca assim que terminar de carregar.
            _esperando = True

            return True

        if status == QSoundEffect.Status.Error:
            return _tocar_reserva()

        return _tocar_reserva()

    except Exception:
        return False


def descrever_problema():
    """Frase curta para a interface quando o latido não sai."""

    if not existe():
        return (
            "Ainda não tenho o som do meu latido aqui. "
            f"Ele precisa estar em {caminho()}."
        )

    return "Não consegui tocar o meu latido agora."
