import subprocess,sys
from pathlib import Path

tests=[
    "Testar_RAG.py",
    "Testar_Avatar_Animado.py",
    "Testar_Fase31.py"
]

ok=True
for t in tests:
    print(f"\n=== {t} ===")
    p=subprocess.run([sys.executable,t],capture_output=True,text=True)
    print(p.stdout)
    if p.returncode!=0:
        print(p.stderr)
        ok=False

overlay=Path("src/overlay/mini_overlay.py").exists()
print("Fase 30 - Mini Overlay:", "OK" if overlay else "ERRO")
ok=ok and overlay

print()
print("✅ FASES 28 + 29 + 30 + 31 VALIDADAS." if ok else "❌ Alguma fase falhou.")
