import json
from pathlib import Path
from datetime import datetime

LOG = Path("logs/self_review.log")
LOG.parent.mkdir(parents=True, exist_ok=True)

class SelfReview:
    def __init__(self, ai=None):
        self.ai = ai

    def _log(self, data):
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def verify_command_result(self, action, result):
        """
        Generic structured verification for tool/command results.
        """
        ok = bool(result.get("ok", False))
        stderr = (result.get("stderr") or "").strip()
        stdout = (result.get("stdout") or "").strip()

        review = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "command_result",
            "action": action,
            "ok": ok and not stderr,
            "issues": [],
            "evidence": {
                "stdout": stdout[:1200],
                "stderr": stderr[:1200],
                "code": result.get("code")
            }
        }

        if not ok:
            review["issues"].append("A ação retornou falha.")
        if stderr:
            review["issues"].append("Houve saída de erro.")
        if result.get("code") not in (None, 0):
            review["issues"].append(f"Código de saída {result.get('code')}.")

        self._log(review)
        return review

    def verify_file(self, path, min_size=1):
        p = Path(path)
        issues = []

        if not p.exists():
            issues.append("Arquivo não existe.")
        elif not p.is_file():
            issues.append("O caminho não é arquivo.")
        elif p.stat().st_size < min_size:
            issues.append("Arquivo está vazio ou menor que o esperado.")

        review = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "file",
            "path": str(p),
            "ok": len(issues) == 0,
            "issues": issues,
            "size": p.stat().st_size if p.exists() and p.is_file() else None
        }
        self._log(review)
        return review

    def verify_json(self, path):
        p = Path(path)
        issues = []

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            data = None
            issues.append(f"JSON inválido: {e}")

        review = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "json",
            "path": str(p),
            "ok": len(issues) == 0,
            "issues": issues
        }
        self._log(review)
        return review

    def ai_review(self, task, evidence):
        """
        Optional second-level semantic review through the configured AI.
        Returns None when AI is unavailable.
        """
        if not self.ai or not getattr(self.ai, "enabled", False):
            return None

        system = """
Você é o auditor interno da MILK.
Revise se a tarefa foi realmente concluída.
Retorne SOMENTE JSON:
{
  "ok": true,
  "confidence": 0.0,
  "issues": [],
  "next_action": "texto curto ou null"
}
Não diga que está concluído se a evidência não provar.
"""
        try:
            return self.ai.ask_json(
                system,
                f"Tarefa: {task}\nEvidência:\n{json.dumps(evidence, ensure_ascii=False)[:5000]}",
                max_tokens=280
            )
        except Exception as e:
            return {
                "ok": False,
                "confidence": 0.0,
                "issues": [f"Falha no self-review por IA: {e}"],
                "next_action": "Usar apenas revisão determinística."
            }

    def final_decision(self, task, evidence):
        deterministic_ok = all(
            item.get("ok", False) for item in evidence if isinstance(item, dict)
        ) if evidence else False

        ai_result = self.ai_review(task, evidence)

        if ai_result is None:
            final = {
                "ok": deterministic_ok,
                "confidence": 1.0 if deterministic_ok else 0.4,
                "issues": [] if deterministic_ok else ["Evidência determinística insuficiente."],
                "review_mode": "deterministic"
            }
        else:
            final = {
                "ok": deterministic_ok and bool(ai_result.get("ok")),
                "confidence": float(ai_result.get("confidence", 0)),
                "issues": ai_result.get("issues", []),
                "next_action": ai_result.get("next_action"),
                "review_mode": "deterministic+ai"
            }

        self._log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "final_decision",
            "task": task,
            "result": final
        })
        return final
