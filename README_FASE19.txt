MILK FASE 19 — GIT / GITHUB / DEVOPS

NOVO
- git status
- git init
- criar/trocar branch
- git diff
- git add -A
- commit
- log
- testes do projeto
- push
- GitHub CLI
- criar repositório
- criar pull request

SEGURANÇA
Ações locais de leitura e teste podem ser feitas diretamente.
Ações que publicam algo exigem confirmação:
- git push
- criação de repositório GitHub
- criação de pull request

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python .\Testar_DevOps.py

3. Se GitHub CLI não estiver instalado:
   powershell -ExecutionPolicy Bypass -File .\Instalar_GitHub_CLI.ps1

4. Depois autentique:
   gh auth login

5. Opcional:
   python .\Integrar_Fase19.py

TESTES DE VOZ / INTENÇÃO
- mostra o status do git
- cria uma branch feature-login
- mostra o diff
- roda os testes do projeto
- mostra os últimos commits
- faz commit mensagem ajuste inicial
- envia para o github

IMPORTANTE
Não desative a confirmação para push/publicação.
