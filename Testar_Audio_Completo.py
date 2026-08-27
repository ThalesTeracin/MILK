import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from voice.listener import NaturalVoiceListener
from voice.speaker import NaturalSpeaker

listener = NaturalVoiceListener()
speaker = NaturalSpeaker()

print("=== MILK - TESTE DE ÁUDIO COMPLETO ===")

listener.calibrate()

speaker.say(
    "Olá. Agora vou esperar um segundo antes de ouvir você. "
    "Quando eu terminar, fale uma frase normalmente."
)

# Evita a própria voz da MILK interferir no microfone.
time.sleep(1.2)

texto = listener.listen()

if texto:
    speaker.say(f"Eu entendi você. Você disse: {texto}")
    print("\n✅ ENTRADA E SAÍDA DE VOZ FUNCIONANDO.")
else:
    print("\n❌ O microfone não reconheceu a fala.")
    print("Rode: python .\\Selecionar_Microfone.py")
