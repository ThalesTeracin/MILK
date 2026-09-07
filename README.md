# Milk

Assistente pessoal em forma de cachorrinha, que vive na área de trabalho do Windows.
Ela conversa por texto e por voz, responde consultas rápidas sozinha, resolve trabalho
pesado com o Claude Code, mantém uma fila de tarefas que sobrevive a fechar a janela,
lembra do que foi dito e faz algumas coisas no Windows — sempre pedindo confirmação
antes de mexer nos seus arquivos.

## Como abrir

```
Milk.bat              abre a Milk
python milk.py        o mesmo, com terminal
python milk.py doutor diagnóstico no terminal
```

Para ela subir junto com o Windows: botão direito no avatar → **🪟 Iniciar com o Windows**.

## O que ela faz

**Conversa.** Clique no avatar para abrir a janela. O que ela não resolve sozinha vai
para o Claude Code, com o progresso aparecendo passo a passo ("📖 Lendo config.py").

**Responde na hora**, sem gastar um pedido ao Claude: hora e data, clima, CEP, cotação
de moedas, Wikipédia, GitHub, feriados, lugares no mapa, e quantos dias faltam para
uma data.

**Fila de tarefas.** Peça uma coisa enquanto ela faz outra: o pedido entra na fila e
começa sozinho quando o anterior termina. "Isso é urgente" passa na frente. Você pode
perguntar o que ela está fazendo, pausar, continuar, cancelar e mandar repetir.

**Memória.** "Lembre que eu prefiro respostas curtas." Ela guarda, e isso passa a valer
nas conversas seguintes. Senha, token e chave ela se recusa a guardar.

**Windows.** Abre programas, pastas, arquivos e sites; procura arquivo pelo nome; conta
como está o computador. Criar, apagar e rodar comando **só depois de você confirmar**.
Coisa que pode quebrar o Windows ela não faz nem confirmada.

**Voz.** Fala com voz neural em português. Pelo botão "🎤 Falar" ou pela escuta contínua,
em que basta dizer **"Milk"** e falar.

**Diagnóstico.** "Milk, você está bem?" — ela testa microfone, internet, Claude, voz,
fila, memória e disco, e diz o que fazer com o que estiver ruim.

## Modos

Botão direito no avatar:

| Modo | O que muda |
|---|---|
| 🔊 Normal | fala e aparece |
| 🔕 Silencioso | responde só por escrito |
| 🌙 Não perturbe | não fala nem aparece sozinha |

O trabalho continua acontecendo nos três.

## Estrutura

```
milk.py                    ponto de entrada
milk/core/                 configuração, texto, pessoa, eventos, modos, log, doutor
milk/avatar/               janela, conversa, passeio, animação
milk/voice/                microfone, escuta contínua, transcrição, TTS, latido
milk/intelligence/         roteador, prompt, ponte com o Claude, rotas
milk/tasks/                fila de tarefas (modelos, persistência, gerente)
milk/memory/               memória de fatos, projetos e conversa
milk/system/               ações no Windows, permissão, confirmação, início
milk/tools/                as APIs públicas e o relógio local
tests/                     300 testes em unittest
```

## Arquivos de estado

Ficam na raiz e podem ser apagados sem quebrar nada (ela recomeça vazia):

| Arquivo | O que guarda |
|---|---|
| `milk_tarefas.json` | a fila e o histórico de tarefas |
| `milk_memoria.json` | fatos e projetos |
| `milk_conversa.json` | as últimas falas |
| `milk_pessoa.json` | com quem ela está falando |
| `milk_modo.json` | normal, silencioso ou não perturbe |

Configuração das ferramentas: `config/settings.json` (nunca guarde token aqui — o do
GitHub é lido da variável de ambiente indicada em `github.token_env`).

Logs: `logs/`, por área, com rotação. Senha e token são apagados antes de escrever.

## Testes

```
.venv\Scripts\python.exe -m unittest discover -s tests
```

## Requisitos

Windows 11, Python 3.14 no `.venv` da pasta, Claude Code instalado e no PATH.
Internet é necessária para voz e reconhecimento de fala.

Esta máquina é **Windows ARM64**: `speech_recognition` não acha o binário FLAC sozinho
aqui, e `milk/voice/flac_fix.py` corrige isso. Whisper e Vosk locais não têm roda para
esta arquitetura.

## Autoria

Esta assistente foi **desenvolvida por Thales Teracin**.

A autoria é declarada em um único lugar, `milk/core/autoria.py`, e propagada
a partir dele: para o cabeçalho de cada arquivo de código, para a licença,
para este README e para a identidade que a Milk carrega quando conversa —
perguntaram quem a criou, ela responde Thales Teracin.

`tests/test_autoria.py` existe para falhar caso essa autoria seja removida,
trocada ou encoberta em qualquer um desses pontos.

## Licença

Software proprietário. Copyright (c) 2026 Thales Teracin, todos os direitos
reservados. O código está publicado para leitura; publicação não é permissão
de uso, cópia, modificação ou redistribuição. Ver `LICENSE.txt`.
