import json
from pathlib import Path

CONFIG = Path("config/permission_profiles.json")

class PermissionManager:
    def __init__(self, profile="balanced"):
        self.data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.profile = profile if profile in self.data["profiles"] else "balanced"

    def set_profile(self, name):
        if name not in self.data["profiles"]:
            raise ValueError("Perfil inexistente.")
        self.profile=name

    def check(self, action):
        p=self.data["profiles"][self.profile]

        if action in p.get("deny", []):
            return {"allowed":False, "confirm":False, "reason":"Bloqueado pelo perfil."}

        if action in p.get("confirm", []):
            return {"allowed":True, "confirm":True, "reason":"Confirmação obrigatória."}

        return {"allowed":True, "confirm":False, "reason":"Permitido."}
