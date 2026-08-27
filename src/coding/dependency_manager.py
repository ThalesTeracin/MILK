from pathlib import Path
import subprocess, sys, re, json

# Dependências permitidas nesta fase.
ALLOWLIST = {
    "requests", "fastapi", "uvicorn", "flask", "pytest",
    "pydantic", "sqlalchemy", "jinja2", "python-dotenv",
    "httpx", "rich"
}

class DependencyManager:
    def __init__(self, project_dir):
        self.project = Path(project_dir)
        self.venv = self.project / ".venv"

    def ensure_venv(self):
        if not self.venv.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv)],
                check=True,
                timeout=180
            )
        return self.python_path()

    def python_path(self):
        return self.venv / "Scripts" / "python.exe"

    def pip_path(self):
        return self.venv / "Scripts" / "pip.exe"

    def parse_requirements(self):
        req = self.project / "requirements.txt"
        if not req.exists():
            return []
        packages = []
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            base = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip().lower()
            if base:
                packages.append((base, line))
        return packages

    def validate_requirements(self):
        allowed = []
        blocked = []
        for base, original in self.parse_requirements():
            if base in ALLOWLIST:
                allowed.append(original)
            else:
                blocked.append(original)
        return allowed, blocked

    def install_allowed(self):
        allowed, blocked = self.validate_requirements()
        self.ensure_venv()
        results = {"installed": [], "blocked": blocked, "errors": []}

        for pkg in allowed:
            p = subprocess.run(
                [str(self.python_path()), "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
                timeout=180
            )
            if p.returncode == 0:
                results["installed"].append(pkg)
            else:
                results["errors"].append({
                    "package": pkg,
                    "stderr": p.stderr[-1200:]
                })
        return results
