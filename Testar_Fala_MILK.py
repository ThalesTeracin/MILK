import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from voice.speaker import NaturalSpeaker

s = NaturalSpeaker()
print("=== TESTE DA VOZ DA MILK ===")
s.say("Se você está ouvindo esta frase, minha saída de voz está funcionando corretamente.")
print("✅ Teste terminou.")
