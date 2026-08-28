"""
Teste da correção crítica da Task 6 (rodada de correção 1).

Motivo: tirar core.handle() da thread do Tk (Fase 33, Task 6) fez a
conexão sqlite3 de LongMemory -- criada na thread principal, dentro de
MilkCore()/MemoryManager() -- passar a ser usada pela thread de trabalho
do overlay (_trabalho_passo). sqlite3.connect() sem check_same_thread=False
recusa isso com ProgrammingError, e como user_message()/assistant_message()
são chamados dentro de try/except: pass em core/orchestrator.py, a memória
longa parava de gravar a conversa inteira sem ninguém perceber.

Sem microfone, sem Tk, sem rede, sem git: só MemoryManager + threading.
"""
import threading

import pytest

from memory.long_memory import LongMemory
from memory.memory_manager import MemoryManager


@pytest.fixture
def gerente(tmp_path):
    """
    MemoryManager com o banco em tmp_path, sem passar pelo __init__ real
    (que sempre abre data/milk_memory.db). A conexão nasce nesta thread
    (a do teste), imitando MilkCore() nascendo na thread principal.
    """
    mm = MemoryManager.__new__(MemoryManager)
    mm.long = LongMemory(tmp_path / "memoria.db")
    mm.active_project_key = None
    return mm


def test_memoria_longa_usada_de_outra_thread_nao_levanta(gerente):
    """
    Reproduz o caminho real: a conexão nasce na thread principal e é usada
    pela thread de trabalho (_trabalho_passo -> core.handle ->
    memory.user_message/context_for_ai).
    """
    erros = []

    def trabalho():
        try:
            gerente.user_message("milk quais projetos")
            gerente.context_for_ai()
            gerente.assistant_message("resposta")
        except Exception as e:
            erros.append(e)

    t = threading.Thread(target=trabalho)
    t.start()
    t.join()

    assert erros == []


def test_memoria_gravada_de_outra_thread_e_lida_depois(gerente):
    """Mesma reprodução, mas confirma que a gravação de fato persistiu."""
    def trabalho():
        gerente.user_message("mensagem de outra thread")

    t = threading.Thread(target=trabalho)
    t.start()
    t.join()

    contexto = gerente.context_for_ai()
    assert any(m["content"] == "mensagem de outra thread" for m in contexto)
