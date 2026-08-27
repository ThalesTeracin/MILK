import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parallel.task_orchestrator import TaskOrchestrator

def ok_job(name, delay):
    time.sleep(delay)
    return {"ok": True, "stdout": f"{name} concluído", "code": 0}

def unsafe_job():
    time.sleep(0.2)
    return {"ok": True, "stdout": "ação sequencial concluída", "code": 0}

print("=== TESTE MILK FASES 23 + 24 ===")

o = TaskOrchestrator(ai=None, max_workers=3)

jobs = [
    {
        "name": "verificar_config",
        "func": ok_job,
        "args": ["config", 0.6],
        "safe_parallel": True
    },
    {
        "name": "verificar_logs",
        "func": ok_job,
        "args": ["logs", 0.5],
        "safe_parallel": True
    },
    {
        "name": "verificar_memoria",
        "func": ok_job,
        "args": ["memoria", 0.4],
        "safe_parallel": True
    },
    {
        "name": "acao_sequencial",
        "func": unsafe_job,
        "safe_parallel": False
    }
]

result = o.execute_and_review("Teste integrado 23+24", jobs)

print("\nExecução:")
for item in result["execution"]:
    print("-", item)

print("\nSelf Review:")
print(result["review"])

if result["review"].get("ok"):
    print("\n✅ FASES 23 + 24 VALIDADAS.")
else:
    print("\n⚠️ Execução terminou, mas Self Review não aprovou.")
