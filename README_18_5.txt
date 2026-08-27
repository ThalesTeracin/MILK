MILK FASE 18.5 — ARQUITETURA CORRIGIDA

CORREÇÕES:
- O microfone não derruba mais o programa em uma falha temporária.
- Faz até 3 tentativas para abrir o áudio.
- Comandos principais são interpretados LOCALMENTE antes da IA.
- "Boa tarde" recebe resposta.
- "abre a calculadora" funciona mesmo sem provedor IA.
- Se a IA estiver configurada, ela vira fallback para linguagem mais livre.
- Voz continua ativa em todas as respostas.

TESTE:
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python .\Conversar_Com_MILK.py

FALE:
- boa tarde
- abre a calculadora
- abre aí a calculadora pra mim
- quero fazer umas contas
- abre o bloco de notas
- como está meu computador
- tchau Milk

Não avance de fase até esses testes funcionarem.
