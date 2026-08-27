MILK FASE 18.10 — WHISPER PRÉ-COMPILADO

Esta correção abandona definitivamente a compilação ARM64.

Motivo:
whisper.cpp atual bloqueou a compilação ARM com MSVC, e a tentativa Clang
não gerou o executável na máquina.

Solução:
usar o binário x64 OFICIAL já compilado pelo projeto whisper.cpp.
Windows 11 ARM64 executa aplicativos x64 através da emulação do próprio Windows.

Vantagens:
- sem Visual Studio
- sem MSVC
- sem Clang
- sem CMake
- sem build
- baixa, extrai e usa

PASSOS:
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   .\INSTALAR_WHISPER_PRECOMPILADO.bat
3. Espere aparecer:
   [OK] WHISPER INSTALADO E VALIDADO.
4. Rode:
   python .\Conversar_Com_MILK.py

IMPORTANTE:
Não execute mais:
Instalar_Whisper_Definitivo.ps1
CORRIGIR_WHISPER_ARM64_CLANG.ps1
Verificar_Reconhecedor_Windows.py

O listener desta versão também grava na taxa nativa do microfone e converte
para 16 kHz antes de enviar ao Whisper, evitando o erro anterior do dispositivo.
