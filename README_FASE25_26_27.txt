MILK — FASES 25 + 26 + 27 + CORREÇÃO DA TELA PRETA

CORREÇÃO DA TELA PRETA
A captura mostrou uma janela com título apontando para:
C:\JARVIS\third_party\whisper...

Portanto a janela preta NÃO vinha do MCP.
Ela vinha do whisper-cli.exe, que era executado como processo de console visível.

CORREÇÃO:
src\voice\listener.py agora usa:
- CREATE_NO_WINDOW
- STARTF_USESHOWWINDOW
- SW_HIDE

Isso executa whisper-cli sem abrir uma janela preta separada.

PASSO 1
Copie tudo para C:\JARVIS e substitua.

PASSO 2
Rode:
C:\JARVIS\APLICAR_CORRECAO_TELA_PRETA.bat

Depois use a MILK normalmente.

FASE 25 — RECOVERY / UNDO + PERMISSÕES
- snapshot de arquivo antes de alteração
- restore
- histórico em data\recovery
- perfis safe, balanced e developer
- shell arbitrário continua bloqueado

FASE 26 — EMPACOTAMENTO
- script PyInstaller
- build windowed (sem console)
- atalho no Desktop

Para criar EXE futuramente:
powershell -ExecutionPolicy Bypass -File C:\JARVIS\installer\build_exe.ps1

Depois:
powershell -ExecutionPolicy Bypass -File C:\JARVIS\installer\CRIAR_ATALHO_DESKTOP.ps1

FASE 27 — PERFIS DE USUÁRIO
- perfis independentes
- preferências
- idioma
- voz
- perfil de permissão
- armazenamento em data\profiles

TESTE DAS FASES
cd C:\JARVIS
python .\Testar_Fase25_26_27.py

Esperado:
✅ FASES 25 + 26 + 27 VALIDADAS.
