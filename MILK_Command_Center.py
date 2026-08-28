# =============================================================================
# PAPEL ALTERADO (Fase 3 - unificação de entry points, 2026-08-27).
# Não faz mais parte do conjunto "sempre ativo" em background -- o
# assistente em si (cérebro + overlay + scheduler) roda como processo único
# via src/main.py (ver src/presence/unified_app.py), supervisionado por
# Tarefa Agendada do Windows (ver installer/registrar_tarefa_agendada.ps1).
# Este arquivo continua existindo apenas como painel manual/on-demand
# (status, logs, atalhos) que o usuário abre quando quiser -- não é mais
# iniciado automaticamente e não deve ser tratado como entry point do
# assistente. O botão "iniciar assistente" agora chama src/main.py.
# =============================================================================
import os
import sys
import time
import queue
import sqlite3
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

import psutil
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import tkinter as tk
from tkinter import ttk, messagebox

from core.config import config_path

ROOT = Path(__file__).resolve().parent
ASSET = ROOT / "assets" / "milk_phase20.png"
LOG = ROOT / "logs" / "command_center.log"
ENV = ROOT / ".env"
MEMORY_DB = ROOT / "data" / "milk_memory.db"
PROJECTS = ROOT / "projects"

BG = "#07111f"
PANEL = "#0b1a2c"
PANEL2 = "#0e243b"
TEXT = "#eaf7ff"
MUTED = "#8fb4cc"
CYAN = "#4bdfff"
BLUE = "#4285ff"
GREEN = "#3ee6a8"
WARN = "#ffd166"
RED = "#ff6b6b"

class MilkCommandCenter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MILK — Fase 20 | Command Center")
        self.geometry("1440x900")
        self.minsize(1180, 760)
        self.configure(bg=BG)

        self.assistant_proc = None
        self.proc_thread = None
        self.output_queue = queue.Queue()
        self.avatar_photo = None
        self.avatar_base = None
        self.avatar_phase = 0
        self.alive = True

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_style()
        self._build_layout()
        self._load_avatar()
        self._refresh_all()
        self._poll_process_output()
        self._animate_avatar()

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar",
                        troughcolor="#15283d",
                        background=CYAN,
                        bordercolor="#15283d",
                        lightcolor=CYAN,
                        darkcolor=CYAN)

    def _build_layout(self):
        # Top bar
        top = tk.Frame(self, bg="#091625", height=62)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="MILK", font=("Segoe UI", 24, "bold"),
                 fg=TEXT, bg="#091625").pack(side="left", padx=(22,8))
        tk.Label(top, text="FASE 20 · COMMAND CENTER",
                 font=("Segoe UI", 12, "bold"),
                 fg=CYAN, bg="#091625").pack(side="left", pady=4)

        self.clock_lbl = tk.Label(top, text="", font=("Segoe UI", 11),
                                  fg=MUTED, bg="#091625")
        self.clock_lbl.pack(side="right", padx=20)

        self.online_dot = tk.Label(top, text="● ONLINE", font=("Segoe UI", 10, "bold"),
                                   fg=GREEN, bg="#091625")
        self.online_dot.pack(side="right", padx=8)

        # Main
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=14, pady=14)

        left = tk.Frame(main, bg=BG, width=300)
        center = tk.Frame(main, bg=BG)
        right = tk.Frame(main, bg=BG, width=320)
        left.pack(side="left", fill="y", padx=(0,10))
        center.pack(side="left", fill="both", expand=True)
        right.pack(side="right", fill="y", padx=(10,0))
        left.pack_propagate(False)
        right.pack_propagate(False)

        # Left cards
        self.sys_card = self._card(left, "SISTEMA")
        self.cpu_lbl, self.cpu_bar = self._metric(self.sys_card, "CPU")
        self.ram_lbl, self.ram_bar = self._metric(self.sys_card, "MEMÓRIA")
        self.disk_lbl, self.disk_bar = self._metric(self.sys_card, "DISCO C:")

        self.memory_card = self._card(left, "MEMÓRIA")
        self.memory_info = tk.Label(self.memory_card, text="Carregando...",
                                    fg=TEXT, bg=PANEL, justify="left",
                                    font=("Segoe UI", 10))
        self.memory_info.pack(anchor="w", padx=14, pady=(2,12))

        self.projects_card = self._card(left, "PROJETOS")
        self.projects_info = tk.Label(self.projects_card, text="Carregando...",
                                      fg=TEXT, bg=PANEL, justify="left",
                                      font=("Segoe UI", 10))
        self.projects_info.pack(anchor="w", padx=14, pady=(2,8))
        self._button(self.projects_card, "Abrir projetos", self.open_projects).pack(fill="x", padx=14, pady=(0,12))

        self.git_card = self._card(left, "GIT / GITHUB")
        self.git_info = tk.Label(self.git_card, text="Carregando...",
                                 fg=TEXT, bg=PANEL, justify="left",
                                 font=("Segoe UI", 10))
        self.git_info.pack(anchor="w", padx=14, pady=(2,8))
        self._button(self.git_card, "Testar DevOps", self.run_devops_test).pack(fill="x", padx=14, pady=(0,12))

        # Center
        hero = tk.Frame(center, bg=PANEL2, highlightthickness=1,
                        highlightbackground="#173a58")
        hero.pack(fill="both", expand=True)

        self.avatar_canvas = tk.Canvas(hero, bg=PANEL2, highlightthickness=0)
        self.avatar_canvas.pack(fill="both", expand=True, padx=12, pady=12)

        status_strip = tk.Frame(center, bg=BG)
        status_strip.pack(fill="x", pady=(10,0))

        self.voice_state = self._status_chip(status_strip, "VOZ", "PRONTA")
        self.ai_state = self._status_chip(status_strip, "IA", "VERIFICANDO")
        self.whisper_state = self._status_chip(status_strip, "WHISPER", "VERIFICANDO")
        self.task_state = self._status_chip(status_strip, "ASSISTENTE", "PARADA")

        # Bottom command/console
        bottom = tk.Frame(center, bg=PANEL, highlightthickness=1,
                          highlightbackground="#173a58")
        bottom.pack(fill="x", pady=(10,0))

        self.console = tk.Text(bottom, height=7, bg="#07131f", fg=TEXT,
                               insertbackground=CYAN, relief="flat",
                               font=("Consolas", 10), wrap="word")
        self.console.pack(fill="x", padx=10, pady=(10,6))
        self.console.insert("end", "MILK Command Center pronto.\n")
        self.console.configure(state="disabled")

        cmdrow = tk.Frame(bottom, bg=PANEL)
        cmdrow.pack(fill="x", padx=10, pady=(0,10))
        self.command_entry = tk.Entry(cmdrow, bg="#0b2135", fg=TEXT,
                                      insertbackground=CYAN, relief="flat",
                                      font=("Segoe UI", 11))
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.command_entry.bind("<Return>", lambda e: self.quick_command())
        self._button(cmdrow, "Executar", self.quick_command, width=12).pack(side="left", padx=(8,0))

        # Right cards
        self.ai_card = self._card(right, "PROVEDOR IA")
        self.ai_info = tk.Label(self.ai_card, text="Carregando...",
                                fg=TEXT, bg=PANEL, justify="left",
                                font=("Segoe UI", 10), wraplength=275)
        self.ai_info.pack(anchor="w", padx=14, pady=(2,8))
        self._button(self.ai_card, "Testar 9Router", self.run_ai_test).pack(fill="x", padx=14, pady=(0,12))

        self.voice_card = self._card(right, "VOZ / CONVERSAÇÃO")
        self.voice_info = tk.Label(self.voice_card,
                                   text="Whisper local + resposta falada",
                                   fg=TEXT, bg=PANEL, justify="left",
                                   font=("Segoe UI", 10))
        self.voice_info.pack(anchor="w", padx=14, pady=(2,8))
        self.start_btn = self._button(self.voice_card, "▶ Iniciar MILK", self.start_assistant)
        self.start_btn.pack(fill="x", padx=14, pady=(0,6))
        self.stop_btn = self._button(self.voice_card, "■ Parar MILK", self.stop_assistant)
        self.stop_btn.pack(fill="x", padx=14, pady=(0,12))

        self.actions_card = self._card(right, "ATALHOS")
        for text, func in [
            ("Abrir 9Router", self.open_9router),
            ("Abrir logs", self.open_logs),
            ("Abrir memória", self.open_memory),
            ("Abrir PowerShell em C:\\JARVIS", self.open_powershell),
        ]:
            self._button(self.actions_card, text, func).pack(fill="x", padx=14, pady=4)

        self.phase_card = self._card(right, "FASE 20")
        tk.Label(self.phase_card,
                 text="Avatar MILK vivo na tela\nCommand Center\nStatus em tempo real\nVoz + IA + Memória + DevOps",
                 fg=TEXT, bg=PANEL, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(2,12))

        self.after(1000, self._tick_clock)

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground="#173a58")
        f.pack(fill="x", pady=(0,10))
        tk.Label(f, text=title, font=("Segoe UI", 11, "bold"),
                 fg=CYAN, bg=PANEL).pack(anchor="w", padx=14, pady=(12,8))
        return f

    def _metric(self, parent, label):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=4)
        lbl = tk.Label(row, text=f"{label}: 0%", fg=TEXT, bg=PANEL,
                       font=("Segoe UI", 9))
        lbl.pack(anchor="w")
        pb = ttk.Progressbar(row, maximum=100)
        pb.pack(fill="x", pady=(2,4))
        return lbl, pb

    def _button(self, parent, text, command, width=None):
        return tk.Button(parent, text=text, command=command,
                         bg="#12314d", fg=TEXT, activebackground="#1b4a72",
                         activeforeground=TEXT, relief="flat",
                         cursor="hand2", font=("Segoe UI", 9, "bold"),
                         width=width)

    def _status_chip(self, parent, title, value):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground="#173a58")
        f.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(f, text=title, fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 8, "bold")).pack()
        lbl = tk.Label(f, text=value, fg=GREEN, bg=PANEL,
                       font=("Segoe UI", 10, "bold"))
        lbl.pack(pady=(0,4))
        return lbl

    def _load_avatar(self):
        if not ASSET.exists():
            self._log("Imagem da MILK não encontrada em assets/milk_phase20.png")
            return
        try:
            img = Image.open(ASSET).convert("RGB")
            # crop a central region to emphasize MILK herself
            w, h = img.size
            crop = img.crop((int(w*0.18), int(h*0.08), int(w*0.82), int(h*0.92)))
            self.avatar_base = crop
            self._render_avatar(1.0)
        except Exception as e:
            self._log(f"Erro ao carregar avatar: {e}")

    def _render_avatar(self, brightness=1.0):
        if self.avatar_base is None:
            return
        cw = max(420, self.avatar_canvas.winfo_width() or 700)
        ch = max(500, self.avatar_canvas.winfo_height() or 650)
        img = ImageEnhance.Brightness(self.avatar_base).enhance(brightness)
        img = ImageOps.contain(img, (cw-30, ch-30), Image.Resampling.LANCZOS)
        self.avatar_photo = ImageTk.PhotoImage(img)
        self.avatar_canvas.delete("all")
        self.avatar_canvas.create_image(cw//2, ch//2, image=self.avatar_photo, anchor="center")
        self.avatar_canvas.create_text(
            cw//2, 30, text="MILK · ONLINE",
            fill=CYAN, font=("Segoe UI", 15, "bold")
        )

    def _animate_avatar(self):
        if not self.alive:
            return
        self.avatar_phase = (self.avatar_phase + 1) % 80
        # subtle breathing/glow pulse
        p = self.avatar_phase
        brightness = 0.96 + (0.08 * (1 - abs(40-p)/40))
        try:
            self._render_avatar(brightness)
        except Exception:
            pass
        self.after(120, self._animate_avatar)

    def _tick_clock(self):
        self.clock_lbl.config(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _refresh_all(self):
        self.refresh_system()
        self.refresh_memory()
        self.refresh_projects()
        self.refresh_git()
        self.refresh_ai()
        self.refresh_whisper()
        self.after(2500, self._refresh_all)

    def refresh_system(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\").percent
            self.cpu_lbl.config(text=f"CPU: {cpu:.0f}%"); self.cpu_bar["value"] = cpu
            self.ram_lbl.config(text=f"MEMÓRIA: {ram:.0f}%"); self.ram_bar["value"] = ram
            self.disk_lbl.config(text=f"DISCO C:: {disk:.0f}%"); self.disk_bar["value"] = disk
        except Exception:
            pass

    def refresh_memory(self):
        try:
            if not MEMORY_DB.exists():
                self.memory_info.config(text="Banco ainda não encontrado.")
                return
            conn = sqlite3.connect(MEMORY_DB)
            cur = conn.cursor()
            vals = {}
            for table in ["conversations","projects","decisions","errors"]:
                try:
                    vals[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except Exception:
                    vals[table] = 0
            conn.close()
            self.memory_info.config(
                text=f"Conversas: {vals['conversations']}\nProjetos: {vals['projects']}\nDecisões: {vals['decisions']}\nErros: {vals['errors']}"
            )
        except Exception as e:
            self.memory_info.config(text=f"Erro: {e}")

    def refresh_projects(self):
        try:
            PROJECTS.mkdir(parents=True, exist_ok=True)
            dirs = [p for p in PROJECTS.iterdir() if p.is_dir()]
            self.projects_info.config(text=f"Projetos locais: {len(dirs)}")
        except Exception as e:
            self.projects_info.config(text=f"Erro: {e}")

    def refresh_git(self):
        try:
            p = subprocess.run(["git","--version"], capture_output=True, text=True, timeout=6)
            text = p.stdout.strip() if p.returncode == 0 else "Git indisponível"
            self.git_info.config(text=text)
        except Exception:
            self.git_info.config(text="Git indisponível")

    def _read_env(self):
        data = {}
        if ENV.exists():
            for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k,v = line.split("=",1)
                    data[k.strip()] = v.strip()
        return data

    def refresh_ai(self):
        env = self._read_env()
        base = env.get("NINEROUTER_BASE_URL","")
        model = env.get("NINEROUTER_MODEL","")
        key = env.get("NINEROUTER_API_KEY","")
        ok = bool(base and model and key)
        self.ai_state.config(text="ATIVA" if ok else "NÃO CONFIG.", fg=GREEN if ok else WARN)
        self.ai_info.config(text=f"Base: {base or '—'}\nModelo: {model or '—'}\nChave: {'carregada' if key else 'ausente'}")

    def refresh_whisper(self):
        cfg = config_path("whisper_local.json")
        ok = cfg.exists()
        self.whisper_state.config(text="PRONTO" if ok else "AUSENTE", fg=GREEN if ok else WARN)

    def _log(self, text):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {text}\n")
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def start_assistant(self):
        # Fase 3 (2026-08-27): antes iniciava Conversar_Com_MILK.py, um
        # "cérebro" duplicado sem NLU completo nem gate de permissão. Agora
        # inicia src/main.py --headless, que usa o MilkCore real (NLU +
        # PermissionManager). Se o processo único (src/main.py, com overlay)
        # já estiver rodando via Tarefa Agendada, NÃO clique aqui -- rodar
        # dois MilkCore ao mesmo tempo disputa o mesmo microfone.
        if self.assistant_proc and self.assistant_proc.poll() is None:
            self._log("MILK já está em execução.")
            return
        script = ROOT / "src" / "main.py"
        if not script.exists():
            messagebox.showerror("MILK", "src/main.py não encontrado em C:\\JARVIS")
            return
        try:
            self.assistant_proc = subprocess.Popen(
                [sys.executable, "-u", str(script), "--headless"],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.task_state.config(text="RODANDO", fg=GREEN)
            self.voice_state.config(text="OUVINDO", fg=CYAN)
            self._log("Assistente de voz iniciado.")
            self.proc_thread = threading.Thread(target=self._read_proc_output, daemon=True)
            self.proc_thread.start()
        except Exception as e:
            self._log(f"Falha ao iniciar MILK: {e}")

    def _read_proc_output(self):
        try:
            for line in self.assistant_proc.stdout:
                self.output_queue.put(line.rstrip())
        except Exception:
            pass

    def _poll_process_output(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                self._log(line)
                low = line.lower()
                if "reconhecido:" in low:
                    self.voice_state.config(text="ENTENDEU", fg=GREEN)
                elif "milk:" in low:
                    self.voice_state.config(text="FALANDO", fg=CYAN)
                elif "fale normalmente" in low or "ouvindo" in low:
                    self.voice_state.config(text="OUVINDO", fg=CYAN)
                if "ia:" in low and "não configur" not in low:
                    self.ai_state.config(text="ATIVA", fg=GREEN)
        except queue.Empty:
            pass

        if self.assistant_proc and self.assistant_proc.poll() is not None:
            self.task_state.config(text="PARADA", fg=MUTED)
            self.voice_state.config(text="PRONTA", fg=GREEN)

        self.after(120, self._poll_process_output)

    def stop_assistant(self):
        if self.assistant_proc and self.assistant_proc.poll() is None:
            try:
                self.assistant_proc.terminate()
                self._log("Assistente interrompido.")
            except Exception as e:
                self._log(f"Erro ao parar assistente: {e}")
        self.task_state.config(text="PARADA", fg=MUTED)
        self.voice_state.config(text="PRONTA", fg=GREEN)

    def quick_command(self):
        cmd = self.command_entry.get().strip()
        if not cmd:
            return
        self._log(f"Você: {cmd}")
        self.command_entry.delete(0, "end")
        # Safe GUI shortcuts
        low = cmd.lower()
        if "calculadora" in low:
            subprocess.Popen(["calc.exe"])
            self._log("MILK: Abrindo calculadora.")
        elif "bloco de notas" in low:
            subprocess.Popen(["notepad.exe"])
            self._log("MILK: Abrindo bloco de notas.")
        elif "9router" in low:
            self.open_9router()
        elif "projetos" in low:
            self.open_projects()
        else:
            self._log("MILK: Para comandos livres, use o modo de voz/IA.")

    def run_ai_test(self):
        self._run_script(ROOT/"Testar_9Router_Direto.py", "Teste 9Router")

    def run_devops_test(self):
        self._run_script(ROOT/"Testar_DevOps.py", "Teste DevOps")

    def _run_script(self, script, label):
        if not script.exists():
            self._log(f"{label}: arquivo não encontrado.")
            return
        try:
            p = subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            def worker():
                out, _ = p.communicate()
                self.output_queue.put(f"=== {label} ===")
                for line in (out or "").splitlines():
                    self.output_queue.put(line)
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            self._log(f"{label}: {e}")

    def open_9router(self):
        webbrowser.open("http://localhost:20128/dashboard")

    def open_projects(self):
        PROJECTS.mkdir(parents=True, exist_ok=True)
        os.startfile(PROJECTS)

    def open_logs(self):
        logs = ROOT/"logs"
        logs.mkdir(exist_ok=True)
        os.startfile(logs)

    def open_memory(self):
        data = ROOT/"data"
        data.mkdir(exist_ok=True)
        os.startfile(data)

    def open_powershell(self):
        subprocess.Popen([
            "powershell.exe",
            "-NoExit",
            "-Command",
            "Set-Location 'C:\\JARVIS'"
        ])

    def on_close(self):
        self.alive = False
        if self.assistant_proc and self.assistant_proc.poll() is None:
            if messagebox.askyesno("MILK", "A MILK está ativa. Deseja encerrar tudo?"):
                self.stop_assistant()
            else:
                return
        self.destroy()

if __name__ == "__main__":
    app = MilkCommandCenter()
    app.mainloop()
