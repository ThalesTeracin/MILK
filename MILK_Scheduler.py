# =============================================================================
# SUBSTITUÍDO (Fase 3 - unificação de entry points, 2026-08-27).
# Não é mais iniciado como processo independente (pythonw MILK_Scheduler.py).
# A função run() abaixo continua sendo usada, mas agora é importada e
# chamada em uma thread por src/presence/unified_app.py, dentro do processo
# único iniciado por src/main.py. Mantido como referência/módulo reutilizável.
# =============================================================================
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

TASKS = Path("config/milk_tasks.json")

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

def run():
    print("MILK Scheduler iniciado.")
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
                    if cmd:
                        subprocess.Popen(cmd, shell=True)
        time.sleep(5)

if __name__ == "__main__":
    run()
