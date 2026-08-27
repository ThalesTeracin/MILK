"""
Ponto de entrada único do MILK (Fase 3 - unificação de entry points).

Uso normal (processo único: cérebro + overlay/avatar + scheduler):
    python src/main.py

Modo texto/sem overlay (debug, sem Tkinter, sem avatar):
    python src/main.py --headless

Antes desta fase, existiam múltiplos processos/entry points
independentes e sem sincronia entre si (MILK_Presence.py,
Conversar_Com_MILK.py, MILK_Scheduler.py, MILK_Command_Center.py -- ver
aviso no topo de cada um). Este arquivo agora é o único ponto de entrada
recomendado.
"""
import sys

from core.orchestrator import MilkCore


def main():
    if "--headless" in sys.argv:
        # Modo texto puro, sem overlay/avatar/scheduler -- útil para debug
        # e para ambientes sem Tkinter/display.
        MilkCore().start()
        return

    from presence.unified_app import UnifiedApp

    core = MilkCore()
    app = UnifiedApp(core)
    app.run()


if __name__ == "__main__":
    main()
