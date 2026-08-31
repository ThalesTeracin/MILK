from pathlib import Path
import hashlib

p = Path(r"C:\JARVIS\src\voice\listener.py")

print("=== VERIFICAÇÃO DA CORREÇÃO ===")
if not p.exists():
    print("ERRO: listener.py não encontrado.")
    raise SystemExit(1)

text = p.read_text(encoding="utf-8", errors="ignore")

checks = {
    "CREATE_NO_WINDOW": "CREATE_NO_WINDOW = 0x08000000" in text,
    "shell=False": "shell=False" in text,
    "DEVNULL stdin": "stdin=subprocess.DEVNULL" in text,
    "cwd whisper": "cwd=str(self.exe.parent)" in text,
}

for k,v in checks.items():
    print(("OK" if v else "FALTA"), "-", k)

print("SHA256:", hashlib.sha256(p.read_bytes()).hexdigest())

if all(checks.values()):
    print("\n✅ LISTENER CORRIGIDO ESTÁ INSTALADO.")
else:
    print("\n❌ O ARQUIVO ANTIGO AINDA ESTÁ EM USO.")
