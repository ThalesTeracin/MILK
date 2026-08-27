import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from voice.speaker import NaturalSpeaker

speaker = NaturalSpeaker()
print("=== TESTE SOMENTE DA VOZ DA MILK ===")
speaker.say("Olá. Este é um teste somente da minha voz. Se você está me ouvindo, a saída de áudio está funcionando.")
print("Fim do teste.")
