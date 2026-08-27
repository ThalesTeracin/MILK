MILK FASE 16 — MEMÓRIA LONGA COM SQLITE

NOVO
- Banco local: C:\JARVIS\data\milk_memory.db
- Histórico de conversas.
- Projetos.
- Eventos dos projetos.
- Decisões.
- Erros e soluções.
- Contexto curto para IA: apenas as últimas mensagens relevantes.
- Economia de tokens: não manda a conversa inteira para o modelo.

INSTALAÇÃO
1. Copie o conteúdo da Fase 16 para C:\JARVIS e substitua.
2. NÃO apague os arquivos das fases anteriores.
3. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt

4. Migre a memória antiga:
   python .\Migrar_Memoria.py

5. Inicie:
   python .\src\main.py

TESTES DE VOZ
- MILK
- quais são meus projetos
- status da memória
- cria um programa Python para cadastro
- quais são meus projetos

ARQUIVOS
Banco:
C:\JARVIS\data\milk_memory.db

Visualizar:
python .\Ver_Memoria.py

IMPORTANTE
SQLite já faz parte do Python. Não precisa instalar banco externo.
