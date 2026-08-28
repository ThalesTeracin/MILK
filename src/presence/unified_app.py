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
import traceback
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageEnhance, ImageTk

from core.activity_state import atividade, definir_atividade, pulsar

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
ASSET = ROOT / "assets" / "milk_presence_source.png"
LOG = ROOT / "logs" / "presence.log"

# Fase 6, item 4: rótulo/cor do overlay por estado de core.activity_state,
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
        # Correção 1 da Task 6, achado 3: trava o fade-in a uma tentativa
        # por ciclo acordado (ver _idle_watch), pra não retentar a cada
        # segundo pra sempre se _ensure_overlay()/deiconify() falhar.
        self._fade_in_tentado = False

        self._load_avatar()

        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._scheduler_loop, daemon=True).start()
        threading.Thread(target=self._trabalho_loop, daemon=True).start()

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
        # atualizado em _animate() a partir de core.activity_state.
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
            # rótulo variam com core.activity_state (ouvindo/pensando/
            # falando), atualizado pelo loop de escuta e por MilkCore.say().
            # Fase 33, Task 6: handle() saiu da thread do Tk -- quem chama
            # o cérebro agora é _trabalho_loop/_trabalho_passo, numa thread
            # própria. Este after() nunca mais fica parado esperando uma
            # chamada de IA: o pulso continua se movendo durante o
            # "pensando", que era exatamente o congelamento que a Task 6
            # existiu para tirar.
            # O try/except protege só o desenho em si: um erro aqui custa
            # um quadro perdido, em vez de congelar o avatar de vez.
            try:
                activity = atividade()
                step, depth = PULSE_BY_ACTIVITY.get(activity, PULSE_DEFAULT)
                self.pulse = (self.pulse + step) % 60
                b = 0.96 + (depth * (1 - abs(30 - self.pulse) / 30))
                self._render_avatar(b)
                self._render_status(activity)
            except Exception:
                _log(f"Erro ao desenhar o avatar:\n{traceback.format_exc()}")
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
            definir_atividade("listening")
            try:
                heard = self.core.voice.listen()
            except Exception as e:
                _log(f"Erro na escuta: {e}")
                time.sleep(1)
                continue
            if heard:
                definir_atividade("thinking")
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

    def _trabalho_loop(self):
        """
        Consome a fila e chama o cérebro, FORA da thread do Tk.

        Antes, handle() rodava na thread do Tk: a chamada de IA inteira, a
        memória e o TTS aconteciam dentro da thread que deveria estar
        animando. O after() ficava parado e o avatar congelava em
        "pensando" -- exatamente quando devia se mexer.

        Esta thread nunca toca em Tkinter, que não aceita chamada de outra
        thread. Ela só muda estado; quem aparece e some é o _idle_watch, na
        thread do Tk, olhando core.state.
        """
        while self.running:
            self._trabalho_passo()

    def _trabalho_passo(self, timeout=0.2):
        """Um giro do laço. Separado para poder ser testado sem thread."""
        try:
            text = self.events.get(timeout=timeout)
        except queue.Empty:
            return

        self.last_activity = time.time()
        try:
            self.core.handle(text)
        except Exception:
            _log(f"Erro ao tratar {text!r}:\n{traceback.format_exc()}")
        finally:
            # Correção 1 da Task 6, achado 3: um handle() longo (ex.:
            # coding_task com build_and_repair) pode passar dos 90s de
            # idle_timeout enquanto ainda está rodando. Sem recarimbar
            # aqui, o _idle_watch -- que agora roda em paralelo, não mais
            # bloqueado pelo handle() como antes desta task -- decreta
            # sleep e some com o avatar no meio do trabalho. Recarimba
            # aconteça o que acontecer, sucesso ou exceção.
            self.last_activity = time.time()

    def _idle_watch(self):
        # Aparecer e sumir virou consequência do estado, não do comando: a
        # thread de trabalho não pode tocar em Tkinter, então quem decide
        # é este laço, que já roda na thread do Tk de segundo em segundo.
        try:
            if self.core.state == "sleep":
                # Reseta a trava de tentativa única do fade-in a cada
                # volta em que a MILK está dormindo: a próxima vez que
                # ela acordar merece uma tentativa nova, mesmo que a
                # tentativa anterior (de um ciclo acordado passado) tenha
                # falhado.
                self._fade_in_tentado = False
                if self.visible:
                    self._fade_out()
            elif not self.visible:
                # Correção 1 da Task 6, achado 2: self.visible só vira
                # True depois que _ensure_overlay()/deiconify() terminam
                # sem erro. Sem esta trava, uma falha nos dois deixaria
                # "not self.visible" sempre verdadeiro e o laço retentaria
                # o fade a cada segundo pra sempre -- uma linha de log por
                # tick. Escolhi marcar a tentativa (em vez de comparar
                # com o estado anterior) porque não precisa de mais um
                # atributo de "estado anterior" pra manter sincronizado; o
                # reset acima, ligado a "dormindo agora", já garante que
                # dormir e acordar de novo libera uma tentativa nova.
                if not self._fade_in_tentado:
                    self._fade_in_tentado = True
                    self._fade_in()

            if self.visible and self.core.state != "sleep" and self.last_activity:
                if time.time() - self.last_activity > self.idle_timeout:
                    self.core.state = "sleep"
                    definir_atividade("idle")
                    self._fade_out()
        except Exception:
            _log(f"Erro no controle de ociosidade:\n{traceback.format_exc()}")
        finally:
            # Correção 1 da Task 6, achado 2: pulsar() não pode ficar
            # dentro do try de cima. Antes, uma falha em qualquer fade
            # pulava pulsar() -- o carimbo do runtime state envelhecia e,
            # em até 5s, o mini overlay declarava a MILK desligada com ela
            # viva. Proteção própria: nem uma falha aqui pode derrubar o
            # after() de baixo.
            try:
                pulsar()
            except Exception:
                _log(f"Erro ao pulsar o carimbo de atividade:\n{traceback.format_exc()}")
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
