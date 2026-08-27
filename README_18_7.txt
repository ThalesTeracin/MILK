MILK 18.7 — RECONHECIMENTO PELO WINDOWS

A tela mostrou que o microfone capta a voz, mas o Google SpeechRecognition
não entende as palavras. Por isso esta versão troca o mecanismo de STT.

Agora a MILK usa o reconhecedor do próprio Windows.

PASSO 1
Copie tudo para C:\JARVIS e substitua.

PASSO 2
Rode:
python .\Verificar_Reconhecedor_Windows.py

Se aparecer pt-BR, continue.

Se NÃO aparecer pt-BR:
Configurações > Hora e idioma > Idioma e região
> Português (Brasil) > Opções de idioma
> instale Reconhecimento de fala.

PASSO 3
Rode:
python .\Conversar_Com_MILK.py

TESTE:
boa tarde
abre a calculadora
abre o bloco de notas
como está meu computador
tchau Milk
