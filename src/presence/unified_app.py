"""
Processo único supervisionado do MILK (Fase 3 da unificação de entry points).

Antes desta fase, o assistente rodava como vários processos Python
independentes e sem sincronia entre si:

  - MILK_Presence.py       overlay/avatar + wake word + loop de voz e de
                            "cérebro" próprios (não usava o orchestrator,
                            não passava pelo PermissionManager da Fase 2).
  - Conversar_Com_MILK.py  outro loop de voz duplicado (idem acima),
                            iniciado manualmente pelo Command Center.
  - MILK_Scheduler.py      loop de tarefas agendadas.
  - MILK_Command_Center.py dashboard manual que, entre outras coisas,
                            iniciava Conversar_Com_MILK.py como subprocess.

Isso causava concorrência pelo mesmo microfone (mais de um
NaturalVoiceListener podia estar ativo ao mesmo tempo) e permitia executar
ações do "cérebro" sem passar pelo gate de permissão real.

Este módulo é o novo processo único: instancia um único
core.orchestrator.MilkCore (cérebro + NLU + gate de permissão + memória),
um único NaturalVoiceListener/NaturalSpeaker (os do próprio MilkCore) e
mantém o overlay/avatar (Tkinter) e o scheduler de tarefas rodando como
threads dentro do mesmo processo.

MILK_Presence.py, Conversar_Com_MILK.py e MILK_Scheduler.py continuam no
repositório como referência (não foram apagados), mas não são mais
chamados como processos independentes -- ver aviso no topo de cada um.
"""

import queue
import sys
import threading
import time
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageEnhance, ImageTk

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
ASSET = ROOT / "assets" / "milk_presence_source.png"
LOG = ROOT / "logs" / "presence.log"

# Fase 6, item 4: rótulo/cor do overlay por estado de MilkCore.activity,
# e velocidade/profundidade do pulso do avatar em _animate(). "idle" cai no
# valor default de PULSE_BY_ACTIVITY (pulso suave, sem rótulo).
ACTIVITY_LABEL = {
    "listening": ("ouvindo…", "#67e8ff"),
    "thinking": ("pensando…", "#f4c95d"),
    "speaking": ("falando…", "#7CFC98"),
}
PULSE_BY_ACTIVITY = {
    "speaking": (2, 0.14),
    "thinking": (1, 0.05),
}
PULSE_DEFAULT = (1, 0.08)


def _ensure_paths():
    """Garante que src/ (imports internos) e ROOT (MILK_Scheduler.py) estão no sys.path."""
    for p in (str(SRC), str(ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


def _log(text):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")


class UnifiedApp:
    """
    Overlay/avatar de presença ligado ao cérebro único (MilkCore).

    O avatar (carregamento de imagem, fade in/out, animação de pulso) é o
    mesmo comportamento de MILK_Presence.py -- só a origem da voz e da
    decisão (ouvir e decidir o que fazer) passou a ser o MilkCore, em vez
    de um loop de voz/IA duplicado.
    """

    def __init__(self, core):
        self.core = core  # instância de core.orchestrator.MilkCore

        self.root = tk.Tk()
        self.root.withdraw()

        self.events = queue.Queue()
        self.running = True
        self.visible = False
        self.last_activity = 0
        self.idle_timeout = 90

        self.overlay = None
        self.canvas = None
        self.photo = None
        self.base_img = None
        self.pulse = 0

        self._load_avatar()

        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._scheduler_loop, daemon=True).start()

        self.root.after(100, self._poll_events)
        self.root.after(120, self._animate)
        self.root.after(1000, self._idle_watch)

    # ---------------- avatar (portado de MILK_Presence.py) ----------------

    def _load_avatar(self):
        if not ASSET.exists():
            return
        img = Image.open(ASSET).convert("RGBA")
        w, h = img.size

        crop = img.crop((int(w * 0.25), int(h * 0.08), int(w * 0.75), int(h * 0.88)))

        px = crop.load()
        for y in range(crop.height):
            for x in range(crop.width):
                r, g, b, a = px[x, y]
                lum = (r + g + b) / 3
                blue_bias = b - r
                if lum < 38 and b < 70:
                    px[x, y] = (r, g, b, 0)
                elif lum < 55 and blue_bias < 18:
                    px[x, y] = (r, g, b, max(0, int((lum - 30) * 8)))
        self.base_img = crop

    def _ensure_overlay(self):
        if self.overlay is not None:
            return

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)

        transparent_key = "#010203"
        win.configure(bg=transparent_key)
        try:
            win.wm_attributes("-transparentcolor", transparent_key)
        except Exception:
            pass

        width, height = 470, 650
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        x = sw - width - 28
        y = max(20, (sh - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        canvas = tk.Canvas(win, width=width, height=height,
                            bg=transparent_key, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        canvas.create_text(width // 2, 30,
                            text="MILK",
                            fill="#67e8ff",
                            font=("Segoe UI", 20, "bold"),
                            tags="title")

        # Fase 6, item 4: rótulo de estado (ouvindo/pensando/falando),
        # atualizado em _animate() a partir de self.core.activity.
        canvas.create_text(width // 2, 58,
                            text="",
                            fill="#67e8ff",
                            font=("Segoe UI", 11),
                            tags="status")

        self.overlay = win
        self.canvas = canvas
        self._render_avatar(1.0)

    def _render_avatar(self, brightness=1.0):
        if self.base_img is None or self.canvas is None:
            return
        img = ImageEnhance.Brightness(self.base_img).enhance(brightness)
        img.thumbnail((440, 585), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("avatar")
        self.canvas.create_image(235, 335, image=self.photo, anchor="center", tags="avatar")

    def _fade_in(self):
        self._ensure_overlay()
        self.overlay.deiconify()
        self.visible = True
        for i in range(0, 11):
            self.overlay.attributes("-alpha", i / 10)
            self.root.update_idletasks()
            time.sleep(0.025)

    def _fade_out(self):
        if not self.overlay or not self.visible:
            return
        for i in range(10, -1, -1):
            self.overlay.attributes("-alpha", i / 10)
            self.root.update_idletasks()
            time.sleep(0.02)
        self.overlay.withdraw()
        self.visible = False

    def _animate(self):
        if self.visible and self.base_img is not None:
            # Fase 6, item 4: velocidade/profundidade do pulso e cor do
            # rótulo variam com self.core.activity (ouvindo/pensando/
            # falando), atualizado pelo loop de escuta e por MilkCore.say().
            # Limitação conhecida: handle() roda de forma síncrona na
            # mesma thread do Tk, então durante uma chamada de IA longa o
            # after() deste método fica parado -- a cor/rótulo já mudou
            # para "pensando" antes do bloqueio, mas o pulso não anima
            # durante a espera. Ainda assim é uma melhora real sobre o
            # pulso único e estático que existia antes.
            activity = getattr(self.core, "activity", "idle")
            step, depth = PULSE_BY_ACTIVITY.get(activity, PULSE_DEFAULT)
            self.pulse = (self.pulse + step) % 60
            b = 0.96 + (depth * (1 - abs(30 - self.pulse) / 30))
            self._render_avatar(b)
            self._render_status(activity)
        self.root.after(120, self._animate)

    def _render_status(self, activity):
        if self.canvas is None:
            return
        label, color = ACTIVITY_LABEL.get(activity, ("", "#67e8ff"))
        self.canvas.itemconfigure("status", text=label, fill=color)

    # ---------------- escuta + cérebro único (MilkCore) --------------------

    def _listen_loop(self):
        """
        Único NaturalVoiceListener ativo no processo: o do próprio MilkCore
        (self.core.voice). Antes, MILK_Presence.py e Conversar_Com_MILK.py
        criavam instâncias adicionais, concorrendo pelo mesmo microfone.
        """
        _log("Loop de escuta unificado iniciado.")
        while self.running:
            self.core.activity = "listening"
            try:
                heard = self.core.voice.listen()
            except Exception as e:
                _log(f"Erro na escuta: {e}")
                time.sleep(1)
                continue
            if heard:
                self.core.activity = "thinking"
                _log(f"Ouvi: {heard}")
                self.events.put(heard)

    def _scheduler_loop(self):
        """
        Roda a lógica de MILK_Scheduler.py (tarefas agendadas em
        config/milk_tasks.json) como thread deste processo, em vez de
        processo separado.
        """
        try:
            import MILK_Scheduler as scheduler
        except Exception as e:
            _log(f"Scheduler indisponível: {e}")
            return
        try:
            scheduler.run()
        except Exception as e:
            _log(f"Scheduler encerrou com erro: {e}")

    def _poll_events(self):
        try:
            while True:
                text = self.events.get_nowait()
                self._on_heard(text)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_heard(self, text):
        self.last_activity = time.time()
        was_sleep = (self.core.state == "sleep")
        low = text.lower().strip()

        # Aparição instantânea do avatar ao detectar a wake word, antes de
        # processar o comando (MilkCore.handle já trata a lógica de
        # sleep/ready e a própria wake word "milk").
        if was_sleep and "milk" in low:
            self._fade_in()

        self.core.handle(text)

        if self.core.state == "sleep" and self.visible:
            self._fade_out()

    def _idle_watch(self):
        if self.visible and self.core.state != "sleep" and self.last_activity:
            if time.time() - self.last_activity > self.idle_timeout:
                self.core.state = "sleep"
                self.core.activity = "idle"
                self._fade_out()
        self.root.after(1000, self._idle_watch)

    def run(self):
        self.root.mainloop()


def run():
    """Ponto de entrada do processo único: cria o MilkCore e o overlay."""
    _ensure_paths()
    from core.orchestrator import MilkCore

    core = MilkCore()
    app = UnifiedApp(core)
    _log("MILK unificado iniciado (cérebro + overlay + scheduler em um único processo).")
    app.run()


if __name__ == "__main__":
    run()
