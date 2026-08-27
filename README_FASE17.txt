MILK FASE 17 — CORREÇÃO DE VOZ + EMAIL + CALENDÁRIO

CORREÇÃO IMPORTANTE
Se a MILK parou de responder ao ser chamada, a principal suspeita é a
sensibilidade do microfone da Fase 16.

A Fase 17:
- calibra o ruído ambiente;
- baixa o limiar de ativação;
- mostra no terminal o que foi reconhecido;
- mantém fallback de voz;
- facilita diagnosticar se o problema é microfone ou reconhecimento.

TESTE DE VOZ
1. Copie os arquivos para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python -m pip install -r requirements.txt
3. Teste antes de iniciar tudo:
   python .\Testar_Voz.py

Se reconhecer sua fala, a parte de voz está funcionando.

EMAIL
- Gmail: busca, leitura, resumo e criação de rascunho.
- Outlook: caixa de entrada, resumo e criação de rascunho.
- Envio automático NÃO foi habilitado por padrão.

CALENDÁRIO
- Google Calendar: próximos compromissos.
- Outlook Calendar: próximos compromissos.

CONFIGURAÇÃO
Leia:
- Configurar_Google.txt
- Configurar_Outlook.txt

IMPORTANTE
Não coloque senhas em arquivos.
Use OAuth.
