# CONTEXT

## COMO RETOMAR

Quando o usuário disser **"continua a Milk"**:

1. Ler este arquivo e `MILK_STATUS.md`.
2. Não reauditar o projeto inteiro nem reler o código por completo sem necessidade.
3. Executar o "Próximo passo exato" que está no fim deste arquivo.

Especificação principal do projeto: `MILK MASTER PROMPT.md` (nome do arquivo tem espaços, não underscores).

## Objetivo atual

Evoluir o projeto Milk seguindo `MILK MASTER PROMPT.md`.
Diagnóstico completo e estado por componente estão em `MILK_STATUS.md`.

## Progresso concluído

Fases 1 a 4 da ordem de execução da especificação: auditoria, backup, diagnóstico e correção dos bugs críticos.

Correções aplicadas e testadas na sessão anterior:

- `corrigir_flac_windows()` — destrava o reconhecimento de voz em Windows ARM64.
- Fila de fala (`fila_fala`, `proxima_fala()`, `parar_fala()`) — falas não se sobrepõem e "Milk, pare." interrompe.
- `formatar_chat()` com `html.escape()` — código com `<` deixou de sumir da janela.
- Avisos de "ocupada" no lugar de retornos silenciosos.

Modularização concluída nesta sessão. O arquivo único de 1.555 linhas foi quebrado em pacotes, sem alterar comportamento:

```
milk.py                            ponto de entrada (chama milk.core.app.main)
milk/core/config.py                caminhos, voz, microfone, dono e latido
milk/core/texto.py                 e_comando_parar, formatar_chat, limpar_para_voz
milk/core/pessoa.py                quem está falando (detecção e persistência)
milk/core/app.py                   main()
milk/voice/flac_fix.py             corrigir_flac_windows()
milk/voice/microfone.py            MicrofoneWorker (aplica a correção do FLAC na importação)
milk/voice/tts.py                  TTSWorker
milk/intelligence/prompt.py        identidade da Milk e tom de conversa
milk/intelligence/claude_bridge.py ClaudeWorker em fluxo, com progresso
milk/avatar/chat.py                ChatBubble
milk/avatar/mascote.py             MilkMascot
```

Verificações feitas depois da modularização:

- todos os módulos importam sem erro no `.venv`;
- a correção do FLAC continua ativa (`get_flac_converter()` retorna o `flac-win32.exe` embutido);
- `QApplication` + `MilkMascot` sobem, criam o chat e a bandeja, e encerram sem erro;
- comparação linha a linha com o arquivo antigo: nenhuma linha de código foi perdida, só os blocos de import foram reorganizados e `app.exec()` virou `return app.exec()`.

Depois da modularização, ainda nesta sessão, entraram três coisas pedidas pelo usuário.

**1. Quem está falando.** `milk/core/pessoa.py` guarda o nome em `milk_pessoa.json`.
A Milk só pergunta quando não sabe: no primeiro uso, ou quando alguém se apresenta como outra pessoa
("sou a Ana", "meu nome é Rafael", "me chama de Lu"). Com o dono (Thales) ela é direta e íntima;
com qualquer outra pessoa ela é cordial e um pouco mais formal. O tom é montado em `milk/intelligence/prompt.py`.

**2. Persona fechada.** A identidade dela diz para nunca citar a tecnologia por trás: nada de Claude,
Anthropic, modelo, treinamento ou prompt. Se perguntarem se ela é uma pessoa, ela não afirma que é humana —
responde como a cachorrinha assistente da casa e segue ajudando. Testado com a pergunta direta
"você é uma IA? quem te criou? usa ChatGPT ou Claude?": ela não entregou nada.

**3. Progresso visível.** `ClaudeWorker` agora roda `claude -p ... --output-format stream-json --verbose`
e lê o processo em fluxo. Cada ferramenta usada vira uma frase curta na barra de status
("📖 Lendo config.py", "⚙️ Conta linhas do arquivo", "🌐 Pesquisando na internet"), junto com o tempo decorrido.
O timeout de 600 s virou um relógio que encerra o processo.

**4. Estilo de fala.** O plugin caveman deixava a fala da Milk telegráfica. Resolvido em duas camadas,
sem tocar na configuração global:

- `milk/core/config.py` tem `CLAUDE_SETTINGS`, passado em `--settings` na chamada da Milk. Vale só para o processo dela.
- `.claude/settings.json` na raiz do projeto desliga o plugin para qualquer sessão aberta nesta pasta.

Verificado: nesta pasta o hook não carrega; fora dela continua carregando normalmente.

**Latido.** Como `latido.wav` não existe, o latido saiu na voz dela: "Au au!" antes de cumprimentar.
Se um dia existir um `latido.wav` na pasta, ele passa na frente automaticamente.
Ao abrir a conversa pelo microfone o latido é pulado, senão ele entraria na gravação.

Verificado ao vivo: pedido real respondido com o progresso aparecendo passo a passo na janela,
nome detectado e salvo em disco, troca de pessoa no meio da conversa, e o relógio parando no fim.

Nesta sessão entrou a camada de ferramentas externas, sem tocar em nada do que já funcionava.

```
config/settings.json                       configurações das ferramentas (sem segredos)
milk/core/settings.py                      leitura do settings.json, com padrões seguros
milk/tools/__init__.py                     contrato comum (Resultado, ErroFerramenta)
milk/tools/http.py                         cliente HTTP compartilhado (urllib)
milk/tools/clima.py                        Open-Meteo
milk/tools/cep.py                          ViaCEP (BrasilAPI de reserva)
milk/tools/brasil_api.py                   BrasilAPI: CEP e feriados
milk/tools/moedas.py                       Frankfurter
milk/tools/wikipedia.py                    Wikimedia
milk/tools/github_api.py                   GitHub
milk/tools/feriados.py                     Nager.Date (BrasilAPI de reserva)
milk/tools/localizacao.py                  Nominatim
milk/intelligence/roteador.py              ferramenta ou Claude
milk/intelligence/ferramenta_worker.py     QThread que roda a ferramenta
```

O fluxo novo cabe em três linhas dentro de `ChatBubble.processar()`: depois da guarda de
"ocupada" e antes de montar o prompt, `rotear(texto)` responde com uma `Decisao` ou com None.
None é o caminho de sempre, com o Claude pensando.

Verificações desta sessão:

- 24 módulos importam sem erro no `.venv`;
- 8 APIs consultadas ao vivo, uma a uma, com os casos de falha junto (CEP inválido, CEP
  inexistente, verbete inexistente, repositório inexistente): 18 de 18;
- roteador com 59 frases, positivas e negativas: todas certas, incluindo "pesquise quem criou
  o Python", que continua indo para o Claude, como pedido;
- ferramenta rodando por `QThread` com a interface viva (168 batidas de um relógio de 50 ms
  durante a consulta, ou seja, a janela não travou);
- `python milk.py` sobe e fica de pé, sem traceback.

**Latido de verdade.** O "au au" saía na voz neural feminina pronunciando as palavras, porque
`latido.wav` nunca existiu. Agora existe `milk/voice/latido.py`, com `QSoundEffect` (já vem no
PySide6): carrega o WAV uma vez, guarda em memória, toca sem bloquear e sem abrir janela.
O arquivo mora em `assets/sounds/latido.wav`, caminho definido só em `milk/core/config.py`.
O volume fica em `config/settings.json` (`latido.volume`).

A voz neural dizendo "Au au" foi removida: sem o arquivo, ela simplesmente não late.

O comando é explícito e local — "Milk, late", "dá um latido", "quero ouvir você latir",
"faça au au". Roda na hora, sem thread e sem Claude, porque `play()` volta na mesma hora.
A resposta aparece escrita ("Au au! 🐶") mas **não** vai para o TTS, senão voltaria o problema
original. Para isso, `Decisao` ganhou dois sinalizadores (`local` e `silenciosa`) e
`receber_claude` ganhou o parâmetro `falar=True`, que não muda nada no caminho do Claude.

Pedidos como "faça um programa que toque latido" e "pesquise sobre latidos de cachorro"
continuam indo para o Claude. Testado.

Não há latido automático: ela não late ao iniciar por conta própria nem antes de responder.
Os pontos onde `latir()` já era chamado antes continuam iguais (ao abrir a conversa pelo clique
e ao registrar o nome de alguém), só que agora tocando o arquivo em vez da voz.

## Arquivos modificados

- `milk.py` — reduzido a ponto de entrada.
- `milk/` — pacote novo com os módulos acima.
- `milk/core/pessoa.py` e `milk/intelligence/prompt.py` — módulos novos.
- `.claude/settings.json` — desliga o plugin caveman só neste projeto.
- `milk_pessoa.json` — criado na primeira vez que alguém se identifica.
- `backups/milk_20260830_181736_pre_modularizacao.py` — backup do arquivo único completo.
- `MILK_STATUS.md`, `CONTEXT.md` — atualizados.
- `milk/avatar/chat.py` — duas linhas de import, o atributo `ferramenta_worker`, a guarda da
  consulta em andamento, a chamada ao roteador e os métodos `preparar_pedido`,
  `usar_ferramenta` e `receber_ferramenta`. Nada foi removido.
- `milk/core/config.py` — a constante `SETTINGS_FILE` e o `BARK_FILE` apontando para
  `assets/sounds/latido.wav` com `pathlib`.
- `milk/voice/latido.py` — módulo novo do efeito sonoro.
- `milk/avatar/mascote.py` — `latir()` delega para o módulo novo; saiu o `winsound` e saiu a
  voz neural dizendo "Au au".
- `assets/sounds/` — pasta criada. **O `latido.wav` ainda precisa ser colocado aí.**
- `backups/chat_20260831_200233_pre_tools.py` e `backups/config_20260831_200233_pre_tools.py`
  — backups feitos antes de editar esses dois.
- `milk/tools/relogio.py` — módulo novo de horário e calendário.
- `milk/core/eventos.py`, `milk/tasks/` (`__init__.py`, `modelos.py`, `persistencia.py`,
  `gerente.py`) e `milk/intelligence/rotas_tarefas.py` — módulos novos da Fase 9.
- `milk/core/config.py` — a constante `TASKS_FILE`.
- `milk/core/app.py` — marca como interrompida a tarefa que estava rodando ao fechar.
- `milk/avatar/chat.py` — dependência nova (`gerente_de_tarefas`), `tarefa_atual`,
  `origem_do_pedido`, assinatura do evento de cancelamento, o bloco `FILA DE TAREFAS`
  (`iniciar_tarefa`, `puxar_proxima`, `tarefa_concluida`, `tarefa_falhou`,
  `progresso_da_tarefa`, `quando_cancelam`, `frase_da_fila`) e o caminho discreto
  (`mostrar_pedido`, `responder`, `responder_direto`). Backup em
  `backups/chat_20260905_163609_pre_tarefas.py`.
- `milk/avatar/passeio.py` — `DESCANSO_MIN`/`DESCANSO_MAX` de volta em 20 s e 60 s.
- `assets/sounds/latido.wav` e `assets/sounds/LEIA-ME.md` — o latido de verdade e a licença.
- `tests/test_tarefas.py` — 57 testes novos.
- `tests/test_chat_di.py` e `tests/test_relogio.py` — passaram a injetar uma fila só na
  memória, para o teste não escrever no `milk_tarefas.json` de verdade.
- `milk/intelligence/roteador.py` — um import, o bloco `RELÓGIO E CALENDÁRIO` com os padrões e
  `rota_relogio`, e a entrada na lista `ROTAS`. Nada foi removido.
  Backup em `backups/roteador_20260905_143930_pre_relogio.py`.
- `tests/test_relogio.py` — 35 testes novos.

## Decisões importantes

- O reconhecimento de voz falhava sempre porque `speech_recognition` não reconhece `platform.machine() == "ARM64"` ao localizar o binário FLAC embutido. Optou-se por apontar o caminho do `flac-win32.exe` embutido em vez de trocar de biblioteca, já que o binário roda por emulação x86 nesta máquina (`flac 1.3.2` confirmado).
- A fala passou a usar fila em vez de descartar texto quando já havia áudio em andamento.
- As mensagens do chat passam por `html.escape()`.
- A Milk nunca revela a tecnologia por trás. Único limite mantido: se perguntarem diretamente se ela é uma pessoa, ela não afirma ser humana.
- O nome de quem fala fica em `milk_pessoa.json`, não em memória. Ela não repergunta a cada sessão.
- O plugin caveman foi desligado por projeto (`.claude/settings.json`) e também por processo (`--settings` na chamada da Milk). A configuração global do usuário não foi alterada. `--bare` foi descartado: pula os hooks, mas exige `ANTHROPIC_API_KEY` e quebraria a autenticação atual.
- O progresso usa `--output-format stream-json`, que é o mesmo processo de antes, só lido em fluxo. Nada de segunda chamada.
- Na modularização, o código foi movido sem reescrita: mesma lógica, mesmos nomes, mesmo estilo. Refatorações de conteúdo ficam para as fases seguintes, uma de cada vez.
- As ferramentas usam `urllib.request` da biblioteca padrão. `requests` não está instalado e não
  foi instalado: o projeto continua com as mesmas dependências de antes.
- O roteador é conservador por decisão explícita. Ele tem uma lista de veto (faça, crie, script,
  arquivo, instale, clone...) e só intercepta pergunta objetiva. Na dúvida, Claude.
- "Quem é X" e "o que é X" vão para a Wikipédia; "quem criou o Python" não vai, porque a
  Wikipédia responde a verbetes, não a pergunta em linguagem natural.
- O token do GitHub nunca fica no projeto. O `settings.json` guarda só o NOME da variável de
  ambiente (`github.token_env`), e o código lê de `os.environ`. Sem token funciona, com o limite
  público de 60 consultas por hora.
- Falha de ferramenta não vira aviso técnico: a frase amigável é falada pela Milk como resposta
  normal. Ela não repete o pedido pelo Claude sozinha.
- Nominatim tem trava de um pedido por segundo e User-Agent próprio, como a política pede.
- ViaCEP é o principal e BrasilAPI é a reserva; Nager.Date é o principal e BrasilAPI é a reserva
  dos feriados. Nenhuma ferramenta tem duas portas de entrada para o usuário.
- `corrigir_flac_windows()` é chamada na importação de `milk/voice/microfone.py`, perto de onde é usada, em vez de ficar solta no ponto de entrada.
- O diretório do pacote `milk/` convive com o arquivo `milk.py`. Isso funciona porque o pacote tem prioridade na importação e `milk.py` só roda como `__main__`, mas é um ponto de atenção se algum dia alguém tentar `import milk` a partir de outra pasta.

## Ambiente verificado

Windows 11 ARM64, Python 3.14.7 em `.venv`, Claude Code CLI 2.1.251, microfone "Grupo de Microfones (Qualcomm)" a 44100 Hz.

## Refatoração — Fase 1 (injeção de dependência) CONCLUÍDA

`ChatBubble.__init__` passou a aceitar as sete dependências como argumentos somente-nomeados,
todos com o valor de sempre como padrão: `criar_claude_worker`, `criar_microfone_worker`,
`criar_ferramenta_worker`, `roteador`, `montador_prompt`, `ler_pessoa`, `gravar_pessoa`.
`ChatBubble(self)` em `mascote.py` não mudou. Único arquivo de produção alterado: `milk/avatar/chat.py`.

Primeira suíte automatizada do projeto: `tests/test_chat_di.py`, 13 testes em `unittest`
(biblioteca padrão, nenhuma dependência nova). Rodar com:
`.venv\Scripts\python.exe -m unittest discover -s tests -v` — passa com `QT_QPA_PLATFORM=offscreen`.
Backup em `backups/chat_20260904_151252_pre_di.py`.

Fases 2 a 4 (dispatcher, ConfirmationManager, pipeline do `processar()`) planejadas mas **não iniciadas**.

## Passeio pela tela (feito)

`milk/avatar/passeio.py` — a Milk fica parada 20 a 60 s e então caminha até um ponto sorteado,
rente ao pé de algum monitor, a 3 px por tique de 30 ms (~100 px/s). Atravessa monitores.
Ela só anda quando não está sendo arrastada, o estado é "parada" e a conversa está fechada;
se perder a permissão no meio do caminho, para onde está. Liga e desliga pelo menu do botão
direito ("🚶 Passear pela tela"). Nenhuma dependência nova.

`abrir_chat` passou a usar `QGuiApplication.screenAt()` no lugar de `primaryScreen()`: depois
que ela anda para o segundo monitor, os dois deixaram de ser o mesmo e a conversa abriria longe dela.

Testes: `tests/test_passeio.py`, 16 testes com monitores e sorteio injetados (valem em qualquer
máquina). Backup em `backups/mascote_20260904_152831_pre_passeio.py`.

## Animação do corpo (feito, com limite conhecido)

`milk/avatar/animacao.py` — 25 quadros por segundo redesenhando o PNG com `QPainter`,
pivô nos pés: quique de 4 px por passo, inclinação de ±3° alternando a cada dois passos,
espelhamento ao mudar de direção e respiro de ±1,5% quando parada. 13 testes em `tests/test_animacao.py`.

**O quique é regido pela distância caminhada (`PASSO_PX`), não pelo relógio.** É o que amarra o
corpo ao chão: quando ela freia para chegar, o corpo desacelera junto em vez de patinar.

## Visual mais clássico e movimento natural (feito)

Escolhas do usuário: **avatar a 110 px** (era 189), **plaquinha "Milk" removida**, **estado mantido**
em corpo 10 px, sem caixa escura, com sombra para ficar legível sobre qualquer papel de parede.
Janela de 230x285 para 140x168.

`Passeio` ganhou movimento natural: posição em número quebrado (a janela só aceita pixel inteiro,
mas o resto é o que permite frear de verdade), rampa de arrancada e de frenagem de 70 px com piso
de 35% da velocidade, ritmo sorteado por volta (0,75x a 1,30x) e paradinhas ocasionais no meio do
caminho — nunca em cima das rampas, que pareceria travamento. Medido: arranque a 1,16 px/tique,
regime a 3,32.

## Porta pronta para a arte de caminhada (feito)

`milk/avatar/quadros.py` + `assets/avatar/LEIA-ME.md`. Assim que existir um ciclo de caminhada em
`assets/avatar/`, a Milk passa a mexer as patinhas **sem mudar uma linha de código**. Aceita, nesta
ordem: `andando.webp`, `andando.gif`, folha de sprites `andando.png` (quadros quadrados lado a lado)
ou `andando/01.png, 02.png, ...`. Quadro desproporcional é descartado na carga.

Com quadros, o desenho manda e o quique procedural sai de cena (senão seria animação duas vezes);
parada, ela volta ao PNG sentado. O avanço no ciclo é regido pela distância, igual ao quique.

Verificado de ponta a ponta com uma folha de teste de 6 quadros: carregou os 6 na altura certa,
`anima_desenhada` virou True ao caminhar, e os quadros trocaram conforme ela andava. A folha de
teste foi apagada; a pasta tem só o LEIA-ME.

**Limite que não se resolve com código:** o `milk_avatar.png` é a cachorrinha **sentada e de frente**.
Não há ciclo de caminhada a extrair, e o rabo não é separável — verificado recortando a região:
o corte deixa o corpo amputado, porque é pelo branco sobre pelo branco. Para ela caminhar de verdade,
com as patas e o rabo abanando, é preciso **arte nova: GIF ou quadros dela de perfil, andando, fundo
transparente**. Aí entra `QMovie` em ~15 linhas e esta camada procedural sai de cena.

Efeito colateral aceito: ao andar para a esquerda a imagem espelha, então a plaquinha "Milk" da coleira
fica invertida. No tamanho em que ela aparece, é ilegível de qualquer forma.

**TEMPORÁRIO:** `DESCANSO_MIN` e `DESCANSO_MAX` estão em 3 s para a demonstração.
Os valores de trabalho são 20 s e 60 s.

## Horário e calendário local (feito)

A parte que faltava da Fase 8: pergunta de relógio não gasta um pedido ao Claude nem uma
chamada de rede. `milk/tools/relogio.py` responde na hora, lendo o relógio da máquina.

O que ela responde: que horas são, que dia é hoje, dia da semana, que dia é amanhã e que dia
foi ontem, em que mês e em que ano estamos, e quantos dias faltam para uma data
("o Natal", "25/12", "dia 10 de outubro", "31/12/2027").

Escolhas:

- Toda função aceita `agora`. Em produção vem `datetime.datetime.now()`; nos testes entra uma
  data fixa, senão o resultado mudaria de um dia para o outro.
- Os nomes de dia e mês são escritos à mão. O `locale` do Windows não é confiável para
  português e mudaria conforme a máquina.
- Meio-dia e meia-noite têm nome, e singular é respeitado ("é 1 hora", "e 1 minuto").
  Formato de 24 horas, sem converter para "da tarde".
- Sem ano dito, a data é a **próxima** ocorrência: em setembro, "1 de janeiro" é o ano que vem.
  Com ano dito, vale o ano dito, mesmo no passado ("já passou, faz N dias").
- Data que ela não reconhece ("quantos dias faltam para eu terminar o projeto") devolve None e
  segue para o Claude, como o resto do roteador.
- A decisão é `local=True`, igual ao latido: roda na thread da interface, porque não há rede
  nem espera. Diferente do latido, ela **é** falada (`silenciosa=False`).

`rota_relogio` entrou no roteador logo depois do latido, antes do CEP.

Verificado: 35 testes novos em `tests/test_relogio.py` (a ferramenta, o entendimento de datas,
as rotas positivas e negativas, e a conversa completa pelo `ChatBubble` — a hora sai falada e
o Claude não é chamado); suíte inteira do projeto em 102 testes, tudo passando; 17 frases das
rotas antigas conferidas uma a uma, nenhuma mudou de destino; 33 módulos importam sem erro.

## Latido de verdade, passeio devolvido e microfone medido (feito)

**O latido agora é real.** O usuário enviou `Maltese-dog-barking-sound-effect.mp3`
(Orange Free Sounds, CC BY-NC 4.0, uso não comercial com atribuição). Dos 13 latidos do
arquivo de 20 s, foi recortado o par mais equilibrado (13,66 s a 14,30 s), com 8 ms de
subida e descida para não estalar, em WAV mono 44100 Hz PCM de 16 bits — o formato que o
`QSoundEffect` toca direto. Está em `assets/sounds/latido.wav`, com a origem e a licença
registradas em `assets/sounds/LEIA-ME.md`. Verificado tocando: `latir()` devolve True,
status `Ready`, tocando por ~0,64 s e parando sozinho. O latido sintético que eu havia
gerado antes foi substituído por este.

**Passeio devolvido ao ritmo de trabalho.** `DESCANSO_MIN` e `DESCANSO_MAX` voltaram para
20 s e 60 s. O bloco "TEMPORÁRIO" saiu do arquivo.

**Microfone: o caminho todo funciona, o aparelho não está entregando som.**
Medido nesta sessão, com o hardware real:

- o `MicrofoneWorker` rodou de ponta a ponta — gravou 7 s, converteu com o ffmpeg embutido
  e falou com o Google, que respondeu;
- a transcrição de um arquivo com voz de verdade (`teste_microfone.wav`) devolveu
  *"viu que você tá conseguindo me ouvir viu que você está conseguindo"*, ou seja,
  reconhecimento e correção do FLAC estão bons. Sem `corrigir_flac_windows()` a mesma
  chamada levanta `OSError`, o que confirma que a correção é o que sustenta isso;
- mas o que o microfone entrega é silêncio: **pico de 15 em 32767, RMS 3,3**. Toquei o
  latido pelos alto-falantes durante uma gravação de 5 s e o nível não mudou (3,4 no
  silêncio, 3,3 com o som tocando);
- a permissão do Windows está liberada (`ConsentStore\microphone` = Allow, em HKCU e HKLM)
  e os dois aparelhos aparecem como OK (`Grupo de Microfones (Qualcomm)` e
  `Alto-falantes (Qualcomm)`).

Conclusão: **não é software.** É mudo no mixer do Windows, volume no zero, ou o áudio
está indo para o fone Bluetooth "Headset (510)" que aparece na lista. Só o usuário pode
resolver isso na máquina.

Efeito colateral: `milk_microfone.wav` foi sobrescrito pela gravação de silêncio. Ele é o
arquivo de trabalho do microfone (`MIC_FILE`), então qualquer uso real do botão "🎤 Falar"
já o sobrescreveria. A gravação antiga com voz continua existindo em `teste_microfone.wav`.

## Fase 9 — Task Manager, fila persistente e Event Bus (feito)

O caminho do pedido agora é: **Milk → roteador → gerente de tarefas → Claude**.
Consulta rápida (hora, clima, CEP) continua respondendo na hora e não vira tarefa;
o que sobra é trabalho, e trabalho entra na fila.

```
milk/core/eventos.py               barramento de eventos internos
milk/tasks/modelos.py              Tarefa, Status, Prioridade
milk/tasks/persistencia.py         milk_tarefas.json, gravação atômica
milk/tasks/gerente.py              GerenteDeTarefas + o gerente do processo
milk/intelligence/rotas_tarefas.py controle da fila por voz
```

**A tarefa tem os doze campos da especificação**: id, descrição, prompt original, criação,
status, prioridade, origem, progresso, resultado, erro, início e término. Os oito status
(`QUEUED`…`INTERRUPTED`) e as quatro prioridades (`LOW`…`URGENT`) são os nomes da
especificação.

**A fila sobrevive a fechar a janela.** Grava em `milk_tarefas.json` por arquivo temporário
e troca no fim, então queda de energia no meio não corrompe o que já estava lá. Arquivo
ausente ou quebrado começa vazio, como o `settings.json`. O histórico para de crescer em 50
tarefas terminadas. Tarefa que aparece como `RUNNING` no disco é de um processo que morreu:
vira `INTERRUPTED` na abertura, e ao fechar a Milk a que estava rodando é marcada igual.

**O que mudou na conversa:** o segundo pedido durante um trabalho não é mais recusado
("Ainda estou no pedido anterior") — ele é anotado ("Anotei: X. Ficou em 2º na fila.") e
começa sozinho quando o anterior termina. Pergunta rápida no meio do trabalho é respondida
sem mexer na barra de progresso nem nos botões, porque quem está com eles é a tarefa que
está rodando.

**Prioridade sai do próprio jeito de pedir**: "isso é urgente" nasce `URGENT` e passa na
frente; "quando puder" nasce `LOW` e vai para o fim.

**Comandos de fila reconhecidos** (todos locais, sem Claude): o que você está fazendo;
quais tarefas estão pendentes; qual o progresso; pause; continue; cancele essa tarefa;
cancele a próxima; cancele tudo; coloque isso como prioridade; faça isso depois; repita a
última; limpe as tarefas concluídas.

**O barramento não é enfeite.** Cancelar é do gerente, matar o processo do Claude é da
janela. Quem liga os dois é o evento `TASK_CANCELLED`: a conversa assina, reconhece que a
tarefa cancelada é a que está rodando e chama `cancelar()` no worker. Nenhum dos dois
conhece o outro. O erro que chega depois (o processo morrendo) vira "Tarefa cancelada." em
vez de aviso de erro.

Verificações: 57 testes novos em `tests/test_tarefas.py` (barramento, modelos,
persistência com arquivo temporário, gerente, frases da fila, rotas e a conversa inteira
com dublê do Claude); 43 frases positivas e 9 negativas de comando de fila, todas certas;
suíte do projeto em **159 testes, tudo passando**; a Milk sobe, abre a conversa, e a fila
da janela é a mesma do processo (verificado ao vivo, offscreen).

Erro encontrado e corrigido no caminho: os radicais dos verbos estavam errados —
"coloque" se escreve com **qu**, e "limpar", "apagar", "mostrar" e "tirar" mudam de forma.
Passaram a usar radical + `\w*`. "Continue" e "pause" sozinhos são comando de fila; com
complemento ("continue o texto que eu escrevi") continuam indo para o Claude.

## Fases 4, 5, 10, 11, 17, 18, 21, 22, 23, 25, 26, 27, 28 e 29 (feito)

Esta rodada fechou as camadas que faltavam para a Milk ser assistente de verdade, e não
só uma janela de conversa. Cada peça entrou com teste próprio.

### Logs (Fase 18)

`milk/core/log.py` — um arquivo por área em `logs/` (app, voice, claude, tasks, tools,
system, errors), com rotação de 1 MB e três gerações. **Segredo não entra no log:** todo
registro passa por um filtro que troca token, senha e chave por `***`. Erro vai para a
área dele e também para `logs/errors`. Sem disco, o logger existe e não escreve — nada
quebra por causa de log.

`milk/core/arquivo.py` — leitura e gravação de JSON com troca atômica, usada pela fila,
pela memória, pelos modos e pela posição. Era código repetido na persistência de tarefas.

### Memória (Fase 11)

`milk/memory/memoria.py`, com as três camadas da especificação:

- **curto prazo**: as últimas 40 falas, em `milk_conversa.json`. Ao abrir, a conversa
  recomeça de onde parou — a Milk sabe do que vocês estavam falando.
- **persistente**: fatos e preferências ("lembre que eu prefiro respostas curtas"), em
  `milk_memoria.json`.
- **projetos**: nome, caminho e as dez últimas anotações de cada projeto.

**Segredo não é memorizado.** Frase com senha, token, chave ou cartão é recusada com uma
explicação, e nada é gravado.

O que ela sabe entra no prompt em bloco curto (12 fatos, no máximo), antes do pedido —
mandar tudo a cada vez gastaria contexto e pioraria a resposta.

Comandos: lembre que…, o que você sabe sobre mim, o que você sabe sobre X, esqueça X,
esqueça tudo, estou trabalhando no projeto X, o que fizemos hoje/ontem (este último lê o
histórico de tarefas da fila).

### Ferramentas do Windows e camada de permissão (Fase 10)

```
milk/system/permissao.py    SAFE / SENSITIVE / DESTRUCTIVE / CRITICAL
milk/system/acoes.py        as ações, com resultado SUCCESS/ERROR/DENIED/TIMEOUT
milk/system/confirmacao.py  a ação que está esperando um "sim"
```

Ela abre programa (26 nomes conhecidos), pasta (inclusive "downloads", "documentos",
"área de trabalho"), arquivo e site; procura arquivo pelo nome nas pastas do usuário;
conta memória, disco, bateria e há quanto tempo a máquina está ligada (pela API do
Windows, sem subprocesso); lista os programas que mais gastam memória; cria pasta, copia,
move e apaga arquivo; e roda PowerShell.

**A regra é a permissão, não a boa vontade:**

- SAFE acontece na hora;
- SENSITIVE e DESTRUCTIVE viram uma pergunta e só acontecem depois do "sim" — que caduca
  em dois minutos e é cancelado se a pessoa mudar de assunto;
- CRITICAL **não acontece nem confirmado**: formatar, diskpart, bcdedit, shutdown, apagar
  dentro de `C:\Windows`, mexer em HKLM, remover conta, baixar-e-executar da internet. Ela
  explica e para.

O caminho agrava a ação: apagar em Downloads é DESTRUCTIVE; o mesmo apagar dentro do
Windows é CRITICAL.

O roteador é conservador como sempre: **só intercepta quando reconhece o alvo**. "Abra um
arquivo novo e escreva um script" não vira ação de sistema, porque não existe programa com
esse nome — segue para o Claude, que sabe programar.

### Escuta contínua com wake word (Fases 4 e 5)

```
milk/voice/vad.py          detecta início e fim de fala por energia
milk/voice/escuta.py       o laço de escuta e o wake word
milk/voice/transcricao.py  gravar, converter e reconhecer (saiu do MicrofoneWorker)
```

Ligada pelo menu do botão direito, ela ouve a sala, mede o silêncio do ambiente nos
primeiros blocos e transcreve **só os trechos com fala** — em vez dos 7 segundos fixos do
botão. Se a fala começar com o nome dela, atende; se não, descarta sem mostrar nada.
Depois de atender, ela segue ouvindo por 12 segundos sem exigir o nome de novo, como
numa conversa normal.

**Por que não um modelo local de wake word:** esta máquina é Windows ARM64, sem roda para
`torch`, `vosk` e companhia. O gatilho é o reconhecimento que já funciona, aplicado só ao
que tem voz. O detector de energia é o que segura o silêncio aqui dentro: a sala não fica
sendo enviada para lugar nenhum.

### Modos, avisos e presença (Fases 26, 27 e 28)

`milk/core/modos.py` — NORMAL, SILENT e DO_NOT_DISTURB, guardados em `milk_modo.json`.
O trabalho continua igual nos três: o que muda é se ela fala, se late e se aparece
sozinha. O botão de voz da conversa e o menu do avatar mexem no mesmo estado.

Avisos naturais: quando uma tarefa da fila começa sozinha ela diz "Terminei essa. Vou
começar a próxima: …", e quando a fila esvazia, "Terminei tudo."

`milk/avatar/posicao.py` — ela volta para onde estava. A posição guardada só vale se
ainda couber em algum monitor de hoje: quem desconectou o segundo monitor não acha a Milk
fora da tela.

### Milk Doctor (Fases 23 e 25)

`milk/core/doutor.py` — treze exames com causa provável e conserto: arquivos, Claude,
estilo de fala, internet, microfone, reconhecimento, voz, latido, tarefas, memória,
ferramentas, disco e logs.

O exame do microfone é o único que mede o mundo real: grava meio segundo e olha o nível.

```
python milk.py doutor      relatório completo no terminal
"Milk, você está bem?"     resumo falado, relatório inteiro no log
```

Dois erros meus apareceram justamente por causa dele e foram corrigidos: o exame do FLAC
olhava `speech_recognition.get_flac_converter` (o nome reexportado, que continua sendo o
original) em vez de `speech_recognition.audio.get_flac_converter`, que é o que o remendo
troca e o que o reconhecimento chama; e o exame do estilo de fala tratava `CLAUDE_SETTINGS`
como caminho, quando ele é o próprio JSON passado em `--settings`.

### Sobreviver e iniciar (Fases 17, 21 e 22)

- `sys.excepthook` registra erro não tratado em `logs/errors` em vez de a Milk sumir sem
  rastro;
- tarefa que estava rodando quando a Milk fechou vira INTERRUPTED, na saída e na volta;
- `Milk.bat` abre sem janela de terminal (`pythonw.exe`), e `Milk.bat doutor` roda o
  diagnóstico com a janela aberta;
- `milk/system/inicio.py` liga e desliga o início com o Windows pela chave `Run` do
  usuário (HKCU), sem instalador e sem pedir administrador. Fica no menu do avatar.

### Verificações desta rodada

- **307 testes automatizados**, todos passando (eram 159 no início da rodada);
- prova de ponta a ponta com as peças de verdade, na Milk subida: hora local, memória
  guardando e respondendo, estado do computador, ação sensível pedindo confirmação, o
  "não" cancelando sem criar a pasta (conferido no Desktop), ação crítica recusada, troca
  de modo desligando a voz, e a memória em disco com o que foi dito;
- escuta contínua ligada e desligada com o microfone real: a thread sobe, informa o
  dispositivo, e encerra limpo;
- `python milk.py doutor` rodando na máquina: 12 de 13 exames OK, e o único FALHA é o
  microfone mudo — que é o problema real desta máquina;
- nenhum teste escreve nos arquivos de estado de verdade (fila, memória e modo entram por
  injeção nos testes).

### Erros meus corrigidos no caminho

1. Radicais de verbo errados nas rotas de fila ("coloque" é com **qu**; limpar, apagar,
   mostrar e tirar mudam de forma).
2. `rota_sistema` devolvia None no meio quando não reconhecia o alvo de "abrir", e isso
   engolia o comando de PowerShell que vinha depois. Agora a ordem é outra e nenhum ramo
   sai no meio.
3. O detector de fala contava o silêncio do fim como fala, então um clique curto virava
   trecho para transcrever. Passou a contar só os blocos com voz.
4. `projeto_recente()` empatava quando dois projetos eram anotados no mesmo segundo.
5. "O que você sabe sobre mim" caía na busca por assunto ("mim") em vez da pergunta geral.
6. A escuta contínua escrevia o pedido na conversa e o `processar()` escrevia de novo.

## Arquivos novos desta rodada

```
milk/core/log.py            logs por área, com rotação e sem segredo
milk/core/arquivo.py        JSON com gravação atômica (usado por todos)
milk/core/modos.py          NORMAL / SILENT / DO_NOT_DISTURB
milk/core/doutor.py         Milk Doctor: 13 exames com conserto
milk/memory/                memória de fatos, projetos e conversa
milk/system/permissao.py    SAFE / SENSITIVE / DESTRUCTIVE / CRITICAL
milk/system/acoes.py        as ações no Windows
milk/system/confirmacao.py  a ação esperando um "sim"
milk/system/inicio.py       iniciar com o Windows (HKCU\...\Run)
milk/voice/vad.py           detecção de fala por energia
milk/voice/escuta.py        escuta contínua com wake word
milk/voice/transcricao.py   gravar, converter e reconhecer
milk/avatar/posicao.py      a Milk volta para onde estava
milk/intelligence/rotas_memoria.py   comandos de memória
milk/intelligence/rotas_sistema.py   comandos de Windows e diagnóstico
Milk.bat                    abre sem terminal; "Milk.bat doutor" diagnostica
README.md                   como usar, o que ela faz, onde fica cada coisa
tests/test_memoria.py       40 testes
tests/test_sistema.py       59 testes
tests/test_escuta.py        19 testes
tests/test_doutor.py        28 testes (diagnóstico, modos, início, posição)
```

Arquivos antigos da raiz (`milk_backup.py`, `milk_v1_funcionando.py`, `milk_v2_backup.py`,
`milk_backup_homenagem.py`, `teste_microfone.py`, `milk_teste.mp3`) foram para
`backups/antigos/`.

## Ela atende quando é chamada (rodada de 05/09/2026, noite)

O microfone voltou a captar (`Grupo de Microfones (Qualcomm...)`) e a escuta contínua
finalmente rodou com voz de gente. O log de `logs/voice/voice.log`, das 20h04 às 20h16,
mostrou o problema real: **ela ouvia tudo e não atendia quase nada.**

Causa: o nome só valia no **começo** da fala. Estas frases, todas ditas de verdade
naquela sessão, foram ignoradas:

```
"Olá milk"                              -> ignorou
"Pode fechar o navegador para mim milk" -> ignorou
"jamilk boa noite tudo bem"             -> ignorou
"milk"                                  -> acordou, mas só escreveu na barra de status
```

O que mudou:

- **O nome vale em qualquer lugar da frase** (`NOME_FORTE`, em `milk/voice/escuta.py`).
  Em português a gente chama pelo nome no fim tanto quanto no começo. As formas curtas que
  também são palavra comum ("mil", "link", "mio") continuam valendo só no começo, senão
  qualquer conversa da sala viraria chamado. `tirar_o_nome()` limpa o vocativo venha ele
  de onde vier.
- **Ela late na hora em que é chamada.** O latido sai de `acordou_pelo_nome()`, antes do
  roteador e antes do Claude — é a única resposta que não depende de rede nenhuma.
- **Chamar só "Milk" agora tem resposta falada** (sinal `so_o_nome`). Antes isso só mudava
  um texto na barra de status, e quem chamava achava que ela não tinha atendido e ia
  clicar no botão. Era exatamente a queixa.
- **Ela já sobe ouvindo.** `microfone.escuta_automatica` no `config/settings.json`. Antes
  era preciso ligar a escuta no menu do botão direito a cada vez. Em "não perturbe" ela
  não liga sozinha.
- **O ouvido fecha enquanto ela late e fala** (`surdear()` / `voltar_a_ouvir()`). Sem isso
  a voz dela mesma cai na janela de conversa e ela responde a si própria. Quem manda
  fechar é o mascote, que é quem toca o som: no modo silencioso não há latido para
  ignorar. O detector ganhou `esquecer()`, que joga fora o trecho sem perder o piso da
  sala.
- **O microfone deixou de ser "auto" no settings.** Em automático ela testava todos os
  aparelhos a cada subida, o que atrasava o início. Agora o nome está fixo; se o aparelho
  sumir, ela volta a procurar sozinha.

### A demora

Medido nesta máquina, com o prompt real da Milk:

```
claude -p "oi"                    6,3 s   (só abrir o processo)
pergunta comum, modelo padrão    14,2 s
a mesma pergunta com haiku       11,0 s
```

O custo é a abertura do processo, não o modelo — trocar de modelo economiza três segundos
e piora a resposta, então não foi trocado. O que foi feito:

- **`milk/intelligence/rotas_conversa.py`** — "oi", "bom dia", "tudo bem?", "obrigado",
  "você está aí?", "tchau" e afins passaram a ter resposta pronta, local, em
  milissegundos. A regra é estreita: a **frase inteira** precisa ser conversa curta, senão
  "bom dia, abra o navegador" viraria só um "bom dia".
- **Ela avisa que vai demorar.** Pedido falado que desce para o Claude ganha um "deixa
  comigo, já te falo" na hora. Quem digitou está vendo a barra de progresso e não é
  interrompido.
- `SILENCIO_PARA_FECHAR` caiu de 0,8 s para 0,6 s: dois décimos a menos antes de ela
  começar a responder.

### Um efeito colateral da sessão de teste

Ela tinha gravado **"Fechar"** como o nome do dono em `milk_pessoa.json` — a palavra
escapou de "fechar navegador" enquanto ela esperava a resposta de "com quem eu estou
falando?". O arquivo foi corrigido para `Thales` e `PALAVRAS_NAO_NOME`
(`milk/core/pessoa.py`) passou a recusar palavra de comando como nome de gente.

### Verificações

- **336 testes automatizados**, todos passando (eram 315). O novo é
  `tests/test_atendimento.py`, e cada caso dele é uma frase que ela ouviu de verdade
  naquele dia e ignorou.
- **Corrente completa com voz falada de verdade**, do áudio ao pedido limpo:

```
"Milk."                 -> reconheceu 'milk'           -> acordou, pedido vazio -> responde falando
"Que horas são, Milk?"  -> reconheceu 'Que horas são milk' -> pedido 'Que horas são'
```

- **Corrente completa com a sua voz gravada** (`teste_microfone.wav`): o detector separou
  o trecho falado, a transcrição levou 0,9 s e saiu correta.
- **Milk subida de verdade**: sobe ouvindo sem ninguém clicar, o latido toca e fecha o
  ouvido, o fim da fala reabre, e o chamado só pelo nome escreve e fala a resposta.
- `python milk.py doutor`: 13 exames, nenhum FALHA. O microfone dá ATENÇÃO porque o padrão
  do Windows continua mudo — o que a Milk usa é o outro, e ela sabe disso.

**O que só você pode confirmar:** falar com ela ao vivo. O microfone Qualcomm desta
máquina cancela o som dos alto-falantes por hardware, então não deu para o computador
chamá-la em voz alta; a corrente foi provada com áudio de voz injetado nela.

## Rodada de 06/09/2026 — a arrumação, e dois erros que ela escondia

### O que mudou

- **`milk/avatar/chat.py` foi de 1.229 para 710 linhas.** O desenho da janela virou
  `milk/avatar/chat_ui.py` (`montar_interface(janela)`), e a fila de tarefas mais a
  resposta do Claude viraram `milk/avatar/chat_tarefas.py` (classe `FilaDeTarefas`,
  de que o `ChatBubble` herda). Nenhuma linha de comportamento foi reescrita: só
  mudaram de arquivo.

### Os dois erros

Ao separar o arquivo, o caminho do botão **🎤 Falar** ficou lado a lado com o da
escuta contínua, e aí deu para ver que os dois não entendiam a mesma coisa.

1. **O botão só tirava o nome do começo da frase.** A escuta contínua já usava
   `tirar_o_nome()`, que acha o nome em qualquer lugar; o botão tinha uma expressão
   própria, presa ao começo. Quem apertava o botão e dizia *que horas são, Milk*
   mandava para o roteador a frase inteira, com o vocativo dentro. Agora o botão usa
   o mesmo `tirar_o_nome()` — o botão não pode entender menos do que o ouvido dela.

2. **O nome no meio da frase deixava a vírgula dele para trás.** Este era da escuta
   contínua também, não só do botão: *fecha o navegador, Milk, por favor* virava
   *fecha o navegador,, por favor*. O vocativo do meio tem vírgula dos dois lados, e
   tirando o nome sobravam as duas. `PONTUACAO_REPETIDA`, em `milk/voice/escuta.py`,
   fica só com a última — a que separa o resto da frase.

### Verificações

- **342 testes automatizados, todos passando** (eram 336). Os 6 novos são os dois
  erros acima: `TestNomeNoBotaoDeFalar` em `tests/test_atendimento.py` (o caminho do
  botão, ponta a ponta) e `test_o_nome_no_meio_nao_deixa_virgula_sobrando` (a
  `tirar_o_nome` direto). Os dois falhavam antes da correção e passam depois.
- Os 336 de antes passam sem uma única alteração — a separação dos arquivos não
  mexeu no que ela faz.
- **Executável refeito e conferido**: `dist\Milk\Milk.exe`, 297 MB na pasta. Rodando
  `Milk.exe doutor` já empacotado, os 13 exames respondem, nenhum FALHA (o microfone
  dá ATENÇÃO porque a sala estava calada).

## Rodada de 06/09/2026, parte 2 — por que ela ficou calada

O log da sua sessão ao vivo (`dist/Milk/logs/`, 17h17 às 17h19) mostrou o que
aconteceu, e não era demora: era silêncio.

```
17:17:09  Milk abriu
17:17:10  escuta contínua ligada (Grupo de Microfones, 48000 Hz)
17:18:02  transcreveu: Silk fecha o navegador
          (e nada mais)
17:19:25  Milk fechou
```

### Ela já sobe ouvindo — isso não era o problema

A segunda linha do log é de um segundo depois de abrir, sem ninguém clicar em nada.
`escuta_automatica` está ligada no `config/settings.json` do projeto **e** no do
`dist\Milk\`. O que faltava não era ativar; era ela entender que era com ela.

### Erro 1: o reconhecimento escreve Silk, e Silk não era o nome dela

O `NOME_FORTE`, em `milk/voice/escuta.py`, cobria a troca da vogal e da consoante do
fim (`m[ie]l[kqc]`), mas não a do **começo**. O reconhecimento ouviu o seu chamado e
escreveu `Silk`; `tem_o_nome()` disse não, e ela ficou muda — sem latido, sem barra
de status, sem nada. Do lado de cá parece demora; era recusa.

Agora o padrão aceita a troca da primeira consoante (`\b[bcdfgjlnpqrstvxz]il[kqc]`):
Silk, Nilk, Bilk, Zilk. Nenhuma palavra comum do português termina em -ilk, -ilq ou
-ilc, então isso não transforma conversa em chamado — e há teste para os dois lados.

### Erro 2: fechar não tinha rota, e custava seis segundos

`rotas_sistema.py` tinha `ABRIR` com dez sinônimos e **nenhum** `FECHAR`. Ou seja:
*abre o bloco de notas* era instantâneo, e *fecha o navegador* — a sua frase — descia
para o `claude -p` e pagava os seis segundos de abertura de processo, para um comando
que o Windows resolve em um décimo de segundo.

Foram acrescentados:

- `FECHAR` / `FECHAR_PROGRAMA` em `milk/intelligence/rotas_sistema.py` (fecha, feche,
  fechar, encerra, encerrar, sai do, sair do), só para programa que ela conhece;
- `fechar_programa()` em `milk/system/acoes.py`, com `taskkill /IM` **sem `/F`** — o
  mesmo que clicar no X, e o programa ainda pode perguntar se você quer salvar;
- `"navegador"` não é um executável só: ela tenta chrome, edge, firefox, brave e opera,
  e fecha os que estiverem abertos;
- `"fechar_programa": Nivel.SEGURA` em `milk/system/permissao.py` — sem pedir
  confirmação, senão voltaria a ser lento. `encerrar_processo` (matar o processo,
  perdendo o que não foi salvo) continua DESTRUTIVA, como era.

### O que ainda custa tempo, e por quê

Medido nesta máquina:

```
roteamento de 'fecha o navegador'      1,1 ms   (era: Claude, 6 s+)
fechar o bloco de notas de verdade     182 ms
fim da fala -> trecho fechado          0,6 s    SILENCIO_PARA_FECHAR
transcrição (rede, Google)             ~0,9 s
```

**O latido sai depois da transcrição, não antes** — ela só sabe que foi chamada
quando o texto volta da rede. Isso põe um piso de cerca de 1,5 s entre você falar e
ela dar sinal de vida, e esse piso não some sem reconhecimento de voz **local**, que
o Windows ARM64 desta máquina não permite (sem roda para torch, ctranslate2 e vosk).
É o limite de hoje, não um ajuste esquecido.

### Verificações

- **351 testes automatizados, todos passando** (eram 336 no início do dia). Os novos
  cobrem: o nome com a consoante trocada, as palavras comuns que **não** podem virar
  chamado, as seis formas de mandar fechar, e a ação de fechar em si.
- **Ao vivo, de verdade**: o bloco de notas foi aberto e fechado pela
  `fechar_programa()` em 182 ms, e o segundo pedido respondeu *não estava aberto*.
- **Executável refeito**: `dist\Milk\Milk.exe`, build das 17h34.

## Rodada de 06/09/2026, parte 3 — o navegador que ela dizia não existir

### O que ela respondia, e por quê

*O chrome não está instalado nesta máquina, ou não está no caminho do sistema.*

Ele está. Nesta máquina:

```
chrome.exe   registro=C:\Program Files\Google\Chrome\Application\chrome.exe   PATH=—
msedge.exe   registro=C:\Program Files (x86)\Microsoft\Edge\...       PATH=—
```

`abrir_programa()` chamava `subprocess.Popen(["chrome.exe"])`, e o **subprocess só
procura no PATH**. O Windows procura em dois lugares: o PATH e a chave
`App Paths` do registro — que é o que a caixa *Executar* usa. Chrome, Edge, Word,
Excel, Spotify e WhatsApp se registram lá e **não** entram no PATH. Ou seja: dos
programas que ela conhece, só funcionavam os do System32 (bloco de notas,
calculadora, paint, cmd, powershell). Todo o resto respondia *não está instalado*.

### A correção

`onde_esta(executavel)`, em `milk/system/acoes.py`: procura no PATH e, se não achar,
no registro (`HKCU` e `HKLM`, visão de 64 e de 32 bits), confirmando que o arquivo
existe. O `Popen` passou a receber o **caminho inteiro**, não o nome solto.

`ms-settings:` e afins não são arquivo — quem abre é o Windows — então esses continuam
indo direto para o `os.startfile`, sem passar pela busca.

### Navegar e ler: o que ela pode e o que não pode

- **Abrir o navegador**: agora funciona (`abre o chrome`, `abre o navegador`).
- **Abrir um endereço**: já funcionava — `abrir_url()` usa `os.startfile`, que passa
  pela associação do Windows e não depende de PATH nenhum.
- **Ler página da web**: **funciona**, pelo Claude. Testado com os mesmos parâmetros
  que ela usa (`claude -p ... --settings ...`): pedindo o título de `example.com`, a
  resposta voltou certa. Custa os ~6 s de abertura do processo, como todo pedido que
  desce para o Claude.
- **O que ela ainda não faz sozinha**: navegar por conta própria — clicar, rolar,
  preencher formulário, ler página dentro do processo dela. Isso é a Fase 13, que
  continua de fora por decisão. As 8 APIs próprias (Wikipedia, clima, CEP, moedas,
  feriados, GitHub, localização, BrasilAPI) respondem sem passar pelo Claude.

### Verificações

- **356 testes, todos passando** (eram 351). Os novos: acha programa no PATH, acha
  programa só no registro, abre pelo caminho inteiro, e o que não existe em lugar
  nenhum continua dizendo *não está instalado*. Há também um teste sem dublê, que
  procura Chrome e Edge de verdade nesta máquina.
- **Ao vivo**: `onde_esta()` achou os caminhos reais de Chrome, Edge e notepad, e
  devolveu `None` para o Firefox (que não está instalado aqui). `abrir_programa
  ('chrome')` abriu o Chrome de verdade, em 11 ms.
- O teste antigo `test_abrir_programa_conhecido` foi atualizado: ele exigia
  `['calc.exe']` no `Popen`, e agora exige o caminho inteiro. A mudança é proposital.
- **Executável refeito**: `dist\Milk\Milk.exe`, build das 18h52.

## Pendências

- **[RESOLVIDO] O microfone não entregava som.** O padrão do Windows continua mudo, mas o
  `Grupo de Microfones (Qualcomm...)` capta, e é ele que está fixado no
  `config/settings.json`. A escuta contínua já rodou com voz de gente.
- **Falta ouvir a escuta contínua ao vivo, com você falando.** A corrente inteira foi
  provada com áudio de voz injetado nela e com a sua voz gravada, mas o microfone desta
  máquina cancela o som dos alto-falantes, então o computador não consegue se chamar
  sozinho. Os números que regulam falso positivo e falso negativo são `FATOR_DE_FALA`,
  `SILENCIO_PARA_FECHAR` e `FALA_MINIMA`, em `milk/voice/vad.py`.
- **O executável está pronto e conferido**, em `dist\Milk\`. A pasta inteira é o que se
  copia (297 MB); o `Milk.exe` sozinho não anda. Para refazer:
  `.venv\Scripts\python.exe construir_exe.py`.
- **A Milk empacotada precisa do Claude Code instalado na máquina** (`claude.exe` no PATH).
  Sem ele, ela abre, ouve, late, atende, dá as horas, consulta as APIs e mexe no Windows —
  mas o que exige raciocínio responde "o comando Claude não foi encontrado".
- **Seis segundos por pedido são do processo do Claude**, não da Milk. Conversa curta e
  pergunta objetiva já não pagam esse pedágio; o resto paga. Fugir disso exigiria não usar
  o `claude -p`, o que é outra decisão.
- **[RESOLVIDO] `milk/avatar/chat.py` passou de 1.229 para 710 linhas**, abaixo do
  limite de 800 do próprio projeto. Saíram dois módulos: `milk/avatar/chat_ui.py` (252
  linhas — só o desenho da janela, `montar_interface(janela)`) e
  `milk/avatar/chat_tarefas.py` (330 linhas — a fila de tarefas e a resposta do Claude,
  na classe `FilaDeTarefas`, de que o `ChatBubble` herda). O que sobrou no `chat.py` é
  quem está falando, o microfone e a decisão do que fazer com cada pedido. Nenhum
  comportamento mudou: os 336 testes de antes continuam passando iguais.
- A pipeline do `processar()` continua sendo um método só, e o `ConfirmationManager`
  continua sendo o `responder_confirmacao` de 43 linhas. Nenhum dos dois incomoda hoje;
  quem incomodava era o tamanho do arquivo, e esse foi resolvido.
- As 8 APIs externas continuam sem teste dentro do projeto (foram testadas ao vivo, uma
  a uma, mas de uma pasta temporária que se perdeu).
- **A caminhada é procedural.** O `milk_avatar.png` é a cachorrinha sentada e de frente;
  para ela andar de verdade, com patas e rabo, é preciso arte nova (GIF ou quadros de
  perfil, fundo transparente). A porta já está pronta em `milk/avatar/quadros.py`.
- Windows ARM64 inviabiliza Whisper e Vosk locais (sem roda para `torch`, `ctranslate2`
  e `vosk`). Reconhecimento e voz dependem de internet, e o wake word é feito em cima do
  reconhecimento, não de um modelo local.
- Fases ainda de fora, por decisão: contexto de tela e OCR (12), browser (13), MCP (14),
  Skills como pastas (15) e Command Center (16). Nenhuma delas é necessária para o uso
  diário; todas exigem dependência nova ou muito código.

## Próximo passo exato

1. **Abrir a Milk (`dist\Milk\Milk.exe` ou `Milk.bat`) e chamar "Milk" em voz alta.** Ela
   já sobe ouvindo, sem clicar em nada. O que se espera: latido na hora, e resposta falada. Chame também com o
   nome no fim ("fecha o navegador para mim, Milk") — era esse caso que falhava.
2. **Testar as duas correções de hoje.** Chame com o nome no fim (*fecha o navegador
   para mim, Milk*) e mande fechar alguma coisa (*Milk, fecha o bloco de notas*) —
   fechar agora é instantâneo, sem passar pelo Claude. Se o reconhecimento escrever o
   nome de outro jeito ainda (Vilk, Guilk, Hilk), o log de
   `logs/voice/voice.log` mostra exatamente o que ele escreveu: é só uma letra a mais
   em `NOME_FORTE`, em `milk/voice/escuta.py`.
3. **Anotar falso positivo e falso negativo.** Se ela atender quando não era com ela,
   suba `FATOR_DE_FALA` em `milk/voice/vad.py` ou tire variantes de `NOME_FRACO` em
   `milk/voice/escuta.py`. Se ela deixar de atender, faça o contrário.
4. Anotar toda frase de conversa curta que ainda desce para o Claude (e portanto demora
   seis segundos à toa) — cada uma é uma linha em `milk/intelligence/rotas_conversa.py`.
5. Ao entregar `dist\Milk\` para outra pessoa: apagar o `milk_pessoa.json` de lá (ele diz
   "Thales") e conferir se a máquina dela tem o Claude Code instalado.
6. Depois, se fizer falta: contexto de tela com OCR (Fase 12) ou Command Center (Fase 16).
