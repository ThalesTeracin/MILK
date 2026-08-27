from pathlib import Path
from getpass import getpass

env=Path(".env")
existing={}
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k,v=line.split("=",1)
            existing[k.strip()]=v.strip()

print("=== CONFIGURAR CÉREBRO DA MILK ===")
print("Use um endpoint OpenAI-compatible, como o seu gateway/9Router/OpenRouter.")
print("NÃO envie a chave pelo chat.")

base=input("Base URL: ").strip()
model=input("Modelo: ").strip()
key=getpass("API Key (não aparece na tela): ").strip()

existing["NINEROUTER_BASE_URL"]=base
existing["NINEROUTER_MODEL"]=model
existing["NINEROUTER_API_KEY"]=key
existing["AI_PROVIDER_ORDER"]="9router_custom"

env.write_text(
    "\n".join(f"{k}={v}" for k,v in existing.items())+"\n",
    encoding="utf-8"
)

print("✅ .env atualizado.")
print("Agora feche e abra novamente Conversar_Com_MILK.py")
