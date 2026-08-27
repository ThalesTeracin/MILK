from pathlib import Path
import subprocess
import json
import os

class GitAgent:
    def __init__(self, default_root=r"C:\JARVIS\projects"):
        self.default_root = Path(default_root)
        self.default_root.mkdir(parents=True, exist_ok=True)

    def _run(self, args, cwd, timeout=60):
        p = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout
        )
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip()
        }

    def _repo(self, path=None):
        repo = Path(path or self.default_root).resolve()
        repo.mkdir(parents=True, exist_ok=True)
        return repo

    def git_available(self):
        try:
            r = subprocess.run(["git","--version"],capture_output=True,text=True,timeout=10)
            return r.returncode == 0, (r.stdout or r.stderr).strip()
        except Exception as e:
            return False, str(e)

    def status(self, path=None):
        repo = self._repo(path)
        return self._run(["git","status","--short","--branch"], repo)

    def init_repo(self, path=None):
        repo = self._repo(path)
        return self._run(["git","init"], repo)

    def current_branch(self, path=None):
        repo = self._repo(path)
        return self._run(["git","branch","--show-current"], repo)

    def create_branch(self, name, path=None):
        repo = self._repo(path)
        safe = "".join(c for c in name if c.isalnum() or c in "-_/").strip("/")
        if not safe:
            return {"ok":False,"stderr":"Nome de branch inválido.","stdout":"","code":1}
        return self._run(["git","switch","-c",safe], repo)

    def switch_branch(self, name, path=None):
        repo = self._repo(path)
        return self._run(["git","switch",name], repo)

    def diff(self, path=None):
        repo = self._repo(path)
        return self._run(["git","diff","--stat"], repo)

    def add_all(self, path=None):
        repo = self._repo(path)
        return self._run(["git","add","-A"], repo)

    def commit(self, message, path=None):
        repo = self._repo(path)
        message = (message or "").strip()
        if not message:
            return {"ok":False,"stderr":"Mensagem de commit vazia.","stdout":"","code":1}
        return self._run(["git","commit","-m",message], repo)

    def log(self, path=None, limit=8):
        repo = self._repo(path)
        return self._run(
            ["git","log",f"-{int(limit)}","--oneline","--decorate","--graph"],
            repo
        )

    def remotes(self, path=None):
        repo = self._repo(path)
        return self._run(["git","remote","-v"], repo)

    def add_remote(self, name, url, path=None):
        repo = self._repo(path)
        if not url.startswith(("https://","git@")):
            return {"ok":False,"stderr":"URL remota inválida.","stdout":"","code":1}
        return self._run(["git","remote","add",name,url], repo)

    def test_project(self, path=None):
        repo = self._repo(path)
        checks = []

        if (repo/"requirements.txt").exists():
            checks.append(self._run(
                ["python","-m","compileall","-q","."],
                repo,
                timeout=90
            ))

        if (repo/"tests").exists():
            checks.append(self._run(
                ["python","-m","pytest","-q"],
                repo,
                timeout=180
            ))

        if (repo/"package.json").exists():
            checks.append(self._run(
                ["npm","test","--","--runInBand"],
                repo,
                timeout=180
            ))

        if not checks:
            return {
                "ok":True,
                "stdout":"Nenhum teste automático detectado.",
                "stderr":"",
                "code":0
            }

        ok = all(c["ok"] for c in checks)
        return {
            "ok":ok,
            "stdout":"\n\n".join(c["stdout"] for c in checks if c["stdout"]),
            "stderr":"\n\n".join(c["stderr"] for c in checks if c["stderr"]),
            "code":0 if ok else 1
        }

    def push(self, path=None, remote="origin", branch=None):
        repo = self._repo(path)
        if not branch:
            branch_result = self.current_branch(repo)
            branch = branch_result["stdout"].strip()
        return self._run(["git","push","-u",remote,branch], repo, timeout=180)
