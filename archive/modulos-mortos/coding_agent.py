from pathlib import Path
import os, re
from coding.safe_runner import SafeRunner

SYSTEM = """
Você é o Coding Agent do MILK.
Retorne SOMENTE JSON:
{
 "project_name":"nome-curto",
 "summary":"resumo",
 "files":[{"path":"relative/path.ext","content":"conteúdo completo"}],
 "run_hint":"instrução curta"
}
Regras: caminhos relativos, nunca sair da pasta do projeto, sem chaves/senhas,
sem ações destrutivas, no máximo 12 arquivos.
"""

class CodingAgent:
    def __init__(self,ai,projects_dir="projects"):
        self.ai=ai
        self.projects_dir=Path(os.getenv("MILK_PROJECTS_DIR",projects_dir))
        self.runner=SafeRunner()
    def _safe_name(self,name):
        name=re.sub(r"[^a-zA-Z0-9_-]+","-",name or "projeto-milk").strip("-")
        return name[:60] or "projeto-milk"
    def _safe_path(self,base,relative):
        target=(base/relative).resolve(); br=base.resolve()
        if br != target and br not in target.parents:
            raise ValueError("Caminho bloqueado.")
        return target
    def build(self,task):
        if not self.ai or not self.ai.enabled:
            return {"ok":False,"message":"AI Router não configurado."}
        spec=self.ai.ask_json(SYSTEM,task,max_tokens=1800)
        if not spec or not isinstance(spec.get("files"),list):
            return {"ok":False,"message":"Não consegui gerar um projeto válido."}
        project=self.projects_dir/self._safe_name(spec.get("project_name"))
        project.mkdir(parents=True,exist_ok=True)
        written=[]
        for item in spec["files"][:12]:
            rel=item.get("path",""); content=item.get("content","")
            if not rel or not isinstance(content,str): continue
            target=self._safe_path(project,rel)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(content,encoding="utf-8"); written.append(str(target))
        return {"ok":True,"project":str(project),"written":written,
                "validation":self.runner.validate(project),
                "summary":spec.get("summary","Projeto criado.")}
