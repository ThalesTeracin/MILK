MILK — FASES 28, 29, 30 e 31

FASE 28 — KNOWLEDGE BASE LOCAL + RAG
- banco SQLite local
- importação de TXT/MD/JSON/PY/PS1/BAT/CSV
- busca lexical TF-IDF simples
- criação de contexto para enviar ao 9Router
- não depende de embeddings pagos

FASE 29 — AVATAR ANIMADO
- estado runtime: falando, ouvindo, pensando
- brilho/pulsação
- sincronização visual com estado de fala
- efeito de boca/luz enquanto TTS fala

OBS:
O lip-sync é visual sincronizado ao estado de fala.
Phoneme lip-sync real pode ser adicionado numa fase futura sem trocar esta base.

FASE 30 — MINI OVERLAY / HOLOGRAMA
- mini MILK transparente
- always-on-top
- arrastável
- sem janela tradicional
- estado PRONTA/OUVINDO/PENSANDO/FALANDO
- inicia via pythonw para não abrir console

FASE 31 — SKILLS + MCP ROUTING
- registro de skills
- skills locais seguras
- roteador avançado
- suporte a MCP
- ações sensíveis exigem confirmação
- shell arbitrário continua bloqueado

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. NÃO apague:
   .env
   config\whisper_local.json
   data\milk_memory.db
   src das fases anteriores

3. Rode:
   cd C:\JARVIS
   python .\Testar_Fases28_31.py

Esperado:
✅ FASES 28 + 29 + 30 + 31 VALIDADAS.

FASE 28:
python .\Importar_Conhecimento.py

FASE 29:
python -m src.avatar.avatar_window

FASE 30:
.\INICIAR_MILK_MINI_OVERLAY.bat

FASE 31:
python .\Testar_Fase31.py

IMPORTANTE
Este pacote NÃO altera o listener do Whisper.
A correção da tela preta deve permanecer instalada.
