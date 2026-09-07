# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Iniciar junto com o Windows (Fase 22).

Usa a chave `Run` do usuário no registro. É o jeito mais simples de
ligar e desligar sem instalador, sem tarefa agendada e sem pedir
administrador: mexe só no ramo do próprio usuário (HKCU).

    esta_ligado()   já sobe com o Windows?
    ligar()         passa a subir
    desligar()      para de subir

Nada aqui levanta exceção para fora: registro é coisa que pode falhar
por permissão, e a Milk não pode morrer por causa disso.
"""

import os
import sys

from milk.core.config import BASE_DIR
from milk.core.log import logger, registrar_erro


CHAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"

NOME = "MilkAssistente"


def comando_de_inicio():
    """A linha que o Windows vai executar no logon.

    `pythonw.exe` no lugar de `python.exe` para não abrir a janela preta
    do terminal junto (Fase 21)."""

    executavel = sys.executable or "python.exe"

    sem_console = executavel.replace("python.exe", "pythonw.exe")

    if not os.path.isfile(sem_console):
        sem_console = executavel

    script = os.path.join(BASE_DIR, "milk.py")

    return f'"{sem_console}" "{script}"'


def _abrir_chave(escrita=False):
    import winreg

    acesso = winreg.KEY_WRITE if escrita else winreg.KEY_READ

    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        CHAVE,
        0,
        acesso,
    )


def esta_ligado():
    """A Milk já está marcada para subir com o Windows?"""

    try:
        import winreg

        with _abrir_chave() as chave:
            valor, _ = winreg.QueryValueEx(chave, NOME)

        return bool(valor)

    except FileNotFoundError:
        return False

    except Exception:
        return False


def ligar():
    """Passa a subir com o Windows. Devolve True se conseguiu."""

    try:
        import winreg

        with _abrir_chave(escrita=True) as chave:
            winreg.SetValueEx(
                chave,
                NOME,
                0,
                winreg.REG_SZ,
                comando_de_inicio(),
            )

        logger("system").info("passou a iniciar com o Windows")

        return True

    except Exception as erro:
        registrar_erro("system", "não consegui ligar o início automático", erro)

        return False


def desligar():
    """Para de subir com o Windows. Devolve True se conseguiu."""

    try:
        import winreg

        with _abrir_chave(escrita=True) as chave:
            winreg.DeleteValue(chave, NOME)

        logger("system").info("deixou de iniciar com o Windows")

        return True

    except FileNotFoundError:
        # Já não estava lá: o estado desejado é este mesmo.
        return True

    except Exception as erro:
        registrar_erro("system", "não consegui desligar o início automático", erro)

        return False


def alternar(ligado):
    return ligar() if ligado else desligar()
