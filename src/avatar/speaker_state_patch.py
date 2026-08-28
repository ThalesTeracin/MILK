# =============================================================================
# SUBSTITUÍDO (Fase 33 - integração Presence + Avatar + Skills, 2026-08-28).
# O estado de atividade da MILK passou a ter um dono único em
# src/core/activity_state.py, que guarda em memória e publica em
# data/milk_runtime_state.json com carimbo de tempo. Este arquivo pertence
# ao mecanismo anterior, cujos campos (speaking/listening/thinking/emotion/
# last_text) nunca chegaram a ser escritos por ninguém.
# Mantido apenas como referência histórica. Não editar/usar.
# =============================================================================

"""
Use this mixin in the existing NaturalSpeaker:
before TTS -> update_state(speaking=True,last_text=text)
finally -> update_state(speaking=False)
"""
from avatar.runtime_state import update_state
