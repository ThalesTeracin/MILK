from pathlib import Path

from core.proc import run_hidden

class GitHubAgent:
    def _run(self, args, cwd=None, timeout=120):
        p = run_hidden(
            args,
            cwd=cwd,
            timeout=timeout
        )
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip()
        }

    def gh_available(self):
        try:
            r = run_hidden(["gh","--version"],timeout=10)
            return r.returncode == 0, (r.stdout or r.stderr).splitlines()[0]
        except Exception as e:
            return False, str(e)

    def auth_status(self):
        return self._run(["gh","auth","status"])

    def create_repo(self, name, private=True, source_path=None):
        args = ["gh","repo","create",name]
        args += ["--private" if private else "--public"]
        if source_path:
            args += ["--source",str(source_path),"--remote","origin"]
        return self._run(args, cwd=source_path)

    def open_repo(self, path=None):
        return self._run(["gh","repo","view","--web"], cwd=path)

    def create_pr(self, title, body="", path=None):
        return self._run(
            ["gh","pr","create","--title",title,"--body",body],
            cwd=path
        )
