from core.proc import run_hidden

class NaturalSpeaker:
    def say(self, text):
        text = str(text or "").strip()
        if not text:
            return

        print(f"MILK: {text}")
        safe = text.replace("'","''")

        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$pt=$s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'pt-BR*' } | Select-Object -First 1; "
            "if($pt){$s.SelectVoice($pt.VoiceInfo.Name)}; "
            "$s.Rate=0; $s.Volume=100; "
            f"$s.Speak('{safe}')"
        )
        run_hidden(
            ["powershell.exe","-NoProfile","-Command",ps],
            timeout=60,
            check=False
        )
