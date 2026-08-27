import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

load_dotenv()

base = os.getenv("NINEROUTER_BASE_URL", "").strip().rstrip("/")
model = os.getenv("NINEROUTER_MODEL", "").strip()
key = os.getenv("NINEROUTER_API_KEY", "").strip()

print("=== TESTE DEFINITIVO 9ROUTER LOCAL ===")
print("Base URL:", base or "AUSENTE")
print("Modelo:", model or "AUSENTE")
print("API Key:", "CARREGADA" if key else "AUSENTE")

if not (base and model and key):
    print("❌ .env incompleto.")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print("\n1) Testando /models...")
r = requests.get(f"{base}/models", headers=headers, timeout=20)
print("HTTP:", r.status_code)

if r.status_code != 200:
    print("Resposta:", (r.text or "")[:3000])
    raise SystemExit(2)

models = r.json().get("data", [])
ids = [m.get("id") for m in models if isinstance(m, dict)]

if model not in ids:
    print("❌ O modelo configurado NÃO aparece em /models:")
    print(model)
    print("Escolha um ID exato retornado pelo 9Router.")
    raise SystemExit(3)

print("✅ Modelo existe no 9Router.")

print("\n2) Testando /chat/completions...")
payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "Responda somente OK."},
        {"role": "user", "content": "Teste MILK"}
    ],
    "temperature": 0,
    "max_tokens": 20
}

r = requests.post(
    f"{base}/chat/completions",
    headers=headers,
    json=payload,
    timeout=45
)

print("HTTP:", r.status_code)
print("Resposta:", (r.text or "")[:3000])

if r.status_code == 200:
    print("\n✅ 9ROUTER + CHAVE + MODELO + CHAT ESTÃO FUNCIONANDO.")
else:
    print("\n❌ O HTTP acima é o erro REAL do 9Router/provedor.")
