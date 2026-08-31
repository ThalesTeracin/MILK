# =============================================================================
# SUBSTITUÍDO (Fase 33 - integração Presence + Avatar + Skills, 2026-08-28).
# O estado de atividade da MILK passou a ter um dono único em
# src/core/activity_state.py, que guarda em memória e publica em
# data/milk_runtime_state.json com carimbo de tempo. Este arquivo pertence
# ao mecanismo anterior, cujos campos (speaking/listening/thinking/emotion/
# last_text) nunca chegaram a ser escritos por ninguém.
# Mantido apenas como referência histórica. Não editar/usar.
# =============================================================================

import json
import threading
from pathlib import Path

STATE = Path("data/milk_runtime_state.json")
STATE.parent.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()

DEFAULT = {
    "speaking": False,
    "listening": False,
    "thinking": False,
    "emotion": "neutral",
    "last_text": ""
}

def read_state():
    with LOCK:
        if not STATE.exists():
            return DEFAULT.copy()
        try:
            data=json.loads(STATE.read_text(encoding="utf-8"))
            out=DEFAULT.copy()
            out.update(data)
            return out
        except Exception:
            return DEFAULT.copy()

def update_state(**kwargs):
    with LOCK:
        data=DEFAULT.copy()
        if STATE.exists():
            try:
                data.update(json.loads(STATE.read_text(encoding="utf-8")))
            except Exception:
                pass
        data.update(kwargs)
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
