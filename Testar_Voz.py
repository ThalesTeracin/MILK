from src.voice.listener import NaturalVoiceListener

v=NaturalVoiceListener()
v.calibrate()
print("Fale algo agora...")
text=v.listen()
print("Reconhecido:", text)
