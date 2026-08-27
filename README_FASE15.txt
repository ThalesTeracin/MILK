MILK FASE 15 — CODING AGENT V2

NOVO
- Ambiente virtual .venv separado por projeto.
- requirements.txt analisado antes de instalar.
- Dependências só são instaladas se estiverem na allowlist.
- Compilação Python automática.
- Pytest automático quando houver pasta tests.
- Até 2 ciclos automáticos de correção.
- Log do resultado em:
  projeto\.milk\last_run.json

DEPENDÊNCIAS PERMITIDAS NESTA FASE
requests
fastapi
uvicorn
flask
pytest
pydantic
sqlalchemy
jinja2
python-dotenv
httpx
rich

INSTALAÇÃO
1. Copie o conteúdo da Fase 15 para C:\JARVIS e substitua.
2. Não apague os arquivos da Fase 14.
3. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
4. Inicie:
   python .\src\main.py

TESTES DE VOZ
- MILK
- cria um programa Python para cadastrar clientes e faz os testes
- desenvolve uma API simples em FastAPI
- corrige meu projeto Python e valida os testes

SEGURANÇA
- Não escreve fora de C:\JARVIS\projects.
- Dependências fora da allowlist são bloqueadas.
- Shell arbitrário e comandos destrutivos continuam bloqueados.
