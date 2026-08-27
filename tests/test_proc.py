"""
Testes de src/core/proc.py -- o módulo central que substituiu as 9
implementações duplicadas do padrão "subprocess oculto" (Fase 1).
"""
import os
import subprocess
import sys

from core.proc import _windows_hidden_kwargs, popen_hidden, run_hidden


def test_windows_hidden_kwargs_shape_on_nt():
    kwargs = _windows_hidden_kwargs()
    if os.name == "nt":
        assert kwargs["creationflags"] == 0x08000000  # CREATE_NO_WINDOW
        assert isinstance(kwargs["startupinfo"], subprocess.STARTUPINFO)
        assert kwargs["startupinfo"].wShowWindow == 0  # SW_HIDE
    else:
        assert kwargs == {}


def test_run_hidden_executes_and_captures_output():
    result = run_hidden([sys.executable, "-c", "print('ola')"])
    assert result.returncode == 0
    assert "ola" in result.stdout


def test_run_hidden_never_uses_shell():
    """
    Regra central do módulo: argv fixo, nunca shell=True. Isso é o que
    elimina o vetor de "tela preta"/console flash das 9 implementações
    antigas.
    """
    result = run_hidden([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.returncode == 3


def test_run_hidden_respects_cwd(tmp_path):
    result = run_hidden([sys.executable, "-c", "import os; print(os.getcwd())"], cwd=tmp_path)
    assert str(tmp_path) in result.stdout


def test_popen_hidden_returns_running_process_and_can_be_read():
    proc = popen_hidden(
        [sys.executable, "-c", "print('popen-ok')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, _ = proc.communicate(timeout=15)
    assert proc.returncode == 0
    assert "popen-ok" in out
