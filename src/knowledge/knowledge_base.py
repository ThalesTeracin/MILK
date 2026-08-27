import sqlite3
import re
import math
from pathlib import Path
from collections import Counter

DB = Path("data/knowledge/milk_knowledge.db")
DB.parent.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9_]+", re.UNICODE)

def tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 2]

class KnowledgeBase:
    def __init__(self, db_path=DB):
        self.db_path = Path(db_path)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source)")

    def add_text(self, source, title, content):
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO documents(source,title,content) VALUES(?,?,?)",
                (source, title, content)
            )
            return cur.lastrowid

    def add_file(self, path):
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(path)

        if p.suffix.lower() not in [".txt",".md",".json",".py",".ps1",".bat",".csv"]:
            raise ValueError("Formato não suportado nesta fase.")

        text = p.read_text(encoding="utf-8", errors="ignore")
        return self.add_text(str(p.resolve()), p.name, text)

    def list_documents(self, limit=100):
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,source,title,created_at FROM documents ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {"id":r[0],"source":r[1],"title":r[2],"created_at":r[3]}
            for r in rows
        ]

    def search(self, query, top_k=5):
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        with self._conn() as c:
            rows = c.execute("SELECT id,source,title,content FROM documents").fetchall()

        if not rows:
            return []

        docs = []
        df = Counter()
        for row in rows:
            tokens = tokenize(row[3])
            counts = Counter(tokens)
            docs.append((row, counts, len(tokens)))
            for tok in counts:
                df[tok] += 1

        n = len(docs)
        scores = []

        for row, counts, length in docs:
            score = 0.0
            for tok in q_tokens:
                tf = counts.get(tok, 0) / max(1, length)
                idf = math.log((n + 1) / (df.get(tok, 0) + 1)) + 1
                score += tf * idf
            if score > 0:
                snippet = row[3][:1200]
                scores.append({
                    "id":row[0],
                    "source":row[1],
                    "title":row[2],
                    "score":score,
                    "snippet":snippet
                })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def build_context(self, query, top_k=4):
        hits = self.search(query, top_k=top_k)
        if not hits:
            return {"context":"","hits":[]}

        parts = []
        for h in hits:
            parts.append(
                f"[Fonte: {h['title'] or h['source']}]\n{h['snippet']}"
            )
        return {"context":"\n\n".join(parts), "hits":hits}
