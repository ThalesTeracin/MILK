from pathlib import Path
import json
from src.memory.long_memory import LongMemory

legacy = Path("data/session_memory.json")
db = LongMemory()

if legacy.exists():
    try:
        data = json.loads(legacy.read_text(encoding="utf-8"))
        for item in data.get("history", []):
            role = item.get("role", "user")
            content = item.get("content", "")
            if content:
                db.add_message(role, content)
        last_project = data.get("last_project")
        if last_project:
            name = str(last_project).replace("\\","/").rstrip("/").split("/")[-1]
            db.remember_project(name=name, path=last_project, status="active", summary="Migrado da memória da Fase 15.")
        print("Migração concluída.")
    except Exception as e:
        print("Falha ao migrar:", e)
else:
    print("Nenhuma memória antiga encontrada. O banco novo já está pronto.")

print("Banco:", db.db_path)
print("Status:", db.stats())
db.close()
