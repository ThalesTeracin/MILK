from devops.git_agent import GitAgent
from devops.github_agent import GitHubAgent

class DevOpsManager:
    def __init__(self):
        self.git = GitAgent()
        self.github = GitHubAgent()

    def summarize(self, result, success_msg="Concluído."):
        if result.get("ok"):
            details = result.get("stdout","").strip()
            return success_msg + (f" {details}" if details else "")
        err = result.get("stderr") or result.get("stdout") or "Erro desconhecido."
        return f"Não consegui concluir. {err[:500]}"
