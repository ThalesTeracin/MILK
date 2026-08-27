# JARVIS TRT AI — Fase 3

## Objetivo
Adicionar reconhecimento de voz real em PT-BR com fallback para texto.

## Como funciona
- O Jarvis inicia em READY.
- Você pode falar comandos simples.
- `sleep` coloca em modo SLEEP.
- No modo SLEEP, falar `jarvis` acorda.
- Caso o microfone falhe, o sistema permite digitar.

## Dependências
- SpeechRecognition
- PyAudio

## Instalação
No PowerShell:

```powershell
cd C:\JARVIS
python -m pip install -r requirements.txt
```

Depois:

```powershell
python .\src\main.py
```
