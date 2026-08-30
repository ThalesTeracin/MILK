"""
Monta a cadeia de provedores da MILK no .env.

A ordem em que você ativar os provedores é a ordem em que o
src/ai/router.py vai tentá-los: o primeiro responde, e quem estiver fora
do ar passa a vez para o próximo. Por isso ative primeiro o cérebro
principal e depois as reservas.

Este script preserva as outras variáveis do .env -- voz, caminhos,
orçamento de tokens. Antes ele reescrevia o arquivo do zero e apagava
tudo o que não fosse provedor.
"""
from pathlib import Path
from getpass import getpass
import json

ARQUIVO_ENV = Path(".env")

providers = json.loads(
    Path("config/providers.json").read_text(encoding="utf-8-sig")
)


def ler_env():
    """O .env atual como dicionário, para não perder o que já existe."""
    if not ARQUIVO_ENV.exists():
        return {}

    atual = {}
    for linha in ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.strip().startswith("#"):
            chave, valor = linha.split("=", 1)
            atual[chave.strip()] = valor.strip()
    return atual


def perguntar(rotulo, atual):
    """Enter mantém o valor atual, para não redigitar o que já está certo."""
    sufixo = f" [{atual}]" if atual else ""
    resposta = input(f"{rotulo}{sufixo}: ").strip()
    return resposta or atual


env = ler_env()
env.setdefault("MILK_NAME", "MILK")
env.setdefault("MILK_LANGUAGE", "pt-BR")
env.setdefault("AI_TIMEOUT_SECONDS", "35")

print("=== MILK - Configurar cadeia de provedores ===")
print("As URLs e modelos conhecidos já vêm preenchidos.")
print("A ordem em que você ativar é a ordem de tentativa.")
print("Enter mantém o valor que já está no .env.")
print()

ordem = []

for chave, cfg in providers.items():
    # Chaves iniciadas por "_" são comentário do arquivo, não provedor.
    if chave.startswith("_") or not isinstance(cfg, dict):
        continue

    print(f"\n[{cfg['label']}]")
    print("URL:", cfg.get("base_url") or "(preencher)")
    print("Modelo:", cfg.get("model") or "(preencher)")
    if cfg.get("_note"):
        print("Nota:", cfg["_note"])

    if input("Ativar este provedor? (s/n): ").strip().lower() != "s":
        continue

    ordem.append(chave)

    nome_url = cfg.get("base_url_env")
    if nome_url:
        valor = perguntar("Base URL", env.get(nome_url) or cfg.get("base_url", ""))
        if valor:
            env[nome_url] = valor

    nome_modelo = cfg.get("model_env")
    if nome_modelo:
        valor = perguntar("Modelo", env.get(nome_modelo) or cfg.get("model", ""))
        if valor:
            env[nome_modelo] = valor

    nome_chave = cfg.get("api_key_env")
    if not nome_chave:
        continue

    if cfg.get("requires_key", True):
        digitada = getpass("API Key (não aparece na tela, Enter mantém): ").strip()
        if digitada:
            env[nome_chave] = digitada
        elif not env.get(nome_chave):
            print("Sem chave, este provedor fica fora da cadeia.")
    else:
        env.setdefault(nome_chave, "local")

env["AI_PROVIDER_ORDER"] = ",".join(ordem)

ARQUIVO_ENV.write_text(
    "\n".join(f"{k}={v}" for k, v in env.items()) + "\n",
    encoding="utf-8"
)

print("\nConfiguração salva em", ARQUIVO_ENV.resolve())
print("Ordem ativa:", env.get("AI_PROVIDER_ORDER") or "nenhuma")
print("Confira com: python Testar_Provedores.py")
print("Não envie o arquivo .env para ninguém.")
