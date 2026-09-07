# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Avatar da Milk na área de trabalho, com bandeja e fila de fala."""

import os

from PySide6.QtCore import Qt, QPoint, QUrl

from PySide6.QtGui import QAction, QColor, QGuiApplication, QPixmap, QIcon

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QSystemTrayIcon,
    QMenu,
)

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from milk.core.config import AVATAR_FILE
from milk.core.texto import limpar_para_voz
from milk.voice.tts import TTSWorker
from milk.voice.latido import latir as tocar_latido
from milk.avatar.animacao import Animacao
from milk.avatar.chat import ChatBubble
from milk.voice.escuta import EscutaWorker
from milk.intelligence.rotas_conversa import atender_ao_nome
from milk.core.settings import obter as ler_ajuste
from milk.core import modos as controle_de_modo
from milk.system import inicio
from milk.avatar import posicao
from milk.avatar.quadros import carregar_quadros
from milk.avatar.passeio import Passeio


class MilkMascot(QWidget):
    def __init__(self):
        super().__init__()

        # O modo guardado manda na voz: silencioso e nao perturbe
        # respondem por escrito.
        self.modos = controle_de_modo.modos()

        self.voz_ativa = self.modos.pode_falar()
        self.tts_worker = None
        self.fila_fala = []

        self.arrastando = False
        self.offset = QPoint()
        self.mouse_press_pos = None

        # Fica None quando o PNG não existe e ela cai no emoji: aí não
        # há o que animar.
        self.avatar_base = None
        self.animacao = None

        self.estado = "parada"

        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.resize(
            140,
            168
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            5,
            5,
            5,
            5
        )

        self.avatar = QLabel()

        self.avatar.setAlignment(
            Qt.AlignCenter
        )

        self.carregar_avatar()

        self.estado_label = QLabel(
            "🐾 pronta"
        )

        self.estado_label.setAlignment(
            Qt.AlignCenter
        )

        # Sem caixa escura e em corpo pequeno: o estado continua visível
        # sem transformar a Milk num painel de programa. A sombra é o que
        # mantém o texto legível sobre qualquer papel de parede.
        self.estado_label.setStyleSheet("""
            color: rgba(255,255,255,190);
            font-size: 10px;
            padding: 0px;
        """)

        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(4)
        sombra.setOffset(0, 1)
        sombra.setColor(QColor(0, 0, 0, 220))

        self.estado_label.setGraphicsEffect(
            sombra
        )

        layout.addWidget(
            self.avatar
        )

        layout.addWidget(
            self.estado_label
        )

        self.chat = ChatBubble(
            self
        )

        self.audio_output = QAudioOutput(
            self
        )

        self.audio_output.setVolume(
            1.0
        )

        self.player = QMediaPlayer(
            self
        )

        self.player.setAudioOutput(
            self.audio_output
        )

        self.player.mediaStatusChanged.connect(
            self.status_audio
        )

        self.criar_tray()

        self.posicionar_canto()

        # Escuta continua: so existe quando o usuario liga.
        self.escuta = None
        self.escutando = False

        self.passeio = Passeio(
            self,
            self.pode_passear,
            parent=self
        )

        self.passeio.comecar()

        if self.avatar_base is not None:
            self.animacao = Animacao(
                self.avatar_base,
                self.avatar.setPixmap,
                andando=lambda: self.passeio.andando,
                direcao=lambda: self.passeio.direcao,
                percorrido=lambda: self.passeio.andado,
                quadros=carregar_quadros(
                    self.avatar_base.height()
                ),
                parent=self
            )

            self.animacao.comecar()

        # Ela já sobe ouvindo. Antes era preciso ligar a escuta no menu
        # do botão direito a cada vez, e quem não sabia disso achava
        # que ela simplesmente não atendia pelo nome.
        if self.escuta_automatica():
            self.ligar_escuta()

    # ========================================================
    # ESCUTA CONTÍNUA
    # ========================================================

    def escuta_automatica(self):
        """Ela deve começar ouvindo, sem ninguém ligar no menu?

        Vem do `config/settings.json`. Em "não perturbe" ela não ouve
        sozinha: o modo existe justamente para ela não interromper."""

        if self.modos.modo == controle_de_modo.NAO_PERTURBE:
            return False

        return bool(
            ler_ajuste(
                "microfone",
                "escuta_automatica",
                True
            )
        )

    def alternar_escuta(self, ligar):
        """Liga e desliga a escuta com wake word.

        Ligada, ela ouve a sala e só atende quando é chamada pelo nome.
        Desligada, o microfone só é usado pelo botão "🎤 Falar"."""

        if ligar:
            return self.ligar_escuta()

        return self.desligar_escuta()

    def ligar_escuta(self):
        if self.escuta is not None and self.escuta.isRunning():
            return True

        self.escuta = EscutaWorker()

        self.escuta.ouviu.connect(self.chamada_por_voz)
        self.escuta.acordou.connect(self.acordou_pelo_nome)
        self.escuta.so_o_nome.connect(self.chamaram_so_o_nome)
        self.escuta.status.connect(self.status_da_escuta)
        self.escuta.erro.connect(self.erro_da_escuta)

        self.escuta.start()

        self.escutando = True

        return True

    def desligar_escuta(self):
        self.escutando = False

        if self.escuta is None:
            return False

        self.escuta.parar()

        # Ela sai no proximo bloco de audio, em fracao de segundo.
        self.escuta.wait(3000)

        self.escuta = None

        self.set_estado("parada")

        return False

    def acordou_pelo_nome(self):
        """Ela foi chamada: late na hora e mostra que ouviu.

        O latido é a única resposta que não depende de rede nenhuma.
        Ele sai antes do reconhecimento, antes do roteador e antes do
        Claude — é o que faz a Milk parecer viva enquanto o resto do
        trabalho acontece."""

        self.set_estado("ouvindo")

        self.latir()

    def chamaram_so_o_nome(self):
        """Disseram "Milk" e mais nada. Ela responde de viva voz.

        Antes isto só mudava a barra de status, então quem chamava
        achava que ela não tinha atendido e ia clicar no botão."""

        self.abrir_chat(latir=False)

        if self.chat is None:
            return

        self.chat.origem_do_pedido = "voz"

        self.chat.responder_direto(
            atender_ao_nome(self.chat.pessoa)
        )

    def chamada_por_voz(self, texto):
        """Fala dirigida a ela, ja sem o nome na frente."""

        if not texto.strip():
            return

        self.abrir_chat(latir=False)

        if self.chat is None:
            return

        self.chat.origem_do_pedido = "voz"

        # Quem escreve o pedido na conversa é o processar(): escrever
        # aqui também faria a fala aparecer duas vezes.
        self.chat.processar(texto)

    def status_da_escuta(self, mensagem):
        if self.chat is not None:
            self.chat.status.setText(mensagem)

    def erro_da_escuta(self, mensagem):
        self.escutando = False

        if self.chat is not None:
            self.chat.status.setText(mensagem)

    # ========================================================
    # MODO DE CONVIVÊNCIA
    # ========================================================

    def definir_modo(self, modo):
        """Normal, silencioso ou não perturbe.

        O trabalho continua igual nos três: o que muda é se ela fala e
        se ela pode aparecer sozinha."""

        self.modos.definir(modo)

        self.voz_ativa = self.modos.pode_falar()

        if not self.voz_ativa:
            self.parar_fala()

        if self.chat is not None:
            self.chat.atualizar_botao_de_voz()

            self.chat.status.setText(
                f"Modo {self.modos.nome()}."
            )

        return self.modos.modo

    def alternar_inicio_automatico(self, ligado):
        """Sobe junto com o Windows, ou não."""

        conseguiu = inicio.alternar(ligado)

        if self.chat is not None:
            self.chat.status.setText(
                "Vou abrir junto com o Windows."
                if ligado and conseguiu
                else (
                    "Não vou mais abrir sozinha."
                    if conseguiu
                    else "Não consegui mudar isso no registro."
                )
            )

        return conseguiu

    def diagnosticar(self):
        """Abre a conversa e roda o Milk Doctor por lá."""

        self.abrir_chat(latir=False)

        if self.chat is not None:
            self.chat.processar("faça um diagnóstico")

    def pode_passear(self):
        """Ela só sai andando quando não está no meio de nada.

        Andar com a conversa aberta arrastaria a janela do chat junto na
        cabeça de quem está lendo, e andar enquanto o dono a arrasta com
        o mouse briga com o próprio arrasto."""

        return (
            not self.arrastando
            and
            self.estado == "parada"
            and
            not self.chat.isVisible()
        )

    # ========================================================
    # AVATAR
    # ========================================================

    def carregar_avatar(self):
        if os.path.exists(
            AVATAR_FILE
        ):
            pixmap = QPixmap(
                AVATAR_FILE
            )

            if not pixmap.isNull():
                # Um pouco menor que o rótulo: a animação inclina a
                # imagem, e sem essa folga as orelhas seriam cortadas.
                imagem = pixmap.scaled(
                    110,
                    110,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                self.avatar_base = imagem

                self.avatar.setPixmap(
                    imagem
                )

                return

        self.avatar.setText(
            "🐶"
        )

        self.avatar.setStyleSheet(
            "font-size:100px;"
        )

    # ========================================================
    # ESTADO
    # ========================================================

    def set_estado(self, estado):
        self.estado = estado

        mapa = {
            "parada": "🐾 pronta",
            "ouvindo": "👂 ouvindo",
            "pensando": "🧠 pensando",
            "falando": "🗣️ falando",
        }

        self.estado_label.setText(
            mapa.get(
                estado,
                "🐾"
            )
        )

    # ========================================================
    # VOZ NEURAL
    # ========================================================

    def falar(self, texto):
        texto = limpar_para_voz(
            texto
        )

        if not texto:
            return

        self.fila_fala.append(
            texto
        )

        self.proxima_fala()

    def proxima_fala(self):
        if (
            self.tts_worker
            and
            self.tts_worker.isRunning()
        ):
            return

        if self.player.playbackState() == (
            QMediaPlayer.PlayingState
        ):
            return

        if not self.fila_fala:
            self.set_estado(
                "parada"
            )

            return

        texto = self.fila_fala.pop(0)

        self.set_estado(
            "falando"
        )

        # A partir daqui ela vai falar. Quem reabre o ouvido é o fim do
        # áudio; este prazo largo é só a rede de segurança para o caso
        # de a voz falhar no meio.
        self.fechar_o_ouvido(
            EscutaWorker.SURDEZ_DA_FALA
        )

        self.tts_worker = TTSWorker(
            texto
        )

        self.tts_worker.pronto.connect(
            self.reproduzir_voz
        )

        self.tts_worker.erro.connect(
            self.erro_voz
        )

        self.tts_worker.start()

    def parar_fala(self):
        self.fila_fala.clear()

        self.player.stop()

        self.abrir_o_ouvido()

        self.set_estado(
            "parada"
        )

    def reproduzir_voz(self, arquivo):
        self.player.setSource(
            QUrl.fromLocalFile(
                arquivo
            )
        )

        self.player.play()

    def status_audio(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.fila_fala:
                self.proxima_fala()
                return

            # Ela terminou de falar: volta a ouvir a sala.
            self.abrir_o_ouvido()

            self.set_estado(
                "parada"
            )

            self.chat.status.setText(
                "Pronta. 🐾"
            )

    def erro_voz(self, mensagem):
        self.chat.status.setText(
            "Resposta pronta."
        )

        # A voz falhou, então não há áudio dela para ignorar.
        self.abrir_o_ouvido(0.0)

        self.proxima_fala()

    # ========================================================
    # CHAT
    # ========================================================

    def abrir_chat(self, latir=True):
        """latir=False ao abrir para ouvir, senão o latido entra no microfone."""

        if latir:
            self.latir()

        # O monitor onde ela está agora, não o principal: depois que ela
        # passou a passear, os dois deixaram de ser sempre o mesmo.
        tela = (
            QGuiApplication.screenAt(
                self.geometry().center()
            )
            or
            QApplication.primaryScreen()
        )

        if tela is None:
            self.chat.show()
            return

        area = tela.availableGeometry()

        x = (
            self.x()
            - self.chat.width()
            + self.width()
        )

        y = (
            self.y()
            - self.chat.height()
            - 10
        )

        x = max(
            area.left() + 10,
            min(
                x,
                area.right()
                - self.chat.width()
                - 10
            )
        )

        y = max(
            area.top() + 10,
            min(
                y,
                area.bottom()
                - self.chat.height()
                - 10
            )
        )

        self.chat.move(
            x,
            y
        )

        self.chat.show()
        self.chat.raise_()

        self.chat.entrada.setFocus()

    # ========================================================
    # LATIDO
    # ========================================================

    def latir(self):
        """Toca o latido de verdade, quando o arquivo existir.

        Não cai mais para a voz neural dizendo "Au au": voz humana
        pronunciando latido não soa como cachorro. Sem o arquivo, ela
        simplesmente não late."""

        if not self.modos.pode_latir():
            return False

        # Ela está com o microfone aberto: o próprio latido seria
        # gravado e mandado para o reconhecimento.
        self.fechar_o_ouvido(
            EscutaWorker.SURDEZ_DO_LATIDO
        )

        return tocar_latido()

    # ========================================================
    # O OUVIDO DELA ENQUANTO ELA FALA
    # ========================================================

    def fechar_o_ouvido(self, segundos):
        """A escuta ignora o microfone por um tempo.

        Sem isto, a voz dela cai na janela de conversa (os segundos em
        que ela atende sem exigir o nome) e ela responde a si mesma."""

        if self.escuta is None:
            return

        try:
            self.escuta.surdear(segundos)

        except Exception:
            pass

    def abrir_o_ouvido(self, atraso=None):
        """Reabre a escuta, com um rabinho de atraso para o eco passar."""

        if self.escuta is None:
            return

        if atraso is None:
            atraso = EscutaWorker.RABO_DA_FALA

        try:
            self.escuta.voltar_a_ouvir(atraso)

        except Exception:
            pass

    # ========================================================
    # CLIQUE / ARRASTAR
    # ========================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.arrastando = True

            self.mouse_press_pos = (
                event.globalPosition().toPoint()
            )

            self.offset = (
                self.mouse_press_pos
                - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if (
            self.arrastando
            and
            event.buttons() & Qt.LeftButton
        ):
            self.move(
                event.globalPosition().toPoint()
                - self.offset
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            atual = (
                event.globalPosition().toPoint()
            )

            self.arrastando = False

            if self.mouse_press_pos is None:
                return

            distancia = (
                atual
                - self.mouse_press_pos
            ).manhattanLength()

            if distancia < 8:
                self.abrir_chat()

            else:
                # Arrastou: e aqui que ela fica daqui em diante.
                self.salvar_posicao()

            self.mouse_press_pos = None

    # ========================================================
    # BOTÃO DIREITO
    # ========================================================

    def contextMenuEvent(self, event):
        menu = QMenu(
            self
        )

        falar = QAction(
            "🎤 Falar com Milk",
            self
        )

        falar.triggered.connect(
            self.abrir_e_ouvir
        )

        conversar = QAction(
            "💬 Abrir conversa",
            self
        )

        conversar.triggered.connect(
            lambda:
            self.abrir_chat()
        )

        teste_voz = QAction(
            "🔊 Testar voz",
            self
        )

        teste_voz.triggered.connect(
            lambda:
            self.falar(
                "Oi. Estou aqui e pronta para ajudar."
            )
        )

        passear = QAction(
            "🚶 Passear pela tela",
            self
        )

        passear.setCheckable(
            True
        )

        passear.setChecked(
            self.passeio.ativo
        )

        passear.toggled.connect(
            self.passeio.alternar
        )

        escutar = QAction(
            "👂 Escuta contínua (diga \"Milk\")",
            self
        )

        escutar.setCheckable(
            True
        )

        escutar.setChecked(
            self.escutando
        )

        escutar.toggled.connect(
            self.alternar_escuta
        )

        modo_normal = QAction("🔊 Modo normal", self)
        modo_silencioso = QAction("🔕 Modo silencioso", self)
        modo_nao_perturbe = QAction("🌙 Não perturbe", self)

        for acao, modo in (
            (modo_normal, controle_de_modo.NORMAL),
            (modo_silencioso, controle_de_modo.SILENCIOSO),
            (modo_nao_perturbe, controle_de_modo.NAO_PERTURBE),
        ):
            acao.setCheckable(True)
            acao.setChecked(self.modos.modo == modo)

            acao.triggered.connect(
                lambda marcado, escolhido=modo:
                self.definir_modo(escolhido)
            )

        com_windows = QAction(
            "🪟 Iniciar com o Windows",
            self
        )

        com_windows.setCheckable(
            True
        )

        com_windows.setChecked(
            inicio.esta_ligado()
        )

        com_windows.toggled.connect(
            self.alternar_inicio_automatico
        )

        diagnostico = QAction(
            "🩺 Diagnóstico (Milk Doctor)",
            self
        )

        diagnostico.triggered.connect(
            self.diagnosticar
        )

        sair = QAction(
            "❌ Encerrar Milk",
            self
        )

        sair.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            falar
        )

        menu.addAction(
            conversar
        )

        menu.addAction(
            teste_voz
        )

        menu.addAction(
            passear
        )

        menu.addAction(
            escutar
        )

        menu.addSeparator()

        menu.addAction(
            modo_normal
        )

        menu.addAction(
            modo_silencioso
        )

        menu.addAction(
            modo_nao_perturbe
        )

        menu.addSeparator()

        menu.addAction(
            com_windows
        )

        menu.addAction(
            diagnostico
        )

        menu.addSeparator()

        menu.addAction(
            sair
        )

        menu.exec(
            event.globalPos()
        )

    def abrir_e_ouvir(self):
        self.abrir_chat(
            latir=False
        )

        self.chat.ouvir()

    # ========================================================
    # BANDEJA
    # ========================================================

    def criar_tray(self):
        self.tray = QSystemTrayIcon(
            self
        )

        icon = QIcon()

        if os.path.exists(
            AVATAR_FILE
        ):
            teste = QIcon(
                AVATAR_FILE
            )

            if not teste.isNull():
                icon = teste

        if not icon.isNull():
            self.tray.setIcon(
                icon
            )

            QApplication.instance().setWindowIcon(
                icon
            )

        self.tray.setToolTip(
            "Milk - Assistente"
        )

        menu = QMenu()

        mostrar = QAction(
            "Mostrar Milk",
            self
        )

        mostrar.triggered.connect(
            self.show
        )

        falar = QAction(
            "Falar com Milk",
            self
        )

        falar.triggered.connect(
            self.abrir_e_ouvir
        )

        sair = QAction(
            "Encerrar",
            self
        )

        sair.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            mostrar
        )

        menu.addAction(
            falar
        )

        menu.addSeparator()

        menu.addAction(
            sair
        )

        self.tray.setContextMenu(
            menu
        )

        if not icon.isNull():
            self.tray.show()

    # ========================================================
    # POSIÇÃO
    # ========================================================

    def posicionar_canto(self):
        """Onde ela estava da última vez; na estreia, no canto de baixo.

        A posição guardada só vale se ainda couber num monitor de hoje:
        quem tirou o segundo monitor não pode achar a Milk fora da tela."""

        guardada = posicao.posicao_valida(
            self.width(),
            self.height()
        )

        if guardada is not None:
            self.move(
                guardada[0],
                guardada[1]
            )

            return

        tela = QApplication.primaryScreen()

        if tela is None:
            return

        area = tela.availableGeometry()

        self.move(
            area.right()
            - self.width()
            - 25,

            area.bottom()
            - self.height()
            - 25
        )

    def salvar_posicao(self):
        """Guarda onde ela está. Chamado ao soltar o arraste e ao sair."""

        return posicao.gravar(
            self.x(),
            self.y()
        )

