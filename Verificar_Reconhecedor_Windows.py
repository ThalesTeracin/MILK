import subprocess

script = '''
Add-Type -AssemblyName System.Speech
$all = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
if ($all.Count -eq 0) {
  Write-Output "NENHUM"
} else {
  foreach ($r in $all) {
    Write-Output ($r.Culture.Name + " | " + $r.Name)
  }
}
'''
p = subprocess.run(
    ["powershell.exe","-NoProfile","-Command",script],
    capture_output=True,text=True
)
print("=== RECONHECEDORES DE FALA DO WINDOWS ===")
print(p.stdout.strip() or "Nenhum reconhecedor encontrado.")

if "pt-BR" not in p.stdout:
    print()
    print("ATENÇÃO: não encontrei reconhecimento pt-BR.")
    print("Windows 11:")
    print("Configurações > Hora e idioma > Idioma e região")
    print("Português (Brasil) > Opções de idioma")
    print("Instale RECONHECIMENTO DE FALA.")
else:
    print()
    print("OK: reconhecimento pt-BR instalado.")
