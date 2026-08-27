MILK FASE 21 — PRESENÇA NATURAL + WAKE WORD + SCHEDULER

OBJETIVO
A MILK deixa de parecer apenas "um programa dentro de uma janela".

Agora ela pode:
- ficar escondida em segundo plano;
- ouvir a palavra MILK;
- aparecer automaticamente na área de trabalho;
- aparecer sem borda/janela tradicional;
- usar fundo transparente;
- dar saudação conforme o horário;
- conversar por voz após ser chamada;
- continuar ouvindo sem precisar apertar botão;
- desaparecer quando você disser para descansar;
- voltar a aparecer quando você chamar MILK novamente;
- desaparecer sozinha após tempo ocioso;
- iniciar junto com o Windows opcionalmente.

EXEMPLO
Você:
"Milk"

Ela aparece e fala:
"Boa tarde. Estou aqui."

Você:
"Como está você?"

MILK responde e continua ouvindo.

Você:
"Pode descansar."

Ela responde:
"Tudo bem. Vou ficar por perto."

e desaparece.

INSTALAÇÃO
1. Copie o conteúdo para C:\JARVIS e substitua.
2. NÃO apague:
   .env
   config\whisper_local.json
   data\milk_memory.db
   src das fases anteriores

3. Rode:
   C:\JARVIS\INSTALAR_FASE21.bat

4. Inicie:
   C:\JARVIS\INICIAR_MILK_PRESENCA.bat

ATIVAR JUNTO COM WINDOWS (OPCIONAL)
PowerShell:
powershell -ExecutionPolicy Bypass -File C:\JARVIS\ATIVAR_MILK_COM_WINDOWS.ps1

DESATIVAR:
powershell -ExecutionPolicy Bypass -File C:\JARVIS\DESATIVAR_MILK_COM_WINDOWS.ps1

SCHEDULER
A Fase 21 também inclui MILK_Scheduler.py.
As tarefas ficam em:
C:\JARVIS\config\milk_tasks.json

IMPORTANTE
A presença natural usa o Whisper e o 9Router já configurados.
Não substitui o Command Center da Fase 20; são dois modos:
- Command Center = painel completo.
- Presence = MILK aparece quando chamada.
