"""
Identifica a versão do MILK em execução.

Duas fontes, de propósito: o arquivo VERSION acompanha instalações sem
git (o caso das outras máquinas), enquanto o commit identifica o código
exato e só existe onde há repositório.
"""

from pathlib import Path

from core.proc import run_hidden

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"
VERSAO_DESCONHECIDA = "desconhecida"


def version_info():
    """Devolve (versao, commit). O commit é None fora de um repositório."""
    try:
        versao = VERSION_FILE.read_text(encoding="utf-8").strip() or VERSAO_DESCONHECIDA
    except Exception:
        versao = VERSAO_DESCONHECIDA

    commit = None
    try:
        resultado = run_hidden(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, timeout=10
        )
        if resultado.returncode == 0:
            commit = resultado.stdout.strip() or None
    except Exception:
        commit = None

    return versao, commit


def formatar_versao():
    """Devolve "32.0 (c53d469)", ou só "32.0" quando não há commit."""
    versao, commit = version_info()
    if commit:
        return "%s (%s)" % (versao, commit)
    return versao
