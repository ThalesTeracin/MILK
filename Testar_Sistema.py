"""
Verificacao de fumaca do MILK.

Roda uma bateria de checagens sobre o estado real da instalacao, sem
depender de rede paga, sem abrir janelas e sem gravar audio. O objetivo
e responder "esta tudo no lugar para o sistema subir?" antes de gerar o
instalador final.

Uso:
    cd C:\\JARVIS
    python .\\Testar_Sistema.py

Codigo de saida 0 se nao houver nenhuma FALHA. Avisos nao reprovam.
"""

import importlib
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.chdir(ROOT)

falhas = []
avisos = []


def secao(titulo):
    print()
    print(titulo)
    print("-" * len(titulo))


def ok(msg):
    print("  [OK]    " + msg)


def falha(msg):
    print("  [FALHA] " + msg)
    falhas.append(msg)


def aviso(msg):
    print("  [AVISO] " + msg)
    avisos.append(msg)


# ---------------------------------------------------------------- 1
secao("1. Ambiente")

if sys.version_info >= (3, 10):
    ok("Python " + sys.version.split()[0])
else:
    falha("Python " + sys.version.split()[0] + " -- o projeto assume 3.10+")

versao_file = ROOT / "VERSION"
if versao_file.exists():
    ok("VERSION = " + versao_file.read_text(encoding="utf-8").strip())
else:
    aviso("arquivo VERSION ausente")


# ---------------------------------------------------------------- 2
secao("2. Dependencias de requirements.txt")

# Nome no pip -> nome do modulo importavel, quando diferem.
APELIDOS = {
    "python-dotenv": "dotenv",
    "SpeechRecognition": "speech_recognition",
    "Pillow": "PIL",
    "google-api-python-client": "googleapiclient",
    "google-auth": "google.auth",
    "google-auth-oauthlib": "google_auth_oauthlib",
    "python-docx": "docx",
    "python-pptx": "pptx",
    "edge-tts": "edge_tts",
}

def checar_requirements(arquivo, obrigatorio):
    """
    Importa cada pacote listado no arquivo. Ausencia em requirements.txt
    reprova; em requirements-optional.txt vira apenas aviso, porque o
    sistema sobe sem esses pacotes.
    """
    if not arquivo.exists():
        if obrigatorio:
            falha(arquivo.name + " ausente")
        return

    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        pacote = linha.split(">=")[0].split("==")[0].split("[")[0].strip()
        modulo = APELIDOS.get(pacote, pacote.replace("-", "_"))
        try:
            importlib.import_module(modulo)
            ok(pacote)
        except Exception as e:
            recado = pacote + " nao importa (" + type(e).__name__ + ": " + str(e) + ")"
            falha(recado) if obrigatorio else aviso(recado + " -- opcional")


checar_requirements(ROOT / "requirements.txt", obrigatorio=True)

secao("2b. Dependencias opcionais")
checar_requirements(ROOT / "requirements-optional.txt", obrigatorio=False)


# ---------------------------------------------------------------- 3
secao("3. Modulos do projeto (src/)")

for arquivo in sorted(SRC.rglob("*.py")):
    if "__pycache__" in arquivo.parts:
        continue
    rel = arquivo.relative_to(SRC)
    if rel.stem == "__init__":
        continue
    nome = ".".join(rel.with_suffix("").parts)
    if nome == "main":
        continue  # main.py sobe o orquestrador quando roda como __main__
    try:
        importlib.import_module(nome)
        ok(nome)
    except Exception as e:
        falha(nome + " nao importa (" + type(e).__name__ + ": " + str(e) + ")")


# ---------------------------------------------------------------- 4
secao("4. Arquivos de configuracao")

try:
    from core.config import config_path
except Exception as e:
    config_path = None
    falha("core.config nao importa (" + type(e).__name__ + ": " + str(e) + ")")

OBRIGATORIOS = [
    "settings.json",
    "providers.json",
    "agents.json",
    "skills.json",
    "permission_profiles.json",
    "mcp_servers.json",
    "milk_tasks.json",
]

for nome in OBRIGATORIOS:
    caminho = config_path(nome) if config_path else (ROOT / "config" / nome)
    if not caminho.exists():
        falha("config/" + nome + " ausente")
        continue
    try:
        json.loads(caminho.read_text(encoding="utf-8-sig"))
        origem = "local" if "local" in caminho.parts else "versionado"
        ok(nome + " (" + origem + ")")
    except json.JSONDecodeError as e:
        falha("config/" + nome + " nao e JSON valido: " + str(e))

persona = ROOT / "config" / "persona.txt"
if persona.exists() and persona.read_text(encoding="utf-8").strip():
    ok("persona.txt")
else:
    falha("config/persona.txt ausente ou vazio")


# ---------------------------------------------------------------- 5
secao("5. Whisper (voz local)")

if config_path:
    wcfg = config_path("whisper_local.json")
    if not wcfg.exists():
        falha("whisper_local.json nao encontrado em config/local/ nem em config/")
    else:
        try:
            dados = json.loads(wcfg.read_text(encoding="utf-8-sig"))
            origem = "local" if "local" in wcfg.parts else "versionado"
            ok("whisper_local.json (" + origem + ")")

            exe = Path(dados.get("whisper_exe", ""))
            if exe.exists():
                ok("executavel: " + str(exe))
            else:
                falha("whisper_exe nao existe no disco: " + str(exe))

            modelo = Path(dados.get("model", ""))
            if modelo.exists():
                mb = modelo.stat().st_size / (1024 * 1024)
                ok("modelo: " + modelo.name + " (" + str(round(mb)) + " MB)")
            else:
                falha("model nao existe no disco: " + str(modelo))

            if dados.get("language"):
                ok("idioma: " + dados["language"])
            else:
                aviso("campo 'language' ausente em whisper_local.json")
        except json.JSONDecodeError as e:
            falha("whisper_local.json invalido: " + str(e))


# ---------------------------------------------------------------- 6
secao("6. Credenciais (.env) -- apenas presenca, nunca valor")

env = ROOT / ".env"
if not env.exists():
    falha(".env ausente (copie de .env.example)")
else:
    chaves = {}
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        chaves[k.strip()] = v.strip()

    ordem = chaves.get("AI_PROVIDER_ORDER", "")
    if not ordem:
        falha("AI_PROVIDER_ORDER nao definido no .env")
    else:
        ok("AI_PROVIDER_ORDER = " + ordem)

    try:
        provedores = json.loads(
            (ROOT / "config" / "providers.json").read_text(encoding="utf-8-sig")
        )
    except Exception:
        provedores = {}

    com_chave = []
    for pid in [p.strip() for p in ordem.split(",") if p.strip()]:
        cfg = provedores.get(pid)
        if not cfg:
            aviso("provedor '" + pid + "' esta em AI_PROVIDER_ORDER mas nao em providers.json")
            continue
        var = cfg.get("api_key_env", "")
        if chaves.get(var):
            ok(cfg["label"] + ": chave presente (" + var + ")")
            com_chave.append(pid)
        else:
            aviso(cfg["label"] + ": sem chave (" + var + " vazio) -- provedor sera pulado")

    if not com_chave:
        falha("nenhum provedor de IA tem chave configurada -- o chat nao vai responder")

    if "9router_custom" in com_chave:
        if not chaves.get("NINEROUTER_BASE_URL"):
            falha("9router_custom tem chave mas NINEROUTER_BASE_URL esta vazio")
        if not chaves.get("NINEROUTER_MODEL"):
            falha("9router_custom tem chave mas NINEROUTER_MODEL esta vazio")


# ---------------------------------------------------------------- 7
secao("7. Memoria (SQLite)")

db = ROOT / "data" / "milk_memory.db"
if not db.exists():
    aviso("data/milk_memory.db ainda nao existe (criado no primeiro uso)")
else:
    try:
        con = sqlite3.connect(db)
        tabelas = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        ok("abre; tabelas: " + (", ".join(tabelas) or "(nenhuma)"))
        if "conversations" not in tabelas:
            falha("tabela 'conversations' ausente -- schema da memoria nao foi criado")
        else:
            cols = [r[1] for r in con.execute("PRAGMA table_info(conversations)")]
            if "project_key" in cols:
                ok("conversations.project_key presente (migracao de projeto aplicada)")
            else:
                falha("conversations.project_key ausente -- migracao de projeto nao rodou")
            n = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            ok(str(n) + " mensagens gravadas")
        con.close()
    except Exception as e:
        falha("nao consegue ler o banco: " + type(e).__name__ + ": " + str(e))


# ---------------------------------------------------------------- 8
secao("8. Recursos visuais")

for nome in ["milk_avatar.png"]:
    p = ROOT / "assets" / nome
    if p.exists():
        ok("assets/" + nome)
    else:
        falha("assets/" + nome + " ausente")


# ---------------------------------------------------------------- 9
secao("9. Pontos de entrada")

for nome in [
    "src/main.py",
    "MILK_Presence.py",
    "MILK_Command_Center.py",
    "MILK_Scheduler.py",
]:
    p = ROOT / nome
    if not p.exists():
        falha(nome + " ausente")
        continue
    try:
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
        ok(nome)
    except SyntaxError as e:
        falha(nome + " tem erro de sintaxe na linha " + str(e.lineno) + ": " + str(e.msg))


# ---------------------------------------------------------------- fim
print()
print("=" * 60)
if falhas:
    print("RESULTADO: " + str(len(falhas)) + " FALHA(S), " + str(len(avisos)) + " aviso(s)")
    print()
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
else:
    print("RESULTADO: tudo passou. " + str(len(avisos)) + " aviso(s).")
    sys.exit(0)
