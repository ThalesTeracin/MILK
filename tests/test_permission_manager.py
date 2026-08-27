"""
Testes de src/security/permission_manager.py -- o gate de permissão que,
antes da Fase 2, existia em config/permission_profiles.json mas nunca era
chamado por nenhum código (decorativo).
"""
import pytest

from security.permission_manager import PermissionManager


def test_default_profile_is_balanced():
    pm = PermissionManager()
    assert pm.profile == "balanced"


def test_unknown_profile_falls_back_to_balanced():
    pm = PermissionManager(profile="nao-existe")
    assert pm.profile == "balanced"


def test_arbitrary_shell_denied_in_every_profile():
    for profile in ["safe", "balanced", "developer"]:
        pm = PermissionManager(profile=profile)
        result = pm.check("arbitrary_shell")
        assert result["allowed"] is False, f"arbitrary_shell deveria ser negado no perfil {profile}"
        assert result["confirm"] is False


def test_safe_profile_denies_delete_file():
    pm = PermissionManager(profile="safe")
    result = pm.check("delete_file")
    assert result["allowed"] is False


def test_balanced_profile_requires_confirmation_for_delete_file():
    pm = PermissionManager(profile="balanced")
    result = pm.check("delete_file")
    assert result["allowed"] is True
    assert result["confirm"] is True


def test_action_not_listed_is_allowed_without_confirmation():
    pm = PermissionManager(profile="balanced")
    result = pm.check("open_app")  # não está em deny nem confirm em nenhum perfil
    assert result == {"allowed": True, "confirm": False, "reason": "Permitido."}


def test_set_profile_switches_active_profile():
    pm = PermissionManager(profile="safe")
    pm.set_profile("developer")
    assert pm.profile == "developer"


def test_set_profile_rejects_unknown_profile():
    pm = PermissionManager(profile="safe")
    with pytest.raises(ValueError):
        pm.set_profile("nao-existe")
