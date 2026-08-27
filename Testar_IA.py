from src.ai.router import AIRouter

router = AIRouter()
print("AI Router:", router.status())

if not router.enabled:
    print("ERRO: rode primeiro: python .\\Configurar_IA.py")
    raise SystemExit(1)

result = router.interpret("pode abrir o programa para fazer contas?")
print("Resposta:", result)

if result:
    print("TESTE OK")
else:
    print("Falha ao consultar o provedor.")
