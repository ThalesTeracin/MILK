from pathlib import Path
from getpass import getpass

print("=== MILK - Configuração do AI Router ===")
print("A chave ficará somente em C:\\JARVIS\\.env")
print()

base_url = input("Base URL do provedor principal: ").strip()
api_key = getpass("API Key do provedor principal: ").strip()
model = input("Nome/ID do modelo: ").strip()

use_fallback = input("Configurar fallback agora? (s/n): ").strip().lower() == "s"

fb_url = fb_key = fb_model = ""
if use_fallback:
    fb_url = input("Fallback Base URL: ").strip()
    fb_key = getpass("Fallback API Key: ").strip()
    fb_model = input("Fallback modelo: ").strip()

content = f"""MILK_NAME=MILK
MILK_LANGUAGE=pt-BR
AI_BASE_URL={base_url}
AI_API_KEY={api_key}
AI_MODEL={model}
AI_FALLBACK_BASE_URL={fb_url}
AI_FALLBACK_API_KEY={fb_key}
AI_FALLBACK_MODEL={fb_model}
AI_MAX_TOKENS=180
AI_TIMEOUT_SECONDS=25
"""

Path(".env").write_text(content, encoding="utf-8")
print()
print("Configuração salva em C:\\JARVIS\\.env")
print("Não envie esse arquivo para ninguém.")
