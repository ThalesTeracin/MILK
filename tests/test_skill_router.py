"""
Testes de src/skills/advanced_router.py.

Ate a fase 33 este router era orfao: nenhum ponto do aplicativo o
importava, so Testar_Fase31.py. As skills nunca rodaram por voz.

Duas coisas mudam e sao o que estes testes protegem: o gate passou a ser o
PermissionManager da fase 2 (o conjunto RISKY proprio do router era uma
copia pior, sem distinguir negar de confirmar), e as skills devolvem uma
frase falavel alem dos dados.

Nenhum teste toca git, disco ou navegador de verdade.
"""
import pytest

from skills.advanced_router import AdvancedSkillRouter


class PermissoesFalsas:
    """PermissionManager de mentira, com a resposta ditada pelo teste."""

    def __init__(self, negar=(), confirmar=()):
        self.negar = set(negar)
        self.confirmar = set(confirmar)
        self.consultadas = []

    def check(self, action):
        self.consultadas.append(action)
        if action in self.negar:
            return {"allowed": False, "confirm": False, "reason": "Bloqueado pelo perfil."}
        if action in self.confirmar:
            return {"allowed": True, "confirm": True, "reason": "Confirmação obrigatória."}
        return {"allowed": True, "confirm": False, "reason": "Permitido."}


@pytest.fixture
def router():
    return AdvancedSkillRouter(permissions=PermissoesFalsas())


# ------------------------------------------------------ route_local

def test_reconhece_status_do_git(router):
    plano = router.route_local("milk, qual o status do git")

    assert plano == {"type": "builtin", "skill": "git_status", "args": {}}


def test_reconhece_abrir_projetos(router):
    plano = router.route_local("abrir projetos")

    assert plano["skill"] == "open_projects"


def test_frase_qualquer_nao_casa(router):
    """Sem plano, o handle segue para o NLU como sempre fez."""
    assert router.route_local("que horas são") is None


def test_texto_vazio_nao_casa(router):
    assert router.route_local("") is None
    assert router.route_local(None) is None


def test_status_do_sistema_nao_e_mais_skill(router):
    """
    WindowsAgent.system_status já responde isso, com frase falável, e está
    ligado ao intent. Se o router capturasse, a resposta pioraria.
    """
    assert router.route_local("status do sistema") is None


def test_pesquisa_no_google_nao_e_mais_skill(router):
    """
    BrowserAgent.search dirige a página e sustenta os browser_click_text e
    browser_fill que vêm depois; o webbrowser do sistema não.
    """
    assert router.route_local("pesquisa no google gatos") is None


# ---------------------------------------------------------- execute

def test_executa_e_devolve_frase(router, monkeypatch):
    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.git_status",
        staticmethod(lambda args=None: {"ok": True, "fala": "Estou na branch master.", "dados": {"branch": "master"}}),
    )

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is True
    assert saida["fala"] == "Estou na branch master."
    assert saida["dados"] == {"branch": "master"}


def test_o_gate_e_consultado_com_o_nome_da_skill():
    permissoes = PermissoesFalsas()
    router = AdvancedSkillRouter(permissions=permissoes)

    router.execute({"type": "builtin", "skill": "open_projects", "args": {}}, confirmed=True)

    assert "open_projects" in permissoes.consultadas


def test_skill_negada_nao_executa():
    permissoes = PermissoesFalsas(negar=["git_status"])
    router = AdvancedSkillRouter(permissions=permissoes)

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False
    assert "perfil" in saida["fala"].lower()


def test_skill_que_pede_confirmacao_nao_executa_ainda():
    permissoes = PermissoesFalsas(confirmar=["open_projects"])
    router = AdvancedSkillRouter(permissions=permissoes)

    saida = router.execute({"type": "builtin", "skill": "open_projects", "args": {}})

    assert saida.get("requires_confirmation") is True
    assert saida["skill"] == "open_projects"


def test_confirmada_a_skill_executa(monkeypatch):
    permissoes = PermissoesFalsas(confirmar=["open_projects"])
    router = AdvancedSkillRouter(permissions=permissoes)
    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.open_projects",
        staticmethod(lambda args=None: {"ok": True, "fala": "Abri a pasta.", "dados": {}}),
    )

    saida = router.execute(
        {"type": "builtin", "skill": "open_projects", "args": {}}, confirmed=True
    )

    assert saida["ok"] is True
    assert saida["fala"] == "Abri a pasta."


def test_sem_gate_configurado_a_skill_nao_roda():
    """
    Router sem PermissionManager é erro de montagem, não permissão livre.
    Deixar passar seria abrir um caminho sem gate nenhum.
    """
    router = AdvancedSkillRouter()

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False


def test_skill_que_levanta_excecao_vira_frase(router, monkeypatch):
    def explode(args=None):
        raise RuntimeError("git não está no PATH")

    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.git_status", staticmethod(explode)
    )

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False
    assert saida["fala"]
    assert "RuntimeError" in saida["dados"]["erro"]
    assert "git não está no PATH" in saida["dados"]["erro"]


def test_plano_vazio(router):
    saida = router.execute(None)

    assert saida["ok"] is False


def test_skill_inexistente(router):
    saida = router.execute({"type": "builtin", "skill": "voar", "args": {}})

    assert saida["ok"] is False


# ------------------------------------------------------- o registro

def test_o_registro_so_lista_o_que_existe():
    """
    config/skills.json declarava git_push, deploy, send_email e
    system_change sem nenhuma implementação: nomes sem nada atrás.
    """
    from skills.skill_registry import BuiltinSkills, SkillRegistry

    for skill in SkillRegistry().list_skills():
        assert hasattr(BuiltinSkills, skill["name"]), skill["name"]
