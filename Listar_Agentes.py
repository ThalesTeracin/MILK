import json
from pathlib import Path
for a in json.loads(Path("config/agents.json").read_text(encoding="utf-8")):
    print(f"{a['name']:<24} - {a['role']}")
