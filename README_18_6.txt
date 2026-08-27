MILK 18.6 — CORREÇÃO DO RECONHECIMENTO

Problema corrigido:
A MILK detectava sua voz, mas frequentemente perdia o começo da frase.
Isso fazia o Google Speech Recognition receber áudio incompleto.

Mudanças:
- 0,5 segundo de pré-áudio antes da detecção da fala.
- limiar de ativação mais sensível.
- normalização do volume.
- silêncio final maior.
- rejeita gravações curtas demais.
- erros de microfone não encerram o programa.
- "boa tarde" e "abre a calculadora" funcionam localmente.

INSTALAÇÃO:
1. Extraia/copiei tudo para C:\JARVIS.
2. Escolha substituir arquivos.
3. Rode:
   cd C:\JARVIS
   python .\Conversar_Com_MILK.py

TESTE:
- boa tarde
- abre a calculadora
- abre o bloco de notas
- como está meu computador
- tchau Milk
