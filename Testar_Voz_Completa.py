import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from voice.listener import NaturalVoiceListener
from voice.speaker import NaturalSpeaker

listener = NaturalVoiceListener()
speaker = NaturalSpeaker()

print("=== TESTE COMPLETO DE VOZ DA MILK ===")
listener.calibrate()
speaker.say("Olá. Agora minha voz também está funcionando. Fale alguma coisa para mim.")

print("Fale agora...")
texto = listener.listen()

if texto:
    print("Reconhecido:", texto)
    speaker.say(f"Eu ouvi você dizer: {texto}")
    speaker.say("Perfeito. O microfone e a minha fala estão funcionando juntos.")
else:
    print("Não reconheci a fala.")
    speaker.say("Não consegui entender sua fala neste teste.")
