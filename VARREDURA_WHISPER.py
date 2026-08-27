from pathlib import Path

ROOT = Path(r"C:\JARVIS")
terms = ["whisper-cli", "subprocess.run", "subprocess.Popen", "os.system", "shell=True"]

print("=== VARREDURA DE CHAMADAS WHISPER ===")
found = 0

for p in ROOT.rglob("*.py"):
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if "whisper-cli" in text or ("whisper" in text.lower() and any(t in text for t in terms[1:])):
        found += 1
        print(f"\nARQUIVO: {p}")
        for i, line in enumerate(text.splitlines(), 1):
            if "whisper" in line.lower() or "subprocess" in line or "os.system" in line or "shell=True" in line:
                print(f"{i:4}: {line[:220]}")

print(f"\nArquivos relevantes encontrados: {found}")
print("O listener correto deve conter: CREATE_NO_WINDOW = 0x08000000")
