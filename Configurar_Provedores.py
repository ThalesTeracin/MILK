from pathlib import Path
from getpass import getpass
import json

providers = json.loads(Path("config/providers.json").read_text(encoding="utf-8"))

print("=== MILK Fase 10 - Configurar Provedores ===")
print("As URLs e modelos já vêm preenchidos.")
print("Você só informa as chaves que quiser usar.")
print()

env = {
    "MILK_NAME": "MILK",
    "MILK_LANGUAGE": "pt-BR",
    "AI_MAX_TOKENS": "180",
    "AI_TIMEOUT_SECONDS": "25",
}

order = []

for key, cfg in providers.items():
    print(f"\n[{cfg['label']}]")
    print("Modelo:", cfg.get("model") or "(preencher)")
    print("URL:", cfg.get("base_url") or "(preencher)")
    use = input("Ativar este provedor? (s/n): ").strip().lower() == "s"
    if not use:
        continue

    order.append(key)

    if key == "9router_custom":
        env["NINEROUTER_BASE_URL"] = input("Base URL do 9Router: ").strip()
        env["NINEROUTER_MODEL"] = input("Modelo do 9Router: ").strip()

    env_name = cfg.get("api_key_env")
    if cfg.get("requires_key", True):
        env[env_name] = getpass("API Key: ").strip()
    else:
        env[env_name] = "ollama"

env["AI_PROVIDER_ORDER"] = ",".join(order)

lines = [f"{k}={v}" for k, v in env.items()]
Path(".env").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("\nConfiguração salva em C:\\JARVIS\\.env")
print("Ordem ativa:", env.get("AI_PROVIDER_ORDER") or "nenhuma")
print("Não envie o arquivo .env para ninguém.")
