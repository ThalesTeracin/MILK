"""
Roteia fala para skill embutida, por palavra-chave local.

Sem IA de proposito: e rapido, nao gasta token e continua funcionando com
o provedor fora do ar. O custo aceito e casar so as frases previstas.

O gate e o PermissionManager da fase 2. Ate a fase 33 este modulo tinha um
conjunto RISKY proprio -- as mesmas acoes de config/permission_profiles.json,
so que sem distinguir negar de confirmar, e com "admin_shell" onde o perfil
diz "open_admin". Dois gates, um pior. Sobrou o do perfil.
"""
from skills.skill_registry import BuiltinSkills, SkillRegistry


class AdvancedSkillRouter:
    def __init__(self, ai=None, mcp_manager=None, permissions=None):
        self.ai = ai
        self.mcp = mcp_manager
        self.registry = SkillRegistry()
        self.permissions = permissions

    def route_local(self, text):
        """Devolve um plano, ou None para o fluxo seguir para o NLU."""
        t = (text or "").lower()

        if "status do git" in t or "status do repositorio" in t or "status do repositório" in t:
            return {"type": "builtin", "skill": "git_status", "args": {}}

        if "abrir projetos" in t or "abre meus projetos" in t or "abrir meus projetos" in t:
            return {"type": "builtin", "skill": "open_projects", "args": {}}

        return None

    def execute(self, plan, confirmed=False):
        if not plan:
            return {"ok": False, "fala": "Não entendi qual ação executar.", "dados": {}}

        skill = plan.get("skill")

        if not self.permissions:
            # Router montado sem gate é erro de montagem, não permissão
            # livre: deixar passar abriria um caminho sem gate nenhum.
            return {
                "ok": False,
                "fala": "Não posso executar isso: o controle de permissões não está configurado.",
                "dados": {"skill": skill},
            }

        veredito = self.permissions.check(skill)
        if not veredito["allowed"]:
            return {
                "ok": False,
                "fala": f"Não posso fazer isso. {veredito['reason']}",
                "dados": {"skill": skill},
            }
        if veredito["confirm"] and not confirmed:
            return {
                "requires_confirmation": True,
                "skill": skill,
                "fala": "Isso requer confirmação. Diga confirmar para continuar.",
            }

        if plan.get("type") == "builtin":
            fn = getattr(BuiltinSkills, skill, None)
            if not fn:
                return {"ok": False, "fala": "Não conheço essa habilidade.", "dados": {"skill": skill}}
            try:
                return fn(plan.get("args") or {})
            except Exception as e:
                return {
                    "ok": False,
                    "fala": "Não consegui executar isso agora.",
                    "dados": {"skill": skill, "erro": f"{type(e).__name__}: {e}"},
                }

        if plan.get("type") == "mcp":
            if not self.mcp:
                return {"ok": False, "fala": "O MCP não está disponível.", "dados": {}}
            return self.mcp.call_tool(
                plan["server"], plan["tool"], plan.get("args") or {}, confirmed=confirmed
            )

        return {"ok": False, "fala": "Não conheço esse tipo de habilidade.", "dados": {"plano": plan}}
