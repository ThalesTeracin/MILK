"""
Centraliza a execução de subprocessos ocultos no Windows.

Origem do bug corrigido: cada módulo que chamava subprocess implementava
sua própria versão (às vezes incompleta) do padrão CREATE_NO_WINDOW +
SW_HIDE, causando o flash de janela de console ("tela preta") de forma
inconsistente. Este módulo é a única fonte de verdade para esse padrão.

Uso:
    from src.core.proc import run_hidden, popen_hidden

    result = run_hidden(["git", "status"], cwd=repo_path, timeout=30)
    proc = popen_hidden(["whisper-cli", ...], cwd=exe_dir, stdout=subprocess.PIPE)

Regras:
- Sempre shell=False, argv como lista fixa (nunca string interpolada).
- Nunca passa por cmd.exe / PowerShell, exceto quando o próprio comando
  alvo é powershell.exe/cmd.exe explicitamente na lista de argv.
"""

import os
import subprocess

# Flags do Windows para suprimir a janela de console.
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
STARTF_USESHOWWINDOW = 0x00000001
SW_HIDE = 0


def _windows_hidden_kwargs():
    """
    Retorna os kwargs necessários para subprocess.run/Popen rodar um
    executável de console sem criar/anexar uma janela de console.
    Usa CREATE_NO_WINDOW + SW_HIDE. Em plataformas != nt retorna {}.
    """
    if os.name != "nt":
        return {}

    si = subprocess.STARTUPINFO()
    si.dwFlags |= STARTF_USESHOWWINDOW
    si.wShowWindow = SW_HIDE

    return {
        "creationflags": CREATE_NO_WINDOW,
        "startupinfo": si,
    }


def run_hidden(args, cwd=None, timeout=None, text=True, capture_output=True,
                env=None, check=False, input=None, **extra):
    """
    Equivalente oculto de subprocess.run(). Sempre shell=False.

    args: lista de argv (nunca string).
    Retorna o CompletedProcess normal do subprocess.run.
    """
    kwargs = _windows_hidden_kwargs()
    kwargs.update(extra)
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        timeout=timeout,
        text=text,
        capture_output=capture_output,
        shell=False,
        env=env,
        check=check,
        input=input,
        **kwargs,
    )


def popen_hidden(args, cwd=None, stdin=None, stdout=None, stderr=None,
                  text=True, env=None, bufsize=-1, **extra):
    """
    Equivalente oculto de subprocess.Popen(). Sempre shell=False.

    args: lista de argv (nunca string).
    Retorna o objeto Popen.
    """
    kwargs = _windows_hidden_kwargs()
    kwargs.update(extra)
    return subprocess.Popen(
        args,
        cwd=str(cwd) if cwd is not None else None,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        text=text,
        env=env,
        bufsize=bufsize,
        shell=False,
        **kwargs,
    )
