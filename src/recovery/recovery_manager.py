import json
import shutil
from pathlib import Path
from datetime import datetime

BASE = Path("data/recovery")
BASE.mkdir(parents=True, exist_ok=True)
LOG = Path("logs/recovery.log")
LOG.parent.mkdir(parents=True, exist_ok=True)

class RecoveryManager:
    def __init__(self, max_snapshots=30):
        self.max_snapshots = max_snapshots

    def _log(self, text):
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {text}\n")

    def snapshot_file(self, path):
        src = Path(path)
        if not src.exists() or not src.is_file():
            return {"ok":False, "error":"Arquivo não encontrado."}

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        folder = BASE / stamp
        folder.mkdir(parents=True, exist_ok=True)

        dst = folder / src.name
        shutil.copy2(src, dst)

        meta = {
            "original": str(src.resolve()),
            "backup": str(dst.resolve()),
            "created": stamp
        }
        (folder/"meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        self._prune()
        self._log(f"snapshot {src} -> {dst}")
        return {"ok":True, "snapshot":str(folder)}

    def restore_snapshot(self, snapshot_folder):
        folder = Path(snapshot_folder)
        meta_file = folder/"meta.json"
        if not meta_file.exists():
            return {"ok":False, "error":"Snapshot inválido."}

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        src = Path(meta["backup"])
        dst = Path(meta["original"])

        if not src.exists():
            return {"ok":False, "error":"Backup não encontrado."}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self._log(f"restore {src} -> {dst}")
        return {"ok":True, "restored":str(dst)}

    def list_snapshots(self, limit=20):
        items=[]
        for folder in sorted(BASE.iterdir(), reverse=True):
            meta=folder/"meta.json"
            if meta.exists():
                try:
                    data=json.loads(meta.read_text(encoding="utf-8"))
                    data["snapshot"]=str(folder)
                    items.append(data)
                except Exception:
                    pass
            if len(items)>=limit:
                break
        return items

    def _prune(self):
        folders=[p for p in sorted(BASE.iterdir(), reverse=True) if p.is_dir()]
        for p in folders[self.max_snapshots:]:
            shutil.rmtree(p, ignore_errors=True)
