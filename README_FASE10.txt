MILK FASE 10 - MULTIPROVEDOR

PRECONFIGURADOS:
- OpenRouter Free: https://openrouter.ai/api/v1 | openrouter/free
- Groq: https://api.groq.com/openai/v1 | openai/gpt-oss-20b
- Gemini: https://generativelanguage.googleapis.com/v1beta/openai/ | gemini-3.7-flash
- NVIDIA: https://integrate.api.nvidia.com/v1 | nvidia/nemotron-3.5-lightning-30b-a3b
- Ollama Local: http://localhost:11434/v1 | qwen2.5:7b
- 9Router: cadastrado como gateway custom porque a URL/modelo dependem da conta/configuração.

INSTALAÇÃO:
1. Copie tudo para C:\JARVIS e substitua.
2. cd C:\JARVIS
3. python -m pip install -r requirements.txt
4. python .\Configurar_Provedores.py
5. python .\Testar_Provedores.py
6. python .\src\main.py

SEGURANÇA:
- Chaves ficam somente no .env local.
- Não envie print da API Key.
- Parser local continua primeiro para gastar zero tokens quando possível.
