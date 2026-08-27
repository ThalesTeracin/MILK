from pathlib import Path
import os, re, json, datetime
from coding.dependency_manager import DependencyManager
from coding.safe_runner import SafeRunner

BUILD_SYSTEM = """
Você é o Coding Agent V2 do MILK.
Crie ou atualize um projeto pequeno e funcional.

Retorne SOMENTE JSON:
{
  "project_name":"nome-curto",
  "summary":"resumo curto",
  "files":[{"path":"relativo.ext","content":"conteúdo completo"}],
  "run_hint":"texto curto"
}

Regras:
- caminhos relativos apenas;
- nunca sair da pasta do projeto;
- máximo 15 arquivos;
- sem segredos, tokens ou senhas;
- sem comandos destrutivos;
- se usar dependências Python, crie requirements.txt;
- prefira dependências comuns;
- adicione testes quando fizer sentido.
"""

REPAIR_SYSTEM = """
Você é o reparador de código do MILK.
Receberá a tarefa, arquivos atuais e erros de validação.
Retorne SOMENTE JSON:
{
  "summary":"o que corrigiu",
  "files":[{"path":"relativo.ext","content":"conteúdo completo"}]
}
Regras:
- altere apenas arquivos necessários;
- caminhos relativos;
- sem comandos destrutivos;
- sem tocar fora da pasta do projeto.
"""

class CodingAgentV2:
    def __init__(self, ai, projects_dir="projects", max_repair_loops=2):
        self.ai = ai
        self.projects_dir = Path(os.getenv("MILK_PROJECTS_DIR", projects_dir))
        self.max_repair_loops = max_repair_loops

    def _safe_name(self, name):
        name = re.sub(r"[^a-zA-Z0-9_-]+", "-", name or "projeto-milk").strip("-")
        return name[:60] or "projeto-milk"

    def _safe_target(self, base, relative):
        target = (base / relative).resolve()
        base_r = base.resolve()
        if base_r != target and base_r not in target.parents:
            raise ValueError("Tentativa de escrever fora do projeto bloqueada.")
        return target

    def _write_files(self, project, files):
        written = []
        for item in (files or [])[:15]:
            rel = item.get("path", "")
            content = item.get("content", "")
            if not rel or not isinstance(content, str):
                continue
            target = self._safe_target(project, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(str(target))
        return written

    def _snapshot(self, project):
        data = {}
        for p in project.rglob("*"):
            if p.is_file() and ".venv" not in p.parts:
                try:
                    rel = str(p.relative_to(project))
                    data[rel] = p.read_text(encoding="utf-8")[:12000]
                except Exception:
                    pass
        return data

    def _log(self, project, payload):
        log_dir = project / ".milk"
        log_dir.mkdir(exist_ok=True)
        path = log_dir / "last_run.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_and_repair(self, task):
        if not self.ai or not self.ai.enabled:
            return {"ok": False, "message": "AI Router não configurado."}

        spec = self.ai.ask_json(BUILD_SYSTEM, task, max_tokens=2200)
        if not spec or not isinstance(spec.get("files"), list):
            return {"ok": False, "message": "A IA não retornou um projeto válido."}

        project = self.projects_dir / self._safe_name(spec.get("project_name"))
        project.mkdir(parents=True, exist_ok=True)

        written = self._write_files(project, spec["files"])

        deps = DependencyManager(project)
        install = deps.install_allowed()

        runner = SafeRunner(project, deps.python_path())
        validation = runner.validate_all()

        repair_history = []
        loop = 0

        while loop < self.max_repair_loops:
            compile_ok = validation.get("compile", {}).get("ok", False)
            tests_ok = validation.get("tests", {}).get("ok", False)

            if compile_ok and tests_ok:
                break

            repair_prompt = {
                "task": task,
                "files": self._snapshot(project),
                "validation": validation,
                "blocked_dependencies": install.get("blocked", [])
            }

            repair = self.ai.ask_json(
                REPAIR_SYSTEM,
                json.dumps(repair_prompt, ensure_ascii=False),
                max_tokens=2200
            )

            if not repair or not isinstance(repair.get("files"), list):
                break

            changed = self._write_files(project, repair["files"])
            repair_history.append({
                "loop": loop + 1,
                "summary": repair.get("summary"),
                "changed": changed
            })

            validation = runner.validate_all()
            loop += 1

        ok = (
            validation.get("compile", {}).get("ok", False)
            and validation.get("tests", {}).get("ok", False)
        )

        result = {
            "ok": ok,
            "project": str(project),
            "summary": spec.get("summary", "Projeto criado."),
            "written": written,
            "dependencies": install,
            "validation": validation,
            "repairs": repair_history,
            "run_hint": spec.get("run_hint"),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds")
        }

        self._log(project, result)
        return result
