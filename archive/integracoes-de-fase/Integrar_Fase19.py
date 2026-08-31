from pathlib import Path

p = Path("src/core/orchestrator.py")
print("=== INTEGRAÇÃO FASE 19 ===")

if not p.exists():
    print("src/core/orchestrator.py não encontrado.")
    print("Use os arquivos de src/devops manualmente no fluxo atual da MILK.")
    raise SystemExit(1)

text = p.read_text(encoding="utf-8")

if "from devops.devops_manager import DevOpsManager" not in text:
    text = text.replace(
        "from datetime import datetime",
        "from datetime import datetime\nfrom devops.devops_manager import DevOpsManager"
    )

if "self.devops=DevOpsManager()" not in text.replace(" ",""):
    marker = "self.running=True"
    if marker in text:
        text = text.replace(marker, marker + "\n        self.devops = DevOpsManager()")

p.write_text(text, encoding="utf-8")
print("Integração básica aplicada ao orchestrator.py.")
print("Leia src/core/nlu_phase19_patch.txt para os intents.")
