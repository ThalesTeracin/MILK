# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""A aparência da janela de conversa.

Só desenho: janela, botões, caixa de texto e cores. Nada aqui decide
o que a Milk responde — quem decide é o `ChatBubble`, em `chat.py`.

`montar_interface(janela)` recebe o `ChatBubble` já com `pessoa` e
`saudacao()` prontos, e pendura nele os widgets que o resto do código
usa pelo nome: `status`, `chat`, `entrada`, `botao_enviar`,
`botao_microfone` e `botao_voz`."""

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from milk.core.texto import formatar_chat


def montar_interface(janela):
    """Desenha a janela de conversa da Milk."""

    janela.setWindowFlags(
        Qt.Tool
        | Qt.FramelessWindowHint
        | Qt.WindowStaysOnTopHint
    )

    janela.setAttribute(
        Qt.WA_TranslucentBackground
    )

    janela.resize(
        470,
        500
    )

    painel = QWidget()
    painel.setObjectName("painel")

    principal = QVBoxLayout(janela)

    principal.setContentsMargins(
        0,
        0,
        0,
        0
    )

    principal.addWidget(
        painel
    )

    layout = QVBoxLayout(
        painel
    )

    layout.setContentsMargins(
        16,
        16,
        16,
        16
    )

    layout.setSpacing(
        10
    )

    titulo = QLabel(
        "🐾 Milk"
    )

    titulo.setObjectName(
        "titulo"
    )

    titulo.setAlignment(
        Qt.AlignCenter
    )

    janela.status = QLabel(
        "Pronta para conversar."
    )

    janela.status.setAlignment(
        Qt.AlignCenter
    )

    janela.status.setObjectName(
        "status"
    )

    janela.chat = QTextEdit()

    janela.chat.setReadOnly(
        True
    )

    janela.chat.append(
        formatar_chat(
            "Milk",
            janela.saudacao()
        )
    )

    janela.entrada = QLineEdit()

    janela.entrada.setPlaceholderText(
        "Digite ou fale comigo..."
    )

    janela.entrada.returnPressed.connect(
        janela.enviar_digitado
    )

    linha1 = QHBoxLayout()

    janela.botao_enviar = QPushButton(
        "Enviar"
    )

    janela.botao_enviar.clicked.connect(
        janela.enviar_digitado
    )

    janela.botao_microfone = QPushButton(
        "🎤 Falar"
    )

    janela.botao_microfone.clicked.connect(
        janela.ouvir
    )

    linha1.addWidget(
        janela.botao_enviar
    )

    linha1.addWidget(
        janela.botao_microfone
    )

    linha2 = QHBoxLayout()

    janela.botao_voz = QPushButton(
        "🔊 Voz ligada"
    )

    janela.botao_voz.clicked.connect(
        janela.alternar_voz
    )

    fechar = QPushButton(
        "Fechar"
    )

    fechar.clicked.connect(
        janela.hide
    )

    linha2.addWidget(
        janela.botao_voz
    )

    linha2.addWidget(
        fechar
    )

    layout.addWidget(
        titulo
    )

    layout.addWidget(
        janela.status
    )

    layout.addWidget(
        janela.chat
    )

    layout.addWidget(
        janela.entrada
    )

    layout.addLayout(
        linha1
    )

    layout.addLayout(
        linha2
    )

    janela.setStyleSheet("""
        #painel {
            background-color: #fff7fb;
            border: 2px solid #e9bfd5;
            border-radius: 24px;
        }

        #titulo {
            color: #202020;
            font-size: 25px;
            font-weight: bold;
        }

        #status {
            color: #9a7188;
            font-size: 11pt;
        }

        QTextEdit {
            background-color: white;
            color: #202020;
            border: 1px solid #dfcbd5;
            border-radius: 14px;
            padding: 10px;
            font-size: 14px;
        }

        QLineEdit {
            background-color: white;
            color: #202020;
            border: 1px solid #dfcbd5;
            border-radius: 12px;
            padding: 11px;
            font-size: 14px;
        }

        QPushButton {
            background-color: #f3d5e4;
            border: 1px solid #dbb8ca;
            border-radius: 11px;
            padding: 10px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #ecc7da;
        }
    """)
