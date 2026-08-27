"""
Use this mixin in the existing NaturalSpeaker:
before TTS -> update_state(speaking=True,last_text=text)
finally -> update_state(speaking=False)
"""
from avatar.runtime_state import update_state
