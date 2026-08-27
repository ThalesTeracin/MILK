from skills.skill_registry import SkillRegistry, BuiltinSkills

RISKY = {
    "delete_file","git_push","deploy","send_email","system_change",
    "admin_shell","arbitrary_shell"
}

class AdvancedSkillRouter:
    def __init__(self, ai=None, mcp_manager=None):
        self.ai=ai
        self.mcp=mcp_manager
        self.registry=SkillRegistry()

    def route_local(self, text):
        t=(text or "").lower()

        if "status do sistema" in t or "como está meu computador" in t or "como esta meu computador" in t:
            return {"type":"builtin","skill":"system_status","args":{}}

        if "status do git" in t:
            return {"type":"builtin","skill":"git_status","args":{}}

        if "abrir projetos" in t or "abre meus projetos" in t:
            return {"type":"builtin","skill":"open_projects","args":{}}

        if "pesquisa no google" in t or "pesquise no google" in t:
            q=t.split("google",1)[1].strip()
            return {"type":"builtin","skill":"web_search","args":{"query":q}}

        return None

    def execute(self, plan, confirmed=False):
        if not plan:
            return {"ok":False,"error":"sem plano"}

        skill=plan.get("skill")
        if skill in RISKY and not confirmed:
            return {"requires_confirmation":True,"skill":skill}

        if plan.get("type")=="builtin":
            fn=getattr(BuiltinSkills,skill,None)
            if not fn:
                return {"ok":False,"error":"skill builtin ausente"}
            result=fn(plan.get("args") or {})
            return {"ok":True,"result":result}

        if plan.get("type")=="mcp":
            if not self.mcp:
                return {"ok":False,"error":"MCP indisponível"}
            return self.mcp.call_tool(
                plan["server"],plan["tool"],plan.get("args") or {},
                confirmed=confirmed
            )

        return {"ok":False,"error":"tipo de skill desconhecido"}
