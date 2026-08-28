"""
Testes de src/core/version.py -- identificação do que está rodando.

A versão vem de um arquivo para funcionar em máquinas sem git; o commit
vem do git quando disponível e identifica o código exato.
"""
import core.version as version_mod
from core.version import formatar_versao, version_info


def test_le_a_versao_do_arquivo():
    versao, _ = version_info()
    assert versao
    assert versao[0].isdigit()


def test_devolve_o_commit_dentro_de_um_repositorio():
    _, commit = version_info()
    assert commit is not None
    assert 6 <= len(commit) <= 12


def test_versao_cai_no_padrao_quando_o_arquivo_some(tmp_path, monkeypatch):
    monkeypatch.setattr(version_mod, "VERSION_FILE", tmp_path / "nao_existe")
    versao, _ = version_info()
    assert versao == version_mod.VERSAO_DESCONHECIDA


class _ResultadoGitFalso:
    """Simula o CompletedProcess devolvido por run_hidden, sem tocar disco."""

    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def test_commit_e_none_fora_de_repositorio(monkeypatch):
    # Simula o retorno do git quando o diretório não é um repositório
    # (returncode != 0), sem depender de onde tmp_path cai no disco real.
    monkeypatch.setattr(
        version_mod, "run_hidden", lambda *a, **k: _ResultadoGitFalso(128)
    )
    _, commit = version_info()
    assert commit is None


def test_commit_e_none_quando_git_lanca_excecao(monkeypatch, capsys):
    # Simula git ausente do PATH (ou qualquer outra falha do run_hidden,
    # como travamento até o timeout). Diferente de "não é um repositório":
    # aqui deve haver aviso na saída, não apenas um None silencioso.
    def _run_hidden_quebrado(*args, **kwargs):
        raise FileNotFoundError("git não encontrado no PATH")

    monkeypatch.setattr(version_mod, "run_hidden", _run_hidden_quebrado)
    _, commit = version_info()
    assert commit is None
    saida = capsys.readouterr().out
    assert "FileNotFoundError" in saida


def test_formatar_inclui_o_commit_entre_parenteses():
    saida = formatar_versao()
    versao, commit = version_info()
    assert saida == "%s (%s)" % (versao, commit)


def test_formatar_omite_os_parenteses_sem_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(version_mod, "ROOT", tmp_path)
    versao, _ = version_info()
    assert formatar_versao() == versao
