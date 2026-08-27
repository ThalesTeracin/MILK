from pathlib import Path
import json, datetime

class SessionMemory:
    def __init__(self,path="data/session_memory.json"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.data={"history":[],"last_command":None,"last_project":None,"last_screenshot":None,"last_url":None,"pending_action":None}
        if self.path.exists():
            try: self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception: pass

    def remember(self,**kwargs):
        self.data.update(kwargs)
        self.path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding="utf-8")

    def add_history(self,role,content):
        self.data.setdefault("history",[]).append({
            "time":datetime.datetime.now().isoformat(timespec="seconds"),
            "role":role,"content":content
        })
        self.data["history"]=self.data["history"][-40:]
        self.remember()
