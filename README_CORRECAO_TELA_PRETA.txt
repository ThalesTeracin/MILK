MILK — CORREÇÃO DA TELA PRETA APÓS FASE 22

CAUSA PROVÁVEL
A Fase 22 inicia servidores MCP como subprocessos Python.
No Windows, subprocessos sem CREATE_NO_WINDOW podem abrir uma janela preta.

Também a inicialização automática da Fase 21 usava um arquivo .cmd no Startup,
que pode piscar uma janela de console ao entrar no Windows.

CORREÇÕES APLICADAS
1. MCP agora usa CREATE_NO_WINDOW e SW_HIDE.
2. O launcher da MILK no Startup passa de .cmd para .vbs invisível.
3. Script de limpeza encerra processos antigos do mock MCP.
4. Não altera Whisper, 9Router, voz, Presence ou Command Center.

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   C:\JARVIS\CORRIGIR_TELA_PRETA.bat

3. Depois, para validar MCP:
   cd C:\JARVIS
   python .\Testar_MCP.py

O teste pode usar a janela do PowerShell que você abriu manualmente,
mas NÃO deve criar outra janela preta separada.

4. Reinicie o Windows quando quiser validar a inicialização automática da MILK.
