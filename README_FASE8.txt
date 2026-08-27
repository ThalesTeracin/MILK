MILK - FASE 8

MUDANÇAS:
- Nome alterado de JARVIS para MILK.
- Wake word: MILK.
- Você fala MILK uma vez; depois fala normalmente.
- Parser local continua sendo usado primeiro: zero tokens.
- Se o parser local não entender, entra o AI Router.
- AI Router aceita gateways OpenAI-compatible.
- Preparado para 9Router/OpenRouter/outros provedores compatíveis.
- Fallback opcional.

INSTALAÇÃO:
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
   python .\src\main.py

IMPORTANTE:
O AI Router fica DESATIVADO até configurar o arquivo .env.
Não coloque chave de API dentro do código.
Na próxima etapa configuraremos o 9Router com sua chave sem expô-la.
