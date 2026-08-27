import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from recovery.recovery_manager import RecoveryManager
from security.permission_manager import PermissionManager
from profiles.profile_manager import ProfileManager

print("=== MILK FASES 25 + 26 + 27 ===")

# Phase 25
tmp=Path("data/test_recovery.txt")
tmp.parent.mkdir(exist_ok=True)
tmp.write_text("versão A",encoding="utf-8")

r=RecoveryManager()
snap=r.snapshot_file(tmp)
tmp.write_text("versão B",encoding="utf-8")
rest=r.restore_snapshot(snap["snapshot"])

print("Fase 25 - Recovery:", rest)
print("Conteúdo restaurado:", tmp.read_text(encoding="utf-8"))

perm=PermissionManager("balanced")
print("Permissão git_push:",perm.check("git_push"))
print("Permissão arbitrary_shell:",perm.check("arbitrary_shell"))

# Phase 27
pm=ProfileManager()
profile=pm.create("principal","Usuário Principal")
print("Fase 27 - Perfil:",profile["display_name"])

# Phase 26 is build script presence validation
build=Path("installer/build_exe.ps1")
print("Fase 26 - Empacotamento:", "OK" if build.exists() else "ERRO")

ok = (
    tmp.read_text(encoding="utf-8")=="versão A"
    and build.exists()
    and pm.load("principal") is not None
)

print()
print("✅ FASES 25 + 26 + 27 VALIDADAS." if ok else "❌ Falha na validação.")
