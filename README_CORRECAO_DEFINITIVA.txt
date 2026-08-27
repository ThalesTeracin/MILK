MILK — CORREÇÃO DEFINITIVA DA TELA PRETA DO WHISPER

A captura confirma que a janela preta pertence ao executável localizado em:
C:\JARVIS\third_party\whisper...

Portanto a origem é whisper-cli.exe.

Esta correção muda a execução para:
- subprocess.Popen DIRETO no whisper-cli.exe
- shell=False
- CREATE_NO_WINDOW (0x08000000)
- STARTUPINFO + SW_HIDE
- stdin DEVNULL
- stdout/stderr capturados
- nunca usa cmd.exe ou PowerShell para executar o Whisper

PASSOS
1. Copie todo o conteúdo para C:\JARVIS e substitua.
2. Rode:
   C:\JARVIS\APLICAR_CORRECAO_DEFINITIVA.bat

3. O resultado precisa mostrar:
   OK - CREATE_NO_WINDOW
   OK - shell=False
   OK - DEVNULL stdin
   OK - cwd whisper
   ✅ LISTENER CORRIGIDO ESTÁ INSTALADO.

4. Depois rode a MILK normalmente.

SE AINDA APARECER UMA JANELA:
rode:
   python C:\JARVIS\VARREDURA_WHISPER.py

Esse script lista qualquer outro arquivo antigo do projeto que ainda esteja
chamando whisper-cli por subprocesso, shell, cmd ou os.system.

NÃO mexe em:
- 9Router
- modelo
- API key
- MCP
- memória
- Presence
- Command Center
