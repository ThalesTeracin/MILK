# =============================================================================
# SUBSTITUÍDO (Fase 3 - unificação de entry points, 2026-08-27).
# Este arquivo não é mais iniciado como processo independente. A lógica de
# overlay/avatar + wake word foi migrada para src/presence/unified_app.py,
# que roda dentro do processo único iniciado por src/main.py, reaproveitando
# o mesmo MilkCore (cérebro + NLU + gate de permissão) em vez de duplicar
# NaturalVoiceListener/NaturalSpeaker próprios como este arquivo fazia.
# Mantido apenas como referência histórica. Não editar/usar como entry point.
# =============================================================================
import os
import sys
import time
import queue
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from voice.listener import NaturalVoiceListener
from voice.speaker import NaturalSpeaker
from ai.persona import system_prompt, VOICE_HINT

ASSET = ROOT / "assets" / "milk_presence_source.png"
LOG = ROOT / "logs" / "presence.log"

WAKE_WORDS = ["milk", "milki", "milque", "milky"]
SLEEP_WORDS = ["pode descansar", "vá dormir", "va dormir", "dormir", "some milk", "até depois milk", "ate depois milk"]

class PresenceOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.listener = NaturalVoiceListener()
        self.speaker = NaturalSpeaker()

        self.events = queue.Queue()
        self.running = True
        self.visible = False
        self.conversation_active = False
        self.last_activity = 0
        self.idle_timeout = 90

        self.overlay = None
        self.canvas = None
        self.photo = None
        self.base_img = None
        self.pulse = 0

        self._load_avatar()

        threading.Thread(target=self._wake_loop, daemon=True).start()
        self.root.after(100, self._poll_events)
        self.root.after(120, self._animate)
        self.root.after(1000, self._idle_watch)

    def _log(self, text):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        print(text)

    def _load_avatar(self):
        if not ASSET.exists():
            return
        img = Image.open(ASSET).convert("RGBA")
        w, h = img.size

        # Crop central character, reducing the dashboard frame.
        crop = img.crop((int(w*0.25), int(h*0.08), int(w*0.75), int(h*0.88)))

        # Make the dark/navy background transparent so MILK appears "out of nowhere".
        px = crop.load()
        for y in range(crop.height):
            for x in range(crop.width):
                r,g,b,a = px[x,y]
                # Preserve bright holographic avatar, remove very dark background.
                lum = (r+g+b)/3
                blue_bias = b - r
                if lum < 38 and b < 70:
                    px[x,y] = (r,g,b,0)
                elif lum < 55 and blue_bias < 18:
                    px[x,y] = (r,g,b,max(0, int((lum-30)*8)))
        self.base_img = crop

    def _ensure_overlay(self):
        if self.overlay is not None:
            return

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)

        # Transparent window background.
        transparent_key = "#010203"
        win.configure(bg=transparent_key)
        try:
            win.wm_attributes("-transparentcolor", transparent_key)
        except Exception:
            pass

        width, height = 470, 650
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        # Appears on right side like a living desktop assistant.
        x = sw - width - 28
        y = max(20, (sh - height)//2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        canvas = tk.Canvas(win, width=width, height=height,
                           bg=transparent_key, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Small floating status text only, no enclosing "screen".
        canvas.create_text(width//2, 30,
                           text="MILK",
                           fill="#67e8ff",
                           font=("Segoe UI", 20, "bold"),
                           tags="title")

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
            self.overlay.attributes("-alpha", i/10)
            self.root.update_idletasks()
            time.sleep(0.025)

    def _fade_out(self):
        if not self.overlay or not self.visible:
            return
        for i in range(10, -1, -1):
            self.overlay.attributes("-alpha", i/10)
            self.root.update_idletasks()
            time.sleep(0.02)
        self.overlay.withdraw()
        self.visible = False

    def _wake_loop(self):
        self._log("MILK Presence aguardando chamada pelo nome.")
        while self.running:
            try:
                heard = self.listener.listen()
            except Exception as e:
                self._log(f"Erro na escuta: {e}")
                time.sleep(1)
                continue

            if not heard:
                continue

            low = heard.lower().strip()
            self._log(f"Ouvi: {heard}")

            if not self.conversation_active:
                if any(w in low for w in WAKE_WORDS):
                    self.events.put(("wake", heard))
                continue

            self.events.put(("conversation", heard))

    def _poll_events(self):
        try:
            while True:
                kind, text = self.events.get_nowait()
                if kind == "wake":
                    self._on_wake(text)
                elif kind == "conversation":
                    self._on_conversation(text)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_wake(self, original_text):
        self.conversation_active = True
        self.last_activity = time.time()
        self._fade_in()

        hour = time.localtime().tm_hour
        if hour < 12:
            greeting = "Bom dia. Estou aqui."
        elif hour < 18:
            greeting = "Boa tarde. Estou aqui."
        else:
            greeting = "Boa noite. Estou aqui."

        self.speaker.say(greeting)

        # If user said more than only wake word, pass remainder to main conversation process.
        low = original_text.lower()
        cleaned = original_text
        for w in WAKE_WORDS:
            if w in low:
                idx = low.find(w)
                cleaned = (original_text[:idx] + original_text[idx+len(w):]).strip(" ,.-")
                break

        if cleaned:
            self._send_to_brain(cleaned)

    def _on_conversation(self, text):
        self.last_activity = time.time()
        low = text.lower().strip()

        if any(x in low for x in SLEEP_WORDS):
            self.speaker.say("Tudo bem. Vou ficar por perto.")
            self.conversation_active = False
            self._fade_out()
            return

        self._send_to_brain(text)

    def _send_to_brain(self, text):
        """
        Send one utterance directly through the existing 9Router brain if possible.
        Falls back to local command execution for common Windows actions.
        """
        try:
            from ai.router import AIRouter
            ai = AIRouter()
        except Exception:
            ai = None

        low = text.lower()

        # Common local actions, zero tokens.
        if "calculadora" in low or "fazer conta" in low:
            subprocess.Popen(["calc.exe"])
            self.speaker.say("Abrindo calculadora.")
            return

        if "bloco de notas" in low or "notepad" in low:
            subprocess.Popen(["notepad.exe"])
            self.speaker.say("Abrindo bloco de notas.")
            return

        if "painel de controle" in low:
            subprocess.Popen(["control.exe"])
            self.speaker.say("Abrindo Painel de Controle.")
            return

        if ai and getattr(ai, "enabled", False):
            reply = ai.chat(
                system_prompt(VOICE_HINT),
                text,
                history=[],
                max_tokens=260
            )
            if reply:
                self.speaker.say(reply)
                return

        self.speaker.say("Eu ouvi você, mas não consegui acessar meu cérebro agora.")

    def _idle_watch(self):
        if self.conversation_active and self.last_activity:
            if time.time() - self.last_activity > self.idle_timeout:
                self.conversation_active = False
                self.speaker.say("Vou ficar em espera. É só me chamar.")
                self._fade_out()
        self.root.after(1000, self._idle_watch)

    def _animate(self):
        if self.visible and self.base_img is not None:
            self.pulse = (self.pulse + 1) % 60
            b = 0.96 + (0.08 * (1 - abs(30-self.pulse)/30))
            self._render_avatar(b)
        self.root.after(120, self._animate)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    PresenceOverlay().run()
