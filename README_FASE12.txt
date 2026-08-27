MILK FASE 12 — VOZ NATURAL + LINGUAGEM LIVRE + CODING AGENT

NOVO
1. Sua fala não fica limitada a blocos fixos de 4 segundos.
   O MILK começa a gravar quando você fala e para depois de silêncio.

2. Você não precisa decorar frases.
   Exemplos que podem ser entendidos:
   - "abre aí pra mim aquele negócio de fazer conta"
   - "quero escrever um texto"
   - "vê por que meu computador está pesado"
   - "faz um site simples pra uma oficina"
   - "cria um programa em Python para cadastro"

3. Voz da MILK mais natural.
   Edge TTS neural em português do Brasil.

4. Coding Agent real.
   Cria arquivos em:
   C:\JARVIS\projects\<nome-do-projeto>

5. Segurança:
   - Coding Agent não pode escrever fora de C:\JARVIS\projects
   - comandos destrutivos continuam bloqueados
   - valida Python com compileall
   - pytest é usado quando já existem testes

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
3. Mantenha seu .env atual.
   Se ainda não tiver, copie .env.example para .env e configure provedores.
4. Rode:
   python .\src\main.py

TESTES
- "MILK"
- "abre aí pra mim a calculadora"
- "vê como está meu computador"
- "faz um site simples com uma página inicial"
- "cria um programa Python que cadastre clientes"

OBSERVAÇÃO
A Fase 12 cria e valida projetos. Instalação autônoma de dependências,
execução de servidores e correção iterativa automática serão ampliadas
na Fase 13/14 junto com Computer Use e Browser Agent.
