# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ponte com o Claude Code, com eventos de progresso.

O processo é lido em fluxo (stream-json), então a janela consegue
mostrar o que está acontecendo em vez de ficar parada em "Pensando...".
"""

import os
import json
import threading
import subprocess

from PySide6.QtCore import QThread, Signal

from milk.core.config import BASE_DIR, CLAUDE_SETTINGS


TIMEOUT_SEGUNDOS = 600


def nome_curto(caminho):
    if not caminho:
        return ""

    return os.path.basename(
        str(caminho).rstrip("\\/")
    )


def descrever_ferramenta(nome, entrada):
    """Frase curta em português para a ferramenta que está rodando."""

    entrada = entrada or {}

    if nome in ("Read", "NotebookRead"):
        return f"📖 Lendo {nome_curto(entrada.get('file_path'))}"

    if nome == "Write":
        return f"📝 Escrevendo {nome_curto(entrada.get('file_path'))}"

    if nome in ("Edit", "NotebookEdit"):
        return f"✏️ Editando {nome_curto(entrada.get('file_path'))}"

    if nome in ("Bash", "PowerShell"):
        descricao = (
            entrada.get("description")
            or
            str(entrada.get("command", ""))[:60]
        )

        return f"⚙️ {descricao}"

    if nome in ("Grep", "Glob"):
        alvo = (
            entrada.get("pattern")
            or
            entrada.get("query")
            or
            ""
        )

        return f"🔎 Procurando {str(alvo)[:40]}"

    if nome in ("WebSearch", "WebFetch"):
        return "🌐 Pesquisando na internet"

    if nome == "TodoWrite":
        return "🧾 Organizando as tarefas"

    if nome in ("Task", "Agent"):
        return "🐾 Chamando ajuda para uma parte do trabalho"

    return f"🔧 Usando {nome}"


def descrever_evento(dado):
    """Traduz um evento do fluxo em texto de progresso, ou None."""

    tipo = dado.get("type")

    if tipo == "system" and dado.get("subtype") == "init":
        return "🐾 Milk começou a trabalhar"

    if tipo != "assistant":
        return None

    mensagem = dado.get("message") or {}

    for bloco in mensagem.get("content") or []:
        if not isinstance(bloco, dict):
            continue

        if bloco.get("type") == "tool_use":
            return descrever_ferramenta(
                bloco.get("name"),
                bloco.get("input")
            )

        if bloco.get("type") == "text" and bloco.get("text", "").strip():
            return "💬 Montando a resposta"

    return None


class ClaudeWorker(QThread):
    sucesso = Signal(str)
    erro = Signal(str)
    progresso = Signal(str)

    def __init__(self, prompt):
        super().__init__()

        self.prompt = prompt
        self.processo = None
        self.expirou = False

    def cancelar(self):
        """Encerra o trabalho em andamento, se houver."""

        processo = self.processo

        if processo and processo.poll() is None:
            try:
                processo.kill()
            except OSError:
                pass

    def _encerrar_por_tempo(self):
        self.expirou = True
        self.cancelar()

    def run(self):
        comando = [
            "claude",
            "-p",
            self.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--settings",
            CLAUDE_SETTINGS,
        ]

        try:
            self.processo = subprocess.Popen(
                comando,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        except FileNotFoundError:
            self.erro.emit(
                "O comando Claude não foi encontrado."
            )

            return

        except Exception as exc:
            self.erro.emit(str(exc))
            return

        relogio = threading.Timer(
            TIMEOUT_SEGUNDOS,
            self._encerrar_por_tempo
        )

        relogio.daemon = True
        relogio.start()

        resposta = ""
        texto_reunido = []
        falhou = None

        try:
            for linha in self.processo.stdout:
                linha = linha.strip()

                if not linha:
                    continue

                try:
                    dado = json.loads(linha)

                except ValueError:
                    continue

                aviso = descrever_evento(dado)

                if aviso:
                    self.progresso.emit(aviso)

                if dado.get("type") == "assistant":
                    for bloco in (
                        dado.get("message") or {}
                    ).get("content") or []:

                        if (
                            isinstance(bloco, dict)
                            and
                            bloco.get("type") == "text"
                        ):
                            texto_reunido.append(
                                bloco.get("text", "")
                            )

                if dado.get("type") == "result":
                    if dado.get("is_error"):
                        falhou = (
                            str(dado.get("result", "")).strip()
                            or
                            "O Claude Code retornou um erro."
                        )
                    else:
                        resposta = str(
                            dado.get("result", "")
                        ).strip()

        except Exception as exc:
            falhou = falhou or str(exc)

        finally:
            relogio.cancel()

        erro_padrao = ""

        if self.processo.stderr:
            erro_padrao = self.processo.stderr.read().strip()

        self.processo.wait()

        if self.expirou:
            self.erro.emit(
                "O trabalho demorou demais e eu parei."
            )

            return

        if falhou:
            self.erro.emit(falhou)
            return

        if not resposta:
            resposta = "\n".join(
                parte
                for parte in texto_reunido
                if parte.strip()
            ).strip()

        if not resposta:
            self.erro.emit(
                erro_padrao
                or
                "Não recebi resposta nenhuma."
            )

            return

        self.sucesso.emit(resposta)
