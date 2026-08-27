import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from voice.listener import NaturalVoiceListener
from voice.speaker import NaturalSpeaker
from agents.windows_agent import WindowsAgent
from core.nlu import HybridNLU

try:
    from ai.router import AIRouter
except Exception:
    AIRouter=None

listener=NaturalVoiceListener()
speaker=NaturalSpeaker()
windows=WindowsAgent()

ai=None
if AIRouter:
    try:
        ai=AIRouter()
    except Exception as e:
        print("⚠️ Não consegui iniciar o cérebro de IA:",e)

nlu=HybridNLU(ai)

print("=== MILK 18.11 — COMANDOS NATURAIS ===")
print("IA:", ai.status() if ai else "não configurada")

listener.calibrate()
speaker.say("Pronto. Agora entendo muito mais formas naturais de pedir as coisas.")

history=[]

while True:
    text=listener.listen()
    if not text:
        continue

    result=nlu.interpret(text)
    intent=result.get("intent","chat")

    if intent=="exit":
        speaker.say("Tudo bem. Até mais.")
        break

    if intent=="open_app":
        speaker.say(windows.open_target(result.get("target")))
        continue

    if intent=="system_status":
        speaker.say(windows.system_status())
        continue

    if intent=="top_processes":
        speaker.say(windows.top_processes())
        continue

    if intent=="web_search":
        speaker.say(windows.search_web(result.get("query") or text))
        continue

    reply=result.get("reply")

    if intent=="chat" and not reply and ai and getattr(ai,"enabled",False):
        try:
            reply=ai.chat(
                "Você é MILK, assistente de voz em português brasileiro. "
                "Converse naturalmente, entenda contexto e seja objetiva e útil.",
                text,
                history=history[-10:],
                max_tokens=300
            )
        except Exception as e:
            print("⚠️ Falha na IA:",e)

    if not reply:
        reply="Estou ouvindo."

    history.append({"role":"user","content":text})
    history.append({"role":"assistant","content":reply})

    speaker.say(reply)
