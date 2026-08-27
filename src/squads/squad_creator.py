import json
from pathlib import Path

class SquadCreator:
    def __init__(self, ai_router=None):
        self.ai=ai_router
        self.agents={a["id"]:a for a in json.loads(Path("config/agents.json").read_text(encoding="utf-8"))}

    def local_select(self, text):
        t=text.lower()
        squad=["aios_master","project_manager"]
        rules=[
            (["codigo","programa","app","site","sistema","software"],["architect","developer","qa_tester","rootcause"]),
            (["interface","ux","design","tela"],["ux_designer","product_owner"]),
            (["banco","dados","planilha","csv"],["data_engineer","analyst"]),
            (["deploy","servidor","aws","nuvem"],["devops","architect"]),
            (["erro","bug","falha"],["rootcause","qa_tester","developer"]),
            (["pesquise","analise","pesquisa"],["analyst"]),
        ]
        for keys,adds in rules:
            if any(k in t for k in keys): squad.extend(adds)
        # conclave for complex creation
        if any(k in t for k in ["crie","construa","desenvolva","planeje"]):
            squad += ["conclave_critic","conclave_advocate","conclave_synthesizer"]
        seen=[]
        for a in squad:
            if a not in seen and a in self.agents: seen.append(a)
        return seen

    def select(self,text):
        local=self.local_select(text)
        if local and len(local)>2: return local
        if not self.ai or not self.ai.enabled: return local
        system="""Você escolhe uma squad de agentes do MILK.
Retorne SOMENTE JSON: {"agents":["id1","id2",...]}.
Use somente IDs conhecidos e no máximo 8 agentes."""
        user="Tarefa: "+text+"\nIDs disponíveis: "+", ".join(self.agents.keys())
        r=self.ai.ask_json(system,user)
        if r and isinstance(r.get("agents"),list):
            valid=[a for a in r["agents"] if a in self.agents]
            if valid: return valid[:8]
        return local
