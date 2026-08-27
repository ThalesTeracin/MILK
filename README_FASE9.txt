MILK - FASE 9 - AI ROUTER REAL

NOVO:
- configuração segura por arquivo .env
- chave não fica dentro do código
- provedor principal OpenAI-compatible
- fallback opcional
- parser local PRIMEIRO para economizar tokens
- IA usada somente quando o comando não for entendido localmente
- limite de resposta da IA: 180 tokens

INSTALAÇÃO:
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
3. Configure o provedor:
   python .\Configurar_IA.py
4. Teste:
   python .\Testar_IA.py
5. Inicie:
   python .\src\main.py

NÃO envie foto da sua API Key.
