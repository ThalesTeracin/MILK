import json
from pathlib import Path
from datetime import datetime

PROFILES = Path("data/profiles")
PROFILES.mkdir(parents=True, exist_ok=True)

class ProfileManager:
    def create(self, name, display_name=None, preferences=None):
        safe = "".join(c for c in name.lower() if c.isalnum() or c in "-_")
        if not safe:
            raise ValueError("Nome inválido.")

        data = {
            "id": safe,
            "display_name": display_name or name,
            "created": datetime.now().isoformat(timespec="seconds"),
            "preferences": preferences or {
                "language":"pt-BR",
                "voice":"default",
                "permission_profile":"balanced"
            }
        }
        path = PROFILES / f"{safe}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def load(self, name):
        safe = "".join(c for c in name.lower() if c.isalnum() or c in "-_")
        path = PROFILES / f"{safe}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self):
        out=[]
        for p in PROFILES.glob("*.json"):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
        return out

    def update_preferences(self, name, updates):
        data=self.load(name)
        if not data:
            raise FileNotFoundError("Perfil não encontrado.")
        data.setdefault("preferences",{}).update(updates)
        path=PROFILES/f"{data['id']}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
