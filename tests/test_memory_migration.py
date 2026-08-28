"""
Testes da migração de schema de src/memory/long_memory.py.

CREATE TABLE IF NOT EXISTS não altera tabela existente: quando uma coluna
é acrescentada ao SCHEMA, todo banco já em disco continua sem ela e o
primeiro INSERT falha com "no such column". LongMemory._migrate() fecha
essa lacuna por ALTER TABLE, e é onde as próximas mudanças de schema
(embeddings, entre outras) devem ser registradas.
"""
import sqlite3

import pytest

from memory.long_memory import LongMemory

# Schema anterior ao project_key, como ficou nos bancos já em uso.
SCHEMA_ANTIGO = """
CREATE TABLE conversations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  token_hint INTEGER DEFAULT 0);
"""


@pytest.fixture
def banco_antigo(tmp_path):
    """Banco no schema anterior, com uma mensagem já gravada."""
    caminho = tmp_path / "antigo.db"
    conn = sqlite3.connect(caminho)
    conn.executescript(SCHEMA_ANTIGO)
    conn.execute(
        "INSERT INTO conversations(created_at, role, content) "
        "VALUES('2026-01-01', 'user', 'mensagem antiga')"
    )
    conn.commit()
    conn.close()
    return caminho


def colunas(memoria, tabela="conversations"):
    return [linha[1] for linha in memoria.conn.execute("PRAGMA table_info(%s)" % tabela)]


def test_adiciona_coluna_faltante_em_banco_antigo(banco_antigo):
    memoria = LongMemory(banco_antigo)
    assert "project_key" in colunas(memoria)
    memoria.close()


def test_preserva_dados_ja_gravados(banco_antigo):
    memoria = LongMemory(banco_antigo)
    linha = memoria.conn.execute(
        "SELECT content, project_key FROM conversations"
    ).fetchone()
    assert linha["content"] == "mensagem antiga"
    assert linha["project_key"] is None
    memoria.close()


def test_insert_grava_project_key_apos_migracao(banco_antigo):
    memoria = LongMemory(banco_antigo)
    memoria.add_message("user", "mensagem nova", project_key="abc123")
    linha = memoria.conn.execute(
        "SELECT project_key FROM conversations WHERE content='mensagem nova'"
    ).fetchone()
    assert linha["project_key"] == "abc123"
    memoria.close()


def test_migracao_e_idempotente(banco_antigo):
    """Reabrir um banco já migrado não pode falhar nem duplicar linhas."""
    LongMemory(banco_antigo).close()

    memoria = LongMemory(banco_antigo)
    assert memoria.conn.execute(
        "SELECT COUNT(*) c FROM conversations"
    ).fetchone()["c"] == 1
    memoria.add_message("assistant", "segunda")
    assert memoria.conn.execute(
        "SELECT COUNT(*) c FROM conversations"
    ).fetchone()["c"] == 2
    memoria.close()


def test_banco_novo_ja_nasce_completo(tmp_path):
    memoria = LongMemory(tmp_path / "novo.db")
    assert "project_key" in colunas(memoria)
    memoria.add_message("user", "oi", project_key="k")
    memoria.close()


def test_project_key_e_opcional(tmp_path):
    """Chamadas antigas, sem o parâmetro, continuam válidas."""
    memoria = LongMemory(tmp_path / "opcional.db")
    memoria.add_message("user", "sem projeto")
    linha = memoria.conn.execute("SELECT project_key FROM conversations").fetchone()
    assert linha["project_key"] is None
    memoria.close()
