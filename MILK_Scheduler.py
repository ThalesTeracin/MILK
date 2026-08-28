# =============================================================================
# SUBSTITUÍDO (Fase 3 - unificação de entry points, 2026-08-27).
# Não é mais iniciado como processo independente (pythonw MILK_Scheduler.py).
# A função run() abaixo continua sendo usada, mas agora é importada e
# chamada em uma thread por src/presence/unified_app.py, dentro do processo
# único iniciado por src/main.py. Mantido como referência/módulo reutilizável.
# =============================================================================
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from security.permission_manager import PermissionManager

TASKS = Path("config/milk_tasks.json")
LOG = Path("logs/scheduler.log")

def load_tasks():
    if not TASKS.exists():
        return []
    try:
        return json.loads(TASKS.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_tasks(tasks):
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    TASKS.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

def _log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def run():
    print("MILK Scheduler iniciado.")
    # Fase 6, item 3: antes rodava comandos de shell arbitrários (do JSON de
    # config) sem passar pelo mesmo gate de permissão usado pelo resto do
    # MilkCore -- inconsistente com a Fase 2 (gate de permissão real).
    # Ação "scheduled_task": bloqueada só no perfil "safe"; "balanced"
    # (padrão do MilkCore) e "developer" continuam permitindo, preservando
    # o comportamento atual para quem já usa tarefas agendadas.
    permissions = PermissionManager(profile="balanced")
    last_minute = None
    while True:
        now = datetime.now()
        key = now.strftime("%Y-%m-%d %H:%M")
        if key != last_minute:
            last_minute = key
            tasks = load_tasks()
            for task in tasks:
                if not task.get("enabled", True):
                    continue
                if task.get("time") == now.strftime("%H:%M"):
                    cmd = task.get("command")
                    if not cmd:
                        continue
                    check = permissions.check("scheduled_task")
                    if not check["allowed"]:
                        _log(
                            f"Tarefa '{task.get('name', cmd)}' bloqueada pelo "
                            f"perfil de permissão ({check['reason']}). Comando: {cmd}"
                        )
                        continue
                    subprocess.Popen(cmd, shell=True)
                    _log(f"Tarefa executada: {cmd}")
        time.sleep(5)

if __name__ == "__main__":
    run()
