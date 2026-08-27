from src.ai.router import AIRouter

router = AIRouter()

print("=== MILK - Teste de Provedores ===")
print("Ordem ativa:", router.status())

if not router.enabled:
    print("Nenhum provedor configurado.")
    print("Rode: python .\\Configurar_Provedores.py")
    raise SystemExit(1)

result = router.interpret("pode abrir o programa que eu uso para fazer contas?")
print("Resultado:", result)

if result:
    print("TESTE OK")
else:
    print("Nenhum provedor respondeu corretamente.")
