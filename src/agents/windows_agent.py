import os
import subprocess
import webbrowser
from urllib.parse import quote_plus
import psutil

class WindowsAgent:
    APPS = {
        "calculadora": "calc.exe",
        "bloco de notas": "notepad.exe",
        "explorador": "explorer.exe",
        "gerenciador de tarefas": "taskmgr.exe",
        "paint": "mspaint.exe",
        "prompt de comando": "cmd.exe",
        "powershell": "powershell.exe",
    }

    def open_target(self, target):
        target=(target or "").lower().strip()

        if target in self.APPS:
            subprocess.Popen(self.APPS[target], shell=False)
            return f"Abrindo {target}."

        if target in ["configurações","configuracoes"]:
            os.startfile("ms-settings:")
            return "Abrindo configurações."

        if target=="navegador":
            webbrowser.open("https://www.google.com")
            return "Abrindo navegador."

        if target=="serviços":
            subprocess.Popen("services.msc", shell=True)
            return "Abrindo serviços do Windows."

        if target=="painel de controle":
            subprocess.Popen("control.exe", shell=False)
            return "Abrindo Painel de Controle."

        return f"Ainda não sei abrir {target}."

    def search_web(self, query):
        webbrowser.open("https://www.google.com/search?q="+quote_plus(query))
        return f"Pesquisando por {query}."

    def system_status(self):
        cpu=psutil.cpu_percent(interval=.4)
        ram=psutil.virtual_memory()
        disk=psutil.disk_usage("C:\\")
        return (
            f"CPU em {cpu:.0f} por cento, "
            f"memória em {ram.percent:.0f} por cento "
            f"e disco C em {disk.percent:.0f} por cento."
        )

    def top_processes(self):
        items=[]
        for p in psutil.process_iter(["name","memory_percent"]):
            try:
                items.append((p.info["memory_percent"] or 0,p.info["name"] or "processo"))
            except Exception:
                pass
        items.sort(reverse=True)
        return "Os processos mais pesados são: " + ", ".join(x[1] for x in items[:5]) + "."
