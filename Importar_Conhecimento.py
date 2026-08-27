import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from knowledge.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

print("=== MILK FASE 28 — IMPORTAR CONHECIMENTO ===")
print("Digite um caminho de arquivo .txt, .md, .json, .py, .ps1, .bat ou .csv")
path = input("Arquivo: ").strip().strip('"')

doc_id = kb.add_file(path)
print(f"✅ Documento adicionado. ID: {doc_id}")
