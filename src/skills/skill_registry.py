"""
As skills embutidas da MILK.

Cada skill devolve {"ok", "fala", "dados"}: a MILK fala o campo "fala", e
"dados" fica para log, teste e para o Command Center mostrar o número
exato sem re-executar a skill.

Duas skills sairam na fase 33 por duplicarem, pior, o que ja existia:
system_status (WindowsAgent.system_status ja devolve frase falavel e esta
ligado ao intent) e web_search (BrowserAgent.search dirige a pagina e
sustenta os browser_click_text e browser_fill que vem depois).
"""
import json
import os
from pathlib import Path

from core.proc import run_hidden

RAIZ = Path(__file__).resolve().parents[2]
REGISTRY = RAIZ / "config" / "skills.json"

# "## No commits yet on master" -> repositório sem nenhum commit ainda; o
# git usa esse texto no lugar do nome de branch normal no cabeçalho de
# `git status --branch`.
PREFIXO_SEM_COMMITS = "No commits yet on "


def _nome_da_branch(cabecalho):
    """
    Extrai o nome da branch do cabeçalho de `git status --short --branch`.

    Formatos tratados:
    - "## fase-33...origem/fase-33" (branch com upstream) -> "fase-33"
    - "## fase-33" (branch sem upstream) -> "fase-33"
    - "## No commits yet on master" (repo sem commits) -> "master"
    - "" (sem cabeçalho) -> "desconhecida"
    """
    sem_prefixo = cabecalho.lstrip("#").strip()
    if sem_prefixo.startswith(PREFIXO_SEM_COMMITS):
        sem_prefixo = sem_prefixo[len(PREFIXO_SEM_COMMITS):].strip()
    else:
        sem_prefixo = sem_prefixo.split("...")[0].strip()
    return sem_prefixo or "desconhecida"


class SkillRegistry:
    def __init__(self):
        self.data = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))

    def list_skills(self):
        return self.data.get("skills", [])

    def get(self, name):
        return next((s for s in self.list_skills() if s.get("name") == name), None)


class BuiltinSkills:
    @staticmethod
    def git_status(args=None):
        p = run_hidden(["git", "status", "--short", "--branch"], cwd=str(RAIZ))
        if p.returncode != 0:
            return {
                "ok": False,
                "fala": "Não consegui ler o status do git.",
                "dados": {"stderr": (p.stderr or "").strip()},
            }

        linhas = [l for l in (p.stdout or "").splitlines() if l.strip()]
        cabecalho = linhas[0] if linhas else ""
        branch = _nome_da_branch(cabecalho)
        pendentes = max(0, len(linhas) - 1)

        if pendentes == 0:
            fala = f"Estou na branch {branch}, sem alterações pendentes."
        elif pendentes == 1:
            fala = f"Estou na branch {branch}, com um arquivo pendente."
        else:
            fala = f"Estou na branch {branch}, com {pendentes} arquivos pendentes."

        return {"ok": True, "fala": fala, "dados": {"branch": branch, "pendentes": pendentes}}

    @staticmethod
    def open_projects(args=None):
        caminho = RAIZ / "projects"
        caminho.mkdir(parents=True, exist_ok=True)
        os.startfile(caminho)
        return {
            "ok": True,
            "fala": "Abri a pasta de projetos.",
            "dados": {"path": str(caminho)},
        }
