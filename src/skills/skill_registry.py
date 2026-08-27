import json
import os
import webbrowser
from pathlib import Path
import psutil

from core.proc import run_hidden

REGISTRY=Path("config/skills.json")

class SkillRegistry:
    def __init__(self):
        self.data=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def list_skills(self):
        return self.data.get("skills",[])

    def get(self, name):
        return next((s for s in self.list_skills() if s.get("name")==name),None)

class BuiltinSkills:
    @staticmethod
    def system_status(args=None):
        return {
            "cpu":psutil.cpu_percent(interval=.2),
            "memory":psutil.virtual_memory().percent,
            "disk":psutil.disk_usage("C:\\").percent
        }

    @staticmethod
    def git_status(args=None):
        p=run_hidden(["git","status","--short","--branch"],cwd=r"C:\JARVIS")
        return {"ok":p.returncode==0,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}

    @staticmethod
    def open_projects(args=None):
        path=Path(r"C:\JARVIS\projects")
        path.mkdir(parents=True,exist_ok=True)
        os.startfile(path)
        return {"ok":True,"path":str(path)}

    @staticmethod
    def web_search(args=None):
        q=(args or {}).get("query","")
        if not q:
            return {"ok":False,"error":"query ausente"}
        import urllib.parse
        webbrowser.open("https://www.google.com/search?q="+urllib.parse.quote_plus(q))
        return {"ok":True}
