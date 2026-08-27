import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from knowledge.knowledge_base import KnowledgeBase

kb=KnowledgeBase()
kb.add_text("teste","Arquitetura MILK",
"""A MILK usa Whisper para reconhecimento de voz, 9Router como cérebro de IA,
MCP para plugins, Self Review para auditoria, Recovery para undo e Command Center para interface.""")

result=kb.build_context("qual é o cérebro de IA da MILK?")
print("=== FASE 28 - RAG ===")
print(result["context"])

if "9Router" in result["context"]:
    print("✅ FASE 28 VALIDADA.")
else:
    print("❌ Fase 28 falhou.")
