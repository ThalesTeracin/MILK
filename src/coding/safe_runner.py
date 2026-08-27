from pathlib import Path
import sys, json, os

from core.proc import run_hidden

class SafeRunner:
    def __init__(self, project_dir, python_exe=None):
        self.project = Path(project_dir)
        self.python_exe = str(python_exe or sys.executable)

    def _run(self, cmd, timeout=90):
        try:
            p = run_hidden(
                cmd,
                cwd=self.project,
                timeout=timeout
            )
            return {
                "ok": p.returncode == 0,
                "returncode": p.returncode,
                "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:]
            }
        except Exception as e:
            return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(e)}

    def compile_python(self):
        return self._run([self.python_exe, "-m", "compileall", "-q", "."], timeout=60)

    def run_pytest(self):
        tests = self.project / "tests"
        if not tests.exists():
            return {"ok": True, "skipped": True, "reason": "Sem pasta tests."}
        return self._run([self.python_exe, "-m", "pytest", "-q"], timeout=120)

    def run_entrypoint(self):
        candidates = ["main.py", "app.py", "server.py"]
        for name in candidates:
            p = self.project / name
            if p.exists():
                return self._run([self.python_exe, name], timeout=20)
        return {"ok": True, "skipped": True, "reason": "Sem entrypoint padrão."}

    def validate_all(self):
        return {
            "compile": self.compile_python(),
            "tests": self.run_pytest()
        }
