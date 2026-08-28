"""
Testes de src/core/config.py -- o resolvedor que faz config/local/
sobrepor config/, para que a atualização não sobrescreva configuração
específica desta máquina.
"""
import core.config as config_mod
from core.config import config_path


def test_devolve_o_versionado_quando_nao_ha_local(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    versionado = tmp_path / "config" / "x.json"
    versionado.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("x.json") == versionado


def test_local_tem_precedencia(tmp_path, monkeypatch):
    (tmp_path / "config" / "local").mkdir(parents=True)
    (tmp_path / "config" / "x.json").write_text("{}", encoding="utf-8")
    local = tmp_path / "config" / "local" / "x.json"
    local.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("x.json") == local


def test_devolve_o_versionado_quando_nenhum_existe(tmp_path, monkeypatch):
    """Quem chama decide o que fazer com caminho inexistente."""
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("nao_existe.json") == tmp_path / "config" / "nao_existe.json"


def test_diretorios_padrao_apontam_para_a_raiz_do_repositorio():
    assert config_mod.CONFIG_DIR.name == "config"
    assert config_mod.LOCAL_DIR.parent == config_mod.CONFIG_DIR
    assert (config_mod.CONFIG_DIR / "persona.txt").exists()
