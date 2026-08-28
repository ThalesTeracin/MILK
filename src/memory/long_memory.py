from pathlib import Path
import sqlite3
import json
import datetime
import hashlib

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    token_hint INTEGER DEFAULT 0,
    project_key TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    path TEXT,
    stack TEXT,
    status TEXT,
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    project_key TEXT,
    error_hash TEXT NOT NULL,
    error_text TEXT NOT NULL,
    solution TEXT
);

CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_project_events_key ON project_events(project_key);
CREATE INDEX IF NOT EXISTS idx_errors_hash ON errors(error_hash);
"""

# Colunas acrescentadas depois que uma tabela já existia em bancos no campo.
#
# CREATE TABLE IF NOT EXISTS não altera tabelas existentes: em um banco
# antigo o SCHEMA acima é aceito sem erro e a coluna nova simplesmente não
# aparece, até o primeiro INSERT falhar com "no such column". Toda coluna
# adicionada ao SCHEMA depois da criação original precisa ser repetida aqui.
#
# Só serve para ADD COLUMN, que é o que o SQLite faz sem reescrever a
# tabela. A declaração não pode ter NOT NULL sem DEFAULT, nem UNIQUE, nem
# PRIMARY KEY. Mudar tipo ou remover coluna exige recriar a tabela.
MIGRATIONS = {
    "conversations": {
        "project_key": "TEXT",
    },
}


class LongMemory:
    def __init__(self, db_path="data/milk_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        """
        Acrescenta as colunas de MIGRATIONS que faltarem. Idempotente:
        rodar em um banco já atualizado não faz nada.
        """
        for tabela, colunas in MIGRATIONS.items():
            existentes = {
                linha[1]
                for linha in self.conn.execute("PRAGMA table_info(%s)" % tabela)
            }
            if not existentes:
                # Tabela ausente neste banco; o SCHEMA já a criou com tudo.
                continue
            for nome, tipo in colunas.items():
                if nome not in existentes:
                    # Identificadores não aceitam placeholder no SQLite, e
                    # tabela/coluna/tipo vêm de MIGRATIONS, nunca do usuário.
                    self.conn.execute(
                        "ALTER TABLE %s ADD COLUMN %s %s" % (tabela, nome, tipo)
                    )
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def add_message(self, role, content, summary=None, token_hint=0, project_key=None):
        self.conn.execute(
            "INSERT INTO conversations(created_at, role, content, summary, token_hint, project_key) VALUES(?,?,?,?,?,?)",
            (
                datetime.datetime.now().isoformat(timespec="seconds"),
                role,
                content,
                summary,
                int(token_hint or 0),
                project_key
            )
        )
        self.conn.commit()

    def recent_messages(self, limit=8):
        rows = self.conn.execute(
            "SELECT role, content, summary FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        rows = list(reversed(rows))
        return [
            {
                "role": r["role"],
                "content": r["summary"] or r["content"]
            }
            for r in rows
        ]

    def compact_context(self, max_chars=5000):
        messages = self.recent_messages(limit=12)
        chunks = []
        total = 0
        for m in reversed(messages):
            line = f"{m['role']}: {m['content']}"
            if total + len(line) > max_chars:
                break
            chunks.append(line)
            total += len(line)
        return "\n".join(reversed(chunks))

    def remember_project(self, name, path=None, stack=None, status="active", summary=None):
        key = self._project_key(name, path)
        now = datetime.datetime.now().isoformat(timespec="seconds")
        self.conn.execute("""
            INSERT INTO projects(project_key, name, path, stack, status, summary, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(project_key) DO UPDATE SET
                name=excluded.name,
                path=COALESCE(excluded.path, projects.path),
                stack=COALESCE(excluded.stack, projects.stack),
                status=COALESCE(excluded.status, projects.status),
                summary=COALESCE(excluded.summary, projects.summary),
                updated_at=excluded.updated_at
        """, (key, name, path, stack, status, summary, now, now))
        self.conn.commit()
        return key

    def add_project_event(self, project_key, event_type, content):
        self.conn.execute(
            "INSERT INTO project_events(project_key, created_at, event_type, content) VALUES(?,?,?,?)",
            (
                project_key,
                datetime.datetime.now().isoformat(timespec="seconds"),
                event_type,
                content
            )
        )
        self.conn.commit()

    def get_project(self, name_or_key):
        row = self.conn.execute("""
            SELECT * FROM projects
            WHERE project_key=? OR lower(name)=lower(?)
            ORDER BY updated_at DESC LIMIT 1
        """, (name_or_key, name_or_key)).fetchone()
        return dict(row) if row else None

    def list_projects(self, limit=10):
        rows = self.conn.execute(
            "SELECT name, path, stack, status, summary, updated_at FROM projects ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def remember_decision(self, scope, key, value):
        self.conn.execute(
            "INSERT INTO decisions(created_at, scope, key, value) VALUES(?,?,?,?)",
            (
                datetime.datetime.now().isoformat(timespec="seconds"),
                scope, key, value
            )
        )
        self.conn.commit()

    def latest_decisions(self, scope=None, limit=10):
        if scope:
            rows = self.conn.execute(
                "SELECT scope,key,value,created_at FROM decisions WHERE scope=? ORDER BY id DESC LIMIT ?",
                (scope, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT scope,key,value,created_at FROM decisions ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def remember_error(self, error_text, project_key=None, solution=None):
        h = hashlib.sha256(error_text.encode("utf-8", errors="ignore")).hexdigest()[:24]
        self.conn.execute(
            "INSERT INTO errors(created_at, project_key, error_hash, error_text, solution) VALUES(?,?,?,?,?)",
            (
                datetime.datetime.now().isoformat(timespec="seconds"),
                project_key, h, error_text, solution
            )
        )
        self.conn.commit()
        return h

    def find_similar_error(self, error_text):
        h = hashlib.sha256(error_text.encode("utf-8", errors="ignore")).hexdigest()[:24]
        row = self.conn.execute(
            "SELECT * FROM errors WHERE error_hash=? AND solution IS NOT NULL ORDER BY id DESC LIMIT 1",
            (h,)
        ).fetchone()
        return dict(row) if row else None

    def stats(self):
        result = {}
        for table in ["conversations","projects","project_events","decisions","errors"]:
            result[table] = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return result

    def _project_key(self, name, path):
        seed = f"{name}|{path or ''}".lower().strip()
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
