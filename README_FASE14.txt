MILK FASE 14 — BROWSER AGENT COM PLAYWRIGHT

NOVO
- Navegador real controlado por Playwright.
- Perfil persistente em C:\JARVIS\browser_profile.
- Pode manter sessões/login do navegador criado pelo MILK.
- Abrir sites.
- Pesquisar.
- Clicar por texto/label em vez de coordenadas.
- Preencher campos.
- Ler e resumir páginas.
- Voltar página.
- Fechar navegador.
- Envio de formulários exige confirmação.

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Execute:
   C:\JARVIS\Instalar_Browser.bat

Ou manual:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
   python -m playwright install chromium

3. Inicie:
   python .\src\main.py

TESTES DE VOZ
- "MILK"
- "abre github.com"
- "pesquisa no google inteligência artificial"
- "clica em entrar"
- "lê essa página pra mim"
- "volta a página"
- "fecha o navegador"

FORMULÁRIO
- "preenche email com exemplo@teste.com"
- "envia o formulário"
A MILK pedirá confirmação antes do envio.

IMPORTANTE
O browser do MILK usa perfil próprio.
Não mexa manualmente na pasta browser_profile.
