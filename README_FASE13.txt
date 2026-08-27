MILK FASE 13 — COMPUTER USE V1 + VISÃO DA TELA

NOVO
- Captura de tela real com MSS.
- Análise visual usando o primeiro provedor multimodal que responder.
- Comandos naturais como:
  "MILK, olha minha tela"
  "o que tem de errado aqui?"
  "tira um print"
- Mouse/teclado V1 via PyAutoGUI.
- Clique exige confirmação nesta fase.
- Digitação pode ser feita por pedido explícito.
- Mantém voz natural e linguagem livre da Fase 12.
- Coding Agent continua disponível.

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
3. Mantenha seu .env atual.
4. Rode:
   python .\src\main.py

TESTES
- "MILK"
- "olha minha tela e me diga o que está acontecendo"
- "tira um print"
- "abre a calculadora"
- "clica no ponto 500 por 300"
- "confirmar clique"
- "digita teste milk"

IMPORTANTE
A análise visual depende de um modelo/provedor que aceite imagens.
Se um provedor não aceitar visão, o roteador tenta o próximo.
Ações destrutivas continuam bloqueadas.
